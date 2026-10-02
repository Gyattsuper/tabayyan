import { useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "";

// Interface text in each language. Results (references, warnings, explanations)
// come from the server already in the chosen language.
const T = {
  ar: {
    dir: "rtl",
    tagline: "تحقّق من الآية أو الحديث قبل أن تنشره",
    ayahMeaning: null,
    ayahRef: "الحجرات: ٦",
    langLabel: "اللغة",
    label: "الصق الرسالة أو النص كما وصلك",
    placeholder: "مثال: قال رسول الله ﷺ: ...  (يمكنك أيضًا لصق نص بالإنجليزية)",
    check: "تحقّق",
    checking: "جارٍ التحقق",
    try: "جرّب:",
    loading: "نبحث في القرآن الكريم وكتب الحديث…",
    emptyInput: "الصق نص الآية أو الحديث أولًا.",
    netError: "تعذر الاتصال بالخادم. تحقق من اتصالك ثم حاول مرة أخرى.",
    how: [
      "يستخرج تبيّن الآية أو الحديث من الرسالة، ويبحث عنه في نص القرآن الكريم وتسعة من كتب الحديث، ثم يخبرك هل هو موجود كما هو، أو تغيّرت بعض كلماته، أو لم يُعثر عليه.",
      "يقبل النصوص العربية والإنجليزية: الإنجليزية تُقارن بأشهر ترجمات معاني القرآن وبترجمة الأحاديث.",
      "الحكم مصدره النصوص نفسها، وليس ذاكرة الذكاء الاصطناعي.",
    ],
    verdict: { found: "موجود في المصادر", partial: "مطابق جزئيًا", not_found: "لم نجده في المصادر" },
    weak: "موجود لكنه ضعيف",
    disputed: "موجود ومختلف في درجته",
    misattributed: "موجود لكن نسبته خاطئة",
    athar: "قول منسوب لغير النبي ﷺ",
    foundEn: "يطابق ترجمة معروفة",
    partialEn: "قريب من ترجمة معروفة",
    inMessage: "ما في الرسالة",
    correctText: "النص الصحيح في المصدر",
    sourceText: "النص في المصدر",
    translation: (t) => `ترجمة ${t}`,
    original: "النص العربي",
    open: (q) => `افتح في ${q ? "Quran.com" : "Sunnah.com"}`,
    grading: "درجة الحديث",
    sahihNote: (s) => `من أحاديث ${s}، وأحاديثه صحيحة عند أهل العلم.`,
    alsoIn: "ورد أيضًا في",
    englishMeaning: (q) => (q ? "المعنى بالإنجليزية" : "الترجمة الإنجليزية"),
    foot1: "تبيّن لا يُصدر فتاوى. لما يتجاوز التحقق من وجود النص ودرجته، ارجع إلى أهل العلم.",
    foot2: "المصادر: نص القرآن من مشروع تنزيل، والأحاديث ودرجاتها من بيانات Sunnah.com، والترجمات من مشروع تنزيل وSunnah.com.",
    extNote: "إضافة كروم: نسخة تجريبية تُثبَّت من المستودع، ولم تُنشر في متجر كروم بعد.",
    install: "طريقة التثبيت",
    code: "الكود على GitHub",
    examples: [
      { label: "رسالة متداولة", text: "انشروها تؤجروا 🌸 قال رسول الله ﷺ: «اطلبوا العلم ولو في الصين»" },
      { label: "آية بكلمة محرّفة", text: "قال تعالى: وما خلقت الجن والإنس إلا ليعبدوني" },
      { label: "حديث صحيح", text: "قال النبي ﷺ: لا يؤمن أحدكم حتى يحب لأخيه ما يحب لنفسه" },
      { label: "حديث ضعيف", text: "اتقوا فراسة المؤمن فإنه ينظر بنور الله" },
    ],
  },
  en: {
    dir: "ltr",
    tagline: "Check a verse or hadith before you share it",
    ayahMeaning: "“O you who have believed, if there comes to you a disobedient one with information, investigate.”",
    ayahRef: "Al-Hujurat 49:6",
    langLabel: "Language",
    label: "Paste the message or text as you received it",
    placeholder: "Example: The Prophet ﷺ said: ...  (Arabic text works too)",
    check: "Check",
    checking: "Checking",
    try: "Try:",
    loading: "Searching the Quran and the hadith collections…",
    emptyInput: "Paste the text of the verse or hadith first.",
    netError: "Could not reach the server. Check your connection and try again.",
    how: [
      "Tabayyan finds the verse or hadith in the message, searches the text of the Quran and nine hadith collections, and tells you whether it is there as written, whether some words were changed, or whether it was not found.",
      "It accepts Arabic and English. English quotes are compared with well-known Quran translations and the hadith translations.",
      "Verdicts come from the source texts themselves, not from an AI model's memory.",
    ],
    verdict: { found: "Found in the sources", partial: "Partial match", not_found: "Not found in the sources" },
    weak: "Found, but graded weak",
    disputed: "Found, grading disputed",
    misattributed: "Found, but wrongly attributed",
    athar: "Attributed to someone other than the Prophet ﷺ",
    foundEn: "Matches a known translation",
    partialEn: "Close to a known translation",
    inMessage: "In the message",
    correctText: "Correct text in the source",
    sourceText: "Text in the source",
    translation: (t) => `${t} translation`,
    original: "Original Arabic",
    open: (q) => `Open in ${q ? "Quran.com" : "Sunnah.com"}`,
    grading: "Hadith grading",
    sahihNote: (s) => `From ${s}, whose hadiths scholars accept as authentic.`,
    alsoIn: "Also found in",
    englishMeaning: (q) => (q ? "English meaning (Saheeh International)" : "English translation"),
    foot1: "Tabayyan does not issue religious rulings. For anything beyond whether a text exists and how it was graded, ask a scholar.",
    foot2: "Sources: Quran text and translations from Tanzil; hadiths, gradings and translations from Sunnah.com data.",
    extNote: "Chrome extension: a beta installed from the repository, not on the Chrome Web Store yet.",
    install: "How to install",
    code: "Code on GitHub",
    examples: [
      { label: "Viral message", text: "Please share 🌸 The Prophet ﷺ said: Seek knowledge even if you have to go to China" },
      { label: "Altered verse", text: "Allah says: And I did not create the jinn and mankind except to obey Me" },
      { label: "Authentic hadith", text: "The Prophet ﷺ said: None of you will have faith till he wishes for his brother what he likes for himself" },
      { label: "Weak hadith", text: "Beware of the believer's intuition, for indeed he sees with Allah's Light" },
    ],
  },
};

function initialLang() {
  try {
    const fromUrl = new URLSearchParams(window.location.search).get("lang");
    if (fromUrl === "ar" || fromUrl === "en") return fromUrl;
    const saved = window.localStorage.getItem("tabayyan-lang");
    if (saved === "ar" || saved === "en") return saved;
  } catch {
    /* storage can be unavailable; fall through */
  }
  return "ar";
}

function Mark({ size = 56 }) {
  return <img src="/mark.svg" width={size} height={size} alt="" aria-hidden="true" />;
}

function QuoteLine({ diff, en }) {
  return (
    <p className={`quote-line${en ? " en" : ""}`} dir={en ? "ltr" : "rtl"}>
      {diff.map((d, i) => (
        <span key={i} className={d.status === "same" ? "" : "w-off"}>
          {d.word}{" "}
        </span>
      ))}
    </p>
  );
}

function SourceText({ words, en }) {
  // Show the matched span with a little context on each side.
  const first = words.findIndex((w) => w.status !== "context");
  const last = words.length - 1 - [...words].reverse().findIndex((w) => w.status !== "context");
  const from = Math.max(0, first - 8);
  const to = Math.min(words.length, last + 9);
  const PUNCT = /^[\s‎‏"'“”«»:.,،؛]+$/;
  return (
    <p className={`source-text${en ? " en" : ""}`} dir={en ? "ltr" : "rtl"} lang={en ? "en" : "ar"}>
      {from > 0 && <span className="w-ctx">… </span>}
      {words.slice(from, to).filter((w) => !PUNCT.test(w.word)).map((w, i) => (
        <span key={i} className={w.status === "context" ? "w-ctx" : w.status === "changed" ? "w-fix" : "w-hit"}>
          {w.word}{" "}
        </span>
      ))}
      {to < words.length && <span className="w-ctx">…</span>}
    </p>
  );
}

// "Found" only means the text exists. If it was graded weak, disputed, or
// attributed to the wrong source, don't show it in the reassuring green.
function headline(r, t) {
  const m = r.match;
  if (r.verdict === "found" && m) {
    if (m.grade_status === "weak") return { title: t.weak, tone: "missing", icon: "!" };
    if (m.grade_status === "disputed") return { title: t.disputed, tone: "partial", icon: "≈" };
    const misattributed = (r.claimed === "hadith" && m.type === "quran") || (r.claimed === "quran" && m.type === "hadith")
      || (r.claimed === "athar" && m.type === "quran");
    if (misattributed) return { title: t.misattributed, tone: "partial", icon: "≈" };
    if (m.translator) return { title: t.foundEn, tone: "found", icon: "✓" };
  }
  if (r.verdict === "partial" && m && m.translator) return { title: t.partialEn, tone: "partial", icon: "≈" };
  // A companion's or scholar's saying that isn't in the hadith books: outside what we search,
  // so don't show it in the alarming red used for unsourced hadiths.
  if (r.verdict === "not_found" && r.claimed === "athar") return { title: t.athar, tone: "scope", icon: "؟" };
  const icon = { found: "✓", partial: "≈", not_found: "!" }[r.verdict];
  const tone = { found: "found", partial: "partial", not_found: "missing" }[r.verdict];
  return { title: t.verdict[r.verdict], tone, icon };
}

function Result({ r, t }) {
  const v = headline(r, t);
  const m = r.match;
  const en = m && m.words_lang === "en";
  const sahihOnly = m && m.grades.length === 1 && m.ref.startsWith(m.grades[0].scholar);
  return (
    <article className={`result tone-${v.tone}`} aria-live="polite">
      <header className="verdict">
        <span className="seal" aria-hidden="true">{v.icon}</span>
        <div>
          <h2>{v.title}</h2>
          {m && <p className="ref">{m.ref}{m.translator && <span className="translator"> · {t.translation(m.translator)}</span>}</p>}
        </div>
      </header>

      {r.explanation && <p className="explanation">{r.explanation}</p>}

      {r.warnings.length > 0 && (
        <ul className="warnings">
          {r.warnings.map((w, i) => <li key={i}>{w}</li>)}
        </ul>
      )}

      {m && (
        <section className="compare">
          {r.verdict === "partial" && (
            <>
              <h3>{t.inMessage}</h3>
              <QuoteLine diff={r.diff} en={en} />
            </>
          )}
          <h3>{r.verdict === "partial" ? t.correctText : t.sourceText}</h3>
          <SourceText words={m.words} en={en} />
          {m.arabic && (
            <details className="original">
              <summary>{t.original}</summary>
              <p className="source-text" dir="rtl" lang="ar">{m.arabic}</p>
            </details>
          )}
          <a className="source-link" href={m.link} target="_blank" rel="noreferrer">
            {t.open(m.type === "quran")}
          </a>
        </section>
      )}

      {m && m.type === "hadith" && (
        <section className="grades">
          <h3>{t.grading}{m.grade_summary && <span className={`grade-pill g-${m.grade_status}`}>{m.grade_summary}</span>}</h3>
          {sahihOnly && <p className="grade-note">{t.sahihNote(m.grades[0].scholar)}</p>}
          {m.grades.length > 0 && !sahihOnly && (
            <dl>
              {m.grades.map((g, i) => (
                <div key={i} className="grade-row">
                  <dt>{g.scholar}</dt>
                  <dd className={`g-${g.status}`}>{g.grade}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      )}

      {r.others.length > 0 && (
        <section className="others">
          <h3>{t.alsoIn}</h3>
          <ul>
            {r.others.map((o) => (
              <li key={o.ref}><a href={o.link} target="_blank" rel="noreferrer">{o.ref}</a></li>
            ))}
          </ul>
        </section>
      )}

      {m && m.english && (
        <details className="english">
          <summary>{t.englishMeaning(m.type === "quran")}</summary>
          <p dir="ltr" lang="en">{m.english}</p>
        </details>
      )}
    </article>
  );
}

export default function App() {
  const [lang, setLang] = useState(initialLang);
  const [text, setText] = useState("");
  const [state, setState] = useState({ status: "idle" });
  const inputRef = useRef(null);
  const t = T[lang];

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.dir = t.dir;
    document.title = lang === "ar" ? "تبيّن" : "Tabayyan";
    try {
      window.localStorage.setItem("tabayyan-lang", lang);
    } catch {
      /* not saved; fine */
    }
  }, [lang, t.dir]);

  async function check(value = text, l = lang) {
    if (!value.trim()) {
      inputRef.current?.focus();
      setState({ status: "error", message: T[l].emptyInput });
      return;
    }
    setState({ status: "loading" });
    try {
      const res = await fetch(`${API}/api/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: value, lang: l }),
      });
      if (!res.ok) throw new Error(res.status);
      setState({ status: "done", data: await res.json() });
    } catch {
      setState({ status: "error", message: T[l].netError });
    }
  }

  function changeLang(l) {
    setLang(l);
    // Results are written in the chosen language, so fetch them again.
    if (state.status === "done") check(text, l);
    else if (state.status === "error") setState({ status: "idle" });
  }

  function tryExample(ex) {
    setText(ex.text);
    check(ex.text);
  }

  return (
    <>
      <header className="band">
        <div className="band-inner">
          <Mark />
          <div className="brand">
            <h1>{lang === "ar" ? "تبيّن" : "Tabayyan"}</h1>
            <p className="tagline">{t.tagline}</p>
          </div>
          <label className="lang">
            <span className="sr-only">{t.langLabel}</span>
            <select value={lang} onChange={(e) => changeLang(e.target.value)} aria-label={t.langLabel}>
              <option value="ar">العربية</option>
              <option value="en">English</option>
            </select>
          </label>
        </div>
        <p className="ayah-note">
          <span className="amiri" dir="rtl" lang="ar">﴿يَا أَيُّهَا الَّذِينَ آمَنُوا إِنْ جَاءَكُمْ فَاسِقٌ بِنَبَإٍ فَتَبَيَّنُوا﴾</span>
          {t.ayahMeaning && <span className="ayah-meaning">{t.ayahMeaning}</span>}
          <span className="ayah-ref">{t.ayahRef}</span>
        </p>
      </header>

      <main className="page">
        <form
          className="ask"
          onSubmit={(e) => {
            e.preventDefault();
            check();
          }}
        >
          <label htmlFor="msg">{t.label}</label>
          <textarea
            id="msg"
            ref={inputRef}
            value={text}
            dir="auto"
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) check();
            }}
            rows={5}
            placeholder={t.placeholder}
          />
          <div className="ask-row">
            <button type="submit" disabled={state.status === "loading"}>
              {state.status === "loading" ? t.checking : t.check}
            </button>
            <div className="examples">
              <span>{t.try}</span>
              {t.examples.map((ex) => (
                <button type="button" key={ex.label} className="chip" onClick={() => tryExample(ex)}>
                  {ex.label}
                </button>
              ))}
            </div>
          </div>
        </form>

        {state.status === "error" && <p className="error" role="alert">{state.message}</p>}
        {state.status === "loading" && <p className="loading" role="status">{t.loading}</p>}
        {state.status === "done" && state.data.results.map((r, i) => <Result key={i} r={r} t={t} />)}
        {state.status === "done" && state.data.results.length === 0 && (
          <p className="error" role="alert">{state.data.message}</p>
        )}
        {state.status === "done" && state.data.results.length > 0 && <p className="scope">{state.data.results[0].scope}</p>}

        {state.status === "idle" && (
          <section className="how">
            {t.how.map((p, i) => <p key={i}>{p}</p>)}
          </section>
        )}
      </main>

      <footer className="foot">
        <p>{t.foot1}</p>
        <p>{t.foot2}</p>
        <p>
          {t.extNote}{" "}
          <a href="https://github.com/Gyattsuper/tabayyan#chrome-extension" target="_blank" rel="noreferrer">
            {t.install}
          </a>
          {" · "}
          <a href="https://github.com/Gyattsuper/tabayyan" target="_blank" rel="noreferrer">
            {t.code}
          </a>
        </p>
      </footer>
    </>
  );
}
