// Overview page: one card per experiment, and a banner for latched alarms.
// Polls /api/v1/status every 15 s. Needs common.js.
"use strict";

(function () {
  const POLL_MS = 15000;
  const el = window.hc.el;

  function experimentLink(name) {
    const link = el("a", name);
    link.href = "/experiment/" + encodeURIComponent(name);
    return link;
  }

  // Red banner: the latched alarms of every experiment that is publishing.
  // An offline experiment's latches are only "last known" and stay on its card.
  function renderBanner(experiments) {
    const banner = document.getElementById("alarm-banner");
    const list = document.getElementById("alarm-list");
    list.replaceChildren();
    Object.keys(experiments).forEach(function (name) {
      const exp = experiments[name];
      if (!exp.online) return;
      exp.latched.forEach(function (alarm) {
        const item = el("li");
        item.append(experimentLink(name), ": " + alarm);
        list.append(item);
      });
    });
    banner.hidden = list.childElementCount === 0;
  }

  // What a channel's cell shows: {text, title}. The newest point of an offline
  // experiment is old, so it is not shown as the value; it is only the tooltip.
  function valueView(ch, live) {
    if (ch.last === null) return { text: "no data", title: "" };
    const known =
      window.hc.formatValue(ch.last[1]) + (ch.unit && ch.last[1] !== null ? " " + ch.unit : "");
    const when = window.hc.formatTime(ch.last[0]);
    if (!live) {
      return { text: "unknown", title: "Last known: " + known + " at " + when };
    }
    return { text: known, title: "at " + when };
  }

  function channelRows(exp) {
    const body = el("tbody");
    exp.channels.forEach(function (ch) {
      const row = el("tr");
      row.append(el("td", ch.label || ch.name));
      const view = valueView(ch, exp.online);
      const value = el("td", view.text, exp.online ? "value" : "value stale");
      if (view.title) value.title = view.title;
      row.append(value);
      body.append(row);
    });
    return body;
  }

  function renderCard(name, exp, now) {
    const live = exp.online;
    const classes = ["card"];
    if (!live) classes.push("offline");
    if (live && exp.latched.length > 0) classes.push("alarm");
    const card = el("article", null, classes.join(" "));

    const header = el("header");
    header.append(el("span", null, "dot " + (live ? "online" : "offline")));
    const title = el("strong");
    title.append(experimentLink(name));
    header.append(title, " ", el("small", live ? "online" : "offline"));
    card.append(header);

    const heard =
      exp.last_seen === null
        ? "never"
        : window.hc.ago(now - exp.last_seen) + " (" + window.hc.formatTime(exp.last_seen) + ")";
    card.append(el("p", "Last heard: " + heard));

    if (exp.latched.length > 0) {
      const alarms = el("div", null, live ? "latched" : "latched stale");
      alarms.append(
        el("strong", live ? "Active alarms" : "Last known alarms, experiment offline")
      );
      const list = el("ul");
      exp.latched.forEach(function (alarm) {
        list.append(el("li", alarm));
      });
      alarms.append(list);
      card.append(alarms);
    }

    if (exp.channels.length > 0) {
      const table = el("table");
      table.append(channelRows(exp));
      card.append(table);
    } else {
      card.append(el("p", "No channels yet."));
    }
    return card;
  }

  // for the tests of the rendering without a browser
  window.hcOverview = { valueView: valueView };

  async function refresh() {
    try {
      const data = await window.hc.getJSON("/api/v1/status");
      window.hc.clearError();
      const names = Object.keys(data.experiments);
      renderBanner(data.experiments);
      const cards = document.getElementById("cards");
      cards.replaceChildren();
      names.forEach(function (name) {
        cards.append(renderCard(name, data.experiments[name], data.now));
      });
      document.getElementById("empty").hidden = names.length > 0;
    } catch (e) {
      window.hc.showError(e.message);
    }
  }

  document.addEventListener("DOMContentLoaded", function () {
    refresh();
    window.setInterval(refresh, POLL_MS);
  });
})();
