# Security policy

Version 1 is an initial local-network deployment, not a security certification. The maintained baseline is PC² 9.10.0 / WTI 1.1 with the documented macOS/Lima isolated judge. Review dependency updates and validate compatibility before each event.

## Report privately

For a suspected credential leak, authentication bypass, sandbox escape, private-data disclosure or audit bypass, use this repository's **Security → Report a vulnerability** private reporting feature. Include affected version, sanitized reproduction steps, expected/actual behavior and impact. Do not publish an exploit containing real credentials, team code, private tests, tokens or network inventories. If private reporting is unavailable, contact the maintainer through the contact channels on [Boamtoal's GitHub profile](https://github.com/Boamtoal) and request a private channel before sending sensitive details.

General non-sensitive bugs may use Issues. There is no promised response-time SLA. Until a fix is available, preserve evidence privately and disable the affected optional exposure; do not silently alter contest results.

## Deployment responsibilities

- Keep the dashboard loopback-only unless approved remote HTTPS access is required; use individual accounts, strong passwords and TOTP.
- Approve remote IPs per user with expiration and revoke sessions/approvals after use.
- Use a trusted router, enough DHCP leases and reachable team devices. Never treat a hotspot failure as a wrong team password without checking the network.
- Keep native services local and team execution isolated. No host mounts and no host execution for untrusted submissions.
- HTTP participant access is plaintext and requires an explicitly approved private-LAN risk decision. Use the supported HTTPS configuration where confidentiality is needed.
- Protect `.local`, backups, recovery keys, source/evidence and learning exports. Never commit operational state.
- Inform teams about diagnostic collection/retention and follow institutional requirements. Browser presence is not a network inventory.
- Perform a full rehearsal, clean recovery test and intended-client load check. Keep final judgement authority with authorized organizers.

## Public source hygiene

`tools/package-source.py` builds an explicit source allowlist and rejects unexpected files, symlinks and selected private-data/secret indicators. It is a publication aid, not proof that arbitrary future source cannot contain a secret. Review the manifest and diff before every push. Use synthetic fixtures; never copy real submissions to tests. Keep original copyright/license and upstream About notices intact.
