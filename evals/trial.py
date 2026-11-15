#!/usr/bin/env python3
"""Local worksheet and report helper for skill evaluation trials.

Stdlib only; no network, no model calls, nothing is executed for the trial.
  trial.py init DESTINATION [--trial-id ...]   write an unscored worksheet
  trial.py report WORKSHEET [--format text|json]  validate and summarise it

A report describes what a reviewer recorded, not verified agent behaviour.
"""
import argparse
import datetime
import hashlib
import json
import subprocess
import sys
from pathlib import Path

EVALS = Path(__file__).resolve().parent
WORKSHEET_VERSION = 1
PROVENANCE = ("trial_id", "trial_date", "catalog_commit", "client", "model", "reviewer")
ACTIVATION_STATUSES = ("pending", "observed", "unobserved")
RUBRIC_STATUSES = ("pass", "fail", "not-applicable", "unscored")
UNDEFINED = "undefined"


class WorksheetError(Exception):
    pass


def canonical_sha256(data) -> str:
    text = json.dumps(data, sort_keys=True, separators=(",", ":"), ensure_ascii=False)
    return hashlib.sha256(text.encode()).hexdigest()


def blank_text(value) -> bool:
    return not isinstance(value, str) or not value.strip()


def case_skeletons(skill: str, content: dict) -> list[dict]:
    cases = []
    for n, prompt in enumerate(content["positive_prompts"], 1):
        cases.append(
            {
                "case_id": f"{skill}/p{n}",
                "skill": skill,
                "kind": "positive",
                "prompt": prompt,
                "expected_skill": skill,
                "activation": {"status": "pending", "activated_skills": [], "evidence": ""},
                "rubric": [
                    {"rubric_id": f"r{i}", "item": item, "status": "unscored", "evidence": "", "na_reason": ""}
                    for i, item in enumerate(content["rubric"], 1)
                ],
            }
        )
    for n, entry in enumerate(content["negative_prompts"], 1):
        cases.append(
            {
                "case_id": f"{skill}/n{n}",
                "skill": skill,
                "kind": "negative",
                "prompt": entry["prompt"],
                "expected_skill": entry["expected_skill"],
                "activation": {"status": "pending", "activated_skills": [], "evidence": ""},
            }
        )
    return cases


def build_worksheet(scenarios_dir: Path, provenance: dict) -> dict:
    files = sorted(scenarios_dir.glob("*.json"))
    if not files:
        raise WorksheetError(f"no scenario files in {scenarios_dir}")
    scenarios, cases = {}, []
    for path in files:
        content = json.loads(path.read_text())
        skill = content["skill"]
        scenarios[skill] = {
            "file": path.name,
            "file_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "content_sha256": canonical_sha256(content),
            "content": content,
        }
        cases.extend(case_skeletons(skill, content))
    worksheet = {"worksheet_version": WORKSHEET_VERSION}
    worksheet.update({key: provenance.get(key) for key in PROVENANCE})
    worksheet["scenarios"] = scenarios
    worksheet["cases"] = cases
    return worksheet


def git_head() -> str | None:
    try:
        out = subprocess.run(
            ["git", "-C", str(EVALS), "rev-parse", "HEAD"], capture_output=True, text=True, timeout=10, check=False
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return out.stdout.strip() if out.returncode == 0 and out.stdout.strip() else None


def validate_worksheet(ws) -> list[str]:
    """Check a worksheet against its own embedded snapshots (never the live scenarios)."""
    if not isinstance(ws, dict):
        return ["worksheet must be a JSON object"]
    errors = []
    if ws.get("worksheet_version") != WORKSHEET_VERSION:
        errors.append(f"worksheet_version must be {WORKSHEET_VERSION}")
    for key in PROVENANCE:
        if blank_text(ws.get(key)):
            errors.append(f"missing provenance: {key} (fill it in before reporting)")
    date = ws.get("trial_date")
    if isinstance(date, str) and date.strip():
        try:
            datetime.date.fromisoformat(date)
        except ValueError:
            errors.append(f"trial_date must be YYYY-MM-DD, got {date!r}")
    expected = {}
    scenarios = ws.get("scenarios")
    if not isinstance(scenarios, dict) or not scenarios:
        errors.append("scenarios snapshot is missing or empty")
        scenarios = {}
    for skill, snap in sorted(scenarios.items()):
        content = snap.get("content") if isinstance(snap, dict) else None
        try:
            skeletons = case_skeletons(skill, content)
        except (KeyError, TypeError, AttributeError):
            errors.append(f"scenario snapshot for {skill!r} is malformed")
            continue
        if canonical_sha256(content) != snap.get("content_sha256"):
            errors.append(f"scenario snapshot for {skill!r} does not match its recorded content_sha256")
        for skeleton in skeletons:
            expected[skeleton["case_id"]] = skeleton
    cases = ws.get("cases")
    if not isinstance(cases, list):
        return errors + ["cases must be a list"]
    seen = set()
    for index, case in enumerate(cases):
        if not isinstance(case, dict):
            errors.append(f"cases[{index}] must be an object")
            continue
        cid = case.get("case_id")
        if cid in seen:
            errors.append(f"duplicate record for case {cid!r}")
            continue
        seen.add(cid)
        if cid not in expected:
            errors.append(f"unknown case id {cid!r} (not in the scenario snapshot)")
            continue
        errors.extend(case_errors(case, expected[cid]))
    for cid in sorted(set(expected) - seen):
        errors.append(f"case {cid!r} is missing from the worksheet")
    return errors


def case_errors(case: dict, skeleton: dict) -> list[str]:
    cid = skeleton["case_id"]
    errors = []
    for field in ("skill", "kind", "prompt", "expected_skill"):
        if case.get(field) != skeleton[field]:
            errors.append(f"{cid}: {field} {case.get(field)!r} does not match the scenario snapshot {skeleton[field]!r}")
    act = case.get("activation")
    if not isinstance(act, dict):
        errors.append(f"{cid}: activation record is missing")
    else:
        status = act.get("status")
        if status not in ACTIVATION_STATUSES:
            errors.append(f"{cid}: invalid activation status {status!r} (use one of {', '.join(ACTIVATION_STATUSES)})")
        skills = act.get("activated_skills")
        if not isinstance(skills, list) or any(blank_text(s) for s in skills):
            errors.append(f"{cid}: activated_skills must be a list of skill names")
        elif status != "observed" and skills:
            errors.append(f"{cid}: activated_skills must be empty unless activation status is 'observed'")
        if status == "observed" and blank_text(act.get("evidence")):
            errors.append(f"{cid}: observed activation needs evidence")
    if skeleton["kind"] == "negative":
        if case.get("rubric"):
            errors.append(f"{cid}: negative cases carry no rubric records")
        return errors
    records = case.get("rubric")
    if not isinstance(records, list):
        return errors + [f"{cid}: rubric must be a list"]
    want = {r["rubric_id"]: r for r in skeleton["rubric"]}
    seen = set()
    for record in records:
        rid = record.get("rubric_id") if isinstance(record, dict) else None
        if rid in seen:
            errors.append(f"{cid}: duplicate rubric record {rid!r}")
            continue
        seen.add(rid)
        if rid not in want:
            errors.append(f"{cid}: unknown rubric id {rid!r}")
            continue
        errors.extend(rubric_errors(cid, record, want[rid]))
    for rid in sorted(set(want) - seen):
        errors.append(f"{cid}: rubric record {rid!r} is missing")
    return errors


def rubric_errors(cid: str, record: dict, skeleton: dict) -> list[str]:
    rid = skeleton["rubric_id"]
    errors = []
    if record.get("item") != skeleton["item"]:
        errors.append(f"{cid}/{rid}: item text does not match the scenario snapshot")
    status = record.get("status")
    if status not in RUBRIC_STATUSES:
        errors.append(f"{cid}/{rid}: invalid status {status!r} (use one of {', '.join(RUBRIC_STATUSES)})")
    elif status in ("pass", "fail") and blank_text(record.get("evidence")):
        errors.append(f"{cid}/{rid}: {status} needs evidence")
    elif status == "not-applicable" and blank_text(record.get("na_reason")):
        errors.append(f"{cid}/{rid}: not-applicable needs na_reason")
    return errors


def activation_outcome(case: dict) -> str:
    act = case["activation"]
    if act["status"] == "pending":
        return "unrecorded"
    if act["status"] == "unobserved":
        return "unobserved"
    activated = set(act["activated_skills"])
    if case["kind"] == "positive":
        return "pass" if case["skill"] in activated else "fail"
    ok = case["expected_skill"] in activated and case["skill"] not in activated
    return "pass" if ok else "fail"


def procedure_outcome(case: dict) -> tuple[str, dict]:
    counts = {status: 0 for status in RUBRIC_STATUSES}
    for record in case["rubric"]:
        counts[record["status"]] += 1
    if counts["fail"]:
        outcome = "fail"
    elif counts["unscored"]:
        outcome = "incomplete"
    elif counts["pass"] == 0:
        outcome = UNDEFINED
    else:
        outcome = "pass"
    return outcome, counts


def rate(numerator: int, denominator: int):
    return UNDEFINED if denominator == 0 else numerator / denominator


def summarize_worksheet(ws: dict) -> dict:
    cases_out = []
    activation = {"pass": 0, "fail": 0, "unobserved": 0, "unrecorded": 0}
    by_kind = {k: {"pass": 0, "fail": 0, "unobserved": 0, "unrecorded": 0} for k in ("positive", "negative")}
    proc_cases = {"pass": 0, "fail": 0, "incomplete": 0, UNDEFINED: 0}
    items = {status: 0 for status in RUBRIC_STATUSES}
    for case in ws["cases"]:
        entry = {
            "case_id": case["case_id"],
            "kind": case["kind"],
            "activation": activation_outcome(case),
            "activated_skills": list(case["activation"]["activated_skills"]),
        }
        activation[entry["activation"]] += 1
        by_kind[case["kind"]][entry["activation"]] += 1
        if case["kind"] == "positive":
            outcome, counts = procedure_outcome(case)
            entry["procedure"] = outcome
            entry["rubric_counts"] = counts
            proc_cases[outcome] += 1
            for status, n in counts.items():
                items[status] += n
        cases_out.append(entry)
    observed = activation["pass"] + activation["fail"]
    scored = items["pass"] + items["fail"]
    applicable = scored + items["unscored"]
    return {
        "trial": {key: ws[key] for key in PROVENANCE},
        "activation": {
            **activation,
            "total": observed + activation["unobserved"] + activation["unrecorded"],
            "observed": observed,
            "rate_observed": rate(activation["pass"], observed),
            "by_kind": by_kind,
            "complete": activation["unobserved"] + activation["unrecorded"] == 0,
        },
        "procedure": {
            "cases": proc_cases,
            "items": {
                "pass": items["pass"],
                "fail": items["fail"],
                "unscored": items["unscored"],
                "not_applicable_excluded": items["not-applicable"],
                "scored": scored,
                "applicable": applicable,
                "rate_scored": rate(items["pass"], scored),
                "rate_applicable": rate(items["pass"], applicable),
            },
            "complete": items["unscored"] == 0,
        },
        "cases": cases_out,
        "note": "Reviewer-recorded observations; not automatic proof of agent behavior.",
    }


def fmt_rate(value, num: int, den: int) -> str:
    return f"{num}/{den} = undefined" if value == UNDEFINED else f"{num}/{den} = {value:.0%}"


def render_text(summary: dict, drift: list[str] | None = None) -> str:
    t, a, p = summary["trial"], summary["activation"], summary["procedure"]
    lines = [
        f"Trial {t['trial_id']} on {t['trial_date']} (catalog {t['catalog_commit']})",
        f"Client {t['client']}, model {t['model']}, reviewer {t['reviewer']}",
        summary["note"],
    ]
    if drift:
        lines.append("Scenarios changed since this trial (snapshot still used): " + ", ".join(drift))
    lines += [
        "",
        "ACTIVATION (expected skill present; pilot skill absent on negative cases)",
        f"  passed {fmt_rate(a['rate_observed'], a['pass'], a['observed'])} observed cases",
        f"  failed {a['fail']}, unobserved {a['unobserved']}, unrecorded {a['unrecorded']} "
        f"(excluded from the denominator, never counted as pass)",
    ]
    for kind, c in a["by_kind"].items():
        lines.append(f"  {kind}: pass {c['pass']}, fail {c['fail']}, unobserved {c['unobserved']}, unrecorded {c['unrecorded']}")
    lines.append(f"  status: {'complete' if a['complete'] else 'INCOMPLETE'}")
    i = p["items"]
    lines += [
        "",
        "PROCEDURE (rubric items on positive cases)",
        f"  scored items passed {fmt_rate(i['rate_scored'], i['pass'], i['scored'])}",
        f"  passed of all applicable {fmt_rate(i['rate_applicable'], i['pass'], i['applicable'])} "
        f"(unscored counted as not passed)",
        f"  failed {i['fail']}, unscored {i['unscored']}, not-applicable {i['not_applicable_excluded']} (excluded)",
        "  cases: " + ", ".join(f"{k} {v}" for k, v in p["cases"].items()),
        f"  status: {'complete' if p['complete'] else 'INCOMPLETE'}",
        "",
        "CASES",
    ]
    for c in summary["cases"]:
        extra = f", procedure {c['procedure']}" if "procedure" in c else ""
        seen = ",".join(c["activated_skills"]) or "-"
        lines.append(f"  {c['case_id']}: activation {c['activation']} (activated: {seen}){extra}")
    return "\n".join(lines) + "\n"


def load_worksheet(path: Path) -> dict:
    try:
        ws = json.loads(path.read_text())
    except (OSError, json.JSONDecodeError) as exc:
        raise WorksheetError(f"cannot read worksheet {path}: {exc}") from exc
    errors = validate_worksheet(ws)
    if errors:
        raise WorksheetError("worksheet is invalid:\n" + "\n".join(f"  - {e}" for e in errors))
    return ws


def drifted_skills(ws: dict, scenarios_dir: Path) -> list[str]:
    changed = []
    for skill, snap in sorted(ws["scenarios"].items()):
        path = scenarios_dir / snap["file"]
        current = hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else None
        if current != snap["file_sha256"]:
            changed.append(skill)
    return changed


def write_new_worksheet(destination: Path, worksheet: dict) -> None:
    destination = destination.resolve()
    if destination.parent == EVALS:
        raise WorksheetError("destination must be outside evals/ so it is not picked up as a scenario file")
    if not destination.parent.is_dir():
        raise WorksheetError(f"destination directory does not exist: {destination.parent}")
    try:
        with open(destination, "x", encoding="utf-8") as handle:
            handle.write(json.dumps(worksheet, indent=2, ensure_ascii=False) + "\n")
    except FileExistsError:
        raise WorksheetError(f"refusing to overwrite existing file: {destination}") from None


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="command", required=True)
    init = sub.add_parser("init", help="write an unscored worksheet to a new file")
    init.add_argument("destination", type=Path)
    for key in PROVENANCE:
        init.add_argument("--" + key.replace("_", "-"), dest=key)
    report = sub.add_parser("report", help="validate a completed worksheet and report")
    report.add_argument("worksheet", type=Path)
    report.add_argument("--format", choices=("text", "json"), default="text")
    report.add_argument("--check-current", action="store_true", help="note scenarios changed since the trial")
    args = parser.parse_args(argv)
    try:
        if args.command == "init":
            provenance = {key: getattr(args, key) for key in PROVENANCE}
            provenance["trial_date"] = provenance["trial_date"] or datetime.date.today().isoformat()
            provenance["catalog_commit"] = provenance["catalog_commit"] or git_head()
            write_new_worksheet(args.destination, build_worksheet(EVALS, provenance))
            print(f"Wrote unscored worksheet: {args.destination}")
            missing = [k for k in PROVENANCE if blank_text(provenance[k])]
            if missing:
                print("Fill in before reporting: " + ", ".join(missing))
            return 0
        ws = load_worksheet(args.worksheet)
        summary = summarize_worksheet(ws)
        drift = drifted_skills(ws, EVALS) if args.check_current else None
        if args.format == "json":
            if drift is not None:
                summary["scenarios_changed_since_trial"] = drift
            print(json.dumps(summary, indent=2))
        else:
            print(render_text(summary, drift), end="")
        return 0
    except WorksheetError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
