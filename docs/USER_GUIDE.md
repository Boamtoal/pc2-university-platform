# University Contest Platform — User Guide

Version 1.0.0 · Initial open-source release · [About and credits](../NOTICE.md)

This guide is also available in the dashboard sidebar under **User Guide**. Installation prerequisites are in [INSTALLATION.md](INSTALLATION.md). Read [Feature availability](SUPPORTED_FEATURES.md) for precise status/limits and [PDF manuals](MANUALS.md) for the English/Arabic books.

- [1. Start here: what this platform does](#start)
- [2. Network, router and participant addresses](#network)
- [3. Sign-in, roles and account separation](#roles)
- [4. Optional access for another organizer](#remote)
- [5. Create a contest and keep history separate](#contests)
- [6. Problems, difficulty and balloon colors](#problems)
- [7. Private tests and trusted execution](#judge-data)
- [8. PDF statements, Arabic versions and supporting files](#resources)
- [9. University identity, logos and colors](#identity)
- [10. Official teams, credentials and the private test team](#teams)
- [11. Schedule, start, pause and remaining time](#clock)
- [12. Participant submissions and result dialogs](#submissions)
- [13. Automatic judging and human approval](#review)
- [14. Read source, output and test-case evidence](#details)
- [15. Private live and public frozen scoreboards](#scoreboards)
- [16. Questions and announcements](#clarifications)
- [17. Team activity, connection warnings and notifications](#monitoring)
- [18. CSV, PDF and recovery backups](#exports)
- [19. Detailed post-contest learning packages](#learning)
- [20. Security, privacy and operating conditions](#security)
- [21. Troubleshooting during an event](#troubleshooting)
- [22. Native Administrator coverage and boundaries](#advanced)
- [23. Version 1 limitations and contribution priorities](#limits)
- [24. Before, during and after the contest](#checklist)

<a id="start"></a>

## 1. Start here: what this platform does

**Where:** User Guide → Start here

University Contest Platform v1.0.0 adds an organizer dashboard, participant interface customization and operational tools around PC² 9.10.0 and its Web Team Interface (WTI). PC² remains the contest engine and the authority for native submissions and official judgements.

The dashboard was developed and customized by Boamtoal in the context of programming contests at Omar Al-Mukhtar University (OMU), Libya. It helps organizers prepare and operate contests; it does not replace or claim authorship of PC². Original PC² and WTI credits, logos and license notices must remain intact.

Read Installation before a fresh deployment, then rehearse the entire event on the intended router and team laptops. Version 1 is an initial open-source release. Successful local checks are not certification for every host, university network or contest size.

After the updated interface has loaded, refreshing the browser restores the signed-in dashboard account’s section, contextual tab and available page position. Saved navigation is scoped to that account and revalidated against its current role. Blocked browser storage falls back safely to Overview.

1. Install the supported runtime and isolated judge on a dedicated organizer computer.
2. Create a separate rehearsal contest and test the complete participant journey.
3. Prepare a new official contest with fresh team credentials and reviewed problem data.
4. Take a recoverable backup, verify the clock is paused, and start it explicitly at the intended time.

<a id="network"></a>

## 2. Network, router and participant addresses

**Where:** System → Participant test & access

Use a real router or dedicated access point, preferably with the organizer server wired to it. A phone hotspot can exhaust DHCP leases, disconnect clients or isolate devices. In the original event, moving from the phone hotspot to a router resolved the observed connectivity problem. This is an operational recommendation, not proof that every router is configured correctly.

The organizer and teams must share a reachable local network. Disable access-point/client isolation on the contest LAN and provide enough DHCP leases. Keep the organizer address stable with a router DHCP reservation when possible. Internet access is not required for local contest traffic after dependencies and the judge VM have been installed.

The sidebar shows the detected server IP and last update. Use the exact participant URL from the access center, including scheme and port. The standard LAN entry is http://SERVER-IP:8088/#/login when HTTP has been explicitly enabled. 127.0.0.1 is only the computer that opens it; never send the dashboard loopback URL to teams.

Automatic address detection can update the displayed address and managed listener after a network change. It cannot rewrite a URL already typed on another laptop. Teams must open the new address. A short hostname works only when the network actually resolves it; an IP address is the reliable fallback.

A fully wired Ethernet contest works without Wi-Fi. Connect the organizer and team computers by Ethernet to the same router or switch. A router normally supplies DHCP; a switch alone needs an existing DHCP service or correctly assigned static addresses. A USB-to-Ethernet adapter can provide a port for the organizer laptop. Use the wired interface’s actual address in participant links.

1. Before the event, open the login page on every physical team laptop.
2. If switching networks during an event, pause the contest explicitly first and communicate the interruption.
3. Move the server and every team to the same router, read the new participant address, and have teams reopen it.
4. Verify existing submissions and pending review, then resume the clock explicitly. Do not create a new contest to fix Wi-Fi.

**Limit:** Browser heartbeat monitoring is not a router device inventory or proof of physical network presence. A local rehearsal on the server cannot certify access from other laptops.


<a id="roles"></a>

## 3. Sign-in, roles and account separation

**Where:** My Account; Security & Logs

The private local dashboard is http://127.0.0.1:8091/ on the server itself. A first owner account named admin receives a random temporary password in the selected state folder at admin-dashboard/INITIAL-LOGIN.txt. Read it locally, change it immediately, and keep it away from teams. The temporary file is removed after a successful password change.

Dashboard passwords must contain 16–128 characters. Enable TOTP two-step verification in My Account; the enrollment QR is generated locally. Store the enrollment secret securely. Password changes invalidate that user’s sessions.

Viewer is read-only. Operator can perform permitted contest and resource operations. Owner also controls dashboard security, sensitive native administration, manual verdict decisions and rejudging. Some advanced native tools are owner-only even if a related basic form is available to an operator.

Dashboard users are separate from native PC² teams, judges and service accounts. Creating a dashboard operator does not create a native judge, and creating a judge account does not launch a judge process. Never give a team the organizer credentials or reuse the internal bridge account in the native Administrator.

1. Use an individual named dashboard account for each organizer.
2. Give each person the least privilege needed.
3. Review sessions and revoke access when an organizer leaves.

<a id="remote"></a>

## 4. Optional access for another organizer

**Where:** System → Remote dashboard access

Local-only administration is the default. Optional remote administration uses a separate HTTPS listener on an explicitly selected private LAN address, normally port 8092. A dashboard account and an unexpired account-specific IP approval are both required; approving an address alone does not sign anyone in.

Choose the user, verify the actual source IP, and approve it for a limited period (1–168 hours). Inspect the displayed HTTPS URL and certificate instructions on the remote laptop. DHCP changes can require approval of the new address. Revoke the approval and the user’s sessions when access is no longer needed.

Participant access settings do not expose the organizer dashboard through the team proxy. Do not forward organizer ports on a public router, bypass TLS checks casually, or expose this initial local deployment as a public Internet service.


**Limit:** This release is not a certified public cloud or multi-tenant hosting platform. Account/IP approval complements authentication; it cannot protect a compromised organizer computer.


<a id="contests"></a>

## 5. Create a contest and keep history separate

**Where:** Contests

Use a new contest for a new event. A draft has its own identity, clock settings, accounts, resources and later native state. Select a clear title and short name, unique lowercase ID, duration, penalty and judging workflow. Choose explicitly whether to copy problems and resources from the selected template.

New official team credentials must be generated for the new event. Historical runs are not copied as new attempts. Each new contest has a reserved private diagnostic account. Prepare drafts while another contest is active, but only one native contest server may be active through the managed lifecycle.

Selecting a draft changes the workspace you edit; it does not move participant traffic or start its clock. Activation is a separate operation, and clock start is separate again. A second-active-contest warning prevents concurrent managed activation.

Deactivate only after pausing the clock and resolving unfinished submissions. Activation failures can leave a reserved stage rather than a safely completed deployment. Use Recover server for the matching reservation; a failure before secure bootstrap requires operator inspection. Do not delete journals or overwrite an initialized native profile to force it to work.

1. Create and name the draft.
2. Add official teams, reviewed problem data, statements and the intended schedule.
3. Rehearse on an independent technical contest.
4. Back up the current contest and safely deactivate it if necessary.
5. Activate the new contest, verify service health and keep the clock paused until the event starts.

<a id="problems"></a>

## 6. Problems, difficulty and balloon colors

**Where:** Problems → Problems; Edit settings

A problem has a stable native ID, letter, title, short name, active flag, limits, validator profile, judge data and optional resources. Edit it from its own row. The difficulty column is organizer metadata; an estimated difficulty is labelled as estimated and does not affect scoring.

Balloon color belongs to the problem. Save both the color name and color value; details show the name and swatch. Colors identify problems on scoreboards, with accessible letters/tooltips retained. Balloon service settings control delivery or printing, not problem color.

Adding a judged problem requires an owner and a paused contest. Choose a deployed isolated language/validator profile and upload paired private tests. New problems start inactive; check their limits, data and published statements before enabling them.

The current policy accepts a time limit of 1–10 seconds and memory limit of 32–1024 MiB. A test ZIP may contain up to 250 matching .in/.ans pairs, at most 20 MiB compressed and 50 MiB expanded. Larger datasets require an intentionally reviewed import/deployment path, not bypassing validation.


**Limit:** Changing a title, test set, difficulty or resource does not rejudge older attempts automatically. Current stored tests may differ from those used by a historical submission.


<a id="judge-data"></a>

## 7. Private tests and trusted execution

**Where:** Problems → Private judge data; Judging → Judge clients

Each test pairs an input file with its expected answer, for example 01.in and 01.ans. Review the problem statement, reference solution, limits and validator behavior together. An incorrect expected answer can produce an incorrect automatic decision even when the software runs correctly.

Compilation and execution of untrusted team code belong to the dedicated isolated Linux judge, not the organizer host. The deployed policy uses an isolated Lima VM, no shared host directories, restricted execution, resource limits and a separate broker. Do not enable host compilers for real untrusted submissions.

The currently deployed isolated profiles cover C++17, C++20 and Python. Custom executables, arbitrary compiler/validator uploads, additional languages and host architectures need trusted engineering and independent validation. Saving a custom language inactive does not make it safe or supported.

Private judge inputs, expected answers, reference solutions and organizer source are not participant resource uploads. Keep them private during the contest; post-contest learning exports intentionally disclose selected material.


**Limit:** The isolation implementation has local regression checks, not an independent security certification. No software-only claim eliminates all risk from hostile code or a privileged host attacker.


<a id="resources"></a>

## 8. PDF statements, Arabic versions and supporting files

**Where:** Resources

Attach each file to the correct problem, or choose a contest-wide booklet. Use the resource type and language to distinguish an English statement, Arabic statement, bilingual PDF and supporting material. Statements and booklets must be PDF; supported general attachments include PDF, TXT, CSV, JSON, ZIP, PNG and JPG.

Uploads are drafts until explicitly published. Participants see only published resources linked to active problems after signing in. Publishing a replacement statement supersedes the same problem/type/language version. Earlier versions remain available privately. Unpublishing blocks direct aliases as well as catalog visibility.

A file may be at most 20 MiB. Retained resources have a 1 GiB quota, including removed versions. Removed files can be restored as drafts. Archives are treated as data, never as runnable installers.

New PDF uploads reject common active/embedded features; export a plain PDF if rejected. These checks are not antivirus scanning. Check every intended participant download and language label before the event.

1. Upload reviewed statements and supporting files.
2. Preview metadata and publish deliberately.
3. Sign in as the diagnostic team and verify access.
4. Confirm that a signed-out browser cannot access problem resources.

<a id="identity"></a>

## 9. University identity, logos and colors

**Where:** System → Dashboard identity; Participant identity

Dashboard identity controls the organizer sidebar name, image and identity colors, including active/hover/focus states. Participant identity separately controls the contestant experience, main labels, logos and participant theme. Do not assume one theme automatically follows the other.

Keep readable contrast. Semantic colors for Accepted, Pending, errors, destructive actions and balloon identities are not ordinary branding colors. Changing institutional identity must not make a failed verdict look successful.

The default identity reflects Omar Al-Mukhtar University and its LCPC context. Another university can configure its own identity. Preserve original PC²/WTI attribution and logos in About, bundled notices and upstream interfaces; university customization does not transfer ownership of PC².

Participant pages and new dashboard UI are English. The standalone participant Instructions page is the deliberate English/Arabic exception. A problem statement may independently be Arabic, English or bilingual.


<a id="teams"></a>

## 10. Official teams, credentials and the private test team

**Where:** Teams & Accounts; System → Participant test & access

Create or import team accounts, set display names, login access and public standings visibility. Account permissions are checkboxes in native tools. Credential generation downloads are private; distribute each team only its own login details. Avoid posting credential lists in chat, public repositories or screenshots.

The reserved team99999 is the organizer diagnostic team. It uses the same participant routes, clock restrictions and judging workflow, but is hidden from official standings, official counts and balloon delivery. Its activity is retained separately for diagnosis. Do not edit or overwrite this reserved identity.

An owner can download test access after reauthentication and configured TOTP. Use that login in a separate browser profile or private window, ideally on a second physical laptop. A separate rehearsal contest is safer for full submission experiments before an official event.

The diagnostic account helps reproduce participant behavior; it does not prove every team’s Wi-Fi, browser, firewall or DHCP configuration works. Before the actual contest, have every official device open the intended URL and sign in.


<a id="clock"></a>

## 11. Schedule, start, pause and remaining time

**Where:** Contest Controls → Clock & schedule

Choose a country and IANA time zone, then use the calendar/time picker. Review both the local time and UTC preview. Changing zone converts the same saved instant; editing the calendar changes the intended instant. Saving a schedule or activating a server does not itself press Start.

At the event, explicitly start the contest from Contest Controls. Sensitive actions require a reason or typed CONFIRM where shown. Pause for an operational interruption before changing networks or performing maintenance. Adding time changes the contest duration; verify the remaining clock afterward.

The remaining-time display advances locally from the server sample and becomes red when 15% of the original duration remains. A stale connection is labelled rather than being presented as a trusted fresh clock. Check the server’s actual state before acting on an offline display.

Freeze remaining time is a scoreboard setting, not a pause of judging or of the clock. Stopping services is different from pausing the contest. A browser refresh, opening a report or signing out does not pause the native event.


**Limit:** Rehearse the intended scheduled behavior and time zone on the installed PC² version. Do not infer that saving a date guarantees an unattended event start.


<a id="submissions"></a>

## 12. Participant submissions and result dialogs

**Where:** Submissions

Teams select a problem, supported language and source file in the participant interface. A received attempt stays Pending while queued, executing or waiting for human approval. Final Accepted is green; Wrong Answer, Compilation Error, Runtime Error and other unsuccessful final results are red.

Final result notifications can appear across participant pages. They report the server’s final decision, not a guessed answer from raw yes/no flags. If the connection drops while sending, check My submissions before trying again. An uncertain receipt is not permission to blindly resubmit.

Submission receipts reduce duplicates for retries with the same retained client key; they are not automatic recovery of all browser state. A full reload may require file reselection. Browser download completion means handoff to the browser, not a guarantee that the file was saved to disk.


<a id="review"></a>

## 13. Automatic judging and human approval

**Where:** Judging → Pending human review; Submissions → Awaiting human

Choose Automatic only, Automatic + human approval, or Human only. Change the workflow while paused and after finalizing pending attempts. Automatic modes require a running judge service. Human only queues manual decisions without automatic execution.

In Automatic + human approval, the automatic verdict is provisional. It remains pending for teams and does not count in standings until an authorized owner confirms a final decision. Open a submission row to see its automatic result, source and retained evidence.

Approve result confirms the exact displayed automatic verdict, including Wrong Answer or a runtime/compile failure. A single confirmation shows the attempt, team, problem and final verdict; no typed reason or CONFIRM is required for this pending approval. An automatic reason is retained in the audit log. Choose different verdict opens one selection/confirmation when an override is needed. Reviewing an already final decision or rejudging retains the separate deliberate review flow.

Manual changes and rejudges affect official results and are audited. Check the current record after a timeout before retrying; native PC² operations are not a distributed database transaction. A new judgement can coexist with retained older evidence, which remains labelled separately.

1. Open the pending queue.
2. Read the automatic result, code and relevant saved evidence.
3. Confirm the displayed automatic verdict, or choose a different precise verdict if needed.
4. Confirm once, then verify the final state and participant notification.

<a id="details"></a>

## 14. Read source, output and test-case evidence

**Where:** Click a submission row → Details

Click a row for a concise summary; editing remains an explicit button. The Details action opens an organized page for source, current private tests and retained compiler/execution/validator evidence. Viewing never compiles, submits or rejudges code.

Separate Input, actual Team output and Expected output. A validator’s decision is authoritative for its configured matching rules; a visual whitespace difference alone is not a new judgement. Green Passed and red Failed reflect retained native test flags. Not validated and Missing are distinct states; no test passes are invented.

PC² may stop at the first failed test. Saved stdout/stderr without a reliable case number is shown as an unassigned report; the dashboard does not guess which input produced it. Compile/runtime error headers are red and relevant failure streams open automatically.

At most ten retained native reports and 64 KiB per text preview are displayed in this view. Empty and missing files differ. Per-case execution time is shown when retained; peak memory and historic test-data revisions are not available in this integration.


<a id="scoreboards"></a>

## 15. Private live and public frozen scoreboards

**Where:** Scoreboard & Awards → Live Scoreboard / Public Scoreboard

Live Scoreboard is a private organizer view that ignores the public freeze. Public Scoreboard follows the participant freeze and is the view intended for audience display. Never project the private live screen during a freeze.

Problem columns use assigned balloon colors with letter/name context. Cells reflect native scoring, attempts, pending state and accepted time. Pending human review does not become a solved problem. Color alone is not the only problem identifier.

Configure penalties, scoring, freeze and finalization deliberately. Thawing releases the frozen public results; it is different from ending the clock. Review unresolved judgements and final ranking before releasing or certifying results.

Balloon delivery and award tools depend on the corresponding native configuration. Email, printers and external drivers are deployment prerequisites; enabling a setting does not create working printer/mail infrastructure.

A 1ST crown badge and a darker accepted-green cell identify First to solve for each problem. It uses original elapsed submission milliseconds among final accepted, visible official teams, not the order of human approval. Exact-time ties are shared. Deleted/rejudged results recalculate the marker. The public view reveals only first solves whose accepted cell has been released by the native freeze policy; the marker does not change rank or penalty.

Balloon delivery lists one entry per final accepted team/problem. Click Mark delivered, review the team, problem and balloon color, then Confirm delivery. No typed reason or CONFIRM is needed. Cancel leaves the entry unchanged. Mark pending reverses the acknowledgement through the same simple confirmation. This records delivery status; it does not claim a balloon was physically handed over or that a printer/email service worked.


<a id="clarifications"></a>

## 16. Questions and announcements

**Where:** Clarifications

Teams send clarification requests through the participant interface. Open the relevant row, read the question and choose whether an answer is private or sent to all teams. Review the audience before confirming.

Use announcements for operational notices, corrected statements and remaining-time messages. Do not disclose private tests, credentials or another team’s source. If a resource changes, publish its reviewed replacement and explicitly explain the change to the intended teams.


<a id="monitoring"></a>

## 17. Team activity, connection warnings and notifications

**Where:** Teams & Accounts → Participant activity / Team connections

The activity timeline stores bounded diagnostic metadata, request failures and verified interactions. It does not record passwords, full source files or unrestricted browser content. Reported team identities are distinguished from identities verified by the participant session.

Connection monitoring aggregates browser tabs. A roughly three-minute heartbeat gap or a closed-session grace interval can produce a connection event. A hidden tab, sleeping laptop, network interruption or browser closure may all affect this signal. It is not a scan of the router’s connected devices.

The notification bell near Local control channel retains security alerts, participant incidents and loss/restoration events. Temporary toasts disappear; stored notifications remain for review. Repeated events can be grouped. Read the event’s timestamp and detail before assuming a new incident.

The diagnostic history is bounded (currently 30 days / 200,000 events). Its HMAC chain helps detect alteration within the retained records; a privileged attacker who controls the host and keys can defeat local guarantees. Connection durations are observed browser-session durations, not proof a device continuously stayed on one physical network.

1. Filter the list by team, time and event category near the records.
2. Check whether a failure is isolated or affects several teams.
3. Correlate request errors with router and server health.
4. Export only the necessary private diagnostic data and follow institutional retention rules.

<a id="exports"></a>

## 18. CSV, PDF and recovery backups

**Where:** Exports & Backups

CSV/PDF reports summarize contest information. They are not a restorable backup. Some native reports contain credentials or private settings and require owner reauthentication. Keep all organizer exports private until their contents have been reviewed.

A full encrypted backup includes the retained contest and dashboard material selected by the backup workflow. Take it with the required services cleanly stopped for consistency. Keep the encryption/recovery key separately; losing the key can make recovery impossible.

Restore creates a new workspace rather than silently overwriting the current contest. Test recovery on a separate copy before relying on it for an event. A contest archive is not a complete disk image of macOS, the installed native dependencies or the judge VM.

Downloads show a spinner during preparation and actual received-byte progress when a reliable Content-Length exists. Unknown lengths use an indeterminate indicator and byte count. Do not interpret an estimated server work percentage as final disk-save completion.


<a id="learning"></a>

## 19. Detailed post-contest learning packages

**Where:** Exports & Backups → Team Learning Reports

An owner can prepare learning packages after the contest is finished and paused, or its native server is stopped. Only teams with retained submissions, their own clarifications or verified interactive activity qualify. Passive heartbeats, unverified identities and the hidden diagnostic team are excluded.

Each participating team receives its own folder and ZIP containing a detailed PDF, report.json, retained source, attempted problem statements, organizer reference code/reasoning, and available evidence. The master archive contains all independent team folders; give a team only its own archive.

Upload reference solutions and reasoning as UTF-8 source or Markdown/text (up to 512 KiB per file), linked to the correct stable problem ID. Difficulty and estimated status, attempt counts, chronology, official decisions and available organizer reasons are included. A textual source comparison is not proof of correctness.

A separately labelled isolated replay executes supported team code against current stored tests. Each replayed case has Input, actual Team output and Expected output. Full raw files accompany marked long previews. C++ reference code uses a monospaced presentation; the original source is retained unchanged.

Historical official judgements remain unchanged. Current-data replay is not a reconstruction of an unavailable historic dataset. Saved native output without a reliable test association remains separate from new replay output. Missing evidence and execution failures are explicitly labelled.

Preparation runs in the background with completed-work progress; a downloadable package appears only after all required team PDFs succeed. The local export folder is admin-dashboard/learning-reports/<export-id>/ beneath that contest’s private state.


**Limit:** These archives intentionally contain solutions and private judge data. Release them only after the contest and after checking reuse rights, privacy and future problem reuse. Replay currently supports the deployed C++17/C++20/Python profiles, not arbitrary native languages.


<a id="security"></a>

## 20. Security, privacy and operating conditions

**Where:** Security & Logs

Use the local dashboard on a trusted, updated organizer machine. Keep OS access controlled, use individual strong credentials, enable TOTP, review account-specific remote approvals and protect backups. Do not publish .local, runtime logs, databases, secrets or participant source.

The HTTP team listener is intended only for an explicitly approved private LAN. HTTP does not encrypt credentials or source in transit. Use the supported HTTPS path with correctly trusted certificates where traffic confidentiality is required; a private address alone is not encryption.

Audit events record actions and metadata with chain verification. Browser diagnostics are a separate bounded stream. Inform participants what is collected, who may inspect it, how long it is retained and how feedback archives are shared, following the university’s applicable policies.

Owners must have permission to use problem statements, reference code, logos and student submissions. Code licensing does not grant trademark rights or permission to republish private contest material. Maintain original notices and attribute contributions when redistributing the source.

Version 1 is provided under the repository license without a promise of uninterrupted operation, perfect scoring inputs or complete protection from compromise. The organizer remains responsible for rehearsal, data correctness, final judgements, lawful use and recovery planning.


<a id="troubleshooting"></a>

## 21. Troubleshooting during an event

**Where:** System; Team connections; Security & Logs

Login page does not open: verify the exact scheme, server IP and port, then the same reachable LAN, DHCP lease and router client isolation. A Windows 169.254.x.x address with no gateway usually indicates no usable DHCP lease. Reconnect to the intended router and obtain a valid address; an Internet connection is not required merely to obtain a local DHCP lease.

On the affected Windows laptop, run ipconfig, then ping SERVER-IP and PowerShell Test-NetConnection SERVER-IP -Port 8088 (use the configured port). Ping failure alone is inconclusive because ICMP may be blocked; the TCP port test is more relevant to the web page. Do not assign a random static address without knowing the subnet, gateway and an unused address.

Participant Request failed is an HTTP/network symptom, not automatically a wrong password or wrong solution. Inspect the request/event details and service health. If many teams fail together, check the router, server listener and DHCP before changing account credentials.

Pending submissions: distinguish queued execution from Awaiting human. Check judge health and the human review queue. Never approve results merely to clear a technical blockage. A timeout may follow a successful native operation; inspect the actual record before retrying.

Dashboard reconnecting: verify its selected state and native services. Guide and About remain readable after dashboard sign-in even without a live contest snapshot. A signed-in page can hold stale data; watch its last update and connection banner.

No retained per-test output: inspect available evidence and its labels. Do not invent actual output from an expected answer. Use a post-contest isolated replay if appropriate, clearly distinguished from the original judgement.

Rejected PDF upload: export a plain non-active PDF and retry within limits. Failed PDF export: check the configured Python runtime and reportlab/pypdf dependencies. Download spinner without a percentage can mean the server does not know the response length.


<a id="advanced"></a>

## 22. Native Administrator coverage and boundaries

**Where:** System → Supported features

The dashboard organizes native tools under their relevant sections: problems/languages/tests; accounts/groups/imports; submission management/comparison; judging; scoring/balloons; clocks; profiles/playback/reset; reports; sites/connections. Sensitive tools require an owner, confirmation and sometimes reauthentication.

The native Java Administrator remains available under a separate account and retains its original About/credits. Use the coverage matrix to see supported operations. This dashboard does not claim complete replacement of every Swing dialog, plugin or deployment mode.

The installed upstream Event Feed add/update methods are unimplemented. Use supported native JSON/XML reports instead. Shadow CCS status and Java plugin inventory are read-only here; the dashboard does not install or execute arbitrary plugins.

Playback requires a separate empty technical contest and explicit start. Native playback can start clocks and continues independently of the browser; stop it through its controls. Reset is destructive, requires a full saved backup and exact confirmation, and is not the normal way to prepare a new event.

Bulk native operations may partially complete if a connection fails. Inspect actual state before retrying. Printers, mail, external validators and multi-site native deployments require their own tested setup.


<a id="limits"></a>

## 23. Version 1 limitations and contribution priorities

**Where:** About; GitHub → Issues / Pull requests

The validated organizer deployment is macOS on Apple Silicon with a dedicated Lima VZ ARM64 Linux judge. Native PC² itself supports more systems, but this overlay’s host lifecycle and isolation are not certified on Windows, Linux organizer hosts or Intel Macs.

Team and remote-administrator browser clients are separate from the organizer host. They may access the supported server from Windows, macOS or Linux browsers; rehearse the actual browsers and LAN. A Linux guest judge does not establish Linux organizer-host support, and Java-based PC² does not automatically port this overlay.

There is no one-click, fully validated clean-machine installer. Install the matching upstream PC²/WTI distribution, build the bridge, configure tool paths and provision the isolated judge according to Installation. Clean-machine installation/restore and the intended physical load still require a rehearsal.

Historic dataset revisions, trustworthy per-test association for every retained native output and peak memory measurements are unavailable. Reports label those gaps. Replay and PDF generation can be expensive for many attempts/tests; capacity planning and more incremental export work remain useful improvements.

Independent security auditing, broader OS/architecture support, external-service integration and larger event load certification remain open contribution areas. See ROADMAP for a maintained list. Do not advertise unfinished features as completed.

Everyone may study, use, modify and contribute under EPL-2.0. Open an issue with sanitized reproduction steps, or a pull request with focused changes and relevant tests. Never attach credentials, real student code, private tests or university network inventories to public issues.


<a id="checklist"></a>

## 24. Before, during and after the contest

**Where:** Organizer checklist

Before: rehearse installation and backup recovery; use a router; open the participant page on every laptop; verify accounts, problem limits, validators, statements, reference solutions, colors, time zone, duration, penalty, freeze and human-review staffing. Check the hidden test account and confirm the clock is paused.

During: start explicitly, monitor judge health and pending review, review notifications, answer clarifications, check last-update timestamps and keep private standings off the public display. Pause before a planned network or service interruption.

After: finalize pending decisions, verify rankings and thaw intentionally. Save reports and an encrypted recovery backup. Prepare learning archives only after permission to disclose solutions/tests, distribute per-team archives privately and apply the university’s retention policy.

