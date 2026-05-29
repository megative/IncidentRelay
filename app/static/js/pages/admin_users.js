let adminUsersCache = [];

function isCurrentAdminUser(user) {
  /*
   * Return true when this row represents the authenticated user.
   */
  return !!(user && user.is_current_user);
}

function normalizeGroupRole(role) {
  if (role === "read_only") {
    return GROUP_VIEWER_ROLE;
  }
  if (role === "rw") {
    return GROUP_EDITOR_ROLE;
  }
  return role || GROUP_VIEWER_ROLE;
}

function loadAdminUsers() {
  /*
   * Load admin users page.
   */
  fillAdminUserRoleSelect();
  fillAdminUserGroupSelect();
  refreshAdminUsers();
}

function refreshAdminUsers() {
  /*
   * Refresh admin user table.
   */
  apiGet("/api/admin/users", function (users) {
    adminUsersCache = asArray(users);
    renderAdminUsersSummary(adminUsersCache);
    renderAdminUsersTable(getFilteredAdminUsers());
  });
}

function renderAdminUsersSummary(users) {
  /*
   * Render summary cards for the admin users page.
   */
  const activeUsers = users.filter(function (user) {
    return !!user.active;
  });
  const adminUsers = users.filter(function (user) {
    return !!user.is_admin;
  });
  $("#admin-users-total-count").text(users.length);
  $("#admin-users-active-count").text(activeUsers.length);
  $("#admin-users-inactive-count").text(users.length - activeUsers.length);
  $("#admin-users-admin-count").text(adminUsers.length);
}

function getFilteredAdminUsers() {
  /*
   * Return users filtered by search input.
   */
  const query = ($("#admin-users-search").val() || "").trim().toLowerCase();
  if (!query) {
    return adminUsersCache;
  }
  return adminUsersCache.filter(function (user) {
    return [
      user.id,
      user.username,
      user.display_name,
      user.email,
      user.phone,
      user.telegram_user_id,
      user.slack_user_id,
      user.mattermost_user_id,
    ].join(" ").toLowerCase().indexOf(query) !== -1;
  });
}

function renderAdminUsersTable(users) {
  /*
   * Render users table.
   */
  const tbody = $("#admin-users-table");
  tbody.empty();
  if (!users.length) {
    tbody.append(
      $("<tr>").append(
        $("<td>")
          .attr("colspan", "7")
          .text("No users")
      )
    );
    return;
  }
  users.forEach(function (user) {
    tbody.append(renderAdminUserRow(user));
  });
}

function renderAdminUserRow(user) {
  /*
   * Render one admin user row.
   */
  const row = $("<tr>").toggleClass("row-disabled", !user.active);
  row.append($("<td>").text(user.id));
  row.append(
    $("<td>")
      .append(
        $("<button>")
          .attr("type", "button")
          .addClass("name-button")
          .text(user.display_name || user.username || ("User #" + user.id))
          .on("click", function () {
            openExistingAdminUserModal(user);
          })
      )
      .append(
        $("<div>")
          .addClass("details-meta")
          .text("@" + (user.username || "-"))
      )
  );
  row.append($("<td>").append(renderAdminUserContacts(user)));
  row.append($("<td>").append(renderAdminUserMessengers(user)));
  row.append(
    $("<td>").append(
      $("<span>")
        .addClass(user.is_admin ? "role-editor" : "role-viewer")
        .text(user.is_admin ? "Admin" : "User")
    )
  );
  row.append(
    $("<td>").append(
      $("<span>")
        .addClass("status-pill")
        .addClass(user.active ? "status-active" : "status-inactive")
        .text(user.active ? "Active" : "Inactive")
    )
  );
  row.append(
    $("<td>")
      .append(renderAdminUserActions(user))
  );
  return row;
}

function renderAdminUserContacts(user) {
  /*
   * Render user contact information.
   */
  const box = $("<div>").addClass("details-compact-list");
  box.append($("<div>").text(user.email || "No email"));
  box.append(
    $("<div>")
      .addClass("details-meta")
      .text(user.phone || "No phone")
  );
  return box;
}

function renderAdminUserMessengers(user) {
  /*
   * Render messenger identifiers.
   */
  const box = $("<div>").addClass("details-compact-list");
  box.append($("<div>").text("Telegram: " + (user.telegram_user_id || "-")));
  box.append(
    $("<div>")
      .addClass("details-meta")
      .text("Slack: " + (user.slack_user_id || "-"))
  );
  box.append(
    $("<div>")
      .addClass("details-meta")
      .text("Mattermost: " + (user.mattermost_user_id || "-"))
  );
  return box;
}

function renderAdminUserActions(user) {
  /*
   * Render user row actions as a shared three-dots menu.
   */
  const isSelf = isCurrentAdminUser(user);
  const isGlobalAdmin = !!(currentUser && currentUser.is_admin);

  const items = [
    {
      label: "Edit",
      icon: "fas fa-edit",
      visible: function () {
        return typeof hasGroupUserAdminAccess === "function"
            ? hasGroupUserAdminAccess()
            : isGlobalAdmin;
      },
      onClick: function () {
        openExistingAdminUserModal(user);
      }
    },
    {
      label: user.active ? "Disable" : "Enable",
      icon: user.active ? "fas fa-pause" : "fas fa-play",
      danger: user.active,
      visible: function () {
        return isGlobalAdmin && !isSelf;
      },
      onClick: function () {
        setAdminUserActive(user, !user.active);
      }
    },
    {
      label: "Remove",
      icon: "fas fa-trash",
      danger: true,
      visible: function () {
        return isGlobalAdmin && !isSelf;
      },
      onClick: function () {
        removeAdminUser(user);
      }
    }
  ];

  const menu = makeActionMenu({
    object: user,
    items: items
  });

  if (isSelf && isGlobalAdmin) {
    const wrapper = $("<div>").addClass("table-actions");
    wrapper.append(menu);
    wrapper.append(
        $("<span>")
            .addClass("details-meta")
            .text("Current user")
    );
    return wrapper;
  }

  return menu;
}

function openNewAdminUserModal() {
  /*
   * Open modal for a new user.
   */
  resetAdminUserForm();
  fillAdminUserRoleSelect();
  setAdminUserGroupControlsEnabled(true);
  applyAdminUserFormPermissions(null);
  $("#admin-user-modal-title").text("New user");
  $("#admin-user-modal-subtitle").text("Create local user account.");
  $("#admin-user-password").attr("placeholder", "Password");
  applyAdminUserRoleFieldAccess(null);
  openAppModal("#admin-user-modal");
}

function openExistingAdminUserModal(user) {
  /*
   * Open modal for an existing user.
   */
  fillAdminUserForm(user);
  setAdminUserGroupControlsEnabled(true);
  $("#admin-user-modal-title").text("User details");
  $("#admin-user-modal-subtitle").text(user.display_name || user.username || ("User #" + user.id));
  $("#admin-user-password").attr("placeholder", "Leave empty to keep current password");
  applyAdminUserSelfProtection(user);
  applyAdminUserFormPermissions(user);
  applyAdminUserRoleFieldAccess(user);
  openAppModal("#admin-user-modal");
}

function collectAdminUserPayload() {
  /*
   * Build user payload.
   */
  const payload = {
    username: $("#admin-user-username").val().trim(),
    display_name: $("#admin-user-display").val().trim() || null,
    email: $("#admin-user-email").val().trim() || null,
    phone: $("#admin-user-phone").val().trim() || null,
    telegram_user_id: $("#admin-user-telegram").val().trim() || null,
    slack_user_id: $("#admin-user-slack").val().trim() || null,
    mattermost_user_id: $("#admin-user-mattermost").val().trim() || null,
    password: $("#admin-user-password").val() || null,
    is_admin: $("#admin-user-is-admin").is(":checked"),
    active: $("#admin-user-active").is(":checked"),
  };
  const groupId = $("#admin-user-group").val();
  payload.group_id = groupId ? Number(groupId) : null;
  if (groupId) {
    payload.group_role = $("#admin-user-group-role").val() || GROUP_VIEWER_ROLE;
  }
  return payload;
}

function validateAdminUserPayload(data, isCreate) {
  /*
   * Validate user form before sending it to the API.
   */
  if (!data.username) {
    showAppError("Username is required");
    return false;
  }
  if (isCreate && !data.password) {
    showAppError("Password is required for a new user");
    return false;
  }
  return true;
}

function saveAdminUser() {
  /*
   * Create or update an admin user.
   */
  const id = $("#admin-user-id").val();
  const data = collectAdminUserPayload();
  const isCreate = !id;
  if (!validateAdminUserPayload(data, isCreate)) {
    return;
  }
  if (id) {
    apiPut("/api/admin/users/" + id, data, function () {
      resetAdminUserForm();
      closeAppModal("#admin-user-modal");
      refreshAdminUsers();
    });
    return;
  }
  apiPost("/api/admin/users", data, function () {
    resetAdminUserForm();
    closeAppModal("#admin-user-modal");
    refreshAdminUsers();
  });
}

function fillAdminUserForm(user) {
  /*
   * Load user data into the form.
   */
  $("#admin-user-id").val(user.id);
  $("#admin-user-username").val(user.username || "");
  $("#admin-user-display").val(user.display_name || "");
  $("#admin-user-email").val(user.email || "");
  $("#admin-user-phone").val(user.phone || "");
  $("#admin-user-telegram").val(user.telegram_user_id || "");
  $("#admin-user-slack").val(user.slack_user_id || "");
  $("#admin-user-mattermost").val(user.mattermost_user_id || "");
  $("#admin-user-password").val("");
  $("#admin-user-is-admin").prop("checked", !!user.is_admin);
  $("#admin-user-active").prop("checked", !!user.active);

  const activeGroupId = getAdminUserActiveGroupId(user);
  $("#admin-user-group").val(activeGroupId ? String(activeGroupId) : "");
  fillAdminUserRoleSelect(getAdminUserGroupRole(user, activeGroupId));
}

function getAdminUserActiveGroupId(user) {
  /*
   * Return the group shown in the Users page editor.
   */
  if (user && user.active_group_id) {
    return user.active_group_id;
  }
  const groups = asArray(user && user.groups);
  return groups.length ? groups[0].group_id : null;
}

function getAdminUserGroupRole(user, groupId) {
  /*
   * Return the role for the selected group.
   */
  const normalizedGroupId = groupId ? Number(groupId) : null;
  const groups = asArray(user && user.groups);
  for (let index = 0; index < groups.length; index += 1) {
    if (Number(groups[index].group_id) === normalizedGroupId) {
      return normalizeGroupRole(groups[index].role);
    }
  }
  return normalizeGroupRole(user && user.active_group_role);
}

function applyAdminUserSelfProtection(user) {
  /*
   * The current user cannot disable or remove their own account.
   */
  const isSelf = isCurrentAdminUser(user);
  $("#admin-user-active").prop("disabled", isSelf);
  $("#admin-user-active-help").text(
    isSelf
      ? "You cannot disable your own account. Ask another global administrator to do it."
      : ""
  );
}

function setAdminUserActive(user, active) {
  /*
   * Enable or disable user through the update endpoint.
   */
  if (isCurrentAdminUser(user) && !active) {
    showAppError("You cannot disable your own account.");
    return;
  }

  const action = active ? "enable" : "disable";
  const btnClass = active ? "btn-success" : "btn-warning";
  showAppConfirm({
    title: "Are you sure?",
    message: "Are you sure you want to " + action + " this user?",
    confirmText: upperCaseFirst(action),
    confirmClass: btnClass,
  }).done(function () {
    apiPut(
      "/api/admin/users/" + user.id,
      {
        username: user.username,
        display_name: user.display_name || null,
        email: user.email || null,
        phone: user.phone || null,
        telegram_user_id: user.telegram_user_id || null,
        slack_user_id: user.slack_user_id || null,
        mattermost_user_id: user.mattermost_user_id || null,
        password: null,
        is_admin: !!user.is_admin,
        active: active,
      },
      function () {
        refreshAdminUsers();
      }
    );
  });
}

function resetAdminUserForm() {
  /*
   * Reset admin user form.
   */
  $("#admin-user-id").val("");
  $("#admin-user-username").val("");
  $("#admin-user-display").val("");
  $("#admin-user-email").val("");
  $("#admin-user-phone").val("");
  $("#admin-user-telegram").val("");
  $("#admin-user-slack").val("");
  $("#admin-user-mattermost").val("");
  $("#admin-user-password").val("");
  $("#admin-user-is-admin").prop("checked", false);
  $("#admin-user-active").prop("checked", true).prop("disabled", false);
  applyAdminUserRoleFieldAccess(null);
  $("#admin-user-active-help").text("");
  $("#admin-user-group").val("");
  fillAdminUserRoleSelect();
  setAdminUserGroupControlsEnabled(true);
}

$(document).on("click", "#reload-admin-users", refreshAdminUsers);
$(document).on("input", "#admin-users-search", function () {
  renderAdminUsersTable(getFilteredAdminUsers());
});
$(document).on("click", "#new-admin-user", openNewAdminUserModal);
$(document).on("click", "#admin-save-user", saveAdminUser);
$(document).on("click", "#admin-reset-user-form", resetAdminUserForm);
$(document).on("click", "#close-admin-user-modal, #close-admin-user-modal-footer", closeAppModal);

function removeAdminUser(user) {
  /*
   * Soft-delete a user from the admin workspace.
   */
  if (isCurrentAdminUser(user)) {
    showAppError("You cannot remove your own account.");
    return;
  }

  const message = [
    "Remove user \"" + (user.username || user.id) + "\"?",
    "",
    "This will revoke personal API tokens and remove the user from groups,",
    "teams, rotations and overrides.",
    "",
    "Historical alerts will be preserved.",
    "",
    "Continue?",
  ].join("\n");
  showAppConfirm({
    title: "Remove user?",
    message: message,
    confirmText: "Remove user",
    confirmClass: "btn-danger",
  }).done(function () {
    apiDelete("/api/admin/users/" + user.id, function () {
      resetAdminUserForm();
      closeAppModal("#admin-user-modal");
      refreshAdminUsers();
    });
  });
}

function fillAdminUserGroupSelect() {
  apiGet("/api/groups", function (groups) {
    const select = $("#admin-user-group");

    select.empty();
    select.append(
        $("<option>")
            .val("")
            .text("Do not add to group")
    );

    asArray(groups).forEach(function (group) {
      if (!canManageGroupId(group.id)) {
        return;
      }

      select.append(
          $("<option>")
              .val(group.id)
              .text("#" + group.id + " " + group.name + " (" + group.slug + ")")
      );
    });
  });
}

function fillAdminUserRoleSelect(selectedValue) {
  if (isGlobalAdminUser()) {
    RbacRoles.fillGroupSelect("#admin-user-group-role", selectedValue);
    return;
  }

  RbacRoles.fillSelect(
      "#admin-user-group-role",
      GROUP_ROLES.filter(function (role) {
        return role.value !== GROUP_USER_ADMIN_ROLE;
      }),
      selectedValue,
      GROUP_VIEWER_ROLE
  );
}

function setAdminUserGroupControlsEnabled(enabled) {
  /*
   * Enable group selection only for new user creation.
   */
  $("#admin-user-group").prop("disabled", !enabled);
  $("#admin-user-group-role").prop("disabled", !enabled);
  $("#admin-user-group-help").text(
    enabled
      ? "Global admins can assign or update this user's default group and role. Removing extra memberships is managed on the Groups page."
      : "Group controls are disabled."
  );
}

function canManageGroupId(groupId) {
    if (isGlobalAdminUser()) {
        return true;
    }

    return asArray(currentUser && currentUser.groups).some(function (group) {
        return (
            Number(group.group_id || group.id) === Number(groupId)
            && group.role === GROUP_USER_ADMIN_ROLE
        );
    });
}
function applyAdminUserFormPermissions(user) {
    const isGlobal = isGlobalAdminUser();
    const isSelf = !!(user && isCurrentAdminUser(user));

    $("#admin-user-is-admin")
        .prop("disabled", !isGlobal)
        .closest("label, .md-checkbox")
        .toggle(isGlobal);

    $("#admin-user-active")
        .prop("disabled", !isGlobal || isSelf);

    if (!isGlobal) {
        $("#admin-user-is-admin").prop("checked", false);
        $("#admin-user-active-help").text(
            "Group admins cannot globally enable or disable user accounts. Use group membership status on the Groups page."
        );
        return;
    }

    $("#admin-user-active-help").text(
        isSelf
            ? "You cannot disable your own account. Ask another global administrator to do it."
            : ""
    );
}
function applyAdminUserRoleFieldAccess(user) {
    /*
     * Group user admins can edit user profile data, but cannot assign
     * global admin role or globally enable/disable users.
     */
    const isGlobalAdmin = !!(currentUser && currentUser.is_admin);
    const isSelf = isCurrentAdminUser(user);

    $("#admin-user-is-admin").prop("disabled", !isGlobalAdmin);
    $("#admin-user-active").prop("disabled", !isGlobalAdmin || isSelf);

    if (!isGlobalAdmin) {
        $("#admin-user-is-admin").prop("checked", false);
        $("#admin-user-active-help").text(
            "Only global administrators can change global admin flag or global active status."
        );
        return;
    }

    $("#admin-user-active-help").text(
        isSelf
            ? "You cannot disable your own account. Ask another global administrator to do it."
            : ""
    );
}
