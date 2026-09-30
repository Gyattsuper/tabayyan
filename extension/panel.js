// Injected into the page: shows a small panel with the result, isolated in a
// shadow root so the page's styles can't break it (and ours can't break the page).
(function () {
  if (globalThis.TabayyanPanel) return;
  const { render, CSS, esc } = globalThis.TabayyanRender;

  let host, body;
  function ensure() {
    if (host && document.contains(host)) return;
    host = document.createElement("div");
    host.style.cssText = "position:fixed;z-index:2147483647;top:16px;left:16px;width:380px;max-width:calc(100vw - 32px)";
    const root = host.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${CSS}
      .card{background:#fff;border-radius:12px;box-shadow:0 10px 30px rgba(25,53,101,.25);overflow:hidden;max-height:80vh;display:flex;flex-direction:column}
      .bar{background:#193565;color:#fff;display:flex;align-items:center;justify-content:space-between;padding:8px 12px;direction:rtl;font:600 15px system-ui,sans-serif}
      .bar button{background:none;border:0;color:#fff;font-size:20px;cursor:pointer;line-height:1}
      .body{padding:4px 10px 12px;overflow:auto}
      .msg{font:14px system-ui,sans-serif;color:#5d6b82;direction:rtl;padding:12px 4px}
      .msg.err{color:#c23b3b}</style>
      <div class="card" role="dialog" aria-label="نتيجة تبيّن">
        <div class="bar"><span>تبيّن</span><button aria-label="إغلاق">×</button></div>
        <div class="body"></div>
      </div>`;
    root.querySelector("button").onclick = () => host.remove();
    body = root.querySelector(".body");
    document.documentElement.appendChild(host);
    document.addEventListener("keydown", (e) => e.key === "Escape" && host?.remove());
  }

  globalThis.TabayyanPanel = {
    loading() {
      ensure();
      body.innerHTML = `<p class="msg">نبحث في القرآن الكريم وكتب الحديث…</p>`;
    },
    error(message) {
      ensure();
      body.innerHTML = `<p class="msg err">${esc(message)}</p>`;
    },
    show(data) {
      ensure();
      body.innerHTML = data.results.map(render).join("");
    },
  };
})();
