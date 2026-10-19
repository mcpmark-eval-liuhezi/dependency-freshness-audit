#!/usr/bin/env python3
"""generate_audit.py — reproducible dependency freshness audit.

Audits five packages of the analytics stack — numpy, pandas, matplotlib,
requests and pydantic — and prints the finished markdown report (audit.md)
to stdout.

What it does
------------
1. Reads the *installed* version of each package from the Python environment
   the script runs in, via ``importlib.metadata``. The check is strictly
   read-only: nothing is installed, upgraded or otherwise modified.
2. Compares each installed version against the latest *stable* release
   (alphas, betas and release candidates are ignored by design). The
   latest-stable data lives in ``LATEST_STABLE`` as a snapshot taken from
   each project's official release pages on ``AUDIT_DATE``; source links are
   recorded inline so the snapshot can be re-verified or refreshed.
3. Computes each package's status (``current`` / ``behind`` / ``missing``)
   and a deterministic priority ranking, then renders the markdown report.

Usage
-----
    python generate_audit.py             # print the report to stdout
    python generate_audit.py > audit.md  # regenerate audit.md

Ranking rule (deterministic, so it can be challenged)
-----------------------------------------------------
    behind by >= 1 major version   priority 4
    behind by >= 1 minor version   priority 3
    behind by patch versions only  priority 2
    missing entirely               priority 1
    current / ahead of stable      priority 0  (no action needed)

Ties are broken alphabetically by package name.
"""

from __future__ import annotations

import re
import sys
from importlib.metadata import PackageNotFoundError, version

AUDIT_DATE = "2026-10-19"
AUDITED_PACKAGES = ["numpy", "pandas", "matplotlib", "requests", "pydantic"]

# Latest *stable* releases (alphas, betas and release candidates excluded),
# snapshotted from each project's official release pages on AUDIT_DATE.
LATEST_STABLE = {
    "numpy": {
        "version": "2.5.4",
        "released": "2026-10-10",
        "source": "https://github.com/numpy/numpy/releases/tag/v2.5.4",
        "headline": (
            "Patch release fixing bugs found after 2.5.3; highlights are many "
            "typing fixes and improvements plus a workaround for the MSVC 19.51 bug."
        ),
    },
    "pandas": {
        "version": "3.0.6",
        "released": "2026-09-17",
        "source": "https://github.com/pandas-dev/pandas/releases/tag/v3.0.6",
        "headline": (
            "Patch release in the 3.0.x series with regression and bug fixes, "
            "recommended for all 3.0.x users; also the first release to support "
            "Python 3.15."
        ),
    },
    "matplotlib": {
        "version": "3.11.2",
        "released": "2026-09-11",
        "source": "https://github.com/matplotlib/matplotlib/releases/tag/v3.11.2",
        "headline": (
            "Second bugfix release of the 3.11.x series; headline change is a "
            "speed-up of RGBA-stage image resampling, alongside numerous "
            "rendering and output fixes."
        ),
    },
    "requests": {
        "version": "2.34.2",
        "released": "2026-05-14",
        "source": "https://github.com/psf/requests/releases/tag/v2.34.2",
        "headline": (
            "Moves the headers input type back to Mapping to avoid invariance "
            "issues with MutableMapping and inferred dict types."
        ),
    },
    "pydantic": {
        "version": "2.14.1",
        "released": "2026-10-11",
        "source": "https://github.com/pydantic/pydantic/releases/tag/v2.14.1",
        "headline": (
            "Performance-focused patch release: avoids Python tuple allocation "
            "during model fields validation and unnecessary extra dict allocation "
            "in model validation, plus a set of validation bug fixes."
        ),
    },
}

# Python support windows as stated on the release pages consulted for this
# audit; only packages whose pages stated a window are listed.
PYTHON_SUPPORT = {"numpy": "3.12-3.15", "pandas": "3.11+"}
PYTHON_SUPPORT_FLOOR = {"numpy": (3, 12), "pandas": (3, 11)}

PRIORITY_BY_DRIFT = {"major": 4, "minor": 3, "patch": 2}
PRIORITY_MISSING = 1
PRIORITY_NO_ACTION = 0

ADVICE_BEHIND = {
    "pandas": (
        "the biggest jump of the five; the 2.x to 3.x line includes "
        "backwards-incompatible API changes, so read the 3.0 whatsnew and run "
        "the full test suite before deploying"
    ),
    "numpy": (
        "a low-risk in-place upgrade; do it in the same change window as the "
        "pandas bump so the core stack moves together"
    ),
}

ADVICE_MISSING = {
    "matplotlib": "install it if plotting is part of the stack's remit",
    "pydantic": "install it when schema validation is needed",
    "requests": "install it when the stack needs to make HTTP calls",
}


def installed_version(package: str):
    """Installed distribution version, or None when the package is absent."""
    try:
        return version(package)
    except PackageNotFoundError:
        return None


def version_tuple(v: str):
    """Best-effort numeric tuple for comparison ('2.3.1' -> (2, 3, 1))."""
    parts = []
    for piece in v.split("."):
        match = re.match(r"\d+", piece)
        if not match:
            break
        parts.append(int(match.group()))
    return tuple(parts)


def classify(installed: str, latest: str):
    """Return (status, drift_kind, drift_count) for an installed version."""
    a, b = version_tuple(installed), version_tuple(latest)
    if a == b:
        return "current", None, 0
    if a > b:
        return "ahead", None, 0
    if a[0] != b[0]:
        return "behind", "major", b[0] - a[0]
    if a[1] != b[1]:
        return "behind", "minor", b[1] - a[1]
    return "behind", "patch", b[2] - a[2]


def build_rows():
    """One row per package: latest, installed, status, priority, rank."""
    rows = []
    for name in AUDITED_PACKAGES:
        latest = LATEST_STABLE[name]["version"]
        installed = installed_version(name)
        row = {"package": name, "latest": latest, "installed": installed}
        if installed is None:
            row.update(status="missing", gap=None, priority=PRIORITY_MISSING)
        else:
            status, drift, count = classify(installed, latest)
            row["status"] = status
            if status == "behind":
                plural = "" if count == 1 else "s"
                row["gap"] = f"{count} {drift} version{plural}"
                row["priority"] = PRIORITY_BY_DRIFT[drift]
            else:
                row.update(gap=None, priority=PRIORITY_NO_ACTION)
        rows.append(row)

    actionable = sorted(
        (r for r in rows if r["priority"] > 0),
        key=lambda r: (-r["priority"], r["package"]),
    )
    for rank, row in enumerate(actionable, start=1):
        row["rank"] = rank
    for row in rows:
        row.setdefault("rank", None)
    return rows


def render(rows):
    """Render the full markdown report from the computed rows."""
    py = f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}"
    env_py = (sys.version_info.major, sys.version_info.minor)

    n_current = sum(1 for r in rows if r["status"] == "current")
    n_behind = sum(1 for r in rows if r["status"] == "behind")
    n_missing = sum(1 for r in rows if r["status"] == "missing")

    ordered = sorted(
        rows,
        key=lambda r: (r["rank"] is None, r["rank"] or 0, r["package"]),
    )

    out = []
    out.append("# Dependency freshness audit")
    out.append("")
    out.append(
        "Handover audit of the analytics stack's five audited dependencies, "
        f"generated by `generate_audit.py` on **{AUDIT_DATE}** (run under Python {py})."
    )
    out.append("")
    out.append(
        "- **Latest stable** = each project's newest final release; alphas, betas "
        "and release candidates are excluded. Sourced from the projects' official "
        "release pages (linked below)."
    )
    out.append(
        "- **Installed** = what `importlib.metadata` finds in the environment this "
        "script runs in. Read-only check: nothing was installed or upgraded during "
        "the audit."
    )
    out.append("")
    out.append("## Summary")
    out.append("")
    out.append("| Package | Latest stable | Installed | Status | Priority |")
    out.append("| --- | --- | --- | --- | --- |")
    for r in ordered:
        installed = r["installed"] if r["installed"] is not None else "not installed"
        if r["status"] == "behind":
            status = f"behind ({r['gap']})"
        elif r["status"] == "missing":
            status = "missing"
        elif r["status"] == "current":
            status = "current"
        else:
            status = "ahead of stable"
        priority = str(r["rank"]) if r["rank"] is not None else "-"
        out.append(
            f"| {r['package']} | {r['latest']} | {installed} | {status} | {priority} |"
        )
    out.append("")
    out.append(
        'Priority 1 = act first; "-" = no action needed. Ranking rule: '
        "major-version lag > minor > patch > missing; ties break alphabetically "
        "by package name."
    )
    out.append("")
    out.append("## Latest stable release highlights")
    out.append("")
    for name in AUDITED_PACKAGES:
        meta = LATEST_STABLE[name]
        out.append(
            f"- **{name} {meta['version']}** (released {meta['released']}) — "
            f"{meta['headline']} ([release page]({meta['source']}))"
        )
    out.append("")
    out.append("## Handover notes")
    out.append("")
    out.append(
        f"As of {AUDIT_DATE}: {n_current} of {len(rows)} packages current, "
        f"{n_behind} behind, {n_missing} missing."
    )
    out.append("")
    ranked = [r for r in ordered if r["rank"] is not None]
    if ranked:
        out.append("What to upgrade or install first, in order:")
        out.append("")
        for r in ranked:
            if r["status"] == "behind":
                verb = "upgrade"
                lead = (
                    f"Installed {r['installed']}, latest stable {r['latest']} "
                    f"({r['gap']} behind)."
                )
                advice = ADVICE_BEHIND.get(
                    r["package"], "upgrade to the latest stable listed above"
                )
            else:
                verb = "install"
                lead = f"Not installed; latest stable is {r['latest']}."
                advice = ADVICE_MISSING.get(
                    r["package"],
                    "install the latest stable listed above if the stack needs it",
                )
            out.append(f"{r['rank']}. **{r['package']} — {verb}.** {lead} {advice}.")
        out.append("")
    else:
        out.append("Nothing to do — every audited package is current.")
        out.append("")
    out.append(f"Python compatibility (this environment runs Python {py}):")
    compat = []
    for name, floor in PYTHON_SUPPORT_FLOOR.items():
        if env_py < floor:
            compat.append(
                f"- Warning: {name} {LATEST_STABLE[name]['version']} supports Python "
                f"{PYTHON_SUPPORT[name]}, but this environment runs Python {py} — "
                "a Python upgrade is a prerequisite for that target version."
            )
    if not compat:
        compat.append(
            "- The recorded Python-support windows (numpy 2.5.4: "
            f"{PYTHON_SUPPORT['numpy']}; pandas 3.0.6: {PYTHON_SUPPORT['pandas']}) "
            f"are satisfied by this environment's Python {py}."
        )
    out.extend(compat)
    out.append("")
    out.append("Also worth knowing:")
    out.append("")
    out.append(
        "- pandas has a 3.1.0rc0 release candidate available; pre-releases are out "
        "of scope for this audit (stable releases only), so it is not counted above."
    )
    out.append("")
    out.append("## Reproducing this audit")
    out.append("")
    out.append(
        "- `python generate_audit.py > audit.md` regenerates this report. Installed "
        "versions are read live from the environment via `importlib.metadata` "
        "(read-only; nothing is installed or upgraded)."
    )
    out.append(
        f"- `LATEST_STABLE` in `generate_audit.py` is a snapshot of each project's "
        f"release pages taken on {AUDIT_DATE} (source links in the highlights "
        "above). Refresh it before re-running after new releases."
    )
    out.append(
        "- Ranking rule (deterministic): behind-by-major → priority 4, "
        "behind-by-minor → 3, behind-by-patch → 2, missing → 1, current/ahead → 0; "
        "ties break alphabetically. Lower rank number = act sooner."
    )
    out.append("")
    return "\n".join(out)


def main():
    rows = build_rows()
    print(render(rows), end="")


if __name__ == "__main__":
    main()
