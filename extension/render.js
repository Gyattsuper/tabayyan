// Renders a Tabayyan result as HTML. Loaded both in the popup and injected
// into pages (as a classic script), so it attaches itself to globalThis.
(function () {
  const esc = (s) =>
    String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
  const PUNCT = /^[\s‎‏"'“”«»:.,،؛]+$/;

  // Interface text. Results themselves arrive from the server in the chosen language.
  const STR = {
    ar: {
      dir: "rtl",
      found: "موجود في المصادر", partial: "مطابق جزئيًا", not_found: "لم نجده في المصادر",
      dorar: "خارج الكتب التسعة: أحكام العلماء (الدرر السنية)",
      weak: "موجود لكنه ضعيف", disputed: "موجود ومختلف في درجته", misattributed: "موجود لكن نسبته خاطئة",
      athar: "قول منسوب لغير النبي ﷺ", foundEn: "يطابق ترجمة معروفة", partialEn: "قريب من ترجمة معروفة",
      inText: "ما في النص", correct: "النص الصحيح", source: "النص في المصدر", open: "افتح المصدر",
      loading: "نبحث في القرآن الكريم وكتب الحديث…",
      reading: "نقرأ النص من الصورة ثم نتحقق منه…",
      fromImage: "النص الذي قرأناه من الصورة",
      netError: "تعذر الاتصال بخادم تبيّن. تأكد من عنوان الخادم في إعدادات الإضافة.",
      close: "إغلاق", result: "نتيجة تبيّن", name: "تبيّن",
      placeholder: "الصق آية أو حديثًا (بالعربية أو الإنجليزية)، أو حدّد نصًا في الصفحة قبل فتح الإضافة",
      check: "تحقّق", noFatwa: "لا يُصدر فتاوى.", settings: "الإعدادات",
      aiLabel: "✦ شرح كتبه الذكاء الاصطناعي من النتيجة، والنص من المصدر.",
    },
    en: {
      dir: "ltr",
      found: "Found in the sources", partial: "Partial match", not_found: "Not found in the sources",
      dorar: "Outside the nine collections: scholars' rulings (Dorar al-Saniyyah)",
      weak: "Found, but graded weak", disputed: "Found, grading disputed", misattributed: "Found, but wrongly attributed",
      athar: "Attributed to someone other than the Prophet ﷺ", foundEn: "Matches a known translation",
      partialEn: "Close to a known translation",
      inText: "In the text", correct: "Correct text", source: "Text in the source", open: "Open the source",
      loading: "Searching the Quran and the hadith collections…",
      reading: "Reading the text in the image, then checking it…",
      fromImage: "Text read from the image",
      netError: "Could not reach the Tabayyan server. Check the server address in the extension settings.",
      close: "Close", result: "Tabayyan result", name: "Tabayyan",
      placeholder: "Paste a verse or hadith (Arabic or English), or select text on the page before opening",
      check: "Check", noFatwa: "Does not issue religious rulings.", settings: "Settings",
      aiLabel: "✦ Explanation written by AI from the result; the text is quoted from the source.",
    },
  };
  const str = (lang) => STR[lang === "en" ? "en" : "ar"];

  function headline(r, t) {
    const m = r.match;
    if (r.verdict === "found" && m) {
      if (m.grade_status === "weak") return [t.weak, "missing"];
      if (m.grade_status === "disputed") return [t.disputed, "partial"];
      if ((r.claimed === "hadith" && m.type === "quran") || (r.claimed === "quran" && m.type === "hadith")
          || (r.claimed === "athar" && m.type === "quran"))
        return [t.misattributed, "partial"];
      return [m.translator ? t.foundEn : t.found, "found"];
    }
    if (r.verdict === "partial") return [m && m.translator ? t.partialEn : t.partial, "partial"];
    if (r.claimed === "athar") return [t.athar, "scope"];
    return [t.not_found, "missing"];
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
    const t = str(r.lang);
    const [title, tone] = headline(r, t);
    const m = r.match;
    const en = m && m.words_lang === "en";
    let html = `<div class="t-res tone-${tone}" dir="${t.dir}">
      <div class="t-head"><strong>${esc(title)}</strong>${m ? `<span>${esc(m.ref)}${m.translator ? ` · ${esc(m.translator)}` : ""}</span>` : ""}</div>`;
    if (r.explanation) html += `<p class="t-expl">${esc(r.explanation)}</p>`;
    if (r.explanation && r.explanation_source === "claude") html += `<p class="t-ai">${esc(t.aiLabel)}</p>`;
    for (const w of r.warnings) html += `<p class="t-warn">${esc(w)}</p>`;
    if (m) {
      const d = en ? "ltr" : "rtl";
      if (r.verdict === "partial")
        html += `<p class="t-label">${t.inText}</p><p class="t-quote" dir="${d}">${r.diff
          .map((x) => (x.status === "same" ? esc(x.word) : `<s>${esc(x.word)}</s>`)).join(" ")}</p>`;
      html += `<p class="t-label">${r.verdict === "partial" ? t.correct : t.source}</p>
        <p class="t-src${en ? " en" : ""}" dir="${d}">${sourceText(m.words)}</p>`;
      if (m.type === "hadith" && m.grades.length > 1)
        html += `<p class="t-grades">${m.grades.map((g) => `${esc(g.scholar)}: <b>${esc(g.grade)}</b>`).join(" , ")}</p>`;
      html += `<a class="t-link" href="${esc(m.link)}" target="_blank" rel="noreferrer">${t.open}</a>`;
    }
    if (r.dorar && r.dorar.items && r.dorar.items.length) {
      html += `<p class="t-label">${t.dorar}</p>` + r.dorar.items.map((it) =>
        `<p class="t-grades" dir="rtl"><b class="${it.status === "strong" ? "g-ok" : it.status === "weak" ? "g-bad" : ""}">${esc(it.grading)}</b> · ${esc(it.scholar)}${it.source ? ` · ${esc(it.source)}` : ""}</p>`).join("")
        + `<a class="t-link" href="${esc(r.dorar.link)}" target="_blank" rel="noreferrer">dorar.net</a>`;
    }
    return html + "</div>";
  }

  const CSS = `
    .t-res{font:15px/1.7 system-ui,"Segoe UI",Tahoma,sans-serif;color:#16233b;text-align:start;border-inline-start:4px solid var(--tone);padding:4px 12px 8px;margin-top:10px}
    .tone-found{--tone:#16875b;--bg:#e7f6ef}.tone-partial{--tone:#a86b00;--bg:#fdf3e0}.tone-missing{--tone:#c23b3b;--bg:#fcebeb}.tone-scope{--tone:#193565;--bg:#e8eef8}
    .t-head{display:flex;flex-direction:column}.t-head strong{color:var(--tone);font-size:18px}.t-head span{font-size:14px}
    .t-expl{margin:8px 0}.t-warn{background:var(--bg);padding:6px 10px;border-radius:6px;margin:6px 0;font-size:14px}
    .t-label{margin:10px 0 2px;font-size:12px;color:#5d6b82}.t-quote{margin:0}.t-quote s{color:#c23b3b}
    .t-src{margin:0;font-family:"Amiri","Traditional Arabic","Noto Naskh Arabic",serif;font-size:20px;line-height:2}
    .t-src.en{font-family:Georgia,serif;font-size:16px;line-height:1.7}
    .t-src .ctx{color:#9aa6b8}.t-src .fix{background:linear-gradient(transparent 55%,rgba(48,208,200,.45) 55%);font-weight:700}
    .t-grades{font-size:13px;color:#5d6b82;margin:6px 0}.g-ok{color:#16875b}.g-bad{color:#c23b3b}.t-link{font-size:13px;color:#193565}
    .t-ai{font-size:11.5px;color:#5d6b82;margin:4px 0 6px}`;

  function renderAll(data) {
    const t = str(data.lang);
    const head = data.transcript
      ? `<p class="t-label" dir="${t.dir}">${t.fromImage}</p><p class="t-quote" dir="auto">${esc(data.transcript)}</p>` : "";
    const note = data.note ? `<p class="t-warn" dir="${t.dir}" style="--bg:#eef3fb">${esc(data.note)}</p>` : "";
    if (!data.results.length) {
      const bg = data.request ? "#eef3fb" : "#fcebeb";
      return head + `<p class="t-warn" dir="${t.dir}" style="--bg:${bg}">${esc(data.message || "")}</p>`;
    }
    return head + note + data.results.map(render).join("");
  }

  globalThis.TabayyanRender = { render, renderAll, CSS, esc, str };
})();
