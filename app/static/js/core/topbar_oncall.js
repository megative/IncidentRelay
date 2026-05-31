let topbarOncallRefreshTimer = null;

function topbarDisplayName(name, slug, fallback) {
    return name || slug || fallback || "-";
}

function topbarFormatOncallDate(value, timezone) {
    if (typeof formatShortDateTimeMinutesInTimezone === "function") {
        return formatShortDateTimeMinutesInTimezone(value, timezone || "UTC");
    }

    if (typeof formatDateTime24 === "function") {
        return formatDateTime24(value, {seconds: false});
    }

    return value || "-";
}

function topbarFormatOncallSlot(slot) {
    const team = topbarDisplayName(slot.team_name, slot.team_slug, "Team");
    const rotation = slot.rotation_name || ("Rotation #" + slot.rotation_id);
    const layer = slot.layer_name || (slot.type === "override" ? "Override" : "Layer");
    const timezone = slot.timezone || "UTC";

    return [
        team + " / " + rotation + " / " + layer,
        topbarFormatOncallDate(slot.start, timezone)
            + " → "
            + topbarFormatOncallDate(slot.end, timezone)
    ].join(" — ");
}

function buildTopbarOncallTooltip(data) {
    const current = asArray(data && data.current);
    const next = asArray(data && data.next);
    const lines = [];

    if (data && data.is_oncall) {
        lines.push("You are on-call now");

        current.slice(0, 3).forEach(function (slot) {
            lines.push("• " + topbarFormatOncallSlot(slot));
        });
    } else {
        lines.push("You are not on-call now");
    }

    lines.push("");

    if (next.length) {
        lines.push("Next shifts:");

        next.slice(0, 5).forEach(function (slot) {
            lines.push("• " + topbarFormatOncallSlot(slot));
        });
    } else {
        lines.push("No upcoming shifts in the next " + ((data && data.lookahead_days) || 30) + " days.");
    }

    return lines.join("\n");
}

function renderTopbarOncallStatus(data) {
    const indicator = $("#topbar-oncall-indicator");

    if (!indicator.length) {
        return;
    }

    const status = oncallStatusKind(data || {});
    const tooltip = oncallBuildTooltip(data || {});

    indicator
        .removeClass(
            "topbar-oncall-unknown "
            + "topbar-oncall-active "
            + "topbar-oncall-escalation "
            + "topbar-oncall-idle"
        )
        .addClass(
            status === "primary"
                ? "topbar-oncall-active"
                : status === "escalation"
                    ? "topbar-oncall-escalation"
                    : "topbar-oncall-idle"
        )
        .attr("title", tooltip)
        .attr(
            "aria-label",
            status === "primary"
                ? "You are primary on-call now"
                : status === "escalation"
                    ? "You are escalation backup now"
                    : "You are not on-call now"
        );

    $("#topbar-profile").attr("title", tooltip);
}

function renderTopbarOncallUnknown(message) {
    const tooltip = message || "On-call status is unavailable";

    $("#topbar-oncall-indicator")
        .removeClass("topbar-oncall-active topbar-oncall-idle")
        .addClass("topbar-oncall-unknown")
        .attr("title", tooltip)
        .attr("aria-label", tooltip);

    $("#topbar-profile").attr("title", tooltip);
}

function loadTopbarOncallStatus() {
    if (!currentUser) {
        renderTopbarOncallUnknown("Not authenticated");
        return;
    }

    apiGet(
        "/api/profile/oncall?days=30",
        function (data) {
            renderTopbarOncallStatus(data || {});
        },
        function () {
            renderTopbarOncallUnknown("On-call status is unavailable");
        }
    );
}

function startTopbarOncallStatusRefresh() {
    if (topbarOncallRefreshTimer) {
        clearInterval(topbarOncallRefreshTimer);
        topbarOncallRefreshTimer = null;
    }

    loadTopbarOncallStatus();

    topbarOncallRefreshTimer = setInterval(function () {
        loadTopbarOncallStatus();
    }, 60000);
}
