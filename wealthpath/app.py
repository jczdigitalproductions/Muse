"""WealthPath AI: goal-based wealth pathways with Stripe Pro unlock.

Run:  python app.py   (from this folder, with the .venv active)
Env:  SECRET_KEY, STRIPE_SECRET_KEY (test, sk_test_...),
      STRIPE_WEBHOOK_SECRET (whsec_..., optional for localhost),
      WEALTHPATH_DB (sqlite path), PORT
"""
import json
import os
from functools import wraps

from flask import (
    Flask,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    session,
    url_for,
)

from db import (
    SEED_EMAIL,
    create_user,
    get_user_by_email,
    get_user_by_id,
    init_db,
    set_pro,
    verify_password,
)
from strategies import EFFORTS, TIMEFRAMES, generate

PRO_PRICE_CENTS = 2900
PRO_LABEL = "WealthPath Pro"


def create_app(db_path=None):
    app = Flask(__name__)
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-only-change-me")
    app.config["DB_PATH"] = db_path or os.getenv(
        "WEALTHPATH_DB",
        os.path.join(os.path.dirname(os.path.abspath(__file__)), "wealthpath.db"),
    )
    init_db(app.config["DB_PATH"])

    def current_user():
        if "user_id" not in session:
            return None
        if not hasattr(g, "user"):
            g.user = get_user_by_id(app.config["DB_PATH"], session["user_id"])
        return g.user

    def login_required(view):
        @wraps(view)
        def _wrapped(*args, **kwargs):
            if current_user() is None:
                if request.path.startswith("/api/"):
                    return jsonify({"error": "Login required."}), 401
                return redirect(url_for("login"))
            return view(*args, **kwargs)

        return _wrapped

    @app.route("/")
    def index():
        if current_user():
            return redirect(url_for("dashboard"))
        return redirect(url_for("login"))

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            user = get_user_by_email(
                app.config["DB_PATH"], request.form.get("email", "")
            )
            if user and verify_password(user, request.form.get("password", "")):
                session["user_id"] = user["id"]
                return redirect(url_for("dashboard"))
            return render_template(
                "login.html", error="Invalid email or password.",
                seed_email=SEED_EMAIL,
            )
        return render_template("login.html", seed_email=SEED_EMAIL)

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if request.method == "POST":
            email = request.form.get("email", "").strip()
            password = request.form.get("password", "")
            if "@" not in email or len(password) < 8:
                return render_template(
                    "register.html",
                    error="Enter a valid email and a password of 8+ characters.",
                )
            user_id = create_user(app.config["DB_PATH"], email, password)
            if user_id is None:
                return render_template(
                    "register.html", error="That email is already registered."
                )
            session["user_id"] = user_id
            return redirect(url_for("dashboard"))
        return render_template("register.html")

    @app.route("/logout", methods=["POST"])
    def logout():
        session.clear()
        return redirect(url_for("login"))

    @app.route("/dashboard")
    @login_required
    def dashboard():
        user = current_user()
        return render_template(
            "dashboard.html",
            email=user["email"],
            is_pro=bool(user["is_pro"]),
            timeframes=TIMEFRAMES,
            efforts=EFFORTS,
            pro_price="$29.00",
        )

    @app.route("/api/generate", methods=["POST"])
    @login_required
    def api_generate():
        user = current_user()
        body = request.get_json(force=True, silent=True) or {}
        try:
            amount = float(body.get("target_amount", 0))
        except (TypeError, ValueError):
            return jsonify({"error": "Target amount must be a number."}), 400
        if not 100 <= amount <= 100_000_000:
            return jsonify(
                {"error": "Target amount must be between $100 and $100,000,000."}
            ), 400
        timeframe = body.get("timeframe", "")
        effort = body.get("effort", "")
        try:
            result = generate(amount, timeframe, effort,
                              is_pro=bool(user["is_pro"]))
        except ValueError as exc:
            return jsonify({"error": str(exc)}), 400
        return jsonify(result)

    @app.route("/api/checkout", methods=["POST"])
    @login_required
    def api_checkout():
        secret = os.getenv("STRIPE_SECRET_KEY")
        if not secret:
            return jsonify({
                "error": "Payments not configured: set STRIPE_SECRET_KEY "
                "(Stripe test key) on the server."
            }), 503
        import stripe

        stripe.api_key = secret
        user = current_user()
        try:
            checkout_session = stripe.checkout.Session.create(
                mode="payment",
                line_items=[{
                    "price_data": {
                        "currency": "usd",
                        "unit_amount": PRO_PRICE_CENTS,
                        "product_data": {
                            "name": f"{PRO_LABEL} - one-time unlock",
                            "description": "Unlocks premium arbitrage strategies.",
                        },
                    },
                    "quantity": 1,
                }],
                metadata={"user_id": str(user["id"])},
                success_url=url_for("success", _external=True)
                + "?session_id={CHECKOUT_SESSION_ID}",
                cancel_url=url_for("cancel", _external=True),
            )
        except Exception as exc:  # surface Stripe errors plainly in test mode
            return jsonify({"error": f"Stripe error: {exc}"}), 502
        return jsonify({"url": checkout_session.url})

    @app.route("/api/checkout/verify")
    @login_required
    def api_verify():
        secret = os.getenv("STRIPE_SECRET_KEY")
        if not secret:
            return jsonify({"error": "Payments not configured."}), 503
        import stripe

        stripe.api_key = secret
        session_id = request.args.get("session_id", "")
        if not session_id:
            return jsonify({"error": "Missing session_id."}), 400
        try:
            checkout_session = stripe.checkout.Session.retrieve(session_id)
        except Exception as exc:
            return jsonify({"error": f"Stripe error: {exc}"}), 502
        user = current_user()
        paid = (
            checkout_session.payment_status == "paid"
            and (checkout_session.metadata or {}).get("user_id")
            == str(user["id"])
        )
        if paid:
            set_pro(app.config["DB_PATH"], user["id"],
                    checkout_session.customer)
        return jsonify({"paid": paid,
                        "is_pro": bool(paid or user["is_pro"])})

    @app.route("/api/stripe/webhook", methods=["POST"])
    def stripe_webhook():
        secret = os.getenv("STRIPE_SECRET_KEY", "")
        webhook_secret = os.getenv("STRIPE_WEBHOOK_SECRET", "")
        payload = request.get_data()
        if webhook_secret:
            import stripe

            try:
                event = stripe.Webhook.construct_event(
                    payload, request.headers.get("Stripe-Signature", ""),
                    webhook_secret,
                )
                event = event.to_dict() if hasattr(event, "to_dict") else event
            except Exception as exc:
                return jsonify({"error": f"Bad signature: {exc}"}), 400
        else:
            try:
                event = json.loads(payload or "{}")
            except ValueError:
                return jsonify({"error": "Invalid JSON."}), 400
        _ = secret  # key only needed for API calls, not webhook receipt
        if event.get("type") == "checkout.session.completed":
            obj = event.get("data", {}).get("object", {})
            user_id = (obj.get("metadata") or {}).get("user_id")
            if user_id:
                set_pro(app.config["DB_PATH"], int(user_id),
                        obj.get("customer"))
        return jsonify({"received": True})

    @app.route("/success")
    @login_required
    def success():
        return render_template("success.html",
                               session_id=request.args.get("session_id", ""))

    @app.route("/cancel")
    @login_required
    def cancel():
        return render_template("cancel.html")

    return app


app = create_app()


if __name__ == "__main__":
    port = int(os.getenv("PORT", "5000"))
    print(f"WealthPath AI on http://127.0.0.1:{port} "
          f"(demo login {SEED_EMAIL} / What!JCZ)")
    app.run(host="127.0.0.1", port=port)
