let routesCache = [];
let selectedRouteDetailsId = null;
let routesSortState = createTableSortState("id", "desc");
const routesSortColumns = {
    name: {path: "name", type: "text", defaultDirection: "asc"},
    team: {path: "team_slug", type: "text", defaultDirection: "asc"},
    source: {path: "source", type: "text", defaultDirection: "asc"},
    rotation: {
        value: function (route) {
            return route.escalation_policy_name || route.rotation_name || "";
        },
        type: "text",
        defaultDirection: "asc"
    },
    channels: {
        value: function (route) {
            return asArray(route.channels).map(function (channel) {
                return channel.name || "";
            }).join(", ");
        },
        type: "text",
        defaultDirection: "asc",
    },
    enabled: {path: "enabled", type: "boolean", defaultDirection: "desc"},
};
let selectedRouteForServiceRules = null;
let routeServiceRulesCache = [];
function getRouteEscalationLabel(route) {
    if (route.escalation_policy_name) {
        return "Policy: " + route.escalation_policy_name;
    }

    if (route.rotation_name) {
        return "Rotation: " + route.rotation_name;
    }

    return "-";
}
function getRouteTeamEscalationLabel(route) {
    if (route.escalation_policy_name) {
        return "Ignored for policy mode";
    }

    if (route.team_escalation_enabled) {
        return "After " + (route.team_escalation_after_reminders || 0) + " reminders";
    }

    return "Disabled";
}
function loadRoutes() {
    fillTeamSelect("#route-team", false, loadRouteDependencies);
    initRoutesTableSorting();
    refreshRoutes();
}

function loadRouteDependencies(callback) {
    const teamId = $("#route-team").val();

    const rotationSelect = $("#route-rotation");
    const channelSelect = $("#route-channels");
    const policySelect = $("#route-escalation-policy");
    const serviceSelect = $("#route-service");

    rotationSelect.empty().append($("<option>").val("").text("No rotation"));
    channelSelect.empty();

    if (policySelect.length) {
        policySelect.empty().append($("<option>").val("").text("No policy"));
    }

    if (serviceSelect.length) {
        serviceSelect.empty().append($("<option>").val("").text("No default service"));
    }

    if (!teamId) {
        if (typeof callback === "function") {
            callback();
        }
        return;
    }

    let rotationsLoaded = false;
    let channelsLoaded = false;
    let policiesLoaded = !policySelect.length;
    let servicesLoaded = !serviceSelect.length;

    function finishWhenReady() {
        if (!rotationsLoaded || !channelsLoaded || !policiesLoaded || !servicesLoaded) {
            return;
        }

        if (typeof callback === "function") {
            callback();
        }
    }

    apiGet("/api/rotations?team_id=" + encodeURIComponent(teamId), function (rotations) {
        rotationSelect.empty().append($("<option>").val("").text("No rotation"));

        asArray(rotations).forEach(function (rotation) {
            if (!rotation.enabled) {
                return;
            }

            rotationSelect.append(
                $("<option>")
                    .val(String(rotation.id))
                    .text(rotation.name)
            );
        });

        rotationsLoaded = true;
        finishWhenReady();
    });

    apiGet("/api/channels?team_id=" + encodeURIComponent(teamId), function (channels) {
        channelSelect.empty();

        asArray(channels).forEach(function (channel) {
            if (!channel.enabled) {
                return;
            }

            channelSelect.append(
                $("<option>")
                    .val(String(channel.id))
                    .text(channel.name + " (" + channel.channel_type + ")")
            );
        });

        channelsLoaded = true;
        finishWhenReady();
    });

    if (policySelect.length) {
        apiGet("/api/escalation-policies?team_id=" + encodeURIComponent(teamId), function (policies) {
            policySelect.empty().append($("<option>").val("").text("No policy"));

            asArray(policies).forEach(function (policy) {
                if (!policy.enabled) {
                    return;
                }

                policySelect.append(
                    $("<option>")
                        .val(String(policy.id))
                        .text(policy.name)
                );
            });

            policiesLoaded = true;
            finishWhenReady();
        });
    }

    if (serviceSelect.length) {
        apiGet("/api/services?team_id=" + encodeURIComponent(teamId), function (services) {
            serviceSelect.empty().append($("<option>").val("").text("No default service"));

            asArray(services).forEach(function (service) {
                if (!service.enabled) {
                    return;
                }

                serviceSelect.append(
                    $("<option>")
                        .val(String(service.id))
                        .text(service.name + " (" + service.slug + ")")
                );
            });

            servicesLoaded = true;
            finishWhenReady();
        });
    }
}

function refreshRoutes() {
    apiGet("/api/routes" + selectedTeamQuery(), function (routes) {
        routesCache = asArray(routes);
        renderRoutesSummary(routesCache);
        fillRouteSourceFilter(routesCache);
        renderRoutesTable();
        restoreRouteDetails();
    });
}

function renderRoutesSummary(routes) {
    routes = asArray(routes);

    const enabled = routes.filter(function (route) {
        return !!route.enabled;
    }).length;

    const withEscalation = routes.filter(function (route) {
        return !!route.rotation_id || !!route.rotation_name ||
            !!route.escalation_policy_id || !!route.escalation_policy_name;
    }).length;

    $("#routes-summary-total").text(routes.length);
    $("#routes-summary-enabled").text(enabled);
    $("#routes-summary-disabled").text(routes.length - enabled);
    $("#routes-summary-rotation").text(withEscalation);
}

function fillRouteSourceFilter(routes) {
    const filter = $("#routes-source-filter");
    const selected = filter.val();
    const sources = { alertmanager: true, zabbix: true, webhook: true };

    asArray(routes).forEach(function (route) {
        if (route.source) {
            sources[route.source] = true;
        }
    });

    filter.empty();
    filter.append($("<option>").val("").text("All sources"));
    Object.keys(sources).sort().forEach(function (source) {
        filter.append($("<option>").val(source).text(source));
    });
    if (selected && sources[selected]) {
        filter.val(selected);
    }
}

function getRouteSearchText(route) {
    const channels = asArray(route.channels).map(function (channel) {
        return channel.name + " " + channel.channel_type;
    }).join(" ");

    return [
        route.id,
        route.team_slug,
        route.name,
        route.source,
        route.rotation_name,
        route.escalation_policy_name,
        route.intake_token_prefix,
        route.enabled ? "enabled" : "disabled",
        channels,
        route.service_name,
        route.service_slug,
    ].join(" ").toLowerCase();
}

function renderRoutesCounter(filteredRoutes, allRoutes) {
    filteredRoutes = asArray(filteredRoutes);
    allRoutes = asArray(allRoutes);
    $("#routes-filtered-count").text(filteredRoutes.length);
    $("#routes-total-count").text(allRoutes.length);
}

function renderRoutesTable() {
    const tbody = $("#routes-table");
    const routes = getFilteredRoutes();
    tbody.empty();
    renderRoutesCounter(routes, routesCache);

    if (!routes.length) {
        tbody.append(
            $("<tr>").append(
                $("<td>").attr("colspan", "8").addClass("empty-cell").text("No routes")
            )
        );
        return;
    }

    routes.forEach(function (route) {
        tbody.append(renderRouteRow(route));
    });
}

function renderRouteRow(route) {
    const row = $("<tr>");
    const channels = asArray(route.channels);

    row.append(
        $("<td>")
            .append(
                $("<button>")
                    .attr("type", "button")
                    .addClass("name-button")
                    .text(route.name || "-")
                    .on("click", function () {
                        renderRouteDetails(route);
                    })
            )
            .append($("<div>").addClass("row-subtitle").text("Route #" + route.id))
    );
    row.append($("<td>").append($("<span>").addClass("route-pill").text(route.team_slug || "-")));
    row.append($("<td>").text(route.source || "-"));
    row.append($("<td>").text(getRouteEscalationLabel(route)));
    row.append($("<td>").append(renderRouteChannels(channels)));
    row.append($("<td>").append($("<span>").addClass("token-pill").text(route.intake_token_prefix || "-")));
    row.append($("<td>").append(renderStatusBadge(route.enabled, "Enabled", "Disabled")));
    row.append($("<td>").addClass("actions-cell").append(renderRouteActions(route)));
    return row;
}

function renderRouteChannels(channels) {
    const wrapper = $("<div>").addClass("route-channels-list");
    channels = asArray(channels);
    if (!channels.length) {
        return wrapper.append($("<span>").text("-"));
    }
    channels.forEach(function (channel) {
        wrapper.append($("<span>").addClass("route-channel-chip").text(channel.name || channel.id));
    });
    return wrapper;
}

function renderRouteActions(route) {
    /*
     * Render route row actions as a shared three-dots menu.
     */
    return makeActionMenu({
        object: route,
        items: [
            {
                label: "Edit",
                icon: "fas fa-edit",
                required: "write",
                denyMessage: "Team manager role is required to edit this route.",
                onClick: function () {
                    editRoute(route.id);
                }
            },
            {
                label: "Regenerate token",
                icon: "fas fa-sync-alt",
                required: "write",
                denyMessage: "Team manager role is required to regenerate route tokens.",
                onClick: function () {
                    regenerateRouteToken(route.id);
                }
            },
            {
                label: "Service rules",
                icon: "fas fa-project-diagram",
                required: "write",
                denyMessage: "Team manager role is required to manage service rules.",
                onClick: function () {
                    openRouteServiceRules(route.id);
                }
            },
            {
                label: route.enabled ? "Disable" : "Enable",
                icon: route.enabled ? "fas fa-pause" : "fas fa-play",
                required: "write",
                danger: route.enabled,
                denyMessage: "Team manager role is required to enable or disable this route.",
                onClick: function () {
                    if (route.enabled) {
                        disableRoute(route);
                    } else {
                        enableRoute(route);
                    }
                }
            },
            {
                label: "Delete",
                icon: "fas fa-trash",
                required: "delete",
                danger: true,
                denyMessage: "Delete permission is required to delete this route.",
                onClick: function () {
                    deleteRoute(route);
                }
            }
        ]
    });
}
function getSelectedRouteForServiceRules() {
    if (!selectedRouteForServiceRules) {
        return null;
    }

    return routesCache.find(function (route) {
        return Number(route.id) === Number(selectedRouteForServiceRules);
    }) || null;
}

function openRouteServiceRules(routeId) {
    const route = routesCache.find(function (item) {
        return Number(item.id) === Number(routeId);
    });

    if (!route) {
        return;
    }

    if (!canWriteObject(route)) {
        showAppError("You do not have permission to manage service rules for this route.");
        return;
    }

    selectedRouteForServiceRules = route.id;

    $("#route-service-rules-title").text("Service rules / " + (route.name || ("Route #" + route.id)));
    $("#service-rule-team").val(route.team_id);
    $("#service-rule-route").val(route.id);

    resetServiceRuleForm();

    loadServiceRuleServices(route.team_id, function () {
        refreshRouteServiceRules();
        openAppModal("#route-service-rules-modal");
    });
}

function loadServiceRuleServices(teamId, callback) {
    const select = $("#service-rule-service");

    select.empty();
    select.append($("<option>").val("").text("Select service"));

    if (!teamId) {
        if (typeof callback === "function") {
            callback();
        }
        return;
    }

    apiGet("/api/services?team_id=" + encodeURIComponent(teamId), function (services) {
        select.empty();
        select.append($("<option>").val("").text("Select service"));

        asArray(services).forEach(function (service) {
            if (!service.enabled) {
                return;
            }

            select.append(
                $("<option>")
                    .val(String(service.id))
                    .text(service.name + " (" + service.slug + ")")
            );
        });

        if (typeof callback === "function") {
            callback();
        }
    });
}

function refreshRouteServiceRules() {
    const route = getSelectedRouteForServiceRules();

    if (!route) {
        routeServiceRulesCache = [];
        renderRouteServiceRulesTable();
        return;
    }

    apiGet(
        "/api/services/match-rules?route_id=" + encodeURIComponent(route.id),
        function (rules) {
            routeServiceRulesCache = asArray(rules);
            renderRouteServiceRulesTable();
        }
    );
}

function renderRouteServiceRulesTable() {
    const tbody = $("#route-service-rules-table");

    tbody.empty();

    if (!routeServiceRulesCache.length) {
        tbody.append(
            $("<tr>").append(
                $("<td>")
                    .attr("colspan", "6")
                    .addClass("empty-cell")
                    .text("No service rules")
            )
        );
        return;
    }

    routeServiceRulesCache.forEach(function (rule) {
        tbody.append(renderRouteServiceRuleRow(rule));
    });
}

function renderRouteServiceRuleRow(rule) {
    const row = $("<tr>");

    row.append($("<td>").text(rule.position || 0));

    row.append(
        $("<td>")
            .addClass("table-cell-truncate")
            .attr("title", rule.name || "-")
            .text(rule.name || "-")
    );

    row.append(
        $("<td>")
            .addClass("table-cell-truncate")
            .attr("title", rule.service_name || rule.service_slug || "-")
            .text(rule.service_name || rule.service_slug || "-")
    );

    row.append(
        $("<td>").append(
            $("<code>")
                .addClass("inline-code")
                .text(JSON.stringify(rule.matchers || {}))
        )
    );

    row.append(
        $("<td>").append(
            renderStatusBadge(rule.enabled, "Enabled", "Disabled")
        )
    );

    row.append(
        $("<td>")
            .addClass("actions-cell")
            .append(
                makeActionMenu({
                    object: getSelectedRouteForServiceRules(),
                    items: [
                        {
                            label: "Edit",
                            icon: "fas fa-edit",
                            required: "write",
                            onClick: function () {
                                editRouteServiceRule(rule);
                            }
                        },
                        {
                            label: "Delete",
                            icon: "fas fa-trash",
                            required: "write",
                            danger: true,
                            onClick: function () {
                                deleteRouteServiceRule(rule);
                            }
                        }
                    ]
                })
            )
    );

    return row;
}

function resetServiceRuleForm() {
    const route = getSelectedRouteForServiceRules();

    $("#service-rule-form-title").text("Create rule");
    $("#service-rule-id").val("");
    $("#service-rule-team").val(route ? route.team_id : "");
    $("#service-rule-route").val(route ? route.id : "");
    $("#service-rule-name").val("");
    $("#service-rule-service").val("");
    $("#service-rule-position").val("0");
    $("#service-rule-matchers").val(JSON.stringify({
        labels: {
            cluster: "cloud-postgresql"
        }
    }, null, 2));
    $("#service-rule-enabled").prop("checked", true);
}

function editRouteServiceRule(rule) {
    $("#service-rule-form-title").text("Edit rule #" + rule.id);
    $("#service-rule-id").val(rule.id);
    $("#service-rule-team").val(rule.team_id);
    $("#service-rule-route").val(rule.route_id || "");
    $("#service-rule-name").val(rule.name || "");
    $("#service-rule-service").val(rule.service_id || "");
    $("#service-rule-position").val(rule.position || 0);
    $("#service-rule-matchers").val(JSON.stringify(rule.matchers || {}, null, 2));
    $("#service-rule-enabled").prop("checked", !!rule.enabled);
}

function collectRouteServiceRulePayload() {
    return {
        team_id: Number($("#service-rule-team").val()),
        route_id: $("#service-rule-route").val()
            ? Number($("#service-rule-route").val())
            : null,
        service_id: Number($("#service-rule-service").val()),
        position: Number($("#service-rule-position").val() || 0),
        name: $("#service-rule-name").val(),
        description: null,
        matchers: parseJsonInput("#service-rule-matchers", {}),
        enabled: $("#service-rule-enabled").is(":checked"),
    };
}

function saveRouteServiceRule() {
    const id = $("#service-rule-id").val();
    const payload = collectRouteServiceRulePayload();

    if (!payload.service_id) {
        showAppError("Service is required.");
        return;
    }

    if (id) {
        apiPut("/api/services/match-rules/" + id, payload, function () {
            resetServiceRuleForm();
            refreshRouteServiceRules();
        });
        return;
    }

    apiPost(
        "/api/services/" + payload.service_id + "/match-rules",
        payload,
        function () {
            resetServiceRuleForm();
            refreshRouteServiceRules();
        }
    );
}

function deleteRouteServiceRule(rule) {
    showAppConfirm({
        title: "Delete this service rule?",
        message: "Delete service rule \"" + (rule.name || ("#" + rule.id)) + "\"?",
        confirmText: "Delete",
        confirmClass: "btn-danger",
    }).done(function () {
        apiDelete("/api/services/match-rules/" + rule.id, function () {
            refreshRouteServiceRules();
        });
    });
}
function routeDetailsItem(label, value) {
    return $("<div>")
        .addClass("details-item")
        .append($("<div>").addClass("details-label").text(label))
        .append($("<div>").addClass("details-value").text(value || "-"));
}

function routeDetailsCode(label, value) {
    return $("<div>")
        .addClass("details-item")
        .append($("<div>").addClass("details-label").text(label))
        .append($("<pre>").addClass("details-code").text(JSON.stringify(value || {}, null, 2)));
}

function renderRouteDetails(route) {
    selectedRouteDetailsId = route.id;

    $("#route-details-subtitle").text((route.team_slug || "-") + " / " + (route.enabled ? "Enabled" : "Disabled"));

    const body = $("#route-details-body");
    body.empty();
    body.append(
        $("<div>")
            .addClass("details-list")
            .append(routeDetailsItem("Name", route.name))
            .append(routeDetailsItem("Team", route.team_slug))
            .append(routeDetailsItem("Source", route.source))
            .append(routeDetailsItem("Escalation", getRouteEscalationLabel(route)))
            .append(routeDetailsItem("Team escalation", getRouteTeamEscalationLabel(route)))
            .append(routeDetailsItem("Channels", asArray(route.channels).map(function (channel) {
                return channel.name;
            }).join(", ") || "-"))
            .append(routeDetailsItem("Token prefix", route.intake_token_prefix))
            .append(routeDetailsItem("Status", route.enabled ? "Enabled" : "Disabled"))
            .append(routeDetailsCode("Matchers", route.matchers || {}))
            .append(routeDetailsCode("Group by", route.group_by || []))
            .append(routeDetailsItem("Service", route.service_name || route.service_slug || "-"))
    );

    const actions = $("<div>").addClass("details-actions");
    appendIconActionIfAllowed(actions, route, {
        required: "write",
        icon: "fas fa-edit",
        label: "Edit route",
        onClick: function () {
            editRoute(route.id);
        },
    });
    appendIconActionIfAllowed(actions, route, {
        required: "write",
        icon: "fas fa-sync-alt",
        label: "Regenerate route token",
        onClick: function () {
            regenerateRouteToken(route.id);
        },
    });
    appendIconActionIfAllowed(actions, route, {
        required: "write",
        icon: route.enabled ? "fas fa-pause" : "fas fa-play",
        label: route.enabled ? "Disable route" : "Enable route",
        className: route.enabled ? "btn-warning" : "btn-success",
        onClick: function () {
            if (route.enabled) {
                disableRoute(route);
            } else {
                enableRoute(route);
            }
        },
    });
    appendIconActionIfAllowed(actions, route, {
        required: "delete",
        icon: "fas fa-trash-alt",
        label: "Delete route",
        className: "btn-danger",
        onClick: function () {
            deleteRoute(route);
        },
    });

    if (actions.children().length) {
        body.append(actions);
    }
}

function renderRouteDetailsEmpty() {
    selectedRouteDetailsId = null;
    $("#route-details-subtitle").text("Select a route");
    $("#route-details-body").html("<p class=\"muted\">Click a route name to inspect matchers, group by, channels and intake token prefix.</p>");
}

function restoreRouteDetails() {
    if (!routesCache.length) {
        renderRouteDetailsEmpty();
        return;
    }

    if (selectedRouteDetailsId) {
        const selected = routesCache.find(function (route) {
            return Number(route.id) === Number(selectedRouteDetailsId);
        });
        if (selected) {
            renderRouteDetails(selected);
            return;
        }
    }

    renderRouteDetails(routesCache[0]);
}

function collectRoutePayload() {
    const selectedPolicyId = $("#route-escalation-policy").val();
    const selectedRotationId = $("#route-rotation").val();

    let escalationMode = $("#route-escalation-mode").val() || "rotation";

    if (selectedPolicyId) {
        escalationMode = "policy";
    }

    const usePolicy = escalationMode === "policy";

    return {
        team_id: Number($("#route-team").val()),
        name: $("#route-name").val(),
        source: $("#route-source").val(),

        escalation_mode: escalationMode,

        rotation_id: !usePolicy && selectedRotationId
            ? Number(selectedRotationId)
            : null,

        escalation_policy_id: usePolicy && selectedPolicyId
            ? Number(selectedPolicyId)
            : null,

        service_id: $("#route-service").val()
            ? Number($("#route-service").val())
            : null,

        channel_ids: ($("#route-channels").val() || []).map(Number),
        matchers: parseJsonInput("#route-matchers", {}),
        group_by: parseJsonInput("#route-group-by", []),
        enabled: $("#route-enabled").is(":checked"),
    };
}

function saveRoute() {
    const id = $("#route-id").val();
    const existing = id ? routesCache.find(function (item) { return Number(item.id) === Number(id); }) : null;
    if (existing && !canWriteObject(existing)) {
        showAppError("You do not have permission to edit this route.");
        return;
    }

    if (id) {
        apiPut("/api/routes/" + id, collectRoutePayload(), function () {
            closeAppModal("#route-form-modal");
            resetRouteForm();
            refreshRoutes();
        });
        return;
    }

    apiPost("/api/routes", collectRoutePayload(), function (response) {
        closeAppModal("#route-form-modal");
        resetRouteForm();
        refreshRoutes();
        showRouteToken(response.intake_token);
    });
}

function editRoute(id) {
    const route = routesCache.find(function (item) {
        return Number(item.id) === Number(id);
    });
    if (!route) {
        return;
    }
    if (!canWriteObject(route)) {
        showAppError("You do not have permission to edit this route.");
        return;
    }

    $("#route-form-title").text("Edit route #" + id);
    $("#route-id").val(route.id);
    $("#route-team").val(route.team_id);
    $("#route-name").val(route.name);
    $("#route-source").val(route.source);
    $("#route-matchers").val(JSON.stringify(route.matchers || {}, null, 2));
    $("#route-group-by").val(JSON.stringify(route.group_by || [], null, 2));
    $("#route-enabled").prop("checked", !!route.enabled);

    loadRouteDependencies(function () {
        const usePolicy = !!route.escalation_policy_id;

        $("#route-escalation-mode").val(usePolicy ? "policy" : "rotation");
        $("#route-rotation").val(route.rotation_id || "");
        $("#route-escalation-policy").val(route.escalation_policy_id || "");

        $("#route-channels").val(asArray(route.channels).map(function (channel) {
            return String(channel.id);
        }));

        $("#route-service").val(route.service_id || "");

        updateRouteEscalationModeUi();
    });

    openAppModal("#route-form-modal");
}

function disableRoute(route) {
    if (!canWriteObject(route)) {
        showAppError("You do not have permission to disable this route.");
        return;
    }

    const routeName = route.name || ("Route #" + route.id);
    showAppConfirm({
        title: "Disable this route?",
        message: "Disable route \"" + routeName + "\"?\n\nThe route will stop accepting incoming alerts, but it will stay visible and can be enabled again.",
        confirmText: "Disable",
        confirmClass: "btn-warning",
    }).done(function () {
        apiPost("/api/routes/" + route.id + "/disable", {}, function () {
            refreshRoutes();
        });
    });
}

function enableRoute(route) {
    if (!canWriteObject(route)) {
        showAppError("You do not have permission to enable this route.");
        return;
    }

    apiPost("/api/routes/" + route.id + "/enable", {}, function () {
        refreshRoutes();
    });
}

function deleteRoute(route) {
    if (!canDeleteObject(route)) {
        showAppError("You do not have permission to delete this route.");
        return;
    }

    const routeName = route.name || ("Route #" + route.id);
    showAppConfirm({
        title: "Delete this route?",
        message: "Delete route \"" + routeName + "\"?\n\nThis will remove the route from active route lists and stop alert intake for this route. Historical alerts will be preserved.",
        confirmText: "Delete",
        confirmClass: "btn-danger",
    }).done(function () {
        apiDelete("/api/routes/" + route.id, function () {
            if (Number(selectedRouteDetailsId) === Number(route.id)) {
                selectedRouteDetailsId = null;
                renderRouteDetailsEmpty();
            }
            refreshRoutes();
        });
    });
}

function resetRouteForm() {
    $("#route-form-title").text("Create route");
    $("#route-id").val("");
    $("#route-name").val("");
    $("#route-source").val("alertmanager");
    $("#route-matchers").val("{}");
    $("#route-group-by").val('["alertname","instance"]');
    $("#route-enabled").prop("checked", true);
    $("#route-rotation").val("");
    $("#route-channels").val([]);
    $("#route-escalation-mode").val("rotation");
    $("#route-escalation-policy").val("");
    $("#route-service").val("");
    updateRouteEscalationModeUi();
}

function showRouteToken(token) {
    openAppModal("#route-token-box");
    $("#route-intake-token").val(token || "");
}

function closeRouteTokenModal() {
    closeAppModal("#route-token-box");
    $("#route-intake-token").val("");
}

function regenerateRouteToken(routeId) {
    const route = routesCache.find(function (item) {
        return Number(item.id) === Number(routeId);
    });
    if (route && !canWriteObject(route)) {
        showAppError("You do not have permission to regenerate this route token.");
        return;
    }

    showAppConfirm({
        title: "Regenerate route intake token?",
        message: "Regenerate route intake token? Existing token will stop working.",
        confirmText: "Regenerate",
        confirmClass: "btn-warning",
    }).done(function () {
        apiPost("/api/routes/" + routeId + "/intake-token", {}, function (response) {
            showRouteToken(response.intake_token);
            refreshRoutes();
        });
    });
}

function openCreateRouteModal() {
    resetRouteForm();
    $("#route-form-title").text("Create route");
    loadRouteDependencies();
    openAppModal("#route-form-modal");
}

function copyRouteIntakeToken() {
    const token = $("#route-intake-token").val() || "";
    if (!token) {
        return;
    }
    if (navigator.clipboard && navigator.clipboard.writeText) {
        navigator.clipboard.writeText(token);
        return;
    }

    const field = $("#route-intake-token");
    field.trigger("select");
    document.execCommand("copy");
}

function initRoutesTableSorting() {
    bindSortableTableHeaders(
        "#routes-table-view",
        routesSortState,
        routesSortColumns,
        renderRoutesTable
    );
}

function getFilteredRoutes() {
    const query = String($("#routes-search").val() || "").trim().toLowerCase();
    const source = String($("#routes-source-filter").val() || "");
    const status = String($("#routes-status-filter").val() || "");

    const filtered = routesCache.filter(function (route) {
        if (source && route.source !== source) {
            return false;
        }
        if (status === "enabled" && !route.enabled) {
            return false;
        }
        if (status === "disabled" && route.enabled) {
            return false;
        }
        if (!query) {
            return true;
        }
        return getRouteSearchText(route).indexOf(query) !== -1;
    });

    return sortTableData(filtered, routesSortState, routesSortColumns);
}

$(document).on("change", "#route-team", function () {
    loadRouteDependencies();
});
$(document).on("change", "#route-escalation-mode", updateRouteEscalationModeUi);
$(document).on("input", "#routes-search", renderRoutesTable);
$(document).on("change", "#routes-source-filter, #routes-status-filter", renderRoutesTable);
$(document).on("click", "#open-route-create-modal", openCreateRouteModal);
$(document).on("click", "#save-route", saveRoute);
$(document).on("click", "#reset-route-form", resetRouteForm);
$(document).on("click", "#reload-routes", refreshRoutes);
$(document).on("click", "#close-route-form-modal", function () {
    closeAppModal("#route-form-modal");
});
$(document).on("click", "#close-route-token-modal, #close-route-token-modal-footer", closeRouteTokenModal);
$(document).on("click", "#copy-route-intake-token", copyRouteIntakeToken);
$(document).on("click", "#route-form-modal", function (event) {
    if (event.target === this) {
        closeAppModal("#route-form-modal");
    }
});
$(document).on("click", "#route-token-box", function (event) {
    if (event.target === this) {
        closeRouteTokenModal();
    }
});
$(document).on("keydown", function (event) {
    if (event.key !== "Escape") {
        return;
    }
    if ($("#route-token-box").hasClass("is-open")) {
        closeRouteTokenModal();
        return;
    }
    if ($("#route-form-modal").hasClass("is-open")) {
        closeAppModal("#route-form-modal");
    }
});
$(document).on("click", "#format-route-matchers", function () {
    formatJsonTextarea("#route-matchers", {}, "Alert filters JSON");
});
$(document).on("change", "#route-rotation", function () {
    if ($(this).val()) {
        $("#route-escalation-mode").val("rotation");
        $("#route-escalation-policy").val("");
    }

    updateRouteEscalationModeUi();
});
$(document).on("change", "#route-escalation-policy", function () {
    if ($(this).val()) {
        $("#route-escalation-mode").val("policy");
    }

    updateRouteEscalationModeUi();
});
function updateRouteEscalationModeUi() {
    const mode = $("#route-escalation-mode").val() || "rotation";
    const usePolicy = mode === "policy";

    $("#route-rotation")
        .prop("disabled", usePolicy)
        .closest(".form-group")
        .toggleClass("is-muted", usePolicy);

    $("#route-escalation-policy")
        .prop("disabled", !usePolicy);

    $("#route-policy-group").toggleClass("is-hidden", !usePolicy);
}
$(document).on("change", "#route-escalation-mode", updateRouteEscalationModeUi);
$(document).on("click", "#save-service-rule", saveRouteServiceRule);

$(document).on("click", "#reset-service-rule-form", resetServiceRuleForm);

$(document).on("click", "#format-service-rule-matchers", function () {
    try {
        const value = JSON.parse($("#service-rule-matchers").val() || "{}");
        $("#service-rule-matchers").val(JSON.stringify(value, null, 2));
    } catch (error) {
        showAppError("Invalid JSON: " + error.message);
    }
});

$(document).on("click", "#close-route-service-rules-modal", function () {
    closeAppModal("#route-service-rules-modal");
});

$(document).on("click", "#route-service-rules-modal", function (event) {
    if (event.target === this) {
        closeAppModal("#route-service-rules-modal");
    }
});
$(document).on("click", "#format-service-rule-matchers", function () {
    formatJsonTextarea("#service-rule-matchers", {}, "Matchers JSON");
});
