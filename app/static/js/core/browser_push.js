function browserPushUrlBase64ToUint8Array(base64String) {
    const padding = "=".repeat((4 - base64String.length % 4) % 4);
    const base64 = (base64String + padding)
        .replace(/-/g, "+")
        .replace(/_/g, "/");

    const rawData = window.atob(base64);
    const output = new Uint8Array(rawData.length);

    for (let i = 0; i < rawData.length; i += 1) {
        output[i] = rawData.charCodeAt(i);
    }

    return output;
}

function browserPushSupported() {
    return (
        "serviceWorker" in navigator
        && "PushManager" in window
        && "Notification" in window
    );
}

function browserPushDeviceName() {
    const platform = navigator.platform || "Browser";
    const userAgent = navigator.userAgent || "";

    if (/Android/i.test(userAgent)) {
        return "Android browser";
    }

    if (/iPhone|iPad|iPod/i.test(userAgent)) {
        return "iOS browser";
    }

    if (/Windows/i.test(platform)) {
        return "Windows browser";
    }

    if (/Mac/i.test(platform)) {
        return "macOS browser";
    }

    if (/Linux/i.test(platform)) {
        return "Linux browser";
    }

    return platform;
}

function browserPushGetVapidKey(callback) {
    apiGet("/api/profile/push/vapid-public-key", callback);
}

function browserPushEnableCurrentDevice(done) {
    if (!browserPushSupported()) {
        showError("Browser push is not supported by this browser.");
        return;
    }

    browserPushGetVapidKey(function (config) {
        if (!config || !config.enabled || !config.public_key) {
            showError("Browser push is not configured on the server.");
            return;
        }

        Notification.requestPermission().then(function (permission) {
            if (permission !== "granted") {
                showError("Notification permission was not granted.");
                return;
            }

            navigator.serviceWorker.ready.then(function (registration) {
                return registration.pushManager.subscribe({
                    userVisibleOnly: true,
                    applicationServerKey: browserPushUrlBase64ToUint8Array(config.public_key)
                });
            }).then(function (subscription) {
                const json = subscription.toJSON();

                apiPost(
                    "/api/profile/push/subscriptions",
                    {
                        endpoint: json.endpoint,
                        keys: json.keys || {},
                        device_name: browserPushDeviceName(),
                        user_agent: navigator.userAgent || ""
                    },
                    function (response) {
                        if (typeof done === "function") {
                            done(response);
                        }
                    }
                );
            });
        });
    });
}

function browserPushDisableCurrentDevice(done) {
    if (!browserPushSupported()) {
        return;
    }

    navigator.serviceWorker.ready.then(function (registration) {
        return registration.pushManager.getSubscription();
    }).then(function (subscription) {
        if (!subscription) {
            if (typeof done === "function") {
                done();
            }
            return;
        }

        const endpoint = subscription.endpoint;

        apiDelete(
            "/api/profile/push/subscriptions/by-endpoint",
            {endpoint: endpoint},
            function () {
                subscription.unsubscribe().finally(function () {
                    if (typeof done === "function") {
                        done();
                    }
                });
            }
        );
    });
}
