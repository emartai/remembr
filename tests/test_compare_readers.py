import unittest

from benchmarks.compare_readers import result_for


class ReaderComparisonTests(unittest.TestCase):
    def test_citation_must_appear_on_a_visible_source_line(self):
        context = "Session header\nD1:1 Agent: D2:2 is mentioned here."
        self.assertTrue(result_for('{"answer":"A","citations":["D1:1"]}', context)[3])
        self.assertFalse(result_for('{"answer":"A","citations":["D2:2"]}', context)[3])

    def test_abstention_requires_no_citations(self):
        reason = '{"answer":"No information available.","citations":[]}'
        self.assertEqual(result_for(reason, "")[2:], (True, True))
        reason = '{"answer":"No information available","citations":["D1:1"]}'
        self.assertEqual(result_for(reason, "D1:1 Agent: detail")[2:], (True, False))

    def test_last_line_at_truncation_boundary_is_not_valid_evidence(self):
        context = "D1:1 Agent: complete.\nD1:2 Agent: " + "x" * 4000
        self.assertFalse(result_for('{"answer":"A","citations":["D1:2"]}', context)[3])
