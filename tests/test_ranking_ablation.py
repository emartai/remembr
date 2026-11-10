"""Ranking receives no gold labels; selection must respect quality/token gates."""

import unittest
import random
from unittest.mock import patch

from benchmarks.ranking_ablation import (
    choose,
    pack,
)
from server.app.ranking import diversify, fuse, lexical_scores, rank, rank_order
from server.app import ranking


class RankingTests(unittest.TestCase):
    def test_fusion_deduplicates_each_list_and_prefers_shared_result(self):
        order, scores = fuse([[0, 0, 1], [1, 2]])
        self.assertEqual(order[0], 1)
        self.assertAlmostEqual(scores[0], 1 / 61)

    def test_absent_lexical_terms_do_not_create_arbitrary_keyword_candidates(self):
        self.assertEqual(lexical_scores("unmentioned", ["database", "memory"]), [0, 0])

    def test_complete_turns_only_within_context_budget(self):
        text, visible = pack(["D1:1 A: full\nD1:2 B: cut off"], [0], 20)
        self.assertLessEqual(len(text), 20)
        self.assertEqual(visible, {"D1:1"})

    def test_diversity_can_choose_complementary_source_over_duplicate(self):
        selected = diversify([0, 1, 2], [1, 0.99, 0.95], [[1, 0], [1, 0], [0, 1]], 2)
        self.assertEqual(selected, [0, 2])

    def test_ranking_is_deterministic_and_has_unique_bounded_results(self):
        args = ("database", ["database", "other"], [1, 0], [[1, 0], [0, 1]])
        self.assertEqual(rank(*args), rank(*args))
        for indices in rank(*args).values():
            self.assertEqual(len(indices), len(set(indices)))
            self.assertTrue(all(0 <= i < 2 for i in indices))

    def test_selector_rejects_multi_hop_regression_overall_regression_and_token_inflation(
        self,
    ):
        baseline = dict(
            recall=0.6, multi_hop_recall=0.4, all_evidence=0.3, mean_context_tokens=100
        )
        for candidate in (
            dict(
                recall=0.7,
                multi_hop_recall=0.3,
                all_evidence=0.4,
                mean_context_tokens=100,
            ),
            dict(
                recall=0.5,
                multi_hop_recall=0.5,
                all_evidence=0.4,
                mean_context_tokens=100,
            ),
            dict(
                recall=0.7,
                multi_hop_recall=0.5,
                all_evidence=0.4,
                mean_context_tokens=120,
            ),
        ):
            self.assertEqual(
                choose({"cosine_8": baseline, "rrf_8": candidate}), "cosine_8"
            )

    def test_api_full_order_has_exactly_the_evaluated_first_page(self):
        documents = ["database choice " + str(i) for i in range(50)]
        vectors = [[1.0, i / 50] for i in range(50)]
        args = ("database", documents, [1.0, 0.5], vectors)
        order = rank_order(*args)
        self.assertEqual(order[:8], rank(*args)["rrf_mmr_compact_8"])
        self.assertEqual(sorted(order), list(range(50)))
        self.assertEqual(rank_order("q", [], [1.0], []), [])

    def test_incremental_diversity_matches_reference_with_negative_similarities(self):
        rng = random.Random(42)
        vectors = [[rng.uniform(-1, 1) for _ in range(8)] for _ in range(40)]
        order = list(range(40))
        rng.shuffle(order)
        relevance = [rng.random() for _ in order]

        def reference(limit, weight):
            chosen = []
            remaining = list(order)
            maximum = max(relevance) or 1
            while remaining and len(chosen) < limit:

                def score(index):
                    redundancy = max(
                        (ranking.cosine(vectors[index], vectors[j]) for j in chosen),
                        default=0,
                    )
                    return (
                        weight * relevance[index] / maximum - (1 - weight) * redundancy
                    )

                best = max(remaining, key=lambda i: (score(i), -i))
                chosen.append(best)
                remaining.remove(best)
            return chosen

        for limit in (0, 1, 8, 40):
            for weight in (0, 0.5, 0.85, 1):
                self.assertEqual(
                    diversify(order, relevance, vectors, limit, weight),
                    reference(limit, weight),
                )

    def test_full_diversity_evaluates_each_remaining_pair_only_once(self):
        vectors = [[1.0, i / 40] for i in range(40)]
        with patch("server.app.ranking.cosine", wraps=ranking.cosine) as similarity:
            diversify(list(range(40)), [1.0] * 40, vectors, 40)
        self.assertLessEqual(similarity.call_count, 40 * 39 // 2)


if __name__ == "__main__":
    unittest.main()
