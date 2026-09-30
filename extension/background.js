import { checkText } from "./config.js";

const MENU_ID = "tabayyan-check";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: MENU_ID, title: "تحقّق مع تبيّن", contexts: ["selection"] });
});

async function run(tabId, fn, args = []) {
  await chrome.scripting.executeScript({ target: { tabId }, func: fn, args });
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (info.menuItemId !== MENU_ID || !tab?.id) return;
  const text = (info.selectionText || "").trim();
  try {
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["render.js", "panel.js"] });
  } catch {
    return; // pages like chrome:// don't allow scripts; the popup still works there
  }
  await run(tab.id, () => globalThis.TabayyanPanel.loading());
  try {
    const data = await checkText(text);
    await run(tab.id, (d) => globalThis.TabayyanPanel.show(d), [data]);
  } catch {
    await run(tab.id, (m) => globalThis.TabayyanPanel.error(m), [
      "تعذر الاتصال بخادم تبيّن. تأكد من عنوان الخادم في إعدادات الإضافة.",
    ]);
  }
});
