function dashboardAsArray(value) {
    /*
     * Return alerts from both old array responses and new paginated responses.
     */
    if (Array.isArray(value)) {
        return value;
    }
    if (value && Array.isArray(value.items)) {
        return value.items;
    }
    return [];
}

function dashboardDateValue(alert) {
    return alert.updated_at || alert.last_seen_at || alert.first_seen_at || alert.created_at || null;
}

function dashboardSortByActivity(alerts) {
    return alerts.slice().sort(function (left, right) {
        const leftDate = new Date(dashboardDateValue(left) || 0).getTime();
        const rightDate = new Date(dashboardDateValue(right) || 0).getTime();
        return rightDate - leftDate;
    });
}

function dashboardGroupCount(alerts, fieldName, fallback) {
    const result = {};
    alerts.forEach(function (alert) {
        const key = alert[fieldName] || fallback || "-";
        result[key] = (result[key] || 0) + 1;
    });
    return result;
}

function dashboardActiveAlerts(alerts) {
    return alerts.filter(function (alert) {
        return alert.status === "firing" || alert.status === "acknowledged";
    });
}
function dashboardEscalationText(alert) {
    if (alert.escalation_policy_name) {
        const rule = alert.escalation_rule_position
            ? " · rule #" + alert.escalation_rule_position
            : "";

        return "Policy: " + alert.escalation_policy_name + rule;
    }

    return "Rotation: " + (alert.rotation_name || "-");
}
function loadDashboard() {
    const params = [];
    if (typeof selectedTeamId === "function" && selectedTeamId()) {
        params.push("team_id=" + encodeURIComponent(selectedTeamId()));
    }
    params.push("page=1");
    params.push("page_size=100");
    params.push("sort=activity");
    params.push("order=desc");

    apiGet("/api/alerts?" + params.join("&"), function (response) {
        const alerts = dashboardAsArray(response);
        const activeAlerts = dashboardActiveAlerts(alerts);
        const sortedAlerts = dashboardSortByActivity(alerts);
        const sortedActiveAlerts = dashboardSortByActivity(activeAlerts);

        renderAlertsSummaryGrid("#overview-alerts-summary", alerts);
        renderDashboardAlertsTable(sortedActiveAlerts.slice(0, 15));
        renderDashboardRecentAlerts(sortedAlerts.slice(0, 5));
        renderDashboardTeamsNow(activeAlerts);
        renderDashboardSeveritySplit(alerts);
        renderDashboardTeamSummary(alerts);
        renderDashboardSystemStatus(alerts, activeAlerts);
    });
    loadDashboardServiceImpact();
}

function renderDashboardAlertsTable(alerts) {
    const tbody = $("#dashboard-alerts");
    tbody.empty();

    if (!alerts.length) {
        tbody.append(
            $("<tr>").append(
                $("<td>")
                    .attr("colspan", "8")
                    .addClass("empty-table-cell")
                    .text("No active incidents")
            )
        );
        return;
    }

    alerts.forEach(function (alert) {
        tbody.append(renderDashboardAlertRow(alert));
    });
}

function renderDashboardAlertRow(alert) {
    const row = $("<tr>");

    row.append(
        $("<td>").append(
            $("<button>")
                .attr("type", "button")
                .attr("title", "Show alert details")
                .addClass("overview-id-link")
                .text("#" + alert.id)
                .on("click", function () {
                    if (typeof showAlertDetails === "function") {
                        showAlertDetails(alert.id);
                    }
                })
        )
    );
    row.append(
        $("<td>")
            .addClass("overview-alert-title-cell")
            .append($("<div>").addClass("overview-alert-title").text(alert.title || "-"))
            .append($("<div>").addClass("overview-alert-meta").text((alert.source || alert.route_name || "Alert") + " · " + dashboardEscalationText(alert)))
    );
    row.append(
        $("<td>").append(
            makeAlertBadge(
                severityLabel(alert.severity),
                severityBadgeClass(alert.severity)
            )
        )
    );
    row.append(
        $("<td>").append(
            makeAlertBadge(alert.status || "-", statusBadgeClass(alert.status))
        )
    );
    row.append($("<td>").text(alert.team_slug || "-"));
    row.append($("<td>").addClass("overview-duration-cell").text(alertDuration(alert)));
    row.append($("<td>").text(formatDateTimeMinutes(dashboardDateValue(alert))));

    const actionsCell = $("<td>").addClass("actions-cell");
    const actions = $("<div>").addClass("table-actions");

    if (canRespondObject(alert)) {
        if (alert.status === "firing") {
            actions.append(
                $("<button>")
                    .attr("type", "button")
                    .addClass("btn btn-warning btn-small")
                    .text("Ack")
                    .on("click", function () {
                        apiPost("/api/alerts/" + alert.id + "/ack", {}, loadDashboard);
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
                        apiPost("/api/alerts/" + alert.id + "/resolve", {}, loadDashboard);
                    })
            );
        }
    }

    actionsCell.append(actions);
    row.append(actionsCell);
    return row;
}

function renderDashboardRecentAlerts(alerts) {
    const target = $("#dashboard-recent-alerts");
    target.empty();

    if (!alerts.length) {
        target.append($("<div>").addClass("overview-empty").text("No alerts yet"));
        return;
    }

    alerts.forEach(function (alert) {
        const item = $("<button>")
            .attr("type", "button")
            .addClass("overview-list-item overview-list-button")
            .on("click", function () {
                if (typeof showAlertDetails === "function") {
                    showAlertDetails(alert.id);
                }
            });

        item.append(
            $("<span>")
                .addClass("overview-list-dot")
                .addClass("overview-dot-" + normalizeAlertValue(alert.status))
        );
        item.append(
            $("<span>")
                .addClass("overview-list-main")
                .append($("<span>").addClass("overview-list-title").text(alert.title || "-"))
                .append(
                    $("<span>")
                        .addClass("overview-list-subtitle")
                        .text(
                            (alert.team_slug || "-") +
                            " · " +
                            severityLabel(alert.severity) +
                            " · " +
                            dashboardEscalationText(alert)
                        )
                )
        );
        item.append(
            $("<span>")
                .addClass("overview-list-time")
                .text(formatDateTimeMinutes(dashboardDateValue(alert)))
        );
        target.append(item);
    });
}

function renderDashboardTeamsNow(activeAlerts) {
    const target = $("#dashboard-teams-now");
    target.empty();

    if (!activeAlerts.length) {
        target.append($("<div>").addClass("overview-empty").text("No teams with active incidents"));
        return;
    }

    const counts = dashboardGroupCount(activeAlerts, "team_slug", "Unknown team");
    const items = Object.keys(counts)
        .map(function (team) {
            return { team: team, count: counts[team] };
        })
        .sort(function (left, right) {
            return right.count - left.count;
        });

    items.slice(0, 6).forEach(function (item) {
        target.append(
            $("<div>")
                .addClass("overview-list-item")
                .append(
                    $("<span>")
                        .addClass("overview-team-avatar")
                        .text(item.team.slice(0, 2).toUpperCase())
                )
                .append(
                    $("<span>")
                        .addClass("overview-list-main")
                        .append($("<span>").addClass("overview-list-title").text(item.team))
                        .append($("<span>").addClass("overview-list-subtitle").text("Active alerts"))
                )
                .append(
                    $("<span>")
                        .addClass("overview-team-count")
                        .text(item.count)
                )
        );
    });
}

function renderDashboardSeveritySplit(alerts) {
    const target = $("#dashboard-severity-split");
    target.empty();
    const counts = dashboardGroupCount(alerts, "severity", "unknown");
    const order = ["critical", "high", "medium", "low", "unknown"];
    renderDashboardBars(target, counts, order, alerts.length, severityLabel);
}

function renderDashboardTeamSummary(alerts) {
    const target = $("#dashboard-team-summary");
    target.empty();
    const counts = dashboardGroupCount(alerts, "team_slug", "Unknown team");
    const order = Object.keys(counts).sort(function (left, right) {
        return counts[right] - counts[left];
    });
    renderDashboardBars(target, counts, order.slice(0, 8), alerts.length, function (value) {
        return value;
    });
}

function renderDashboardBars(target, counts, order, total, labelFunction) {
    if (!total) {
        target.append($("<div>").addClass("overview-empty").text("No data"));
        return;
    }

    order.forEach(function (key) {
        const count = counts[key] || 0;
        if (!count) {
            return;
        }
        const percent = Math.round((count / total) * 100);
        target.append(
            $("<div>")
                .addClass("overview-bar-row")
                .append(
                    $("<div>")
                        .addClass("overview-bar-meta")
                        .append($("<span>").text(labelFunction(key)))
                        .append($("<span>").text(count))
                )
                .append(
                    $("<div>")
                        .addClass("overview-bar-track")
                        .append(
                            $("<div>")
                                .addClass("overview-bar-fill")
                                .attr("style", "width: " + percent + "%;")
                        )
                )
        );
    });
}

function renderDashboardSystemStatus(alerts, activeAlerts) {
    const target = $("#dashboard-system-status");
    const firing = activeAlerts.filter(function (alert) {
        return alert.status === "firing";
    }).length;

    if (!alerts.length) {
        target.text("No alerts in the current selection.");
        return;
    }
    if (firing > 0) {
        target.text(firing + " firing alert" + (firing === 1 ? "" : "s") + " require attention.");
        return;
    }
    if (activeAlerts.length > 0) {
        target.text(activeAlerts.length + " active alert" + (activeAlerts.length === 1 ? "" : "s") + " acknowledged.");
        return;
    }
    target.text("All tracked alerts are resolved.");
}

$(document).on("click", "#reload-dashboard", loadDashboard);
function dashboardSelectedTeamQuery() {
    if (typeof selectedTeamId === "function" && selectedTeamId()) {
        return "?team_id=" + encodeURIComponent(selectedTeamId());
    }

    return "";
}

function dashboardDisplayName(name, slug, fallback) {
    return name || slug || fallback || "-";
}

function dashboardImpactStatusRank(status) {
    const ranks = {
        disabled: 0,
        operational: 1,
        unknown: 2,
        maintenance: 3,
        degraded: 4,
        partial_outage: 5,
        major_outage: 6,
    };

    return ranks[status || "unknown"] || 0;
}

function dashboardImpactStatusLabel(status) {
    return String(status || "unknown").replace(/_/g, " ");
}

function dashboardImpactStatusCssClass(status) {
    const normalized = status || "unknown";

    return {
        major_outage: "impact-status-major",
        partial_outage: "impact-status-partial",
        degraded: "impact-status-degraded",
        maintenance: "impact-status-maintenance",
        operational: "impact-status-operational",
        disabled: "impact-status-neutral",
        unknown: "impact-status-neutral"
    }[normalized] || "impact-status-neutral";
}

function dashboardImpactBadge(status) {
    const normalized = status || "unknown";

    return $("<span>")
        .addClass("status-pill impact-status-pill")
        .addClass(dashboardImpactStatusCssClass(normalized))
        .text(dashboardImpactStatusLabel(normalized));
}

function dashboardImpactIssueRootCause(issue) {
    return dashboardDisplayName(
        issue.root_cause_service_name,
        issue.root_cause_service_slug,
        issue.root_cause_service_display
    );
}

function dashboardImpactIssuePath(issue) {
    const path = dashboardAsArray(issue.path);

    if (!path.length) {
        return dashboardDisplayName(
            issue.service_name,
            issue.service_slug,
            issue.service_display
        );
    }

    return path.map(function (node) {
        return dashboardDisplayName(
            node.service_name,
            node.service_slug,
            node.service_display
        );
    }).join(" → ");
}

function dashboardBestImpactIssue(row) {
    const issues = dashboardAsArray(row.upstream_issues);

    if (!issues.length) {
        return null;
    }

    return issues
        .slice()
        .sort(function (left, right) {
            return dashboardImpactStatusRank(right.impact_status || right.status)
                - dashboardImpactStatusRank(left.impact_status || left.status);
        })[0];
}

function dashboardImpactRows(rows) {
    return dashboardAsArray(rows)
        .filter(function (row) {
            return row.effective_status
                && row.effective_status !== "operational"
                && row.effective_status !== "disabled";
        })
        .sort(function (left, right) {
            return dashboardImpactStatusRank(right.effective_status)
                - dashboardImpactStatusRank(left.effective_status)
                || Number(right.critical_open_alerts || 0) - Number(left.critical_open_alerts || 0)
                || Number(right.open_alerts || 0) - Number(left.open_alerts || 0);
        });
}

function loadDashboardServiceImpact() {
    apiGet("/api/services/impact" + dashboardSelectedTeamQuery(), function (rows) {
        renderDashboardServiceImpact(dashboardImpactRows(rows));
    });
}

function renderDashboardServiceImpact(rows) {
    const target = $("#dashboard-service-impact");
    target.empty();

    $("#dashboard-impacted-services-count").text(rows.length);

    if (!rows.length) {
        target.append(
            $("<div>")
                .addClass("overview-empty")
                .text("No impacted services")
        );
        return;
    }

    rows.slice(0, 5).forEach(function (row) {
        target.append(renderDashboardServiceImpactItem(row));
    });

    if (rows.length > 5) {
        target.append(
            $("<button>")
                .attr("type", "button")
                .addClass("overview-list-item overview-list-button dashboard-impact-more")
                .text("+" + (rows.length - 5) + " more impacted service" + (rows.length - 5 === 1 ? "" : "s"))
                .on("click", function () {
                    navigate("/services", true);
                })
        );
    }
}

function renderDashboardServiceImpactItem(row) {
    const serviceName = dashboardDisplayName(
        row.service_name,
        row.service_slug,
        "Service #" + row.service_id
    );

    const teamName = dashboardDisplayName(row.team_name, row.team_slug);
    const issue = dashboardBestImpactIssue(row);

    const item = $("<button>")
        .attr("type", "button")
        .addClass("overview-list-item overview-list-button dashboard-impact-item")
        .addClass(
            "dashboard-impact-item-"
            + String(row.effective_status || "unknown").replace(/_/g, "-")
        )
        .on("click", function () {
            navigate("/services", true);
        });

    item.append(
        $("<span>")
            .addClass("overview-list-dot")
            .addClass("overview-dot-" + String(row.effective_status || "unknown").replace(/_/g, "-"))
    );

    const main = $("<div>").addClass("overview-list-main");

    main.append(
        $("<div>")
            .addClass("overview-list-title dashboard-impact-title")
            .text(serviceName)
    );

    const subtitleParts = [
        teamName,
        "open " + Number(row.open_alerts || 0),
    ];

    if (Number(row.critical_open_alerts || 0) > 0) {
        subtitleParts.push("critical " + Number(row.critical_open_alerts || 0));
    }

    main.append(
        $("<div>")
            .addClass("overview-list-subtitle")
            .text(subtitleParts.join(" · "))
    );

    if (issue) {
        main.append(
            $("<div>")
                .addClass("dashboard-impact-root")
                .text(
                    "Root cause: "
                    + dashboardImpactIssueRootCause(issue)
                    + " · "
                    + dashboardImpactIssuePath(issue)
                )
        );
    } else if (row.has_alert_impact) {
        main.append(
            $("<div>")
                .addClass("dashboard-impact-root")
                .text("Caused by open alerts")
        );
    }

    item.append(main);

    item.append(
        $("<div>")
            .addClass("dashboard-impact-status")
            .append(dashboardImpactBadge(row.effective_status))
    );

    return item;
}
