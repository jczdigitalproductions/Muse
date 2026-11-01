(() => {
  const analyzeBtn = document.getElementById("analyze");
  if (!analyzeBtn) return;
  const resultsEl = document.getElementById("notes-results");
  const errEl = document.getElementById("notes-error");
  const textEl = document.getElementById("termsheet");
  const sampleEl = document.getElementById("use-sample");
  const pathsEl = document.getElementById("n-paths");

  const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const pct = (n, d = 2) => (Number(n) * 100).toFixed(d) + "%";
  const money = (n) => "$" + Number(n).toLocaleString("en-US", { maximumFractionDigits: 2 });

  function skeletons() {
    resultsEl.innerHTML = '<div class="summary"><p>Pricing note &mdash; extraction, Monte Carlo, stress regimes&hellip;</p></div>'
      + Array.from({ length: 3 }, () =>
        '<div class="skel" aria-hidden="true"><div class="bar" style="width:55%"></div><div class="bar" style="width:92%"></div></div>'
      ).join("");
  }

  function termsTable(terms) {
    const rows = [
      ["Issuer", terms.issuer],
      ["Product", terms.product_type],
      ["Underlyings", terms.underlyings.join(", ")],
      ["Notional", money(terms.notional)],
      ["Maturity", terms.maturity_years + " years"],
      ["Coupon", pct(terms.coupon_rate) + " p.a." + (terms.memory_coupon ? " (memory)" : "")],
      ["Coupon barrier", pct(terms.coupon_barrier)],
      ["Autocall barrier", pct(terms.autocall_barrier)],
      ["Knock-in barrier", pct(terms.knock_in_barrier)],
    ];
    return '<table class="grid"><tbody>' + rows.map(([k, v]) =>
      `<tr><th>${esc(k)}</th><td>${esc(v)}</td></tr>`).join("") + "</tbody></table>";
  }

  function render(data) {
    const m = data.metrics;
    const method = data.extraction === "meta" ? "Muse Spark" : "pattern fallback";
    let html = `<div class="summary"><p>Fair value <strong>${money(m.price)}</strong> `
      + `(${Number(m.fair_value_pct).toFixed(2)}% of notional), extracted via ${esc(method)}.</p>`
      + `<small>Autocall ${pct(m.p_autocall, 1)} &middot; knock-in loss ${pct(m.p_knock_in_loss, 1)} `
      + `&middot; std err ${money(m.stderr)}</small></div>`;

    html += `<section class="group"><h2>Extracted terms</h2><div class="strategy">${termsTable(data.terms)}</div></section>`;

    html += `<section class="group"><h2>Stress regimes <span class="count">fair value % of notional</span></h2>`
      + `<div class="strategy"><table class="grid wide"><thead><tr><th>Regime</th><th>Fair value</th>`
      + `<th>Autocall</th><th>Knock-in</th></tr></thead><tbody>`
      + data.stress.map((r) => `<tr><td>${esc(r.regime)}</td><td>${Number(r.fair_value_pct).toFixed(2)}%</td>`
        + `<td>${pct(r.p_autocall, 1)}</td><td>${pct(r.p_knock_in_loss, 1)}</td></tr>`).join("")
      + "</tbody></table></div></section>";

    const checks = Object.entries(data.verification.checks).map(([k, v]) =>
      `<li class="${v ? "ok" : "bad"}">${v ? "PASS" : "FAIL"} &mdash; ${esc(k)}</li>`).join("");
    html += `<section class="group"><h2>Verification <span class="count">${data.verification.passed ? "all checks passed" : "failures present"}</span></h2>`
      + `<div class="strategy"><ul class="checks">${checks}</ul></div></section>`;

    html += `<section class="group"><h2>Payoff diagram</h2>`
      + `<div class="strategy"><img class="chart" alt="Payoff diagram" src="data:image/png;base64,${data.charts.payoff}"></div></section>`;
    html += `<section class="group"><h2>Risk heatmap</h2>`
      + `<div class="strategy"><img class="chart" alt="Risk heatmap" src="data:image/png;base64,${data.charts.heatmap}"></div></section>`;
    resultsEl.innerHTML = html;
  }

  analyzeBtn.addEventListener("click", async () => {
    errEl.hidden = true;
    const useSample = sampleEl.checked;
    const text = textEl.value;
    if (!useSample && text.trim().length < 20) {
      errEl.textContent = "Paste a termsheet of at least 20 characters or use the sample.";
      errEl.hidden = false;
      return;
    }
    analyzeBtn.disabled = true;
    skeletons();
    try {
      const res = await fetch("/api/notes/analyze", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text, use_sample: useSample, n_paths: Number(pathsEl.value) }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Analysis failed.");
      render(data);
    } catch (err) {
      resultsEl.innerHTML = `<div class="empty"><h2>Something went wrong.</h2><p>${esc(err.message)}</p></div>`;
    } finally {
      analyzeBtn.disabled = false;
    }
  });
})();
