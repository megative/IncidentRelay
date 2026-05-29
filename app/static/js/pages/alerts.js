let currentDetailsAlertId = null;
let currentDetailsAlertCanRespond = false;
let alertsCache = [];
let alertsAutoRefreshTimer = null;
let alertsLastAppliedQueryString = null;
let alertsCurrentPage = 1;
let alertsPageSize = 25;
let alertsSortState = createTableSortState("activity", "desc");
let alertsServiceFilterApplying = false;
let alertsServiceFilterLoaded = false;
let alertsPagination = {
    page: 1,
    page_size: 25,
    total_items: 0,
    total_pages: 1,
    from: 0,
    to: 0,
    has_prev: false,
    has_next: false,
};
let alertsSummary = {
    firing: 0,
    acknowledged: 0,
    resolved: 0,
    silenced: 0,
    reminders: 0,
    total: 0,
};

const alertsSortColumns = {
    status: { type: "rank", defaultDirection: "asc" },
    id: { path: "id", type: "number", defaultDirection: "desc" },
    title: { path: "title", type: "text", defaultDirection: "asc" },
    severity: { type: "rank", defaultDirection: "desc" },
    team: {
        value: function (alert) { return alert.team_slug || ""; },
        type: "text",
        defaultDirection: "asc",
    },
    assignee: {
        value: function (alert) { return alert.assignee || ""; },
        type: "text",
        defaultDirection: "asc",
    },
    created: {
        value: function (alert) { return alertCreatedValue(alert); },
        type: "datetime",
        defaultDirection: "desc",
    },
    last_seen: { path: "last_seen_at", type: "datetime", defaultDirection: "desc" },
    reminders: { path: "reminder_count", type: "number", defaultDirection: "desc" },
    activity: {
        value: function (alert) { return alertActivityValue(alert); },
        type: "datetime",
        defaultDirection: "desc",
    },
};

function initAlertsTableSorting() {
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
    return String(value || "").toLowerCase();
}

function alertCreatedValue(alert) {
    return alert.first_seen_at || alert.created_at || null;
}

function alertActivityValue(alert) {
    return alert.last_seen_at || alert.updated_at || alert.created_at || alert.first_seen_at || null;
}

function getAlertIdFromPath(pathname) {
    const match = String(pathname || "").match(/^\/alerts\/(\d+)\/?$/);
    if (!match) {
        return null;
    }
    return Number(match[1]);
}

function buildAlertDetailsUrl(alertId) {
    return "/alerts/" + encodeURIComponent(alertId);
}
function alertServiceLabel(alert) {
    if (!alert.service_id) {
        return "No service";
    }

    return alert.service_name || alert.service_slug || ("Service #" + alert.service_id);
}


function alertServiceDetailsLabel(alert) {
    if (!alert.service_id) {
        return "-";
    }

    const parts = [alertServiceLabel(alert)];

    if (alert.service_criticality) {
        parts.push(alert.service_criticality);
    }

    if (alert.service_status) {
        parts.push(alert.service_status);
    }

    return parts.join(" / ");
}
function buildAlertListUrl() {
    return "/alerts" + (window.location.search || "");
}

function openAlertDetailsPage(alertId) {
    const url = buildAlertDetailsUrl(alertId);
    history.pushState({ path: url }, "", url);
    showAlertDetails(alertId);
}

function syncAlertDetailsFromUrl() {
    const alertId = getAlertIdFromPath(window.location.pathname);
    if (!alertId) {
        if (alertDetailsModal().hasClass("is-open")) {
            closeAlertDetailsModal({ updateUrl: false });
        }
        return;
    }
    if (currentDetailsAlertId === alertId && alertDetailsModal().hasClass("is-open")) {
        return;
    }
    showAlertDetails(alertId);
}

function alertDuration(alert) {
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
    if (value === "warning" || value === "medium") {
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
    return $("<span>")
        .addClass("alerts-pill")
        .addClass(cssClass)
        .text(text || "-");
}

function buildAlertsApiUrl() {
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
    if ($("#alerts-service-filter").val()) {
        params.push("service_id=" + encodeURIComponent($("#alerts-service-filter").val()));
    }

    params.push("page=" + encodeURIComponent(alertsCurrentPage));
    params.push("page_size=" + encodeURIComponent(alertsPageSize));
    params.push("sort=" + encodeURIComponent(alertsSortState.column || "activity"));
    params.push("order=" + encodeURIComponent(alertsSortState.direction || "desc"));
    return "/api/alerts" + (params.length ? "?" + params.join("&") : "");
}

function writeAlertsQueryParams() {
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
    if ($("#alerts-service-filter").val()) {
        params.set("service_id", $("#alerts-service-filter").val());
    }
    if (
        alertsSortState.column &&
        (alertsSortState.column !== "activity" || alertsSortState.direction !== "desc")
    ) {
        params.set("sort", alertsSortState.column);
        params.set("order", alertsSortState.direction || "desc");
    }

    const query = params.toString();
    const nextUrl = window.location.pathname + (query ? "?" + query : "");
    history.replaceState({path: nextUrl}, "", nextUrl);
    alertsLastAppliedQueryString = window.location.search || "";
}

function loadAlerts() {
    applyAlertsQueryParams();
    initAlertsTableSorting();

    loadAlertServiceFilter(function () {
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
    });
}

function renderAlertsPage() {
    renderAlertsSummaryGrid("#alerts-alerts-summary", alertsSummary);
    renderAlertsInboxCounter(alertsPagination);
    renderActiveAlertFilters(alertsPagination);
    renderAlertsTable(alertsCache);
    renderAlertsPagination(alertsPagination);
    syncAlertDetailsFromUrl();
}

function renderAlertsPagination(pagination) {
    pagination = pagination || {};
    $("#alerts-current-page").text(pagination.page || 1);
    $("#alerts-total-pages").text(pagination.total_pages || 1);
    $("#alerts-prev-page").prop("disabled", !pagination.has_prev);
    $("#alerts-next-page").prop("disabled", !pagination.has_next);
    $("#alerts-page-size").val(String(pagination.page_size || alertsPageSize));
    $(".alerts-pagination").toggle((pagination.total_items || 0) > 0);
}

function resetAlertsPagination() {
    alertsCurrentPage = 1;
}

function renderActiveAlertFilters(pagination) {
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
    const tbody = $("#alerts-table");
    tbody.empty();

    if (!alerts.length) {
        tbody.append(
            $("<tr>").append(
                $("<td>").attr("colspan", "11").addClass("empty-table-cell").text("No alerts found")
            )
        );
        return;
    }

    alerts.forEach(function (alert) {
        tbody.append(renderAlertPageRow(alert));
    });
}

function renderAlertPageRow(alert) {
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
            .append($("<div>").addClass("alerts-subtitle").text(buildAlertSubtitle(alert)))
            .append($("<div>").addClass("alerts-age").text("Age: " + alertDuration(alert)))
    );
    row.append($("<td>").append(makeAlertBadge(severityLabel(alert.severity), severityBadgeClass(alert.severity))));
    row.append(
        $("<td>")
            .append($("<div>").addClass("alerts-team").text(alert.team_slug || "-"))
            .append($("<div>").addClass("alerts-subtitle").text(alert.route_name || "No route"))
            .append(
                $("<div>")
                    .addClass("alerts-subtitle")
                    .text(alert.service_id ? "Service: " + alertServiceLabel(alert) : "No service")
            )
    );
    row.append($("<td>").text(alert.assignee || "-"));
    row.append($("<td>").text(formatDateTimeMinutes(alertCreatedValue(alert))));
    row.append($("<td>").text(formatDateTimeMinutes(alert.last_seen_at)));
    row.append($("<td>").append(renderEscalationCell(alert)));
    row.append($("<td>").append(renderReminderCount(alert)));

    const actionsCell = $("<td>").addClass("actions-cell");
    const actions = $("<div>").addClass("table-actions");
    const canRespond = canRespondObject(alert);

    if (canRespond && normalizeAlertValue(alert.status) === "firing") {
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
    if (canRespond && normalizeAlertValue(alert.status) !== "resolved") {
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
function alertServiceLabel(alert) {
    if (!alert.service_id) {
        return "No service";
    }

    return alert.service_name || alert.service_slug || ("Service #" + alert.service_id);
}


function alertServiceDetailsLabel(alert) {
    if (!alert.service_id) {
        return "-";
    }

    const parts = [];

    parts.push(alertServiceLabel(alert));

    if (alert.service_criticality) {
        parts.push(alert.service_criticality);
    }

    if (alert.service_status) {
        parts.push(alert.service_status);
    }

    return parts.join(" / ");
}
function renderReminderCount(alert) {
    const count = alert.reminder_count || 0;
    return $("<span>")
        .addClass("alerts-reminder-badge")
        .toggleClass("is-active", count > 0)
        .text(count);
}
function renderEscalationModeBadge(alert) {
    const isPolicy = !!alert.escalation_policy_name;
    const label = isPolicy ? "Policy" : "Rotation";

    return $("<span>")
        .addClass("alerts-pill")
        .addClass(isPolicy ? "alerts-badge-info" : "alerts-badge-muted")
        .attr("title", isPolicy
            ? "Escalation policy: " + alert.escalation_policy_name
            : "Simple rotation escalation")
        .text(label);
}

function renderEscalationCell(alert) {
    const wrapper = $("<div>").addClass("alerts-escalation-cell");

    wrapper.append(renderEscalationModeBadge(alert));

    if (alert.escalation_policy_name) {
        wrapper.append(
            $("<div>")
                .addClass("alerts-subtitle")
                .text(alert.escalation_policy_name)
        );

        if (alert.escalation_rule_position) {
            wrapper.append(
                $("<div>")
                    .addClass("alerts-subtitle")
                    .text(
                        "Rule #" + alert.escalation_rule_position +
                        " / " + (alert.escalation_rule_target_type || "-")
                    )
            );
        }

        if (alert.next_escalation_at) {
            wrapper.append(
                $("<div>")
                    .addClass("alerts-age")
                    .text("Next: " + formatDateTimeMinutes(alert.next_escalation_at))
            );
        }

        return wrapper;
    }

    wrapper.append(
        $("<div>")
            .addClass("alerts-subtitle")
            .text("Level: " + (alert.escalation_level || 0))
    );

    if (alert.team_escalation_enabled) {
        wrapper.append(
            $("<div>")
                .addClass("alerts-age")
                .text("After " + (alert.team_escalation_after_reminders || 0) + " reminders")
        );
    }

    return wrapper;
}
function alertEscalationModeLabel(alert) {
    if (alert.escalation_policy_name) {
        return "Policy";
    }

    return "Simple rotation";
}

function alertPolicyRuleLabel(alert) {
    if (!alert.escalation_rule_position) {
        return "-";
    }

    const targetType = alert.escalation_rule_target_type || "-";

    return "#" + alert.escalation_rule_position + " / " + targetType;
}
function alertTeamEscalationLabel(alert) {
    if (alert.escalation_policy_name) {
        return "Used only when escalation mode is Rotation";
    }

    if (alert.team_escalation_enabled) {
        return "After " + (alert.team_escalation_after_reminders || 0) + " reminders";
    }

    return "Disabled";
}
function showAlertDetails(alertId) {
    currentDetailsAlertId = alertId;
    apiGet("/api/alerts/" + alertId, function (alert) {
        const modal = alertDetailsModal();
        if (!modal.length) {
            console.error("Alert details modal not found");
            return;
        }

        currentDetailsAlertId = alert.id;
        currentDetailsAlertCanRespond = canRespondObject(alert);

        modal.find("#alert-details-title").text("Alert #" + alert.id + ": " + (alert.title || "-"));
        modal.find("#alert-details-subtitle").text(
            (alert.team_slug || "-") + " / " + (alert.status || "-") + " / " + (alert.severity || "-")
        );
        renderAlertDetailsSummary(alert, modal);
        modal.find("#alert-details-labels").text(JSON.stringify(alert.labels || {}, null, 2));
        modal.find("#alert-details-payload").text(JSON.stringify(alert.payload || {}, null, 2));
        renderEvents(alert.events || [], modal);
        renderNotifications(alert.notifications || [], modal);
        renderAlertServiceContext(alert, modal);

        if (!currentDetailsAlertCanRespond || normalizeAlertValue(alert.status) === "resolved") {
            modal.find("#modal-alert-ack").hide();
            modal.find("#modal-alert-resolve").hide();
        } else {
            modal.find("#modal-alert-ack").toggle(normalizeAlertValue(alert.status) === "firing");
            modal.find("#modal-alert-resolve").show();
        }

        openAlertDetailsModal();
    });
}
function ensureAlertServiceContext(modal) {
    let target = modal.find("#alert-service-context");

    if (target.length) {
        return target;
    }

    target = $("<div>")
        .attr("id", "alert-service-context")
        .addClass("alert-service-context");

    modal.find("#alert-details-summary").after(target);

    return target;
}


function renderAlertServiceContext(alert, modal) {
    const target = ensureAlertServiceContext(modal);
    target.empty();

    if (!alert.service_id) {
        target.hide();
        return;
    }

    target.show();

    target.append(
        $("<div>")
            .addClass("alert-service-context-header")
            .append($("<h3>").text("Service context"))
            .append(
                $("<div>")
                    .addClass("card-subtitle")
                    .text(alertServiceDetailsLabel(alert))
            )
    );

    const linksList = $("<div>")
        .attr("id", "alert-service-links")
        .addClass("alert-service-context-list")
        .append($("<div>").addClass("help-text").text("Loading links..."));

    const runbooksList = $("<div>")
        .attr("id", "alert-service-runbooks")
        .addClass("alert-service-context-list")
        .append($("<div>").addClass("help-text").text("Loading runbooks..."));

    target.append(
        $("<div>")
            .addClass("alert-service-context-grid")
            .append(
                $("<section>")
                    .addClass("alert-service-context-section")
                    .append($("<h4>").text("Links"))
                    .append(linksList)
            )
            .append(
                $("<section>")
                    .addClass("alert-service-context-section")
                    .append($("<h4>").text("Runbooks"))
                    .append(runbooksList)
            )
    );

    apiGet("/api/services/" + alert.service_id + "/links", function (links) {
        renderAlertServiceLinks(asArray(links));
    });

    apiGet("/api/services/" + alert.service_id + "/runbooks", function (runbooks) {
        renderAlertServiceRunbooks(alert, asArray(runbooks));
    });
}


function renderAlertServiceLinks(links) {
    const target = $("#alert-service-links");
    target.empty();

    const enabledLinks = links.filter(function (link) {
        return !!link.enabled;
    });

    if (!enabledLinks.length) {
        target.append($("<div>").addClass("help-text").text("No links."));
        return;
    }

    enabledLinks.forEach(function (link) {
        target.append(
            $("<a>")
                .addClass("alert-service-context-link")
                .attr("href", link.url)
                .attr("target", "_blank")
                .attr("rel", "noopener noreferrer")
                .append($("<span>").addClass("alert-service-context-title").text(link.label || link.url))
                .append(
                    $("<span>")
                        .addClass("alert-service-context-meta")
                        .text(link.link_type || "other")
                )
        );
    });
}


function renderAlertServiceRunbooks(alert, runbooks) {
    const target = $("#alert-service-runbooks");
    target.empty();

    const matchedRunbooks = runbooks.filter(function (runbook) {
        return !!runbook.enabled && alertMatchesRunbook(alert, runbook);
    });

    if (!matchedRunbooks.length) {
        target.append($("<div>").addClass("help-text").text("No matching runbooks."));
        return;
    }

    matchedRunbooks.forEach(function (runbook) {
        target.append(
            $("<a>")
                .addClass("alert-service-context-link")
                .attr("href", runbook.url)
                .attr("target", "_blank")
                .attr("rel", "noopener noreferrer")
                .append($("<span>").addClass("alert-service-context-title").text(runbook.title || runbook.url))
                .append(
                    $("<span>")
                        .addClass("alert-service-context-meta")
                        .text(
                            [
                                runbook.severity ? "severity: " + runbook.severity : null,
                                runbook.description || null,
                            ].filter(Boolean).join(" / ") || "runbook"
                        )
                )
        );
    });
}


function alertMatchesRunbook(alert, runbook) {
    if (runbook.severity && normalizeAlertValue(runbook.severity) !== normalizeAlertValue(alert.severity)) {
        return false;
    }

    return alertMatchesSimpleMatchers(alert, runbook.matchers || {});
}


function alertMatchesSimpleMatchers(alert, matchers) {
    const matcherKeys = Object.keys(matchers || {});

    if (!matcherKeys.length) {
        return true;
    }

    const labels = alert.labels || {};
    const expectedLabels = matchers.labels || {};

    for (const key in expectedLabels) {
        if (!Object.prototype.hasOwnProperty.call(expectedLabels, key)) {
            continue;
        }

        const expected = expectedLabels[key];
        const actual = labels[key];

        if (Array.isArray(expected)) {
            if (expected.map(String).indexOf(String(actual)) === -1) {
                return false;
            }
            continue;
        }

        if (String(actual) !== String(expected)) {
            return false;
        }
    }

    return true;
}
function renderAlertDetailsSummary(alert, modal) {
    const summary = modal.find("#alert-details-summary");
    summary.empty();

    summary.append(detailItem("Source", alert.source));
    summary.append(detailItem("External ID", alert.external_id));
    summary.append(detailItem("Route", alert.route_name));
    summary.append(detailItem("Service", alertServiceDetailsLabel(alert)));
    summary.append(detailItem("Service status", alert.service_status));
    summary.append(detailItem("Service criticality", alert.service_criticality));
    summary.append(detailItem("Escalation mode", alertEscalationModeLabel(alert)));
    summary.append(detailItem("Escalation policy", alert.escalation_policy_name));
    summary.append(detailItem("Policy rule", alertPolicyRuleLabel(alert)));
    summary.append(detailItem("Rotation", alert.rotation_name));
    summary.append(detailItem("Assignee", alert.assignee));
    summary.append(detailItem("Next escalation", formatDateTimeMinutes(alert.next_escalation_at)));
    summary.append(detailItem("Last escalated", formatDateTimeMinutes(alert.last_escalated_at)));
    summary.append(detailItem("Escalation level", alert.escalation_level || 0));
    summary.append(detailItem("Policy repeat count", alert.escalation_repeat_count || 0));
    summary.append(detailItem("Default rotation", alertTeamEscalationLabel(alert)));
    summary.append(detailItem("Acknowledged by", alert.acknowledged_by));
    summary.append(detailItem("Created", formatDateTimeMinutes(alert.first_seen_at || alert.created_at)));
    summary.append(detailItem("Last seen", formatDateTimeMinutes(alert.last_seen_at)));
    summary.append(detailItem("Last notification", formatDateTimeMinutes(alert.last_notification_at)));
    summary.append(detailItem("Group key", alert.group_key));
    summary.append(detailItem("Dedup key", alert.dedup_key));
    summary.append(detailItem("Reminder count", alert.reminder_count || 0));
    summary.append(detailItem(
        "Reminder interval",
        alert.rotation_reminder_interval_seconds
            ? alert.rotation_reminder_interval_seconds + "s"
            : "-"
    ));
}

function renderEvents(events, modal) {
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
                .append($("<div>").text(formatDateTimeMinutes(event.created_at) + " " + (event.message || "")))
        );
    });
}

function renderNotifications(notifications, modal) {
    const target = modal.find("#alert-details-notifications");
    target.empty();
    if (!notifications.length) {
        target.append($("<div>").addClass("help-text").text("No delivery records."));
        return;
    }

    notifications.forEach(function (item) {
        const channel = item.channel ? item.channel.name + " (" + item.channel.channel_type + ")" : "-";
        const status = item.last_error ? "failed: " + item.last_error : (item.last_event_type || "sent");
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
    return $("<div>")
        .addClass("detail-item")
        .append($("<div>").addClass("detail-label").text(label))
        .append($("<div>").addClass("detail-value").text(value || "-"));
}

function setAlertsAutoRefresh(enabled) {
    if (alertsAutoRefreshTimer) {
        clearInterval(alertsAutoRefreshTimer);
        alertsAutoRefreshTimer = null;
    }
    if (enabled) {
        alertsAutoRefreshTimer = setInterval(loadAlerts, 30000);
    }
}

function alertDetailsModal() {
    return $("#alert-details-modal");
}

function openAlertDetailsModal() {
    const modal = alertDetailsModal();
    if (!modal.length) {
        console.error("Alert details modal not found");
        return;
    }
    modal.css("display", "flex").addClass("is-open");
    $("body").addClass("modal-open");
}

function closeAlertDetailsModal(options) {
    options = options || {};
    alertDetailsModal()
        .css("display", "none")
        .removeClass("is-open");
    $("body").removeClass("modal-open");
    currentDetailsAlertId = null;
    currentDetailsAlertCanRespond = false;

    if (options.updateUrl === false) {
        return;
    }
    if (getAlertIdFromPath(window.location.pathname)) {
        const url = buildAlertListUrl();
        history.pushState({ path: url }, "", url);
    }
}

function alertsResponseItems(response) {
    if (Array.isArray(response)) {
        return response;
    }
    return asArray(response.items);
}

function alertsResponsePagination(response) {
    if (!response || !response.pagination) {
        return {
            page: alertsCurrentPage,
            page_size: alertsPageSize,
            total_items: 0,
            total_pages: 1,
            from: 0,
            to: 0,
            has_prev: false,
            has_next: false,
        };
    }
    return response.pagination;
}

function alertsResponseSummary(response) {
    if (!response || !response.summary) {
        return {
            firing: 0,
            acknowledged: 0,
            resolved: 0,
            silenced: 0,
            reminders: 0,
            total: 0,
        };
    }
    return response.summary;
}

function renderAlertsInboxCounter(pagination) {
    pagination = pagination || {};
    $("#alerts-page-from").text(pagination.from || 0);
    $("#alerts-page-to").text(pagination.to || 0);
    $("#alerts-filtered-count").text(pagination.total_items || 0);
    $("#alerts-total-count").text(alertsSummary.total || pagination.total_items || 0);
    $("#alerts-total-wrapper").hide();
}

function applyAlertsQueryParams() {
    const queryString = window.location.search || "";
    if (alertsLastAppliedQueryString === queryString) {
        return;
    }

    alertsLastAppliedQueryString = queryString;
    const params = new URLSearchParams(queryString);
    $("#status-filter").val(params.get("status") || "");
    $("#severity-filter").val(params.get("severity") || "");
    $("#alerts-search").val(params.get("search") || "");
    $("#alerts-service-filter").val(params.get("service_id") || "");

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

$(document).on("click", "#reload-alerts", function () {
    loadAlerts();
});
$(document).on("change", "#status-filter", function () {
    resetAlertsPagination();
    writeAlertsQueryParams();
    loadAlerts();
});
$(document).on("change", "#severity-filter", function () {
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
    if (!currentDetailsAlertCanRespond) {
        showAppError("You do not have permission to acknowledge this alert.");
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
    if (!currentDetailsAlertCanRespond) {
        showAppError("You do not have permission to resolve this alert.");
        return;
    }

    apiPost("/api/alerts/" + currentDetailsAlertId + "/resolve", {}, function () {
        showAlertDetails(currentDetailsAlertId);
        loadAlerts();
    });
});
$(document).on("change", "#alerts-service-filter", function () {
    if (alertsServiceFilterApplying) {
        return;
    }

    resetAlertsPagination();
    writeAlertsQueryParams();
    loadAlerts();
});
function loadAlertServiceFilter(callback) {
    const select = $("#alerts-service-filter");

    if (!select.length) {
        if (typeof callback === "function") {
            callback();
        }
        return;
    }

    const params = new URLSearchParams(window.location.search || "");
    const currentValue = select.val() || params.get("service_id") || "";

    alertsServiceFilterApplying = true;

    select.empty();
    select.append($("<option>").val("").text("All services"));

    apiGet("/api/services" + selectedTeamQuery(), function (services) {
        asArray(services).forEach(function (service) {
            if (!service.enabled) {
                return;
            }

            select.append(
                $("<option>")
                    .val(String(service.id))
                    .text(
                        (service.team_slug || service.team_name || "-")
                        + " / "
                        + (service.name || service.slug || service.id)
                    )
            );
        });

        if (currentValue) {
            select.val(String(currentValue));
        }

        alertsServiceFilterLoaded = true;
        alertsServiceFilterApplying = false;

        if (typeof callback === "function") {
            callback();
        }
    });
}
