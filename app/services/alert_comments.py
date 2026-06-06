from __future__ import annotations

from app.modules.db import alerts_repo

MAX_COMMENT_LENGTH = 5000


def normalize_comment_body(body: str | None) -> str:
    body = (body or "").strip()

    if not body:
        raise ValueError("comment body is required")

    if len(body) > MAX_COMMENT_LENGTH:
        raise ValueError(f"comment body is too long, max {MAX_COMMENT_LENGTH} characters")

    return body


def create_group_comment(
    *,
    group_id: int,
    body: str | None,
    user_id: int | None = None,
):
    group = alerts_repo.get_alert_group(group_id)
    if not group:
        raise LookupError("alert group not found")

    body = normalize_comment_body(body)

    comment = alerts_repo.create_alert_comment(
        group_id=group.id,
        user_id=user_id,
        body=body,
    )

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="commented",
        message=body,
        user_id=user_id,
    )

    return comment


def create_child_alert_comment(
    *,
    group_id: int,
    alert_id: int,
    body: str | None,
    user_id: int | None = None,
):
    group = alerts_repo.get_alert_group(group_id)
    if not group:
        raise LookupError("alert group not found")

    alert = alerts_repo.get_alert(alert_id)
    if not alert or alert.group_id != group.id:
        raise LookupError("alert not found in this group")

    body = normalize_comment_body(body)

    comment = alerts_repo.create_alert_comment(
        group_id=group.id,
        alert_id=alert.id,
        user_id=user_id,
        body=body,
    )

    alerts_repo.create_alert_event(
        group_id=group.id,
        alert_id=alert.id,
        event_type="commented",
        message=body,
        user_id=user_id,
    )

    return comment


def get_group_comment_or_raise(*, group_id: int, comment_id: int):
    comment = alerts_repo.get_alert_comment(comment_id)

    if not comment or comment.deleted:
        raise LookupError("comment not found")

    if comment.group_id != group_id:
        raise LookupError("comment not found in this alert group")

    return comment


def update_group_comment(
    *,
    group_id: int,
    comment_id: int,
    body: str | None,
    user_id: int | None = None,
):
    group = alerts_repo.get_alert_group(group_id)
    if not group:
        raise LookupError("alert group not found")

    get_group_comment_or_raise(
        group_id=group.id,
        comment_id=comment_id,
    )

    body = normalize_comment_body(body)

    comment = alerts_repo.update_alert_comment(
        comment_id,
        body=body,
    )

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="comment_updated",
        message=body,
        user_id=user_id,
    )

    return comment


def delete_group_comment(
    *,
    group_id: int,
    comment_id: int,
    user_id: int | None = None,
):
    group = alerts_repo.get_alert_group(group_id)
    if not group:
        raise LookupError("alert group not found")

    comment = get_group_comment_or_raise(
        group_id=group.id,
        comment_id=comment_id,
    )

    deleted = alerts_repo.soft_delete_alert_comment(comment.id)
    if not deleted:
        raise LookupError("comment not found")

    alerts_repo.create_alert_event(
        group_id=group.id,
        event_type="comment_deleted",
        message="Comment deleted",
        user_id=user_id,
    )

    return comment
