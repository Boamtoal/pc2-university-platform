# LCPC OMU Organizer Dashboard

Open **http://127.0.0.1:8091/** on the server computer. The default dashboard binds IPv4 loopback only. Optional remote administration uses a separate HTTPS listener on one explicitly selected private LAN IP, with account-specific IP approvals. It has no route through the participant proxy; changing the participant Wi-Fi profile does not expose dashboard access. A different computer's `127.0.0.1` refers to that different computer.

The interface is English. Participant instructions retain their existing English/Arabic translation. Statements may be English, Arabic or bilingual.

## First sign-in

The initial owner is `admin`. Read its random temporary password from the private state file `admin-dashboard/INITIAL-LOGIN.txt`; do not share it with teams. The dashboard requires a new, unique password of 16–128 characters before any contest data or controls are available. The temporary-password file is deleted after this change. Password changes invalidate all of that user's sessions.

In **My Account**, enable two-step verification with a TOTP authenticator. Re-enter the current password, scan the QR code with your authenticator app, then enter its current six-digit code within five minutes. **Cannot scan?** reveals the manual setup key. Keep the QR code and key private. The QR code is generated locally with the bundled MIT-licensed Project Nayuki encoder; no external authentication or QR service is used.

## Screens and permissions

- **Overview / Submissions:** current attempts and exact PC² verdicts, source file selection and download. Accepted is green, Pending amber, unsuccessful verdicts red. Source reads are audited without logging code.
- **Submission details:** click a submission row, then choose **Details → Test cases** for any accepted or rejected attempt. Green Passed and red Failed reflect PC²’s retained per-case flags; they never substitute for the separate per-case judgement. Amber Not validated means a case record exists without a completed validator flag. The per-test judge verdict is displayed separately (for example Runtime Error). Missing records stay grey, and a pending judgement does not reuse earlier saved test results. PC² can stop on its first failed case. Accepted overall results never fabricate missing individual passes.
- Test-data views distinguish the reference expected answer from retained actual program output. Saved outputs without a reliable test number are labeled by report, never assigned to a test by guessing. Compile/runtime failures are red in report and stream headers; nonempty failure streams open automatically.
- Per-test execution times come from PC². Peak memory is not available in this integration. **View test data** previews the currently stored private input and expected output; it does not claim to reproduce an older problem-data revision. The Source code tab remains available for all attempts.
- **Saved judge reports:** retained compilation/runtime/validator messages, exit codes and timings are shown as saved evidence, which may belong to an earlier judgement after manual changes. The integration does not claim each stdout/stderr file belongs to a particular test when PC² does not retain that association. At most ten saved reports and the first 64 KiB per text file are displayed. Missing and empty files are distinguished. Opening details never executes, submits or rejudges code. These endpoints require dashboard authentication and role checks, with additional IP approval for remote sessions, and are audited without recording input, answers, output or code contents.
- **Teams:** create team accounts, edit display names, login permission and public standings visibility. Team passwords are never displayed in the dashboard or audit log.
- **Problems:** adjust title, active state, time limit (1–10 s), memory limit (32–1024 MiB), and balloon color. **Edit settings** and **Add judged problem** include a color name and color picker. The table shows the assigned color. Colors persist in drafts and native installation; explicit color edits also synchronize existing native balloon delivery maps without enabling email or printing. Existing colors/results remain unchanged until an organizer saves.
- **Add judged problem:** owner only, while the contest is paused. Choose an existing sandbox/validator profile and upload a private ZIP of paired `.in` and `.ans` files. Example: `01.in` with `01.ans`. Up to 250 pairs, 20 MiB compressed, 50 MiB expanded. The problem starts inactive. Check the data and publish statements before activating it. Custom executables/validator uploads are not supported.
- **Resources:** per-problem English/Arabic/bilingual PDF statements and supporting files; separate contest booklets. Uploads are drafts. Publish explicitly. Publishing a new statement supersedes the previous published statement of the same problem, type and language. Earlier versions remain available to organizers. Remove is recoverable through **Removed files → Restore as draft**.
- **Admin Scoreboard:** full PC² standings with freeze ignored for this private view. Public freeze settings remain controlled by the contest configuration. Cells include attempts, pending state and accepted solution time.
- **Clarifications:** reply to questions or prepare announcements. Sending requires explicit confirmation.
- **Judging workflow (owner only, in Judging):** choose Automatic only, Automatic + human approval, or Human only. This changes PC²'s native `computerJudged` / `manualReview` flags for all problems, suppresses preliminary team notifications, and excludes preliminary results from both public and private standings. Pause the clock and finalize pending submissions first. Existing final results are not retracted. New problems inherit their template's workflow. A judge service must already be running for either automatic mode; Human only queues no automatic execution.
- **Human approval:** open **Judging → Pending human review**, or **Submissions → Awaiting human**, and click a submission row. **Accept solution** preselects Accepted; **Reject / choose verdict** preselects Wrong Answer and lets the owner choose the precise rejection reason. **Confirm auto: …** adopts the automatic verdict exactly, including a rejection. Enter a reason and explicitly confirm the final change. The backend verifies that an automatic verdict has not changed before approval, and waits for native server confirmation. Only an owner may finalize decisions in the dashboard; existing native judge permissions remain unchanged. Pending results do not count in either scoreboard.
- **Contest Controls:** start/pause, add time, title, scheduled start and public freeze/thaw. Actions affect the real contest and require typing `CONFIRM`. Dates are displayed in the saved contest time zone (Libya / Africa/Tripoli by default). The scheduled-start editor uses a native calendar/date-time picker, a country selector and a precise regional time-zone selector. Changing country/zone converts the existing instant rather than silently rescheduling it; editing the calendar changes the intended instant. A readable local-time/UTC preview appears before confirmation. The server converts and validates local time using its IANA timezone database, handles fractional-hour offsets and daylight saving, rejects nonexistent local times, and requires an explicit offset for repeated hours. Country/zone preferences persist after a successful save and apply to dashboard timestamps. Clearing the field explicitly removes the scheduled date. Saving the date does not start the clock.
- **Security & Logs:** owner-only users, active sessions, revocation, alerts and audit integrity verification. Viewer is read-only; operator manages contest/resources; owner additionally manages security, manual verdict changes and rejudging. Each user changes their initial password on first sign-in.
- **Review judgement / Rejudge:** owner-only controls in the submission summary dialog. A reason and explicit confirmation are required. These change official results; inspect the resulting attempt after any operation. Do not retry a timeout before checking the actual PC² state.

## Administration tools in their workspace sections

Administration tools appear in their relevant workspace sections, with contextual tabs rather than one global administrator menu. Problems owns colors, full per-problem settings, languages, private tests and saved validation. Teams & Accounts owns native identities, permissions, groups and import. Submissions owns source comparison, organizer submission and submission management. Judging owns workflow, judge clients, verdict definitions and notifications. Scoreboard & Awards owns scoring, medals, delivery and balloon printer/mail services. Contests owns profile metadata, playback and reset. Contest Controls owns time, scheduling and display settings. Exports & Backups owns native reports alongside backup/report packages. System owns sites, connections, external/native runtime status and service logs. Security & Logs owns dashboard identities and the audit trail.

Live native tools are owner-only for the selected active contest. Draft preparation remains in the regular Teams, Problems, Resources and Contest Controls screens. Use **Problems → Edit settings** for a grouped full native problem editor while active; drafts retain their preparation editor. Balloon colors are edited on their problem only. The balloon services screen configures delivery/printing/mail and directs color changes back to Problems. **System → Supported features** maps every capability to its destination and documents runtime limits. See [PC2-ADMINISTRATOR-COVERAGE.md](PC2-ADMINISTRATOR-COVERAGE.md).

Native accounts and permissions are distinct from dashboard identities. The native editor supports account metadata, membership, permissions and write-only credentials; generation/import returns newly created credentials in a private CSV. Runtime service credentials and permissions are protected. Creating a judge account does not launch a judge process. Active compiler configurations must satisfy the deployed isolated Linux policy. Custom configurations can be saved inactive.

Native setting edits require a reason and typed `CONFIRM`; sensitive edits additionally require the current dashboard owner password and TOTP when enabled. Most configuration changes require paused clocks and no unfinished submissions. Record fingerprints reject stale edits. A private test-data replacement never rejudges old attempts automatically. Batch rejudging, organizer submissions, checkout release, time corrections and soft deletion are explicit actions, not side effects of viewing records.

**Export configuration JSON** exports the selected settings domain without passwords. **Import configuration JSON** validates the entire batch in an isolated native model and shows a preview. Commit requires owner reauthentication, rejects changed native state, and consumes the private five-minute plan before sending native operations. Native PC² packets are not a distributed database transaction: a connection failure during commit may leave a partial result. Inspect actual records before preparing a new import. Group membership is exported by name for mapping between contests. Judge datasets are managed separately.

**Native Reports** runs the installed PC² report classes, with team/problem/language/site/group/verdict/state/time filters. All report downloads require owner reauthentication because some native reports include passwords or private settings. Native reports are private text downloads; PDF/CSV and encrypted recovery archives remain in **Exports & Backups**. Reports requiring the desktop's file-export machinery are listed explicitly with that alternative rather than presented as working downloads.

**Contest Playback** imports a bounded ZIP containing native `name=value` event lines separated by `|` and referenced source files. Relative source paths are resolved and constrained to that uploaded dataset before native parsing. Import only parses and stores data. Start requires an empty, paused technical contest and explicit owner confirmation. PC²'s server starts its clocks and creates native replay submissions/judgements. It runs independently of the dashboard; close/sign-out does not stop playback. Stop explicitly through the playback section. Already imported records remain. The installed native server retains its loaded dataset; use a fresh technical contest for a different dataset. The UI displays the last native status received; reload it after operations.

**Reset & Recovery** requires a saved full backup, owner reauthentication, the exact workspace ID, the native contest title, `RESET CONTEST`, a reason and `CONFIRM`. It removes native submissions/clarifications and resets clocks; optional definition removal is separately selected. Use independent contests for new events instead of resetting historical records.

Service-log downloads are limited to known service files and 256 KiB. Known account/site/contest/mail credentials are redacted in the native bridge before return. Source comparison is read-only. Input-validation results, installed Java plugins and Shadow CCS status show saved/native status; they do not launch arbitrary macOS executables or install plugins. The installed desktop Event Feed definition add/update methods themselves are unimplemented; use available native JSON/XML report exports.

Additional isolated tests:

```sh
python3 -B lcpc/admin/tests/test_native_admin.py
node --check lcpc/admin-ui/administrator.js
node --test lcpc/admin/tests/workspace-nav.test.cjs
```

`AdministratorFeaturesTest.java` compiles with the existing bridge libraries and runs in a temporary working directory. It tests native schemas/reports, account permissions, judge policy, notifications, imports, stale/consumed configuration plans, secret redaction and playback parsing/forwarding. Playback fixture controllers never connect to a server or execute source. HTTP fixtures use a fake bridge; no student source is submitted or rejudged.

## Participant diagnostics and client rehearsal

**Teams & Accounts → Participant activity** provides the separate team troubleshooting timeline, browser signals, incidents, request correlation, filters, CSV and integrity checks. **System → Participant test & access → Private test team** provides **Download test account access** (owner password and configured authenticator required) and **Review test submissions**. Each new contest gets its own generated password for reserved participant `team99999`; existing uninitialized drafts receive it without changing official teams. This is a normal participant login using the same isolated judging, clock and approval rules. Its native scoreboard permission is forcibly disabled, its runs are excluded from official dashboard counts/CSV/PDF reports, and balloon delivery is blocked. Diagnostic runs remain visible through **Submissions → Accounts → Test account only**, in private logs, and separately in `test-submissions.csv`; private backup snapshots retain them. The reserved account cannot be edited or imported over through dashboard account tools. Its current password is read from PC² after activation and retained privately on clean deactivation, so a participant-side password change does not leave downloads stale. Archived initialized contests are retained unchanged; they are not silently given new native accounts. The same center can prepare an independent rehearsal draft with fresh access credentials. See [PARTICIPANT-DIAGNOSTICS.md](PARTICIPANT-DIAGNOSTICS.md) for identity guarantees, sources, retention, operational limits and safe rehearsal switching. Browser diagnostics begin on the participant’s next page load; existing sessions are preserved.

## Participant resource access

Signed-in participants use their existing **Problem PDFs** tab. Only published resources linked to active problems are listed and downloadable. English and Arabic statements may coexist. Supporting files always download. Private judge input/output files are never published by the resource manager. Unpublishing also blocks old direct statement aliases, including `/problems/A.pdf`.

Instructions are public before login. Problem pages, the resource catalog and resource downloads require a valid participant session. The standalone instructions and resources pages contain no platform navigation.

Allowed uploads: PDF, TXT, CSV, JSON, ZIP, PNG and JPG. Statements/booklets require PDF. Each file is at most 20 MiB; retained resources have a 1 GiB quota, including removed versions. Archives allow documents/data only and are never executed. Strict new-upload checks reject common active/embedded PDF content; export a plain PDF if rejected. Existing trusted contest PDFs were imported unchanged to preserve the original statements, including their embedded data. These checks are not an antivirus scanner or a proof that arbitrary documents are harmless.

## Start / stop

From the project directory, for the current contest:

```sh
python3 -B lcpc/admin/manage.py start --state .local/instances/lcpc-omu-preparation
python3 -B lcpc/admin/manage.py status --state .local/instances/lcpc-omu-preparation
python3 -B lcpc/admin/manage.py stop --state .local/instances/lcpc-omu-preparation
```

`init` provisions a dedicated PC² service account once and imports existing statement PDFs. Do not run another bridge with the same account concurrently. Native Administrator remains available under its existing separate account. Start PC² before using dashboard controls. Initialization and dashboard startup never start the contest clock.

The state-aware `pc2ctl.py` also supports `dashboard-init`, `dashboard`, `dashboard-status`, `dashboard-stop`. Set `LCPC_STATE_DIR` to the intended instance before using that controller. Normal contest shutdown stops the dashboard first. Encrypted backup includes dashboard state, resources and sources; stop components cleanly before taking a consistent backup. There is no automatic launch at macOS boot.

## Security and logs

The dashboard uses an independent scrypt-hashed password store, hash-only session tokens, HttpOnly/SameSite cookies, same-origin checks, CSRF tokens, role checks, bounded requests, strict CSP and upload/path restrictions. Sessions expire after 30 minutes idle or 8 hours total; closing a browser does not necessarily expire a browser-restored session. Failed sign-ins are throttled for 15 minutes after ten failures from a peer.

`admin-dashboard/audit.jsonl` rotates at 5 MiB with ten retained files. SQLite holds the audit chain, alerts, users and resource metadata. Audit events are chained with HMAC-SHA256 to detect alteration of retained entries. A privileged local attacker who can read the signing key or replace/truncate the whole database can defeat this; this is not an external immutable log. Service logs are `server.log` and `bridge.log`; credentials are redacted from bridge logging.

Private files/directories use 0600/0700 permissions. The PC² service credential remains private on disk because the local integration must authenticate to PC². Avoid shared macOS login accounts. Loopback isolation prevents ordinary LAN access; it does not protect against malware, an untrusted process, or a privileged user already running on this server. No software can promise complete immunity from compromise.

## Verification

```sh
python3 -B lcpc/admin/tests/test_security.py
python3 -B lcpc/admin/tests/test_participant_resources.py
python3 -B lcpc/admin/tests/test_schedule.py
node --test lcpc/admin/tests/schedule.test.cjs
node --test lcpc/admin/tests/run-details.test.cjs
node --check lcpc/admin-ui/app.js
```

The tests use temporary stores, fake PC² data and isolated loopback HTTP servers. They do not submit student code or alter live contest results/time. Native connectivity and source retrieval were checked read-only. The mutating native controls were compiled and reviewed but deliberately not executed against current student submissions or the contest clock during setup.

Native Java fixtures `RunDiagnosticsTest.java` and `JudgingWorkflowTest.java` compile against the existing PC²/WTI libraries. The workflow fixture exercises native RunList transitions and native scoring eligibility for all three modes with accepted/rejected decisions. It also verifies that provisional team/scoring notification switches are disabled. No live contest workflow is changed by these fixtures.

The bundled offline country/zone catalog comes from the installed IANA `zone.tab` and `iso3166.tab`; date conversion uses server `zoneinfo`, not a guessed fixed country offset or a third-party geolocation service. Countries with multiple zones offer a second selector. Refresh the bundled catalog / server timezone database when deploying to environments with newer regional timezone changes.

## Contest workspaces

**Contests → New Contest** creates a private independent draft. Use a unique lowercase ID, a title, duration, wrong-answer penalty and judging workflow. Choose an empty contest or copy the viewed contest's problems and embedded private judge data. Resource copying is optional; copied PDFs and helpers always start unpublished. Teams, passwords, submissions, clarifications, results and old clock progress are never copied. Languages use the existing trusted isolated Linux profiles; arbitrary compiler/validator commands cannot be uploaded through the dashboard.

**Open** selects an organizer workspace without changing participant access. In a draft, use **Teams**, **Problems**, **Resources** and **Contest Controls** to finish preparation. The first problem supports the standard isolated validator with paired `.in`/`.ans` ZIP data. Subsequent draft problems can inherit an existing template profile; copying a whole contest preserves its native validator settings. Draft duration/penalty and the calendar/time-zone editor remain editable before activation. Review problem settings, activate the intended problems and publish the intended resources explicitly.

Exactly **one contest may be active**, including a paused contest. A second activation shows a warning and is rejected with HTTP 409 on the server; denials are audited. Supported CLI server startup also checks actual Java servers and the active reservation, under a process lock. Switching workspaces does not bypass the reservation. Do not run raw Java commands outside the managed lifecycle.

To change the active contest:

1. Open the active workspace, pause its clock, and finalize pending submissions.
2. In **Contests**, choose **Deactivate** and type `CONFIRM`. Participant access, judge, standings exporter and PC² server stop cleanly; submissions and results are retained.
3. Open the prepared workspace and choose **Activate**, then confirm. New contests load a clean PC² database with only their configured teams/problems, use their own service credentials and resource catalog, and start the existing isolated judge and approved participant network profile. Activation keeps the contest clock paused and automatic clock start disabled. Start it explicitly in **Contest Controls**.
4. Archive inactive contests to make them read-only. Unarchive before editing/reactivating. Their last saved native snapshot is available offline for reports; native source/diagnostic retrieval requires activating that contest, while full backups preserve all saved files offline.

An incomplete activation closes participant exposure and keeps the server reserved if native services survived. The dashboard records a failed job and an alert; it never silently switches back or deletes partial state. **Release if stopped** is available for failed reservations only after native services and the isolated judge have actually stopped. A partially installed draft requires recovery; retry never installs over existing submissions/problems. Changing the selected workspace invalidates stale-tab mutations through a required contest ID. The dashboard's original owner identities, sessions and central audit store remain in the original control instance across switches. Continue starting the dashboard against that original state.

## Reports and encrypted backups

Owners use **Exports & Backups** for the selected contest:

- **CSV package**: ZIP of contest settings, teams, problems, submissions, administrator standings, clarifications, languages, resource versions and scoped audit entries, plus the full nested JSON snapshot. No passwords, private input/answer bytes or source code are exported into reports. Spreadsheet formula prefixes are escaped. Historical audit records without a contest ID belong to the original contest.
- **PDF report**: a downloadable, paginated English report. Generation uses the configured Python runtime with ReportLab (`LCPC_PDF_PYTHON` overrides the bundled runtime path). Reports use existing data; they never execute student code or rejudge submissions.
- **Full backup**: deactivate first. A background job produces an AES-256-GCM / RSA-OAEP encrypted archive and SHA-256 manifest, packaged as a ZIP. The archive preserves the selected native contest state and sources, saved judge evidence, private tests, resources, instructions, dashboard data and operation sources. SQLite databases use the backup API; authenticated sessions are removed from their copied databases. Saved backups remain listed after dashboard restart. macOS, Java libraries and the Linux VM are not disk images and must be installed separately.
- **Recovery key**: download separately with owner password reauthentication and TOTP if enabled. The ZIP contains `recipient.key` and `recipient.crt`. Keep it securely off the server and separate from the encrypted archives. Anyone holding the private key can decrypt archives encrypted for it. Key downloads produce an audit event and security alert.

A draft can be backed up too. Source PDFs, helper files and code are preserved in the full archive, not embedded into CSV/PDF reports. Archives and keys are private owner downloads and are never served through the participant proxy.

Restore into a **new** workspace, never over an existing one. Stop the organizer dashboard to prevent catalog races, then run from the project directory:

```sh
python3 -B lcpc/admin/restore_backup.py --archive /absolute/path/contest-backup.zip --key-dir /absolute/path/recovery-key-folder --id restored-event
```

The tool verifies recipient identity, ciphertext hash, authenticated decryption and plaintext hash, rejects unsafe/duplicate tar entries, removes old PIDs, preserves recovered operations/control history under `_recovery/`, and registers the restored workspace offline. It never stops or replaces the currently active contest. Review the restored installation paths, runtime versions and approved LAN profile before activation. On a replacement machine, restore the project/runtime first; start the dashboard with the restored state only when bootstrapping a new control plane. Restored owner credentials come from the backed-up control store, with sessions removed. Keep service credentials private and rotate them according to the recovery procedure.

Additional isolated verification:

```sh
python3 -B lcpc/admin/tests/test_contests.py
python3 -B lcpc/admin/tests/test_contest_http.py
```

These test separate workspaces, paused-active conflicts, stale tabs, read-only archives, resource isolation, CSV injection handling, native lifecycle adapter calls and a real encryption/decryption/restore round trip with a temporary test key. Java `ContestTemplatesTest` uses the native PC² model for clean template import and unstarted clocks, and can parse generated empty CDPs without starting any server. Actual live contest switching is deliberately not exercised against the current event.

### List details and dashboard identity

Data rows and resource/clarification cards open read-only details with a click or Enter/Space. Submission, private-test, participant-activity and connection rows retain their dedicated detail views. Edit controls remain separate buttons; row activation never edits, switches contest workspaces, downloads, revokes access, acknowledges incidents or changes contest state. Nested controls and text selection remain independent, and opening a detail inside a dialog preserves the parent form.

**System → Dashboard identity → Active section indicator** customizes the sidebar’s active-section stripe separately from its background and primary button colors. The same palette provides active-section background, menu hover, row hover and keyboard-focus colors. Text contrast is derived automatically; success/error/warning badges and destructive buttons retain their semantic colors. Changes preview before saving and persist in the shared control database. Existing saved identities inherit the installed yellow indicator; restoring defaults restores that color too. Participant branding is unchanged.

The compact sidebar status below the installation identity shows the active participant server's assigned managed IP and the most recent successful address/snapshot refresh in the selected display time zone. It remains visible while the navigation itself scrolls; selecting a draft does not advertise the draft's stale address. Failed refreshes keep the last observation with an explicit update-failed label.

Problem detail cards show the configured balloon name alongside its actual color swatch. Unassigned colors remain unassigned until explicitly saved through the problem editor; opening details never assigns a color.

### Organized review pages

Sidebar sections use local SVG icons with a consistent stroke and their semantic section meaning. Clicking a submission opens a compact official-verdict/evidence summary. **Details** opens a separate authenticated review tab with Summary, Problem, Test cases, Source code and Judge reports. Clicking a problem opens its metadata summary with its own Details page for resources and owner-only private judge data.

Execution evidence is classified separately from the official judgement. Compile failures take precedence; explicit execution failures/nonzero execution exits remain runtime or the recorded resource-limit outcome. Validator exit 42 is accepted, 43 is a wrong answer; unknown validator failures remain distinct. A stale runtime label cannot override a recorded execution exit of zero. Missing stage evidence stays unknown. Output validation is not a correctness check after an earlier execution failure, and a saved stdout file may be an execution diagnostic rather than student output. No stream is matched to a test case without a recorded association. Review never reruns code or replaces the official judgement.

Review URLs carry the contest ID and refuse private reads after the selected workspace changes. Reads remain authenticated, loopback-only, no-store and audited without recording source or private reference contents. Pending submission pages refresh automatically and preserve scroll positions; final reviews refresh on request. The source viewer retains separate file selection, wrapping and download. Filters stay beside the test list, and selecting a case updates a separate reference/output panel.

### Public and live scoreboards

Scoreboard & Awards has **Live Scoreboard** (private final standings, no freeze) and **Public Scoreboard** (the native freeze-aware export). Both retain native PC² ranks and penalties, show pending attempts, offer a team search beside the table and refresh every five seconds without resetting scroll. The public tab opens the managed LAN `/standings/` display, without organizer navigation or an organizer session. It uses participant branding and offers full screen. Its JSON is produced by `PublicStandings` with `obeyFreeze=true`; it never fetches the private dashboard snapshot. The address is also listed in System → Participant test & access.

The export explicitly removes timing fields from unsolved/pending cells and publishes only standings columns and released aggregate totals. Missing or older-than-30-second exports clear the display and show an error; there is no fallback to full standings. A preliminary-scoring configuration stops publication and blocks the final live view. Final release follows PC² certification plus thaw; viewing either tab never changes freeze, certification, judging or the clock. These live views are available for the active contest; retained offline standings remain in Exports & Backups.

Validation: `node --test lcpc/admin/tests/scoreboards.test.cjs lcpc/branding/tests/scoreboard.test.cjs`, `python3 -B lcpc/admin/tests/test_scoreboards.py` and the isolated Java `ScoreboardReleaseTest` fixture (native freeze, penalties, approval, certified thaw and public-field filtering).

### Participant Identity

System → **Participant identity** controls the selected contest’s public platform/university names, contest subtitle, Instructions headings/subtitles (including optional Arabic values for Instructions), footer text and four logo slots. Each logo has an editable description, upload/reset control, order and placement checkboxes for the main/sign-in header, resource pages and scoreboards. Preview changes before saving. Only an owner may edit; archived contests are read-only. Concurrent edits and a changed selected workspace are rejected. New contests inherit this identity independently of problem/resource copying; later edits stay scoped to that contest. Dashboard Identity remains separate.

PNG/JPEG uploads are limited to 1 MiB per logo, 8192 pixels per side and 32 megapixels. SVG and remote image URLs are rejected. The private contest database stores configuration and image bytes for encrypted backups. Publication writes immutable, hashed local images followed by a public allowlisted manifest at `/assets/lcpc-branding/participant-identity.json`; passwords, tokens, source, private tests and database paths are never in this manifest. Participant pages request only that public manifest and refresh identity within 30 seconds or on window focus. Original supplied/native image files remain unchanged. This does not change the native contest title, schedule, judging, scoreboard freeze or PDF authentication.

### Notification inbox

The bell beside **Local control channel** shows the current owner’s unread count. It collects dashboard security alerts, participant warnings/errors and observed connection-loss/restoration events across contest workspaces. The notification table and per-owner read receipts persist across refreshes/restarts. Deduplicated copies retain the notification history even after the original participant-event retention period. Opening an item marks it read; “Mark all as read” affects only notifications through the currently observed latest ID. Neither action acknowledges a security alert nor resolves a participant incident. Existing incident controls remain in Security & Logs and Participant activity.

Temporary notices retain their existing duration. A five-second inbox poll shows new notices and retains each event in the inbox; old history is not replayed as a popup on sign-in. Connection alerts remain observations: a missing browser signal can also mean a suspended/closed tab. Native PC² connection changes and browser signal changes keep their distinct labels. Inbox queries/read changes require an authenticated owner, local access and CSRF for POSTs. Search, category, unread filtering and pagination are inside the inbox.

Validation: `test_participant_identity.py`, `test_notifications.py`, `test_identity_notifications_http.py`, `participant-identity.test.cjs`, `notifications.test.cjs`, plus the existing identity, navigation, contest-copy/activation and scoreboard tests.

## Server controls and participant result dialogs

**Contest Controls → Server & participant access** has owner-only **Start server** and **Stop server** actions, with job progress. Overview has a Server controls shortcut. These reuse the audited, CSRF-protected contest activation/deactivation flow and the single-active-contest guard. Starting services leaves the clock paused. Stopping requires a paused clock and finalized pending submissions.

A shared final-result dialog is installed in the team app and standalone Instructions, Problem PDFs listing and scoreboard HTML pages. The normal WebSocket result event triggers an immediate authenticated refresh; polling also detects final results when the socket is unavailable or the participant is on a standalone page. Only the current authenticated team's runs are read. The bounded `/api/teams/result-notifications` response excludes private judge evidence and every provisional verdict. Accepted is green; unsuccessful final verdicts are red. Multiple results queue, acknowledgement persists across refresh and pages within the participant session, and foreground tabs coordinate presentation. Rejudgements can produce a new notification. Historic results are not replayed on the first sign-in. All dialog text is English.

The deployment hook is version checked, retains the original extracted bundle and a vendor-alert fallback, and changes the frontend bundle URL to invalidate browser caches. It is installed automatically when a contest server is activated; original ZIP/JAR archives and custom statements remain unchanged. Backend/UI tests use isolated fixtures rather than official submissions.

## Approved remote administrators

From the server computer, open **System → Remote dashboard access**. Create a dedicated account (Operator, Viewer or Owner), approve that exact account and its private IPv4 address for 1–168 hours, and enable HTTPS on a currently assigned server LAN address. The default approval is eight hours. The colleague receives the shown `https://<server-ip>:8092/` link and a temporary password, which must be changed on first sign-in. Only Owner can finalize judgements in this dashboard.

Download the public trust certificate from the same local page and provide its SHA-256 fingerprint through your trusted channel. The colleague must trust that public certificate on their device before signing in. CA/server private keys stay in the private control store and are not downloadable. This does not modify OS trust stores automatically. The optional listener uses TLS 1.2 or later and binds one specific RFC1918 IPv4 address; public addresses, wildcard binds and subnet-wide approvals are rejected. If the server address changes, select its new assigned address locally; there is no automatic broadening of access.

IP approval is checked against the actual TCP peer before TLS handshakes, and the account/IP pair is checked again on every authenticated request. Forwarded headers cannot claim a different peer. Remote sessions have separate Secure/HttpOnly/SameSite=Strict host-only cookies, and are bound to their peer and transport channel. Existing CSRF, host/origin checks, roles, password hashing, first-password-change and configured TOTP controls still apply. Existing local sessions migrate with the local loopback peer/channel.

Only a local owner, after password/TOTP reauthentication and explicit confirmation, may enable/disable access or approve/revoke IPs. Even a remote Owner cannot change these approvals or download trust material. Revocation ends that account's sessions from the selected IP immediately; disabling access closes the HTTPS listener and removes all remote sessions while retaining local access. Expired approvals and disabled accounts lose access without waiting for session expiry.

Blocked peer IPs appear in the local access page and security notification inbox, with bounded/rate-limited attempt logging. Remote API requests are audited with the actual peer IP, method and endpoint, excluding passwords, cookies, codes and request bodies. Grant changes and listener lifecycle events are audited. Remote access defaults to disabled, works independently of contest activation, and does not open the local HTTP control endpoint or the private PC² transport to the LAN.

Validation includes verified TLS over isolated loopback fixtures, matching account/IP approvals, cookie/channel and peer binding, expiry, immediate session revocation, local-only approval management, forwarded-header rejection, CSRF/origin/role checks and listener enable/disable. No real remote account or IP is preapproved.


### Connection alerts, participant colors and recovery (21 October 2026)

Participant connection monitoring now combines tabs for the same team/IP. A browser heartbeat gap becomes actionable after three minutes; closing or navigating a page gets a 90-second grace period, with another active tab preventing a false loss. These are browser observations, not proof of router membership. Native PC² login flips remain diagnostic events without separate owner alerts. A restoration notification is generated only after an unresolved loss was observed. Repeated request failures with the same cause within five minutes update one inbox entry and its occurrence count. Correlated browser/gateway duplicates and expected unauthenticated public Instructions probes are excluded from alerts. Historical derived connection noise is archived and remains available through **Include archived diagnostics**; underlying signed activity is preserved.

**System → Participant identity → Colors** configures ten independent participant presentation colors, with a preview and explicit copy-from-dashboard action. Saving validates readable text contrast. Participant branding does not inherit subsequent dashboard palette changes. Verdicts, destructive actions and problem balloon colors retain their meaning. Asset URLs carry content hashes so updated participant scripts load after restart. Login logos are centered as a group, including when only one logo is enabled.

The dashboard header stays visible while scrolling in every section. **Contest clock** provides a persistent route to clock controls; navigation search locates sections. An inactive workspace displays **Offline** and its retained time instead of claiming an endless reconnection. Starting the dashboard alone never starts the native server or the contest clock.

**Recover server** resumes a failed activation reservation. Installation retains a private stage journal and native completion receipt, upserts exact team identities and reuses verified existing draft problems. Recovery stops only matching public-standings processes before restarting that publisher. It resumes the previously installed dedicated Linux judge VM when stopped; it does not download or create a replacement VM. Recovery refuses incompatible native state or a running clock. A failure before secure bootstrap completes still requires operator inspection; existing initialized profiles are never overwritten. Maintenance shutdown still requires a paused clock and finalized pending submissions; no decision is silently approved or rejected to make shutdown succeed.

Participant refresh retains a valid session during transient backend/network errors and retries with a bounded delay. Confirmed authentication rejection still signs out. Submission retries carrying the same client receipt key replay a retained result rather than forwarding duplicate code; an uncertain receipt instructs the participant to check **My submissions**. This is not automatic source resubmission, and a browser may require file reselection after a full reload.

Deployment remains scoped to the installed macOS Apple Silicon / Lima VZ judge environment. Java/tool locations can be configured with `LCPC_JAVA_HOME`, `LCPC_JAVA_BIN`, `LCPC_BUILD_JAVA_HOME`, `LCPC_LIMA_BIN` and `LCPC_OPENSSL_BIN`; `JAVA_HOME` is also supported. Synthetic regression tests are included in publication rules; operational state, credentials, submissions and private contest material remain excluded. A clean-machine deployment/restore and the intended physical client load still need validation before a university-wide release. Historic diagnostics continue to label current reference data honestly; they do not invent an unavailable historic test revision.


### Team Learning Reports

Open **Exports & Backups → Team Learning Reports**. An owner can prepare a post-contest package after the selected contest finishes or its server is stopped. Generation runs in the background, keeps the clock/results unchanged and publishes a downloadable package only after all team PDFs succeed. Each saved export offers **Download all teams** and individual team ZIPs. Give a team only its own archive.

A team qualifies through retained non-deleted attempts, its own clarifications or verified interactive activity. Passive heartbeats and unverified reported identities do not qualify; the hidden diagnostic team is always excluded. Each team folder contains a detailed PDF, `report.json`, original published question PDFs/support files for attempted problems, current reference code/reasoning, complete current input/answer files, every retained attempt's source, textual comparison and saved compiler/execution/validator streams. The PDF includes difficulty/estimated status, attempt chronology, auto/final verdicts, decision history and available organizer reasons. Every replayed test has an Input block, actual Team output and Expected output, with full files accompanying clearly marked long previews. The numeric case-status table and raw source diff are not used as substitutes for test data. Reference C++ is displayed in a fixed-width font with presentation-only clang-format formatting; original source is retained. Original problem PDFs are appended. Byte-limited previews are marked; full retained files accompany them.

Reference code and explanations can be uploaded in this section as UTF-8 source or Markdown/text, up to 512 KiB per file. References are linked to the stable native problem ID. Existing imported OMU materials are recognized only when their editorial explicitly identifies the current problem letter/title. References are exported as organizer material, not executed or independently certified by export.

The export captures a temporary checksummed copy of the existing local native profile and reads that copy, without starting PC² or signing in as a team. Snapshot changes during capture reject the export instead of mixing evidence. It never resubmits or changes official judgements. Team code is compiled and executed only through the isolated Linux sandbox for a separately labelled post-contest replay. Current test data is explicitly distinguished from unavailable historic revisions; historic saved stdout/stderr has no asserted per-test association. Newly captured replay output is explicitly associated with each current input and kept separate from original decisions. Recommendations use recorded verdict categories and supplied reasoning, not invented diagnoses or a claim that textual code similarity proves correctness. Each team package excludes other teams' sources/questions, passwords, sessions, device addresses and administration databases. The organizer master package contains the independent team folders; exports are private, owner-only, same-origin/CSRF protected, contest-scoped and audited. Learning exports contain deliberately disclosed solutions/tests, so they belong to post-contest team feedback rather than the public participant resource portal.


Downloads in the dashboard and participant resource pages show a spinner during server preparation and actual received-byte percentage when Content-Length is usable. Unknown/compressed lengths show transferred size without a fabricated percentage. Report preparation has a separate completed-work-unit progress bar. Controls prevent duplicate clicks and restore their state after success or error. Completion means the file was handed to the browser; browsers do not expose final disk-save completion. Learning export folders are retained privately under `admin-dashboard/learning-reports/<export-id>/teams/`, alongside the master and individual team ZIPs.
