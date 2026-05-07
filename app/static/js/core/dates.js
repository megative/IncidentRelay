function padDateTimePart(value) {
    /*
     * Return a date/time part as a two-digit string.
     */
    return String(value).padStart(2, "0");
}
const dateTimeFormattersCache = {};


function getBrowserLocales() {
    /*
     * Return browser-preferred locales for date/time formatting.
     */
    if (navigator.languages && navigator.languages.length) {
        return navigator.languages;
    }

    if (navigator.language) {
        return navigator.language;
    }

    return "en-GB";
}


function parseDisplayDate(value) {
    /*
     * Parse an API datetime value or Date object.
     */
    if (!value) {
        return null;
    }

    const date = value instanceof Date ? value : new Date(value);

    if (Number.isNaN(date.getTime())) {
        return null;
    }

    return date;
}


function getDateTimeFormatter(kind) {
    /*
     * Return cached browser-locale formatter.
     */
    const locales = getBrowserLocales();
    const cacheKey = kind + ":" + JSON.stringify(locales);

    if (dateTimeFormattersCache[cacheKey]) {
        return dateTimeFormattersCache[cacheKey];
    }

    const optionsByKind = {
        date: {
            year: "numeric",
            month: "2-digit",
            day: "2-digit"
        },
        shortDate: {
            month: "2-digit",
            day: "2-digit"
        },
        time: {
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        },
        timeMinutes: {
            hour: "2-digit",
            minute: "2-digit"
        },
        dateTime: {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit",
            second: "2-digit"
        },
        dateTimeMinutes: {
            year: "numeric",
            month: "2-digit",
            day: "2-digit",
            hour: "2-digit",
            minute: "2-digit"
        }
    };

    dateTimeFormattersCache[cacheKey] = new Intl.DateTimeFormat(
        locales,
        optionsByKind[kind] || optionsByKind.dateTime
    );

    return dateTimeFormattersCache[cacheKey];
}


function formatBrowserDate(value, kind) {
    /*
     * Format date/time using browser locale preferences.
     */
    const date = parseDisplayDate(value);

    if (!date) {
        return "-";
    }

    return getDateTimeFormatter(kind || "dateTime").format(date);
}


function formatDate(value) {
    /*
     * Format date using browser locale.
     */
    return formatBrowserDate(value, "date");
}


function formatShortDate(value) {
    /*
     * Format short date using browser locale.
     */
    return formatBrowserDate(value, "shortDate");
}


function formatTime(value) {
    /*
     * Format time using browser locale.
     */
    return formatBrowserDate(value, "time");
}


function formatTimeMinutes(value) {
    /*
     * Format time without seconds using browser locale.
     */
    return formatBrowserDate(value, "timeMinutes");
}


function formatDateTime(value) {
    /*
     * Format datetime using browser locale.
     */
    return formatBrowserDate(value, "dateTime");
}

function formatDateTimeMinutes(value) {
    /*
     * Format datetime without seconds using browser locale.
     */
    return formatBrowserDate(value, "dateTimeMinutes");
}


/*
 * Temporary compatibility wrapper for old code.
 * It no longer forces 24-hour format; browser settings decide that.
 */
function formatDateTime24(value, options) {
    if (options && options.seconds === false) {
        return formatDateTimeMinutes(value);
    }

    return formatDateTime(value);
}
function isoToDatetimeLocal(value) {
    /* Convert an ISO date string to datetime-local format. */
    if (!value) { return ""; }
    return value.slice(0, 16);
}
