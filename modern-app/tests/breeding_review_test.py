import asyncio
import copy
import io
import unittest

from openpyxl import load_workbook
from fastapi import HTTPException
from starlette.datastructures import UploadFile

import backend.main as breeding


def complete_pair(male_genotype="+/-", female_genotype="+/-"):
    return [
        {
            "breeder_id": "M1",
            "breeder_name": "Male one",
            "gender": "male",
            "sire_id": "MS1",
            "dam_id": "MD1",
            "cre": male_genotype,
            "reporter": "f/+",
        },
        {
            "breeder_id": "F1",
            "breeder_name": "Female one",
            "gender": "female",
            "sire_id": "FS1",
            "dam_id": "FD1",
            "cre": female_genotype,
            "reporter": "f/+",
        },
    ]


class BreedingReviewTests(unittest.TestCase):
    def review(self, breeders, **overrides):
        settings = {
            "breeders": breeders,
            "desired_genotype": {"cre": "+/-", "reporter": "f/+"},
            "exclude_shared_parent": True,
            "confirm_simple_inheritance": True,
        }
        settings.update(overrides)
        request = breeding.FindPairsRequest(**settings)
        return asyncio.run(breeding.find_pairs(request))

    def test_empty_input_does_not_substitute_example_breeders(self):
        request = breeding.FindPairsRequest(
            breeders=[],
            desired_genotype={"cre": "+/-"},
        )

        with self.assertRaises(HTTPException) as error:
            asyncio.run(breeding.find_pairs(request))

        self.assertEqual(error.exception.status_code, 400)
        self.assertIn("Load breeder records", error.exception.detail)

    def test_inheritance_model_must_be_confirmed_before_showing_locus_probabilities(self):
        results = self.review(complete_pair(), confirm_simple_inheritance=False)
        self.assertEqual(results["direct_pairs"], [])
        self.assertEqual(results["needs_review_pairs"][0]["Locus_Probabilities"], {})
        self.assertIn("Confirm the simple two-allele", results["needs_review_pairs"][0]["Reasons"][0])

    def test_multiple_locus_results_stay_separate_until_assumption_is_confirmed(self):
        separate = self.review(complete_pair())
        pair = separate["direct_pairs"][0]
        self.assertEqual(pair["Locus_Probabilities"], {"cre": 50.0, "reporter": 50.0})
        self.assertIsNone(pair["Probability"])
        self.assertEqual(pair["Ranking_Score"], 50.0)

        combined = self.review(complete_pair(), confirm_independent_assortment=True)
        self.assertEqual(combined["direct_pairs"][0]["Probability"], 25.0)

    def test_missing_genotype_is_held_for_review(self):
        results = self.review(complete_pair(male_genotype=""))
        self.assertEqual(results["direct_pairs"], [])
        self.assertIn("Missing genotypes", results["needs_review_pairs"][0]["Reasons"][0])

    def test_configured_wildtype_requires_explicit_confirmation_and_is_recorded(self):
        original = breeding.gene_db.wildtype_genotype.copy()
        try:
            breeding.gene_db.wildtype_genotype = {"cre": "-/-"}
            without_confirmation = self.review(complete_pair(male_genotype=""))
            self.assertIn("Missing genotypes", without_confirmation["needs_review_pairs"][0]["Reasons"][0])

            confirmed = self.review(complete_pair(male_genotype=""), assume_missing_wildtype=True)
            pair = confirmed["direct_pairs"][0]
            self.assertEqual(pair["Locus_Probabilities"]["cre"], 50.0)
            self.assertIn("blank cre treated as -/-", pair["Assumptions"][0])
        finally:
            breeding.gene_db.wildtype_genotype = original

    def test_known_shared_parent_is_excluded_and_incomplete_parent_ids_need_review(self):
        breeders = complete_pair()
        breeders[0]["sire_id"] = "SHARED"
        breeders[1]["dam_id"] = "SHARED"
        shared = self.review(breeders)
        self.assertEqual(shared["excluded_pairs"][0]["Status"], "Excluded")
        self.assertIn("known shared parent", shared["excluded_pairs"][0]["Reasons"][0])

        incomplete_breeders = complete_pair()
        incomplete_breeders[0].pop("dam_id")
        held = self.review(incomplete_breeders)
        self.assertEqual(held["needs_review_pairs"][0]["Relationship"], "Unresolved")
        allowed = self.review(incomplete_breeders, allow_unknown_relationship=True)
        self.assertEqual(len(allowed["direct_pairs"]), 1)

    def test_researcher_exclusion_is_saved_in_the_review_results(self):
        results = self.review(complete_pair(), excluded_pairs=[["M1", "F1"]])
        self.assertEqual(results["direct_pairs"], [])
        self.assertEqual(results["excluded_pairs"][0]["Reasons"], ["Pair excluded by the researcher."])

    def test_invalid_target_genotype_returns_a_clear_client_error(self):
        request = breeding.FindPairsRequest(
            breeders=complete_pair(),
            desired_genotype={"cre": "+/"},
            exclude_shared_parent=True,
        )
        with self.assertRaises(HTTPException) as error:
            asyncio.run(breeding.find_pairs(request))
        self.assertEqual(error.exception.status_code, 400)

    def test_csv_upload_keeps_parent_id_columns_for_review(self):
        original_database = copy.deepcopy(breeding.gene_db.transgene_db)
        original_reverse = copy.deepcopy(breeding.gene_db.transgene_to_category)
        original_wildtype = copy.deepcopy(breeding.gene_db.wildtype_genotype)
        upload = UploadFile(
            filename="breeders.csv",
            file=io.BytesIO(
                b"breeder_id,breeder_name,gender,sire_id,dam_id,cre\n"
                b"M1,Male one,male,MS1,MD1,+/-\n"
                b"F1,Female one,female,FS1,FD1,+/-\n"
            ),
        )
        original_save = breeding.gene_db.save_database
        breeding.gene_db.save_database = lambda: None
        try:
            result = asyncio.run(breeding.upload_file(upload))
            self.assertEqual(result["breeders"][0]["sire_id"], "MS1")
            self.assertEqual(result["breeders"][1]["dam_id"], "FD1")
        finally:
            breeding.gene_db.transgene_db = original_database
            breeding.gene_db.transgene_to_category = original_reverse
            breeding.gene_db.wildtype_genotype = original_wildtype
            breeding.gene_db.save_database = original_save

    def test_export_uses_the_reviewed_rows_and_includes_the_selected_pair(self):
        results = self.review(complete_pair(), confirm_independent_assortment=True)
        request = breeding.FindPairsRequest(
            breeders=complete_pair(),
            desired_genotype={"cre": "+/-", "reporter": "f/+"},
            reviewed_results=results,
            review_metadata={"selected_pair_id": results["direct_pairs"][0]["Pair_ID"]},
        )
        response = asyncio.run(breeding.export_breeders(request))

        async def read_body():
            return b"".join([chunk async for chunk in response.body_iterator])

        workbook = load_workbook(io.BytesIO(asyncio.run(read_body())), data_only=True)
        self.assertEqual(workbook["Selected pair"].max_row, 2)
        self.assertEqual(workbook["Direct"].max_row, 2)
        self.assertEqual(workbook["Review"]["B5"].value, results["direct_pairs"][0]["Pair_ID"])

    def test_export_rejects_a_selected_pair_that_cannot_produce_the_target(self):
        results = copy.deepcopy(self.review(complete_pair()))
        indirect_pair = results["direct_pairs"].pop(0)
        results["indirect_pairs"].append(indirect_pair)
        request = breeding.FindPairsRequest(
            breeders=complete_pair(),
            desired_genotype={"cre": "+/-", "reporter": "f/+"},
            reviewed_results=results,
            review_metadata={"selected_pair_id": indirect_pair["Pair_ID"]},
        )

        with self.assertRaises(HTTPException) as error:
            asyncio.run(breeding.export_breeders(request))

        self.assertEqual(error.exception.status_code, 400)
        self.assertIn("can produce the target", error.exception.detail)

    def test_export_requires_a_reason_for_a_lower_ranked_eligible_pair(self):
        breeders = complete_pair()
        alternative = copy.deepcopy(breeders[0])
        alternative["breeder_id"] = "M2"
        alternative["breeder_name"] = "Male two"
        breeders.append(alternative)
        results = self.review(breeders, desired_genotype={"cre": "+/-"})
        self.assertEqual(len(results["direct_pairs"]), 2)
        request = breeding.FindPairsRequest(
            breeders=breeders,
            desired_genotype={"cre": "+/-"},
            reviewed_results=results,
            review_metadata={"selected_pair_id": results["direct_pairs"][1]["Pair_ID"]},
        )

        with self.assertRaises(HTTPException) as error:
            asyncio.run(breeding.export_breeders(request))

        self.assertEqual(error.exception.status_code, 400)
        self.assertIn("Add a reason", error.exception.detail)

    def test_export_keeps_formula_like_breeder_text_as_literal(self):
        breeders = complete_pair()
        breeders[0]["breeder_name"] = "=1+1"
        results = self.review(breeders)
        request = breeding.FindPairsRequest(
            breeders=breeders,
            desired_genotype={"cre": "+/-", "reporter": "f/+"},
            reviewed_results=results,
        )
        response = asyncio.run(breeding.export_breeders(request))

        async def read_body():
            return b"".join([chunk async for chunk in response.body_iterator])

        workbook = load_workbook(io.BytesIO(asyncio.run(read_body())), data_only=False)
        self.assertEqual(workbook["Breeder inputs"]["B2"].value, "=1+1")
        self.assertEqual(workbook["Breeder inputs"]["B2"].data_type, "s")
        formula_cells = [
            f"{worksheet.title}!{cell.coordinate}"
            for worksheet in workbook.worksheets
            for row in worksheet.iter_rows()
            for cell in row
            if cell.data_type == "f"
        ]
        self.assertEqual(formula_cells, [])


if __name__ == "__main__":
    unittest.main()
