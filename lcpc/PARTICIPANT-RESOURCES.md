# University participant resources

**Instructions** appears in the header even before login. **Problem PDFs** appears
in the main navigation only while signed in. Both open a new tab and use the
current server address. Instructions alone support English and Arabic; all other
added interface text remains English.

Resource files live outside the public WTI web directory. The participant
gateway serves the instructions index publicly and validates the team session
before serving the problem page or any PDF. An unauthenticated request to those
protected files redirects to team login. Login creates a
session-only HttpOnly cookie; logout clears it. No password is saved.

## Customization

- Instructions: edit both language sections in `lcpc/public-instructions/index.html` to change the university identity and instructions. Both university logos are displayed. This standalone page has no platform navigation links, whether signed in or not.
- Problems page: edit `lcpc/public-problems/index.html` to update problem titles and file links. Keep only PDF viewing and downloading actions; do not add platform navigation.
- PDFs: replace files in `lcpc/public-problems/`, including `booklet.pdf`, when preparing another contest.
- Logos: `lcpc/branding/assets/omu-logo.png` and `lcpc-logo.png`.
- Navigation labels and placement: `lcpc/branding/resources.js`; appearance: `resources.css`.

The starter instructions explain the interface. Add the committee's approved
schedule, permitted languages and event-specific rules before another event.

## Deployment

From the project directory:

```sh
python3 -B - <<'PY'
import sys
from pathlib import Path
sys.path.insert(0, 'lcpc')
from infra.branding import install
install(Path('.local/instances/lcpc-omu-preparation'))
PY
```

Refresh the browser afterward. Content updates need no contest restart.
New instances also copy these sources; replace the problem set and instructions
before giving participants access. The network profile must include the
participant gateway resource routes from `lcpc/infra/network.py`.

## Refreshing the team dashboard

`session.js` retains the session token and team name in the current tab's
`sessionStorage`. It never retains the password. After refresh, the gateway
validates the token before the dashboard and result websocket resume. Logout
and invalid sessions clear saved state. Changing the origin (for example, from
an IP address to a hostname) uses a different browser storage area.

`infra/frontend_session.py` installs narrowly matched hooks in the extracted
WTI JavaScript bundle and refuses an unfamiliar version. Vendor ZIP/JAR files
remain intact. The first reload after installation requires one login because
older pages did not save their session state.
