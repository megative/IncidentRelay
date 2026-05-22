# Profile and Personal API Tokens

Open:

```text
Profile
```

The profile page contains user identity, contact fields, active group context and personal API tokens.

## Contact fields

Fill contact fields used by notification channels.

| Field | Used by |
|---|---|
| Email | Email channel |
| Phone | Voice call channel |
| Mattermost user ID | Mattermost action attribution |
| Telegram user ID | Telegram actions |
| Slack user ID | Future or external Slack workflows |

Email and voice call channels send to the assigned user's profile contact data, not to channel-level recipient lists.

## Active group

The active group controls the current group context in the UI and for group-scoped operations.

A normal user sees groups where they have active membership. A global admin can access all active groups according to global admin behavior.

## Personal API tokens

Personal tokens allow API access as the current user.

Recommended practices:

- use short-lived tokens where possible;
- restrict token usage to the needed group when the UI/API supports it;
- rotate tokens after exposure;
- delete unused tokens.
