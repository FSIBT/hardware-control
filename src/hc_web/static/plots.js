// Experiment page: one Plotly plot per channel with a shared x axis.
// Sampled channels are lines, state channels are categorical steps ("hv").
// Offline intervals (gaps) are shaded, and a line is broken at every gap and at
// every unknown value. Alarm events are vertical markers. Auto-refreshes every
// 30 s and then fetches only what is newer than the data it already has.
// Needs common.js and Plotly.
//
// Traces are plain "scatter" (SVG), never the WebGL variant: that one compiles
// code at runtime through regl, which the page's Content-Security-Policy (no
// 'unsafe-eval') would block.
"use strict";

(function () {
  const POLL_MS = 30000;
  const MAX_LINE_POINTS = 4000; // per sampled channel, then min/max decimation
  const MARKERS_BELOW = 300; // draw point markers on short series
  const MAX_ALARM_LABELS = 30;
  const DEFAULT_RANGE = 7 * 86400;
  const TIME = "%{x|%Y-%m-%d %H:%M:%S}<br>";

  // --- series building (no DOM) ----------------------------------------------

  function pad(n, width) {
    return String(n).padStart(width, "0");
  }

  // An axis value for unix time t: the browser's local wall-clock time as text.
  // Plotly never applies a time zone to such a string (what it does with a bare
  // number differs between versions), so the axis shows local time.
  function toX(t) {
    const d = new Date(t * 1000);
    return (
      d.getFullYear() + "-" + pad(d.getMonth() + 1, 2) + "-" + pad(d.getDate(), 2) + " " +
      pad(d.getHours(), 2) + ":" + pad(d.getMinutes(), 2) + ":" + pad(d.getSeconds(), 2) +
      "." + pad(d.getMilliseconds(), 3)
    );
  }

  // Unknown intervals [start, end] (end null: still offline), old ones plus the
  // ones of a later fetch that covers [since, now]. Everything of the old list
  // from `since` on is replaced; what is left joins the new gaps if they touch.
  function mergeGaps(old, fresh, since) {
    const all = [];
    old.forEach(function (g) {
      if (g[0] >= since) return;
      all.push([g[0], g[1] === null || g[1] > since ? since : g[1]]);
    });
    fresh.forEach(function (g) {
      all.push([g[0], g[1]]);
    });
    all.sort(function (a, b) {
      return a[0] - b[0];
    });
    const out = [];
    all.forEach(function (g) {
      const last = out[out.length - 1];
      if (last && last[1] === null) return; // inside the open gap
      if (last && g[0] <= last[1]) {
        last[1] = g[1] === null ? null : Math.max(last[1], g[1]);
      } else {
        out.push([g[0], g[1]]);
      }
    });
    return out;
  }

  // Order by time. At the same time a point comes after the end of a gap and
  // before the start of one.
  function byTime(a, b) {
    return a[0] - b[0] || a[2] - b[2];
  }

  // A sampled series as [t, v] pairs where v is null at every gap boundary and
  // at every unknown value, so that the line is broken there.
  function sampledSeries(points, gaps) {
    const items = points.map(function (p) {
      return [p[0], p[1], 0];
    });
    gaps.forEach(function (g) {
      items.push([g[0], null, 1]);
      if (g[1] !== null) items.push([g[1], null, -1]);
    });
    items.sort(byTime);
    const out = [];
    items.forEach(function (p) {
      const last = out[out.length - 1];
      if (p[1] === null && last && last[1] === null) return;
      out.push([p[0], p[1]]);
    });
    return out;
  }

  // Keep a long line drawable: per run of known values, the minimum and the
  // maximum of each bucket. Unknown values (null) stay where they are.
  function decimate(points, limit) {
    if (points.length <= limit) return points;
    const size = Math.ceil(points.length / (limit / 2));
    const out = [];
    let i = 0;
    while (i < points.length) {
      if (points[i][1] === null) {
        out.push(points[i]);
        i += 1;
        continue;
      }
      let lo = points[i];
      let hi = points[i];
      let j = i;
      while (j < points.length && points[j][1] !== null && j - i < size) {
        if (points[j][1] < lo[1]) lo = points[j];
        if (points[j][1] > hi[1]) hi = points[j];
        j += 1;
      }
      if (lo === hi) out.push(lo);
      else if (lo[0] <= hi[0]) out.push(lo, hi);
      else out.push(hi, lo);
      i = j;
    }
    return out;
  }

  // A state channel as [t, "value"] steps up to `endT`. `before` is the value
  // in force at `since`. Where the value becomes unknown (a null point or the
  // start of a gap) the previous value is held up to that moment, then null
  // breaks the line.
  function stateSeries(before, points, gaps, since, endT) {
    const items = [];
    if (before && before[1] !== null) items.push([since, String(before[1]), 0]);
    points.forEach(function (p) {
      items.push([p[0], p[1] === null ? null : String(p[1]), 0]);
    });
    gaps.forEach(function (g) {
      items.push([g[0], null, 1]);
    });
    items.sort(byTime);
    const out = [];
    let current = null;
    items.forEach(function (item) {
      if (item[1] === null) {
        if (current !== null) {
          out.push([item[0], current]);
          out.push([item[0], null]);
          current = null;
        }
      } else {
        out.push([item[0], item[1]]);
        current = item[1];
      }
    });
    if (current !== null && endT > out[out.length - 1][0]) out.push([endT, current]);
    return out;
  }

  window.hcSeries = {
    toX: toX,
    mergeGaps: mergeGaps,
    sampledSeries: sampledSeries,
    stateSeries: stateSeries,
    decimate: decimate,
  };

  // --- page --------------------------------------------------------------------

  if (typeof document === "undefined" || !document.getElementById("plots")) return;

  const el = window.hc.el;
  const container = document.getElementById("plots");
  const experiment = container.dataset.experiment;

  const model = {
    channels: [], // {name, full, kind, unit, label, points, before, categories, div}
    gaps: [],
    events: [],
    range: DEFAULT_RANGE,
    viewRange: null, // the x range the user zoomed to, else the window follows now
    clockOffset: 0, // server time minus browser time
    interval: 60,
    online: false,
  };

  function serverNow() {
    return Date.now() / 1000 + model.clockOffset;
  }

  function cssVar(name, fallback) {
    const value = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
    return value || fallback;
  }

  // Plotly renders a small HTML subset in titles and hover text: show server
  // text literally.
  function plain(text) {
    return String(text).replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  }

  function windowStart() {
    return serverNow() - model.range;
  }

  // --- data ----------------------------------------------------------------------

  function fetchUrls(since) {
    const channels = model.channels.map(function (c) {
      return experiment + "/" + c.name;
    });
    return [
      "/api/v1/data?channels=" + encodeURIComponent(channels.join(",")) + "&since=" + since,
      "/api/v1/events?since=" + since,
    ];
  }

  function noteCategory(ch, v) {
    if (v === null || v === undefined) return;
    const text = String(v);
    if (ch.categories.indexOf(text) < 0) ch.categories.push(text);
  }

  // Merge a response into the model. `replace`: the response covers the whole
  // window; otherwise it covers [since, now] and replaces only that part.
  function apply(data, events, since, replace) {
    model.clockOffset = data.now - Date.now() / 1000;
    const info = data.experiments[experiment];
    model.online = info.online;
    model.interval = info.timeout / 3;
    model.lastSeen = info.last_seen;
    model.latched = info.latched;
    model.gaps = replace ? info.gaps : mergeGaps(model.gaps, info.gaps, since);

    model.channels.forEach(function (ch) {
      const fresh = data.channels[ch.full];
      if (replace) {
        ch.points = fresh.points;
        ch.before = fresh.before;
        ch.categories = [];
        noteCategory(ch, fresh.before && fresh.before[1]);
      } else {
        ch.points = ch.points
          .filter(function (p) {
            return p[0] < since;
          })
          .concat(fresh.points);
      }
      fresh.points.forEach(function (p) {
        noteCategory(ch, p[1]);
      });
    });

    const mine = events.events.filter(function (e) {
      return e.experiment === experiment;
    });
    model.events = replace
      ? mine
      : model.events
          .filter(function (e) {
            return e.t < since;
          })
          .concat(mine);
    if (!replace) trim(windowStart());
  }

  // Forget what has slid out of the window; a state channel keeps the last
  // dropped value as the one in force at the new start.
  function trim(start) {
    model.channels.forEach(function (ch) {
      let n = 0;
      while (n < ch.points.length && ch.points[n][0] < start) n += 1;
      if (n === 0) return;
      if (ch.kind === "state") ch.before = ch.points[n - 1];
      ch.points = ch.points.slice(n);
    });
    model.gaps = model.gaps.filter(function (g) {
      return g[1] === null || g[1] >= start;
    });
    model.events = model.events.filter(function (e) {
      return e.t >= start;
    });
  }

  function newestPoint() {
    let newest = null;
    model.channels.forEach(function (ch) {
      if (ch.points.length === 0) return;
      const t = ch.points[ch.points.length - 1][0];
      if (newest === null || t > newest) newest = t;
    });
    return newest;
  }

  // --- drawing -------------------------------------------------------------------

  function drawStatus() {
    const dot = document.getElementById("status-dot");
    dot.className = "dot " + (model.online ? "online" : "offline");
    let text = model.online ? "online" : "offline";
    if (model.lastSeen !== null && model.lastSeen !== undefined) {
      text += ", last heard " + window.hc.ago(serverNow() - model.lastSeen);
    }
    if (!model.online && model.latched.length > 0) {
      text += ". Last known alarms: " + model.latched.join(", ");
    }
    document.getElementById("status-text").textContent = text;

    const banner = document.getElementById("alarm-banner");
    const list = document.getElementById("alarm-list");
    list.replaceChildren();
    if (model.online) {
      model.latched.forEach(function (alarm) {
        list.append(el("li", alarm));
      });
    }
    banner.hidden = list.childElementCount === 0;
  }

  function colours() {
    return {
      text: cssVar("--pico-color", "#373c44"),
      grid: cssVar("--pico-muted-border-color", "#e7eaf0"),
      line: cssVar("--pico-primary", "#0172ad"),
      muted: cssVar("--pico-muted-color", "#7b8495"),
      alarm: cssVar("--pico-del-color", "#c62828"),
    };
  }

  function markerShapes(now, colour) {
    const shapes = [];
    const end = toX(now);
    model.gaps.forEach(function (g) {
      shapes.push({
        type: "rect",
        xref: "x",
        yref: "paper",
        x0: toX(g[0]),
        x1: g[1] === null ? end : toX(g[1]),
        y0: 0,
        y1: 1,
        fillcolor: colour.muted,
        opacity: 0.25,
        line: { width: 0 },
        layer: "below",
      });
    });
    model.events.forEach(function (e) {
      shapes.push({
        type: "line",
        xref: "x",
        yref: "paper",
        x0: toX(e.t),
        x1: toX(e.t),
        y0: 0,
        y1: 1,
        line: {
          color: e.action === "triggered" ? colour.alarm : colour.muted,
          width: 1.5,
          dash: e.action === "triggered" ? "solid" : "dot",
        },
      });
    });
    return shapes;
  }

  function alarmLabels(colour) {
    return model.events
      .filter(function (e) {
        return e.action === "triggered";
      })
      .slice(-MAX_ALARM_LABELS)
      .map(function (e) {
        return {
          x: toX(e.t),
          xref: "x",
          y: 1,
          yref: "paper",
          text: plain(e.alarm),
          textangle: -90,
          showarrow: false,
          xanchor: "right",
          yanchor: "top",
          font: { size: 10, color: colour.alarm },
        };
      });
  }

  function traceFor(ch, now, colour) {
    const unit = ch.unit ? " " + plain(ch.unit) : "";
    if (ch.kind === "state") {
      const steps = stateSeries(ch.before, ch.points, model.gaps, windowStart(), now);
      return {
        type: "scatter",
        mode: "lines+markers",
        line: { shape: "hv", color: colour.line, width: 1.5 },
        marker: { size: 4, color: colour.line },
        connectgaps: false,
        x: steps.map(function (p) {
          return toX(p[0]);
        }),
        y: steps.map(function (p) {
          return p[1];
        }),
        hovertemplate: TIME + "%{y}<extra></extra>",
      };
    }
    const line = decimate(sampledSeries(ch.points, model.gaps), MAX_LINE_POINTS);
    return {
      type: "scatter",
      mode: line.length <= MARKERS_BELOW ? "lines+markers" : "lines",
      line: { color: colour.line, width: 1.5 },
      marker: { size: 4, color: colour.line },
      connectgaps: false,
      x: line.map(function (p) {
        return toX(p[0]);
      }),
      y: line.map(function (p) {
        return p[1];
      }),
      hovertemplate: TIME + "%{y}" + unit + "<extra></extra>",
    };
  }

  function drawPlots() {
    const colour = colours();
    const now = serverNow();
    const shapes = markerShapes(now, colour);
    model.channels.forEach(function (ch, index) {
      const layout = {
        height: ch.kind === "state" ? 200 : 240,
        margin: { l: 60, r: 20, t: 10, b: 30 },
        showlegend: false,
        paper_bgcolor: "rgba(0,0,0,0)",
        plot_bgcolor: "rgba(0,0,0,0)",
        font: { color: colour.text },
        xaxis: {
          type: "date",
          range: model.viewRange || [toX(windowStart()), toX(now)],
          gridcolor: colour.grid,
        },
        yaxis: { automargin: true, gridcolor: colour.grid, fixedrange: true },
        shapes: shapes,
        // the alarm names are written on the first plot only
        annotations: index === 0 ? alarmLabels(colour) : [],
      };
      if (ch.kind === "state") {
        layout.yaxis.type = "category";
        layout.yaxis.categoryorder = "array";
        layout.yaxis.categoryarray = ch.categories;
      }
      const config = { displaylogo: false, responsive: true };
      Plotly.react(ch.div, [traceFor(ch, now, colour)], layout, config).then(function () {
        bindZoomSync(ch.div);
      });
    });
  }

  // The x axes of all plots move together. What the user zoomed to is kept in
  // model.viewRange and passed back on every redraw (the window of an unzoomed
  // plot slides along with the clock).
  let syncing = false;

  function bindZoomSync(div) {
    if (div.dataset.bound) return;
    div.dataset.bound = "1";
    div.on("plotly_relayout", async function (ev) {
      if (syncing) return;
      let update = null;
      if (ev["xaxis.range[0]"] !== undefined) {
        update = { "xaxis.range": [ev["xaxis.range[0]"], ev["xaxis.range[1]"]] };
      } else if (ev["xaxis.range"]) {
        update = { "xaxis.range": ev["xaxis.range"] };
      } else if (ev["xaxis.autorange"]) {
        update = { "xaxis.autorange": true };
      }
      if (update === null) return;
      if (update["xaxis.autorange"]) {
        // double click: back to the whole window
        model.viewRange = null;
        drawPlots();
        return;
      }
      model.viewRange = update["xaxis.range"];
      syncing = true;
      try {
        await Promise.all(
          model.channels
            .filter(function (ch) {
              return ch.div !== div;
            })
            .map(function (ch) {
              return Plotly.relayout(ch.div, update);
            })
        );
      } finally {
        syncing = false;
      }
    });
  }

  function updateCsvLink() {
    const channels = model.channels.map(function (c) {
      return experiment + "/" + c.name;
    });
    document.getElementById("csv-link").href =
      "/api/v1/data.csv?channels=" +
      encodeURIComponent(channels.join(",")) +
      "&since=" +
      windowStart().toFixed(3) +
      "&until=" +
      serverNow().toFixed(3);
  }

  function drawRangeButtons() {
    document.querySelectorAll("#range-buttons button").forEach(function (button) {
      const active = Number(button.dataset.seconds) === model.range;
      button.classList.toggle("outline", !active);
      button.setAttribute("aria-pressed", active ? "true" : "false");
    });
  }

  // --- loading ---------------------------------------------------------------------

  async function load(replace) {
    let since = windowStart();
    if (!replace) {
      const newest = newestPoint();
      // a little before the newest point, in case a publisher batch was split
      if (newest !== null) since = Math.max(since, newest - model.interval);
    }
    const urls = fetchUrls(since);
    const results = await Promise.all(urls.map(window.hc.getJSON));
    apply(results[0], results[1], since, replace);
    drawStatus();
    drawPlots();
    updateCsvLink();
  }

  async function refresh(replace) {
    try {
      await load(replace);
      window.hc.clearError();
    } catch (e) {
      window.hc.showError(e.message);
    }
  }

  function addPlotSlot(ch) {
    const section = el("section");
    const title = ch.label || ch.name;
    section.append(el("h3", ch.unit ? title + " (" + ch.unit + ")" : title, "plot-title"));
    ch.div = el("div", null, "plot");
    section.append(ch.div);
    container.append(section);
  }

  async function start() {
    document.querySelectorAll("#range-buttons button").forEach(function (button) {
      button.addEventListener("click", function () {
        model.range = Number(button.dataset.seconds);
        model.viewRange = null;
        drawRangeButtons();
        refresh(true);
      });
    });
    drawRangeButtons();

    let status;
    try {
      status = await window.hc.getJSON("/api/v1/status");
    } catch (e) {
      window.hc.showError(e.message);
      return;
    }
    model.clockOffset = status.now - Date.now() / 1000;
    const info = status.experiments[experiment];
    const channels = info ? info.channels : [];
    document.getElementById("empty").hidden = channels.length > 0;
    channels.forEach(function (c) {
      const ch = {
        name: c.name,
        full: experiment + "/" + c.name,
        kind: c.kind,
        unit: c.unit,
        label: c.label,
        points: [],
        before: null,
        categories: [],
        div: null,
      };
      model.channels.push(ch);
      addPlotSlot(ch);
    });
    if (channels.length === 0) return;

    await refresh(true);
    window.setInterval(function () {
      refresh(false);
    }, POLL_MS);
    // follow the browser's light/dark setting
    window.matchMedia("(prefers-color-scheme: dark)").addEventListener("change", drawPlots);
  }

  document.addEventListener("DOMContentLoaded", start);
})();
