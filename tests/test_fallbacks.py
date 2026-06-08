import unittest

from car_advisor import CarListing, build_advisor_recommendation


class AdvisorFallbackTests(unittest.TestCase):
    def test_returns_exact_requested_model_within_budget(self):
        inventory = [
            CarListing(make="Hyundai", model="i20", price=490000, lead_id="i20-low"),
            CarListing(make="Maruti", model="Baleno", price=460000, lead_id="baleno"),
        ]

        result = build_advisor_recommendation(
            inventory,
            requested_model="i20",
            max_budget=5,
        )

        self.assertEqual(result.status, "exact_match")
        self.assertEqual([car.lead_id for car in result.exact_matches], ["i20-low"])
        self.assertEqual(result.similar_options, ())

    def test_mentions_starting_price_and_similar_options_when_model_above_budget(self):
        inventory = [
            CarListing(make="Hyundai", model="i20", price=625000, lead_id="i20-high"),
            CarListing(make="Maruti", model="Baleno", price=480000, lead_id="baleno"),
            CarListing(make="Tata", model="Altroz", price=495000, lead_id="altroz"),
            CarListing(make="Maruti", model="Swift", price=520000, lead_id="swift-high"),
        ]

        result = build_advisor_recommendation(
            inventory,
            requested_model="i20",
            max_budget=500000,
        )

        self.assertEqual(result.status, "over_budget_with_similar")
        self.assertEqual(result.requested_starting_price, 625000)
        self.assertEqual([car.lead_id for car in result.similar_options], ["baleno", "altroz"])
        self.assertIn("i20 is unavailable in the user's budget", result.message)
        self.assertIn("i20 starts from 6.25 lakh", result.message)
        self.assertIn("Baleno, Altroz", result.message)

    def test_suggests_segment_options_when_requested_model_is_missing(self):
        inventory = [
            {"make": "Maruti", "model": "Baleno", "price": 470000, "id": "baleno"},
            {"make": "Tata", "model": "Altroz", "price": 490000, "id": "altroz"},
            {"make": "Toyota", "model": "Glanza", "price": 510000, "id": "glanza-high"},
        ]

        result = build_advisor_recommendation(
            inventory,
            requested_model="i20",
            max_budget=5,
        )

        self.assertEqual(result.status, "unavailable_with_similar")
        self.assertEqual([car.lead_id for car in result.similar_options], ["baleno", "altroz"])
        self.assertIn("Currently i20 is unavailable", result.message)
        self.assertIn("Baleno, Altroz", result.message)

    def test_uses_aliases_for_requested_model_and_alternatives(self):
        inventory = [
            CarListing(make="Hyundai", model="Elite i20", price=510000, lead_id="elite"),
            CarListing(make="Toyota", model="Glanza", price=490000, lead_id="glanza"),
        ]

        result = build_advisor_recommendation(
            inventory,
            requested_model="new-i20",
            max_budget=5,
        )

        self.assertEqual(result.status, "over_budget_with_similar")
        self.assertEqual(result.requested_starting_price, 510000)
        self.assertEqual([car.lead_id for car in result.similar_options], ["glanza"])


if __name__ == "__main__":
    unittest.main()
