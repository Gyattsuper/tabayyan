// Injected into the page: shows a small panel with the result, isolated in a
// shadow root so the page's styles can't break it (and ours can't break the page).
(function () {
  if (globalThis.TabayyanPanel) return;
  const { renderAll, CSS, esc, str } = globalThis.TabayyanRender;

  let host, body, root;
  function ensure(lang) {
    const t = str(lang);
    if (host && document.contains(host)) {
      root.querySelector(".bar").dir = t.dir;
      root.querySelector(".bar span").textContent = t.name;
      root.querySelector(".bar button").setAttribute("aria-label", t.close);
      return;
    }
    host = document.createElement("div");
    host.style.cssText = "position:fixed;z-index:2147483647;top:16px;left:16px;width:380px;max-width:calc(100vw - 32px)";
    root = host.attachShadow({ mode: "open" });
    root.innerHTML = `<style>${CSS}
      .card{background:#fff;border-radius:12px;box-shadow:0 10px 30px rgba(25,53,101,.25);overflow:hidden;max-height:80vh;display:flex;flex-direction:column}
      .bar{background:#193565;color:#fff;display:flex;align-items:center;justify-content:space-between;padding:8px 12px;font:600 15px system-ui,sans-serif}
      .bar button{background:none;border:0;color:#fff;font-size:20px;cursor:pointer;line-height:1}
      .body{padding:4px 10px 12px;overflow:auto}
      .msg{font:14px system-ui,sans-serif;color:#5d6b82;padding:12px 4px}
      .msg.err{color:#c23b3b}</style>
      <div class="card" role="dialog" aria-label="${t.result}">
        <div class="bar" dir="${t.dir}"><span>${t.name}</span><button aria-label="${t.close}">×</button></div>
        <div class="body"></div>
      </div>`;
    root.querySelector("button").onclick = () => host.remove();
    body = root.querySelector(".body");
    document.documentElement.appendChild(host);
    document.addEventListener("keydown", (e) => e.key === "Escape" && host?.remove());
  }

  globalThis.TabayyanPanel = {
    loading(lang, image) {
      ensure(lang);
      body.innerHTML = `<p class="msg" dir="${str(lang).dir}">${image ? str(lang).reading : str(lang).loading}</p>`;
    },
    error(lang, message) {
      ensure(lang);
      body.innerHTML = `<p class="msg err" dir="${str(lang).dir}">${esc(message || str(lang).netError)}</p>`;
    },
    show(data) {
      ensure(data.lang);
      body.innerHTML = renderAll(data);
    },
  };
})();
