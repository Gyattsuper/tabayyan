import { checkText } from "./config.js";

const text = document.getElementById("text");
const go = document.getElementById("go");
const out = document.getElementById("out");
const { render, CSS } = globalThis.TabayyanRender;

const style = document.createElement("style");
style.textContent = CSS;
document.head.appendChild(style);

// Prefill with whatever is selected on the current page.
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
  out.innerHTML = `<p class="msg">نبحث في القرآن الكريم وكتب الحديث…</p>`;
  try {
    const data = await checkText(value);
    out.innerHTML = data.results.map(render).join("");
  } catch {
    out.innerHTML = `<p class="msg err">تعذر الاتصال بخادم تبيّن. تأكد من عنوان الخادم في الإعدادات.</p>`;
  } finally {
    go.disabled = false;
  }
}

go.addEventListener("click", check);
text.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && (e.ctrlKey || e.metaKey)) check();
});
