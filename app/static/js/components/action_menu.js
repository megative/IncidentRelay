function closeAppActionMenus() {
    $(".app-action-menu.is-open")
        .removeClass("is-open")
        .find(".app-action-menu-toggle")
        .attr("aria-expanded", "false");
}

function isActionMenuItemAllowed(menuObject, item) {
    const options = item || {};

    if (options.hidden) {
        return false;
    }

    if (typeof options.visible === "function" && !options.visible(menuObject, options)) {
        return false;
    }

    if (typeof options.visible !== "undefined" && !options.visible) {
        return false;
    }

    if (typeof options.allowed === "function") {
        return !!options.allowed(menuObject, options);
    }

    if (typeof options.allowed !== "undefined") {
        return !!options.allowed;
    }

    if (options.required) {
        if (typeof canActionObject !== "function") {
            return false;
        }

        return canActionObject(options.object || menuObject, options.required);
    }

    return true;
}

function denyActionMenuItem(item) {
    const message = item.denyMessage || "You do not have permission to perform this action.";

    if (typeof showAppError === "function") {
        showAppError(message, "Access denied");
    }
}

function makeActionMenuItem(menuObject, item) {
    const options = item || {};

    if (!isActionMenuItemAllowed(menuObject, options)) {
        return null;
    }

    const button = $("<button>")
        .attr("type", "button")
        .addClass("app-action-menu-item")
        .toggleClass("is-danger", !!options.danger)
        .toggleClass("is-disabled", !!options.disabled)
        .prop("disabled", !!options.disabled)
        .append(
            $("<span>")
                .addClass("app-action-menu-icon")
                .append(
                    $("<i>")
                        .addClass(options.icon || "fas fa-circle")
                        .attr("aria-hidden", "true")
                )
        )
        .append(
            $("<span>")
                .addClass("app-action-menu-label")
                .text(options.label || "Action")
        );

    if (typeof options.onClick === "function" && !options.disabled) {
        button.on("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            if (!isActionMenuItemAllowed(menuObject, options)) {
                denyActionMenuItem(options);
                return;
            }

            closeAppActionMenus();
            options.onClick(event);
        });
    }

    return button;
}

function makeActionMenu(options) {
    const opts = options || {};
    const menuObject = opts.object || opts.item || null;
    const items = asArray(opts.items);

    const allowedItems = items.filter(function (item) {
        return isActionMenuItemAllowed(menuObject, item);
    });

    const menu = $("<div>").addClass("app-action-menu");

    if (opts.className) {
        menu.addClass(opts.className);
    }

    const toggle = $("<button>")
        .attr("type", "button")
        .attr("aria-haspopup", "true")
        .attr("aria-expanded", "false")
        .attr("title", opts.label || "Actions")
        .attr("aria-label", opts.label || "Actions")
        .addClass("btn btn-small app-action-menu-toggle")
        .prop("disabled", !allowedItems.length)
        .append(
            $("<i>")
                .addClass(opts.icon || "fas fa-ellipsis-v")
                .attr("aria-hidden", "true")
        )
        .on("click", function (event) {
            event.preventDefault();
            event.stopPropagation();

            const isOpen = menu.hasClass("is-open");
            closeAppActionMenus();

            if (!isOpen && allowedItems.length) {
                menu.addClass("is-open");
                toggle.attr("aria-expanded", "true");
            }
        });

    const list = $("<div>").addClass("app-action-menu-list");

    allowedItems.forEach(function (item) {
        const menuItem = makeActionMenuItem(menuObject, item);
        if (menuItem) {
            list.append(menuItem);
        }
    });

    menu.append(toggle).append(list);
    return menu;
}



$(document).on("click.appActionMenu", function () {
    closeAppActionMenus();
});

$(document).on("keydown.appActionMenu", function (event) {
    if (event.key === "Escape") {
        closeAppActionMenus();
    }
});
