# Version 1.0.0 source release validation

Release date: **2026-10-23**. Checks below used a separate source-only staging directory with the installed matching native dependencies supplied separately. No visual preview was performed.

| Check | Result |
| --- | --- |
| Java bridge compilation from staged reusable sources | Passed with Java 17 `--release 17`; existing internal Unsafe self-test warnings remain |
| Python administrator tests on staged source | 185 tests, successful; one optional independent OpenCV QR decoder test skipped |
| Administrator + participant JavaScript tests | 96 passed |
| Publication policy tests | 4 passed |
| Generated UI/Markdown guide consistency | Passed |
| Guide/About routes, static logos and private-path denial | Covered by isolated HTTP tests |
| Relative links in new release documentation | Checked; no missing local targets |
| Fresh synthetic practice-state preparation from staged sources | Passed; no native database or contest clock started |
| Source manifest and selected private-data/secret-pattern scan | Passed; real event state and native binary distribution excluded |

The source manifest records each published file's SHA-256 and size. This helps review the release contents, not certify that every future change is safe.

## Not established by these checks

- Full installation and restoration on a newly provisioned physical organizer computer.
- A complete fresh VM/bootstrap cycle on a new host.
- Router reachability and simultaneous physical participant load at another university.
- Independent security certification or an audit of every upstream dependency.
- Organizer Windows/Linux/Intel support, arbitrary language/validator execution, or public cloud hosting.

These remain deployment acceptance requirements or roadmap items. Source-level checks do not justify advertising an event as guaranteed free of problems. See Installation, User Guide, Security and Roadmap.
