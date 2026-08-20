const hostEl = document.getElementById("host");
const keyEl = document.getElementById("key");
chrome.storage.local.get({ host: "http://127.0.0.1:8787", key: "desk-local" }).then((s) => {
  hostEl.value = s.host;
  keyEl.value = s.key;
});
document.getElementById("save").onclick = async () => {
  await chrome.storage.local.set({ host: hostEl.value.trim(), key: keyEl.value.trim() });
  chrome.runtime.sendMessage("refresh");
};
