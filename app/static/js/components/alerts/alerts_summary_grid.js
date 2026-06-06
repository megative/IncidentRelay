function normalizeSummaryStatus(status) {
    /*
     * Normalize alert status for summary counters.
     */
    return String(status || "").toLowerCase();
}


function renderAlertsSummaryGrid(containerSelector, alertsOrSummary) {
    const container = $(containerSelector);

    let counters = {
        firing: 0,
        acknowledged: 0,
        resolved: 0,
        reminders: 0,
        total: 0
    };

    if (Array.isArray(alertsOrSummary)) {
        counters.total = alertsOrSummary.length;

        alertsOrSummary.forEach(function (alert) {
            const status = normalizeSummaryStatus(alert.status);

            if (status === "firing") {
                counters.firing += 1;
            }

            if (status === "acknowledged") {
                counters.acknowledged += 1;
            }

            if (status === "resolved") {
                counters.resolved += 1;
            }

            counters.reminders += Number(alert.reminder_count || 0);
        });
    } else if (alertsOrSummary && typeof alertsOrSummary === "object") {
        counters = {
            firing: Number(alertsOrSummary.firing || 0),
            acknowledged: Number(alertsOrSummary.acknowledged || 0),
            resolved: Number(alertsOrSummary.resolved || 0),
            reminders: Number(alertsOrSummary.reminders || 0),
            total: Number(alertsOrSummary.total || 0)
        };
    }

    container.find('[data-summary-value="firing"]').text(counters.firing);
    container.find('[data-summary-value="acknowledged"]').text(counters.acknowledged);
    container.find('[data-summary-value="resolved"]').text(counters.resolved);
    container.find('[data-summary-value="reminders"]').text(counters.reminders);
    container.find('[data-summary-value="total"]').text(counters.total);
}
function openClickableSummaryCard(card) {
    /*
     * Open a summary card target.
     */
    const href = $(card).data("href");

    if (!href) {
        return;
    }

    navigate(String(href), true);
}


$(document).on("click", ".clickable-summary-card", function (event) {
    /*
     * Navigate when a summary card is clicked.
     */
    if ($(event.target).closest("a, button, input, select, textarea").length) {
        return;
    }

    openClickableSummaryCard(this);
});


$(document).on("keydown", ".clickable-summary-card", function (event) {
    /*
     * Support keyboard navigation for clickable summary cards.
     */
    if (event.key !== "Enter" && event.key !== " ") {
        return;
    }

    event.preventDefault();
    openClickableSummaryCard(this);
});
