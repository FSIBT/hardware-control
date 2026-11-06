// Log-out button of the navigation bar (only present for a logged-in user).
"use strict";

(function () {
  document.addEventListener("DOMContentLoaded", function () {
    const button = document.getElementById("logout-button");
    if (!button) return;
    button.addEventListener("click", async function () {
      button.disabled = true;
      try {
        await fetch("/auth/logout", {
          method: "POST",
          credentials: "same-origin",
          headers: { "Content-Type": "application/json" },
          body: "{}",
        });
        window.location.href = "/login";
      } catch (e) {
        const box = document.getElementById("error");
        box.textContent = "Could not reach the server.";
        box.hidden = false;
        button.disabled = false;
      }
    });
  });
})();
