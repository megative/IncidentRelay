function splitAppPath(path) {
    /*
     * Split an internal app URL into route path and full path.
     *
     * Example:
     *   /alerts?status=firing -> routePath=/alerts, fullPath=/alerts?status=firing
     */
    const url = new URL(path || "/", window.location.origin);

    return {
        routePath: url.pathname,
        fullPath: url.pathname + url.search + url.hash
    };
}

function navigate(path, pushState) {
    /*
     * Navigate to an application page.
     *
     * Query string is preserved for page filters, but route lookup uses only
     * pathname because routes are registered as /alerts, /routes, etc.
     */
    const appPath = splitAppPath(path);
    const routePath = appPath.routePath;

    if ((routePath === "/admin/users" || routePath === "/groups") && (!currentUser || !currentUser.is_admin)) {
        alert("Admin permission is required.");
        path = "/";
    }

    const normalizedPath = splitAppPath(path);
    const selectedRoute = routes[normalizedPath.routePath] || routes["/"];

    $(".view").removeClass("view-visible").css("display", "none");
    $("#view-" + selectedRoute.page).addClass("view-visible").css("display", "block");

    $("#page-title").text(selectedRoute.title);
    $("#page-subtitle").text(selectedRoute.subtitle);

    $(".menu-link").removeClass("active");
    $('.menu-link[href="' + normalizedPath.routePath + '"]').addClass("active");

    if (pushState) {
        history.pushState({ path: normalizedPath.fullPath }, "", normalizedPath.fullPath);
    }

    safePageLoad(selectedRoute.load);
}
function safePageLoad(loadFunction) {
    /* Prevent one page error from hiding the whole view. */
    try {
        loadFunction();
    } catch (error) {
        console.error("Page load failed:", error);
        alert("Page load failed: " + error);
    }
}
function updateAuthUi() {
    /* Update menu items that depend on authentication and role. */
    if (!currentUser || !currentUser.is_admin) {
        $(".menu-link-admin").addClass("is-hidden");
    } else {
        $(".menu-link-admin").removeClass("is-hidden");
    }

    if (currentUser) {
        $("#topbar-username").text(currentUser.display_name || currentUser.username);
        fillActiveGroupSelect();
    }
}
function startAuthenticatedApp() {
    /* Load user state and start the application. */
    apiGet("/api/auth/me", function (user) {
        currentUser = user;
        updateAuthUi();
        fillTeamSelect("#global-team-filter", true, function () { navigate(window.location.pathname, false); });
    });
}

$(document).ready(function () {
    /* Initialize frontend routing and global selectors. */
    loadVersion();

    if (window.location.pathname === "/login") {
        navigate("/login", false);
    } else {
        startAuthenticatedApp();
    }

    $(".menu-link[data-page]").on("click", function (event) { event.preventDefault(); navigate($(this).attr("href"), true); });

    $("#global-team-filter").on("change", function () { navigate(window.location.pathname, false); });

    $("#active-group-select").on("change", function () {
        const groupId = $(this).val();

        apiPost("/api/profile/active-group", { group_id: groupId ? Number(groupId) : null }, function (user) {
            currentUser = user;
            updateAuthUi();
            fillTeamSelect("#global-team-filter", true, function () { navigate(window.location.pathname, false); });
        });
    });

    $("#topbar-profile").on("click", function () { navigate("/profile", true); });

    $("#topbar-logout").on("click", function () {
        logout();
    });

    window.onpopstate = function () { navigate(window.location.pathname, false); };
});