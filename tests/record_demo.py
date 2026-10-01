"""Record the 2-minute demo video of Tabayyan (web app + Chrome extension).

Everything shown is the real app running against the real API. Captions and a
visible cursor are overlaid so the recording reads without narration.
"""
import base64
import sys
import time
from pathlib import Path

from playwright.sync_api import sync_playwright

SP = Path(sys.argv[1])
EXT = SP / "ext_copy"
OUT = SP / "video"
OUT.mkdir(exist_ok=True)
MARK = base64.b64encode(Path("/home/claude/tabayyan/frontend/public/mark.svg").read_bytes()).decode()

OVERLAY = """
(() => {
  if (window.__tb) return; window.__tb = true;
  const add = () => {
    const c = document.createElement('div'); c.id='__cursor';
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2l16 10-7 1.5L9.5 21z" fill="#fff" stroke="#111" stroke-width="1.4"/></svg>';
    c.style.cssText='position:fixed;left:-50px;top:-50px;z-index:2147483647;pointer-events:none;transition:none';
    document.documentElement.appendChild(c);
    document.addEventListener('mousemove', e => { c.style.left=e.clientX-3+'px'; c.style.top=e.clientY-2+'px'; }, true);
    const cap = document.createElement('div'); cap.id='__cap';
    cap.style.cssText='position:fixed;left:50%;bottom:26px;transform:translateX(-50%);max-width:86%;z-index:2147483646;'+
      'background:rgba(18,40,77,.94);color:#fff;font:600 25px/1.6 "Noto Sans Arabic",sans-serif;padding:10px 26px;border-radius:12px;'+
      'direction:rtl;text-align:center;box-shadow:0 6px 24px rgba(0,0,0,.25);opacity:0;transition:opacity .35s';
    document.documentElement.appendChild(cap);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', add); else add();
})();
"""


def card_html(lines, big=None, small=None):
    body = "".join(f"<p>{l}</p>" for l in lines)
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>
    body{{margin:0;height:100vh;background:#193565;color:#fff;font-family:"Noto Sans Arabic",sans-serif;display:flex;align-items:center;
      justify-content:center;overflow:hidden;position:relative}}
    .ros{{position:absolute;left:-160px;top:-120px;width:620px;opacity:.35}}
    .box{{text-align:center;max-width:900px;animation:in .6s ease-out both}}
    @keyframes in{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
    h1{{font-size:96px;margin:0 0 6px;line-height:1.2}}
    .sub{{font-size:32px;color:#30D0C8;margin:0 0 20px}}
    p{{font-size:34px;line-height:1.7;margin:6px 0}}
    .small{{font-size:22px;color:#AFC0DE;margin-top:28px}}
    </style></head><body><img class="ros" src="data:image/svg+xml;base64,{MARK}">
    <div class="box">{f"<h1>{big}</h1>" if big else ""}{body}{f'<p class="small">{small}</p>' if small else ""}</div></body></html>"""


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(SP / "profile_vid"), headless=True, channel="chromium",
        # In new headless mode the window size includes ~139px of hidden browser UI,
        # so this gives a 1280x720 page that the video captures in full.
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--window-size=1280,859"],
        no_viewport=True, record_video_dir=str(OUT),
        record_video_size={"width": 1280, "height": 720})
    sw = ctx.service_workers[0] if ctx.service_workers else ctx.wait_for_event("serviceworker", timeout=15000)
    ctx.add_init_script(OVERLAY)
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()
    T0 = time.time()

    def caption(text, wait=0):
        pg.evaluate("""t => { const c=document.getElementById('__cap'); if(!c) return;
            if(!t){c.style.opacity=0;return;} c.textContent=t; c.style.opacity=1; }""", text)
        if wait:
            pg.wait_for_timeout(wait)

    def move_to(selector, nth=0, click=True):
        box = pg.locator(selector).nth(nth).bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        pg.mouse.move(x, y, steps=18)
        pg.wait_for_timeout(250)
        if click:
            pg.mouse.click(x, y)

    def scroll_to(y, ms=900):
        pg.evaluate("y => window.scrollTo({top:y, behavior:'smooth'})", y)
        pg.wait_for_timeout(ms)

    def result_top():
        return pg.evaluate("() => document.querySelector('.result').getBoundingClientRect().top + window.scrollY - 20")

    def check(text, chip=None):
        scroll_to(0, 500)
        if chip is not None:
            move_to(".chip", chip)
        else:
            move_to("#msg")
            pg.fill("#msg", "")
            pg.type("#msg", text, delay=28)
            pg.wait_for_timeout(300)
            move_to("button[type=submit]")
        pg.wait_for_selector(".result")
        pg.wait_for_timeout(700)

    # 1. Opening
    pg.set_content(card_html([], big="تبيّن", small="تحدي الذكاء الاصطناعي في خدمة المحتوى الإسلامي").replace(
        '<div class="box"><h1>تبيّن</h1>', '<div class="box"><h1>تبيّن</h1><p class="sub">تحقّق من الآية أو الحديث قبل أن تنشره</p>'))
    pg.wait_for_timeout(4200)

    # 2. Problem
    pg.set_content(card_html([
        "رسائل كثيرة تنتشر فيها أحاديث مكذوبة،",
        "وآيات تغيّرت كلماتها، وأقوال تُنسب إلى النبي ﷺ دون أصل.",
        "<span style='color:#30D0C8'>والتحقق منها يدويًا بطيء ويحتاج خبرة.</span>"]))
    pg.wait_for_timeout(6500)

    # 3. App: fabricated quote
    pg.goto("http://localhost:8000/")
    pg.wait_for_timeout(900)
    caption("الصق الرسالة كما وصلتك", 1500)
    check("انشروها تؤجروا 🌸 قال رسول الله ﷺ: «اطلبوا العلم ولو في الصين»")
    scroll_to(result_top() - 160)
    caption("قول مشهور لا أصل له في المصادر: يُنبَّه المستخدم ألا ينشره منسوبًا إلى النبي ﷺ", 6500)

    # 4. Altered verse
    caption("")
    check("قال تعالى: وما خلقت الجن والإنس إلا ليعبدوني")
    scroll_to(result_top())
    caption("آية بكلمة محرّفة: تظهر الكلمة الخطأ، والنص الصحيح من المصحف", 7500)

    # 5. Authentic hadith
    caption("")
    check(None, chip=2)
    scroll_to(result_top())
    caption("حديث صحيح: المرجع الدقيق، ودرجته، وأين ورد أيضًا", 4000)
    scroll_to(result_top() + 260, 1200)
    pg.wait_for_timeout(2500)

    # 6. Weak hadith
    caption("")
    check(None, chip=3)
    scroll_to(result_top())
    caption("موجود في جامع الترمذي، لكن العلماء ضعّفوه، فلا يظهر باللون الأخضر", 4500)
    scroll_to(result_top() + 330, 1200)
    pg.wait_for_timeout(2500)

    # 7. Misattribution
    caption("")
    check("قال رسول الله ﷺ: إن الله مع الصابرين")
    scroll_to(result_top() - 60)
    caption("آية من القرآن نُسبت إلى النبي ﷺ: ينبّه إلى أن النسبة خاطئة", 6500)

    # 8. Chrome extension
    caption("")
    pg.goto("http://localhost:8765/")
    pg.wait_for_timeout(700)
    caption("إضافة كروم: حدّد النص في أي صفحة أو منصة", 600)
    post = pg.locator(".post").first.bounding_box()
    sx, ex, yy = post["x"] + post["width"] - 175, post["x"] + 45, post["y"] + 46
    pg.mouse.move(sx, yy, steps=15)
    pg.mouse.down()
    pg.mouse.move(ex, yy + 46, steps=30)
    pg.mouse.up()
    pg.evaluate("""()=>{const r=document.createRange();const n=document.querySelector('.post').firstChild;
        const t=n.textContent;r.setStart(n,t.indexOf('قال'));r.setEnd(n,t.indexOf('»')+1);getSelection().removeAllRanges();getSelection().addRange(r);}""")
    pg.wait_for_timeout(1200)
    caption("ثم انقر بالزر الأيمن واختر: تحقّق مع تبيّن", 2200)
    sw.evaluate("""async (text) => {
        const [tab] = await chrome.tabs.query({url: "http://localhost:8765/*"});
        await chrome.scripting.executeScript({target:{tabId:tab.id}, files:["render.js","panel.js"]});
        await chrome.scripting.executeScript({target:{tabId:tab.id}, func:()=>globalThis.TabayyanPanel.loading()});
        const res = await fetch("http://localhost:8000/api/check", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({text, lang:"ar"})});
        const data = await res.json();
        await new Promise(r => setTimeout(r, 500));
        await chrome.scripting.executeScript({target:{tabId:tab.id}, func:(d)=>globalThis.TabayyanPanel.show(d), args:[data]});
    }""", "قال رسول الله صلى الله عليه وسلم: «النظافة من الإيمان»")
    caption("النتيجة تظهر فوق الصفحة نفسها، دون مغادرتها", 5500)

    # 9. How it stays reliable
    pg.set_content(card_html([
        "الحكم مصدره النصوص الموثقة، لا ذاكرة الذكاء الاصطناعي.",
        "<span style='color:#AFC0DE;font-size:28px'>القرآن الكريم كاملًا، وتسعة من كتب الحديث بدرجات العلماء</span>",
        "<span style='color:#AFC0DE;font-size:28px'>دور النموذج: استخراج النص وشرح النتيجة فقط</span>",
        "<span style='color:#30D0C8'>لا يُصدر فتاوى، ويحيل إلى أهل العلم</span>"]))
    pg.wait_for_timeout(7500)

    # 10. Closing
    pg.set_content(card_html(["<span class='sub' style='font-size:32px;color:#30D0C8'>تحقّق قبل أن تنشر</span>"], big="تبيّن",
                             small="محمد الزهراني"))
    pg.wait_for_timeout(4000)

    print(f"recorded {time.time() - T0:.1f}s")
    video = pg.video.path()
    ctx.close()
    print(video)
