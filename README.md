# Provenance Lens

**Version:** 0.1  
**Status:** experimental

Provenance Lens inspects finished claims and writing to distinguish **direct support, synthesis, inference, and missing provenance bridges**.

Its central rule:

> **Classification describes the visible reasoning structure. It is not a truth score.**

A sentence may be an inference and still be reasonable. A synthesis may be strong. A directly supported statement may still depend on a flawed source. Provenance Lens does not collapse those questions together.

## What it records

A project contains:

- the finished passage under inspection
- sources
- source-backed evidence snippets
- individual writing units
- the classification of each unit
- evidence links
- links to prior writing units used as reasoning bases
- classification notes
- structural audit findings

Writing-unit classes:

- `direct-support`
- `synthesis`
- `inference`
- `missing-bridge`

## Quick start

```bash
python provenance_lens.py new lens.json \
  --title "Warning-note paragraph" \
  --passage "The warning note appears only in later retellings, so it may have entered the story later."

python provenance_lens.py source lens.json "1904 station log" \
  --kind primary --date 1904

python provenance_lens.py evidence lens.json \
  "The checked 1904 log contains no warning note." \
  --source S001

python provenance_lens.py unit lens.json \
  "The warning note does not appear in the checked 1904 log." \
  --kind direct-support \
  --evidence E001

python provenance_lens.py unit lens.json \
  "The warning note may have entered the story later." \
  --kind inference \
  --basis U001

python provenance_lens.py audit lens.json
python provenance_lens.py render lens.json -o report.md
python provenance_lens.py matrix lens.json -o matrix.md
python provenance_lens.py mermaid lens.json -o lens.mmd
```

## Structural audit

The audit checks whether the visible support structure matches the classification.

It can flag:

- `direct-support` with no evidence link
- `synthesis` with fewer than two recorded bases
- `inference` with no recorded basis
- evidence with no source
- any unit explicitly marked `missing-bridge`

A flag does **not** mean false. It means the bridge is absent, thin, or intentionally unresolved in the current project.

## Outputs

Provenance Lens can produce:

- plain JSON
- a Markdown inspection report
- a classification matrix
- a Mermaid provenance graph
- a structural audit

## Example

The fictional example in [`examples/demo.json`](examples/demo.json) inspects a short paragraph about a warning-note story.

The first two units are directly supported by recorded evidence. A third unit synthesizes them. A fourth is an inference built from those earlier units. A final stronger claim is deliberately marked `missing-bridge`.

See:

- [`examples/demo.md`](examples/demo.md)
- [`examples/demo.mmd`](examples/demo.mmd)

## What Provenance Lens does not do

Provenance Lens does not automatically fact-check a source.

It does not assume direct support means truth.

It does not downgrade synthesis or inference merely because they involve reasoning.

It does not convert a missing bridge into a claim of falsehood.

It keeps the reasoning path visible so the reader can see where evidence ends and interpretation begins.

## Tests

```bash
python -m unittest discover -s tests -v
```

## License and reuse

**No reuse license has been granted.**

This public build is available for inspection and development by its maintainers. Do not assume that public visibility grants permission to copy, redistribute, modify, sell, incorporate, or relicense the code or documentation.

See [`COPYRIGHT.md`](COPYRIGHT.md).

## Working principle

If the sentence crossed a bridge, keep the bridge visible.
