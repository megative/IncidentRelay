from datetime import datetime

from app.db import database_proxy as db
from app.modules.db.models import (
    AlertRoute,
    ApiToken,
    Group,
    NotificationChannel,
    Rotation,
    Silence,
    Team,
    TeamUser,
    User,
    UserGroup,
)


def list_groups(active_only=False, include_deleted=False):
    """
    Return groups ordered by id.
    """

    query = Group.select().order_by(Group.id.asc())

    if not include_deleted:
        query = query.where(Group.deleted == False)

    if active_only:
        query = query.where(Group.active == True)

    return list(query)


def list_groups_for_user(user, write_required=False):
    """
    Return active groups visible to a user.
    """

    if user and user.is_admin:
        return list_groups(active_only=True)

    if not user:
        return []

    query = (
        UserGroup
        .select(UserGroup)
        .join(Group)
        .where(
            (UserGroup.user == user.id)
            & (UserGroup.active == True)
            & (Group.active == True)
            & (Group.deleted == False)
        )
        .order_by(UserGroup.id.asc())
    )

    if write_required:
        query = query.where(UserGroup.role == "rw")

    return [membership.group for membership in query]


def get_group(group_id, include_deleted=False):
    """
    Return a group by id.
    """

    query = Group.select().where(Group.id == group_id)

    if not include_deleted:
        query = query.where(Group.deleted == False)

    return query.get()


def create_group(slug, name, description=None):
    """
    Create a group.
    """

    return Group.create(slug=slug, name=name, description=description)


def update_group(group_id, data):
    """
    Update a group.
    """

    group = get_group(group_id)

    for field in ["slug", "name", "description", "active"]:
        if field in data:
            setattr(group, field, data[field])

    group.save()
    return group


def add_user_to_group(user_id, group_id, role="read_only"):
    """
    Add a user to a group.
    """

    membership, created = UserGroup.get_or_create(
        user=user_id,
        group=group_id,
        defaults={"role": role},
    )

    if not created:
        membership.role = role
        membership.active = True
        membership.save()

    return membership


def list_user_groups(user_id):
    """
    Return active group memberships for a user.
    """

    return list(
        UserGroup
        .select(UserGroup)
        .join(Group)
        .where(
            (UserGroup.user == user_id)
            & (Group.active == True)
            & (Group.deleted == False)
        )
        .order_by(UserGroup.id.asc())
    )


def get_user_group_role(user_id, group_id):
    """
    Return the role a user has in an active group.
    """

    membership = (
        UserGroup
        .select(UserGroup)
        .join(Group)
        .where(
            (UserGroup.user == user_id)
            & (UserGroup.group == group_id)
            & (UserGroup.active == True)
            & (Group.active == True)
            & (Group.deleted == False)
        )
        .first()
    )

    return membership.role if membership else None


def get_group_membership(membership_id):
    """
    Return a group membership by id.
    """

    return UserGroup.get_by_id(membership_id)


def update_group_membership(membership_id, role, active=True):
    """
    Update a group membership.
    """

    membership = get_group_membership(membership_id)
    membership.role = role
    membership.active = active
    membership.save()
    return membership


def disable_group_membership(membership_id):
    """
    Disable a group membership.
    """

    membership = get_group_membership(membership_id)
    membership.active = False
    membership.save()
    return membership


def soft_delete_group(group_id):
    """
    Soft-delete a group and disable all resources under it.

    The operation is intentionally soft-delete based:
    - historical alerts and audit logs stay readable;
    - teams/routes/rotations/channels/silences are disabled;
    - users are not deleted;
    - group memberships are disabled.
    """
    now = datetime.utcnow()

    with db.atomic():
        group = get_group(group_id)

        group.deleted = True
        group.deleted_at = now
        group.active = False
        group.save()

        team_ids = [
            team.id
            for team in (
                Team
                .select(Team.id)
                .where(
                    (Team.group == group_id)
                    & (Team.deleted == False)
                )
            )
        ]

        Team.update(
            deleted=True,
            deleted_at=now,
            active=False,
        ).where(
            (Team.group == group_id)
            & (Team.deleted == False)
        ).execute()

        UserGroup.update(
            active=False,
        ).where(
            UserGroup.group == group_id
        ).execute()

        User.update(
            active_group=None,
        ).where(
            User.active_group == group_id
        ).execute()

        if team_ids:
            Rotation.update(
                deleted=True,
                deleted_at=now,
                enabled=False,
            ).where(
                (Rotation.team.in_(team_ids))
                & (Rotation.deleted == False)
            ).execute()

            AlertRoute.update(
                deleted=True,
                deleted_at=now,
                enabled=False,
            ).where(
                (AlertRoute.team.in_(team_ids))
                & (AlertRoute.deleted == False)
            ).execute()

            NotificationChannel.update(
                deleted=True,
                deleted_at=now,
                enabled=False,
            ).where(
                (NotificationChannel.team.in_(team_ids))
                & (NotificationChannel.deleted == False)
            ).execute()

            Silence.update(
                deleted=True,
                deleted_at=now,
                enabled=False,
            ).where(
                (Silence.team.in_(team_ids))
                & (Silence.deleted == False)
            ).execute()

            TeamUser.update(
                active=False,
            ).where(
                TeamUser.team.in_(team_ids)
            ).execute()

            ApiToken.update(
                deleted=True,
                deleted_at=now,
                active=False,
            ).where(
                (
                    (ApiToken.team.in_(team_ids))
                    | (ApiToken.group == group_id)
                )
                & (ApiToken.deleted == False)
            ).execute()
        else:
            ApiToken.update(
                deleted=True,
                deleted_at=now,
                active=False,
            ).where(
                (ApiToken.group == group_id)
                & (ApiToken.deleted == False)
            ).execute()

        NotificationChannel.update(
            deleted=True,
            deleted_at=now,
            enabled=False,
        ).where(
            (NotificationChannel.group == group_id)
            & (NotificationChannel.deleted == False)
        ).execute()

    return group


def delete_group_membership(membership_id: int) -> dict:
    """
    Permanently remove user from group, all group teams and all group rotations.
    """
    membership = get_group_membership(membership_id)

    group_id = membership.group.id
    user_id = membership.user.id

    with db.atomic():
        team_ids_query = (
            Team
            .select(Team.id)
            .where(Team.group == group_id)
        )

        rotation_ids_query = (
            Rotation
            .select(Rotation.id)
            .where(Rotation.team.in_(team_ids_query))
        )

        RotationMember.delete().where(
            (RotationMember.user == user_id) &
            (RotationMember.rotation.in_(rotation_ids_query))
        ).execute()

        RotationOverride.delete().where(
            (RotationOverride.user == user_id) &
            (RotationOverride.rotation.in_(rotation_ids_query))
        ).execute()

        TeamUser.delete().where(
            (TeamUser.user == user_id) &
            (TeamUser.team.in_(team_ids_query))
        ).execute()

        membership.delete_instance()

    return {
        "id": membership_id,
        "group_id": group_id,
        "user_id": user_id,
    }
