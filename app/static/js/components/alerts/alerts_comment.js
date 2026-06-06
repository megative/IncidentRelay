function loadAlertComments(groupId) {
    const list = $("#alert-comments-list");

    if (!list.length) {
        return;
    }

    list.empty().append(
        $("<div>")
            .addClass("help-text")
            .text("Loading comments...")
    );

    apiGet("/api/alerts/" + groupId + "/comments", function (comments) {
        comments = asArray(comments);
        list.empty();

        if (!comments.length) {
            list.append(
                $("<div>")
                    .addClass("alert-comments-empty")
                    .text("No comments yet.")
            );
            return;
        }

        comments.forEach(function (comment) {
            list.append(renderAlertComment(comment));
        });
    });
}

function renderAlertComment(comment) {
    const user = comment.user || {};
    const author = (
        user.display_name ||
        user.username ||
        user.email ||
        "Unknown user"
    );

    const article = $("<article>")
        .addClass("alert-comment")
        .attr("data-comment-id", comment.id);

    const meta = $("<div>")
        .addClass("alert-comment-meta")
        .append($("<strong>").text(author));

    const timeText = comment.edited
        ? formatDateTimeMinutes(comment.created_at) + " · edited " + formatDateTimeMinutes(comment.updated_at)
        : formatDateTimeMinutes(comment.created_at);

    meta.append($("<span>").text(timeText));

    const body = $("<div>")
        .addClass("alert-comment-body")
        .text(comment.body || "");

    article.append(meta);
    article.append(body);

    if (currentDetailsAlertCanRespond) {
        article.append(renderAlertCommentActions(comment));
    }

    return article;
}
$(document)
    .off("submit.alertComments", "#alert-comment-form")
    .on("submit.alertComments", "#alert-comment-form", function (event) {
        event.preventDefault();

        const form = $(this);
        const groupId = form.attr("data-group-id");
        const textarea = form.find("#alert-comment-body");
        const body = textarea.val() || "";

        if (!groupId) {
            showAppError("Alert group id is missing.");
            return;
        }

        if (!body.trim()) {
            showAppError("Comment cannot be empty.", "Validation error");
            return;
        }

        apiPost(
            "/api/alerts/" + groupId + "/comments",
            {
                body: body
            },
            function () {
                textarea.val("");
                refreshAlertCommentsAndEvents(groupId);
                loadAlerts();
            }
        );
    });
function prepareAlertComments(alert, modal) {
    const form = modal.find("#alert-comment-form");
    const refreshButton = modal.find("#alert-comments-refresh");

    if (!form.length) {
        return;
    }

    form.attr("data-group-id", alert.id);
    form.find("#alert-comment-body").val("");

    refreshButton.attr("data-group-id", alert.id);

    form.toggle(
        currentDetailsAlertCanRespond
        // && normalizeAlertValue(alert.status) !== "resolved"
    );

    loadAlertComments(alert.id);
}
function refreshAlertCommentsAndEvents(groupId) {
    if (!groupId) {
        return;
    }

    loadAlertComments(groupId);

    apiGet("/api/alerts/" + groupId + "/events", function (events) {
        renderEvents(events || [], alertDetailsModal());
    });
}
function renderAlertCommentActions(comment) {
    return $("<div>")
        .addClass("alert-comment-actions")
        .append(
            $("<button>")
                .attr("type", "button")
                .addClass("btn btn-secondary btn-small alert-comment-edit")
                .text("Edit")
        )
        .append(
            $("<button>")
                .attr("type", "button")
                .addClass("btn btn-danger btn-small alert-comment-delete")
                .text("Delete")
        );
}
function startEditAlertComment(article) {
    const body = article.find(".alert-comment-body").first();
    const actions = article.find(".alert-comment-actions").first();
    const currentBody = body.text();

    body
        .addClass("is-editing")
        .empty()
        .append(
            $("<textarea>")
                .addClass("form-control alert-comment-edit-body")
                .attr("rows", "3")
                .attr("maxlength", "5000")
                .val(currentBody)
        );

    actions
        .empty()
        .append(
            $("<button>")
                .attr("type", "button")
                .addClass("btn btn-primary btn-small alert-comment-save")
                .text("Save")
        )
        .append(
            $("<button>")
                .attr("type", "button")
                .addClass("btn btn-secondary btn-small alert-comment-cancel")
                .attr("data-original-body", currentBody)
                .text("Cancel")
        );
}


function cancelEditAlertComment(article) {
    const body = article.find(".alert-comment-body").first();
    const actions = article.find(".alert-comment-actions").first();
    const originalBody = article.find(".alert-comment-cancel").attr("data-original-body") || "";

    body
        .removeClass("is-editing")
        .empty()
        .text(originalBody);

    actions
        .empty()
        .append(
            $("<button>")
                .attr("type", "button")
                .addClass("btn btn-secondary btn-small alert-comment-edit")
                .text("Edit")
        )
        .append(
            $("<button>")
                .attr("type", "button")
                .addClass("btn btn-danger btn-small alert-comment-delete")
                .text("Delete")
        );
}
function confirmDeleteAlertComment(onConfirm) {
    if (typeof showAppDialog === "function") {
        showAppDialog({
            type: "warning",
            title: "Delete comment",
            message: "Delete this comment?",
            confirmText: "Delete",
            cancelText: "Cancel"
        }).done(function () {
            onConfirm();
        });

        return;
    }

    if (window.confirm("Delete this comment?")) {
        onConfirm();
    }
}
$(document)
    .off("click.alertCommentsRefresh", "#alert-comments-refresh")
    .on("click.alertCommentsRefresh", "#alert-comments-refresh", function () {
        const groupId = $(this).attr("data-group-id")
            || $("#alert-comment-form").attr("data-group-id")
            || currentDetailsAlertId;

        loadAlertComments(groupId);
    });


$(document)
    .off("click.alertCommentEdit", ".alert-comment-edit")
    .on("click.alertCommentEdit", ".alert-comment-edit", function () {
        const article = $(this).closest(".alert-comment");
        startEditAlertComment(article);
    });


$(document)
    .off("click.alertCommentCancel", ".alert-comment-cancel")
    .on("click.alertCommentCancel", ".alert-comment-cancel", function () {
        const article = $(this).closest(".alert-comment");
        cancelEditAlertComment(article);
    });


$(document)
    .off("click.alertCommentSave", ".alert-comment-save")
    .on("click.alertCommentSave", ".alert-comment-save", function () {
        const article = $(this).closest(".alert-comment");
        const commentId = article.attr("data-comment-id");
        const groupId = $("#alert-comment-form").attr("data-group-id") || currentDetailsAlertId;
        const textarea = article.find(".alert-comment-edit-body").first();
        const body = textarea.val() || "";

        if (!groupId || !commentId) {
            showAppError("Comment id or alert group id is missing.");
            return;
        }

        if (!body.trim()) {
            showAppError("Comment cannot be empty.", "Validation error");
            return;
        }

        apiPut(
            "/api/alerts/" + groupId + "/comments/" + commentId,
            {
                body: body
            },
            function () {
                refreshAlertCommentsAndEvents(groupId);
            }
        );
    });


$(document)
    .off("click.alertCommentDelete", ".alert-comment-delete")
    .on("click.alertCommentDelete", ".alert-comment-delete", function () {
        const article = $(this).closest(".alert-comment");
        const commentId = article.attr("data-comment-id");
        const groupId = $("#alert-comment-form").attr("data-group-id") || currentDetailsAlertId;

        if (!groupId || !commentId) {
            showAppError("Comment id or alert group id is missing.");
            return;
        }

        confirmDeleteAlertComment(function () {
            apiDelete(
                "/api/alerts/" + groupId + "/comments/" + commentId,
                function () {
                    refreshAlertCommentsAndEvents(groupId);
                }
            );
        });
    });
