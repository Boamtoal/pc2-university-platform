# LCPC OMU standings logos

The two PNGs in `assets/` are exact copies of the organizer's supplied images.
Java and CSS scale them for display without altering the originals.

`StandingsBranding` adds a header to the original PC² Standings and Standings
HTML panes through the existing local Java agent. Existing notices and scoring
components remain present. `pc2ctl.py` supplies the assets path when launching.

`infra.branding.install(state)` copies the assets and standalone CSS/JavaScript
into extracted WTI files. The script inserts a decorative header on the
scoreboard route only. The full ICPC table presents each problem's attempts,
solution time, accepted/pending/unsolved state, and the original server rank
and penalty. A read-only XHR load listener consumes the existing authorized
scoreboard response; it does not read tokens, add API requests, recompute
rankings, or fetch hidden run data. Freeze visibility remains server-controlled.
Authentication, API responses, and vendor ZIP/JARs are unchanged. If no valid
snapshot is available, the original Angular table remains visible.
Problem headers show their letter and the first two title characters; the full
title remains in the hover tooltip. Fixed table columns and wrapped team names
keep the six-problem event within a desktop viewport. Both standings views use
the same incremental DOM updater, preserving the scroll container, team rows,
keyboard focus and ancestor scroll positions across refreshes.
New instances install this automatically; existing instances
can call the same idempotent deployment function. Reload WTI pages afterward.

`header.css` places team identity in its own full-width row beneath the logos
and navigation. Long names wrap across the available header width. The original
Angular team identity and sign-in visibility remain unchanged.
`header.js` retains the header's PC2 and ICPC logos and adds the supplied university
and university contest logos alongside them. White backgrounds on the added logos
keep the blue university artwork visible on the dark header. Original image files
stay intact.
The team identity row displays `TEAM number / display name`. The name is matched
by stable team ID in the existing published standings snapshot, so a ranking
change cannot assign another team's name. Names are inserted as text, and the
row keeps its full-width wrapping layout. No additional PC2 login is performed.

`resources.js` mounts Instructions in the header before and after login, and
Problem PDFs only while signed in. Both open a new tab and use the current
server origin. The installer copies the editable `lcpc/public-problems/` and
`lcpc/public-instructions/` directories outside the public web root. The gateway
serves only the instructions index publicly; PDFs require a valid team session.
Instructions include both university logos and an English/Arabic language switch.
Neither resource page contains navigation to platform sections. Instructions have
only language controls; the problems page retains only PDF viewing and downloading.
Other platform additions remain English.
Signed-in navigation follows the contest workflow: Problem PDFs, Runs,
Clarifications, Scoreboard, Instructions, Options, Logout. DOM order matches
visual and keyboard order; existing route handlers and keyboard focus are retained.
`session.js` retains the current tab's token and team name, validates the session
on refresh and restores the websocket. Passwords are never saved. Version-checked
hooks in `infra/frontend_session.py` integrate this with the extracted WTI bundle;
vendor ZIP/JARs remain unchanged. See `lcpc/PARTICIPANT-RESOURCES.md` for details.

`run-results.js` presents descriptive, colored verdicts in the Runs table,
result popups and judgement filter. Pending and preliminary runs remain pending;
time, memory, compilation and runtime failures retain their specific reasons.
Only rendered text and CSS change. Angular models, option values and server
judgements remain untouched, including the internal Yes/AC representation.
Empty judgement filters retain their normal placeholder instead of displaying
Pending. Selected verdicts and dropdown options use colored text without the
padding or background used by result cells, preserving the Material field layout.

Encrypted backups include this directory and deployed WTI files. To remove
the decoration, omit the `lcpc.branding` Java property and remove the two
`assets/lcpc-branding` tags from extracted WTI `index.html`, then restart the
Admin client and reload the web page.

## Participant workspace styling

`participant-ui.css` is a separate fixed participant theme, visually aligned with the organizer dashboard's default navy, white surfaces, borders, typography and spacing. It preserves the top navigation, four logos and full-width team name. Runs and clarifications use compact filters above their table; sign-in, options, Material selectors, source-upload dialogs, result popups and the standings share the same surfaces and semantic verdict colors. Compilation and runtime errors are red; accepted and pending remain green and amber.

`participant-ui.js` adds authenticated route headings, accessible login labels and table/navigation semantics. It does not send requests, read credentials, change form values, replace Angular controls, alter judging or move focus/scroll. Standalone PDF resources and bilingual instructions use the complete, scoped `resource-pages.css` theme. Their font is Arial with Tahoma for Arabic; original logo files are displayed at their natural proportions on white backgrounds. The public scoreboard keeps its separate `resource-ui.css` theme. Their existing content, authentication and absence of cross-page navigation remain intact. The participant palette is independent of customizable organizer identity settings.

Use `infra.branding.install_participant_ui(state)` for an existing installation. This targeted installer copies the presentation assets and inserts resource stylesheet references without replacing customized HTML, PDFs, catalogs, vendor bundles or session hooks. Full branding installation and contest activation also install this theme. Reload the participant browser tab after deployment. UI files are served locally; no external fonts, analytics or CDN dependencies are introduced.


## Configurable participant identity

The dashboard’s System → Participant identity publishes one allowlisted, contest-scoped public manifest and immutable PNG/JPEG image assets. `participant-identity.js` reads it without sending team credentials, applies text with `textContent`, preserves native Angular elements, and selects configured logos for each surface. It updates the main/sign-in header, Instructions language headings/subtitles and footers, Problem PDFs, both participant/public scoreboard branding and browser titles. It never calls a private organizer API or accepts remote image URLs. `participant-identity.css` contains only logo/caption presentation; semantic verdict colors stay fixed. Identity writes are owner-only and audited, and cloning a contest inherits identity without sharing subsequent changes. Both original PC²/ICPC images and original university assets are retained.
