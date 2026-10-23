# Installation and first rehearsal

This is a **source overlay**, not a self-contained replacement distribution of PC². The procedure below is for an experienced organizer on the documented host. It has not been validated as a one-click clean-machine installer. Do a complete rehearsal and recovery test before scheduling a real event.

## Supported baseline

- Dedicated **macOS Apple Silicon** organizer host with enough RAM/storage for Java, PDF generation and a **4 GiB RAM / 20 GiB disk** Lima VZ Linux ARM64 judge. Keep at least 8 GiB free host storage; large learning exports need significantly more space.
- Matching official **PC² 9.10.0 build 7065** distribution, including `lib/pc2.jar`, its dependency jars and `projects/WebTeamInterface-1.1-7065.zip`. Obtain it from [official PC² distribution information](https://pc2ccs.github.io/). Verify the distribution's provenance/checksum and preserve its original licenses, manuals and About credits.
- Java capable of building with `--release 17` (Java 17 is the bridge build baseline). The deployed native runtime also uses `-Djdk.crypto.KeyAgreement.legacyKDF=true` for its storage compatibility. New JDK/upstream combinations need independent validation.
- Python **3.11+**, an isolated virtual environment with [PDF requirements](../lcpc/admin/requirements.txt), Node **20+** for JavaScript tests, Lima, OpenSSL supporting CMS AES-GCM, Caddy, and macOS command-line tools (`xcrun`, `lsof`, `ssh`).
- Optional `clang-format` for presentation-only C++ formatting in learning PDFs. Original source remains intact if presentation formatting is unavailable.
- A real router/dedicated AP, enough DHCP leases, no team-client isolation and preferably a wired organizer host. Initial dependency/VM downloads require Internet; local event traffic afterward does not.

The bundled VM template pins a specific Ubuntu ARM64 image and SHA-256. If it is unavailable, review and deliberately update **both** URL and digest; do not disable image verification. Guest package repositories require access during initial provisioning.

## 1. Install the source overlay beside the native distribution

Work in a **fresh copy** of the official PC² installation. Keep any existing event installation separate and backed up. Clone this repository into a separate directory, then copy the source overlay into the fresh native root:

```sh
git clone https://github.com/Boamtoal/pc2-university-platform.git
cp -R pc2-university-platform/lcpc /path/to/fresh-pc2-9.10.0/
cp -R pc2-university-platform/tools /path/to/fresh-pc2-9.10.0/
```

Do not replace the upstream `README`, `VERSION`, `doc`, `bin`, `lib` or About/license assets. Keep this repository's documentation and [NOTICE](../NOTICE.md) available to operators too. Commands below run from `/path/to/fresh-pc2-9.10.0`; replace that placeholder with your real directory.

## 2. Python and build dependencies

```sh
cd /path/to/fresh-pc2-9.10.0
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -r lcpc/admin/requirements.txt
mkdir -p work/wti .local/tools
unzip -q projects/WebTeamInterface-1.1-7065.zip -d work/wti
export LCPC_BUILD_JAVA_HOME="$JAVA_HOME"
sh lcpc/build-tools.sh
```

Set `JAVA_HOME` to an installed JDK first, or set `LCPC_BUILD_JAVA_HOME` directly. The expected extracted build dependency is `work/wti/WebTeamInterface-1.1/WebTeamInterface-1.1.jar`. The source package excludes event-specific import/audit programs; the reusable bridge sources remain included.

Install Lima, Caddy and a suitable OpenSSL through your trusted package manager. Copy the trusted Caddy executable to `.local/tools/caddy` (the current lifecycle expects that path) and make it executable. For example, after installation:

```sh
cp "$(command -v caddy)" .local/tools/caddy
chmod 700 .local/tools/caddy
```

Do not download an arbitrary executable from an issue/comment. Configure runtime paths explicitly if your installation differs:

| Variable | Meaning |
| --- | --- |
| `LCPC_JAVA_HOME` / `JAVA_HOME` | Native Java home |
| `LCPC_JAVA_BIN` | Java executable if no Java home is selected |
| `LCPC_BUILD_JAVA_HOME` | JDK for compiling the bridge |
| `LCPC_LIMA_BIN` | Trusted `limactl` executable |
| `LCPC_OPENSSL` | OpenSSL executable for the participant network manager |
| `LCPC_PDF_PYTHON` | Python executable with reportlab/pypdf; defaults to the running Python |
| `LCPC_STATE_DIR` | Selected private native contest state for `pc2ctl.py` |

Some older lifecycle helpers still expect Homebrew OpenSSL at `/opt/homebrew/bin/openssl`, and macOS tools at their standard locations. See Roadmap before attempting another host layout. Start the dashboard with the same virtual-environment Python or explicitly configure `LCPC_PDF_PYTHON`.

## 3. Provision the isolated judge

Read `lcpc/infra/judge-vm.yaml` and `lcpc/infra/linux/` before provisioning. The VM has **no host directory mounts**. Never add your contest or home directory as a shared mount to make an error disappear.

```sh
export LIMA_HOME="$PWD/.local/lima"
limactl start --tty=false --name=lcpc-judge lcpc/infra/judge-vm.yaml
python -B lcpc/pc2ctl.py linux-install
```

Initial VM provisioning installs Linux packages and the trusted sandbox runtime; it does not initialize an official contest or start its clock. Re-running setup against a modified judge requires operator review. An existing incompatible VM must not be silently replaced.

## 4. Bootstrap a fresh technical rehearsal

Do this only in the fresh installation with no other managed server using the native ports. The supplied practice template contains **two public synthetic toy problems**, no real event tests or solutions.

```sh
python -B lcpc/pc2ctl.py init-isolated-test rehearsal
export LCPC_STATE_DIR="$PWD/.local/instances/rehearsal"
python -B lcpc/pc2ctl.py bootstrap
python -B lcpc/pc2ctl.py isolated-up
python -B lcpc/admin/manage.py init --state "$LCPC_STATE_DIR"
python -B lcpc/admin/manage.py start --state "$LCPC_STATE_DIR"
```

Bootstrap is only for a new uninitialized instance. It generates fresh private credentials and secures native accounts. Never rerun it over an initialized event. A partial failure must be inspected rather than deleting profiles to force a restart. Startup leaves the contest clock paused.

Open **http://127.0.0.1:8091/** locally. Read the random owner password from `$LCPC_STATE_DIR/admin-dashboard/INITIAL-LOGIN.txt`, sign in as `admin`, replace it with a unique 16–128 character password and enable TOTP. Do not include this file in any public archive. The native Administrator, when required, uses a separate account.

## 5. Configure private participant access

Read the access center and network policy first. Prefer HTTPS for confidentiality. The supported TLS path creates a local CA that clients must intentionally trust; do not train participants to ignore certificate warnings.

For an explicitly approved plaintext private LAN rehearsal, identify the organizer's actual IP and subnet first, then use the network manager:

```sh
python -B lcpc/pc2ctl.py network-http-prepare SERVER-IP LAN-CIDR
python -B lcpc/pc2ctl.py network-confirm SERVER-IP LAN-CIDR
python -B lcpc/pc2ctl.py network-trial
```

`SERVER-IP` and `LAN-CIDR` are placeholders, not valid literal arguments. Use only a verified private network you administer. For TLS use `network-prepare SERVER-IP LAN-CIDR` and follow the generated CA instructions before `network-trial`. Default participant HTTP is port **8088**, TLS **8443**. The dashboard is **8091** loopback; optional remote organizer HTTPS is a separate **8092** listener with user/IP approval.

Check **System → Participant test & access** for the actual URLs and read-only checks. The UI's adaptive IP display does not change addresses already typed on other laptops. Test on the real router and every physical team device.

## 6. Rehearse and prepare the official event

Use the separate diagnostic team in a separate browser profile, verify statements/downloads, send known successful and failing synthetic solutions, inspect exact verdicts and human approval, and compare private/public freeze behavior. Starting the **technical** clock for these tests is an explicit operator action. Never test by changing official event results.

Create the official event through **Contests**, using a new unique ID and fresh teams. Review problem data, references, limits, validators, resources, difficulty, colors, duration, timezone, penalties, approval mode and freeze. Safely deactivate the rehearsal before activation. Activation and clock start remain separate actions.

Take an encrypted backup and rehearse restoration into a new workspace. Verify intended concurrent load, storage and at least one full post-contest learning export. Record what was tested and any limitations before accepting the deployment.

## Routine start and stop

Use the saved managed contest in the dashboard's server controls or an explicitly selected state. `manage.py start` starts only the dashboard. Native activation/startup does not start the contest clock. Pause the native contest and resolve pending judgements before planned maintenance. Use clean lifecycle shutdown; do not kill Java to bypass a refusal.

```sh
python -B lcpc/admin/manage.py status --state "$LCPC_STATE_DIR"
python -B lcpc/pc2ctl.py status
```

See the User Guide for event workflows. Read operational acceptance scripts before executing them; some submit test source, alter a dedicated trial or need retained local evidence. A passing source-level test suite is not proof that another laptop can reach your router.
