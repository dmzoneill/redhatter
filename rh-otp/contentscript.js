if(window.location.href.includes("openshiftapps.com/oauth/authorize")) {
    var now = new Date().getTime();
    while(new Date().getTime() < now + 1000){}
    document.getElementsByClassName("pf-c-button")[0].click();
}

if(window.location.href.includes("gitlab.cee.redhat.com/users/sign_in")) {
    var now = new Date().getTime();
    while(new Date().getTime() < now + 1000){}
    document.getElementsByClassName("qa-saml-login-button")[0].click();
}

if(window.location.href.includes("ci.int.devshift.net")) {
    var now = new Date().getTime();
    while(new Date().getTime() < now + 1000){}
    var elements = document.getElementsByTagName("b");
    var arrayLength = elements.length;
    for (var i = 0; i < arrayLength; i++) {
        if(elements[i].innerText.trim() == "LOG IN") {
            window.location.href = elements[i].parentElement.href;
            break;
        }
    }
}