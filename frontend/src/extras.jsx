import { useEffect, useRef, useState } from "react";

const API = import.meta.env.VITE_API_URL || "";

// Interface text for the features around a check.
export const X = {
  ar: {
    image: "صورة",
    imageTitle: "تحقق من صورة أو لقطة شاشة",
    reading: "نقرأ النص من الصورة…",
    readFrom: "النص الذي قرأناه من الصورة. راجعه، وإن كان فيه خطأ في القراءة فصحّحه ثم اضغط تحقّق.",
    imageTip: "يمكنك أيضًا لصق صورة هنا مباشرة.",
    findAlt: "ابحث عن نص صحيح بديل",
    findingAlt: "نبحث في المصادر عن نص صحيح قريب المعنى…",
    altTitle: "نصوص صحيحة قريبة المعنى",
    altNote: "اختيرت من المصادر الموثقة فقط، ونصها منقول منها كما هو. قرب المعنى تقدير، فارجع إلى أهل العلم في فهمها.",
    writeReply: "اكتب ردًا لطيفًا",
    writingReply: "نكتب الرد…",
    replyTitle: "رد يمكنك إرساله",
    copy: "نسخ",
    copied: "تم النسخ",
    whatsapp: "أرسل عبر واتساب",
    edit: "يمكنك تعديل الرد قبل إرساله.",
    learn: "تعلّم",
    daily: "حديث اليوم",
    dailyNote: "من الأربعين النووية، كما هو في المصدر.",
    open: "افتح في Sunnah.com",
    meaning: "الترجمة الإنجليزية",
    lessonsTitle: "دروس قصيرة في التحقق",
    lessons: [
      {
        q: "كيف تعرف أن الرسالة قد تكون مكذوبة؟",
        a: [
          "تطلب منك النشر بإلحاح، أو تعدك بأجر عظيم إن نشرتها، أو تتوعدك إن لم تفعل.",
          "تذكر ثوابًا مبالغًا فيه لعمل يسير، أو أرقامًا وتفاصيل غريبة.",
          "لا تذكر مصدرًا، أو تذكر «رواه البخاري» دون رقم يمكن التحقق منه.",
          "ألفاظها حديثة لا تشبه كلام النبوة.",
        ],
      },
      {
        q: "ما معنى درجات الحديث؟",
        a: [
          "صحيح: نقله رواة عدول ضابطون بسند متصل، دون شذوذ ولا علة.",
          "حسن: مثل الصحيح، لكن ضبط بعض رواته أخف. وهو مقبول يُحتج به.",
          "ضعيف: لم تجتمع فيه شروط القبول، فلا يُنسب إلى النبي ﷺ بجزم.",
          "موضوع: مكذوب على النبي ﷺ، ولا تجوز روايته إلا لبيان كذبه.",
        ],
      },
      {
        q: "هل «لم نجده» يعني أنه مكذوب؟",
        a: [
          "لا. تبيّن يبحث في القرآن وتسعة من كتب الحديث، وهناك كتب أخرى كثيرة.",
          "لكن ما لا يُعرف مصدره لا يُنسب إلى النبي ﷺ حتى يُعرف، فاسأل أهل العلم قبل نشره.",
        ],
      },
      {
        q: "لماذا يهم تغيير كلمة واحدة؟",
        a: [
          "القرآن محفوظ بلفظه، وتغيير كلمة فيه ولو بحسن نية خطأ ينبغي تصحيحه.",
          "وفي الحديث، قد تغيّر الكلمة الواحدة المعنى، فانقل النص كما ورد في المصدر.",
        ],
      },
    ],
    noAi: "هذه الميزة تحتاج خدمة الذكاء الاصطناعي، وهي غير متاحة الآن.",
    failed: "تعذر إكمال الطلب. حاول مرة أخرى.",
    bigImage: "الصورة كبيرة جدًا.",
  },
  en: {
    image: "Image",
    imageTitle: "Check an image or screenshot",
    reading: "Reading the text in the image…",
    readFrom: "The text we read from the image. Check it, and if anything was misread, correct it and press Check.",
    imageTip: "You can also paste an image here directly.",
    findAlt: "Find an authentic alternative",
    findingAlt: "Searching the sources for an authentic text with a close meaning…",
    altTitle: "Authentic texts with a close meaning",
    altNote: "Chosen only from the authenticated sources, quoted exactly as they are there. Closeness of meaning is an estimate, so ask scholars about their meaning.",
    writeReply: "Write a polite reply",
    writingReply: "Writing the reply…",
    replyTitle: "A reply you can send",
    copy: "Copy",
    copied: "Copied",
    whatsapp: "Send on WhatsApp",
    edit: "You can edit the reply before sending it.",
    learn: "Learn",
    daily: "Hadith of the day",
    dailyNote: "From an-Nawawi's Forty Hadith, as it is in the source.",
    open: "Open in Sunnah.com",
    meaning: "English translation",
    lessonsTitle: "Short lessons on checking",
    lessons: [
      {
        q: "How can you tell a message may be fabricated?",
        a: [
          "It pushes you to forward it, promises a great reward if you share it, or threatens you if you don't.",
          "It promises an exaggerated reward for a small deed, or gives strange numbers and details.",
          "It gives no source, or says \"narrated by Bukhari\" with no number you can check.",
          "Its wording is modern and does not sound like the language of the hadiths.",
        ],
      },
      {
        q: "What do hadith gradings mean?",
        a: [
          "Sahih (authentic): passed on by trustworthy, precise narrators through a connected chain, with no hidden defect.",
          "Hasan (good): like sahih, but some narrators were less precise. It is accepted.",
          "Daif (weak): does not meet the conditions for acceptance, so it is not attributed to the Prophet ﷺ with certainty.",
          "Mawdu (fabricated): falsely attributed to the Prophet ﷺ. It may only be mentioned to warn about it.",
        ],
      },
      {
        q: "Does \"not found\" mean fabricated?",
        a: [
          "No. Tabayyan searches the Quran and nine hadith collections, and there are many other books.",
          "But a text whose source is unknown should not be attributed to the Prophet ﷺ until it is known, so ask a scholar before sharing it.",
        ],
      },
      {
        q: "Why does one changed word matter?",
        a: [
          "The Quran is preserved word for word, and a changed word, even with good intentions, is a mistake that should be corrected.",
          "In a hadith, one word can change the meaning, so quote the text as it is in the source.",
        ],
      },
    ],
    noAi: "This feature needs the AI service, which is not available right now.",
    failed: "Could not complete the request. Please try again.",
    bigImage: "The image is too large.",
  },
};

async function post(path, body) {
  const res = await fetch(`${API}${path}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || res.status);
  return data;
}

// Shrink big photos before upload: text stays readable at 1600px.
export function imageToDataUrl(file, max = 1600) {
  return new Promise((resolve, reject) => {
    const img = new Image();
    const url = URL.createObjectURL(file);
    img.onload = () => {
      const scale = Math.min(1, max / Math.max(img.width, img.height));
      const c = document.createElement("canvas");
      c.width = Math.round(img.width * scale);
      c.height = Math.round(img.height * scale);
      c.getContext("2d").drawImage(img, 0, 0, c.width, c.height);
      URL.revokeObjectURL(url);
      resolve(c.toDataURL("image/jpeg", 0.88));
    };
    img.onerror = () => reject(new Error("image"));
    img.src = url;
  });
}

export async function checkImage(file, lang) {
  if (file.size > 25 * 1024 * 1024) throw new Error(X[lang].bigImage);
  const image = await imageToDataUrl(file);
  return post("/api/check-image", { image, lang });
}

export function ImageButton({ lang, disabled, onFile }) {
  const input = useRef(null);
  const x = X[lang];
  return (
    <>
      <button type="button" className="img-btn" title={x.imageTitle} disabled={disabled}
        onClick={() => input.current?.click()}>
        <svg width="18" height="18" viewBox="0 0 24 24" aria-hidden="true"><path fill="currentColor" d="M9 4 7.2 6H4a2 2 0 0 0-2 2v10a2 2 0 0 0 2 2h16a2 2 0 0 0 2-2V8a2 2 0 0 0-2-2h-3.2L15 4H9Zm3 4.5a4.5 4.5 0 1 1 0 9 4.5 4.5 0 0 1 0-9Zm0 2a2.5 2.5 0 1 0 0 5 2.5 2.5 0 0 0 0-5Z"/></svg>
        {x.image}
      </button>
      <input ref={input} type="file" accept="image/*" hidden
        onChange={(e) => { const f = e.target.files?.[0]; e.target.value = ""; if (f) onFile(f); }} />
    </>
  );
}

function CopyButton({ text, x }) {
  const [done, setDone] = useState(false);
  return (
    <button type="button" className="mini" onClick={async () => {
      try { await navigator.clipboard.writeText(text); setDone(true); setTimeout(() => setDone(false), 1500); } catch { /* ignore */ }
    }}>{done ? x.copied : x.copy}</button>
  );
}

// Buttons under a result: authentic alternatives (for unsourced or weak texts) and a polite reply.
export function ResultActions({ r, lang, aiOn }) {
  const x = X[lang];
  const [alt, setAlt] = useState({ status: "idle" });
  const [reply, setReply] = useState({ status: "idle" });
  const weak = r.match && r.match.grade_status === "weak";
  const wantsAlt = (r.verdict === "not_found" && r.claimed !== "athar") || weak;

  async function findAlt() {
    setAlt({ status: "loading" });
    try {
      setAlt({ status: "done", data: await post("/api/alternatives", { text: r.quote, lang }) });
    } catch (e) {
      setAlt({ status: "error", message: String(e.message || x.failed) });
    }
  }

  async function writeReply() {
    setReply({ status: "loading" });
    const first = alt.status === "done" ? alt.data.items[0] : null;
    try {
      const d = await post("/api/reply", { result: r, alternative: first || null, lang });
      setReply({ status: "done", text: d.reply });
    } catch {
      setReply({ status: "error", message: x.failed });
    }
  }

  return (
    <section className="actions">
      <div className="action-row">
        {wantsAlt && aiOn && alt.status === "idle" && (
          <button type="button" className="act" onClick={findAlt}>{x.findAlt}</button>
        )}
        {reply.status !== "loading" && (
          <button type="button" className="act ghost" onClick={writeReply}>{x.writeReply}</button>
        )}
      </div>

      {alt.status === "loading" && <p className="muted">{x.findingAlt}</p>}
      {alt.status === "error" && <p className="error-sm">{alt.message}</p>}
      {alt.status === "done" && (
        <div className="alts">
          {alt.data.items.length === 0 ? (
            <p className="muted">{alt.data.message}</p>
          ) : (
            <>
              <h3>{x.altTitle}</h3>
              {alt.data.items.map((a, i) => (
                <div key={i} className="alt">
                  <p className="alt-text" dir="rtl" lang="ar">{a.excerpt}</p>
                  <p className="alt-ref">
                    <a href={a.link} target="_blank" rel="noreferrer">{a.ref}</a>
                    {a.grade_summary && <span className="grade-pill g-strong">{a.grade_summary}</span>}
                  </p>
                  {a.why && <p className="alt-why">{a.why}</p>}
                  {a.english && (
                    <details className="english"><summary>{x.meaning}</summary><p dir="ltr" lang="en">{a.english}</p></details>
                  )}
                </div>
              ))}
              <p className="muted small">{x.altNote}</p>
            </>
          )}
        </div>
      )}

      {reply.status === "loading" && <p className="muted">{x.writingReply}</p>}
      {reply.status === "error" && <p className="error-sm">{reply.message}</p>}
      {reply.status === "done" && (
        <div className="reply">
          <h3>{x.replyTitle}</h3>
          <textarea dir="auto" value={reply.text} rows={5}
            onChange={(e) => setReply({ status: "done", text: e.target.value })} />
          <p className="muted small">{x.edit}</p>
          <div className="action-row">
            <CopyButton text={reply.text} x={x} />
            <a className="mini wa" href={`https://wa.me/?text=${encodeURIComponent(reply.text)}`} target="_blank" rel="noreferrer">
              {x.whatsapp}
            </a>
          </div>
        </div>
      )}
    </section>
  );
}

// Hadith of the day (straight from the data) and short lessons on checking.
export function Learn({ lang }) {
  const x = X[lang];
  const [day, setDay] = useState(null);
  useEffect(() => {
    let live = true;
    fetch(`${API}/api/daily?lang=${lang}`).then((r) => r.json()).then((d) => live && setDay(d)).catch(() => {});
    return () => { live = false; };
  }, [lang]);
  return (
    <section className="learn" aria-labelledby="learn-h">
      <h2 id="learn-h">{x.learn}</h2>
      {day && (
        <article className="daily">
          <h3>{x.daily}</h3>
          <p className="daily-text" dir="rtl" lang="ar">{day.text}</p>
          <p className="alt-ref"><a href={day.link} target="_blank" rel="noreferrer">{day.ref}</a></p>
          {lang === "en" && day.english && <p className="daily-en" dir="ltr" lang="en">{day.english}</p>}
          <p className="muted small">{x.dailyNote}</p>
        </article>
      )}
      <h3 className="lessons-h">{x.lessonsTitle}</h3>
      {x.lessons.map((l, i) => (
        <details key={i} className="lesson">
          <summary>{l.q}</summary>
          <ul>{l.a.map((p, j) => <li key={j}>{p}</li>)}</ul>
        </details>
      ))}
    </section>
  );
}
