function RHOTPLoaded() {
    console.log("RHOTPLoaded");

    console.log("Check ephemeral");
    if (window.location.href.includes("env-ephemeral")) {
        chrome.storage.sync.get("automaticLoginEph", (result) => {
            if (result["automaticLoginEph"].toString() == "true") {

                if (document.getElementById("#input-error") != null) {
                    return;
                }

                document.getElementById("kc-page-title").innerText = "Standby, signing you in..."
                chrome.runtime.sendMessage(
                    {
                        action: 'doAutomaticLogin',
                        context: "jdoeEphemeral"
                    },
                    function (response) {
                        chrome.storage.sync.get('creds', (result) => {
                            console.log('update password box');
                            const pwfield = document.getElementById("password");
                            const unfield1 = document.getElementById("username");

                            const unpw = result.creds.split(",");
                            const un = unpw[0];
                            const pw = unpw[1];
                            unfield1.value = un;
                            unfield1.style.border = "thick solid #0000FF";
                            pwfield.value = pw;
                            pwfield.style.border = "thick solid #0000FF";

                            setTimeout(function () {
                                const pwfield = document.getElementById("password");
                                let button = document.getElementById("kc-login");
                                console.log(pwfield.value);
                                console.log(button);
                                button.click();
                            }, 1000);
                        });
                    }
                );
            }
        });
    }

    console.log("Check openshiftapps.com/oauth/authorize");
    if (window.location.href.includes("openshiftapps.com/oauth/authorize")) {
        document.getElementsByClassName("pf-c-button")[0].click();
    }

    console.log("Check gitlab.cee.redhat.com/users/sign_in");
    if (window.location.href.includes("gitlab.cee.redhat.com/users/sign_in")) {
        document.getElementsByClassName("qa-saml-login-button")[0].click();
    }

    console.log("Check ci.int.devshift.net");
    if (window.location.href.includes("ci.int.devshift.net")) {
        console.log("ci.int.devshift.net login");
        let elements = document.getElementsByTagName("b");
        let arrayLength = elements.length;
        for (let i = 0; i < arrayLength; i++) {
            if (elements[i].innerText.trim() == "log in") {
                console.log("Set location: " + elements[i].parentElement.href);
                window.location.href = elements[i].parentElement.href;
                break;
            }
        }
    }
}

window.addEventListener('load', RHOTPLoaded, false);