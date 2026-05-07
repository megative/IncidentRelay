function asArray(value) {
    /* Return value when it is an array, otherwise return an empty array. */
    return Array.isArray(value) ? value : [];
}
function parseJsonInput(selector, fallback) {
    /* Parse JSON from an input field. */
    const raw = $(selector).val();
    if (!raw) { return fallback; }
    try { return JSON.parse(raw); } catch (error) { alert("Invalid JSON in " + selector + ": " + error); throw error; }
}

function loadVersion() {
    /* Load service version. */
    apiGet("/api/version", function (data) { $("#service-version").text("v" + data.service_version); });
}

function renderStatusBadge(isActive, activeText = "Enabled", inactiveText = "Disabled") {
    /*
     * Render a reusable status badge.
     */
    return $("<span>")
        .addClass("status-pill")
        .addClass(isActive ? "status-enabled" : "status-disabled")
        .text(isActive ? activeText : inactiveText);
}
function upperCaseFirst(value) { return value.charAt(0).toUpperCase() + value.slice(1); }
