import { useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "";

const EXAMPLES = [
  { label: "رسالة متداولة", text: "انشروها تؤجروا 🌸 قال رسول الله ﷺ: «اطلبوا العلم ولو في الصين»" },
  { label: "آية بكلمة محرّفة", text: "قال تعالى: وما خلقت الجن والإنس إلا ليعبدوني" },
  { label: "حديث صحيح", text: "قال النبي ﷺ: لا يؤمن أحدكم حتى يحب لأخيه ما يحب لنفسه" },
  { label: "حديث ضعيف", text: "اتقوا فراسة المؤمن فإنه ينظر بنور الله" },
];

const VERDICT = {
  found: { title: "موجود في المصادر", tone: "found", icon: "✓" },
  partial: { title: "مطابق جزئيًا", tone: "partial", icon: "≈" },
  not_found: { title: "لم نجده في المصادر", tone: "missing", icon: "!" },
};

const GRADE_TONE = { "صحيح": "strong", "حسن": "strong", "ضعيف": "weak", "موضوع": "weak", "منكر": "weak", "باطل": "weak", "شاذ": "weak" };

function Mark({ size = 56 }) {
  return <img src="/mark.svg" width={size} height={size} alt="" aria-hidden="true" />;
}

function QuoteLine({ diff }) {
  return (
    <p className="quote-line">
      {diff.map((d, i) => (
        <span key={i} className={d.status === "same" ? "" : "w-off"}>
          {d.word}{" "}
        </span>
      ))}
    </p>
  );
}

function SourceText({ words }) {
  // Show the matched span with a little context on each side.
  const first = words.findIndex((w) => w.status !== "context");
  const last = words.length - 1 - [...words].reverse().findIndex((w) => w.status !== "context");
  const from = Math.max(0, first - 8);
  const to = Math.min(words.length, last + 9);
  const PUNCT = /^[\s\u200e\u200f"'“”«»:.,،؛]+$/;
  return (
    <p className="source-text">
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
function headline(r) {
  const m = r.match;
  if (r.verdict === "found" && m) {
    if (m.grade_status === "weak") return { title: "موجود لكنه ضعيف", tone: "missing", icon: "!" };
    if (m.grade_status === "disputed") return { title: "موجود ومختلف في درجته", tone: "partial", icon: "≈" };
    const misattributed = (r.claimed === "hadith" && m.type === "quran") || (r.claimed === "quran" && m.type === "hadith");
    if (misattributed) return { title: "موجود لكن نسبته خاطئة", tone: "partial", icon: "≈" };
  }
  return VERDICT[r.verdict];
}

function Result({ r }) {
  const v = headline(r);
  const m = r.match;
  return (
    <article className={`result tone-${v.tone}`} aria-live="polite">
      <header className="verdict">
        <span className="seal" aria-hidden="true">{v.icon}</span>
        <div>
          <h2>{v.title}</h2>
          {m && <p className="ref">{m.ref}</p>}
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
              <h3>ما في الرسالة</h3>
              <QuoteLine diff={r.diff} />
            </>
          )}
          <h3>{r.verdict === "partial" ? "النص الصحيح في المصدر" : "النص في المصدر"}</h3>
          <SourceText words={m.words} />
          <a className="source-link" href={m.link} target="_blank" rel="noreferrer">
            افتح في {m.type === "quran" ? "Quran.com" : "Sunnah.com"}
          </a>
        </section>
      )}

      {m && m.type === "hadith" && (
        <section className="grades">
          <h3>درجة الحديث{m.grade_summary && <span className={`grade-pill g-${m.grade_status}`}>{m.grade_summary}</span>}</h3>
          {m.grades.length === 1 && m.ref.startsWith(m.grades[0].scholar) && (
            <p className="grade-note">من أحاديث {m.grades[0].scholar}، وأحاديثه صحيحة عند أهل العلم.</p>
          )}
          {m.grades.length > 0 && !(m.grades.length === 1 && m.ref.startsWith(m.grades[0].scholar)) && (
            <dl>
              {m.grades.map((g, i) => (
                <div key={i} className="grade-row">
                  <dt>{g.scholar}</dt>
                  <dd className={`g-${GRADE_TONE[g.grade] || "none"}`}>{g.grade}</dd>
                </div>
              ))}
            </dl>
          )}
        </section>
      )}

      {r.others.length > 0 && (
        <section className="others">
          <h3>ورد أيضًا في</h3>
          <ul>
            {r.others.map((o) => (
              <li key={o.ref}><a href={o.link} target="_blank" rel="noreferrer">{o.ref}</a></li>
            ))}
          </ul>
        </section>
      )}

      {m && m.english && (
        <details className="english">
          <summary>{m.type === "quran" ? "المعنى بالإنجليزية" : "الترجمة الإنجليزية"}</summary>
          <p dir="ltr" lang="en">{m.english}</p>
        </details>
      )}
    </article>
  );
}

export default function App() {
  const [text, setText] = useState("");
  const [state, setState] = useState({ status: "idle" });
  const inputRef = useRef(null);

  async function check(value = text) {
    if (!value.trim()) {
      inputRef.current?.focus();
      setState({ status: "error", message: "الصق نص الآية أو الحديث أولًا." });
      return;
    }
    setState({ status: "loading" });
    try {
      const res = await fetch(`${API}/api/check`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ text: value, lang: "ar" }),
      });
      if (!res.ok) throw new Error(res.status);
      setState({ status: "done", data: await res.json() });
    } catch {
      setState({ status: "error", message: "تعذر الاتصال بالخادم. تحقق من اتصالك ثم حاول مرة أخرى." });
    }
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
          <div>
            <h1>تبيّن</h1>
            <p className="tagline">تحقّق من الآية أو الحديث قبل أن تنشره</p>
          </div>
        </div>
        <p className="ayah-note">
          <span className="amiri">﴿يَا أَيُّهَا الَّذِينَ آمَنُوا إِنْ جَاءَكُمْ فَاسِقٌ بِنَبَإٍ فَتَبَيَّنُوا﴾</span>
          <span className="ayah-ref">الحجرات: ٦</span>
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
          <label htmlFor="msg">الصق الرسالة أو النص كما وصلك</label>
          <textarea
            id="msg"
            ref={inputRef}
            value={text}
            onChange={(e) => setText(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) check();
            }}
            rows={5}
            placeholder="مثال: قال رسول الله ﷺ: ..."
          />
          <div className="ask-row">
            <button type="submit" disabled={state.status === "loading"}>
              {state.status === "loading" ? "جارٍ التحقق" : "تحقّق"}
            </button>
            <div className="examples">
              <span>جرّب:</span>
              {EXAMPLES.map((ex) => (
                <button type="button" key={ex.label} className="chip" onClick={() => tryExample(ex)}>
                  {ex.label}
                </button>
              ))}
            </div>
          </div>
        </form>

        {state.status === "error" && <p className="error" role="alert">{state.message}</p>}
        {state.status === "loading" && <p className="loading" role="status">نبحث في القرآن الكريم وكتب الحديث…</p>}
        {state.status === "done" && state.data.results.map((r, i) => <Result key={i} r={r} />)}
        {state.status === "done" && <p className="scope">{state.data.results[0].scope}</p>}

        {state.status === "idle" && (
          <section className="how">
            <p>
              يستخرج تبيّن الآية أو الحديث من الرسالة، ويبحث عنه في نص القرآن الكريم وتسعة من كتب الحديث،
              ثم يخبرك هل هو موجود كما هو، أو تغيّرت بعض كلماته، أو لم يُعثر عليه.
            </p>
            <p>الحكم مصدره النصوص نفسها، وليس ذاكرة الذكاء الاصطناعي.</p>
          </section>
        )}
      </main>

      <footer className="foot">
        <p>تبيّن لا يُصدر فتاوى. لما يتجاوز التحقق من وجود النص ودرجته، ارجع إلى أهل العلم.</p>
        <p>
          المصادر: نص القرآن من مشروع تنزيل، والأحاديث ودرجاتها من بيانات Sunnah.com.
        </p>
      </footer>
    </>
  );
}
