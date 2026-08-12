from __future__ import annotations

import unittest

from app.core.query_generator import generate_role_queries


class QueryGeneratorTests(unittest.TestCase):
    def test_qa_role_expands_to_german_and_english_variants(self) -> None:
        variants = generate_role_queries(("QA Engineer",), max_variants_per_role=20)

        self.assertIn("test automation engineer", variants)
        self.assertIn("softwaretester", variants)
        self.assertIn("sdet", variants)
        self.assertEqual(len(variants), len(set(value.casefold() for value in variants)))

    def test_unknown_role_is_preserved(self) -> None:
        self.assertEqual(generate_role_queries(("Rocket Wrangler",)), ("Rocket Wrangler",))

    def test_many_explicit_roles_are_never_dropped_by_alias_limit(self) -> None:
        roles = tuple(f"Custom role {number}" for number in range(30))

        self.assertEqual(generate_role_queries(roles, max_total=24), roles)


if __name__ == "__main__":
    unittest.main()
