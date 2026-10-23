# PC² Administrator coverage

Applies to this installed PC² 9.10.0 runtime and the local organizer dashboard. This is a capability map, not a claim of byte-for-byte desktop UI parity. All web administration remains on IPv4 loopback, authenticated and owner-only in their contextual tool tabs. Native PC² enforces its own service-account permissions as well.

| Administrator function | Dashboard support |
| --- | --- |
| Native accounts, account generation, metadata, members, permissions | Teams & Accounts → PC² accounts & permissions / Generate & import. Write-only passwords; new credential CSV. Service accounts protected. |
| Groups/divisions, primary group, scoreboard visibility | Teams & Accounts → Groups & divisions and account editor. |
| Languages, compile/run commands, executable masks, interpreted flags | Problems → Languages. Only deployed isolated Linux profiles can be active. Other profiles may be prepared inactive. |
| Problems, letters, IDs, active state, IO/visibility flags, limits | Problems → Edit settings. Existing sandbox limits remain enforced. New problem definitions with judge data use Problems. |
| Built-in validators, CLICS comparison tolerances, stopping on failure | Problems → Edit settings. Custom executable validators require a trusted deployed runtime. |
| Private test input/answers | Problems → Private judge data; paired ZIP replacement; existing saved diagnostics in Submission details. Replacement does not auto-rejudge. |
| Participant statements and attachments | Resources: English/Arabic PDFs, helpers, booklets, draft/publish/version/recover. Separate from private tests. |
| Judgement definitions | Judging → Verdict definitions. Native Accepted acronym remains protected. |
| Automatic judging and filtering | Judging → Judge clients: enable/filter native judge settings. Separate judge processes must already exist. |
| Automatic/manual/hybrid finalization | Judging plus Submission details. Preliminary results stay private and unscored. |
| Scoring properties, penalty, team display, contest configuration | Scoreboard & Awards → Scoring rules; Contest Controls → Display & advanced settings. |
| Scheduled start/time zone | Contest Controls calendar and country/time-zone selector. |
| Site clocks and all-site start/pause | Contest Controls → Site clocks. Real native time controls, explicit confirmation. |
| Sites, connections, site proxies, native logoff | System → Sites / Connections; Teams & Accounts → account actions. Local server binding and runtime connections protected. Remote sites need configured servers. |
| Runs, elapsed correction, recoverable removal, checkout release | Submissions → Manage submissions. Final verdict review remains in Submission details. |
| Rejudge selected submissions | Submissions → Manage submissions. Explicit owner reauthentication/reason; no background rejudging from settings edits. |
| Submit on behalf of team | Submissions → Submit for a team. Running clock, deployed language and active team/problem required. Creates an official submission. |
| Compare source | Submissions → Compare source, read-only diff of two retained attempts. |
| Clarifications, announcements, categories, deletion/recovery, checkout | Clarifications → Questions & announcements / Manage clarifications / Categories. |
| Final/preliminary notification rules | Judging → Verdict notifications. Preliminary delivery remains suppressed by judging workflow policy. |
| Balloons, colors, SMTP/printer settings, delivery acknowledgements | Scoreboard & Awards → Balloon services / Balloon delivery. Colors belong to Problems → Edit settings. Uses existing native services/drivers; does not install printers or send a test email. |
| Medal thresholds and certification | Scoreboard & Awards → Medals & certification. |
| Native report registry and filters | Exports & Backups → Native reports, owner reauthentication. Text reports supported; desktop file-only exports have a visible alternative. |
| PDF/CSV export and full recovery backup | Exports & Backups; encrypted native state/source/resources archive and separate recovery key. |
| Native per-domain configuration import/export | Configuration JSON with isolated complete-batch validation, preview and one-use stale-state plan. No arbitrary Java serialization upload. |
| Contest profiles | Contests → Profile metadata edits native metadata. Contests manages independent event creation/clone/activation/archive to preserve linked resources, identities and single active event. |
| Playback | Contests → Playback imports native ZIP data, validates contained source references, and forwards start/stop to the native server. Empty technical contest only. PC² starts clocks. No duplicate client replay worker. |
| Native reset | Contests → Reset & recovery with backup, exact identity, typed reset phrase, confirmation and owner reauthentication. Prefer a new contest for a new event. |
| Logs, alerts, access records | System → Service logs and Security & Logs. Bounded/redacted service tails, central audit and role checks. |
| Event feed definitions | Status only. In the installed desktop class `EditEventFeedDefinitionPane`, both add/update methods return without implementing a change. Native JSON/XML report exports remain available. No extra network listener is created. |
| Input validators | Saved native validation results are available. Running arbitrary uploaded custom executables on macOS is outside the deployed isolated judge policy. |
| Shadow CCS | Read-only native state and existing reports. Primary-CCS credentials are hidden; an external CCS connection/credential deployment is not silently provisioned. |
| Java plugins / graphical tools | Installed plugin inventory only. Arbitrary JVM code installation, Swing windows and physical print dialogs require the native desktop/trusted deployment. |
| OS/VM/service deployment | Managed contest lifecycle only. Creating compiler commands, judge accounts, SMTP settings or sites does not install software or launch arbitrary local processes. |

Native write acknowledgements and packet delivery are asynchronous. After a timeout, inspect actual PC² state before retrying. Neither configuration batches nor multi-run actions claim a native atomic transaction. Desktop file-only report exporters are explicitly identified in the registry; encrypted backups preserve recovery data but are not described as native CDP/Resolver exports.

Verification uses isolated native model fixtures and fake-bridge HTTP servers. Production UI review is read-only; current submissions, clock and standings are not modified to exercise these controls.
