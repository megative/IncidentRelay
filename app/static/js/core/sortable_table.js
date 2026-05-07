function createTableSortState(column, direction) {
    /*
     * Create a reusable table sort state object.
     *
     * Pages should keep this object globally and pass it to
     * bindSortableTableHeaders() and sortTableData().
     */
    return {
        column: column,
        direction: normalizeSortDirection(direction || "asc")
    };
}


function normalizeSortDirection(direction) {
    /*
     * Return a safe sort direction.
     */
    return direction === "asc" ? "asc" : "desc";
}


function getSortablePathValue(item, path) {
    /*
     * Read a value from an object using a dotted path.
     *
     * Example:
     *   getSortablePathValue(alert, "team.slug")
     */
    if (!path) {
        return null;
    }

    return String(path)
        .split(".")
        .reduce(function (value, key) {
            if (value === null || value === undefined) {
                return null;
            }

            return value[key];
        }, item);
}


function normalizeSortableValue(value, type) {
    /*
     * Normalize values before comparing them.
     */
    if (type === "number" || type === "rank") {
        const numberValue = Number(value);
        return Number.isNaN(numberValue) ? 0 : numberValue;
    }

    if (type === "datetime") {
        if (!value) {
            return 0;
        }

        const timestamp = new Date(value).getTime();
        return Number.isNaN(timestamp) ? 0 : timestamp;
    }

    if (type === "boolean") {
        return value ? 1 : 0;
    }

    return String(value || "").toLowerCase();
}


function compareSortableValues(left, right, type) {
    /*
     * Compare two normalized values.
     */
    const leftValue = normalizeSortableValue(left, type);
    const rightValue = normalizeSortableValue(right, type);

    if (type === "number" || type === "rank" || type === "datetime" || type === "boolean") {
        return leftValue - rightValue;
    }

    return leftValue.localeCompare(rightValue, undefined, {
        numeric: true,
        sensitivity: "base"
    });
}


function sortTableData(items, sortState, columns) {
    /*
     * Sort an array using a reusable table sort definition.
     *
     * columns format:
     * {
     *   id: {path: "id", type: "number"},
     *   name: {value: function (row) { return row.name; }, type: "text"}
     * }
     */
    items = Array.isArray(items) ? items.slice() : [];

    if (!sortState || !sortState.column || !columns || !columns[sortState.column]) {
        return items;
    }

    const column = columns[sortState.column];
    const direction = normalizeSortDirection(sortState.direction);
    const type = column.type || "text";

    return items
        .map(function (item, index) {
            return {
                item: item,
                index: index
            };
        })
        .sort(function (left, right) {
            const leftValue = typeof column.value === "function"
                ? column.value(left.item)
                : getSortablePathValue(left.item, column.path || sortState.column);

            const rightValue = typeof column.value === "function"
                ? column.value(right.item)
                : getSortablePathValue(right.item, column.path || sortState.column);

            let result = compareSortableValues(leftValue, rightValue, type);

            if (direction === "desc") {
                result = -result;
            }

            if (result === 0) {
                return left.index - right.index;
            }

            return result;
        })
        .map(function (wrapped) {
            return wrapped.item;
        });
}


function updateSortableTableHeaders(tableSelector, sortState) {
    /*
     * Update sortable table headers after sort state changes.
     */
    const table = $(tableSelector);

    table.find("th[data-sort]").each(function () {
        const header = $(this);
        const column = String(header.data("sort") || "");
        const isSorted = sortState && column === sortState.column;
        const direction = isSorted ? sortState.direction : "";

        header
            .toggleClass("is-sorted", isSorted)
            .toggleClass("is-sorted-asc", isSorted && direction === "asc")
            .toggleClass("is-sorted-desc", isSorted && direction === "desc")
            .attr("aria-sort", isSorted ? (direction === "asc" ? "ascending" : "descending") : "none");

        let indicator = header.find(".sort-indicator");

        if (!indicator.length) {
            indicator = $("<span>")
                .addClass("sort-indicator")
                .attr("aria-hidden", "true");

            header.append(indicator);
        }

        indicator.text(isSorted ? (direction === "asc" ? " ↑" : " ↓") : " ↕");
    });
}


function bindSortableTableHeaders(tableSelector, sortState, columns, onSortChanged) {
    /*
     * Bind click handlers for sortable table headers.
     *
     * This function is generic and can be reused by Alerts, Routes,
     * Channels, Teams, Users and other table pages.
     */
    const headerSelector = tableSelector + " th[data-sort]";

    $(document)
        .off("click.sortableTable", headerSelector)
        .on("click.sortableTable", headerSelector, function () {
            const columnKey = String($(this).data("sort") || "");
            const column = columns[columnKey];

            if (!column) {
                return;
            }

            if (sortState.column === columnKey) {
                sortState.direction = sortState.direction === "asc" ? "desc" : "asc";
            } else {
                sortState.column = columnKey;
                sortState.direction = normalizeSortDirection(column.defaultDirection || "asc");
            }

            updateSortableTableHeaders(tableSelector, sortState);

            if (typeof onSortChanged === "function") {
                onSortChanged(sortState);
            }
        });

    updateSortableTableHeaders(tableSelector, sortState);
}