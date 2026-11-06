// Passkey registration and login. Talks to the JSON routes under /auth/.
// Holds no secrets: challenges come from the server and are single use.
"use strict";

(function () {
  function b64uToBuf(text) {
    const b64 = text.replace(/-/g, "+").replace(/_/g, "/");
    const padded = b64 + "=".repeat((4 - (b64.length % 4)) % 4);
    const raw = atob(padded);
    const bytes = new Uint8Array(raw.length);
    for (let i = 0; i < raw.length; i++) bytes[i] = raw.charCodeAt(i);
    return bytes.buffer;
  }

  function bufToB64u(buffer) {
    const bytes = new Uint8Array(buffer);
    let raw = "";
    for (let i = 0; i < bytes.length; i++) raw += String.fromCharCode(bytes[i]);
    return btoa(raw).replace(/\+/g, "-").replace(/\//g, "_").replace(/=+$/, "");
  }

  function showError(message) {
    const box = document.getElementById("error");
    if (!box) return;
    box.textContent = message;  // textContent: never interpreted as HTML
    box.hidden = false;
  }

  function clearError() {
    const box = document.getElementById("error");
    if (box) box.hidden = true;
  }

  async function postJson(url, body) {
    let response;
    try {
      response = await fetch(url, {
        method: "POST",
        credentials: "same-origin",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(body || {}),
      });
    } catch (e) {
      throw new Error("Could not reach the server.");
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

  function describe(e) {
    if (e && e.name === "NotAllowedError") {
      return "The passkey request was cancelled or timed out.";
    }
    if (e && e.name === "InvalidStateError") {
      return "This passkey is already registered.";
    }
    return (e && e.message) || "Something went wrong.";
  }

  function requireWebauthn() {
    if (!window.PublicKeyCredential || !navigator.credentials) {
      throw new Error("This browser does not support passkeys (HTTPS is required).");
    }
  }

  // Create a passkey. `body` is {code, name} for an invite, {} when logged in.
  async function register(body) {
    requireWebauthn();
    const options = await postJson("/auth/register/options", body);
    options.challenge = b64uToBuf(options.challenge);
    options.user.id = b64uToBuf(options.user.id);
    (options.excludeCredentials || []).forEach(function (c) {
      c.id = b64uToBuf(c.id);
    });
    const cred = await navigator.credentials.create({ publicKey: options });
    const payload = {
      id: cred.id,
      rawId: bufToB64u(cred.rawId),
      type: cred.type,
      response: {
        clientDataJSON: bufToB64u(cred.response.clientDataJSON),
        attestationObject: bufToB64u(cred.response.attestationObject),
        transports: cred.response.getTransports ? cred.response.getTransports() : [],
      },
      clientExtensionResults: cred.getClientExtensionResults(),
    };
    return postJson("/auth/register/verify", payload);
  }

  async function login() {
    requireWebauthn();
    const options = await postJson("/auth/login/options", {});
    options.challenge = b64uToBuf(options.challenge);
    (options.allowCredentials || []).forEach(function (c) {
      c.id = b64uToBuf(c.id);
    });
    const cred = await navigator.credentials.get({ publicKey: options });
    const payload = {
      id: cred.id,
      rawId: bufToB64u(cred.rawId),
      type: cred.type,
      response: {
        clientDataJSON: bufToB64u(cred.response.clientDataJSON),
        authenticatorData: bufToB64u(cred.response.authenticatorData),
        signature: bufToB64u(cred.response.signature),
        userHandle: cred.response.userHandle
          ? bufToB64u(cred.response.userHandle)
          : null,
      },
      clientExtensionResults: cred.getClientExtensionResults(),
    };
    return postJson("/auth/login/verify", payload);
  }

  async function logout() {
    return postJson("/auth/logout", {});
  }

  async function guarded(button, action) {
    clearError();
    button.disabled = true;
    try {
      await action();
      window.location.href = "/";
    } catch (e) {
      showError(describe(e));
      button.disabled = false;
    }
  }

  window.hcWebauthn = { register: register, login: login, logout: logout };

  document.addEventListener("DOMContentLoaded", function () {
    const loginButton = document.getElementById("login-button");
    if (loginButton) {
      loginButton.addEventListener("click", function () {
        guarded(loginButton, login);
      });
    }
    const form = document.getElementById("invite-form");
    if (form) {
      form.addEventListener("submit", function (event) {
        event.preventDefault();
        const button = form.querySelector("button");
        const name = form.elements.name.value.trim();
        if (!name) {
          showError("Please enter a display name.");
          return;
        }
        guarded(button, function () {
          return register({ code: form.dataset.code, name: name });
        });
      });
    }
  });
})();
