# Contributing

This is **version 1.0.0**, the first public release. Everyone may use, study, modify and improve the source under EPL-2.0. Contributions should preserve original PC²/WTI authorship, notices and logos/acknowledgements. Do not imply that Boamtoal or OMU created the upstream contest engine.

## Workflow

1. Read the User Guide, Installation and Roadmap. Open a sanitized issue describing a concrete problem before large architectural changes.
2. Fork and branch. Keep changes focused and write English interface/documentation text; translated participant Instructions are an intentional exception.
3. Add meaningful synthetic regression coverage for changed behavior. Do not write tests that depend on real teams, credentials or private judge data.
4. Run the relevant checks below. Document anything not exercised, especially native server, sandbox, LAN and clean-machine paths.
5. Send a pull request describing the trigger, behavior, validation and limits. Never publish your `.local`, student source, private tests, problem booklets, backups or logs.

By submitting a contribution, you state you have the right to provide it under EPL-2.0. Keep original file-level third-party licenses. The code license does not grant logo/trademark or endorsement rights.

## Local checks

Python 3.11+ and Node 20+ are recommended. Install the PDF requirements in an isolated virtual environment for PDF tests. Native-backed checks additionally need the documented matching external PC²/WTI jars and Java 17+ bridge build.

```sh
python3 tools/build-guide.py --check
node --check lcpc/admin-ui/guide.js
node --test lcpc/admin/tests/*.test.cjs lcpc/branding/tests/*.test.cjs
python3 -B -m unittest discover -s lcpc/admin/tests -p 'test_*.py'
```

The admin test suite uses temporary state and fake bridges for HTTP/storage paths; some modules compile/read native Java classes and some generate PDFs. For a quick dependency-light documentation check:

```sh
node --test lcpc/admin/tests/guide.test.cjs lcpc/admin/tests/workspace-nav.test.cjs
python3 -B -m unittest discover -s tools/tests -p 'test_*.py'
```

Tests under `lcpc/infra/test_*.py` include real operational acceptance scripts. **Read each script before running it**: some require a dedicated isolated trial, installed VM and native services; they are not a generic safe CI command for a live contest. Use a fresh technical state, never an official event. Do not start the contest clock as a side effect of a documentation check.

## Guide maintenance

Edit `docs/guide.json`, then run `python3 tools/build-guide.py`. Commit both generated `docs/USER_GUIDE.md` and `lcpc/admin-ui/guide-content.js`. The UI escapes guide content and supports offline reading after dashboard sign-in. Keep claims aligned with implemented behavior and explicitly state gaps.

## Release process

Run `python3 tools/package-source.py --output /tmp/pc2-university-platform-source` into a new directory. Review its manifest and scan results. Compile/run supported checks against that staged source where dependencies are available. Verify the README logos and relative links exist. Tag a tested source release; list any untested deployment scenarios in release notes. Do not publish an operational installation wholesale.
