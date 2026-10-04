#!/usr/bin/env python3
"""Inspect finished writing without collapsing support, synthesis, and inference."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import re
import sys
from pathlib import Path
from typing import Any

FORMAT = "provenance-lens/0.1"
SOURCE_KINDS = ("primary", "contemporary-report", "later-retelling", "reference", "analysis", "other")
UNIT_KINDS = ("direct-support", "synthesis", "inference", "missing-bridge")


class LensError(Exception):
    pass


def now_utc() -> str:
    return dt.datetime.now(dt.timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")


def valid_date(value: str) -> bool:
    if re.fullmatch(r"\d{4}", value):
        return True
    try:
        if re.fullmatch(r"\d{4}-\d{2}", value):
            dt.date.fromisoformat(value + "-01")
            return True
        if re.fullmatch(r"\d{4}-\d{2}-\d{2}", value):
            dt.date.fromisoformat(value)
            return True
    except ValueError:
        return False
    return False


def new_project(title: str, passage: str | None = None) -> dict[str, Any]:
    title = title.strip()
    if not title:
        raise LensError("title cannot be empty")
    return {
        "format": FORMAT,
        "title": title,
        "passage": (passage or "").strip(),
        "created_at": now_utc(),
        "sources": [],
        "evidence": [],
        "units": [],
    }


def next_id(items: list[dict[str, Any]], prefix: str) -> str:
    high = 0
    for item in items:
        value = item.get("id", "")
        if value.startswith(prefix) and value[len(prefix):].isdigit():
            high = max(high, int(value[len(prefix):]))
    return f"{prefix}{high + 1:03d}"


def find(items: list[dict[str, Any]], item_id: str, label: str) -> dict[str, Any]:
    for item in items:
        if item["id"] == item_id:
            return item
    raise LensError(f"{label} not found: {item_id}")


def validate(data: dict[str, Any]) -> None:
    if not isinstance(data, dict) or data.get("format") != FORMAT:
        raise LensError("unsupported project format")
    if not isinstance(data.get("title"), str) or not data["title"].strip():
        raise LensError("project requires a title")
    for key in ("sources", "evidence", "units"):
        if not isinstance(data.get(key), list):
            raise LensError(f"project requires a {key} list")

    sids: set[str] = set()
    for source in data["sources"]:
        sid = source.get("id")
        if not isinstance(sid, str) or not sid or sid in sids:
            raise LensError("invalid or duplicate source id")
        sids.add(sid)
        if source.get("kind") not in SOURCE_KINDS:
            raise LensError(f"{sid}: invalid source kind")
        if not isinstance(source.get("label"), str) or not source["label"].strip():
            raise LensError(f"{sid}: source label cannot be empty")
        if source.get("date") and not valid_date(source["date"]):
            raise LensError(f"{sid}: invalid date")

    eids: set[str] = set()
    for evidence in data["evidence"]:
        eid = evidence.get("id")
        if not isinstance(eid, str) or not eid or eid in eids:
            raise LensError("invalid or duplicate evidence id")
        eids.add(eid)
        if not isinstance(evidence.get("text"), str) or not evidence["text"].strip():
            raise LensError(f"{eid}: evidence text cannot be empty")
        for sid in evidence.get("sources", []):
            if sid not in sids:
                raise LensError(f"{eid}: unknown source {sid}")

    uids: set[str] = set()
    for unit in data["units"]:
        uid = unit.get("id")
        if not isinstance(uid, str) or not uid or uid in uids:
            raise LensError("invalid or duplicate unit id")
        uids.add(uid)

    for unit in data["units"]:
        uid = unit["id"]
        if not isinstance(unit.get("text"), str) or not unit["text"].strip():
            raise LensError(f"{uid}: unit text cannot be empty")
        if unit.get("kind") not in UNIT_KINDS:
            raise LensError(f"{uid}: invalid unit kind")
        for eid in unit.get("evidence", []):
            if eid not in eids:
                raise LensError(f"{uid}: unknown evidence {eid}")
        for basis in unit.get("basis_units", []):
            if basis not in uids:
                raise LensError(f"{uid}: unknown basis unit {basis}")
            if basis == uid:
                raise LensError(f"{uid}: a unit cannot use itself as basis")


def load(path: str | Path) -> dict[str, Any]:
    p = Path(path)
    if not p.exists():
        raise LensError(f"project not found: {p}")
    try:
        data = json.loads(p.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise LensError(f"invalid JSON: {exc}") from exc
    validate(data)
    return data


def save(path: str | Path, data: dict[str, Any]) -> None:
    validate(data)
    Path(path).write_text(json.dumps(data, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def add_source(data: dict[str, Any], label: str, kind: str, date: str | None = None, url: str | None = None, note: str | None = None) -> str:
    if kind not in SOURCE_KINDS:
        raise LensError("invalid source kind")
    if date and not valid_date(date):
        raise LensError("date must be YYYY, YYYY-MM, or YYYY-MM-DD")
    if not label.strip():
        raise LensError("source label cannot be empty")
    sid = next_id(data["sources"], "S")
    data["sources"].append({"id": sid, "label": label.strip(), "kind": kind, "date": date or "", "url": url or "", "note": note or ""})
    return sid


def add_evidence(data: dict[str, Any], text: str, sources: list[str] | None = None, note: str | None = None) -> str:
    if not text.strip():
        raise LensError("evidence text cannot be empty")
    source_ids = list(dict.fromkeys(sources or []))
    for sid in source_ids:
        find(data["sources"], sid, "source")
    eid = next_id(data["evidence"], "E")
    data["evidence"].append({"id": eid, "text": text.strip(), "sources": source_ids, "note": note or ""})
    return eid


def add_unit(data: dict[str, Any], text: str, kind: str, evidence: list[str] | None = None, basis_units: list[str] | None = None, reason: str | None = None) -> str:
    if kind not in UNIT_KINDS:
        raise LensError("invalid unit kind")
    if not text.strip():
        raise LensError("unit text cannot be empty")
    evidence_ids = list(dict.fromkeys(evidence or []))
    basis_ids = list(dict.fromkeys(basis_units or []))
    for eid in evidence_ids:
        find(data["evidence"], eid, "evidence")
    for uid in basis_ids:
        find(data["units"], uid, "basis unit")
    uid = next_id(data["units"], "U")
    data["units"].append({
        "id": uid,
        "text": text.strip(),
        "kind": kind,
        "evidence": evidence_ids,
        "basis_units": basis_ids,
        "reason": reason or "",
    })
    return uid


def audit(data: dict[str, Any]) -> list[str]:
    findings: list[str] = []
    for evidence in data["evidence"]:
        if not evidence.get("sources"):
            findings.append(f"{evidence['id']}: evidence has no recorded source")

    for unit in data["units"]:
        uid = unit["id"]
        kind = unit["kind"]
        evidence_count = len(unit.get("evidence", []))
        basis_count = len(unit.get("basis_units", []))
        if kind == "direct-support" and evidence_count == 0:
            findings.append(f"{uid}: direct-support unit has no evidence link")
        if kind == "synthesis" and evidence_count + basis_count < 2:
            findings.append(f"{uid}: synthesis has fewer than two recorded bases")
        if kind == "inference" and evidence_count + basis_count == 0:
            findings.append(f"{uid}: inference has no recorded basis")
        if kind == "missing-bridge":
            findings.append(f"{uid}: unit is explicitly marked missing-bridge")
    return findings


def render_matrix(data: dict[str, Any]) -> str:
    counts = {kind: sum(u["kind"] == kind for u in data["units"]) for kind in UNIT_KINDS}
    return (
        "| direct-support | synthesis | inference | missing-bridge |\n"
        "|---:|---:|---:|---:|\n"
        f"| {counts['direct-support']} | {counts['synthesis']} | {counts['inference']} | {counts['missing-bridge']} |\n"
    )


def render_markdown(data: dict[str, Any]) -> str:
    source_labels = {s["id"]: s["label"] for s in data["sources"]}
    evidence_map = {e["id"]: e for e in data["evidence"]}
    lines = [
        f"# {data['title']}", "",
        f"_Provenance Lens format: `{FORMAT}`_", "",
        "> Classification describes the visible support structure. It is not an automatic truth score.", "",
    ]
    if data.get("passage"):
        lines += ["## Passage under inspection", "", data["passage"], ""]

    lines += ["## Lens", ""]
    if not data["units"]:
        lines += ["_No writing units yet._", ""]
    for unit in data["units"]:
        lines += [f"### {unit['id']} · {unit['kind']}", "", unit["text"], ""]
        if unit.get("reason"):
            lines += [f"**Classification note:** {unit['reason']}", ""]
        if unit.get("evidence"):
            lines += ["**Evidence:**", ""]
            for eid in unit["evidence"]:
                item = evidence_map[eid]
                source_text = ""
                if item.get("sources"):
                    source_text = " · " + ", ".join(f"{sid} {source_labels[sid]}" for sid in item["sources"])
                lines.append(f"- {eid}: {item['text']}{source_text}")
            lines.append("")
        if unit.get("basis_units"):
            lines += ["**Basis units:** " + ", ".join(unit["basis_units"]), ""]

    lines += ["## Classification matrix", "", render_matrix(data).rstrip(), "", "## Structural audit", ""]
    findings = audit(data)
    lines += [f"- {finding}" for finding in findings] if findings else ["_No structural audit flags._"]
    return "\n".join(lines).rstrip() + "\n"


def render_mermaid(data: dict[str, Any]) -> str:
    lines = ["flowchart LR"]
    for source in data["sources"]:
        label = source["label"].replace('"', "'").replace("\n", " ")
        lines.append(f'  {source["id"]}["{source["id"]} · {label}"]')
    for evidence in data["evidence"]:
        label = evidence["text"].replace('"', "'").replace("\n", " ")
        lines.append(f'  {evidence["id"]}["{evidence["id"]} · {label}"]')
        for sid in evidence["sources"]:
            lines.append(f'  {sid} -->|supports record| {evidence["id"]}')
    for unit in data["units"]:
        label = unit["text"].replace('"', "'").replace("\n", " ")
        lines.append(f'  {unit["id"]}["{unit["id"]} · {unit["kind"]} · {label}"]')
        for eid in unit["evidence"]:
            lines.append(f'  {eid} -->|supports| {unit["id"]}')
        for basis in unit["basis_units"]:
            lines.append(f'  {basis} -->|basis for| {unit["id"]}')
    return "\n".join(lines) + "\n"


def summary(data: dict[str, Any]) -> str:
    counts = {kind: sum(u["kind"] == kind for u in data["units"]) for kind in UNIT_KINDS}
    return (
        f"{data['title']}: {len(data['units'])} unit(s), "
        f"{counts['direct-support']} direct, {counts['synthesis']} synthesis, "
        f"{counts['inference']} inference, {counts['missing-bridge']} missing bridge, "
        f"{len(audit(data))} audit flag(s)"
    )


def parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="provenance-lens", description="Inspect finished writing for visible provenance bridges.")
    sub = p.add_subparsers(dest="command", required=True)

    q = sub.add_parser("new"); q.add_argument("file"); q.add_argument("--title", required=True); q.add_argument("--passage")
    q = sub.add_parser("source"); q.add_argument("file"); q.add_argument("label"); q.add_argument("--kind", choices=SOURCE_KINDS, default="other"); q.add_argument("--date"); q.add_argument("--url"); q.add_argument("--note")
    q = sub.add_parser("evidence"); q.add_argument("file"); q.add_argument("text"); q.add_argument("--source", action="append", default=[]); q.add_argument("--note")
    q = sub.add_parser("unit"); q.add_argument("file"); q.add_argument("text"); q.add_argument("--kind", choices=UNIT_KINDS, required=True); q.add_argument("--evidence", action="append", default=[]); q.add_argument("--basis", action="append", default=[]); q.add_argument("--reason")

    for name in ("show", "check", "audit"):
        q = sub.add_parser(name); q.add_argument("file")
    for name in ("render", "matrix", "mermaid"):
        q = sub.add_parser(name); q.add_argument("file"); q.add_argument("-o", "--output")
    return p


def main(argv: list[str] | None = None) -> int:
    args = parser().parse_args(argv)
    try:
        if args.command == "new":
            if Path(args.file).exists():
                raise LensError(f"refusing to overwrite existing file: {args.file}")
            save(args.file, new_project(args.title, args.passage))
            print(f"created {args.file}")
            return 0

        data = load(args.file)

        if args.command == "source":
            sid = add_source(data, args.label, args.kind, args.date, args.url, args.note); save(args.file, data); print(sid)
        elif args.command == "evidence":
            eid = add_evidence(data, args.text, args.source, args.note); save(args.file, data); print(eid)
        elif args.command == "unit":
            uid = add_unit(data, args.text, args.kind, args.evidence, args.basis, args.reason); save(args.file, data); print(uid)
        elif args.command == "show":
            print(summary(data))
        elif args.command == "check":
            print(f"ok: {args.file}")
        elif args.command == "audit":
            findings = audit(data); print("\n".join(findings) if findings else "no structural audit flags")
        else:
            output = {"render": render_markdown, "matrix": render_matrix, "mermaid": render_mermaid}[args.command](data)
            if args.output:
                Path(args.output).write_text(output, encoding="utf-8"); print(args.output)
            else:
                print(output, end="")
        return 0
    except LensError as exc:
        print(f"provenance-lens: {exc}", file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
