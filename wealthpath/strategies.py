"""Strategy generation engine for WealthPath AI.

Curated playbook across four categories, filtered and ranked per goal. When a
Meta/OpenAI-compatible endpoint is configured, an LLM drafts the personalized
path summary; the playbook itself always works offline. Yield figures are
illustrative ranges, clearly labeled as such in the UI.
"""
import os

TIMEFRAMES = {
    "1M": "1 Month",
    "3M": "3 Months",
    "6M": "6 Months",
    "1Y": "1 Year",
    "3Y": "3 Years",
    "5Y": "5 Years",
}

EFFORTS = {
    "passive": "Passive / Automated",
    "hustle": "Side Hustle / Active",
    "venture": "Business / Venture",
    "all": "All effort levels",
}

CATEGORIES = [
    ("bonuses", "Bank, Brokerage & Card Bonuses"),
    ("capital", "Crowdfunding & Alternative Capital"),
    ("gigs", "Targeted Income & High-Pay Gigs"),
    ("startup", "Startup Programs & Non-Dilutive Funding"),
]

STRATEGIES = [
    # -- a. Brokerage, bank & card bonuses --
    {
        "id": "bonus-ladder",
        "category": "bonuses",
        "title": "High-Yield Savings Bonus Ladder",
        "summary": "Stack 2-3 bank new-account bonuses alongside a high-yield "
        "account for your cash base.",
        "detail": "Several online banks pay $200-$500 for a qualifying direct "
        "deposit within 90 days. Open one primary high-yield account, then add "
        "one or two bonus offers whose deposit terms you can meet from normal "
        "cash flow. Track payout dates and minimum-balance windows on a simple "
        "calendar so no bonus claws back.",
        "yield_min": 200,
        "yield_max": 1500,
        "effort": ["passive"],
        "timeframes": ["1M", "3M", "6M", "1Y"],
        "premium": False,
        "next_steps": [
            "Compare current high-yield rates and bonus terms.",
            "Route one direct deposit to meet the qualifying activity.",
            "Calendar the payout date and any early-closure fee window.",
        ],
    },
    {
        "id": "broker-promo",
        "category": "bonuses",
        "title": "Brokerage Transfer & New-Account Promos",
        "summary": "Move existing invested cash to a broker paying a transfer "
        "bonus instead of leaving it idle.",
        "detail": "Major brokerages periodically pay $300-$2,500 for new assets "
        "above published tiers with a 9-12 month holding period. If you already "
        "hold the qualifying balance, this is a transfer, not new risk. Confirm "
        "the bonus tier, the assets-in-kind policy, and any account fees before "
        "moving.",
        "yield_min": 300,
        "yield_max": 2500,
        "effort": ["passive"],
        "timeframes": ["3M", "6M", "1Y"],
        "premium": False,
        "next_steps": [
            "List current promos and their qualifying tiers.",
            "Confirm in-kind transfer support for your holdings.",
            "Initiate the transfer and diary the holding-period end.",
        ],
    },
    {
        "id": "cashback-stack",
        "category": "bonuses",
        "title": "Cash-Back Card Setup on Existing Spend",
        "summary": "Route spend you already have through flat and category "
        "cards for a baseline rebate.",
        "detail": "A flat 2% card plus one rotating-category card turns existing "
        "bills and groceries into $150-$1,200 a year with autopay in full. The "
        "rule is strict: no carried balance, ever - interest wipes out every "
        "reward. Revisit categories quarterly as rotations change.",
        "yield_min": 150,
        "yield_max": 1200,
        "effort": ["passive"],
        "timeframes": ["1M", "3M", "6M", "1Y", "3Y", "5Y"],
        "premium": False,
        "next_steps": [
            "Pick one flat-rate and one category card.",
            "Enable autopay for the full statement balance.",
            "Review category rotations each quarter.",
        ],
    },
    {
        "id": "churn-calendar",
        "category": "bonuses",
        "title": "Arbitrage Calendar: Sequenced Bonus Harvesting",
        "summary": "A sequenced 12-month calendar that chains card, bank, and "
        "broker bonuses without overlap conflicts.",
        "detail": "Premium playbook: order applications so inquiry-sensitive "
        "issuers come first, bank bonuses second, and broker transfers last. "
        "Each quarter targets one card bonus plus one deposit bonus, keeping "
        "utilization low and spend organic. Includes a tracker for bonus "
        "deadlines, retention-offer scripts, and downgrade paths so annual "
        "fees never stick.",
        "yield_min": 1500,
        "yield_max": 8000,
        "effort": ["hustle"],
        "timeframes": ["3M", "6M", "1Y"],
        "premium": True,
        "next_steps": [
            "Pull your reports and sequence inquiry-sensitive issuers first.",
            "Schedule one card plus one deposit bonus per quarter.",
            "Set downgrade reminders before each annual fee posts.",
        ],
    },
    # -- b. Crowdfunding & alternative capital --
    {
        "id": "presell",
        "category": "capital",
        "title": "Pre-Sell a Defined Deliverable",
        "summary": "Fund the goal by pre-selling a concrete product, cohort, "
        "or service block on a crowdfunding page.",
        "detail": "Campaigns that fund have a defined deliverable, a fixed "
        "price, and a ship date. Draft the offer in one page, price three "
        "tiers, and collect the first 30% from your own network before launch "
        "day - platform traffic follows momentum, it does not create it.",
        "yield_min": 1000,
        "yield_max": 25000,
        "effort": ["hustle"],
        "timeframes": ["1M", "3M", "6M"],
        "premium": False,
        "next_steps": [
            "Write the one-page offer with tiers and a ship date.",
            "Line up 30% of the target from direct contacts.",
            "Launch and update backers weekly until fulfillment.",
        ],
    },
    {
        "id": "grant-sprint",
        "category": "capital",
        "title": "Grant-Database Sprint: 20 Applications in 30 Days",
        "summary": "A templated pipeline that turns one core narrative into "
        "twenty tailored grant applications.",
        "detail": "Premium playbook: build a single evidence pack - budget, "
        "milestones, bios - then adapt the cover narrative per funder from a "
        "shared library. Target small rolling-deadline grants first for fast "
        "feedback, and log every submission with decision dates and reviewer "
        "notes so each round compounds.",
        "yield_min": 2500,
        "yield_max": 50000,
        "effort": ["hustle"],
        "timeframes": ["3M", "6M", "1Y"],
        "premium": True,
        "next_steps": [
            "Assemble the evidence pack once, reuse everywhere.",
            "Submit to rolling-deadline grants first for fast signal.",
            "Log decisions and recycle winning language into new drafts.",
        ],
    },
    {
        "id": "community-round",
        "category": "capital",
        "title": "Community Round via a Regulated Portal",
        "summary": "Raise from supporters with a revenue-share or SAFE note "
        "through a compliant funding portal.",
        "detail": "Regulation crowdfunding portals let non-accredited backers "
        "participate with standard disclosures. Works best with an existing "
        "audience and a clear use of funds. Budget for portal fees and "
        "financial-review costs, and keep the round simple: one instrument, "
        "one close date.",
        "yield_min": 5000,
        "yield_max": 100000,
        "effort": ["venture"],
        "timeframes": ["3M", "6M", "1Y"],
        "premium": False,
        "next_steps": [
            "Choose one instrument and draft the use of funds.",
            "Prepare portal disclosures and review costs.",
            "Set a single close date and run a weekly update cadence.",
        ],
    },
    {
        "id": "capital-stack",
        "category": "capital",
        "title": "Alternative Capital Stack: Layered Non-Dilutive First",
        "summary": "Sequence presale, grant, and credit layers so each one "
        "de-risks the next.",
        "detail": "Premium playbook: open with a presale to prove demand, use "
        "presale traction in grant applications, then add a revenue-based line "
        "against contracted cash. Each layer is documented so diligence for "
        "the next takes days, not weeks. Includes covenant checks to avoid "
        "cross-default traps between layers.",
        "yield_min": 10000,
        "yield_max": 250000,
        "effort": ["venture"],
        "timeframes": ["6M", "1Y"],
        "premium": True,
        "next_steps": [
            "Close the presale layer to evidence demand.",
            "File grants citing presale traction.",
            "Add credit only against contracted revenue.",
        ],
    },
    # -- c. Targeted income / high-comp gigs --
    {
        "id": "productized-offer",
        "category": "gigs",
        "title": "Productized Freelance Offer at a Reset Rate",
        "summary": "Package your strongest skill as a fixed-scope, fixed-price "
        "offer and raise the rate 30-50%.",
        "detail": "Hourly billing caps income; fixed-scope offers let one "
        "engagement fund a large slice of the goal. Define the outcome, the "
        "timeline, and two add-ons, then pitch ten past contacts this week. "
        "Two yeses at the new rate beats ten hours at the old one.",
        "yield_min": 1000,
        "yield_max": 15000,
        "effort": ["hustle"],
        "timeframes": ["1M", "3M", "6M"],
        "premium": False,
        "next_steps": [
            "Write the fixed-scope offer with two add-ons.",
            "Pitch ten past contacts this week.",
            "Raise the rate again after the second yes.",
        ],
    },
    {
        "id": "fractional-role",
        "category": "gigs",
        "title": "Contract or Fractional Role Targeting",
        "summary": "Land one 3-6 month contract at market rate to cover the "
        "goal with a single income line.",
        "detail": "Fractional and contract roles pay full-market rates without "
        "the hiring-committee timeline. Shortlist fifteen companies showing "
        "the pain you solve, send a two-paragraph pitch with one proof point, "
        "and propose a paid two-week trial to collapse the decision cycle.",
        "yield_min": 5000,
        "yield_max": 60000,
        "effort": ["hustle"],
        "timeframes": ["1M", "3M", "6M", "1Y"],
        "premium": False,
        "next_steps": [
            "Shortlist fifteen companies with the pain you solve.",
            "Send the two-paragraph pitch with one proof point.",
            "Propose a paid two-week trial to close faster.",
        ],
    },
    {
        "id": "offer-playbook",
        "category": "gigs",
        "title": "Competing-Offer Compensation Playbook",
        "summary": "Run parallel processes and convert the best one into a "
        "negotiated uplift with scripts.",
        "detail": "Premium playbook: keep three processes live, disclose "
        "timelines without disclosing numbers, and use the written scripts to "
        "convert the lead offer into base, bonus, and equity improvements. "
        "Includes the exact ask ladder and the walk-away line so you never "
        "negotiate against yourself.",
        "yield_min": 5000,
        "yield_max": 80000,
        "effort": ["hustle"],
        "timeframes": ["1M", "3M"],
        "premium": True,
        "next_steps": [
            "Keep three live processes with staggered timelines.",
            "Run the ask ladder: base, then bonus, then equity.",
            "Set the walk-away line in writing before the final call.",
        ],
    },
    {
        "id": "retainer-ladder",
        "category": "gigs",
        "title": "Consulting Retainer Ladder",
        "summary": "Convert project clients onto monthly retainers for "
        "compounding recurring income.",
        "detail": "After any successful project, offer a three-tier retainer: "
        "advisory access, a monthly deliverable block, and embedded support. "
        "Three small retainers beat one big hunt every quarter, and recurring "
        "revenue is the only gig income that stacks toward multi-year goals.",
        "yield_min": 3000,
        "yield_max": 40000,
        "effort": ["hustle", "venture"],
        "timeframes": ["3M", "6M", "1Y"],
        "premium": False,
        "next_steps": [
            "Draft the three retainer tiers after each project win.",
            "Offer the middle tier first, anchored by the top.",
            "Review and raise retainers every two quarters.",
        ],
    },
    # -- d. Startup programs & non-dilutive funding --
    {
        "id": "accelerator-pipe",
        "category": "startup",
        "title": "Accelerator Application Pipeline",
        "summary": "Apply to a batched set of accelerators with one strong, "
        "reused application core.",
        "detail": "Most accelerator applications ask the same ten questions. "
        "Write strong answers once, record a two-minute demo, and submit to "
        "every program whose thesis fits - batching beats perfecting one. "
        "Track interview invites weekly and iterate the deck between batches.",
        "yield_min": 10000,
        "yield_max": 150000,
        "effort": ["venture"],
        "timeframes": ["3M", "6M", "1Y"],
        "premium": False,
        "next_steps": [
            "Answer the core ten questions once, reuse everywhere.",
            "Record a two-minute demo video.",
            "Submit in batches and iterate between them.",
        ],
    },
    {
        "id": "innovation-scan",
        "category": "startup",
        "title": "Government & Corporate Innovation Program Scan",
        "summary": "Map SBIR-style and corporate innovation programs against "
        "your milestones for non-dilutive shots.",
        "detail": "Government and corporate programs fund milestones, not "
        "pitches. List your next four milestones, then match each to programs "
        "whose solicitations name that outcome. Phase 1 awards are small but "
        "fast and unlock larger Phase 2 conversations.",
        "yield_min": 5000,
        "yield_max": 100000,
        "effort": ["venture"],
        "timeframes": ["6M", "1Y", "3Y"],
        "premium": False,
        "next_steps": [
            "List your next four milestones in order.",
            "Match each milestone to open solicitations.",
            "File Phase 1 first to unlock Phase 2 paths.",
        ],
    },
    {
        "id": "nondilutive-map",
        "category": "startup",
        "title": "Non-Dilutive Funding Stack Map",
        "summary": "A milestone-linked map of grants, credits, and awards "
        "that funds the venture without equity.",
        "detail": "Premium playbook: lay milestones on a timeline, attach "
        "every matching non-dilutive source with amounts and windows, and "
        "sequence filings so wins arrive just before the spend they cover. "
        "Includes R&D credit timing and the documentation standard that "
        "survives audit.",
        "yield_min": 25000,
        "yield_max": 500000,
        "effort": ["venture"],
        "timeframes": ["6M", "1Y", "3Y", "5Y"],
        "premium": True,
        "next_steps": [
            "Timeline the milestones with spend dates.",
            "Attach sources with amounts and filing windows.",
            "File ahead of spend and keep audit-grade records.",
        ],
    },
    {
        "id": "incubator-seq",
        "category": "startup",
        "title": "Incubator Seed-Pool & Demo-Day Sequencing",
        "summary": "Time incubator entry and demo days so each cohort funds "
        "the traction the next one requires.",
        "detail": "Premium playbook: enter an equity-light incubator for the "
        "seed pool and lab access, hit the demo-day metrics with that runway, "
        "then sequence a second, deeper program off proven numbers. Covers "
        "term comparisons, mentor-leverage tactics, and the demo-day narrative "
        "arc that converts rooms.",
        "yield_min": 25000,
        "yield_max": 500000,
        "effort": ["venture"],
        "timeframes": ["1Y", "3Y", "5Y"],
        "premium": True,
        "next_steps": [
            "Compare incubator terms on equity, cash, and access.",
            "Set demo-day metrics before day one.",
            "Sequence the second program off proven numbers.",
        ],
    },
]


META_MODEL_DEFAULT_BASE_URL = "https://api.meta.ai/v1"


def _llm_summary(target_amount, timeframe_label, effort_label):
    """Personalized path summary via Meta Model API, or None."""
    base_url = (
        os.getenv("META_MODEL_API_BASE")
        or os.getenv("OPENAI_BASE_URL")
        or META_MODEL_DEFAULT_BASE_URL
    )
    api_key = os.getenv("META_MODEL_API_KEY") or os.getenv("OPENAI_API_KEY")
    if not api_key:
        return None
    try:
        from openai import OpenAI
    except ImportError:
        return None
    try:
        client = OpenAI(base_url=base_url, api_key=api_key)
        resp = client.chat.completions.create(
            model=os.getenv("WEALTHPATH_MODEL", "muse-spark-1.3"),
            messages=[
                {
                    "role": "system",
                    "content": "Write a 2-3 sentence personal wealth-path "
                    "summary. No invented offers or figures; speak in "
                    "categories (bonuses, capital, gigs, programs).",
                },
                {
                    "role": "user",
                    "content": f"Goal: ${target_amount:,.0f} in "
                    f"{timeframe_label} via {effort_label}.",
                },
            ],
            temperature=0.3,
            max_tokens=180,
        )
        return resp.choices[0].message.content.strip()
    except Exception:
        return None


def _curated_summary(target_amount, timeframe_label, effort_label, n_free, n_locked):
    return (
        f"To reach ${target_amount:,.0f} in {timeframe_label} "
        f"({effort_label.lower()}), start with the {n_free} free pathways "
        f"below; {n_locked} advanced arbitrage pathways unlock with "
        "WealthPath Pro."
    )


def _public_view(strategy, unlocked):
    base = {
        "id": strategy["id"],
        "category": strategy["category"],
        "title": strategy["title"],
        "summary": strategy["summary"],
        "yield_min": strategy["yield_min"],
        "yield_max": strategy["yield_max"],
        "effort": strategy["effort"],
        "locked": strategy["premium"] and not unlocked,
    }
    if unlocked or not strategy["premium"]:
        base["detail"] = strategy["detail"]
        base["next_steps"] = strategy["next_steps"]
    return base


def generate(target_amount, timeframe, effort, is_pro=False):
    """Filter and rank the playbook for one goal."""
    if timeframe not in TIMEFRAMES:
        raise ValueError(f"Unknown timeframe: {timeframe}")
    if effort not in EFFORTS:
        raise ValueError(f"Unknown effort level: {effort}")
    matched = [
        s
        for s in STRATEGIES
        if timeframe in s["timeframes"]
        and (effort == "all" or effort in s["effort"])
    ]
    matched.sort(key=lambda s: (s["premium"], -s["yield_max"]))
    groups = []
    n_locked = 0
    for key, label in CATEGORIES:
        items = [_public_view(s, is_pro) for s in matched if s["category"] == key]
        if items:
            n_locked += sum(1 for i in items if i["locked"])
            groups.append({"key": key, "label": label, "items": items})
    n_free = sum(
        1 for g in groups for i in g["items"] if not i["locked"]
    )
    summary = _llm_summary(
        target_amount, TIMEFRAMES[timeframe], EFFORTS[effort]
    )
    source = "ai" if summary else "curated"
    if not summary:
        summary = _curated_summary(
            target_amount, TIMEFRAMES[timeframe], EFFORTS[effort],
            n_free, n_locked,
        )
    return {
        "summary": summary,
        "summary_source": source,
        "groups": groups,
        "n_free": n_free,
        "n_locked": n_locked,
        "is_pro": is_pro,
    }
