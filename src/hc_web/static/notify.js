// Browser notifications, opt-in. While a page of the site is open and the user
// has allowed notifications, this polls /api/v1/events and /api/v1/status every
// 15 s (no server-sent events: the server uses synchronous workers) and shows a
// Notification for every new "triggered" event and for every experiment that
// goes offline. Needs common.js.
"use strict";

(function () {
  const POLL_MS = 15000;
  const STORAGE_KEY = "hcweb.lastEventId";
  // An id no event has: asking for the events after it returns none, but the
  // answer still says what the newest id is ("last_id").
  const NO_EVENT_ID = 9007199254740991;

  // The newest event id already notified, shared by all tabs through
  // localStorage so that several tabs do not repeat a notification. Ids grow in
  // the order the events reach the server, so an event that arrives late (the
  // publisher was offline, its clock is behind) is still announced, which a
  // "newer than the newest time" rule would miss.
  let memoryLastId = null;

  function readLastId() {
    try {
      const raw = window.localStorage.getItem(STORAGE_KEY);
      const value = raw === null ? NaN : Number(raw);
      return Number.isInteger(value) && value >= 0 ? value : null;
    } catch (e) {
      return memoryLastId;
    }
  }

  function writeLastId(id) {
    memoryLastId = id;
    try {
      window.localStorage.setItem(STORAGE_KEY, String(id));
    } catch (e) {
      // storage unavailable (private mode): this tab still remembers
    }
  }

  // What to do with an answer of /events: the events to announce and the id to
  // remember. First use (stored is null): start at the newest id, so that old
  // events are not announced. A stored id above the server's newest one means
  // the server's database is a new one: start again from its newest id.
  function planEvents(stored, data) {
    if (stored === null || stored > data.last_id) {
      return { next: data.last_id, fresh: [] };
    }
    const fresh = data.events.filter(function (e) {
      return e.id > stored;
    });
    let next = stored;
    fresh.forEach(function (e) {
      next = Math.max(next, e.id);
    });
    return { next: next, fresh: fresh };
  }

  window.hcNotify = {
    planEvents: planEvents,
    readLastId: readLastId,
    writeLastId: writeLastId,
  };

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
    const asked = readLastId();
    const after = asked === null ? NO_EVENT_ID : asked;
    const data = await window.hc.getJSON("/api/v1/events?after_id=" + encodeURIComponent(after));
    // Read again right before using it: another tab may have been quicker.
    const plan = planEvents(readLastId(), data);
    if (plan.next !== readLastId()) writeLastId(plan.next);
    plan.fresh.forEach(function (e) {
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
