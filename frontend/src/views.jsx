import { useEffect, useState } from "react";
import MYTHS from "./myths.json";

const API = import.meta.env.VITE_API_URL || "";
const REPO = "https://github.com/Gyattsuper/tabayyan";

// ---------- navigation ----------

export const NAV = [
  { id: "check", icon: "check" },
  { id: "search", icon: "search" },
  { id: "myths", icon: "myths" },
  { id: "learn", icon: "learn" },
  { id: "history", icon: "history" },
  { id: "tools", icon: "tools" },
  { id: "about", icon: "about" },
];

export const V = {
  ar: {
    nav: {
      check: "التحقق", search: "ابحث في المصادر", myths: "أقوال لا تصح", learn: "تعلّم",
      history: "سجلّك", tools: "الإضافة والتطبيق", about: "عن تبيّن",
    },
    tab: { check: "تحقّق", search: "ابحث", myths: "لا تصح", learn: "تعلّم" },
    menu: "القائمة",
    close: "إغلاق",
    noFatwa: "لا يُصدر فتاوى. ارجع إلى أهل العلم فيما يتجاوز التحقق من النص.",
    // search
    searchTitle: "ابحث في المصادر",
    searchIntro: "اكتب موضوعًا، فتظهر لك آيات وأحاديث صحيحة عنه من المصادر الموثقة. مفيد لمن يريد أن ينشر نصًا صحيحًا بدل نص لا أصل له.",
    searchPh: "مثال: بر الوالدين، الصبر، حق الجار",
    searchBtn: "ابحث",
    all: "الكل", quran: "القرآن", hadith: "الحديث",
    searching: "نبحث في المصادر…",
    noResults: "لم نجد نتائج. جرّب كلمات أخرى أو موضوعًا أعم.",
    byMeaning: "بحثنا بالمعنى: الذكاء الاصطناعي حوّل الموضوع إلى عبارات بحث فقط، والنصوص كلها من المصادر. الأحاديث المعروضة صحيحة أو حسنة.",
    byWords: "بحثنا بالكلمات. الأحاديث المعروضة صحيحة أو حسنة.",
    checkThis: "تحقّق منه",
    showEnglish: "الترجمة الإنجليزية",
    topics: ["بر الوالدين", "الصبر", "حق الجار", "الصدق", "الرحمة", "طلب العلم"],
    // myths
    mythsTitle: "أقوال منتشرة لا تصح نسبتها",
    mythsIntro: "أقوال تنتشر على أنها أحاديث نبوية، ولم نجدها في كتب الحديث التسعة. اضغط على أي قول لترى النتيجة بنفسك، ومعها نص صحيح بديل إن وُجد.",
    // history
    historyTitle: "سجلّك",
    historyIntro: "آخر ما تحققت منه على هذا الجهاز. لا يُرسل إلى أي مكان.",
    historyEmpty: "لم تتحقق من شيء بعد. ما تتحقق منه سيظهر هنا.",
    clear: "امسح السجل",
    again: "تحقّق مرة أخرى",
    // learn
    learnTitle: "تعلّم",
    learnIntro: "حديث كل يوم من الأربعين النووية، ودروس قصيرة تساعدك على التمييز قبل النشر.",
    // tools
    toolsTitle: "الإضافة والتطبيق",
    toolsIntro: "تحقّق حيث تقرأ: من صفحات الإنترنت، ومن واتساب مباشرة.",
    extTitle: "إضافة كروم",
    extBody: "حدّد أي نص في صفحة، أو انقر بالزر الأيمن على صورة، واختر «تحقّق مع تبيّن». تظهر النتيجة فوق الصفحة نفسها. الإضافة نسخة تجريبية لم تُنشر في متجر كروم بعد.",
    extSteps: [
      "نزّل ملف المشروع وفك ضغطه.",
      "افتح chrome://extensions وفعّل وضع المطوّر.",
      "اضغط «تحميل إضافة غير مضغوطة» واختر مجلد extension.",
    ],
    download: "نزّل ملف المشروع",
    appTitle: "تطبيق على هاتفك",
    appBody: "ثبّت تبيّن على الشاشة الرئيسية. على أندرويد يظهر تبيّن بعدها في قائمة المشاركة في واتساب: اضغط مطولًا على الرسالة، ثم مشاركة، ثم تبيّن.",
    install: "ثبّت التطبيق",
    installed: "التطبيق مثبّت",
    iosNote: "على آيفون: افتح الموقع في سفاري، ثم زر المشاركة، ثم «إضافة إلى الشاشة الرئيسية».",
    // about
    aboutTitle: "عن تبيّن",
    aboutLead: "تبيّن يتحقق من الآيات والأحاديث المتداولة قبل نشرها، بالرجوع إلى نصوص المصادر نفسها.",
    aboutHow: [
      ["يستخرج النص", "من الرسالة أو الصورة، مع التمييز بين ما نُسب إلى القرآن أو السنة أو غيرهما."],
      ["يبحث ويطابق", "في القرآن الكريم وتسعة من كتب الحديث، ويقارن الكلمات واحدة واحدة."],
      ["يعرض الحكم", "موجود، أو مطابق جزئيًا مع النص الصحيح، أو غير موجود، مع المرجع والدرجة."],
    ],
    aboutAi: "الذكاء الاصطناعي (Claude) يستخرج النص ويشرح النتيجة ويقترح البديل ويكتب الرد، لكنه لا يُصدر الحكم أبدًا. كل نص يظهر لك منقول من المصادر.",
    numbersTitle: "نتائج الاختبار",
    numbers: [
      ["99.4%", "من النصوص الصحيحة المكتوبة بإملاء دارج وجدها تبيّن، مقابل 6.7% للبحث النصي العادي"],
      ["98.1%", "من النصوص المحرّفة كشفها وعرض نصها الصحيح"],
      ["49 من 49", "قولًا منتشرًا لا أصل له عدّها غير موجودة"],
    ],
    numbersNote: "على نحو 60 ألف نص من 100 عينة عشوائية. التفاصيل وكل الأخطاء في ملف TESTING.md.",
    sourcesTitle: "المصادر",
    sources: "القرآن الكريم (مشروع تنزيل) وأربع ترجمات لمعانيه، وصحيح البخاري ومسلم والسنن الأربع وموطأ مالك والأربعون النووية والأحاديث القدسية، بدرجات العلماء كما وردت في بيانات Sunnah.com.",
    limitsTitle: "حدود الأداة",
    limits: "«لم نجده» يعني أنه ليس في هذه الكتب، ولا يعني بالضرورة أنه مكذوب. ودرجات الأحاديث معروضة كما حكم بها العلماء، دون ترجيح منا.",
    aiTool: "تبيّن أداة آلية مدعومة بالذكاء الاصطناعي، وليس عالمًا ولا مفتيًا. لا يجيب عن الأسئلة الشخصية في الأحكام، ولا يؤلّف أدلة: إن لم يجد نصًا في المصادر قال ذلك.",
    privacyTitle: "الخصوصية",
    privacy: [
      "لا حسابات ولا تسجيل دخول، ولا نطلب اسمك أو بريدك.",
      "النص أو الصورة التي ترسلها يُعالج على خادم تبيّن ويُرسل إلى Claude من Anthropic لاستخراج النص وكتابة الشرح، ولا نحفظه في أي قاعدة بيانات.",
      "سجل تحققاتك ولغتك محفوظان في جهازك فقط (في المتصفح)، وتستطيع مسح السجل من صفحة «السجل».",
      "نصوص الأحاديث غير الموجودة في الكتب التسعة تُرسل إلى الدرر السنية لجلب أحكام العلماء عليها.",
      "لا نستخدم ما ترسله لاستنتاج شيء عنك، ولا نعرض إعلانات.",
    ],
    code: "الكود والتوثيق على GitHub",
  },
  en: {
    nav: {
      check: "Check", search: "Search the sources", myths: "Popular unsourced sayings", learn: "Learn",
      history: "Your history", tools: "Extension & app", about: "About",
    },
    tab: { check: "Check", search: "Search", myths: "Myths", learn: "Learn" },
    menu: "Menu",
    close: "Close",
    noFatwa: "Does not issue religious rulings. Ask scholars about anything beyond checking the text.",
    searchTitle: "Search the sources",
    searchIntro: "Type a topic to see authentic verses and hadiths about it from the authenticated sources. Useful when you want to share an authentic text instead of an unsourced one.",
    searchPh: "For example: parents, patience, neighbors",
    searchBtn: "Search",
    all: "All", quran: "Quran", hadith: "Hadith",
    searching: "Searching the sources…",
    noResults: "No results. Try other words or a broader topic.",
    byMeaning: "Searched by meaning: AI only turned your topic into search phrases; every text is from the sources. Hadiths shown are graded sahih or hasan.",
    byWords: "Searched by words. Hadiths shown are graded sahih or hasan.",
    checkThis: "Check it",
    showEnglish: "English translation",
    topics: ["Parents", "Patience", "Neighbors", "Honesty", "Mercy", "Seeking knowledge"],
    mythsTitle: "Popular sayings that are not authentic",
    mythsIntro: "Sayings that spread as hadiths but that we did not find in the nine hadith collections. Tap any of them to see the result yourself, with an authentic alternative when there is one.",
    historyTitle: "Your history",
    historyIntro: "What you checked recently on this device. It is not sent anywhere.",
    historyEmpty: "Nothing checked yet. What you check will appear here.",
    clear: "Clear history",
    again: "Check again",
    learnTitle: "Learn",
    learnIntro: "A hadith a day from an-Nawawi's Forty, and short lessons that help you tell before you share.",
    toolsTitle: "Extension & app",
    toolsIntro: "Check where you read: on web pages, and straight from WhatsApp.",
    extTitle: "Chrome extension",
    extBody: "Select any text on a page, or right-click an image, and choose \"Check with Tabayyan\". The result appears on the page itself. The extension is a beta, not on the Chrome Web Store yet.",
    extSteps: [
      "Download the project and unzip it.",
      "Open chrome://extensions and turn on Developer mode.",
      "Click \"Load unpacked\" and choose the extension folder.",
    ],
    download: "Download the project",
    appTitle: "An app on your phone",
    appBody: "Install Tabayyan on your home screen. On Android it then appears in WhatsApp's share menu: long-press a message, tap Share, then Tabayyan.",
    install: "Install the app",
    installed: "App installed",
    iosNote: "On iPhone: open the site in Safari, tap Share, then \"Add to Home Screen\".",
    aboutTitle: "About Tabayyan",
    aboutLead: "Tabayyan checks verses and hadiths that are shared around before you pass them on, against the source texts themselves.",
    aboutHow: [
      ["Finds the quote", "in the message or image, and notes whether it is presented as Quran, hadith or something else."],
      ["Searches and compares", "the Quran and nine hadith collections, word by word."],
      ["Gives the verdict", "found, partial match with the correct text, or not found, with the reference and grading."],
    ],
    aboutAi: "AI (Claude) finds the quote, explains the result, suggests alternatives and drafts replies, but it never decides the verdict. Every text you see is quoted from the sources.",
    numbersTitle: "Test results",
    numbers: [
      ["99.4%", "of real quotes typed with everyday spelling found, versus 6.7% for plain text search"],
      ["98.1%", "of altered quotes caught, with the correct text shown"],
      ["49 of 49", "popular unsourced sayings reported as not found"],
    ],
    numbersNote: "On about 60,000 quotes from 100 random samples. Details and every miss in TESTING.md.",
    sourcesTitle: "Sources",
    sources: "The Quran (Tanzil) and four English translations of its meaning; Sahih al-Bukhari, Sahih Muslim, the four Sunan, Muwatta Malik, Nawawi's Forty and the Forty Qudsi, with scholars' gradings as given in the Sunnah.com data.",
    limitsTitle: "Limits",
    limits: "\"Not found\" means not in these books; it does not by itself mean fabricated. Gradings are shown as the scholars gave them, without our own judgment.",
    aiTool: "Tabayyan is an automated, AI-assisted tool, not a scholar or a mufti. It does not answer personal questions about rulings and does not compose evidence: when it finds no text in the sources, it says so.",
    privacyTitle: "Privacy",
    privacy: [
      "No accounts or sign-in, and we never ask for your name or email.",
      "The text or image you send is processed on Tabayyan's server and sent to Claude by Anthropic to find the quote and write the explanation. We do not store it in any database.",
      "Your check history and language are stored only on your device (in the browser), and you can clear the history from the History page.",
      "Hadith texts not found in the nine collections are sent to Dorar al-Saniyyah to fetch scholars' rulings on them.",
      "We do not use what you send to infer anything about you, and there are no ads.",
    ],
    code: "Code and documentation on GitHub",
  },
};

export function Icon({ name }) {
  const paths = {
    check: "M12 2 4 5v6c0 5 3.4 9.4 8 11 4.6-1.6 8-6 8-11V5l-8-3Zm-1.2 13.6-3.4-3.4 1.4-1.4 2 2 4.6-4.6 1.4 1.4-6 6Z",
    search: "M10 3a7 7 0 1 0 4.2 12.6l5.1 5.1 1.4-1.4-5.1-5.1A7 7 0 0 0 10 3Zm0 2a5 5 0 1 1 0 10 5 5 0 0 1 0-10Z",
    myths: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20ZM4 12a8 8 0 0 1 12.9-6.3L5.7 16.9A7.96 7.96 0 0 1 4 12Zm8 8a7.96 7.96 0 0 1-4.9-1.7L18.3 7.1A8 8 0 0 1 12 20Z",
    learn: "M4 4.5C4 3.7 4.7 3 5.5 3H11v16H5.5c-.8 0-1.5.7-1.5 1.5v-16Zm16 0c0-.8-.7-1.5-1.5-1.5H13v16h5.5c.8 0 1.5.7 1.5 1.5v-16Z",
    history: "M13 3a9 9 0 0 0-9 9H1l3.9 3.9L9 12H6a7 7 0 1 1 2.05 4.95l-1.42 1.42A9 9 0 1 0 13 3Zm-1 5v5l4.3 2.5.7-1.2-3.5-2.1V8H12Z",
    tools: "M7 2h10a2 2 0 0 1 2 2v16a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V4a2 2 0 0 1 2-2Zm0 3v14h10V5H7Zm4 15h2v-1h-2v1Z",
    about: "M12 2a10 10 0 1 0 0 20 10 10 0 0 0 0-20Zm1 15h-2v-6h2v6Zm0-8h-2V7h2v2Z",
    menu: "M3 6h18v2H3V6Zm0 5h18v2H3v-2Zm0 5h18v2H3v-2Z",
  };
  return (
    <svg width="20" height="20" viewBox="0 0 24 24" aria-hidden="true" className="ico">
      <path fill="currentColor" d={paths[name]} />
    </svg>
  );
}

function ViewHead({ title, intro }) {
  return (
    <header className="view-head">
      <h1>{title}</h1>
      {intro && <p>{intro}</p>}
    </header>
  );
}

// ---------- search the sources ----------

export function SearchView({ lang, onCheck, seed = "" }) {
  const v = V[lang];
  const [q, setQ] = useState(seed);
  const [kind, setKind] = useState("");
  const [st, setSt] = useState({ status: "idle" });

  async function run(query = q, k = kind) {
    if (!query.trim()) return;
    setSt({ status: "loading" });
    try {
      const params = new URLSearchParams({ q: query, lang, kind: k });
      const d = await (await fetch(`${API}/api/search?${params}`)).json();
      setSt({ status: "done", data: d });
    } catch {
      setSt({ status: "error" });
    }
  }

  // Opened from a "give me a hadith that proves..." request: search its topic right away.
  useEffect(() => {
    if (seed) run(seed, kind);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [seed]);

  return (
    <section className="view">
      <ViewHead title={v.searchTitle} intro={v.searchIntro} />
      <form className="search-bar" onSubmit={(e) => { e.preventDefault(); run(); }}>
        <input value={q} onChange={(e) => setQ(e.target.value)} placeholder={v.searchPh} dir="auto" aria-label={v.searchTitle} />
        <button type="submit">{v.searchBtn}</button>
      </form>
      <div className="search-opts">
        <div className="seg" role="radiogroup">
          {[["", v.all], ["quran", v.quran], ["hadith", v.hadith]].map(([k, label]) => (
            <button key={k} type="button" role="radio" aria-checked={kind === k}
              className={kind === k ? "on" : ""} onClick={() => { setKind(k); if (st.status === "done") run(q, k); }}>
              {label}
            </button>
          ))}
        </div>
        <div className="topics">
          {v.topics.map((tp) => (
            <button key={tp} type="button" className="chip" onClick={() => { setQ(tp); run(tp); }}>{tp}</button>
          ))}
        </div>
      </div>

      {st.status === "loading" && <p className="muted">{v.searching}</p>}
      {st.status === "error" && <p className="error">{v.noResults}</p>}
      {st.status === "done" && (
        <>
          {st.data.items.length === 0 ? <p className="muted">{v.noResults}</p> : (
            <p className="muted small">{st.data.mode === "meaning" ? v.byMeaning : v.byWords}</p>
          )}
          <ol className="hits">
            {st.data.items.map((it, i) => (
              <li key={i} className="hit">
                <p className={`hit-text${it.type === "quran" ? " q" : ""}`} dir="rtl" lang="ar">
                  {it.type === "quran" ? `﴿${it.text}﴾` : it.text}
                </p>
                {lang === "en" && it.english && <p className="hit-en" dir="ltr" lang="en">{it.english}</p>}
                <div className="hit-meta">
                  <a href={it.link} target="_blank" rel="noreferrer">{it.ref}</a>
                  {it.grade_summary && <span className={`grade-pill g-${it.grade_status}`}>{it.grade_summary}</span>}
                </div>
                {lang === "ar" && it.english && (
                  <details className="english"><summary>{v.showEnglish}</summary><p dir="ltr" lang="en">{it.english}</p></details>
                )}
              </li>
            ))}
          </ol>
        </>
      )}
    </section>
  );
}

// ---------- popular unsourced sayings ----------

export function MythsView({ lang, onCheck }) {
  const v = V[lang];
  const list = MYTHS[lang] || MYTHS.ar;
  return (
    <section className="view">
      <ViewHead title={v.mythsTitle} intro={v.mythsIntro} />
      <ul className="myths">
        {list.map((m) => (
          <li key={m}>
            <button type="button" className="myth" onClick={() => onCheck(lang === "ar" ? `قال رسول الله ﷺ: «${m}»` : `The Prophet ﷺ said: "${m}"`)}>
              <span className="myth-text" dir="auto">{m}</span>
              <span className="myth-go">{v.checkThis}</span>
            </button>
          </li>
        ))}
      </ul>
    </section>
  );
}

// ---------- history (this device only) ----------

const HKEY = "tabayyan-history";

export function loadHistory() {
  try {
    return JSON.parse(window.localStorage.getItem(HKEY) || "[]");
  } catch {
    return [];
  }
}

export function addHistory(text, data) {
  try {
    const r = data.results?.[0];
    const item = { text: text.slice(0, 600), verdict: r?.verdict || "none", ref: r?.match?.ref || "", at: Date.now() };
    const list = [item, ...loadHistory().filter((h) => h.text !== item.text)].slice(0, 30);
    window.localStorage.setItem(HKEY, JSON.stringify(list));
  } catch {
    /* storage unavailable: no history */
  }
}

export function HistoryView({ lang, t, onCheck }) {
  const v = V[lang];
  const [list, setList] = useState(loadHistory);
  const fmt = new Intl.DateTimeFormat(lang === "ar" ? "ar-SA" : "en-GB", { dateStyle: "medium", timeStyle: "short" });
  return (
    <section className="view">
      <ViewHead title={v.historyTitle} intro={v.historyIntro} />
      {list.length === 0 ? <p className="empty">{v.historyEmpty}</p> : (
        <>
          <ul className="hist">
            {list.map((h) => (
              <li key={h.at}>
                <button type="button" className="hist-item" onClick={() => onCheck(h.text)} title={v.again}>
                  <span className={`dot d-${h.verdict}`} aria-hidden="true" />
                  <span className="hist-body">
                    <span className="hist-text" dir="auto">{h.text}</span>
                    <span className="hist-meta">
                      {(t.verdict[h.verdict] || "")}{h.ref ? ` · ${h.ref}` : ""} · {fmt.format(h.at)}
                    </span>
                  </span>
                </button>
              </li>
            ))}
          </ul>
          <button type="button" className="act ghost" onClick={() => {
            try { window.localStorage.removeItem(HKEY); } catch { /* ignore */ }
            setList([]);
          }}>{v.clear}</button>
        </>
      )}
    </section>
  );
}

// ---------- extension and app ----------

export function ToolsView({ lang }) {
  const v = V[lang];
  const [prompt, setPrompt] = useState(window.__installPrompt || null);
  const [done, setDone] = useState(false);
  useEffect(() => {
    const on = (e) => { e.preventDefault(); window.__installPrompt = e; setPrompt(e); };
    window.addEventListener("beforeinstallprompt", on);
    return () => window.removeEventListener("beforeinstallprompt", on);
  }, []);
  const standalone = typeof window !== "undefined" && window.matchMedia?.("(display-mode: standalone)").matches;
  return (
    <section className="view">
      <ViewHead title={v.toolsTitle} intro={v.toolsIntro} />
      <div className="tool">
        <h2>{v.appTitle}</h2>
        <p>{v.appBody}</p>
        {standalone || done ? <p className="ok">{v.installed}</p> : prompt && (
          <button type="button" className="act" onClick={async () => {
            prompt.prompt();
            const r = await prompt.userChoice.catch(() => null);
            if (r?.outcome === "accepted") setDone(true);
          }}>{v.install}</button>
        )}
        <p className="muted small">{v.iosNote}</p>
      </div>
      <div className="tool">
        <h2>{v.extTitle}</h2>
        <p>{v.extBody}</p>
        <ol className="steps">{v.extSteps.map((s) => <li key={s}>{s}</li>)}</ol>
        <a className="act link" href={`${REPO}/archive/refs/heads/main.zip`}>{v.download}</a>
      </div>
    </section>
  );
}

// ---------- about ----------

export function AboutView({ lang }) {
  const v = V[lang];
  return (
    <section className="view about">
      <ViewHead title={v.aboutTitle} intro={v.aboutLead} />
      <ol className="pipeline">
        {v.aboutHow.map(([h, p]) => (
          <li key={h}><strong>{h}</strong><span>{p}</span></li>
        ))}
      </ol>
      <p className="ai-note">{v.aboutAi}</p>

      <h2>{v.numbersTitle}</h2>
      <dl className="numbers">
        {v.numbers.map(([n, d]) => (
          <div key={n}><dt dir="auto">{n}</dt><dd>{d}</dd></div>
        ))}
      </dl>
      <p className="muted small">{v.numbersNote}</p>

      <h2>{v.sourcesTitle}</h2>
      <p>{v.sources}</p>
      <h2>{v.limitsTitle}</h2>
      <p>{v.limits}</p>
      <p>{v.aiTool}</p>
      <h2>{v.privacyTitle}</h2>
      <ul className="privacy">
        {v.privacy.map((p) => <li key={p}>{p}</li>)}
      </ul>
      <p><a href={REPO} target="_blank" rel="noreferrer">{v.code}</a></p>
    </section>
  );
}
