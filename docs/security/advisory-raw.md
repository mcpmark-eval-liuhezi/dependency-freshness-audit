# Raw Advisory Facts — `requests` (pip)

Source: GitHub Global Security Advisories (pip ecosystem, `requests`), retrieved 2026-10-21 via `list_global_security_advisories` and `get_global_security_advisory`. This file is the unedited audit-trail record of the selected advisory.

## Selection
Highest-severity reviewed advisory affecting `requests` in the pip ecosystem. Severity ladder checked: critical (none found), high (1 found), medium (2+ found). No tie to break.

## Advisory record (as returned by the lookup)
- GHSA ID: GHSA-x84v-xcm2-53pg
- CVE ID: CVE-2018-18074
- Severity: high
- CVSS: score 7.5, vector CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:N/A:N
- CWE: CWE-522 — Insufficiently Protected Credentials
- Summary: Insufficiently Protected Credentials in Requests
- Description: The Requests package through 2.19.1 before 2018-09-14 for Python sends an HTTP Authorization header to an http URI upon receiving a same-hostname https-to-http redirect, which makes it easier for remote attackers to discover credentials by sniffing the network.
- Package: pip / requests
- Vulnerable version range: <= 2.19.1
- First patched version: 2.20.0
- Published at: 2018-10-29T19:06:46Z
- Updated at: 2024-10-21T21:26:18Z
- NVD published at: 2018-10-09T17:29:00Z
- GitHub reviewed at: 2020-06-16T22:02:40Z
- Type: reviewed
- Source code location: https://github.com/requests/requests
- Advisory URL: https://github.com/advisories/GHSA-x84v-xcm2-53pg

## References (as returned)
1. https://nvd.nist.gov/vuln/detail/CVE-2018-18074
2. https://github.com/requests/requests/issues/4716
3. https://github.com/requests/requests/pull/4718
4. https://github.com/requests/requests/commit/c45d7c49ea75133e52ab22a8e9e13173938e36ff
5. https://access.redhat.com/errata/RHSA-2019:2035
6. https://bugs.debian.org/910766
7. http://docs.python-requests.org/en/master/community/updates/#release-and-version-history
8. http://lists.opensuse.org/opensuse-security-announce/2019-07/msg00024.html
9. https://www.oracle.com/security-alerts/cpujul2022.html
10. https://github.com/pypa/advisory-database/tree/main/vulns/requests/PYSEC-2018-28.yaml
11. https://usn.ubuntu.com/3790-1
12. https://usn.ubuntu.com/3790-2
13. https://github.com/advisories/GHSA-x84v-xcm2-53pg
