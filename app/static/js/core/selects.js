function selectedTeamId() { return $("#global-team-filter").val(); }
function selectedTeamQuery() { const teamId = selectedTeamId(); return teamId ? "?team_id=" + encodeURIComponent(teamId) : ""; }

function fillGroupSelect(selector, includeAll, callback) {
    /* Fill a select element with groups ordered by id. */
    apiGet("/api/groups", function (groups) {
        const select = $(selector); select.empty();
        if (includeAll) { select.append($("<option>").val("").text("All groups")); }
        groups = asArray(groups);
        groups.forEach(function (group) { select.append($("<option>").val(group.id).text("#" + group.id + " " + group.name + " (" + group.slug + ")")); });
        if (typeof callback === "function") { callback(groups); }
    });
}

function fillTeamSelect(selector, includeAll, callback) {
    /* Fill a select element with teams ordered by id. */
    apiGet("/api/teams", function (teams) {
        const select = $(selector); select.empty();
        if (includeAll) { select.append($("<option>").val("").text("All teams")); }
        teams = asArray(teams);
        teams.forEach(function (team) { select.append($("<option>").val(team.id).text("#" + team.id + " " + team.name + " (" + team.slug + ")")); });
        if (typeof callback === "function") { callback(teams); }
    });
}

function fillUserSelect(selector, callback, url) {
    /* Fill a select element with users ordered by id. */
    apiGet(url || "/api/users", function (users) {
        const select = $(selector); select.empty();
        users = asArray(users);
        users.forEach(function (user) { select.append($("<option>").val(user.id).text("#" + user.id + " " + user.username)); });
        if (typeof callback === "function") { callback(users); }
    });
}

function fillActiveGroupSelect() {
    /* Fill the active group selector in the topbar. */
    const select = $("#active-group-select");
    select.empty();
    select.append($("<option>").val("").text("All my groups"));

    if (!currentUser || !currentUser.groups) {
        return;
    }

    currentUser.groups.forEach(function (membership) {
        select.append(
            $("<option>")
                .val(membership.group_id)
                .text(membership.group_name + " (" + membership.role + ")")
        );
    });

    if (currentUser.active_group_id) {
        select.val(String(currentUser.active_group_id));
    }
}
