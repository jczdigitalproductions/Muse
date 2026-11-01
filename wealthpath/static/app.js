(() => {
  const dash = document.querySelector(".dash");
  const isPro = () => dash.dataset.isPro === "1";
  const amountEl = document.getElementById("amount");
  const resultsEl = document.getElementById("results");
  const generateBtn = document.getElementById("generate");
  const formError = document.getElementById("form-error");
  const modal = document.getElementById("upgrade-modal");
  const checkoutError = document.getElementById("checkout-error");

  const pick = (containerId) => {
    const box = document.getElementById(containerId);
    box.addEventListener("click", (e) => {
      const btn = e.target.closest("button");
      if (!btn) return;
      box.querySelectorAll("button").forEach((b) => b.classList.remove("active"));
      btn.classList.add("active");
    });
    return () => box.querySelector("button.active").dataset.value;
  };
  const getTimeframe = pick("timeframes");
  const getEffort = pick("efforts");

  document.querySelectorAll(".chips button").forEach((b) =>
    b.addEventListener("click", () => { amountEl.value = b.dataset.amount; })
  );

  const money = (n) => "$" + Number(n).toLocaleString("en-US");
  const esc = (s) => String(s).replace(/[&<>"']/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));

  function skeletons() {
    resultsEl.innerHTML = '<div class="summary"><p>Generating your wealth pathways&hellip;</p></div>'
      + Array.from({ length: 4 }, () =>
        '<div class="skel" aria-hidden="true"><div class="bar" style="width:55%"></div><div class="bar" style="width:92%"></div><div class="bar" style="width:78%"></div></div>'
      ).join("");
  }

  function strategyCard(item) {
    const tag = item.locked
      ? '<span class="tag pro">PRO</span>'
      : '<span class="tag free">FREE</span>';
    let inner = `<div class="strategy-head"><h3>${tag}${esc(item.title)}</h3>`
      + `<span class="yield">${money(item.yield_min)} &ndash; ${money(item.yield_max)}</span></div>`
      + `<p>${esc(item.summary)}</p>`;
    if (!item.locked) {
      inner += `<p>${esc(item.detail)}</p><ol class="steps">`
        + item.next_steps.map((s) => `<li>${esc(s)}</li>`).join("") + "</ol>";
    } else {
      inner = `<div class="lock-body">${inner}</div>`
        + `<div class="unlock"><p>Premium arbitrage playbook &mdash; unlock with WealthPath Pro.</p>`
        + `<button class="btn primary" data-upgrade type="button">Unlock Pro</button></div>`;
    }
    return `<article class="strategy${item.locked ? " locked" : ""}">${inner}</article>`;
  }

  function render(data) {
    const src = data.summary_source === "ai" ? "Personalized by AI" : "Curated playbook";
    let html = `<div class="summary"><p>${esc(data.summary)}</p>`
      + `<small>${esc(src)} &middot; ${data.n_free} free &middot; ${data.n_locked} locked &middot; illustrative ranges, verify current terms</small></div>`;
    for (const group of data.groups) {
      html += `<section class="group"><h2>${esc(group.label)} <span class="count">${group.items.length} pathways</span></h2>`
        + group.items.map(strategyCard).join("") + "</section>";
    }
    if (!data.groups.length) {
      html += '<div class="empty"><h2>No pathways match that mix.</h2><p>Try a longer timeframe or a broader effort level.</p></div>';
    }
    resultsEl.innerHTML = html;
  }

  generateBtn.addEventListener("click", async () => {
    formError.hidden = true;
    const amount = Number(amountEl.value);
    if (!Number.isFinite(amount) || amount < 100 || amount > 100000000) {
      formError.textContent = "Enter a target between $100 and $100,000,000.";
      formError.hidden = false;
      return;
    }
    generateBtn.disabled = true;
    skeletons();
    try {
      const res = await fetch("/api/generate", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ target_amount: amount, timeframe: getTimeframe(), effort: getEffort() }),
      });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Generation failed.");
      dash.dataset.isPro = data.is_pro ? "1" : "0";
      render(data);
    } catch (err) {
      resultsEl.innerHTML = `<div class="empty"><h2>Something went wrong.</h2><p>${esc(err.message)}</p></div>`;
    } finally {
      generateBtn.disabled = false;
    }
  });

  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-upgrade]")) {
      if (isPro()) return;
      checkoutError.hidden = true;
      modal.hidden = false;
    }
    if (e.target.closest("#close-modal") || e.target === modal) modal.hidden = true;
  });

  document.getElementById("checkout").addEventListener("click", async (e) => {
    const btn = e.currentTarget;
    checkoutError.hidden = true;
    btn.disabled = true;
    try {
      const res = await fetch("/api/checkout", { method: "POST" });
      const data = await res.json();
      if (!res.ok) throw new Error(data.error || "Checkout failed.");
      window.location.href = data.url;
    } catch (err) {
      checkoutError.textContent = err.message;
      checkoutError.hidden = false;
    } finally {
      btn.disabled = false;
    }
  });
})();
