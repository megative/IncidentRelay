function normalizePhoneInputValue(value) {
    /*
     * Allow only digits and one optional leading plus.
     */
    value = String(value || "").replace(/[^\d+]/g, "");

    const hasLeadingPlus = value.startsWith("+");

    value = value.replace(/\+/g, "");

    if (value.length > 20) {
        value = value.substring(0, 20);
    }

    return (hasLeadingPlus ? "+" : "") + value;
}

$(document).on("input", 'input[data-phone-input="true"]', function () {
    this.value = normalizePhoneInputValue(this.value);
});
