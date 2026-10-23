# Version 1: known limitations and contribution roadmap

Status describes this overlay, not the full upstream PC² product. An unchecked feature is not an implied promise or a working control.

| Area | Current boundary | Useful next work |
| --- | --- | --- |
| Organizer hosts | Validated macOS Apple Silicon, Lima VZ ARM64 judge | Isolated Linux organizer deployment, Windows/Intel paths and acceptance tests |
| Installation | Engineer-assisted upstream installation and bridge/VM provisioning | Idempotent installer with version/hash checks and clean-machine CI |
| Recovery | Encrypted contest recovery to a new workspace; not a host/VM disk image | Fresh-machine restore rehearsals and complete disaster recovery procedure |
| Security | Scoped roles, CSRF, audit chains, isolated execution and regression checks | Independent review, dependency vulnerability maintenance, hostile-code audit |
| Capacity | Local checks and event experience | Reproducible load certification at intended team/test counts; storage budgets |
| Historic evidence | Current reference data and retained native records are labelled | Versioned judge datasets and reliable historical per-test stream association |
| Metrics | Available execution timings; no guaranteed peak memory | Trusted peak-memory reporting with correct native associations |
| Languages | Deployed C++17/C++20/Python isolated profiles | Reviewed isolated Java/other-language profiles and replay support |
| Native coverage | Many native tools integrated; selected operations remain read-only | See administrator coverage; preserve upstream behavior rather than inventing controls |
| Event feeds | Upstream installed add/update methods unimplemented | Upstream-compatible implementation and event-stream acceptance testing |
| Shadow/plugins | Saved status/inventory only | Trusted deployment procedures and suitable upstream integration |
| Printers/mail | Depend on external drivers/services | Tested operator setup and delivery verification |
| Network monitoring | Observed browser sessions, not router inventory | Optional consented router integration with clear privacy guarantees |
| PDF/learning export | Detailed current-data replay and complete raw files; large reports costly | Incremental work, quotas/retention UI, cancellation/resume and capacity testing |
| General identity | Configurable primary dashboards and participant identity | Audit remaining default text in native reports and templates for reuse |
| Cloud/multi-tenancy | Private LAN architecture, not Internet-hosting certification | Separate deployment threat model and independent assessment |

Contributions are welcome. Open a sanitized issue or focused pull request. Do not submit real passwords, student code, judge data or local logs. Changes to isolation, credentials, scoring or final judgements require meaningful security/regression review.
