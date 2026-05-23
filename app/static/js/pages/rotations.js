let rotationsCache = [];
let selectedRotationForLayers = null;
let selectedRotationNameForLayers = "";
let rotationLayersCache = [];
let rotationLayerEligibleUsersCache = [];
let layerMembersCache = {};
let layerRestrictionsCache = {};
let expandedLayerId = null;

const WEEKDAY_LABELS = [
    "Monday",
    "Tuesday",
    "Wednesday",
    "Thursday",
    "Friday",
    "Saturday",
    "Sunday"
];

const FALLBACK_TIMEZONES = [
    "UTC",
    "Europe/London",
    "Europe/Berlin",
    "Europe/Paris",
    "Europe/Moscow",
    "Asia/Almaty",
    "Asia/Tashkent",
    "Asia/Dubai",
    "Asia/Yekaterinburg",
    "Asia/Novosibirsk",
    "Asia/Vladivostok",
    "Asia/Tokyo",
    "Asia/Shanghai",
    "Asia/Kolkata",
    "America/New_York",
    "America/Chicago",
    "America/Denver",
    "America/Los_Angeles",
    "America/Sao_Paulo",
    "Australia/Sydney"
];

function getBrowserTimezones() {
    let zones = [];

    if (
        window.Intl
        && typeof Intl.supportedValuesOf === "function"
    ) {
        try {
            zones = Intl.supportedValuesOf("timeZone") || [];
        } catch (error) {
            zones = [];
        }
    }

    FALLBACK_TIMEZONES.forEach(function (zone) {
        if (zones.indexOf(zone) === -1) {
            zones.push(zone);
        }
    });

    zones.sort(function (left, right) {
        if (left === "UTC") {
            return -1;
        }

        if (right === "UTC") {
            return 1;
        }

        return left.localeCompare(right);
    });

    return zones;
}

function fillTimezoneSelect(selector, selectedTimezone) {
    const select = $(selector);

    if (!select.length) {
        return;
    }

    const value = selectedTimezone || "UTC";
    const zones = getBrowserTimezones();

    select.empty();

    zones.forEach(function (zone) {
        select.append(
            $("<option>")
                .val(zone)
                .text(zone)
        );
    });

    if (zones.indexOf(value) === -1) {
        select.append(
            $("<option>")
                .val(value)
                .text(value)
        );
    }

    select.val(value);
}

function initTimezoneSelect(selector, selectedTimezone, dropdownParent) {
    const select = $(selector);

    if (!select.length) {
        return;
    }

    fillTimezoneSelect(select, selectedTimezone || "UTC");

    if ($.fn.select2) {
        if (select.hasClass("select2-hidden-accessible")) {
            select.select2("destroy");
        }

        select.select2({
            width: "100%",
            placeholder: "Select timezone",
            dropdownParent: dropdownParent ? $(dropdownParent) : undefined
        });
    }
}

function setTimezoneSelectValue(selector, value) {
    const select = $(selector);
    const timezone = value || "UTC";

    if (!select.length) {
        return;
    }

    if (!select.find("option").filter(function () {
        return $(this).val() === timezone;
    }).length) {
        select.append(
            $("<option>")
                .val(timezone)
                .text(timezone)
        );
    }

    select.val(timezone).trigger("change");
}

function getTimezoneSelectValue(selector) {
    return $(selector).val() || "UTC";
}

function openRotationLayersModal() {
    $("#rotation-layers-modal")
        .css("display", "flex")
        .addClass("is-open");

    $("body").addClass("modal-open");
}

function closeRotationLayersModal() {
    $("#rotation-layers-modal")
        .css("display", "none")
        .removeClass("is-open");

    $("body").removeClass("modal-open");

    selectedRotationForLayers = null;
    selectedRotationNameForLayers = "";
    rotationLayersCache = [];
    rotationLayerEligibleUsersCache = [];
    layerMembersCache = {};
    layerRestrictionsCache = {};
    expandedLayerId = null;

    $("#rotation-layer-cards")
        .empty()
        .append($("<div>").addClass("empty-cell").text("No rotation selected"));
}

function findSelectedLayerRotation() {
    return rotationsCache.find(function (item) {
        return Number(item.id) === Number(selectedRotationForLayers);
    });
}

function selectRotationLayers(rotationId) {
    const rotation = rotationsCache.find(function (item) {
        return Number(item.id) === Number(rotationId);
    });

    if (!rotation) {
        showAppError("Rotation was not found.");
        return;
    }

    selectedRotationForLayers = rotation.id;
    selectedRotationNameForLayers = rotation.name || ("rotation #" + rotation.id);
    rotationLayersCache = [];
    rotationLayerEligibleUsersCache = [];
    layerMembersCache = {};
    layerRestrictionsCache = {};
    expandedLayerId = null;

    $("#rotation-layers-title").text("Rotation layers: " + selectedRotationNameForLayers);

    openRotationLayersModal();

    loadEligibleUsersForLayerCards(rotation.id, function () {
        loadRotationLayerCards(rotation.id);
    });
}

function loadEligibleUsersForLayerCards(rotationId, callback) {
    apiGet("/api/rotations/" + rotationId + "/eligible-users", function (users) {
        rotationLayerEligibleUsersCache = asArray(users);

        if (typeof callback === "function") {
            callback(rotationLayerEligibleUsersCache);
        }
    });
}

function loadRotationLayerCards(rotationId, callback) {
    const container = $("#rotation-layer-cards");

    container
        .empty()
        .append($("<div>").addClass("layer-card-loading").text("Loading layers..."));

    apiGet("/api/rotations/" + rotationId + "/layers", function (layers) {
        rotationLayersCache = asArray(layers).sort(function (a, b) {
            return Number(a.priority || 0) - Number(b.priority || 0);
        });

        loadAllLayerCardDetails(function () {
            renderRotationLayerCards();

            if (typeof callback === "function") {
                callback();
            }
        });
    });
}

function loadAllLayerCardDetails(callback) {
    if (!rotationLayersCache.length) {
        if (typeof callback === "function") {
            callback();
        }
        return;
    }

    let pending = rotationLayersCache.length * 2;

    function doneOne() {
        pending -= 1;

        if (pending <= 0 && typeof callback === "function") {
            callback();
        }
    }

    rotationLayersCache.forEach(function (layer) {
        apiGet("/api/rotations/layers/" + layer.id + "/members", function (members) {
            layerMembersCache[layer.id] = asArray(members);
            doneOne();
        });

        apiGet("/api/rotations/layers/" + layer.id + "/restrictions", function (restrictions) {
            layerRestrictionsCache[layer.id] = asArray(restrictions).map(function (item) {
                return {
                    weekday: item.weekday,
                    start_time: item.start_time,
                    end_time: item.end_time
                };
            });
            doneOne();
        });
    });
}

function loadOneLayerCardDetails(layerId, callback) {
    let pending = 2;

    function doneOne() {
        pending -= 1;

        if (pending <= 0 && typeof callback === "function") {
            callback();
        }
    }

    apiGet("/api/rotations/layers/" + layerId + "/members", function (members) {
        layerMembersCache[layerId] = asArray(members);
        doneOne();
    });

    apiGet("/api/rotations/layers/" + layerId + "/restrictions", function (restrictions) {
        layerRestrictionsCache[layerId] = asArray(restrictions).map(function (item) {
            return {
                weekday: item.weekday,
                start_time: item.start_time,
                end_time: item.end_time
            };
        });
        doneOne();
    });
}

function renderRotationLayerCards() {
    const container = $("#rotation-layer-cards");
    container.empty();

    if (!rotationLayersCache.length) {
        container.append(
            $("<div>")
                .addClass("empty-cell")
                .text("No layers. Add the first layer to define on-call coverage.")
        );
        return;
    }

    rotationLayersCache.forEach(function (layer, index) {
        container.append(renderRotationLayerCard(layer, index + 1));
        updateLayerCadenceVisibility(layer.id);
    });
    initLayerTimezoneSelects();
}

function renderRotationLayerCard(layer, number) {
    const card = $("<div>")
        .addClass("rotation-layer-card")
        .toggleClass("is-editing", Number(expandedLayerId) === Number(layer.id))
        .toggleClass("is-disabled", !layer.enabled)
        .attr("data-layer-id", layer.id);

    card.append(renderLayerCardHeader(layer, number));
    card.append(renderLayerSummary(layer));

    const editor = $("<div>").addClass("rotation-layer-editor");
    editor.append(renderLayerSettingsEditor(layer));
    editor.append(renderLayerMembersEditor(layer));
    editor.append(renderLayerRestrictionsEditor(layer));

    card.append(editor);

    return card;
}

function renderLayerCardHeader(layer, number) {
    const header = $("<div>").addClass("rotation-layer-card-header");

    header.append(
        $("<div>")
            .addClass("rotation-layer-number")
            .text(number)
    );

    header.append(
        $("<div>")
            .addClass("rotation-layer-title")
            .append($("<strong>").text(layer.name || "Unnamed layer"))
            .append(
                $("<small>").text(
                    "Priority " + Number(layer.priority || 0) +
                    " · " +
                    (layer.enabled ? "Enabled" : "Disabled") +
                    " · " +
                    (layer.timezone || "UTC")
                )
            )
    );

    const actions = $("<div>").addClass("rotation-layer-header-actions");

    actions.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-small")
            .text(Number(expandedLayerId) === Number(layer.id) ? "Collapse" : "Edit")
            .on("click", function () {
                toggleLayerEditor(layer.id);
            })
    );

    actions.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-danger btn-small")
            .text("Delete")
            .on("click", function () {
                deleteRotationLayer(layer.id);
            })
    );

    header.append(actions);

    return header;
}

function renderLayerSummary(layer) {
    const summary = $("<div>").addClass("rotation-layer-summary");

    summary.append(
        $("<div>")
            .addClass("rotation-layer-summary-item")
            .append($("<span>").text("Who rotates"))
            .append($("<strong>").html(formatLayerMembersSummary(layer.id)))
    );

    summary.append(
        $("<div>")
            .addClass("rotation-layer-summary-item")
            .append($("<span>").text("Rotation"))
            .append($("<strong>").text(formatLayerCadence(layer)))
    );

    summary.append(
        $("<div>")
            .addClass("rotation-layer-summary-item")
            .append($("<span>").text("Active"))
            .append($("<strong>").html(formatLayerRestrictionsSummary(layer.id)))
    );

    return summary;
}

function formatLayerMembersSummary(layerId) {
    const members = asArray(layerMembersCache[layerId])
        .filter(function (member) {
            return member.active !== false;
        })
        .sort(function (a, b) {
            return Number(a.position || 0) - Number(b.position || 0);
        });

    if (!members.length) {
        return '<span class="muted">No users</span>';
    }

    return members.map(function (member) {
        return escapeHtml(member.display_name || member.username || ("user #" + member.user_id));
    }).join(" → ");
}

function formatLayerCadence(layer) {
    const type = layer.rotation_type || "daily";
    const handoff = layer.handoff_time || "09:00";
    const timezone = layer.timezone || "UTC";

    if (type === "weekly") {
        const weekday = layer.handoff_weekday === null || layer.handoff_weekday === undefined
            ? "Monday"
            : weekdayLabel(layer.handoff_weekday);

        return "Weekly, " + weekday + " " + handoff + ", " + timezone;
    }

    if (type === "custom") {
        return "Every " +
            (layer.interval_value || 1) +
            " " +
            (layer.interval_unit || "days") +
            ", " +
            timezone;
    }

    return "Daily, " + handoff + ", " + timezone;
}

function formatLayerRestrictionsSummary(layerId) {
    const restrictions = asArray(layerRestrictionsCache[layerId]);

    if (!restrictions.length) {
        return '<span class="muted">24/7</span>';
    }

    const parts = restrictions.slice(0, 4).map(function (item) {
        return escapeHtml(
            weekdayLabel(item.weekday) +
            " " +
            item.start_time +
            "-" +
            item.end_time
        );
    });

    if (restrictions.length > 4) {
        parts.push("+" + (restrictions.length - 4) + " more");
    }

    return parts.join("<br>");
}

function renderLayerSettingsEditor(layer) {
    const section = $("<section>").addClass("layer-editor-section");

    section.append($("<h4>").text("1. When do they rotate?"));
    section.append(
        $("<div>")
            .addClass("layer-editor-section-subtitle")
            .text("Configure handoff time, timezone and priority for this layer.")
    );

    const grid = $("<div>").addClass("app-form-grid");

    grid.append(layerTextField(layer.id, "name", "Name", layer.name || ""));
    grid.append(layerNumberField(layer.id, "priority", "Priority", layer.priority || 0, 0));

    grid.append(
        $("<div>")
            .addClass("app-field app-form-wide")
            .append($("<label>").text("Description"))
            .append(
                $("<textarea>")
                    .addClass("input")
                    .attr("rows", 2)
                    .attr("data-layer-field", "description")
                    .val(layer.description || "")
            )
    );

    grid.append(
        $("<div>")
            .addClass("app-field")
            .append($("<label>").text("Schedule starts at"))
            .append(
                $("<input>")
                    .addClass("input")
                    .attr("type", "datetime-local")
                    .attr("data-layer-field", "start_at")
                    .val(isoToDatetimeLocal(layer.start_at))
            )
    );

    grid.append(
        $("<div>")
            .addClass("app-field")
            .append($("<label>").text("Cadence"))
            .append(
                $("<select>")
                    .addClass("input")
                    .attr("data-layer-field", "rotation_type")
                    .append($("<option>").val("daily").text("Daily handoff"))
                    .append($("<option>").val("weekly").text("Weekly handoff"))
                    .append($("<option>").val("custom").text("Custom interval"))
                    .val(layer.rotation_type || "daily")
            )
    );

    grid.append(
        $("<div>")
            .addClass("app-field layer-weekly-options")
            .append($("<label>").text("Weekly handoff day"))
            .append(
                $("<select>")
                    .addClass("input")
                    .attr("data-layer-field", "handoff_weekday")
                    .append($("<option>").val("0").text("Monday"))
                    .append($("<option>").val("1").text("Tuesday"))
                    .append($("<option>").val("2").text("Wednesday"))
                    .append($("<option>").val("3").text("Thursday"))
                    .append($("<option>").val("4").text("Friday"))
                    .append($("<option>").val("5").text("Saturday"))
                    .append($("<option>").val("6").text("Sunday"))
                    .val(String(layer.handoff_weekday === null || layer.handoff_weekday === undefined ? 0 : layer.handoff_weekday))
            )
    );

    grid.append(
        $("<div>")
            .addClass("app-field")
            .append($("<label>").text("Handoff time"))
            .append(
                $("<input>")
                    .addClass("input")
                    .attr("type", "time")
                    .attr("data-layer-field", "handoff_time")
                    .val(layer.handoff_time || "09:00")
            )
    );

    grid.append(
        $("<div>")
            .addClass("app-field layer-custom-options")
            .append($("<label>").text("Every"))
            .append(
                $("<input>")
                    .addClass("input")
                    .attr("type", "number")
                    .attr("min", "1")
                    .attr("data-layer-field", "interval_value")
                    .val(layer.interval_value || 1)
            )
    );

    grid.append(
        $("<div>")
            .addClass("app-field layer-custom-options")
            .append($("<label>").text("Unit"))
            .append(
                $("<select>")
                    .addClass("input")
                    .attr("data-layer-field", "interval_unit")
                    .append($("<option>").val("minutes").text("minutes"))
                    .append($("<option>").val("hours").text("hours"))
                    .append($("<option>").val("days").text("days"))
                    .append($("<option>").val("weeks").text("weeks"))
                    .val(layer.interval_unit || "days")
            )
    );

    grid.append(layerTimezoneField(layer.id, layer.timezone || "UTC"));

    grid.append(
        $("<div>")
            .addClass("app-field")
            .append(
                $("<label>")
                    .addClass("app-switch")
                    .append(
                        $("<input>")
                            .attr("type", "checkbox")
                            .attr("data-layer-field", "enabled")
                            .prop("checked", layer.enabled !== false)
                    )
                    .append($("<span>").addClass("app-switch-ui"))
                    .append(
                        $("<span>")
                            .append($("<strong>").text("Enabled"))
                            .append($("<small>").text("Layer participates in final schedule"))
                    )
            )
    );

    section.append(grid);

    section.append(
        $("<div>")
            .addClass("layer-editor-actions")
            .append(
                $("<button>")
                    .attr("type", "button")
                    .addClass("btn btn-primary")
                    .text("Save layer")
                    .on("click", function () {
                        saveRotationLayerFromCard(layer.id);
                    })
            )
    );

    return section;
}
function layerTimezoneField(layerId, value) {
    const select = $("<select>")
        .addClass("input timezone-select")
        .attr("data-layer-field", "timezone")
        .attr("data-layer-timezone-select", layerId);

    getBrowserTimezones().forEach(function (zone) {
        select.append(
            $("<option>")
                .val(zone)
                .text(zone)
        );
    });

    if (value && !select.find('option[value="' + value.replace(/"/g, '\\"') + '"]').length) {
        select.append(
            $("<option>")
                .val(value)
                .text(value)
        );
    }

    select.val(value || "UTC");

    return $("<div>")
        .addClass("app-field")
        .append($("<label>").text("Timezone"))
        .append(select);
}
function renderLayerMembersEditor(layer) {
    const section = $("<section>").addClass("layer-editor-section");

    section.append($("<h4>").text("2. Who rotates?"));
    section.append(
        $("<div>")
            .addClass("layer-editor-section-subtitle")
            .text("Users rotate in position order: 0, 1, 2 and so on.")
    );

    const addRow = $("<div>").addClass("layer-member-add-row");

    const userSelect = $("<select>")
        .addClass("input")
        .attr("data-layer-member-user", layer.id);

    if (!rotationLayerEligibleUsersCache.length) {
        userSelect.append($("<option>").val("").text("No active team members"));
    } else {
        rotationLayerEligibleUsersCache.forEach(function (user) {
            userSelect.append(
                $("<option>")
                    .val(user.user_id)
                    .text("#" + user.user_id + " " + (user.display_name || user.username || "user"))
            );
        });
    }

    addRow.append(
        $("<div>")
            .addClass("app-field")
            .append($("<label>").text("User"))
            .append(userSelect)
    );

    addRow.append(
        $("<div>")
            .addClass("app-field")
            .append($("<label>").text("Position"))
            .append(
                $("<input>")
                    .addClass("input")
                    .attr("type", "number")
                    .attr("min", "0")
                    .attr("data-layer-member-position", layer.id)
                    .val(nextLayerMemberPosition(layer.id))
            )
    );

    addRow.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn")
            .text("Add user")
            .on("click", function () {
                addLayerMemberFromCard(layer.id);
            })
    );

    section.append(addRow);

    const list = $("<div>").addClass("layer-members-list");
    const members = asArray(layerMembersCache[layer.id]).sort(function (a, b) {
        return Number(a.position || 0) - Number(b.position || 0);
    });

    if (!members.length) {
        list.append(
            $("<div>")
                .addClass("layer-empty-box")
                .text("No users in this layer yet.")
        );
    } else {
        members.forEach(function (member) {
            list.append(renderLayerMemberRow(layer.id, member));
        });
    }

    section.append(list);

    return section;
}

function renderLayerMemberRow(layerId, member) {
    const row = $("<div>").addClass("layer-member-row");

    row.append(
        $("<div>")
            .addClass("layer-member-name")
            .append($("<strong>").text(member.display_name || member.username || ("user #" + member.user_id)))
            .append($("<small>").text("User ID " + member.user_id + " · member #" + member.id))
    );

    row.append(
        $("<input>")
            .addClass("input")
            .attr("type", "number")
            .attr("min", "0")
            .attr("data-member-position", member.id)
            .val(member.position || 0)
    );

    row.append(
        $("<label>")
            .addClass("app-switch")
            .append(
                $("<input>")
                    .attr("type", "checkbox")
                    .attr("data-member-active", member.id)
                    .prop("checked", member.active !== false)
            )
            .append($("<span>").addClass("app-switch-ui"))
            .append(
                $("<span>")
                    .append($("<strong>").text("Active"))
                    .append($("<small>").text("Can be selected"))
            )
    );

    const actions = $("<div>").addClass("table-actions");

    actions.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-small")
            .text("Save")
            .on("click", function () {
                updateLayerMemberFromCard(layerId, member.id);
            })
    );

    actions.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-danger btn-small")
            .text("Remove")
            .on("click", function () {
                removeLayerMemberFromCard(layerId, member.id);
            })
    );

    row.append(actions);

    return row;
}

function renderLayerRestrictionsEditor(layer) {
    const section = $("<section>").addClass("layer-editor-section");

    section.append($("<h4>").text("3. When is this layer active?"));
    section.append(
        $("<div>")
            .addClass("layer-editor-section-subtitle")
            .text("No restrictions means this layer is active 24/7.")
    );

    const toolbar = $("<div>").addClass("layer-restrictions-toolbar");

    toolbar.append(presetButton(layer.id, "24/7", "24x7"));
    toolbar.append(presetButton(layer.id, "Business hours", "business"));
    toolbar.append(presetButton(layer.id, "Nights", "nights"));
    toolbar.append(presetButton(layer.id, "Weekend", "weekend"));

    toolbar.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-small")
            .text("+ Add window")
            .on("click", function () {
                addRestrictionRowToCard(layer.id);
            })
    );

    section.append(toolbar);

    const list = $("<div>")
        .addClass("layer-restrictions-list")
        .attr("data-layer-restrictions-list", layer.id);

    const restrictions = asArray(layerRestrictionsCache[layer.id]);

    if (!restrictions.length) {
        list.append(
            $("<div>")
                .addClass("layer-empty-box")
                .text("Active 24/7. Add windows if this layer should only work during specific days or hours.")
        );
    } else {
        restrictions.forEach(function (restriction, index) {
            list.append(renderLayerRestrictionRow(layer.id, restriction, index));
        });
    }

    section.append(list);

    section.append(
        $("<div>")
            .addClass("layer-editor-actions")
            .append(
                $("<button>")
                    .attr("type", "button")
                    .addClass("btn btn-primary")
                    .text("Save restrictions")
                    .on("click", function () {
                        saveLayerRestrictionsFromCard(layer.id);
                    })
            )
    );

    return section;
}

function renderLayerRestrictionRow(layerId, restriction, index) {
    const row = $("<div>")
        .addClass("layer-restriction-row")
        .attr("data-restriction-row", layerId);

    const weekdaySelect = $("<select>")
        .addClass("input")
        .attr("data-restriction-weekday", index)
        .append($("<option>").val("").text("Every day"))
        .append($("<option>").val("0").text("Monday"))
        .append($("<option>").val("1").text("Tuesday"))
        .append($("<option>").val("2").text("Wednesday"))
        .append($("<option>").val("3").text("Thursday"))
        .append($("<option>").val("4").text("Friday"))
        .append($("<option>").val("5").text("Saturday"))
        .append($("<option>").val("6").text("Sunday"));

    weekdaySelect.val(restriction.weekday === null || restriction.weekday === undefined ? "" : String(restriction.weekday));

    row.append(weekdaySelect);

    row.append(
        $("<input>")
            .addClass("input")
            .attr("type", "time")
            .attr("data-restriction-start", index)
            .val(restriction.start_time || "09:00")
    );

    row.append(
        $("<input>")
            .addClass("input")
            .attr("type", "time")
            .attr("data-restriction-end", index)
            .val(restriction.end_time || "18:00")
    );

    row.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-danger btn-small")
            .text("Remove")
            .on("click", function () {
                removeRestrictionRowFromCard(layerId, index);
            })
    );

    return row;
}

function layerTextField(layerId, field, label, value) {
    return $("<div>")
        .addClass("app-field")
        .append($("<label>").text(label))
        .append(
            $("<input>")
                .addClass("input")
                .attr("type", "text")
                .attr("data-layer-field", field)
                .val(value || "")
        );
}

function layerNumberField(layerId, field, label, value, minValue) {
    return $("<div>")
        .addClass("app-field")
        .append($("<label>").text(label))
        .append(
            $("<input>")
                .addClass("input")
                .attr("type", "number")
                .attr("min", String(minValue || 0))
                .attr("data-layer-field", field)
                .val(value || 0)
        );
}

function presetButton(layerId, label, preset) {
    return $("<button>")
        .attr("type", "button")
        .addClass("btn btn-small")
        .text(label)
        .on("click", function () {
            applyLayerRestrictionPreset(layerId, preset);
        });
}

function layerCard(layerId) {
    return $('.rotation-layer-card[data-layer-id="' + layerId + '"]');
}

function layerField(layerId, field) {
    return layerCard(layerId).find('[data-layer-field="' + field + '"]');
}

function collectLayerPayloadFromCard(layerId) {
    const rotation = findSelectedLayerRotation();

    const rotationType = layerField(layerId, "rotation_type").val() || "daily";
    const payload = {
        name: layerField(layerId, "name").val(),
        description: layerField(layerId, "description").val() || null,
        priority: Number(layerField(layerId, "priority").val() || 0),
        start_at: layerField(layerId, "start_at").val() || (rotation ? rotation.start_at : null),
        rotation_type: rotationType,
        interval_value: Number(layerField(layerId, "interval_value").val() || 1),
        interval_unit: layerField(layerId, "interval_unit").val() || "days",
        handoff_time: layerField(layerId, "handoff_time").val() || "09:00",
        handoff_weekday: Number(layerField(layerId, "handoff_weekday").val() || 0),
        timezone: layerField(layerId, "timezone").val() || (rotation ? rotation.timezone : "UTC"),
        enabled: layerField(layerId, "enabled").is(":checked")
    };

    if (rotationType === "daily") {
        payload.interval_value = 1;
        payload.interval_unit = "days";
    }

    if (rotationType === "weekly") {
        payload.interval_value = 1;
        payload.interval_unit = "weeks";
    }

    return payload;
}

function toggleLayerEditor(layerId) {
    if (Number(expandedLayerId) === Number(layerId)) {
        expandedLayerId = null;
        renderRotationLayerCards();
        return;
    }

    expandedLayerId = layerId;

    loadOneLayerCardDetails(layerId, function () {
        renderRotationLayerCards();
    });
}

function updateLayerCadenceVisibility(layerId) {
    const card = layerCard(layerId);
    const type = card.find('[data-layer-field="rotation_type"]').val();

    card.find(".layer-weekly-options").toggle(type === "weekly");
    card.find(".layer-custom-options").toggle(type === "custom");
}

function addLayerCard() {
    if (!selectedRotationForLayers) {
        showAppError("Select a rotation first.");
        return;
    }

    const rotation = findSelectedLayerRotation();
    const nextPriority = rotationLayersCache.length
        ? Math.max.apply(null, rotationLayersCache.map(function (layer) {
            return Number(layer.priority || 0);
        })) + 10
        : 10;

    const payload = {
        name: "New layer",
        description: null,
        priority: nextPriority,
        start_at: rotation ? rotation.start_at : null,
        rotation_type: rotation ? (rotation.rotation_type || "daily") : "daily",
        interval_value: rotation ? (rotation.interval_value || 1) : 1,
        interval_unit: rotation ? (rotation.interval_unit || "days") : "days",
        handoff_time: rotation ? (rotation.handoff_time || "09:00") : "09:00",
        handoff_weekday: rotation && rotation.handoff_weekday !== null ? rotation.handoff_weekday : 0,
        timezone: rotation ? (rotation.timezone || "UTC") : "UTC",
        enabled: true
    };

    apiPost("/api/rotations/" + selectedRotationForLayers + "/layers", payload, function (layer) {
        expandedLayerId = layer.id;

        loadRotationLayerCards(selectedRotationForLayers, function () {
            showAppSuccess("Layer created.");
        });
    });
}

function saveRotationLayerFromCard(layerId) {
    const payload = collectLayerPayloadFromCard(layerId);

    apiPut("/api/rotations/layers/" + layerId, payload, function () {
        expandedLayerId = layerId;

        loadRotationLayerCards(selectedRotationForLayers, function () {
            refreshRotations();
            showAppSuccess("Layer updated.");
        });
    });
}

function deleteRotationLayer(layerId) {
    showAppConfirm({
        title: "Delete this layer?",
        message: "Delete this layer?",
        confirmText: "Delete layer",
        confirmClass: "btn-danger",
    }).done(function () {
        apiDelete("/api/rotations/layers/" + layerId, function () {
            if (Number(expandedLayerId) === Number(layerId)) {
                expandedLayerId = null;
            }

            loadRotationLayerCards(selectedRotationForLayers, function () {
                refreshRotations();
            });
        });
    });
}

function nextLayerMemberPosition(layerId) {
    const members = asArray(layerMembersCache[layerId]);

    if (!members.length) {
        return 0;
    }

    return Math.max.apply(null, members.map(function (member) {
        return Number(member.position || 0);
    })) + 1;
}

function addLayerMemberFromCard(layerId) {
    const userId = layerCard(layerId).find('[data-layer-member-user="' + layerId + '"]').val();
    const position = layerCard(layerId).find('[data-layer-member-position="' + layerId + '"]').val();

    if (!userId) {
        showAppError("Select a user first.");
        return;
    }

    apiPost("/api/rotations/layers/" + layerId + "/members", {
        user_id: Number(userId),
        position: Number(position || 0)
    }, function () {
        loadOneLayerCardDetails(layerId, function () {
            renderRotationLayerCards();
            refreshRotations();
            showAppSuccess("Layer member added.");
        });
    });
}

function updateLayerMemberFromCard(layerId, memberId) {
    const position = $('[data-member-position="' + memberId + '"]').val();
    const active = $('[data-member-active="' + memberId + '"]').is(":checked");

    apiPut("/api/rotations/layers/members/" + memberId, {
        position: Number(position || 0),
        active: active
    }, function () {
        loadOneLayerCardDetails(layerId, function () {
            renderRotationLayerCards();
            refreshRotations();
            showAppSuccess("Layer member updated.");
        });
    });
}

function removeLayerMemberFromCard(layerId, memberId) {
    showAppConfirm({
        title: "Remove this user from the layer?",
        message: "Remove this user from the layer?",
        confirmText: "Remove user from the layer",
        confirmClass: "btn-danger",
    }).done(function () {
        apiDelete("/api/rotations/layers/members/" + memberId, function () {
            loadOneLayerCardDetails(layerId, function () {
                renderRotationLayerCards();
                refreshRotations();
            });
        });
    });
}

function weekdayLabel(value) {
    if (value === null || value === undefined || value === "") {
        return "Every day";
    }

    return WEEKDAY_LABELS[Number(value)] || "-";
}

function collectRestrictionsFromCard(layerId) {
    const rows = layerCard(layerId).find('[data-restriction-row="' + layerId + '"]');
    const restrictions = [];

    rows.each(function () {
        const row = $(this);
        const weekdayValue = row.find("[data-restriction-weekday]").val();

        restrictions.push({
            weekday: weekdayValue === "" ? null : Number(weekdayValue),
            start_time: row.find("[data-restriction-start]").val() || "09:00",
            end_time: row.find("[data-restriction-end]").val() || "18:00"
        });
    });

    return restrictions;
}

function refreshRestrictionDraftFromCard(layerId) {
    layerRestrictionsCache[layerId] = collectRestrictionsFromCard(layerId);
}

function addRestrictionRowToCard(layerId) {
    refreshRestrictionDraftFromCard(layerId);

    layerRestrictionsCache[layerId].push({
        weekday: null,
        start_time: "09:00",
        end_time: "18:00"
    });

    renderRotationLayerCards();
}

function removeRestrictionRowFromCard(layerId, index) {
    refreshRestrictionDraftFromCard(layerId);

    layerRestrictionsCache[layerId].splice(index, 1);

    renderRotationLayerCards();
}

function applyLayerRestrictionPreset(layerId, preset) {
    if (preset === "24x7") {
        layerRestrictionsCache[layerId] = [
            { weekday: null, start_time: "00:00", end_time: "00:00" }
        ];
    } else if (preset === "business") {
        layerRestrictionsCache[layerId] = [0, 1, 2, 3, 4].map(function (weekday) {
            return { weekday: weekday, start_time: "09:00", end_time: "18:00" };
        });
    } else if (preset === "nights") {
        layerRestrictionsCache[layerId] = [0, 1, 2, 3, 4].map(function (weekday) {
            return { weekday: weekday, start_time: "18:00", end_time: "09:00" };
        });
    } else if (preset === "weekend") {
        layerRestrictionsCache[layerId] = [
            { weekday: 5, start_time: "00:00", end_time: "00:00" },
            { weekday: 6, start_time: "00:00", end_time: "00:00" }
        ];
    }

    renderRotationLayerCards();
}

function saveLayerRestrictionsFromCard(layerId) {
    const restrictions = collectRestrictionsFromCard(layerId);

    apiPut("/api/rotations/layers/" + layerId + "/restrictions", {
        restrictions: restrictions
    }, function () {
        layerRestrictionsCache[layerId] = restrictions;

        loadOneLayerCardDetails(layerId, function () {
            renderRotationLayerCards();
            refreshRotations();
            showAppSuccess("Restrictions saved.");
        });
    });
}

function escapeHtml(value) {
    return String(value || "")
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;")
        .replace(/"/g, "&quot;")
        .replace(/'/g, "&#039;");
}

$(document).on("click", "#add-layer-card", addLayerCard);

$(document).on(
    "click",
    "#close-rotation-layers-modal, #close-rotation-layers-modal-footer",
    closeRotationLayersModal
);

$(document).on("click", "#rotation-layers-modal", function (event) {
    if (event.target === this) {
        closeRotationLayersModal();
    }
});

$(document).on("change", '[data-layer-field="rotation_type"]', function () {
    const layerId = $(this).closest(".rotation-layer-card").attr("data-layer-id");
    updateLayerCadenceVisibility(layerId);
});

$(document).on("keydown", function (event) {
    if (event.key === "Escape" && $("#rotation-layers-modal").hasClass("is-open")) {
        closeRotationLayersModal();
    }
});
function loadRotations() {
    /* Load rotations page data. */
    fillTeamSelect("#rotation-team", false);
    fillUserSelect("#member-user");
    fillUserSelect("#override-user");
    updateRotationCadenceFields();
    refreshRotations();
}

function formatSeconds(seconds) {
    /* Format seconds as a compact duration. */
    if (!seconds) { return "-"; }
    if (seconds % 86400 === 0) { return (seconds / 86400) + "d"; }
    if (seconds % 3600 === 0) { return (seconds / 3600) + "h"; }
    if (seconds % 60 === 0) { return (seconds / 60) + "m"; }
    return seconds + "s";
}

function rotationInitials(value) {
    /*
     * Build initials for user avatar.
     */
    return String(value || "?")
        .trim()
        .split(/\s+/)
        .slice(0, 2)
        .map(function (part) {
            return part.substring(0, 1).toUpperCase();
        })
        .join("") || "?";
}


function getRotationCurrentUser(rotation) {
    /*
     * Return current on-call user label.
     */
    return rotation.current_oncall || rotation.current_user || rotation.current_username || "";
}


function getRotationSearchText(rotation) {
    /*
     * Build searchable rotation text.
     */
    return [
        rotation.id,
        rotation.team_slug,
        rotation.team_name,
        rotation.name,
        rotation.description,
        rotation.rotation_type,
        rotation.handoff_time,
        getRotationCurrentUser(rotation),
        rotation.enabled ? "active" : "inactive"
    ].join(" ").toLowerCase();
}


function getFilteredRotations() {
    /*
     * Apply client-side filters to rotationsCache.
     */
    const query = String($("#rotations-search").val() || "").trim().toLowerCase();
    const team = String($("#rotations-team-filter").val() || "");
    const status = String($("#rotations-status-filter").val() || "");

    return rotationsCache.filter(function (rotation) {
        if (team && String(rotation.team_slug || "") !== team) {
            return false;
        }

        if (status === "active" && !rotation.enabled) {
            return false;
        }

        if (status === "inactive" && rotation.enabled) {
            return false;
        }

        if (!query) {
            return true;
        }

        return getRotationSearchText(rotation).indexOf(query) !== -1;
    });
}

function renderRotationsSummary(rotations) {
    /*
     * Render rotations summary cards.
     */
    rotations = Array.isArray(rotations) ? rotations : [];

    let active = 0;
    let oncall = 0;
    let reminders = 0;

    rotations.forEach(function (rotation) {
        if (rotation.enabled) {
            active += 1;
        }

        if (getRotationCurrentUser(rotation)) {
            oncall += 1;
        }

        if (Number(rotation.reminder_interval_seconds || 0) > 0) {
            reminders += 1;
        }
    });

    $("#rotations-summary-total").text(rotations.length);
    $("#rotations-summary-active").text(active);
    $("#rotations-summary-oncall").text(oncall);
    $("#rotations-summary-reminders").text(reminders);
}
function reminderValueToSeconds() {
    /* Convert reminder value and unit to seconds. */
    const value = Number($("#rotation-reminder-value").val() || 5);
    const unit = $("#rotation-reminder-unit").val();

    if (unit === "days") { return value * 86400; }
    if (unit === "hours") { return value * 3600; }
    return value * 60;
}

function setReminderFields(seconds) {
    /* Fill reminder fields from seconds. */
    if (seconds % 86400 === 0) {
        $("#rotation-reminder-value").val(seconds / 86400);
        $("#rotation-reminder-unit").val("days");
    } else if (seconds % 3600 === 0) {
        $("#rotation-reminder-value").val(seconds / 3600);
        $("#rotation-reminder-unit").val("hours");
    } else {
        $("#rotation-reminder-value").val(Math.max(1, Math.floor(seconds / 60)));
        $("#rotation-reminder-unit").val("minutes");
    }
}

function refreshRotations(doneCallback) {
    /*
     * Refresh rotations table and selects.
     */
    apiGet("/api/rotations" + selectedTeamQuery(), function (rotations) {
        rotations = Array.isArray(rotations) ? rotations : [];
        rotationsCache = rotations;

        renderRotationsSummary(rotationsCache);
        renderRotationsInboxCounter(rotationsCache, rotationsCache);

        const tbody = $("#rotations-table");
        const memberSelect = $("#member-rotation");
        const overrideSelect = $("#override-rotation");
        const savedOverrideRotationId = overrideSelect.val();

        tbody.empty();
        memberSelect.empty();
        overrideSelect.empty();

        if (!rotations.length) {
            tbody.append(
                $("<tr>").append(
                    $("<td>")
                        .attr("colspan", "9")
                        .addClass("empty-cell")
                        .text("No rotations")
                )
            );

            $("#rotation-members-table")
                .empty()
                .append(
                    $("<tr>").append(
                        $("<td>")
                            .attr("colspan", "6")
                            .addClass("empty-cell")
                            .text("No rotation selected")
                    )
                );

            $("#overrides-table")
                .empty()
                .append(
                    $("<tr>").append(
                        $("<td>")
                            .attr("colspan", "6")
                            .addClass("empty-cell")
                            .text("No rotation selected")
                    )
                );

            if (typeof doneCallback === "function") {
                doneCallback();
            }

            return;
        }

        rotations.forEach(function (rotation) {
            const cadence = rotation.rotation_type === "custom"
                ? "every " + rotation.interval_value + " " + rotation.interval_unit
                : rotation.rotation_type;

            const row = $("<tr>");

            row.append(
                $("<td>").append(
                    $("<button>")
                        .attr("type", "button")
                        .addClass("rotation-name-button")
                        .text('#' + rotation.id)
                        .on("click", function () {
                            renderRotationDetails(rotation);
                        })
                )
            );
            row.append($("<td>").text(rotation.team_slug));
            row.append(
                $("<td>").append(
                    $("<button>")
                        .attr("type", "button")
                        .addClass("rotation-name-button")
                        .text(rotation.name || "-")
                        .on("click", function () {
                            renderRotationDetails(rotation);
                        })
                )
            );
            row.append($("<td>").text(cadence));
            row.append($("<td>").text(rotation.current_oncall || "-"));
            row.append($("<td>").text(rotation.handoff_time || "-"));
            row.append($("<td>").text(formatSeconds(rotation.reminder_interval_seconds)));
            row.append($("<td>").append(renderStatusBadge(rotation.enabled)));

            const actions = $("<td>").addClass("actions");

            actions.append(
                $("<button>")
                    .attr("type", "button")
                    .addClass("btn btn-small")
                    .text("Edit")
                    .on("click", function () {
                        editRotation(rotation.id);
                    })
            );

            makeIconButton({
                icon: "fas fa-layer-group",
                label: "Rotation layers",
                onClick: function () {
                    selectRotationLayers(rotation.id);
                }
            })

            actions.append(
                $("<button>")
                    .attr("type", "button")
                    .addClass("btn btn-small")
                    .text("Overrides")
                    .on("click", function () {
                        selectOverrideRotation(rotation.id);
                    })
            );

            actions.append(
                $("<button>")
                    .attr("type", "button")
                    .addClass("btn btn-small")
                    .text("Layers")
                    .on("click", function () {
                        selectRotationLayers(rotation.id);
                    })
            );

            actions.append(
                $("<button>")
                    .attr("type", "button")
                    .addClass("btn btn-danger btn-small")
                    .text("Remove")
                    .on("click", function () {
                        deleteRotation(rotation.id);
                    })
            );

            row.append(actions);
            tbody.append(row);

            if (rotation.enabled) {
                const label = rotation.team_slug + " / " + rotation.name;

                memberSelect.append(
                    $("<option>")
                        .val(rotation.id)
                        .text(label)
                );

                overrideSelect.append(
                    $("<option>")
                        .val(rotation.id)
                        .text(label)
                );
            }
        });

        // if (savedMemberRotationId) {
        //     memberSelect.val(String(savedMemberRotationId));
        // }

        if (savedOverrideRotationId) {
            overrideSelect.val(String(savedOverrideRotationId));
        }

        if (typeof doneCallback === "function") {
            doneCallback();
            return;
        }

        // if (selectedRotationForMembers) {
        //     loadRotationMembers(selectedRotationForMembers, selectedRotationNameForMembers);
        // }

        if (overrideSelect.val()) {
            loadOverrides();
        }
    });
}

function updateRotationCadenceFields() {
    /* Toggle rotation cadence fields. */
    const type = $("#rotation-type").val();
    $("#weekly-options").toggle(type === "weekly");
    $("#custom-interval-options").toggle(type === "custom");
}

function collectRotationPayload() {
    /* Build rotation payload from form fields. */
    return {
        team_id: Number($("#rotation-team").val()),
        name: $("#rotation-name").val(),
        description: $("#rotation-description").val(),
        start_at: $("#rotation-start").val(),
        rotation_type: $("#rotation-type").val(),
        interval_value: Number($("#rotation-interval-value").val()),
        interval_unit: $("#rotation-interval-unit").val(),
        handoff_time: $("#rotation-handoff-time").val(),
        handoff_weekday: Number($("#rotation-weekday").val()),
        reminder_interval_seconds: reminderValueToSeconds(),
        timezone: getTimezoneSelectValue("#rotation-timezone"),
    };
}

function saveRotation() {
    /* Create or update a rotation. */
    const id = $("#rotation-id").val();

    if (id) {
        apiPut("/api/rotations/" + id, collectRotationPayload(), function () {
            closeRotationFormModal();
            resetRotationForm();
            refreshRotations();
        });
        return;
    }

    apiPost("/api/rotations", collectRotationPayload(), function () {
        closeRotationFormModal();
        resetRotationForm();
        refreshRotations();
    });
}

function editRotation(id) {
    /* Load rotation data into the form. */
    const rotation = rotationsCache.find(function (item) {
        return item.id === id;
    });

    if (!rotation) {
        return;
    }

    $("#rotation-form-title").text("Edit rotation #" + id);
    $("#rotation-id").val(rotation.id);
    $("#rotation-team").val(rotation.team_id);
    $("#rotation-name").val(rotation.name);
    $("#rotation-description").val(rotation.description || "");
    $("#rotation-start").val(isoToDatetimeLocal(rotation.start_at));
    $("#rotation-type").val(rotation.rotation_type || "daily");
    $("#rotation-interval-value").val(rotation.interval_value || 1);
    $("#rotation-interval-unit").val(rotation.interval_unit || "days");
    $("#rotation-handoff-time").val(rotation.handoff_time || "09:00");
    $("#rotation-weekday").val(rotation.handoff_weekday === null ? 0 : rotation.handoff_weekday);
    setReminderFields(rotation.reminder_interval_seconds);
    $("#rotation-timezone").val(rotation.timezone || "UTC");
    updateRotationCadenceFields();
    openRotationFormModal();

    initTimezoneSelect(
        "#rotation-timezone",
        rotation.timezone || "UTC",
        "#rotation-form-modal"
    );

    setTimezoneSelectValue(
        "#rotation-timezone",
        rotation.timezone || "UTC"
    );
}

function deleteRotation(id) {
    /* Disable a rotation. */
    showAppConfirm({
        title: "Disable this rotation?",
        message: "Disable this rotation?",
        confirmText: "Disable rotation?",
        confirmClass: "btn-danger",
    }).done(function () {
        apiDelete("/api/rotations/" + id, refreshRotations);
    });
}

function resetRotationForm() {
    /* Reset rotation form. */
    $("#rotation-form-title").text("Create rotation");
    $("#rotation-id").val("");
    $("#rotation-name").val("");
    $("#rotation-description").val("");
    $("#rotation-start").val("");
    $("#rotation-type").val("daily");
    $("#rotation-interval-value").val(1);
    $("#rotation-interval-unit").val("days");
    $("#rotation-handoff-time").val("09:00");
    $("#rotation-weekday").val(0);
    setReminderFields(300);
    // $("#rotation-timezone").val("UTC");
    updateRotationCadenceFields();
    initTimezoneSelect(
        "#rotation-timezone",
        "UTC",
        "#rotation-form-modal"
    );
}

let rotationOverridesAfterChange = null;


function findRotationInCache(rotationId) {
    /*
     * Return a rotation from local cache.
     */
    return rotationsCache.find(function (item) {
        return Number(item.id) === Number(rotationId);
    });
}


function rememberRotationInCache(rotation) {
    /*
     * Add or replace one rotation in rotationsCache.
     */
    const rotationId = Number(rotation.id);
    const index = rotationsCache.findIndex(function (item) {
        return Number(item.id) === rotationId;
    });

    if (index >= 0) {
        rotationsCache[index] = rotation;
        return;
    }

    rotationsCache.push(rotation);
}


function ensureOverrideRotationOption(rotation) {
    /*
     * Ensure the overrides modal rotation selector has the selected rotation.
     */
    const select = $("#override-rotation");
    const rotationId = String(rotation.id);

    if (!select.find('option[value="' + rotationId + '"]').length) {
        select.append(
            $("<option>")
                .val(rotationId)
                .text((rotation.team_slug || rotation.team_name || "-") + " / " + rotation.name)
        );
    }

    select.val(rotationId);
}


function loadRotationForOverride(rotationId, callback) {
    /*
     * Load rotation for override modal if it is not already cached.
     */
    const cachedRotation = findRotationInCache(rotationId);

    if (cachedRotation) {
        callback(cachedRotation);
        return;
    }

    apiGet("/api/rotations/" + encodeURIComponent(rotationId), function (rotation) {
        if (!rotation || !rotation.id) {
            showAppError("Rotation was not found.");
            return;
        }

        rememberRotationInCache(rotation);
        callback(rotation);
    });
}


function selectOverrideRotation(rotationId, options) {
    /*
     * Select a rotation, load eligible users, prefill override fields
     * and open the existing overrides modal.
     */
    options = options || {};

    if (!rotationId) {
        showAppError("Rotation was not found.");
        return;
    }

    loadRotationForOverride(rotationId, function (rotation) {
        rotationOverridesAfterChange = typeof options.afterChange === "function"
            ? options.afterChange
            : null;

        ensureOverrideRotationOption(rotation);

        fillRotationEligibleUserSelect("#override-user", rotation.id, function () {
            openRotationOverridesModal();

            $("#override-rotation").val(String(rotation.id));

            applyOverridePrefill(options);

            loadOverrides();
        });
    });
}

function loadOverrides() {
    /* Load overrides for the selected rotation. */
    const rotationId = $("#override-rotation").val();
    const tbody = $("#overrides-table");

    tbody.empty();

    if (!rotationId) {
        tbody.append($("<tr>").append($("<td>").attr("colspan", "6").text("No rotation selected")));
        return;
    }

    const rotation = rotationsCache.find(function (item) { return item.id === Number(rotationId); });
    $("#overrides-title").text("Overrides" + (rotation ? ": " + rotation.name : ""));

    apiGet("/api/rotations/" + rotationId + "/overrides", function (overrides) {
        if (!overrides.length) {
            tbody.append($("<tr>").append($("<td>").attr("colspan", "6").text("No overrides")));
            return;
        }

        overrides.forEach(function (override) {
            const row = $("<tr>");
            row.append($("<td>").text(override.id));
            row.append($("<td>").text(override.display_name || override.username));
            row.append($("<td>").text(formatDateTime24(override.starts_at)));
            row.append($("<td>").text(formatDateTime24(override.ends_at)));
            row.append($("<td>").text(override.reason || "-"));

            const actions = $("<td>").addClass("actions");
            actions.append($("<button>").attr("type", "button").addClass("btn btn-danger btn-small").text("Delete").on("click", function () {
                deleteOverride(override.id);
            }));
            row.append(actions);

            tbody.append(row);
        });
    });
}

function createOverride() {
    /*
     * Create a temporary rotation override.
     */
    const rotationId = $("#override-rotation").val();

    if (!rotationId) {
        showAppError("Select a rotation first.");
        return;
    }

    apiPost("/api/rotations/" + rotationId + "/overrides", {
        user_id: Number($("#override-user").val()),
        starts_at: $("#override-starts-at").val(),
        ends_at: $("#override-ends-at").val(),
        reason: $("#override-reason").val() || null
    }, function () {
        $("#override-reason").val("");
        loadOverrides();

        if (typeof rotationOverridesAfterChange === "function") {
            rotationOverridesAfterChange();
        }

        showAppSuccess("Override created.");
    });
}


function deleteOverride(overrideId) {
    /*
     * Delete a rotation override.
     */
    showAppConfirm({
        title: "Disable this override?",
        message: "Disable this override?",
        confirmText: "Disable override?",
        confirmClass: "btn-danger",
    }).done(function () {
        apiDelete("/api/rotations/overrides/" + overrideId, function () {
            loadOverrides();

            if (typeof rotationOverridesAfterChange === "function") {
                rotationOverridesAfterChange();
            }
        });
    });
}

$(document).on("change", "#rotation-type", updateRotationCadenceFields);

$(document).on("change", "#override-rotation", function () {
    const rotationId = $(this).val();

    fillRotationEligibleUserSelect("#override-user", rotationId, loadOverrides);
});
$(document).on("click", "#save-rotation", saveRotation);
$(document).on("click", "#reset-rotation-form", resetRotationForm);
$(document).on("click", "#reload-rotations", refreshRotations);
$(document).on("click", "#reload-overrides", loadOverrides);
$(document).on("click", "#create-override", createOverride);

function renderRotationsTable() {
    /*
     * Render rotations table using current filters.
     */
    const tbody = $("#rotations-table");
    const rotations = getFilteredRotations();

    tbody.empty();

    $("#rotations-filtered-count").text(rotations.length);
    $("#rotations-total-count").text(rotationsCache.length);

    if (!rotations.length) {
        tbody.append(
            $("<tr>").append(
                $("<td>")
                    .attr("colspan", "8")
                    .addClass("empty-cell")
                    .text("No rotations")
            )
        );
        return;
    }

    rotations.forEach(function (rotation) {
        tbody.append(renderRotationRow(rotation));
    });
}


function renderRotationRow(rotation) {
    /*
     * Render one rotation row.
     */
    const row = $("<tr>");

    const rotationName = $("<button>")
        .attr("type", "button")
        .addClass("rotation-name-button")
        .text(rotation.name || "-")
        .on("click", function () {
            renderRotationDetails(rotation);
        });

    row.append(
        $("<td>")
            .append(rotationName)
            .append(
                $("<div>")
                    .addClass("row-subtitle")
                    .text(rotation.description || "Rotation #" + rotation.id)
            )
    );

    row.append(
        $("<td>").append(
            $("<span>")
                .addClass("team-pill")
                .text(rotation.team_name || rotation.team_slug || "-")
        )
    );

    row.append($("<td>").text(getRotationCadence(rotation)));

    const currentUser = getRotationCurrentUser(rotation);

    if (currentUser) {
        row.append(
            $("<td>").append(
                $("<div>")
                    .addClass("rotation-current-user")
                    .append($("<div>").addClass("rotation-user-avatar").text(rotationInitials(currentUser)))
                    .append(
                        $("<div>")
                            .append($("<div>").addClass("rotation-user-name").text(currentUser))
                            .append($("<div>").addClass("rotation-user-meta").text("Currently on call"))
                    )
            )
        );
    } else {
        row.append($("<td>").append($("<span>").addClass("rotation-empty-user").text("-")));
    }

    row.append($("<td>").text(rotation.handoff_time || "-"));
    row.append($("<td>").text(formatSeconds(rotation.reminder_interval_seconds)));

    row.append(
        $("<td>").append(
            renderStatusBadge(rotation.enabled, "Active", "Inactive")
        )
    );

    const actions = $("<div>").addClass("table-actions");

    actions.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-small")
            .text("Edit")
            .on("click", function () {
                editRotation(rotation.id);
            })
    );

    actions.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-small")
            .text("Layers")
            .on("click", function () {
                selectRotationLayers(rotation.id);
            })
    );

    actions.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-small")
            .text("Overrides")
            .on("click", function () {
                selectOverrideRotation(rotation.id);
            })
    );

    actions.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-danger btn-small")
            .text("Disable")
            .on("click", function () {
                deleteRotation(rotation.id);
            })
    );

    row.append($("<td>").addClass("actions-cell").append(actions));

    return row;
}

$(document).on("input", "#rotations-search", renderRotationsTable);
$(document).on("change", "#rotations-team-filter, #rotations-status-filter", renderRotationsTable);
function openRotationFormModal() {
    /*
     * Open rotation create/edit modal.
     */
    $("#rotation-form-modal")
        .css("display", "flex")
        .addClass("is-open");
    initTimezoneSelect(
        "#rotation-timezone",
        "UTC",
        "#rotation-form-modal"
    );
    $("body").addClass("modal-open");
}


function closeRotationFormModal() {
    /*
     * Close rotation create/edit modal.
     */
    $("#rotation-form-modal")
        .css("display", "none")
        .removeClass("is-open");

    $("body").removeClass("modal-open");
}


function openCreateRotationModal() {
    /*
     * Reset form and open modal in create mode.
     */
    resetRotationForm();
    $("#rotation-form-title").text("Create rotation");
    openRotationFormModal();
}
$(document).on("click", "#open-rotation-create-modal", openCreateRotationModal);

$(document).on("click", "#close-rotation-form-modal", closeRotationFormModal);

$(document).on("click", "#rotation-form-modal", function (event) {
    if (event.target === this) {
        closeRotationFormModal();
    }
});

$(document).on("keydown", function (event) {
    if (event.key === "Escape" && $("#rotation-form-modal").hasClass("is-open")) {
        closeRotationFormModal();
    }
});

function openRotationOverridesModal() {
    /*
     * Open rotation overrides modal.
     */
    $("#rotation-overrides-modal")
        .css("display", "flex")
        .addClass("is-open");

    $("body").addClass("modal-open");
}


function closeRotationOverridesModal() {
    /*
     * Close rotation overrides modal.
     */
    $("#rotation-overrides-modal")
        .css("display", "none")
        .removeClass("is-open");

    $("body").removeClass("modal-open");
    rotationOverridesAfterChange = null;
}

$(document).on("click", "#close-rotation-overrides-modal, #close-rotation-overrides-modal-footer", closeRotationOverridesModal);

$(document).on("click", "#rotation-overrides-modal", function (event) {
    if (event.target === this) {
        closeRotationOverridesModal();
    }
});

$(document).on("keydown", function (event) {
    if (event.key !== "Escape") {
        return;
    }

    if ($("#rotation-overrides-modal").hasClass("is-open")) {
        closeRotationOverridesModal();
    }
});
function getRotationCadence(rotation) {
    /*
     * Return human-readable rotation cadence.
     */
    if (rotation.rotation_type === "custom") {
        return (rotation.custom_days || 1) + "d";
    }

    if (rotation.rotation_type === "weekly") {
        return "weekly";
    }

    if (rotation.rotation_type === "daily") {
        return "daily";
    }

    return rotation.rotation_type || "-";
}

function rotationDetailsItem(label, value) {
    /*
     * Render one details item.
     */
    return $("<div>")
        .addClass("details-item")
        .append($("<div>").addClass("details-label").text(label))
        .append($("<div>").addClass("details-value").text(value || "-"));
}


function renderRotationDetails(rotation) {
    /*
     * Render selected rotation in right-side details panel.
     */
    selectedRotationDetailsId = rotation.id;

    $("#rotation-details-subtitle").text(
        (rotation.team_slug || rotation.team_name || "-") +
        " / " +
        (rotation.enabled ? "Active" : "Inactive")
    );

    const body = $("#rotation-details-body");
    body.empty();

    body.append(
        $("<div>")
            .addClass("details-list")
            .append(rotationDetailsItem("Name", rotation.name))
            .append(rotationDetailsItem("Team", rotation.team_name || rotation.team_slug))
            .append(rotationDetailsItem("Current on call", getRotationCurrentUser(rotation) || "-"))
            .append(rotationDetailsItem("Cadence", getRotationCadence(rotation)))
            .append(rotationDetailsItem("Handoff time", rotation.handoff_time))
            .append(rotationDetailsItem("Reminder", formatSeconds(rotation.reminder_interval_seconds)))
            .append(rotationDetailsItem("Timezone", rotation.timezone))
            .append(rotationDetailsItem("Description", rotation.description))
    );

    body.append(
        $("<div>")
            .addClass("details-actions")
            .append(
                makeIconButton({
                    icon: "fas fa-edit",
                    label: "Edit rotation",
                    onClick: function () {
                        editRotation(rotation.id);
                    }
                })
            )
            .append(
                makeIconButton({
                    icon: "fas fa-layer-group",
                    label: "Rotation layers",
                    onClick: function () {
                        selectRotationLayers(rotation.id);
                    }
                })
            )
            .append(
                makeIconButton({
                    icon: "fas fa-user-clock",
                    label: "Rotation overrides",
                    onClick: function () {
                        selectOverrideRotation(rotation.id);
                    }
                })
            )
            .append(
                makeIconButton({
                    icon: "fas fa-calendar-alt",
                    label: "Open calendar",
                    onClick: function () {
                        navigate("/calendar?team_id=" + encodeURIComponent(rotation.team_id), true);
                    }
                })
            )
            .append(
                makeIconButton({
                    icon: "fas fa-pause",
                    label: "Disable rotation",
                    className: "btn-danger",
                    onClick: function () {
                        deleteRotation(rotation.id);
                    }
                })
            )
    );
}

function renderRotationsInboxCounter(filteredRotations, allRotations) {
    /*
     * Render "Showing X of Y rotations" counter.
     */
    filteredRotations = Array.isArray(filteredRotations) ? filteredRotations : [];
    allRotations = Array.isArray(allRotations) ? allRotations : [];

    $("#rotations-filtered-count").text(filteredRotations.length);
    $("#rotations-total-count").text(allRotations.length);
}
function fillRotationEligibleUserSelect(selector, rotationId, callback) {
    /*
     * Fill user select with users eligible for this rotation.
     */
    const select = $(selector);
    select.empty();

    if (!rotationId) {
        select.append(
            $("<option>")
                .val("")
                .text("Select rotation first")
        );

        if (typeof callback === "function") {
            callback([]);
        }

        return;
    }

    apiGet("/api/rotations/" + rotationId + "/eligible-users", function (users) {
        users = asArray(users);

        select.empty();

        if (!users.length) {
            select.append(
                $("<option>")
                    .val("")
                    .text("No active team members")
            );
        }

        users.forEach(function (user) {
            select.append(
                $("<option>")
                    .val(user.user_id)
                    .text("#" + user.user_id + " " + (user.display_name || user.username || "user"))
            );
        });

        if (typeof callback === "function") {
            callback(users);
        }
    });
}
function applyOverridePrefill(options) {
    /*
     * Apply optional override form prefill.
     *
     * This must be called after:
     *   - override modal exists in DOM
     *   - rotation select has the rotation option
     *   - eligible users select is filled
     */
    options = options || {};

    if (options.userId) {
        $("#override-user").val(String(options.userId));
    }

    if (options.startsAt) {
        $("#override-starts-at").val(options.startsAt);
    }

    if (options.endsAt) {
        $("#override-ends-at").val(options.endsAt);
    }

    if (options.reason !== undefined) {
        $("#override-reason").val(options.reason || "");
    }
}
function initLayerTimezoneSelects() {
    $(".rotation-layer-card.is-editing select.timezone-select").each(function () {
        const select = $(this);

        if ($.fn.select2) {
            if (select.hasClass("select2-hidden-accessible")) {
                select.select2("destroy");
            }

            select.select2({
                width: "100%",
                placeholder: "Select timezone",
                dropdownParent: $("#rotation-layers-modal")
            });
        }
    });
}
