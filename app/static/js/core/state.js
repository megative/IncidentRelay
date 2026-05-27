let currentUser = null;

const routes = {
    "/": { page: "dashboard", title: "Overview", subtitle: "Real-time summary of active incidents, acknowledgements, reminders and affected teams", load: function () { loadDashboard(); } },
    "/alerts": { page: "alerts", title: "Alerts", subtitle: "Search, inspect, acknowledge and resolve routed incidents from one workspace", load: function () { loadAlerts(); } },
    "/rotations": { page: "rotations", title: "Rotations", subtitle: "Manage on-call rotations", load: function () { loadRotations(); } },
    "/calendar": { page: "calendar", title: "Calendar", subtitle: "On-call calendar by team", load: function () { loadCalendar(); } },
    "/routes": { page: "routes", title: "Routes", subtitle: "Connect alert sources, rotations and channels", load: function () { loadRoutes(); } },
    "/escalation-policies": { page: "escalation-policies", title: "Escalation Policies", subtitle: "Define alert escalation chains by team", load: function () { loadEscalationPolicies(); } },
    "/channels": { page: "channels", title: "Channels", subtitle: "Notification channels", load: function () { loadChannels(); } },
    "/silences": { page: "silences", title: "Silences", subtitle: "Mute alerts by matchers", load: function () { loadSilences(); } },
    "/teams": { page: "teams", title: "Teams", subtitle: "Independent duty teams", load: function () { loadTeams(); } },
    "/groups": { page: "groups", title: "Groups", subtitle: "Access boundaries and user roles", load: function () { loadGroups(); } },
    "/profile": { page: "profile", title: "Profile", subtitle: "User profile and personal API token", load: function () { loadProfile(); } },
    "/admin/users": { page: "admin-users", title: "Admin users", subtitle: "Admin-only user workspace", load: function () { loadAdminUsers(); } },
    "/admin/sso": { page: "sso", title: "SSO", subtitle: "OIDC and SAML login providers", load: function () {  loadSsoAdmin(); } },
    "/login": { page: "login", title: "Login", subtitle: "JWT authentication", load: function () { loadLogin(); } }
};
