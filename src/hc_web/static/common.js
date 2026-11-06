// Helpers shared by the viewer pages (overview and experiment plots).
// Everything from the server is put on the page with textContent and DOM
// construction, never as HTML.
"use strict";

(function () {
  function el(tag, text, className) {
    const node = document.createElement(tag);
    if (text !== undefined && text !== null) node.textContent = String(text);
    if (className) node.className = className;
    return node;
  }

  function showError(message) {
    const box = document.getElementById("error");
    box.textContent = message;
    box.hidden = false;
  }

  function clearError() {
    document.getElementById("error").hidden = true;
  }

  // GET a JSON route with the session cookie. A 401 means the session is gone.
  async function getJSON(url) {
    let response;
    try {
      response = await fetch(url, { credentials: "same-origin" });
    } catch (e) {
      throw new Error("Could not reach the server.");
    }
    if (response.status === 401) {
      window.location.href = "/login";
      throw new Error("Please log in again.");
    }
    let data = {};
    try {
      data = await response.json();
    } catch (e) {
      // not JSON: fall through to the status message
    }
    if (!response.ok) {
      throw new Error(data.error || "Request failed (" + response.status + ").");
    }
    return data;
  }

  function formatTime(t) {
    if (t === null || t === undefined) return "never";
    return new Date(t * 1000).toLocaleString();
  }

  // "12 s ago", "3 min ago", ...
  function ago(seconds) {
    if (seconds < 0) seconds = 0;
    if (seconds < 90) return Math.round(seconds) + " s ago";
    if (seconds < 5400) return Math.round(seconds / 60) + " min ago";
    if (seconds < 172800) return Math.round(seconds / 3600) + " h ago";
    return Math.round(seconds / 86400) + " days ago";
  }

  // A number with at most 6 significant digits; unknown (null) is "unknown".
  function formatValue(v) {
    if (v === null || v === undefined) return "unknown";
    if (typeof v === "number") return String(Number(v.toPrecision(6)));
    return String(v);
  }

  window.hc = {
    el: el,
    showError: showError,
    clearError: clearError,
    getJSON: getJSON,
    formatTime: formatTime,
    ago: ago,
    formatValue: formatValue,
  };
})();
