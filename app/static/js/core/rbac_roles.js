var GROUP_VIEWER_ROLE = "viewer";
var GROUP_EDITOR_ROLE = "editor";
var GROUP_USER_ADMIN_ROLE = "user_admin";

var GROUP_ROLES = [
  { value: GROUP_VIEWER_ROLE, label: "Group Viewer" },
  { value: GROUP_EDITOR_ROLE, label: "Group Editor" },
  { value: GROUP_USER_ADMIN_ROLE, label: "Group Admin" },
];

var TEAM_VIEWER_ROLE = "viewer";
var TEAM_RESPONDER_ROLE = "responder";
var TEAM_MANAGER_ROLE = "manager";

var TEAM_ROLES = [
  { value: TEAM_VIEWER_ROLE, label: "Team Viewer" },
  { value: TEAM_RESPONDER_ROLE, label: "Team Responder" },
  { value: TEAM_MANAGER_ROLE, label: "Team Manager" },
];

window.RbacRoles = (function () {
  function getValue(value, fallbackValue) {
    return value || fallbackValue;
  }

  function label(roles, value, fallbackValue) {
    const safeRoles = Array.isArray(roles) ? roles : [];
    const selected = getValue(value, fallbackValue);

    const item = safeRoles.find(function (role) {
      return role.value === selected;
    });

    return item ? item.label : selected;
  }

  function fillSelect(selector, roles, selectedValue, fallbackValue) {
    const select = $(selector);
    const safeRoles = Array.isArray(roles) ? roles : [];
    const selected = selectedValue || select.val() || fallbackValue;

    select.empty();

    safeRoles.forEach(function (role) {
      select.append(
        $("<option>")
          .val(role.value)
          .text(role.label)
      );
    });

    if (safeRoles.some(function (role) {
      return role.value === selected;
    })) {
      select.val(selected);
      return;
    }

    if (safeRoles.length) {
      select.val(safeRoles[0].value);
    }
  }

  function groupLabel(role) {
    return label(GROUP_ROLES, role, GROUP_VIEWER_ROLE);
  }

  function teamLabel(role) {
    return label(TEAM_ROLES, role, TEAM_VIEWER_ROLE);
  }

  function groupClass(role) {
    const value = getValue(role, GROUP_VIEWER_ROLE);

    if (value === GROUP_USER_ADMIN_ROLE) {
      return "role-user-admin";
    }

    if (value === GROUP_EDITOR_ROLE) {
      return "role-editor";
    }

    return "role-viewer";
  }

  function teamClass(role) {
    const value = getValue(role, TEAM_VIEWER_ROLE);

    if (value === TEAM_MANAGER_ROLE) {
      return "role-manager";
    }

    if (value === TEAM_RESPONDER_ROLE) {
      return "role-responder";
    }

    return "role-viewer";
  }

  function fillGroupSelect(selector, selectedValue) {
    fillSelect(selector, GROUP_ROLES, selectedValue, GROUP_VIEWER_ROLE);
  }

  function fillTeamSelect(selector, selectedValue) {
    fillSelect(selector, TEAM_ROLES, selectedValue, TEAM_VIEWER_ROLE);
  }

  return {
    label: label,
    fillSelect: fillSelect,

    groupLabel: groupLabel,
    teamLabel: teamLabel,

    groupClass: groupClass,
    teamClass: teamClass,

    fillGroupSelect: fillGroupSelect,
    fillTeamSelect: fillTeamSelect,
  };
})();
function getCurrentUserGroupRole(groupId) {
  /*
   * Return current user's role in a group.
   */
  if (!currentUser || currentUser.is_admin) {
    return currentUser && currentUser.is_admin ? "global_admin" : null;
  }

  const group = asArray(currentUser.groups).find(function (item) {
    return Number(item.id) === Number(groupId);
  });

  return group ? group.role : null;
}

function canEditGroup(groupId) {
  /*
   * Return true when current user can edit objects in a group.
   */
  const role = getCurrentUserGroupRole(groupId);

  return currentUser && (
      currentUser.is_admin ||
      role === "editor" ||
      role === "user_admin"
  );
}

function canManageGroupUsers(groupId) {
  /*
   * Return true when current user can manage users in a group.
   */
  const role = getCurrentUserGroupRole(groupId);

  return currentUser && (
      currentUser.is_admin ||
      role === "user_admin"
  );
}

function canEditTeam(team) {
  /*
   * Return true when current user can edit a team-scoped object.
   */
  if (!currentUser) {
    return false;
  }

  if (currentUser.is_admin) {
    return true;
  }

  if (team && team.group_id && canEditGroup(team.group_id)) {
    return true;
  }

  const teamRole = team && (team.current_user_role || team.user_role || team.role);

  return teamRole === "manager";
}
function getObjectPermissions(item) {
  /*
   * Return normalized permissions object.
   */
  return (item && item.permissions) || {};
}

function canReadObject(item) {
  return !!getObjectPermissions(item).can_read;
}

function canWriteObject(item) {
  return !!getObjectPermissions(item).can_write;
}

function canDeleteObject(item) {
  const permissions = getObjectPermissions(item);

  if (typeof permissions.can_delete !== "undefined") {
    return !!permissions.can_delete;
  }

  return !!permissions.can_write;
}

function canRespondObject(item) {
  return !!getObjectPermissions(item).can_respond;
}

function canManageUsersObject(item) {
  return !!getObjectPermissions(item).can_manage_users;
}
function appendActionIfAllowed(container, item, options) {
  /*
   * Append action button only when object permissions allow it.
   */
  const required = options.required || "write";

  const allowed =
    required === "read" ? canReadObject(item) :
    required === "respond" ? canRespondObject(item) :
    required === "manage_users" ? canManageUsersObject(item) :
    required === "delete" ? canDeleteObject(item) :
    canWriteObject(item);

  if (!allowed) {
    return container;
  }

  container.append(
    $("<button>")
      .attr("type", "button")
      .addClass(options.className || "btn btn-small btn-secondary")
      .text(options.text)
      .on("click", options.onClick)
  );

  return container;
}
