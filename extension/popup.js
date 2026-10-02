import { checkText, getLang, setLang } from "./config.js";

const text = document.getElementById("text");
const go = document.getElementById("go");
const out = document.getElementById("out");
const langSel = document.getElementById("lang");
const { renderAll, CSS, str } = globalThis.TabayyanRender;
let lang = "ar";

function applyLang() {
  const t = str(lang);
  document.documentElement.lang = lang;
  document.documentElement.dir = t.dir;
  langSel.value = lang;
  document.getElementById("name").textContent = t.name;
  text.placeholder = t.placeholder;
  go.textContent = t.check;
  document.getElementById("nofatwa").textContent = t.noFatwa;
  document.getElementById("settings").textContent = t.settings;
}

langSel.addEventListener("change", async () => {
  lang = langSel.value;
  await setLang(lang);
  applyLang();
  if (out.innerHTML && text.value.trim()) check();
});

const style = document.createElement("style");
style.textContent = CSS;
document.head.appendChild(style);

// Prefill with whatever is selected on the current page.
await getLang().then((l) => { lang = l; applyLang(); });
chrome.tabs.query({ active: true, currentWindow: true }, async ([tab]) => {
  try {
    const [{ result }] = await chrome.scripting.executeScript({
      target: { tabId: tab.id },
      func: () => window.getSelection().toString(),
    });
    if (result && result.trim()) {
      text.value = result.trim();
      check();
    }
  } catch {
    /* restricted page: user can paste instead */
  }
});

async function check() {
  const value = text.value.trim();
  if (!value) {
    text.focus();
    return;
  }
  go.disabled = true;
  out.innerHTML = `<p class="msg">${str(lang).loading}</p>`;
  try {
    const data = await checkText(value, lang);
    out.innerHTML = renderAll(data);
  } catch {
    out.innerHTML = `<p class="msg err">${str(lang).netError}</p>`;
  } finally {
    go.disabled = false;
  }
}

go.addEventListener("click", check);
text.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) check();
});
