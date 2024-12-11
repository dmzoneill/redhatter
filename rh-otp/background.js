async function login(context, sendResponse) {
    chrome.storage.sync.get("headless", (result) => {
        let headless = result["headless"].toString()
        $.get("http://localhost:8009/get_creds?context=" + context + "&headless=" + headless, function (data) {
            chrome.storage.sync.set({ creds: data }, async function () {
                sendResponse("done");
            });
        });
    });
}

chrome.runtime.onMessage.addListener(function (message, sender, sendResponse) {
    console.log("Received message");
    if (message.action === 'doAutomaticLogin') {
        login(message.context, sendResponse);
    }
    else if (message.action === 'doOpenEphemeral') {
        login(message.context, sendResponse);
    }
    return true;
});
