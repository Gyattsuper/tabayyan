import { checkImage, checkText, getLang, withDorar } from "./config.js";

const MENU_ID = "tabayyan-check";
const IMAGE_MENU_ID = "tabayyan-check-image";

chrome.runtime.onInstalled.addListener(() => {
  chrome.contextMenus.create({ id: MENU_ID, title: "تحقّق مع تبيّن | Check with Tabayyan", contexts: ["selection"] });
  chrome.contextMenus.create({
    id: IMAGE_MENU_ID, title: "تحقّق من الصورة مع تبيّن | Check image with Tabayyan", contexts: ["image"],
  });
});

async function run(tabId, fn, args = []) {
  await chrome.scripting.executeScript({ target: { tabId }, func: fn, args });
}

chrome.contextMenus.onClicked.addListener(async (info, tab) => {
  if (!tab?.id || ![MENU_ID, IMAGE_MENU_ID].includes(info.menuItemId)) return;
  const isImage = info.menuItemId === IMAGE_MENU_ID;
  const text = (info.selectionText || "").trim();
  try {
    await chrome.scripting.executeScript({ target: { tabId: tab.id }, files: ["render.js", "panel.js"] });
  } catch {
    return; // pages like chrome:// don't allow scripts; the popup still works there
  }
  const lang = await getLang();
  await run(tab.id, (l, img) => globalThis.TabayyanPanel.loading(l, img), [lang, isImage]);
  try {
    const data = await withDorar(isImage ? await checkImage(info.srcUrl, lang) : await checkText(text, lang));
    await run(tab.id, (d) => globalThis.TabayyanPanel.show(d), [data]);
  } catch (e) {
    const msg = isImage && e && !/^HTTP/.test(e.message) ? e.message : null;
    await run(tab.id, (l, m) => globalThis.TabayyanPanel.error(l, m), [lang, msg]);
  }
});
