# Quanta Cloud Administrator Guide

For workspace Owners and Admins. Release 8.x.

## Invite users

Admin console > Users > Invite. Enter one email address per line, choose a role and send. Invitations expire after 7 days.

Members are notified by email of the change.

## Change a user's role

Admin console > Users, open the user and pick Owner, Admin, Member or Guest. A workspace must always have at least one Owner.

Members are notified by email of the change.

## Remove a user

Admin console > Users, open the user and choose Remove. Their content stays in the workspace and is reassigned to the admin who removed them.

Changes are logged in the audit log.

## Set up single sign-on

Admin console > Security > SSO. Upload your identity provider's metadata, test with one account, then enforce SSO for everyone.

Only Owners and Admins see this setting.

## Enforce two-factor authentication

Admin console > Security > Two-factor. Users without two-factor authentication are asked to set it up at their next sign-in.

Changes are logged in the audit log.

## Export workspace data

Admin console > Data > Export. Exports include all content and comments as JSON plus the original files; large exports are split into parts of 10 GB.

This setting applies to the whole workspace.

## Set a retention policy

Admin console > Data > Retention. Choose how long deleted items stay in the trash (7 to 90 days; default 30).

Only Owners and Admins see this setting.

## Connect a calendar

Settings > Integrations > Calendar. Each user connects their own calendar; admins can switch the integration off for the workspace.

This setting applies to the whole workspace.

## Create an API token

Admin console > API > Tokens. Tokens inherit the permissions of the user who created them and can be limited to read-only.

Only Owners and Admins see this setting.

## Review the audit log

Admin console > Security > Audit log. The audit log keeps 90 days of events; with the Advanced audit log add-on it keeps 3 years.

Members are notified by email of the change.

## Restrict guest access

Admin console > Security > Guests. Guests can be limited to the projects they were invited to, or switched off altogether.

Only Owners and Admins see this setting.

## Change the workspace region

Enterprise only. Ask your customer success manager; a region move is scheduled in a maintenance window and takes up to 48 hours.

Members are notified by email of the change.

## Set up a sandbox

Admin console > Workspaces > Sandbox. The sandbox is a copy of your settings without content, for testing automations and integrations.

Only Owners and Admins see this setting.

## Manage billing

Admin console > Billing. Change the plan, the number of seats, the billing period and the invoice email address.

Changes are logged in the audit log.

## Transfer ownership

Admin console > Users, open the new owner and choose Make owner. The previous owner becomes an admin.

Changes are logged in the audit log.

## Delete the workspace

Admin console > Workspace > Delete. Only the Owner can do this. The workspace is recoverable for 30 days.

Members are notified by email of the change.

## Set password rules

Admin console > Security > Passwords. Set a minimum length (at least 12 characters) and whether passwords expire.

Only Owners and Admins see this setting.

## Approve integrations

Admin console > Integrations > Approval. When approval is on, members request an integration and an admin approves it.

Changes are logged in the audit log.

## Archive a project

Open the project > ... > Archive. Archived projects are read-only and do not count towards storage on the Starter plan.

This setting applies to the whole workspace.

## Create custom fields

Admin console > Fields. Business and Enterprise allow up to 200 custom fields per workspace, Team up to 20.

Members are notified by email of the change.

## Configure automations

Project > Automations. Team allows 250 automation runs per month, Business 25,000 and Enterprise unlimited.

Only Owners and Admins see this setting.

## Brand the workspace

Admin console > Workspace > Branding. Upload a logo and choose an accent colour; Business and Enterprise only.

Members are notified by email of the change.

## Getting help

See the Support Policy for response times by plan.