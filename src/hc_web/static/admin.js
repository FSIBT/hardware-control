// Admin page. Talks to the JSON routes under /admin/api/.
// Everything from the server is put on the page with textContent and DOM
// construction, never as HTML.
"use strict";

(function () {
  const API = "/admin/api/";
  let currentUser = null;

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

  function formatTime(t) {
    if (t === null || t === undefined) return "never";
    return new Date(t * 1000).toLocaleString();
  }

  async function request(method, path, body) {
    const options = { method: method, credentials: "same-origin" };
    if (method === "POST") {
      options.headers = { "Content-Type": "application/json" };
      options.body = JSON.stringify(body || {});
    }
    let response;
    try {
      response = await fetch(API + path, options);
    } catch (e) {
      throw new Error("Could not reach the server.");
    }
    let data = {};
    try {
      data = await response.json();
    } catch (e) {
      // not JSON: fall through to the status message
    }
    if (response.status === 401) {
      window.location.href = "/login";
      throw new Error("Please log in again.");
    }
    if (!response.ok) {
      throw new Error(data.error || "Request failed (" + response.status + ").");
    }
    return data;
  }

  // Run an action; report a failure on the page instead of throwing.
  async function run(action) {
    clearError();
    try {
      await action();
    } catch (e) {
      showError(e.message || "Something went wrong.");
    }
  }

  function replaceRows(id, rows, emptyText, columns) {
    const body = document.getElementById(id);
    body.replaceChildren();
    if (rows.length === 0) {
      const tr = el("tr");
      const td = el("td", emptyText);
      td.colSpan = columns;
      tr.appendChild(td);
      body.appendChild(tr);
      return body;
    }
    return body;
  }

  function button(label, onClick, className) {
    const b = el("button", label, className);
    b.type = "button";
    b.addEventListener("click", function () {
      b.disabled = true;
      run(onClick).then(function () { b.disabled = false; });
    });
    return b;
  }

  // --- users ---------------------------------------------------------------

  function credentialsText(credentials) {
    if (credentials.length === 0) return "none";
    return credentials
      .map(function (c) {
        return c.label + " (added " + formatTime(c.created) +
          ", last used " + formatTime(c.last_used) + ")";
      })
      .join("; ");
  }

  async function changeRole(user, role) {
    await request("POST", "users/" + user.id + "/role", { role: role });
    await loadUsers();
  }

  async function removeUser(user) {
    if (!window.confirm("Delete user " + user.name + "? Their passkeys are removed.")) {
      return;
    }
    await request("POST", "users/" + user.id + "/delete", {});
    await loadUsers();
  }

  async function loadUsers() {
    const data = await request("GET", "users");
    currentUser = data.current_user;
    const body = replaceRows("users-body", data.users, "No users.", 4);
    data.users.forEach(function (user) {
      const tr = el("tr");
      tr.appendChild(el("td", user.name + (user.id === currentUser ? " (you)" : "")));
      tr.appendChild(el("td", user.role));
      tr.appendChild(el("td", credentialsText(user.credentials)));
      const actions = el("td");
      const other = user.role === "admin" ? "viewer" : "admin";
      actions.appendChild(button("Make " + other, function () {
        return changeRole(user, other);
      }, "outline secondary"));
      actions.appendChild(button("Delete", function () {
        return removeUser(user);
      }, "outline danger"));
      tr.appendChild(actions);
      body.appendChild(tr);
    });
  }

  // --- invites -------------------------------------------------------------

  function showSecret(boxId, valueId, value) {
    document.getElementById(valueId).textContent = value;
    document.getElementById(boxId).hidden = false;
  }

  async function copy(valueId, copyButton) {
    const text = document.getElementById(valueId).textContent;
    try {
      await navigator.clipboard.writeText(text);
      copyButton.textContent = "Copied";
    } catch (e) {
      // no clipboard access: select the text so Ctrl+C works
      const range = document.createRange();
      range.selectNodeContents(document.getElementById(valueId));
      const selection = window.getSelection();
      selection.removeAllRanges();
      selection.addRange(range);
      copyButton.textContent = "Press Ctrl+C";
    }
  }

  // --- tokens --------------------------------------------------------------

  async function revoke(token) {
    if (!window.confirm("Revoke token " + token.name + "? Clients using it stop working.")) {
      return;
    }
    await request("POST", "tokens/" + token.id + "/revoke", {});
    await loadTokens();
  }

  async function loadTokens() {
    const data = await request("GET", "tokens");
    const body = replaceRows("tokens-body", data.tokens, "No tokens.", 7);
    data.tokens.forEach(function (token) {
      const tr = el("tr");
      tr.appendChild(el("td", token.experiment));
      tr.appendChild(el("td", token.name));
      tr.appendChild(el("td", token.scope));
      tr.appendChild(el("td", formatTime(token.created)));
      tr.appendChild(el("td", formatTime(token.last_used)));
      tr.appendChild(el("td", token.revoked ? "revoked" : "active"));
      const actions = el("td");
      if (!token.revoked) {
        actions.appendChild(button("Revoke", function () {
          return revoke(token);
        }, "outline danger"));
      }
      tr.appendChild(actions);
      body.appendChild(tr);
    });
  }

  // --- warnings ------------------------------------------------------------

  async function loadWarnings() {
    const data = await request("GET", "warnings");
    const body = replaceRows("warnings-body", data.warnings, "No warnings.", 3);
    data.warnings.forEach(function (w) {
      const tr = el("tr");
      tr.appendChild(el("td", formatTime(w.t)));
      tr.appendChild(el("td", w.experiment === null ? "-" : w.experiment));
      tr.appendChild(el("td", w.message));
      body.appendChild(tr);
    });
  }

  document.addEventListener("DOMContentLoaded", function () {
    const inviteForm = document.getElementById("invite-form");
    inviteForm.addEventListener("submit", function (event) {
      event.preventDefault();
      run(async function () {
        const data = await request("POST", "invite", {
          role: document.getElementById("invite-role").value,
        });
        document.getElementById("invite-copy").textContent = "Copy";
        showSecret("invite-result", "invite-url", data.url);
      });
    });
    document.getElementById("invite-copy").addEventListener("click", function (event) {
      copy("invite-url", event.target);
    });

    const tokenForm = document.getElementById("token-form");
    tokenForm.addEventListener("submit", function (event) {
      event.preventDefault();
      run(async function () {
        const data = await request("POST", "tokens", {
          experiment: document.getElementById("token-experiment").value.trim(),
          name: document.getElementById("token-name").value.trim(),
          scope: document.getElementById("token-scope").value,
        });
        document.getElementById("token-copy").textContent = "Copy";
        showSecret("token-result", "token-value", data.token);
        tokenForm.reset();
        await loadTokens();
      });
    });
    document.getElementById("token-copy").addEventListener("click", function (event) {
      copy("token-value", event.target);
    });
    run(loadUsers);
    run(loadTokens);
    run(loadWarnings);
  });
})();
