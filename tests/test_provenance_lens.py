import tempfile
import unittest
from pathlib import Path

from provenance_lens import (
    add_evidence, add_source, add_unit, audit, load, new_project,
    render_markdown, render_matrix, render_mermaid, save,
)


class ProvenanceLensTests(unittest.TestCase):
    def test_direct_support_has_explicit_evidence(self):
        data = new_project("Lens")
        sid = add_source(data, "1904 log", "primary", "1904")
        eid = add_evidence(data, "The log contains no warning note.", [sid])
        uid = add_unit(data, "The warning note does not appear in the checked 1904 log.", "direct-support", [eid])
        self.assertEqual(uid, "U001")
        self.assertEqual(audit(data), [])

    def test_synthesis_requires_multiple_bases_for_clean_audit(self):
        data = new_project("Synthesis")
        e1 = add_evidence(data, "Early source lacks the detail.")
        add_unit(data, "The detail appears later.", "synthesis", [e1])
        self.assertTrue(any("fewer than two" in x for x in audit(data)))

    def test_inference_can_use_prior_units_as_basis(self):
        data = new_project("Inference")
        sid = add_source(data, "Source", "primary")
        e1 = add_evidence(data, "Early source lacks the warning.", [sid])
        e2 = add_evidence(data, "Later source includes the warning.", [sid])
        u1 = add_unit(data, "The checked early source lacks the warning.", "direct-support", [e1])
        u2 = add_unit(data, "A later source includes the warning.", "direct-support", [e2])
        add_unit(data, "The warning may have entered the tradition later.", "inference", basis_units=[u1, u2])
        self.assertEqual(audit(data), [])

    def test_missing_bridge_is_explicitly_visible(self):
        data = new_project("Gap")
        add_unit(data, "The witness must have fabricated the story.", "missing-bridge")
        self.assertTrue(any("explicitly marked missing-bridge" in x for x in audit(data)))

    def test_round_trip_and_renderers(self):
        data = new_project("Render", "A short finished passage.")
        sid = add_source(data, "Archive record", "primary")
        eid = add_evidence(data, "Archive supports the date.", [sid])
        add_unit(data, "The event occurred in 1904.", "direct-support", [eid])
        with tempfile.TemporaryDirectory() as td:
            p = Path(td) / "lens.json"; save(p, data); loaded = load(p)
        self.assertIn("direct-support", render_markdown(loaded))
        self.assertIn("direct-support", render_matrix(loaded))
        self.assertIn("supports", render_mermaid(loaded))


if __name__ == "__main__":
    unittest.main()
