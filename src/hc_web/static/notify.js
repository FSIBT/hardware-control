// Browser notifications, opt-in. While a page of the site is open and the user
// has allowed notifications, this polls /api/v1/events and /api/v1/status every
// 15 s (no server-sent events: the server uses synchronous workers) and shows a
// Notification for every new "triggered" event and for every experiment that
// goes offline. Needs common.js.
"use strict";

(function () {
  const POLL_MS = 15000;
  const STORAGE_KEY = "hcweb.lastEventT";

  // The newest event time already notified, shared by all tabs through
  // localStorage so that several tabs do not repeat a notification.
  let memoryLastSeen = null;

  function readLastSeen() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const value = raw === null ? NaN : Number(raw);
      return Number.isFinite(value) ? value : null;
    } catch (e) {
      return memoryLastSeen;
    }
  }

  function writeLastSeen(t) {
    memoryLastSeen = t;
    try {
      window.localStorage.setItem(STORAGE_KEY, String(t));
    } catch (e) {
      // storage unavailable (private mode): this tab still remembers
    }
  }

  function show(title, body, tag) {
    try {
      const n = new Notification(title, { body: body, tag: tag });
      n.onclick = function () {
        window.focus();
        n.close();
      };
    } catch (e) {
      // some browsers only allow notifications from a service worker
    }
  }

  // --- events ----------------------------------------------------------------

  async function pollEvents() {
    let lastSeen = readLastSeen();
    // First use: start from now, so that old events are not announced.
    const since = lastSeen === null ? Date.now() / 1000 : lastSeen;
    const data = await window.hc.getJSON("/api/v1/events?since=" + encodeURIComponent(since));
    if (lastSeen === null) {
      writeLastSeen(data.now);
      return;
    }
    // Read again right before using it: another tab may have been quicker.
    lastSeen = readLastSeen();
    const fresh = data.events.filter(function (e) {
      return e.t > lastSeen;
    });
    if (fresh.length === 0) return;
    writeLastSeen(fresh[fresh.length - 1].t);
    fresh.forEach(function (e) {
      if (e.action !== "triggered") return;
      show(
        "Alarm: " + e.alarm,
        e.experiment + (e.message ? ": " + e.message : ""),
        "alarm-" + e.experiment + "-" + e.alarm + "-" + e.t
      );
    });
  }

  // --- offline ---------------------------------------------------------------

  let wasOnline = null; // experiment name -> bool, null before the first poll

  async function pollStatus() {
    const data = await window.hc.getJSON("/api/v1/status");
    const previous = wasOnline;
    wasOnline = {};
    Object.keys(data.experiments).forEach(function (name) {
      const online = data.experiments[name].online;
      wasOnline[name] = online;
      if (previous !== null && previous[name] === true && !online) {
        show("Experiment offline", name + " stopped reporting.", "offline-" + name);
      }
    });
  }

  async function poll() {
    try {
      await pollEvents();
      await pollStatus();
    } catch (e) {
      // the page's own polling reports unreachable servers
    }
  }

  let timer = null;

  function start() {
    if (timer !== null) return;
    poll();
    timer = window.setInterval(poll, POLL_MS);
  }

  // --- the opt-in button -----------------------------------------------------

  function setup() {
    const button = document.getElementById("notify-button");
    if (!button) return;
    if (!("Notification" in window)) {
      button.hidden = true;
      return;
    }

    function update() {
      const permission = Notification.permission;
      button.hidden = false;
      if (permission === "granted") {
        button.textContent = "Notifications on";
        button.disabled = true;
        start();
      } else if (permission === "denied") {
        button.textContent = "Notifications blocked in the browser";
        button.disabled = true;
      } else {
        button.textContent = "Enable notifications";
        button.disabled = false;
      }
    }

    button.addEventListener("click", async function () {
      try {
        await Notification.requestPermission();
      } catch (e) {
        // older browsers use a callback; the state is read below anyway
      }
      update();
    });
    update();
  }

  document.addEventListener("DOMContentLoaded", setup);
})();
