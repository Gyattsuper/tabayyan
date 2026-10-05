// Shared settings for the extension.
// The server address and language can be changed in the extension's options page.
export const DEFAULT_API = "https://tabayyan.onrender.com";

export async function apiBase() {
  const { api } = await chrome.storage.sync.get("api");
  return (api || DEFAULT_API).replace(/\/+$/, "");
}

export async function getLang() {
  const { lang } = await chrome.storage.sync.get("lang");
  return lang === "en" ? "en" : "ar";
}

export async function setLang(lang) {
  await chrome.storage.sync.set({ lang: lang === "en" ? "en" : "ar" });
}

export async function checkText(text, lang) {
  const res = await fetch(`${await apiBase()}/api/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, lang: lang || (await getLang()) }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}

export async function checkImage(src, lang) {
  const body = src.startsWith("data:") ? { image: src } : { image_url: src };
  const res = await fetch(`${await apiBase()}/api/check-image`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ ...body, lang: lang || (await getLang()) }),
  });
  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.detail || `HTTP ${res.status}`);
  return data;
}

// For texts not in the nine collections, add the scholars' rulings from the Dorar al-Saniyyah
// encyclopedia. Best effort: a failure leaves the result as it was.
export async function withDorar(data) {
  const base = await apiBase();
  await Promise.all((data.results || []).map(async (r) => {
    if (r.verdict !== "not_found" || r.quote_lang !== "ar" || r.claimed === "quran") return;
    try {
      const res = await fetch(`${base}/api/dorar?q=${encodeURIComponent(r.quote)}`);
      if (res.ok) r.dorar = await res.json();
    } catch { /* ignore */ }
  }));
  return data;
}
