# Other organizer operating systems: experimental porting notes

**NOT TESTED WITH THIS PLATFORM. These are research-based starting points, not a working installer or a supported deployment.** The exercised organizer host remains macOS on Apple Silicon. No Windows, Linux or Intel Mac acceptance run was performed. Documentation reviewed on 23 October 2026; upstream requirements may change.

This applies to the machine running the contest server. Teams using a browser on another OS do not need a server port. A remote administrator can use the approved HTTPS browser path to an existing supported server. PC²/WTI, this Python/Java overlay and the isolated execution service are separate components.

## 1. Understand what must be ported

The following list is based on this repository, rather than a claim from upstream documentation:

- Host discovery and executable paths: `lcpc/runtime_paths.py`, `lcpc/lan_info.py` and `lcpc/workspace_state.py`.
- Host processes, sockets, shutdown and restart: `lcpc/infra/vm.py`, `lcpc/infra/runtime_guard.py`, `lcpc/pc2ctl.py` and managed contest lifecycle.
- Guest architecture/image and bridge/tunnel provisioning: `lcpc/infra/judge-vm.yaml` and Linux judge scripts. Rebuild every architecture-dependent broker/binary for the chosen guest; update the image URL and its verified checksum together.
- LAN discovery, proxy, firewall, TLS and backup tools: `lcpc/infra/network.py`, `lcpc/infra/network_watch.py` and `lcpc/infra/secure_backup.py`. Environment overrides cover only some tools; audit remaining macOS paths.
- PDF fonts and dependencies: `docs/MANUALS.md`. A successful PDF build alone says nothing about judge isolation or scoring correctness.

Preserve separate organizer/guest boundaries and account permissions. An environment-variable change or a successful Java launch does not complete this work. Installing a language runtime must also happen inside the chosen isolated judge.

## 2. Linux organizer host: possible engineering route

Lima documents Linux hosts and a QEMU driver. This suggests a possible replacement for the current macOS VZ backend; it does not validate the existing template on Linux. Read [Lima installation](https://lima-vm.io/docs/installation/) and [VM driver selection](https://lima-vm.io/docs/config/vmtype/).

Start on a separate lab machine with virtualization available. Inventory Java, Python, Node, OpenSSL, proxy and compiler dependencies for that distribution. Select a guest image matching the intended CPU and verify its provenance/checksum. QEMU's [official installation page](https://www.qemu.org/download/) describes distribution packages; package availability is not a finished judge installation.

Port the host adapters and implement explicit service supervision, startup order, private state permissions and clean shutdown. On systemd distributions, service units are a possible supervision mechanism; see [systemd.service](https://www.freedesktop.org/software/systemd/man/latest/systemd.service.html). This repository provides no complete Linux organizer service set. Preserve the dedicated guest and trusted broker; do not replace them with direct student-code execution in the dashboard process.

## 3. Windows organizer host: possible engineering route

An engineer could investigate a Linux VM or WSL2 as a development environment. **Neither route has been tested for this platform.** WSL2 installation is not an isolated-judge security approval. Running a nested judge VM may require virtualization capabilities and additional architecture work.

Microsoft documents WSL installation and version checks. The following PowerShell commands prepare/inspect WSL only; they do not install or start this platform. The install command can require administrator rights and a restart:

```powershell
wsl --install -d Ubuntu
wsl --list --verbose
```

See [Microsoft WSL installation](https://learn.microsoft.com/en-us/windows/wsl/install). Continue with the Linux porting tasks in a separate lab environment, including host adapters, trusted binaries and a genuinely separated execution boundary.

If service supervision is explored inside WSL, review [Microsoft systemd guidance](https://learn.microsoft.com/en-us/windows/wsl/systemd/); enabling systemd does not by itself keep the WSL instance alive or make contest startup/recovery reliable.

LAN access requires its own design. Windows-local browser access does not establish access from team laptops. Review NAT/mirrored networking, Windows/guest firewall rules and intended listeners using [Microsoft WSL networking](https://learn.microsoft.com/en-us/windows/wsl/networking). Do not forward the loopback administrator port to the LAN. Any future forwarding design must preserve trustworthy client identity for IP approvals instead of treating all forwarded clients as local administrators.

## 4. Intel Mac organizer host: possible engineering route

Lima supports multiple CPU/driver combinations, but this overlay currently pins an ARM64 judge profile. Build a separate x86_64 guest profile and matching trusted binaries; verify the chosen macOS/Lima driver requirements rather than merely renaming the ARM64 image. See [Lima VM types](https://lima-vm.io/docs/config/vmtype/) and [Lima architecture support](https://lima-vm.io/docs/).

Review executable locations, available macOS tools and PDF fonts. Measure compilation, execution and timeout behavior on that architecture. Passing on Apple Silicon does not certify Intel timing or capacity.

## 5. Isolation requirements that must survive the port

Ordinary VM examples may share host files automatically. Lima documents configurable host mounts; its defaults are not this platform's security policy. Explicitly review/remove host shares and credentials, and verify the final guest configuration against the intended boundary. See [Lima filesystem mounts](https://lima-vm.io/docs/config/mount/).

Preserve restricted execution users, filesystem/network restrictions, resource limits, output caps, timeout handling, cleanup and private judge data. Review the actual broker, guest kernel features and trust model. WSL, a container, systemd or a VM product name alone does not prove these properties.

## 6. Acceptance before claiming a supported port

Use synthetic accounts/problems and a separate event. Record OS/CPU, dependency versions, guest image hash, adapter changes and test results. At minimum verify startup/shutdown/reboot recovery; account roles/TOTP/IP approval; team login/upload from actual other laptops; accepted/WA/compile/runtime/timeout verdicts; held human review; ties/penalties/freeze/First to Solve; sandbox escape boundaries; PDF/replay exports; and backup restore. Rehearse sustained load and power/network interruption without official contest data.

Publish remaining failures and unsupported workflows with the proposed port. Open a focused pull request with sanitized fixtures and evidence. Until that work is reviewed, the compatibility table in [Installation](INSTALLATION.md) remains unchanged. Original PC² guidance is available from the [official project](https://pc2ccs.github.io/); this porting sketch does not change upstream authorship or license terms.
