const DEFAULTS = { host: "http://127.0.0.1:8787", key: "desk-local" };

async function settings() {
  const s = await chrome.storage.local.get(DEFAULTS);
  return { ...DEFAULTS, ...s };
}

async function pullAndPush() {
  const { host, key } = await settings();
  let summary = null;
  try {
    const r = await fetch("https://cursor.com/api/usage-summary", {
      credentials: "include",
      headers: { Accept: "application/json" },
    });
    if (!r.ok) throw new Error("cursor " + r.status);
    summary = await r.json();
  } catch (e) {
    console.warn("cursor fetch", e);
    return;
  }
  const plan = (summary.individualUsage && summary.individualUsage.plan) || {};
  const body = {
    autoPercentUsed: plan.autoPercentUsed ?? summary.autoPercentUsed ?? summary.auto_percent_used,
    apiPercentUsed: plan.apiPercentUsed ?? summary.apiPercentUsed ?? summary.api_percent_used,
    totalPercentUsed: plan.totalPercentUsed ?? summary.totalPercentUsed,
    billingCycleEnd: summary.billingCycleEnd ?? summary.cycleEnd,
  };
  await fetch(host + "/v1/cursor?key=" + encodeURIComponent(key), {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(body),
  });
}

chrome.runtime.onInstalled.addListener(() => {
  chrome.alarms.create("desk-cursor", { periodInMinutes: 5 });
  pullAndPush();
});
chrome.alarms.onAlarm.addListener((a) => {
  if (a.name === "desk-cursor") pullAndPush();
});
chrome.runtime.onMessage.addListener((msg, _s, send) => {
  if (msg === "refresh") pullAndPush().then(() => send({ ok: true }));
  return true;
});
