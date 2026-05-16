function setLoginStatus(message, type) {
    /*
     * Show login page status message.
     */
    $("#login-status")
        .css("display", "block")
        .removeClass("login-status-error login-status-success login-status-info")
        .addClass("login-status-" + (type || "info"))
        .text(message || "");
}

function login(event) {
    /*
     * Request a JWT token and store it locally.
     */
    if (event) {
        event.preventDefault();
    }

    const username = $("#username").val().trim();
    const password = $("#password").val();

    if (!username || !password) {
        setLoginStatus("Please enter username and password", "error");
        return;
    }

    setLoginStatus("Signing in...", "info");

    apiPost(
        "/api/auth/login",
        {
            username: username,
            password: password
        },
        function (data) {
            localStorage.setItem("oncall_jwt", data.access_token);

            setLoginStatus(
                "Logged in as " + data.user.username + "\nExpires at: " + data.expires_at,
                "success"
            );

            window.location.href = "/";
        },
        function (xhr) {
            const message = getApiErrorMessage(
                xhr,
                "Invalid username or password"
            );

            if (xhr && xhr.status === 401) {
                setLoginStatus("Invalid username or password", "error");
                return;
            }

            setLoginStatus(message, "error");
        }
    );
}

function logout() {
    /* Remove the stored JWT token and clear the cookie. */
    apiPost("/api/auth/logout", {}, function () {
        localStorage.removeItem("oncall_jwt");
        $("#login-status").text("Logged out");
        window.location.href = "/login";
    });
}

function loadLogin() {
    /* Show current login state. */
    const token = localStorage.getItem("oncall_jwt");
    $("#login-status").text(token ? "JWT token is stored in this browser." : "");
}

$(document).on("submit", "#login-form", login);
$(document).on("click", "#logout-submit", logout);