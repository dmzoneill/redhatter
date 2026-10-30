/* global chrome */
function RHOTPLoaded() {
  console.log("🔁 RHOTPLoaded");

  const currentURL = window.location.href;
  const currentHost = window.location.hostname;
  const currentPath = window.location.pathname;

  // Match on the real hostname (exact or subdomain), never a substring of the
  // full URL, so e.g. https://evil.example/?auth.redhat.com cannot trigger
  // credential autofill.
  function onHost(host) {
    return currentHost === host || currentHost.endsWith("." + host);
  }

  // Handle login process
  // Utility: Login using stored creds and form selectors
  function handleLogin({
    context = "associate",
    userId = "username",
    passId = "password",
    loginBtnId = "submit",
    loginDelay = 800,
    titleSelector,
    titleText,
    errorSelector = ".alert-error, .alert-danger, .kc-feedback-text", // add others if needed
    errorTextMatch = "Invalid username or password",
  }) {
    // 🛑 Early exit if error message is visible
    const errorElements = document.querySelectorAll(errorSelector);
    for (const el of errorElements) {
      if (
        el.textContent?.toLowerCase().includes(errorTextMatch.toLowerCase())
      ) {
        console.warn("🚫 Login error detected, skipping auto-login.");
        return;
      }
    }

    // Optional: Update page title text
    if (titleSelector && titleText) {
      const titleElem = document.querySelector(titleSelector);
      if (titleElem) titleElem.innerText = titleText;
    }

    chrome.runtime.sendMessage({ action: "doAutomaticLogin", context }, () => {
      chrome.storage.sync.get("creds", (result) => {
        if (!result.creds) {
          console.warn("⚠️ No credentials found.");
          return;
        }

        let creds = result.creds;

        if (creds.startsWith('"') && creds.endsWith('"')) {
          creds = creds.substring(1, creds.length - 1); // or use .slice(1, -1)
        }

        const [username, password] = creds.split(",");

        const userField = document.getElementById(userId);
        const passField = document.getElementById(passId);

        if (!userField || !passField) {
          console.warn("⚠️ Username or password field not found.");
          return;
        }

        userField.value = username;
        passField.value = password;

        userField.style.border = "thick solid #00AA00";
        passField.style.border = "thick solid #00AA00";

        setTimeout(() => {
          const loginBtn = document.getElementById(loginBtnId);
          if (loginBtn) {
            console.log("🚀 Clicking login button...");
            loginBtn.click();
          } else {
            console.warn("⚠️ Login button not found.");
          }
        }, loginDelay);
      });
    });
  }

  // Check for various login scenarios and handle accordingly
  function handleLoginScenarios() {
    console.log("handleLoginScenarios");
    if (
      currentURL.includes("env-ephemeral") &&
      document.getElementById("#input-error")
    ) {
      chrome.storage.sync.get("automaticLoginEph", (result) => {
        if (result.automaticLoginEph?.toString() === "true") {
          console.log("Ephemeral login");
          handleLogin({
            context: "jdoeEphemeral",
            userId: "username",
            passId: "password",
            loginBtnId: "kc-login",
            titleSelector: "#kc-page-title",
            titleText: "Standby, signing you in...",
            loginDelay: 1000,
          });
        }
      });
    }

    if (onHost("auth.redhat.com")) {
      console.log("login: auth.redhat.com");
      handleLogin({ context: "associate" });
    } else if (
      onHost("sso.redhat.com") &&
      currentPath.startsWith("/auth/realms")
    ) {
      console.log("login: sso.redhat.com/auth/realms");
      SSORedhatLogin();
    } else if (
      onHost("openshiftapps.com") &&
      currentPath.startsWith("/oauth/authorize")
    ) {
      console.log("login: openshiftapps.com/oauth/authorize");
      clickButton(".pf-c-button", "🟥 Clicking Red Hat OAuth button");
    } else if (
      onHost("gitlab.cee.redhat.com") &&
      currentPath.startsWith("/users/sign_in")
    ) {
      console.log("login: gitlab.cee.redhat.com/users/sign_in");
      clickSAMLButton("🔐 Clicking GitLab SAML login");
    } else if (onHost("ci.int.devshift.net")) {
      console.log("login: ci.int.devshift.net");
      searchAndRedirectToDevshiftLogin();
    } else if (onHost("gitlab.cee.redhat.com")) {
      console.log("login: gitlab.cee.redhat.com");
      clickButton(
        'a[href="/users/sign_in?redirect_to_referer=yes"]',
        "🔗 Found GitLab redirect sign-in, clicking...",
      );
    } else if (
      onHost("source.redhat.com") &&
      window.location.search.includes("signin")
    ) {
      console.log("login: source.redhat.com/?signin");
      document.getElementById("samlsignin-submit-button").click();
    }
  }

  function SSORedhatLogin() {
    chrome.runtime.sendMessage({ action: "DoGetAssociateEmail" }, () => {
      chrome.storage.sync.get("email", (result) => {
        if (!result.email) {
          console.warn("⚠️ No email found.");
          return;
        }

        const usernameField = document.getElementById("username-verification");
        usernameField.value = result.email.replace(/['"]/g, "");

        const loginShowStep2 = document.getElementById("login-show-step2");
        loginShowStep2.click();

        // Wait 1 second (1000ms) before clicking the second button
        setTimeout(() => {
          const rhSsoFlow = document.getElementById("rh-sso-flow");
          if (rhSsoFlow) {
            rhSsoFlow.click();
          } else {
            console.warn("⚠️ rh-sso-flow button not found.");
          }
        }, 1000); // 1 second delay
      });
    });
  }

  // Click a button with the provided selector and log message
  function clickButton(selector, logMessage) {
    const btn = document.querySelector(selector);
    if (btn) {
      console.log(logMessage);
      btn.click();
    }
  }

  // Handle SAML login button by data-testid
  function clickSAMLButton(logMessage) {
    const samlButton = document.querySelector(
      'button[data-testid="saml-login-button"]',
    );
    if (samlButton) {
      console.log(logMessage);
      samlButton.click();
    } else {
      console.log("❌ SAML Login button not found.");
    }
  }

  // Search for Devshift login link and redirect
  function searchAndRedirectToDevshiftLogin() {
    console.log("🔍 Searching for Devshift login link...");
    const elements = document.getElementsByTagName("a");
    for (let i = 0; i < elements.length; i++) {
      if (elements[i].innerText.trim() === "log in") {
        const loginHref = elements[i].parentElement.href;
        console.log("➡️ Redirecting to:", loginHref);
        window.location.href = loginHref;
        break;
      }
    }
  }

  setTimeout(handleLoginScenarios, 1000);
}

window.addEventListener("load", RHOTPLoaded, false);
