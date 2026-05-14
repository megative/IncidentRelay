let routesCache = [];
let selectedRouteDetailsId = null;
let routesSortState = createTableSortState("id", "desc");

const routesSortColumns = {
    name: {
        path: "name",
        type: "text",
        defaultDirection: "asc"
    },
    team: {
        path: "team_slug",
        type: "text",
        defaultDirection: "asc"
    },
    source: {
        path: "source",
        type: "text",
        defaultDirection: "asc"
    },
    rotation: {
        path: "rotation_name",
        type: "text",
        defaultDirection: "asc"
    },
    channels: {
        value: function (route) {
            return asArray(route.channels)
                .map(function (channel) {
                    return channel.name || "";
                })
                .join(", ");
        },
        type: "text",
        defaultDirection: "asc"
    },
    enabled: {
        path: "enabled",
        type: "boolean",
        defaultDirection: "desc"
    }
};

function loadRoutes() {
    /*
     * Load routes page.
     */
    fillTeamSelect("#route-team", false, loadRouteDependencies);
    initRoutesTableSorting();
    refreshRoutes();
}


function loadRouteDependencies(callback) {
    /*
     * Load rotations and channels for the selected route team.
     *
     * The callback is called only after both selects are filled. This is
     * important for edit mode, because route channel ids can be selected only
     * after channel <option> elements exist in the DOM.
     */
    const teamId = $("#route-team").val();
    const rotationSelect = $("#route-rotation");
    const channelSelect = $("#route-channels");

    rotationSelect.empty();
    channelSelect.empty();

    if (!teamId) {
        rotationSelect.append(
            $("<option>")
                .val("")
                .text("No rotation")
        );

        if (typeof callback === "function") {
            callback();
        }

        return;
    }

    let rotationsLoaded = false;
    let channelsLoaded = false;

    function finishWhenReady() {
        /*
         * Run callback after both async requests have completed.
         */
        if (!rotationsLoaded || !channelsLoaded) {
            return;
        }

        if (typeof callback === "function") {
            callback();
        }
    }

    apiGet("/api/rotations?team_id=" + encodeURIComponent(teamId), function (rotations) {
        rotationSelect.empty();

        rotationSelect.append(
            $("<option>")
                .val("")
                .text("No rotation")
        );

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
}


function refreshRoutes() {
    /*
     * Refresh routes table.
     */
    apiGet("/api/routes" + selectedTeamQuery(), function (routes) {
        routesCache = asArray(routes);

        renderRoutesSummary(routesCache);
        fillRouteSourceFilter(routesCache);
        renderRoutesTable();
        restoreRouteDetails();
    });
}


function renderRoutesSummary(routes) {
    /*
     * Render routes summary cards.
     */
    routes = asArray(routes);

    const enabled = routes.filter(function (route) {
        return !!route.enabled;
    }).length;

    const withRotation = routes.filter(function (route) {
        return !!route.rotation_id || !!route.rotation_name;
    }).length;

    $("#routes-summary-total").text(routes.length);
    $("#routes-summary-enabled").text(enabled);
    $("#routes-summary-disabled").text(routes.length - enabled);
    $("#routes-summary-rotation").text(withRotation);
}


function fillRouteSourceFilter(routes) {
    /*
     * Fill source filter from loaded routes and known sources.
     */
    const filter = $("#routes-source-filter");
    const selected = filter.val();

    const sources = {
        alertmanager: true,
        zabbix: true,
        webhook: true
    };

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
    /*
     * Build searchable route text.
     */
    const channels = asArray(route.channels).map(function (channel) {
        return channel.name + " " + channel.channel_type;
    }).join(" ");

    return [
        route.id,
        route.team_slug,
        route.name,
        route.source,
        route.rotation_name,
        route.intake_token_prefix,
        route.enabled ? "enabled" : "disabled",
        channels
    ].join(" ").toLowerCase();
}

function renderRoutesCounter(filteredRoutes, allRoutes) {
    /*
     * Render "Showing X of Y routes".
     */
    filteredRoutes = asArray(filteredRoutes);
    allRoutes = asArray(allRoutes);

    $("#routes-filtered-count").text(filteredRoutes.length);
    $("#routes-total-count").text(allRoutes.length);
}


function renderRoutesTable() {
    /*
     * Render filtered routes table.
     */
    const tbody = $("#routes-table");
    const routes = getFilteredRoutes();

    tbody.empty();
    renderRoutesCounter(routes, routesCache);

    if (!routes.length) {
        tbody.append(
            $("<tr>").append(
                $("<td>")
                    .attr("colspan", "8")
                    .addClass("empty-cell")
                    .text("No routes")
            )
        );
        return;
    }

    routes.forEach(function (route) {
        tbody.append(renderRouteRow(route));
    });
}


function renderRouteRow(route) {
    /*
     * Render one route row.
     */
    const row = $("<tr>");
    const channels = asArray(route.channels);

    row.append(
        $("<td>")
            .append(
                $("<button>")
                    .attr("type", "button")
                    .addClass("route-name-button")
                    .text(route.name || "-")
                    .on("click", function () {
                        renderRouteDetails(route);
                    })
            )
            .append(
                $("<div>")
                    .addClass("row-subtitle")
                    .text("Route #" + route.id)
            )
    );

    row.append(
        $("<td>").append(
            $("<span>")
                .addClass("route-pill")
                .text(route.team_slug || "-")
        )
    );

    row.append($("<td>").text(route.source || "-"));
    row.append($("<td>").text(route.rotation_name || "-"));

    row.append($("<td>").append(renderRouteChannels(channels)));

    row.append(
        $("<td>").append(
            $("<span>")
                .addClass("token-pill")
                .text(route.intake_token_prefix || "-")
        )
    );

    row.append(
        $("<td>").append(
            renderStatusBadge(route.enabled ? "Enabled" : "Disabled")

        )
    );

    row.append($("<td>").addClass("actions-cell").append(renderRouteActions(route)));

    return row;
}


function renderRouteChannels(channels) {
    /*
     * Render route channel chips.
     */
    const wrapper = $("<div>").addClass("route-channels-list");

    channels = asArray(channels);

    if (!channels.length) {
        return wrapper.append($("<span>").text("-"));
    }

    channels.forEach(function (channel) {
        wrapper.append(
            $("<span>")
                .addClass("route-channel-chip")
                .text(channel.name || channel.id)
        );
    });

    return wrapper;
}


function renderRouteActions(route) {
    /*
     * Render row actions.
     */
    const actions = $("<div>").addClass("table-actions");

    actions.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-small")
            .text("Edit")
            .on("click", function () {
                editRoute(route.id);
            })
    );

    actions.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-small")
            .text("Regenerate token")
            .on("click", function () {
                regenerateRouteToken(route.id);
            })
    );

    if (route.enabled) {
        actions.append(
            $("<button>")
                .attr("type", "button")
                .addClass("btn btn-warning btn-small")
                .text("Disable")
                .on("click", function () {
                    disableRoute(route);
                })
        );
    } else {
        actions.append(
            $("<button>")
                .attr("type", "button")
                .addClass("btn btn-success btn-small")
                .text("Enable")
                .on("click", function () {
                    enableRoute(route);
                })
        );
    }

    actions.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-danger btn-small")
            .text("Delete")
            .on("click", function () {
                deleteRoute(route);
            })
    );

    return actions;
}


function routeDetailsItem(label, value) {
    /*
     * Render one details item.
     */
    return $("<div>")
        .addClass("details-item")
        .append($("<div>").addClass("details-label").text(label))
        .append($("<div>").addClass("details-value").text(value || "-"));
}


function routeDetailsCode(label, value) {
    /*
     * Render one JSON details item.
     */
    return $("<div>")
        .addClass("details-item")
        .append($("<div>").addClass("details-label").text(label))
        .append(
            $("<pre>")
                .addClass("details-code")
                .text(JSON.stringify(value || {}, null, 2))
        );
}


function renderRouteDetails(route) {
    /*
     * Render selected route details.
     */
    selectedRouteDetailsId = route.id;

    $("#route-details-subtitle").text(
        (route.team_slug || "-") + " / " + (route.enabled ? "Enabled" : "Disabled")
    );

    const body = $("#route-details-body");
    body.empty();

    body.append(
        $("<div>")
            .addClass("details-list")
            .append(routeDetailsItem("Name", route.name))
            .append(routeDetailsItem("Team", route.team_slug))
            .append(routeDetailsItem("Source", route.source))
            .append(routeDetailsItem("Rotation", route.rotation_name))
            .append(routeDetailsItem("Channels", asArray(route.channels).map(function (channel) {
                return channel.name;
            }).join(", ") || "-"))
            .append(routeDetailsItem("Token prefix", route.intake_token_prefix))
            .append(routeDetailsItem("Status", route.enabled ? "Enabled" : "Disabled"))
            .append(routeDetailsCode("Matchers", route.matchers || {}))
            .append(routeDetailsCode("Group by", route.group_by || []))
    );

    body.append(
        $("<div>")
            .addClass("details-actions")
            .append(
                makeIconButton({
                    icon: "fas fa-edit",
                    label: "Edit route",
                    onClick: function () {
                        editRoute(route.id);
                    }
                })
            )
            .append(
                makeIconButton({
                    icon: "fas fa-sync-alt",
                    label: "Regenerate route token",
                    onClick: function () {
                        regenerateRouteToken(route.id);
                    }
                })
            )
            .append(
                makeIconButton({
                    icon: "fas fa-pause",
                    label: "Disable route",
                    className: "btn-warning",
                    onClick: function () {
                        deleteRoute(route.id);
                    }
                })
            )
    );
}


function renderRouteDetailsEmpty() {
    /*
     * Render empty route details state.
     */
    selectedRouteDetailsId = null;

    $("#route-details-subtitle").text("Select a route");
    $("#route-details-body").html(
        '<div class="details-empty">' +
        'Click a route name to inspect matchers, group by, channels and intake token prefix.' +
        '</div>'
    );
}


function restoreRouteDetails() {
    /*
     * Restore selected route details after reload.
     */
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
    /*
     * Build route payload.
     */
    return {
        team_id: Number($("#route-team").val()),
        name: $("#route-name").val(),
        source: $("#route-source").val(),
        rotation_id: $("#route-rotation").val() ? Number($("#route-rotation").val()) : null,
        channel_ids: ($("#route-channels").val() || []).map(Number),
        matchers: parseJsonInput("#route-matchers", {}),
        group_by: parseJsonInput("#route-group-by", []),
        enabled: $("#route-enabled").is(":checked")
    };
}


function saveRoute() {
    /*
     * Create or update route.
     */
    const id = $("#route-id").val();

    if (id) {
        apiPut("/api/routes/" + id, collectRoutePayload(), function () {
            closeRouteFormModal();
            resetRouteForm();
            refreshRoutes();
        });
        return;
    }

    apiPost("/api/routes", collectRoutePayload(), function (response) {
        closeRouteFormModal();
        resetRouteForm();
        refreshRoutes();
        showRouteToken(response.intake_token);
    });
}


function editRoute(id) {
    /*
     * Load route data into the form.
     */
    const route = routesCache.find(function (item) {
        return Number(item.id) === Number(id);
    });

    if (!route) {
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
        $("#route-rotation").val(route.rotation_id || "");
        $("#route-channels").val(asArray(route.channels).map(function (channel) {
            return String(channel.id);
        }));
    });

    openRouteFormModal();
}


function disableRoute(route) {
    /*
     * Disable a route without deleting it.
     */
    const routeName = route.name || ("Route #" + route.id);

    showAppConfirm({
        title: "Disable this route?",
        message: (
            "Disable route \"" + routeName + "\"?\n\n" +
            "The route will stop accepting incoming alerts, but it will stay " +
            "visible and can be enabled again."
        ),
        confirmText: "Disable",
        confirmClass: "btn-warning",
    }).done(function () {
        apiPost("/api/routes/" + route.id + "/disable", {}, function () {
            refreshRoutes();
            showAppSuccess("Route disabled.");
        });
    });
}


function enableRoute(route) {
    /*
     * Enable a disabled route.
     */
    apiPost("/api/routes/" + route.id + "/enable", {}, function () {
        refreshRoutes();
        showAppSuccess("Route enabled.");
    });
}


function deleteRoute(route) {
    /*
     * Soft-delete a route.
     */
    const routeName = route.name || ("Route #" + route.id);

    showAppConfirm({
        title: "Delete this route?",
        message: (
            "Delete route \"" + routeName + "\"?\n\n" +
            "This will remove the route from active route lists and stop " +
            "alert intake for this route. Historical alerts will be preserved."
        ),
        confirmText: "Delete",
        confirmClass: "btn-danger",
    }).done(function () {
        apiDelete("/api/routes/" + route.id, function () {
            if (Number(selectedRouteDetailsId) === Number(route.id)) {
                selectedRouteDetailsId = null;
                renderRouteDetailsEmpty();
            }

            refreshRoutes();
            showAppSuccess("Route deleted.");
        });
    });
}


function resetRouteForm() {
    /*
     * Reset route form.
     */
    $("#route-form-title").text("Create route");
    $("#route-id").val("");
    $("#route-name").val("");
    $("#route-source").val("alertmanager");
    $("#route-matchers").val('{}');
    $("#route-group-by").val('["alertname","instance"]');
    $("#route-enabled").prop("checked", true);
    $("#route-rotation").val("");
    $("#route-channels").val([]);
}


function showRouteToken(token) {
    /*
     * Show route token once.
     */
    $("#route-token-box")
        .css("display", "flex")
        .addClass("is-open");

    $("body").addClass("modal-open");
    $("#route-intake-token").val(token || "");
}


function closeRouteTokenModal() {
    /*
     * Close route token modal.
     */
    $("#route-token-box")
        .css("display", "none")
        .removeClass("is-open");

    $("body").removeClass("modal-open");
    $("#route-intake-token").val("");
}


function regenerateRouteToken(routeId) {
    /*
     * Regenerate route intake token.
     */
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


function openRouteFormModal() {
    /*
     * Open route create/edit modal.
     */
    $("#route-form-modal")
        .css("display", "flex")
        .addClass("is-open");

    $("body").addClass("modal-open");
}


function closeRouteFormModal() {
    /*
     * Close route create/edit modal.
     */
    $("#route-form-modal")
        .css("display", "none")
        .removeClass("is-open");

    $("body").removeClass("modal-open");
}


function openCreateRouteModal() {
    /*
     * Reset form and open create modal.
     */
    resetRouteForm();
    $("#route-form-title").text("Create route");
    loadRouteDependencies();
    openRouteFormModal();
}


function copyRouteIntakeToken() {
    /*
     * Copy intake token to clipboard.
     */
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


$(document).on("change", "#route-team", function () {
    loadRouteDependencies();
});

$(document).on("input", "#routes-search", renderRoutesTable);
$(document).on("change", "#routes-source-filter, #routes-status-filter", renderRoutesTable);

$(document).on("click", "#open-route-create-modal", openCreateRouteModal);
$(document).on("click", "#save-route", saveRoute);
$(document).on("click", "#reset-route-form", resetRouteForm);
$(document).on("click", "#reload-routes", refreshRoutes);

$(document).on("click", "#close-route-form-modal", closeRouteFormModal);
$(document).on("click", "#close-route-token-modal, #close-route-token-modal-footer", closeRouteTokenModal);
$(document).on("click", "#copy-route-intake-token", copyRouteIntakeToken);

$(document).on("click", "#route-form-modal", function (event) {
    if (event.target === this) {
        closeRouteFormModal();
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
        closeRouteFormModal();
    }
});

function initRoutesTableSorting() {
    bindSortableTableHeaders(
        "#routes-table-view",
        routesSortState,
        routesSortColumns,
        renderRoutesTable
    );
}

function getFilteredRoutes() {
    const filtered = routesCache.filter(function (route) {
        /*
         * Existing filters.
         */
        return true;
    });

    return sortTableData(filtered, routesSortState, routesSortColumns);
}

$(document).on("click", "#format-route-matchers", function () {
    formatJsonTextarea("#route-matchers", {}, "Alert filters JSON");
});
