# Main Concepts

IncidentRelay is built from a small set of concepts:

| Concept           | Description                                                                    |
|-------------------|--------------------------------------------------------------------------------|
| Group             | Access boundary and group-level administration scope                           |
| User              | Person who can log in, be on-call, receive notifications or use personal API tokens |
| Team              | Operational unit inside a group                                                |
| Rotation          | On-call schedule for a team                                                    |
| Route             | Incoming alert routing rule with its own intake token                          |
| Escalation policy | Escalation policy                                                                               |
| Channel           | Outgoing notification destination                                              |
| Alert             | Alert created or updated by an incoming integration                            |
| Silence           | Temporary rule that suppresses notifications for matching new alerts           |
| Override          | Temporary replacement in a rotation                                            |

Recommended reading order:

1. [Groups and RBAC](groups-and-rbac.md)
2. [Teams, Rotations and Routes](teams-rotations-routes.md)
3. [Route Intake Tokens](route-intake-tokens.md)
4. [Channels](channels.md)
5. [Reminders and Escalations](reminders-and-escalations.md)
6. [Escalation policy](escalation-policies.md)
