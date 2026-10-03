"""Record the 2-minute demo video of Tabayyan (web app, phone layout and Chrome extension).

Usage: python tests/record_demo.py <work_dir>
  work_dir holds: ext_copy/ (the extension pointed at http://localhost:8000), feed/ (a sample
  social page served on :8765), makeimg.js, live_ai.json and live_search.json.

Everything shown is the real app running against the local API. This workspace has no Claude API
key, so the parts that need Claude (quote extraction, explanations, image reading, alternatives,
replies, topic search) are answered with responses captured from the live site
(tabayyan.onrender.com, Claude enabled). Verdicts, references and highlighted words still come
from the local server; only the Claude-written text is taken from the capture.
"""
import base64
import json
import sys
import time
import urllib.parse
import urllib.request
from pathlib import Path

from playwright.sync_api import sync_playwright

SP = Path(sys.argv[1])
EXT = SP / "ext_copy"
OUT = SP / "video"
OUT.mkdir(exist_ok=True)
API = "http://localhost:8000"
MARK = base64.b64encode(Path(__file__).resolve().parent.parent.joinpath("frontend/public/mark.svg").read_bytes()).decode()
LIVE = json.loads((SP / "live_ai.json").read_text(encoding="utf-8"))
SEARCH = (SP / "live_search.json").read_text(encoding="utf-8")
MAKEIMG = (SP / "makeimg.js").read_text(encoding="utf-8")

OVERLAY = """
(() => {
  if (window.__tb || window.top !== window) return; window.__tb = true;
  const add = () => {
    const c = document.createElement('div'); c.id='__cursor';
    c.innerHTML = '<svg width="26" height="26" viewBox="0 0 24 24"><path d="M4 2l16 10-7 1.5L9.5 21z" fill="#fff" stroke="#111" stroke-width="1.4"/></svg>';
    c.style.cssText='position:fixed;left:-50px;top:-50px;z-index:2147483647;pointer-events:none;transition:none';
    document.documentElement.appendChild(c);
    document.addEventListener('mousemove', e => { c.style.left=e.clientX-3+'px'; c.style.top=e.clientY-2+'px'; }, true);
    const cap = document.createElement('div'); cap.id='__cap';
    cap.style.cssText='position:fixed;left:calc(50% - 138px);bottom:22px;transform:translateX(-50%);max-width:66%;z-index:2147483646;'+
      'background:rgba(18,40,77,.95);color:#fff;font:600 23px/1.6 "Noto Sans Arabic",sans-serif;padding:10px 24px;border-radius:12px;'+
      'direction:rtl;text-align:center;box-shadow:0 6px 24px rgba(0,0,0,.25);opacity:0;transition:opacity .35s;pointer-events:none';
    document.documentElement.appendChild(cap);
  };
  if (document.readyState === 'loading') document.addEventListener('DOMContentLoaded', add); else add();
})();
"""


def card_html(lines, big=None, small=None, sub=None):
    body = "".join(f"<p>{l}</p>" for l in lines)
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>
    body{{margin:0;height:100vh;background:#193565;color:#fff;font-family:"Noto Sans Arabic",sans-serif;display:flex;align-items:center;
      justify-content:center;overflow:hidden;position:relative}}
    .ros{{position:absolute;left:-160px;top:-120px;width:620px;opacity:.35}}
    .box{{text-align:center;max-width:960px;animation:in .6s ease-out both}}
    @keyframes in{{from{{opacity:0;transform:translateY(10px)}}to{{opacity:1;transform:none}}}}
    h1{{font-size:96px;margin:0 0 6px;line-height:1.2}}
    .sub{{font-size:32px;color:#30D0C8;margin:0 0 20px}}
    p{{font-size:33px;line-height:1.7;margin:6px 0}}
    .small{{font-size:22px;color:#AFC0DE;margin-top:28px}}
    .dim{{color:#AFC0DE;font-size:27px}}
    </style></head><body><img class="ros" src="data:image/svg+xml;base64,{MARK}">
    <div class="box">{f"<h1>{big}</h1>" if big else ""}{f'<p class="sub">{sub}</p>' if sub else ""}{body}{f'<p class="small">{small}</p>' if small else ""}</div></body></html>"""


def phone_html():
    return f"""<!doctype html><html lang="ar" dir="rtl"><head><meta charset="utf-8"><style>
    body{{margin:0;height:100vh;background:#193565;color:#fff;font-family:"Noto Sans Arabic",sans-serif;display:flex;align-items:center;
      justify-content:center;gap:70px;overflow:hidden;position:relative}}
    .ros{{position:absolute;left:-160px;top:-120px;width:620px;opacity:.3}}
    .phone{{width:390px;height:844px;border-radius:46px;border:12px solid #0b1a33;overflow:hidden;background:#fff;
      transform:scale(.78);transform-origin:center;margin:-93px -43px;box-shadow:0 30px 80px rgba(0,0,0,.45)}}
    iframe{{width:390px;height:844px;border:0;display:block}}
    .txt{{max-width:420px}} h2{{font-size:44px;margin:0 0 12px}} p{{font-size:26px;line-height:1.7;color:#cfe0f5;margin:0}}
    </style></head><body><img class="ros" src="data:image/svg+xml;base64,{MARK}">
    <div class="txt"><h2>على الجوال</h2><p>شريط سفلي للأقسام، ويمكن تثبيت الموقع كتطبيق ومشاركة الرسائل إليه من واتساب مباشرة.</p></div>
    <div class="phone"><iframe src="{API}/#/check"></iframe></div></body></html>"""


def local_post(path, body):
    req = urllib.request.Request(API + path, json.dumps(body).encode(), {"Content-Type": "application/json"})
    return json.load(urllib.request.urlopen(req))


def replay_check(key, lang):
    """Local verdicts for the quotes Claude extracted on the live site, with its explanations."""
    cap = LIVE["checks"][key]
    results = []
    for quote, expl in zip(cap["quotes"], cap["explanations"]):
        if lang == "en":
            msg = f'Allah says: "{quote}"'
        else:
            msg = f"قال رسول الله ﷺ: «{quote}»"
        r = local_post("/api/check", {"text": msg, "lang": lang})["results"][0]
        assert r["quote"] == quote, (r["quote"], quote)
        r["explanation"], r["explanation_source"] = expl, "claude"
        results.append(r)
    out = {"extractor": "claude", "results": results, "lang": lang}
    if "transcript" in cap:
        out["transcript"] = cap["transcript"]
    return json.dumps(out, ensure_ascii=False)


def fulfill(route, body, delay):
    time.sleep(delay)
    route.fulfill(status=200, content_type="application/json; charset=utf-8", body=body)


def on_api(route, request):
    url, data = request.url, request.post_data or ""
    if url.endswith("/api/health"):
        h = json.load(urllib.request.urlopen(API + "/api/health"))
        h["claude"] = True
        return fulfill(route, json.dumps(h), 0)
    if url.endswith("/api/check"):
        body = json.loads(data)
        for key, text_key in (("A", "A_TEXT"), ("D", "D_TEXT"), ("F", "F_TEXT")):
            if body.get("text") == LIVE[text_key]:
                return fulfill(route, replay_check(key, body.get("lang", "ar")), 1.6)
    if url.endswith("/api/check-image"):
        return fulfill(route, replay_check("E", "ar"), 3.0)
    if url.endswith("/api/alternatives"):
        return fulfill(route, json.dumps(LIVE["B"], ensure_ascii=False), 2.4)
    if url.endswith("/api/reply"):
        return fulfill(route, json.dumps(LIVE["C"], ensure_ascii=False), 2.2)
    if "/api/search" in url and urllib.parse.parse_qs(urllib.parse.urlparse(url).query).get("q") == [LIVE["G_QUERY"]]:
        return fulfill(route, SEARCH, 2.0)
    route.continue_()


with sync_playwright() as p:
    ctx = p.chromium.launch_persistent_context(
        str(SP / "profile_vid"), headless=True, channel="chromium", accept_downloads=True,
        # In new headless mode the window size includes ~139px of hidden browser UI,
        # so this gives a 1280x720 page that the video captures in full.
        args=[f"--disable-extensions-except={EXT}", f"--load-extension={EXT}", "--window-size=1280,859"],
        no_viewport=True, record_video_dir=str(OUT),
        record_video_size={"width": 1280, "height": 720})
    def ext_worker():
        for w in ctx.service_workers:
            if w.url.startswith("chrome-extension://"):
                return w
        return ctx.wait_for_event("serviceworker", predicate=lambda w: w.url.startswith("chrome-extension://"),
                                  timeout=15000)
    sw = ext_worker()
    T_START = time.time()
    print("extension worker:", sw.url)
    ctx.add_init_script(OVERLAY)
    ctx.route("**/api/**", on_api)
    pg = ctx.pages[0] if ctx.pages else ctx.new_page()

    # the WhatsApp-style screenshot used in the image step (same drawing as on the live capture)
    pg.goto(API + "/api/health")
    png = pg.evaluate(MAKEIMG)
    img_path = SP / "whatsapp.png"
    img_path.write_bytes(base64.b64decode(png.split(",", 1)[1]))
    T0 = time.time()

    def caption(text, wait=0):
        pg.evaluate("""t => { const c=document.getElementById('__cap'); if(!c) return;
            if(!t){c.style.opacity=0;return;}
            const side = document.querySelector('.side') && innerWidth > 900;
            c.style.left = !side ? '50%' : (document.documentElement.dir === 'ltr' ? 'calc(50% + 138px)' : 'calc(50% - 138px)');
            c.textContent=t; c.style.opacity=1; }""", text)
        if wait:
            pg.wait_for_timeout(wait)

    def move_to(locator, click=True):
        loc = pg.locator(locator) if isinstance(locator, str) else locator
        loc.scroll_into_view_if_needed()
        box = loc.bounding_box()
        x, y = box["x"] + box["width"] / 2, box["y"] + box["height"] / 2
        pg.mouse.move(x, y, steps=16)
        pg.wait_for_timeout(200)
        if click:
            pg.mouse.click(x, y)

    def scroll_to(y, ms=800):
        pg.evaluate("y => window.scrollTo({top:y, behavior:'smooth'})", y)
        pg.wait_for_timeout(ms)

    def top_of(selector, nth=0, offset=20):
        return pg.evaluate("([s,n,o]) => document.querySelectorAll(s)[n].getBoundingClientRect().top + window.scrollY - o",
                           [selector, nth, offset])

    def type_check(text, delay=None):
        scroll_to(0, 400)
        move_to("#msg")
        pg.fill("#msg", "")
        pg.type("#msg", text, delay=delay or (10 if len(text) > 80 else 22))
        pg.wait_for_timeout(250)
        move_to("button[type=submit]")
        pg.wait_for_selector(".result", timeout=60000)
        pg.wait_for_timeout(500)

    def nav(view):
        caption("")
        move_to(f'.side .nav a[href="#/{view}"]')
        pg.wait_for_timeout(600)

    # 1. Opening and problem
    pg.set_content(card_html([], big="تبيّن", sub="تحقّق من الآية أو الحديث قبل أن تنشره",
                             small="تحدي الذكاء الاصطناعي في خدمة المحتوى الإسلامي"))
    pg.wait_for_timeout(2700)
    pg.set_content(card_html([
        "رسائل كثيرة تنتشر فيها أحاديث مكذوبة،",
        "وآيات تغيّرت كلماتها، وصور يُنسب فيها كلام إلى النبي ﷺ دون أصل.",
        "<span style='color:#30D0C8'>والتحقق منها يدويًا بطيء ويحتاج خبرة.</span>"]))
    pg.wait_for_timeout(4300)

    # 2. A saying with no source: alternative + polite reply
    pg.goto(API + "/#/check")
    pg.wait_for_selector("#msg")
    pg.wait_for_timeout(700)
    caption("الصق الرسالة كما وصلتك", 1200)
    type_check(LIVE["A_TEXT"])
    scroll_to(top_of(".result", 0, 120))
    caption("قول مشهور لا أصل له في المصادر: ينبَّه ألا يُنشر منسوبًا إلى النبي ﷺ", 3300)
    caption("")
    move_to(pg.get_by_role("button", name="ابحث عن نص صحيح بديل"))
    pg.wait_for_selector(".alts .alt")
    scroll_to(top_of(".alts", 0, 140))
    caption("وبدلًا منه: حديث صحيح وآية بالمعنى نفسه، من المصادر لا من ذاكرة النموذج", 3700)
    caption("")
    move_to(pg.get_by_role("button", name="اكتب ردًا لطيفًا"))
    pg.wait_for_selector(".reply")
    scroll_to(top_of(".reply", 0, 160))
    caption("وردّ لطيف جاهز للإرسال إلى المجموعة، مع زر واتساب", 3600)

    # 3. Two hadiths inside a chatty message
    caption("")
    type_check(LIVE["D_TEXT"], delay=6)
    scroll_to(top_of(".result", 0))
    caption("حديثان وسط تحية ودعاء: يستخرجهما Claude، والحكم من المصادر. الأول في صحيح البخاري", 3900)
    scroll_to(top_of(".result", 1))
    caption("الثاني سقطت منه كلمة «لك»، فتظهر في النص الصحيح من جامع الترمذي", 3600)

    # 4. A screenshot
    caption("")
    scroll_to(0, 400)
    with pg.expect_file_chooser() as fc:
        move_to(".img-btn")
    caption("وصلتك صورة؟ ارفعها أو الصقها", 0)
    fc.value.set_files(str(img_path))
    pg.evaluate("""src => { const o=document.createElement('div'); o.id='__shot';
        o.style.cssText='position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(10,20,40,.55);z-index:2147483640';
        o.innerHTML='<img src="'+src+'" style="width:560px;border-radius:14px;box-shadow:0 20px 60px rgba(0,0,0,.4)">';
        document.body.appendChild(o); }""", png)
    pg.wait_for_timeout(2000)
    pg.evaluate("() => document.getElementById('__shot')?.remove()")
    pg.wait_for_selector(".result", timeout=60000)
    pg.wait_for_timeout(400)
    scroll_to(top_of(".transcript-note", 0, 40))
    caption("يقرأ Claude النص كما هو دون تصحيح، ثم يُفحص: «قرأ» بدل «تعلّم» في صحيح البخاري", 4300)
    caption("")
    with pg.expect_download() as dl:
        move_to(pg.get_by_role("button", name="صورة للمشاركة"))
    card = SP / "share_card.png"
    dl.value.save_as(card)
    card_src = "data:image/png;base64," + base64.b64encode(card.read_bytes()).decode()
    pg.evaluate("""src => { const o=document.createElement('div'); o.id='__shot';
        o.style.cssText='position:fixed;inset:0;display:flex;align-items:center;justify-content:center;background:rgba(10,20,40,.6);z-index:2147483640';
        o.innerHTML='<img src="'+src+'" style="width:470px;border-radius:12px;box-shadow:0 20px 60px rgba(0,0,0,.4)">';
        document.body.appendChild(o); }""", card_src)
    caption("أي نتيجة تُحفظ صورة للحالة أو لوسائل التواصل", 3000)
    pg.evaluate("() => document.getElementById('__shot')?.remove()")

    # 5. English
    caption("")
    scroll_to(0, 400)
    move_to(".side select", click=False)
    pg.select_option(".side select", "en")
    pg.wait_for_timeout(700)
    caption("بالإنجليزية أيضًا: تقارَن بأربع ترجمات معروفة للقرآن", 0)
    type_check(LIVE["F_TEXT"], delay=12)
    scroll_to(top_of(".result", 0))
    pg.wait_for_timeout(3300)
    caption("")
    pg.select_option(".side select", "ar")
    pg.wait_for_timeout(500)

    # 6. Search by topic, popular unsourced sayings
    nav("search")
    move_to(pg.locator(".topics .chip").first)
    pg.wait_for_selector(".hit", timeout=60000)
    caption("ابحث بالموضوع: آيات وأحاديث صحيحة جاهزة للمشاركة", 3200)
    scroll_to(260, 900)
    pg.wait_for_timeout(300)
    nav("myths")
    caption("قائمة بأقوال منتشرة لا أصل لها في الكتب التسعة", 2700)
    nav("learn")
    caption("وحديث اليوم من الأربعين النووية، ودروس قصيرة", 2400)

    # 7. Phone layout
    caption("")
    pg.set_content(phone_html())
    frame = pg.frame_locator("iframe")
    frame.locator("#msg").wait_for()
    pg.wait_for_timeout(900)
    frame.locator(".chip").nth(1).click()
    frame.locator(".result").wait_for(timeout=60000)
    pg.wait_for_timeout(1000)
    frame.locator(".result").first.evaluate("e => window.scrollTo({top: e.getBoundingClientRect().top + scrollY - 70, behavior: 'smooth'})")
    pg.wait_for_timeout(2700)

    # 8. Chrome extension
    pg.goto("http://localhost:8765/")
    pg.wait_for_timeout(600)
    caption("إضافة كروم: حدّد النص في أي صفحة، ثم انقر بالزر الأيمن: تحقّق مع تبيّن", 0)
    post = pg.locator(".post").first.bounding_box()
    sx, ex, yy = post["x"] + post["width"] - 10, post["x"] + 140, post["y"] + 20
    pg.mouse.move(sx, yy, steps=12)
    pg.mouse.down()
    pg.mouse.move(ex, yy + 4, steps=24)
    pg.mouse.up()
    pg.evaluate("""()=>{const r=document.createRange();const n=document.querySelector('.post').firstChild;
        const t=n.textContent;r.setStart(n,0);r.setEnd(n,t.indexOf('»')+1);getSelection().removeAllRanges();getSelection().addRange(r);}""")
    pg.wait_for_timeout(1500)
    sw.evaluate("""async (text) => {
        const [tab] = await chrome.tabs.query({url: "http://localhost:8765/*"});
        await chrome.scripting.executeScript({target:{tabId:tab.id}, files:["render.js","panel.js"]});
        await chrome.scripting.executeScript({target:{tabId:tab.id}, func:()=>globalThis.TabayyanPanel.loading("ar")});
        const res = await fetch("http://localhost:8000/api/check", {method:"POST", headers:{"Content-Type":"application/json"}, body: JSON.stringify({text, lang:"ar"})});
        const data = await res.json();
        await new Promise(r => setTimeout(r, 500));
        await chrome.scripting.executeScript({target:{tabId:tab.id}, func:(d)=>globalThis.TabayyanPanel.show(d), args:[data]});
    }""", "قال رسول الله صلى الله عليه وسلم: «النظافة من الإيمان»")
    caption("النتيجة فوق الصفحة نفسها. وبالزر الأيمن على صورة: تحقّق من الصورة", 4200)

    # 9. How it stays reliable, closing
    pg.set_content(card_html([
        "الحكم مصدره النصوص الموثقة، لا ذاكرة الذكاء الاصطناعي.",
        "<span class='dim'>القرآن الكريم كاملًا، وتسعة من كتب الحديث بدرجات العلماء</span>",
        "<span class='dim'>Claude يستخرج النص ويقرأ الصور ويشرح، وكل ذلك يُتحقق منه</span>",
        "<span class='dim'>99.4% من النصوص الصحيحة تُعرف، و98.1% من المحرّفة تُكشف (100 عينة)</span>",
        "<span style='color:#30D0C8'>لا يُصدر فتاوى، ويحيل إلى أهل العلم</span>"]))
    pg.wait_for_timeout(5300)
    pg.set_content(card_html([], big="تبيّن", sub="تحقّق قبل أن تنشر", small="tabayyan.onrender.com · محمد الزهراني"))
    pg.wait_for_timeout(3000)

    print(f"recorded {time.time() - T0:.1f}s, starts at {T0 - T_START:.2f}s into the video")
    video = pg.video.path()
    ctx.close()
    print(video)
