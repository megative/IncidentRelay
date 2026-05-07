function resetAppDialog() {
    /*
     * Reset global dialog state before showing a new message.
     */
    $("#app-dialog-modal")
        .removeClass("app-dialog-error app-dialog-warning app-dialog-success app-dialog-info");

    $("#app-dialog-title").text("Message");
    $("#app-dialog-subtitle").text("");
    $("#app-dialog-message").text("");
    $("#app-dialog-icon").text("!");

    $("#app-dialog-cancel").show().text("Cancel");
    $("#app-dialog-confirm")
        .removeClass("btn-danger btn-warning btn-success btn-primary")
        .addClass("btn-primary")
        .text("OK");
}


function closeAppDialog() {
    /*
     * Close global dialog.
     */
    $("#app-dialog-modal").addClass("is-hidden");
}


function showAppDialog(options) {
    /*
     * Show global application dialog.
     *
     * Returns:
     *   jQuery Promise resolved on confirm, rejected on cancel/close.
     */
    const deferred = $.Deferred();
    const opts = options || {};
    const type = opts.type || "info";

    resetAppDialog();

    $("#app-dialog-modal")
        .addClass("app-dialog-" + type)
        .removeClass("is-hidden");

    $("#app-dialog-title").text(opts.title || "Message");
    $("#app-dialog-subtitle").text(opts.subtitle || "");
    $("#app-dialog-message").text(opts.message || "");

    $("#app-dialog-icon").text(opts.icon || getAppDialogIcon(type));

    $("#app-dialog-confirm")
        .text(opts.confirmText || "OK")
        .removeClass("btn-primary btn-danger btn-warning btn-success")
        .addClass(opts.confirmClass || getAppDialogButtonClass(type));

    if (opts.cancelText === null || opts.hideCancel) {
        $("#app-dialog-cancel").hide();
    } else {
        $("#app-dialog-cancel").show().text(opts.cancelText || "Cancel");
    }

    $("#app-dialog-confirm").off("click.appDialog").on("click.appDialog", function () {
        closeAppDialog();
        deferred.resolve();
    });

    $("#app-dialog-cancel, #app-dialog-close")
        .off("click.appDialog")
        .on("click.appDialog", function () {
            closeAppDialog();
            deferred.reject();
        });

    return deferred.promise();
}


function getAppDialogIcon(type) {
    /*
     * Return icon text for dialog type.
     */
    if (type === "error") {
        return "!";
    }

    if (type === "warning") {
        return "!";
    }

    if (type === "success") {
        return "✓";
    }

    return "i";
}


function getAppDialogButtonClass(type) {
    /*
     * Return default button class for dialog type.
     */
    if (type === "error") {
        return "btn-danger";
    }

    if (type === "warning") {
        return "btn-warning";
    }

    if (type === "success") {
        return "btn-success";
    }

    return "btn-primary";
}


function showAppSuccess(message, title) {
    /*
     * Show success dialog.
     */
    return showAppDialog({
        type: "success",
        title: title || "Success",
        message: message || "Done",
        confirmText: "OK",
        hideCancel: true
    });
}


function showAppConfirm(options) {
    /*
     * Show confirmation dialog.
     */
    return showAppDialog({
        type: options.type || "warning",
        title: options.title || "Confirm action",
        subtitle: options.subtitle || "",
        message: options.message || "Are you sure?",
        confirmText: options.confirmText || "Confirm",
        cancelText: options.cancelText || "Cancel",
        confirmClass: options.confirmClass || "btn-warning"
    });
}
$(document).on("click", "#app-dialog-modal", function (event) {
    /*
     * Close dialog when clicking outside the modal dialog.
     */
    if (event.target === this) {
        $("#app-dialog-cancel").trigger("click");
    }
});


$(document).on("keydown", function (event) {
    /*
     * Close global dialog by Escape.
     */
    if (event.key !== "Escape") {
        return;
    }

    if (!$("#app-dialog-modal").hasClass("is-hidden")) {
        $("#app-dialog-cancel").trigger("click");
    }
});
