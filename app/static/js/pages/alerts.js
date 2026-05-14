let currentDetailsAlertId = null;
let alertsCache = [];
let alertsAutoRefreshTimer = null;
let alertsLastAppliedQueryString = null;

let alertsCurrentPage = 1;
let alertsPageSize = 25;
let alertsSortState = createTableSortState("activity", "desc");
let alertsPagination = {
    page: 1,
    page_size: 25,
    total_items: 0,
    total_pages: 1,
    from: 0,
    to: 0,
    has_prev: false,
    has_next: false
};
let alertsSummary = {
    firing: 0,
    acknowledged: 0,
    resolved: 0,
    silenced: 0,
    reminders: 0,
    total: 0
};

const alertsSortColumns = {
    status: {
        type: "rank",
        defaultDirection: "asc"
    },
    id: {
        path: "id",
        type: "number",
        defaultDirection: "desc"
    },
    title: {
        path: "title",
        type: "text",
        defaultDirection: "asc"
    },
    severity: {
        type: "rank",
        defaultDirection: "desc"
    },
    team: {
        value: function (alert) {
            return alert.team_slug || "";
        },
        type: "text",
        defaultDirection: "asc"
    },
    assignee: {
        value: function (alert) {
            return alert.assignee || "";
        },
        type: "text",
        defaultDirection: "asc"
    },
    created: {
        value: function (alert) {
            return alertCreatedValue(alert);
        },
        type: "datetime",
        defaultDirection: "desc"
    },
    last_seen: {
        path: "last_seen_at",
        type: "datetime",
        defaultDirection: "desc"
    },
    reminders: {
        path: "reminder_count",
        type: "number",
        defaultDirection: "desc"
    },
    activity: {
        value: function (alert) {
            return alertActivityValue(alert);
        },
        type: "datetime",
        defaultDirection: "desc"
    }
};

function initAlertsTableSorting() {
    /*
     * Enable reusable column sorting for the alerts table.
     */
    bindSortableTableHeaders(
        "#alerts-table-view",
        alertsSortState,
        alertsSortColumns,
        function () {
            resetAlertsPagination();
            writeAlertsQueryParams();
            loadAlerts();
        }
    );
}

function normalizeAlertValue(value) {
    /*
     * Convert any value to normalized lowercase string.
     */
    return String(value || "").toLowerCase();
}

function alertCreatedValue(alert) {
    /*
     * Return the best available creation timestamp.
     */
    return alert.first_seen_at || alert.created_at || null;
}

function alertActivityValue(alert) {
    /*
     * Return the best available activity timestamp.
     */
    return alert.last_seen_at || alert.updated_at || alert.created_at || alert.first_seen_at || null;
}
function getAlertIdFromPath(pathname) {
    /*
     * Return alert ID from /alerts/<id>.
     */
    const match = String(pathname || "").match(/^\/alerts\/(\d+)\/?$/);

    if (!match) {
        return null;
    }

    return Number(match[1]);
}

function buildAlertDetailsUrl(alertId) {
    /*
     * Build a browser URL for an alert details page.
     */
    return "/alerts/" + encodeURIComponent(alertId);
}

function buildAlertListUrl() {
    /*
     * Return the Alerts list URL while preserving current filters.
     */
    return "/alerts" + (window.location.search || "");
}

function openAlertDetailsPage(alertId) {
    /*
     * Open alert details and put a shareable URL into the browser address bar.
     */
    const url = buildAlertDetailsUrl(alertId);

    history.pushState({ path: url }, "", url);
    showAlertDetails(alertId);
}

function syncAlertDetailsFromUrl() {
    /*
     * Open or close alert details according to the current browser URL.
     */
    const alertId = getAlertIdFromPath(window.location.pathname);

    if (!alertId) {
        if (alertDetailsModal().hasClass("is-open")) {
            closeAlertDetailsModal({ updateUrl: false });
        }

        return;
    }

    if (
        currentDetailsAlertId === alertId &&
        alertDetailsModal().hasClass("is-open")
    ) {
        return;
    }

    showAlertDetails(alertId);
}
function alertDuration(alert) {
    /*
     * Calculate alert age from created/first_seen_at to now.
     */
    const startedRaw = alertCreatedValue(alert);

    if (!startedRaw) {
        return "-";
    }

    const started = new Date(startedRaw);
    if (Number.isNaN(started.getTime())) {
        return "-";
    }

    let seconds = Math.max(0, Math.floor((Date.now() - started.getTime()) / 1000));

    const days = Math.floor(seconds / 86400);
    seconds -= days * 86400;

    const hours = Math.floor(seconds / 3600);
    seconds -= hours * 3600;

    const minutes = Math.floor(seconds / 60);

    if (days > 0) {
        return days + "d " + hours + "h";
    }

    if (hours > 0) {
        return hours + "h " + minutes + "m";
    }

    return Math.max(minutes, 1) + "m";
}

function severityLabel(severity) {
    const value = normalizeAlertValue(severity);

    if (value === "critical") {
        return "Critical";
    }

    if (value === "high") {
        return "High";
    }

    if (value === "medium") {
        return "Medium";
    }

    if (value === "low") {
        return "Low";
    }

    return severity || "-";
}

function statusLabel(status) {
    const value = normalizeAlertValue(status);

    if (value === "firing") {
        return "Firing";
    }

    if (value === "acknowledged") {
        return "Acknowledged";
    }

    if (value === "resolved") {
        return "Resolved";
    }

    if (value === "silenced") {
        return "Silenced";
    }

    return status || "-";
}

function severityBadgeClass(severity) {
    const value = normalizeAlertValue(severity);

    if (value === "critical") {
        return "alerts-badge-critical";
    }

    if (value === "high") {
        return "alerts-badge-high";
    }

    if (value === "warning") {
        return "alerts-badge-medium";
    }

    if (value === "medium") {
        return "alerts-badge-medium";
    }

    if (value === "low") {
        return "alerts-badge-low";
    }

    if (value === "info") {
        return "alerts-badge-info";
    }

    return "alerts-badge-muted";
}

function statusBadgeClass(status) {
    const value = normalizeAlertValue(status);

    if (value === "firing") {
        return "alerts-badge-firing";
    }

    if (value === "acknowledged") {
        return "alerts-badge-acknowledged";
    }

    if (value === "resolved") {
        return "alerts-badge-resolved";
    }

    if (value === "silenced") {
        return "alerts-badge-silenced";
    }

    return "alerts-badge-muted";
}

function makeAlertBadge(text, cssClass) {
    /*
     * Build a pill badge.
     */
    return $("<span>")
        .addClass("alerts-pill")
        .addClass(cssClass)
        .text(text || "-");
}

function buildAlertsApiUrl() {
    /*
     * Build alerts API URL using backend pagination, filters and table sorting.
     */
    const params = [];

    if (typeof selectedTeamId === "function" && selectedTeamId()) {
        params.push("team_id=" + encodeURIComponent(selectedTeamId()));
    }

    if ($("#status-filter").val()) {
        params.push("status=" + encodeURIComponent($("#status-filter").val()));
    }

    if ($("#severity-filter").val()) {
        params.push("severity=" + encodeURIComponent($("#severity-filter").val()));
    }

    if ($("#alerts-search").val()) {
        params.push("search=" + encodeURIComponent($("#alerts-search").val()));
    }

    params.push("page=" + encodeURIComponent(alertsCurrentPage));
    params.push("page_size=" + encodeURIComponent(alertsPageSize));
    params.push("sort=" + encodeURIComponent(alertsSortState.column || "activity"));
    params.push("order=" + encodeURIComponent(alertsSortState.direction || "desc"));

    return "/api/alerts" + (params.length ? "?" + params.join("&") : "");
}
function writeAlertsQueryParams() {
    /*
     * Save current alerts filters, sorting and pagination to the browser URL.
     */

    const params = new URLSearchParams();

    if (typeof selectedTeamId === "function" && selectedTeamId()) {
        params.set("team_id", selectedTeamId());
    }

    if ($("#status-filter").val()) {
        params.set("status", $("#status-filter").val());
    }

    if ($("#severity-filter").val()) {
        params.set("severity", $("#severity-filter").val());
    }

    if ($("#alerts-search").val()) {
        params.set("search", $("#alerts-search").val());
    }

    if (alertsCurrentPage > 1) {
        params.set("page", String(alertsCurrentPage));
    }

    if (alertsPageSize !== 25) {
        params.set("page_size", String(alertsPageSize));
    }

    if (
        alertsSortState.column &&
        (
            alertsSortState.column !== "activity" ||
            alertsSortState.direction !== "desc"
        )
    ) {
        params.set("sort", alertsSortState.column);
        params.set("order", alertsSortState.direction || "desc");
    }

    const query = params.toString();
    const nextUrl = window.location.pathname + (query ? "?" + query : "");

    history.replaceState({ path: nextUrl }, "", nextUrl);
    alertsLastAppliedQueryString = window.location.search || "";
}
function loadAlerts() {
    /*
     * Load one alert page from backend.
     */
    applyAlertsQueryParams();
    initAlertsTableSorting();

    apiGet(buildAlertsApiUrl(), function (response) {
        alertsCache = alertsResponseItems(response);
        alertsPagination = alertsResponsePagination(response);
        alertsSummary = alertsResponseSummary(response);
        alertsCurrentPage = alertsPagination.page || alertsCurrentPage;
        alertsPageSize = alertsPagination.page_size || alertsPageSize;
        writeAlertsQueryParams();

        updateSortableTableHeaders("#alerts-table-view", alertsSortState);
        renderAlertsPage();
    });
}

function renderAlertsPage() {
    /*
     * Render alert page widgets from paginated backend response.
     */
    renderAlertsSummaryGrid("#alerts-alerts-summary", alertsSummary);
    renderAlertsInboxCounter(alertsPagination);
    renderActiveAlertFilters(alertsPagination);
    renderAlertsTable(alertsCache);
    renderAlertsPagination(alertsPagination);
    syncAlertDetailsFromUrl();
}

function renderAlertsPagination(pagination) {
    /*
     * Render backend pagination controls state.
     */
    pagination = pagination || {};

    $("#alerts-current-page").text(pagination.page || 1);
    $("#alerts-total-pages").text(pagination.total_pages || 1);

    $("#alerts-prev-page").prop("disabled", !pagination.has_prev);
    $("#alerts-next-page").prop("disabled", !pagination.has_next);
    $("#alerts-page-size").val(String(pagination.page_size || alertsPageSize));

    $(".alerts-pagination").toggle((pagination.total_items || 0) > 0);
}


function resetAlertsPagination() {
    /*
     * Reset pagination to the first page after filters/search/API reload.
     */
    alertsCurrentPage = 1;
}

function renderActiveAlertFilters(pagination) {
    /*
     * Render active filter chips.
     */
    const target = $("#alerts-active-filters");
    target.empty();

    const chips = [];

    if ($("#status-filter").val()) {
        chips.push("Status: " + statusLabel($("#status-filter").val()));
    }

    if ($("#severity-filter").val()) {
        chips.push("Severity: " + severityLabel($("#severity-filter").val()));
    }

    if ($("#alerts-search").val()) {
        chips.push("Search: " + $("#alerts-search").val());
    }

    chips.push("Result: " + ((pagination && pagination.total_items) || 0));

    chips.forEach(function (chip) {
        target.append($("<span>").addClass("alerts-filter-chip").text(chip));
    });
}

function renderAlertsTable(alerts) {
    /*
     * Render alert inbox table.
     */
    const tbody = $("#alerts-table");
    tbody.empty();

    if (!alerts.length) {
        tbody.append(
            $("<tr>").append(
                $("<td>")
                    .attr("colspan", "10")
                    .addClass("empty-table-cell")
                    .text("No alerts found")
            )
        );
        return;
    }

    alerts.forEach(function (alert) {
        tbody.append(renderAlertPageRow(alert));
    });
}

function renderAlertPageRow(alert) {
    /*
     * Render one alert row.
     */
    const row = $("<tr>").addClass("alerts-row alerts-row-" + normalizeAlertValue(alert.status));

    row.append(
        $("<td>").append(
            $("<div>")
                .addClass("alerts-status-cell")
                .append($("<span>").addClass("alerts-status-dot alerts-dot-" + normalizeAlertValue(alert.status)))
                .append(makeAlertBadge(statusLabel(alert.status), statusBadgeClass(alert.status)))
        )
    );

    row.append(
        $("<td>").append(
            $("<a>")
                .attr("href", buildAlertDetailsUrl(alert.id))
                .attr("title", "View alert details")
                .addClass("alerts-id-link")
                .text("#" + alert.id)
                .on("click", function (event) {
                    event.preventDefault();
                    openAlertDetailsPage(alert.id);
                })
        )
    );

    row.append(
        $("<td>")
            .addClass("alert-title-cell")
            .append($("<div>").addClass("alerts-title").text(alert.title || "-"))
            .append(
                $("<div>")
                    .addClass("alerts-subtitle")
                    .text(buildAlertSubtitle(alert))
            )
            .append(
                $("<div>")
                    .addClass("alerts-age")
                    .text("Age: " + alertDuration(alert))
            )
    );

    row.append(
        $("<td>").append(
            makeAlertBadge(severityLabel(alert.severity), severityBadgeClass(alert.severity))
        )
    );

    row.append(
        $("<td>")
            .append($("<div>").addClass("alerts-team").text(alert.team_slug || "-"))
            .append($("<div>").addClass("alerts-subtitle").text(alert.route_name || "No route"))
    );

    row.append($("<td>").text(alert.assignee || "-"));
    row.append($("<td>").text(formatDateTimeMinutes(alertCreatedValue(alert))));
    row.append($("<td>").text(formatDateTimeMinutes(alert.last_seen_at)));
    row.append($("<td>").append(renderEscalationCount(alert)));
    row.append($("<td>").append(renderReminderCount(alert)));

    const actionsCell = $("<td>").addClass("actions-cell");
    const actions = $("<div>").addClass("table-actions");

    if (alert.status === "firing") {
        actions.append(
            $("<button>")
                .attr("type", "button")
                .addClass("btn btn-warning btn-small")
                .text("Ack")
                .on("click", function () {
                    apiPost("/api/alerts/" + alert.id + "/ack", {}, loadAlerts);
                })
        );
    }

    if (alert.status !== "resolved") {
        actions.append(
            $("<button>")
                .attr("type", "button")
                .addClass("btn btn-resolve btn-small")
                .text("Resolve")
                .on("click", function () {
                    apiPost("/api/alerts/" + alert.id + "/resolve", {}, loadAlerts);
                })
        );
    }

    actionsCell.append(actions);
    row.append(actionsCell);

    return row;
}

function buildAlertSubtitle(alert) {
    /*
     * Build secondary text for alert row.
     */
    const parts = [];

    if (alert.source) {
        parts.push(alert.source);
    }

    if (alert.external_id) {
        parts.push(alert.external_id);
    }

    if (alert.group_key) {
        parts.push(alert.group_key);
    }

    return parts.length ? parts.join(" · ") : "Routed alert";
}

function renderReminderCount(alert) {
    /*
     * Render reminder counter badge.
     */
    const count = alert.reminder_count || 0;

    return $("<span>")
        .addClass("alerts-reminder-badge")
        .toggleClass("is-active", count > 0)
        .text(count);
}

function renderEscalationCount(alert) {
    /*
     * Render reminder Escalation badge.
     */
    const count = alert.escalation_level || 0;

    return $("<span>")
        .addClass("alerts-reminder-badge")
        .toggleClass("is-active", count > 0)
        .text(count);
}

function showAlertDetails(alertId) {
    /*
     * Load and render full alert details in modal.
     */
    currentDetailsAlertId = alertId;

    apiGet("/api/alerts/" + alertId, function (alert) {
        const modal = alertDetailsModal();

        if (!modal.length) {
            console.error("Alert details modal not found");
            return;
        }

        currentDetailsAlertId = alert.id;

        modal.find("#alert-details-title").text(
            "Alert #" + alert.id + ": " + (alert.title || "-")
        );

        modal.find("#alert-details-subtitle").text(
            (alert.team_slug || "-") + " / " + (alert.status || "-") + " / " + (alert.severity || "-")
        );

        renderAlertDetailsSummary(alert, modal);

        modal.find("#alert-details-labels").text(JSON.stringify(alert.labels || {}, null, 2));
        modal.find("#alert-details-payload").text(JSON.stringify(alert.payload || {}, null, 2));

        renderEvents(alert.events || [], modal);
        renderNotifications(alert.notifications || [], modal);

        if (alert.status === "resolved") {
            modal.find("#modal-alert-ack").hide();
            modal.find("#modal-alert-resolve").hide();
        } else {
            if (alert.status === "firing") {
                modal.find("#modal-alert-ack").show();
            } else {
                modal.find("#modal-alert-ack").hide();
            }

            modal.find("#modal-alert-resolve").show();
        }

        openAlertDetailsModal();
    });
}

function renderAlertDetailsSummary(alert, modal) {
    /*
     * Render alert summary block.
     */
    const summary = modal.find("#alert-details-summary");
    summary.empty();

    summary.append(detailItem("Source", alert.source));
    summary.append(detailItem("External ID", alert.external_id));
    summary.append(detailItem("Route", alert.route_name));
    summary.append(detailItem("Rotation", alert.rotation_name));
    summary.append(detailItem("Assignee", alert.assignee));
    summary.append(detailItem("Acknowledged by", alert.acknowledged_by));
    summary.append(detailItem("Created", formatDateTimeMinutes(alert.first_seen_at || alert.created_at)));
    summary.append(detailItem("Last seen", formatDateTimeMinutes(alert.last_seen_at)));
    summary.append(detailItem("Last notification", formatDateTimeMinutes(alert.last_notification_at)));
    summary.append(detailItem("Group key", alert.group_key));
    summary.append(detailItem("Dedup key", alert.dedup_key));
    summary.append(detailItem("Reminder count", alert.reminder_count || 0));
    summary.append(detailItem(
        "Reminder interval",
        alert.rotation_reminder_interval_seconds ? alert.rotation_reminder_interval_seconds + "s" : "-"
    ));
}


function renderEvents(events, modal) {
    /*
     * Render alert events.
     */
    const target = modal.find("#alert-details-events");
    target.empty();

    if (!events.length) {
        target.append($("<div>").addClass("help-text").text("No events."));
        return;
    }

    events.forEach(function (event) {
        target.append(
            $("<div>")
                .addClass("event-item")
                .append($("<strong>").text("#" + event.id + " " + event.event_type))
                .append(
                    $("<div>").text(
                        formatDateTimeMinutes(event.created_at) + " " + (event.message || "")
                    )
                )
        );
    });
}


function renderNotifications(notifications, modal) {
    /*
     * Render notification delivery records.
     */
    const target = modal.find("#alert-details-notifications");
    target.empty();

    if (!notifications.length) {
        target.append($("<div>").addClass("help-text").text("No delivery records."));
        return;
    }

    notifications.forEach(function (item) {
        const channel = item.channel
            ? item.channel.name + " (" + item.channel.channel_type + ")"
            : "-";

        const status = item.last_error
            ? "failed: " + item.last_error
            : (item.last_event_type || "sent");

        target.append(
            $("<div>")
                .addClass("event-item")
                .append($("<strong>").text("#" + item.id + " " + channel))
                .append($("<div>").text((item.provider || "-") + " / " + status))
                .append($("<div>").text("message_id: " + (item.external_message_id || "-")))
        );
    });
}

function detailItem(label, value) {
    /*
     * Render one key/value item.
     */
    return $("<div>")
        .addClass("detail-item")
        .append($("<div>").addClass("detail-label").text(label))
        .append($("<div>").addClass("detail-value").text(value || "-"));
}

function setAlertsAutoRefresh(enabled) {
    /*
     * Enable or disable alerts auto-refresh.
     */
    if (alertsAutoRefreshTimer) {
        clearInterval(alertsAutoRefreshTimer);
        alertsAutoRefreshTimer = null;
    }

    if (enabled) {
        alertsAutoRefreshTimer = setInterval(loadAlerts, 30000);
    }
}

$(document).on("click", "#reload-alerts", function () {
    loadAlerts();
});

$(document).on("change", "#status-filter", function () {
    resetAlertsPagination();
    writeAlertsQueryParams();
    loadAlerts();
});

$(document).on("change", "#severity-filter, #alerts-sort", function () {
    resetAlertsPagination();
    writeAlertsQueryParams();
    loadAlerts();
});

$(document).on("input", "#alerts-search", function () {
    resetAlertsPagination();
    writeAlertsQueryParams();
    loadAlerts();
});

$(document).on("change", "#alerts-page-size", function () {
    alertsPageSize = Number($(this).val() || 25);
    resetAlertsPagination();
    writeAlertsQueryParams();
    loadAlerts();
});

$(document).on("click", "#alerts-prev-page", function () {
    if (!alertsPagination.has_prev) {
        return;
    }

    alertsCurrentPage = Math.max(1, alertsCurrentPage - 1);
    writeAlertsQueryParams();
    loadAlerts();
});

$(document).on("click", "#alerts-next-page", function () {
    if (!alertsPagination.has_next) {
        return;
    }

    alertsCurrentPage += 1;
    writeAlertsQueryParams();
    loadAlerts();
});

$(document).on("change", "#alerts-auto-refresh", function () {
    setAlertsAutoRefresh($(this).is(":checked"));
});

$(document).on("click", "#close-alert-details", closeAlertDetailsModal);
$(document).on("click", "#close-alert-details-footer", closeAlertDetailsModal);

$(document).on("click", "#alert-details-modal", function (event) {
    if (event.target === this) {
        closeAlertDetailsModal();
    }
});

$(document).on("keydown", function (event) {
    if (event.key === "Escape" && alertDetailsModal().hasClass("is-open")) {
        closeAlertDetailsModal();
    }
});

$(document).on("click", "#modal-alert-ack", function () {
    if (!currentDetailsAlertId) {
        return;
    }

    apiPost("/api/alerts/" + currentDetailsAlertId + "/ack", {}, function () {
        showAlertDetails(currentDetailsAlertId);
        loadAlerts();
    });
});

$(document).on("click", "#modal-alert-resolve", function () {
    if (!currentDetailsAlertId) {
        return;
    }

    apiPost("/api/alerts/" + currentDetailsAlertId + "/resolve", {}, function () {
        showAlertDetails(currentDetailsAlertId);
        loadAlerts();
    });
});
function alertDetailsModal() {
    /*
     * Return the single global alert details modal.
     * The modal must be included only once in index.html.
     */
    return $("#alert-details-modal");
}


function openAlertDetailsModal() {
    /*
     * Open alert details modal.
     */
    const modal = alertDetailsModal();

    if (!modal.length) {
        console.error("Alert details modal not found");
        return;
    }

    modal.css("display", "flex").addClass("is-open");
    $("body").addClass("modal-open");
}


function closeAlertDetailsModal(options) {
    /*
     * Close alert details modal.
     */
    options = options || {};

    alertDetailsModal()
        .css("display", "none")
        .removeClass("is-open");

    $("body").removeClass("modal-open");
    currentDetailsAlertId = null;

    if (options.updateUrl === false) {
        return;
    }

    if (getAlertIdFromPath(window.location.pathname)) {
        const url = buildAlertListUrl();
        history.pushState({ path: url }, "", url);
    }
}
function alertsResponseItems(response) {
    /*
     * Return alerts from the paginated API response.
     */
    if (Array.isArray(response)) {
        return response;
    }

    return asArray(response.items);
}


function alertsResponsePagination(response) {
    /*
     * Return backend pagination metadata.
     */
    if (!response || !response.pagination) {
        return {
            page: alertsCurrentPage,
            page_size: alertsPageSize,
            total_items: 0,
            total_pages: 1,
            from: 0,
            to: 0,
            has_prev: false,
            has_next: false
        };
    }

    return response.pagination;
}


function alertsResponseSummary(response) {
    /*
     * Return backend summary metadata.
     */
    if (!response || !response.summary) {
        return {
            firing: 0,
            acknowledged: 0,
            resolved: 0,
            silenced: 0,
            reminders: 0,
            total: 0
        };
    }

    return response.summary;
}

function renderAlertsInboxCounter(pagination) {
    /*
     * Render "Showing X-Y of Z alerts" counter from backend pagination.
     */
    pagination = pagination || {};

    $("#alerts-page-from").text(pagination.from || 0);
    $("#alerts-page-to").text(pagination.to || 0);
    $("#alerts-filtered-count").text(pagination.total_items || 0);
    $("#alerts-total-count").text(alertsSummary.total || pagination.total_items || 0);

    $("#alerts-total-wrapper").hide();
}
function applyAlertsQueryParams() {
    /*
     * Apply URL query params to alert filters and sorting state.
     *
     * This allows dashboard summary cards to open /alerts with preselected
     * filters, for example /alerts?status=firing.
     */
    const queryString = window.location.search || "";

    if (alertsLastAppliedQueryString === queryString) {
        return;
    }

    alertsLastAppliedQueryString = queryString;

    const params = new URLSearchParams(queryString);

    $("#status-filter").val(params.get("status") || "");
    $("#severity-filter").val(params.get("severity") || "");
    $("#alerts-search").val(params.get("search") || "");

    if (params.get("team_id")) {
        $("#global-team-filter").val(params.get("team_id"));
    }

    if (params.get("page")) {
        alertsCurrentPage = Math.max(1, Number(params.get("page")) || 1);
    } else {
        alertsCurrentPage = 1;
    }

    if (params.get("page_size")) {
        alertsPageSize = Number(params.get("page_size")) || alertsPageSize;
        $("#alerts-page-size").val(String(alertsPageSize));
    }

    if (params.get("sort")) {
        alertsSortState.column = params.get("sort");
    }

    if (params.get("order")) {
        alertsSortState.direction = params.get("order") === "asc" ? "asc" : "desc";
    }

    if (typeof updateSortableTableHeaders === "function") {
        updateSortableTableHeaders("#alerts-table-view", alertsSortState);
    }
}
