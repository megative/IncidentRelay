function oncallStatusPillClass(status) {
    return {
        primary: "status-active",
        escalation: "status-scheduled",
        idle: "status-neutral",
        unknown: "status-neutral"
    }[status || "unknown"] || "status-neutral";
}

function renderOncallStatusPill(data) {
    const status = oncallStatusKind(data || {});

    const textByStatus = {
        primary: "Primary on-call now",
        escalation: "Escalation backup now",
        idle: "Not on-call now"
    };

    return $("<span>")
        .addClass("status-pill")
        .addClass(oncallStatusPillClass(status))
        .text(textByStatus[status] || "Unknown");
}

function renderOncallPrimarySlotCard(slot) {
    const card = $("<div>").addClass("slot-card");

    card.append(
        $("<div>")
            .addClass("slot-title")
            .text(oncallDisplayName(slot.team_name, slot.team_slug, "Team"))
    );

    card.append(
        $("<div>")
            .addClass("slot-meta")
            .text([
                slot.rotation_name || ("Rotation #" + slot.rotation_id),
                slot.layer_name || (slot.type === "override" ? "Override" : "Layer"),
                slot.timezone || "UTC"
            ].filter(Boolean).join(" · "))
    );

    card.append(
        $("<div>")
            .addClass("slot-time")
            .text(
                oncallFormatDate(slot.start, slot.timezone)
                + " → "
                + oncallFormatDate(slot.end, slot.timezone)
            )
    );

    if (slot.type === "override" && slot.reason) {
        card.append(
            $("<div>")
                .addClass("slot-reason")
                .text(slot.reason)
        );
    }

    return card;
}

function renderOncallEscalationCard(item) {
    const card = $("<div>").addClass("slot-card escalation-card");

    card.append(
        $("<div>")
            .addClass("slot-title")
            .text(oncallDisplayName(item.team_name, item.team_slug, item.team_display || "Team"))
    );

    card.append(
        $("<div>")
            .addClass("slot-meta")
            .text([
                item.policy_name || ("Policy #" + item.policy_id),
                "level " + (item.level || "-"),
                item.delay_seconds ? "after " + Math.round(Number(item.delay_seconds) / 60) + " min" : null
            ].filter(Boolean).join(" · "))
    );

    if (item.kind === "rotation" && item.start && item.end) {
        card.append(
            $("<div>")
                .addClass("slot-time")
                .text(
                    (item.rotation_name || ("Rotation #" + item.rotation_id))
                    + " · "
                    + oncallFormatDate(item.start, item.timezone)
                    + " → "
                    + oncallFormatDate(item.end, item.timezone)
                )
        );
    } else {
        card.append(
            $("<div>")
                .addClass("slot-time")
                .text("Direct user escalation target")
        );
    }

    return card;
}

function renderOncallSection(title, items, renderer, emptyText) {
    const section = $("<section>").addClass("section");

    section.append(
        $("<div>")
            .addClass("section-title")
            .text(title)
    );

    const list = $("<div>").addClass("list");

    if (!items.length) {
        list.append(
            $("<div>")
                .addClass("empty")
                .text(emptyText)
        );
    } else {
        items.forEach(function (item) {
            list.append(renderer(item));
        });
    }

    section.append(list);

    return section;
}

function renderOncallStatusPanel(target, data) {
    const root = $(target);
    const current = oncallAsArray(data && data.current);
    const next = oncallAsArray(data && data.next);
    const escalationCurrent = oncallAsArray(data && data.escalation_current);
    const escalationNext = oncallAsArray(data && data.escalation_next);

    root.empty();

    const header = $("<div>").addClass("panel-header");

    header.append(renderOncallStatusPill(data || {}));

    header.append(
        $("<button>")
            .attr("type", "button")
            .addClass("btn btn-small")
            .text("Refresh")
            .on("click", function () {
                loadOncallStatusPanel(root);
            })
    );

    root.append(header);

    root.append(
        renderOncallSection(
            "Current primary shifts",
            current,
            renderOncallPrimarySlotCard,
            "You are not primary on-call now."
        )
    );

    root.append(
        renderOncallSection(
            "Current escalation backup",
            escalationCurrent,
            renderOncallEscalationCard,
            "You are not an active escalation backup now."
        )
    );

    root.append(
        renderOncallSection(
            "Next primary shifts",
            next,
            renderOncallPrimarySlotCard,
            "No upcoming primary shifts in the selected lookahead window."
        )
    );

    root.append(
        renderOncallSection(
            "Next escalation backup shifts",
            escalationNext,
            renderOncallEscalationCard,
            "No upcoming escalation backup shifts in the selected lookahead window."
        )
    );
}

function loadOncallStatusPanel(target, options) {
    const root = $(target);
    const opts = options || {};
    const days = opts.days || 30;
    const endpoint = opts.endpoint || "/api/profile/oncall";

    root.empty().append(
        $("<div>")
            .addClass("empty")
            .text("Loading on-call status...")
    );

    apiGet(endpoint + "?days=" + encodeURIComponent(days), function (data) {
        renderOncallStatusPanel(root, data || {});
    });
}
