(function () {
    const RULES_URL = "/api/profile/notification-rules";
    let notificationRulesCache = [];

    document.addEventListener("DOMContentLoaded", function () {
        if (!document.getElementById("notification-rules-card")) {
            return;
        }

        bindNotificationRuleEvents();
        loadNotificationRules();
    });

    function bindNotificationRuleEvents() {
        $("#open-notification-rule-modal").off("click").on("click", function () {
            resetNotificationRuleForm();
            openNotificationRuleModal();
        });

        $("#reload-notification-rules-btn").off("click").on("click", function () {
            loadNotificationRules();
        });

        $("#save-notification-rule-btn").off("click").on("click", function () {
            saveNotificationRule();
        });

        $("#close-notification-rule-modal, #cancel-notification-rule")
            .off("click")
            .on("click", function () {
                closeNotificationRuleModal();
            });
    }

    function openNotificationRuleModal() {
        if (typeof openAppModal === "function") {
            openAppModal("#notification-rule-modal");
            return;
        }

        $("#notification-rule-modal").removeClass("is-hidden").addClass("is-open");
    }

    function closeNotificationRuleModal(selector) {
        selector = selector || "#notification-rule-modal";

        if (typeof closeAppModal === "function") {
            closeAppModal(selector);
            return;
        }

        $(selector).addClass("is-hidden").removeClass("is-open");
    }

    function loadNotificationRules() {
        const tbody = $("#notification-rules-body");

        tbody.empty().append(
            $("<tr>").append(
                $("<td>")
                    .attr("colspan", "7")
                    .addClass("empty-cell")
                    .text("Loading notification rules...")
            )
        );

        apiGet(RULES_URL, function (rules) {
            notificationRulesCache = asArray(rules);
            renderNotificationRulesTable();
        });
    }

    function renderNotificationRulesTable() {
        const tbody = $("#notification-rules-body");
        tbody.empty();

        if (!notificationRulesCache.length) {
            tbody.append(
                $("<tr>").append(
                    $("<td>")
                        .attr("colspan", "7")
                        .addClass("empty-cell")
                        .text("No custom notification rules yet. Browser push still works automatically if it is enabled in your profile.")
                )
            );
            return;
        }

        notificationRulesCache.forEach(function (rule) {
            tbody.append(renderNotificationRuleRow(rule));
        });
    }

    function renderNotificationRuleRow(rule) {
        const row = $("<tr>");

        row.append($("<td>").text(rule.position || "-"));
        row.append($("<td>").text(formatMethod(rule.method)));
        row.append($("<td>").text(formatDelay(rule.delay_seconds)));
        row.append($("<td>").text(formatList(rule.severities, "All severities")));
        row.append($("<td>").text(formatEventTypes(rule.event_types)));
        row.append(
            $("<td>").append(
                renderStatusBadge(Boolean(rule.enabled), "Enabled", "Disabled")
            )
        );
        row.append(
            $("<td>")
                .addClass("actions-cell")
                .append(renderNotificationRuleActions(rule))
        );

        return row;
    }

    function renderNotificationRuleActions(rule) {
        return makeActionMenu({
            object: rule,
            items: [
                {
                    label: "Edit",
                    icon: "fas fa-edit",
                    onClick: function () {
                        editNotificationRule(rule.id);
                    }
                },
                {
                    label: rule.enabled ? "Disable" : "Enable",
                    icon: rule.enabled ? "fas fa-pause" : "fas fa-play",
                    danger: rule.enabled,
                    onClick: function () {
                        updateNotificationRule(rule.id, {
                            enabled: !rule.enabled
                        });
                    }
                },
                {
                    label: "Delete",
                    icon: "fas fa-trash",
                    danger: true,
                    onClick: function () {
                        deleteNotificationRule(rule);
                    }
                }
            ]
        });
    }

    function resetNotificationRuleForm() {
        $("#notification-rule-modal-title").text("Create notification rule");
        $("#notification-rule-id").val("");
        $("#notification-rule-method").val("browser_push");
        $("#notification-rule-delay").val("0");
        $("#notification-rule-enabled").prop("checked", true);
        $(".notification-rule-severity").prop("checked", false);
        $(".notification-rule-event-type").prop("checked", false);
    }

    function editNotificationRule(ruleId) {
        const rule = notificationRulesCache.find(function (item) {
            return Number(item.id) === Number(ruleId);
        });

        if (!rule) {
            return;
        }

        $("#notification-rule-modal-title").text("Edit notification rule #" + rule.id);
        $("#notification-rule-id").val(rule.id);
        $("#notification-rule-method").val(rule.method || "browser_push");
        $("#notification-rule-delay").val(String(rule.delay_seconds || 0));
        $("#notification-rule-enabled").prop("checked", Boolean(rule.enabled));

        setCheckedValues(".notification-rule-severity", rule.severities || []);
        setCheckedValues(".notification-rule-event-type", rule.event_types || []);

        openNotificationRuleModal();
    }

    function saveNotificationRule() {
        const id = $("#notification-rule-id").val();
        const payload = collectNotificationRulePayload();

        if (id) {
            apiPut(RULES_URL + "/" + id, payload, function () {
                closeNotificationRuleModal();
                loadNotificationRules();
            });
            return;
        }

        apiPost(RULES_URL, payload, function () {
            closeNotificationRuleModal();
            loadNotificationRules();
        });
    }

    function collectNotificationRulePayload() {
        return {
            method: $("#notification-rule-method").val(),
            delay_seconds: Number($("#notification-rule-delay").val() || 0),
            severities: getCheckedValues(".notification-rule-severity"),
            event_types: getCheckedValues(".notification-rule-event-type"),
            enabled: $("#notification-rule-enabled").is(":checked")
        };
    }

    function updateNotificationRule(ruleId, payload) {
        apiPut(RULES_URL + "/" + ruleId, payload, function () {
            loadNotificationRules();
        });
    }

    function deleteNotificationRule(rule) {
        showAppConfirm({
            title: "Delete this notification rule?",
            message: "Delete notification rule #" + rule.id + "?",
            confirmText: "Delete",
            confirmClass: "btn-danger"
        }).done(function () {
            apiDelete(RULES_URL + "/" + rule.id, function () {
                loadNotificationRules();
            });
        });
    }

    function getCheckedValues(selector) {
        return $(selector + ":checked").map(function () {
            return this.value;
        }).get();
    }

    function setCheckedValues(selector, values) {
        values = asArray(values).map(String);

        $(selector).each(function () {
            $(this).prop("checked", values.includes(String(this.value)));
        });
    }

    function formatMethod(method) {
        if (method === "browser_push") {
            return "Browser push";
        }

        if (method === "voice_call") {
            return "Voice call";
        }

        if (method === "email") {
            return "Email";
        }

        return method || "-";
    }

    function formatDelay(seconds) {
        const value = Number(seconds || 0);

        if (value <= 0) {
            return "Immediately";
        }

        if (value < 60) {
            return value + " sec";
        }

        const minutes = Math.round(value / 60);

        if (minutes === 1) {
            return "After 1 minute";
        }

        return "After " + minutes + " minutes";
    }

    function formatList(values, emptyLabel) {
        values = asArray(values);

        if (!values.length) {
            return emptyLabel;
        }

        return values.join(", ");
    }

    function formatEventTypes(values) {
        values = asArray(values);

        if (!values.length) {
            return "Default events";
        }

        return values.map(function (value) {
            if (value === "notification") {
                return "initial alert";
            }

            return value;
        }).join(", ");
    }
})();
