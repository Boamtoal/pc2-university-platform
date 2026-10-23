# Architecture and trust boundaries

## Components

- `lcpc/admin-ui/`: static English organizer interface. Guide content is generated from `docs/guide.json` and requires no external service or live contest snapshot.
- `lcpc/admin/`: Python HTTP service, local SQLite metadata, authorization, resource lifecycle, audit chain, contests, backup/report and learning workflows.
- `lcpc/src/`: Java bridge, native record/query/operation adapters and execution guards. Compiled against the separately installed PC²/WTI jars.
- `lcpc/branding/`: participant overlay assets, English/Arabic instructions support, identity and precise result/clock presentation. Original upstream bundles/credits remain separate.
- `lcpc/infra/`: participant proxy, diagnostics, managed networking, service lifecycle and isolated judge coordination.
- `lcpc/infra/linux/`: trusted Linux sandbox broker, compiler profiles and replay. No organizer host directory mounts are requested by the VM configuration.
- `lcpc/public-{instructions,problems,standings}/`: standalone templates. Do not confuse the problem portal shell with actual private problem PDFs.
- `.local/`: private installation/runtime state, never source-control material. Each managed contest owns a separate instance beneath it.

PC² is authoritative for official attempts, judgements and scoring. The dashboard stores resource metadata, access policy, branding, difficulty and diagnostics. Pending human review is kept distinct from final native results. Reports label retained historical evidence versus replay against current data.

## Default listeners

| Listener | Default | Intended exposure |
| --- | --- | --- |
| Native PC² | 127.0.0.1:50002 | Local bridge and private judge tunnel |
| Native WTI | 127.0.0.1:8080 | Behind the participant proxy |
| Participant gateway internals | loopback:8090 | Internal only |
| Participant entry | selected LAN IP:8088 | Explicit private LAN HTTP or configured HTTPS path |
| Dashboard | 127.0.0.1:8091 | Organizer server only |
| Optional remote dashboard | approved LAN IP:8092, HTTPS | Enabled separately, user authentication plus expiring IP approval |

Read actual access-center URLs rather than assuming every installation uses these defaults. A private LAN is not encrypted by definition. Hostnames require actual DNS/mDNS support. Port forwarding is not part of the supported public deployment.

## Data boundaries

- Participant login is required for published problem catalogs/downloads. Instructions are deliberately public; private tests and administrative APIs are not.
- Team activity is bounded diagnostic metadata, not unrestricted browsing surveillance. Reported and verified identities remain separate.
- Source and judge data enter the Linux sandbox through the trusted broker. Do not run team code in the organizer's Python process or host compiler.
- Exporting current test output does not alter official results. Historical streams without a reliable test number remain unassigned.
- Per-team learning archives exclude other teams; the organizer master archive contains all team packages and must remain private.
- Local audit chains depend on local keys. They do not defeat an attacker who already controls the organizer host.

## Operations and failures

Draft preparation, server activation and clock start are distinct. One managed native contest can be active at a time. Native multi-operation commits can partially complete across a connection failure; inspect actual state before retrying. Recovery journals are deliberate safeguards, not disposable cache. Backups require the documented consistency conditions and restore into new workspaces.

## Licensing

The overlay is EPL-2.0. Upstream PC²/WTI and external dependencies retain their rights; Nayuki's included QR encoder remains MIT. Identity assets have separate trademark/permission constraints. See [NOTICE](../NOTICE.md).
