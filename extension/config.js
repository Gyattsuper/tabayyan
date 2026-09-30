// Shared settings for the extension.
// After deploying the API, set the server address in the extension's options page.
export const DEFAULT_API = "http://localhost:8000";

export async function apiBase() {
  const { api } = await chrome.storage.sync.get("api");
  return (api || DEFAULT_API).replace(/\/+$/, "");
}

export async function checkText(text) {
  const res = await fetch(`${await apiBase()}/api/check`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ text, lang: "ar" }),
  });
  if (!res.ok) throw new Error(`HTTP ${res.status}`);
  return res.json();
}
