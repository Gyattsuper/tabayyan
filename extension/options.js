import { DEFAULT_API, apiBase, getLang, setLang } from "./config.js";

const input = document.getElementById("api");
const status = document.getElementById("status");
const langSel = document.getElementById("lang");

apiBase().then((v) => (input.value = v));
getLang().then((l) => (langSel.value = l));
langSel.addEventListener("change", () => setLang(langSel.value));

document.getElementById("save").addEventListener("click", async () => {
  const value = input.value.trim().replace(/\/+$/, "") || DEFAULT_API;
  await chrome.storage.sync.set({ api: value });
  status.textContent = "جارٍ اختبار الاتصال…";
  try {
    const res = await fetch(`${value}/api/health`);
    status.textContent = res.ok ? "تم الحفظ، والخادم يعمل." : `تم الحفظ، لكن الخادم ردّ بخطأ ${res.status}.`;
  } catch {
    status.textContent = "تم الحفظ، لكن تعذر الوصول إلى الخادم. تحقق من العنوان.";
  }
});
