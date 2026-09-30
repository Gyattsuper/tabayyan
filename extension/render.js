// Renders a Tabayyan result as HTML. Loaded both in the popup and injected
// into pages (as a classic script), so it attaches itself to globalThis.
(function () {
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const PUNCT = /^[\s‎‏"'“”«»:.,،؛]+$/;

  function headline(r) {
    const m = r.match;
    if (r.verdict === "found" && m) {
      if (m.grade_status === "weak") return ["موجود لكنه ضعيف", "missing"];
      if (m.grade_status === "disputed") return ["موجود ومختلف في درجته", "partial"];
      if ((r.claimed === "hadith" && m.type === "quran") || (r.claimed === "quran" && m.type === "hadith"))
        return ["موجود لكن نسبته خاطئة", "partial"];
      return ["موجود في المصادر", "found"];
    }
    return r.verdict === "partial" ? ["مطابق جزئيًا", "partial"] : ["لم نجده في المصادر", "missing"];
  }

  function sourceText(words) {
    const first = words.findIndex((w) => w.status !== "context");
    let last = words.length - 1;
    while (last > 0 && words[last].status === "context") last--;
    const from = Math.max(0, first - 5), to = Math.min(words.length, last + 6);
    const parts = words.slice(from, to).filter((w) => !PUNCT.test(w.word)).map((w) =>
      `<span class="${w.status === "context" ? "ctx" : w.status === "changed" ? "fix" : ""}">${esc(w.word)}</span>`);
    return (from > 0 ? "… " : "") + parts.join(" ") + (to < words.length ? " …" : "");
  }

  function render(r) {
    const [title, tone] = headline(r);
    const m = r.match;
    let html = `<div class="t-res tone-${tone}">
      <div class="t-head"><strong>${esc(title)}</strong>${m ? `<span>${esc(m.ref)}</span>` : ""}</div>`;
    if (r.explanation) html += `<p class="t-expl">${esc(r.explanation)}</p>`;
    for (const w of r.warnings) html += `<p class="t-warn">${esc(w)}</p>`;
    if (m) {
      if (r.verdict === "partial")
        html += `<p class="t-label">ما في النص</p><p class="t-quote">${r.diff
          .map((d) => (d.status === "same" ? esc(d.word) : `<s>${esc(d.word)}</s>`)).join(" ")}</p>`;
      html += `<p class="t-label">${r.verdict === "partial" ? "النص الصحيح" : "النص في المصدر"}</p>
        <p class="t-src">${sourceText(m.words)}</p>`;
      if (m.type === "hadith" && m.grades.length > 1)
        html += `<p class="t-grades">${m.grades.map((g) => `${esc(g.scholar)}: <b>${esc(g.grade)}</b>`).join(" ، ")}</p>`;
      html += `<a class="t-link" href="${esc(m.link)}" target="_blank" rel="noreferrer">افتح المصدر</a>`;
    }
    return html + "</div>";
  }

  const CSS = `
    .t-res{font:15px/1.7 system-ui,"Segoe UI",Tahoma,sans-serif;color:#16233b;direction:rtl;text-align:right;border-inline-start:4px solid var(--tone);padding:4px 12px 8px;margin-top:10px}
    .tone-found{--tone:#16875b;--bg:#e7f6ef}.tone-partial{--tone:#a86b00;--bg:#fdf3e0}.tone-missing{--tone:#c23b3b;--bg:#fcebeb}
    .t-head{display:flex;flex-direction:column}.t-head strong{color:var(--tone);font-size:18px}.t-head span{font-size:14px}
    .t-expl{margin:8px 0}.t-warn{background:var(--bg);padding:6px 10px;border-radius:6px;margin:6px 0;font-size:14px}
    .t-label{margin:10px 0 2px;font-size:12px;color:#5d6b82}.t-quote{margin:0}.t-quote s{color:#c23b3b}
    .t-src{margin:0;font-family:"Amiri","Traditional Arabic","Noto Naskh Arabic",serif;font-size:20px;line-height:2}
    .t-src .ctx{color:#9aa6b8}.t-src .fix{background:linear-gradient(transparent 55%,rgba(48,208,200,.45) 55%);font-weight:700}
    .t-grades{font-size:13px;color:#5d6b82;margin:6px 0}.t-link{font-size:13px;color:#193565}`;

  globalThis.TabayyanRender = { render, CSS, esc };
})();
