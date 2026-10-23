# Complete PDF manuals

From **User Guide**, choose **Download English PDF** or **Download Arabic PDF**. Both downloads require a dashboard session, remain available without a native PC² connection and use the shared spinner/received-byte progress indicator.

- [English manual](manuals/University_Contest_Platform_User_Guide_EN.pdf)
- [Arabic manual](manuals/University_Contest_Platform_User_Guide_AR.pdf)

**Organizer-host compatibility:** the current exercised server deployment is **macOS on Apple Silicon**. Windows, Linux and Intel Mac organizer hosts require porting and validation and are not supported installation targets in this overlay release. Team/remote-administrator browsers are clients of that server and may run on other operating systems; rehearse each actual browser and network. Both PDF editions explain this distinction. See the [full compatibility table](INSTALLATION.md#operating-system-compatibility).

The editions contain 24 numbered chapters, a clickable contents page, one connected workspace tree generated from the actual navigation, workflow diagrams, installation instructions, feature support boundaries, operating conditions and original credits. The English interface labels are retained in Arabic instructions so readers can find the matching control. PC²/ICPC and OMU/contest logos retain their owners' rights.

Appendix D gives a **not-tested** Windows/Linux/Intel Mac porting sketch with official links. Its sources are [PORTING.md](PORTING.md) and [PORTING_AR.md](PORTING_AR.md); keep both in sync when updating the books. These are engineering ideas, not tested installation commands for this platform.

The manuals describe version 1.0.0 with documented source revisions through 23 October 2026; use the matching source checkout when following the instructions. A documented control does not install its external service or certify every host and network. Read [Feature availability](SUPPORTED_FEATURES.md) and [Roadmap](ROADMAP.md) before operating an event.

## Rebuild after documentation changes

The English core is `docs/guide.json`; its Arabic counterpart is `docs/guide.ar.json`. Keep chapter IDs and their order aligned. The capability source is `docs/features.json`. Run:

```sh
python3 tools/build-guide.py
python3 -m venv .local/manual-venv
.local/manual-venv/bin/python -m pip install -r docs/manual-requirements.txt
.local/manual-venv/bin/python tools/build-manual-pdfs.py
```

WeasyPrint needs its supported native Pango/font dependencies. This documentation build currently uses Arial/Tahoma fonts installed on the supported macOS host. For another documentation build host, supply licensed fonts with Latin/Arabic coverage and update the CSS font paths in the generator; this is separate from participant language runtime support. No private contest state is needed.

The generator writes final artifacts into `output/pdf/` and copies the same two named manuals into `docs/manuals/` for dashboard downloads and future sanitized source packaging. It uses no browser or external website. Intermediate HTML and manifests go into `tmp/pdfs/`. Never put problem booklets, solutions or team reports in `docs/manuals/`: only the two exact public guide filenames are allowlisted for source packaging.

Verify generated chapters, Arabic fonts, destinations, page geometry and links after rebuilding. A structural check does not replace reader review of typography and usability. Rebuild both editions whenever support limits or workflows change; do not publish stale manuals as current behavior.
