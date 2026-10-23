import unittest

from hunter import classify, config
from hunter.accreditation import _match, normalise

ME = config.PROFILES["abhishek"]
WIFE = config.PROFILES["wife"]


def job(title="Senior DevOps Engineer", company="Xero", work_type="Full time", **kw):
    return {"id": "t:1", "source": "Seek", "title": title, "company": company,
            "advertiser": company, "work_type": work_type, "teaser": "", **kw}


ACC = {"status": "accredited", "expiry": "2099-01-01"}
NOT_LISTED = {"status": "not_listed"}


class TitleFit(unittest.TestCase):
    def test_core_titles(self):
        for t in ["Senior DevOps Engineer", "Site Reliability Engineer", "SRE Lead", "Platform Engineer",
                  "Cloud Engineer - AWS", "Forward Deployed Engineer", "AI Platform Engineer",
                  "Software Specialist (Developer Platforms)", "Kubernetes Engineer"]:
            self.assertEqual(classify.title_fit(t, ME), "core", t)

    def test_power_and_plant_titles_out_of_scope(self):
        for t in ["Power Platform Engineer", "Senior Power Systems Engineer", "SCADA Engineer",
                  "Automation and Control Systems Engineer", "Protection Engineer"]:
            self.assertIsNone(classify.title_fit(t, ME), t)

    def test_loose_title_needs_it_context(self):
        j = job(title="Systems Engineer")
        classify.analyse(j, "Maintain our electricity distribution network assets and substations.", ACC)
        self.assertNotIn("abhishek", j["for"])
        k = job(title="Systems Engineer")
        classify.analyse(k, "Run our AWS cloud and Linux servers; IT systems, DevOps tooling.", ACC)
        self.assertIn("abhishek", k["for"])

    def test_out_of_scope(self):
        for t in [".Net Developer", "Graduate DevOps Engineer", "DevOps Intern", "Account Manager - Cloud",
                  "Senior API Developer", "Registered Nurse", "ITSM Platform Specialist",
                  "DevOps Product Manager", "DevOps Engineer - Mandarin Speaking"]:
            self.assertIsNone(classify.title_fit(t, ME), t)


class WifeProfile(unittest.TestCase):
    def test_ict_pm_titles(self):
        for t in ["IT Project Manager", "Senior Project Manager", "Delivery Manager - Digital",
                  "Technical Program Manager", "Scrum Master", "Programme Manager, Cloud Migration"]:
            self.assertEqual(classify.title_fit(t, WIFE), "core", t)

    def test_ba_and_product_titles(self):
        for t in ["Business Analyst", "Senior Business Analyst - Digital", "Product Manager", "Product Owner",
                  "Technical Product Manager"]:
            self.assertEqual(classify.title_fit(t, WIFE), "core", t)
        for t in ["Product Marketing Manager", "Financial Business Analyst", "Credit Business Analyst"]:
            self.assertIsNone(classify.title_fit(t, WIFE), t)

    def test_visa_route(self):
        pm = job(title="IT Project Manager", seek_class=["6281"])
        ba = job(title="Business Analyst", seek_class=["6281"])
        classify.analyse(pm, "", ACC)
        classify.analyse(ba, "", ACC)
        self.assertEqual(pm["for"]["wife"]["route"], "iswv")
        self.assertEqual(ba["for"]["wife"]["route"], "aewv")

    def test_non_it_pm_titles(self):
        for t in ["Construction Project Manager", "Project Manager - Civil and Land Development",
                  "Marketing Project Manager", "Project Coordinator", "Fit-out Project Manager"]:
            self.assertIsNone(classify.title_fit(t, WIFE), t)

    def test_generic_pm_needs_an_it_context(self):
        j = job(title="Project Manager", company="Xero")
        classify.analyse(j, "Deliver our ERP and cloud data platform migration using agile.", ACC)
        self.assertIn("wife", j["for"])
        self.assertNotIn("abhishek", j["for"])
        k = job(title="Project Manager", company="Xero")
        classify.analyse(k, "Run our new warehouse fit and staff rosters.", ACC)
        self.assertEqual(k["for"], {})

    def test_roading_and_engineering_pm_rejected(self):
        for desc in [
            "Senior Project Manager with strong experience in road stabilisation. Lead crews across the "
            "region on infrastructure programmes; use our application to apply.",
            "At Jacobs we deliver infrastructure for thriving cities, with digital tools and data. "
            "Lead multi-disciplinary engineering projects.",
        ]:
            j = job(title="Senior Project Manager", company="Higgins")
            classify.analyse(j, desc, ACC)
            self.assertNotIn("wife", j["for"], desc[:40])

    def test_seek_ict_category_counts_as_it(self):
        j = job(title="Senior Project Manager", seek_class=["6281"])
        classify.analyse(j, "Lead a team.", ACC)
        self.assertIn("wife", j["for"])

    def test_each_person_has_own_score(self):
        j = job(title="DevOps Engineer")
        classify.analyse(j, "AWS Terraform Kubernetes", ACC)
        self.assertEqual(list(j["for"]), ["abhishek"])


class VisaReady(unittest.TestCase):
    def analyse(self, desc, acc=ACC, **kw):
        return classify.analyse(job(**kw), desc, acc)

    def test_accredited_clean_ad_is_emailed(self):
        j = self.analyse("We run AWS EKS with Terraform and ArgoCD.")
        self.assertTrue(j["visa_ready"])
        self.assertIn("terraform", j["for"]["abhishek"]["skills"])

    def test_not_listed_employer_is_not_emailed(self):
        self.assertFalse(self.analyse("Great team, AWS.", acc=NOT_LISTED)["visa_ready"])

    def test_not_listed_but_offers_sponsorship_is_emailed(self):
        j = self.analyse("Visa sponsorship is available for the right candidate.", acc=NOT_LISTED)
        self.assertTrue(j["visa_ready"])

    def test_no_sponsorship_blocks(self):
        for text in ["We are unable to offer visa sponsorship.", "We cannot sponsor visas for this role.",
                     "Open to NZ citizens or residents only.", "Applicants must be able to work without sponsorship.",
                     "This role requires a security clearance."]:
            j = self.analyse(text)
            self.assertEqual(j["tier"], "blocked", text)
            self.assertFalse(j["visa_ready"], text)

    def test_right_to_work_boilerplate_is_held_back_not_blocked(self):
        j = self.analyse("You must have the right to work in New Zealand.")
        self.assertNotEqual(j["tier"], "blocked")
        self.assertFalse(j["visa_ready"])

    def test_residency_pathway_is_not_a_blocker(self):
        j = self.analyse("This role offers a pathway to residency and relocation support.")
        self.assertEqual(j["hard_blockers"], [])
        self.assertTrue(j["visa_ready"])

    def test_agency_accreditation_does_not_count(self):
        j = self.analyse("Our client runs AWS.", company="Robert Half")
        self.assertTrue(j["recruiter"])
        self.assertFalse(j["visa_ready"])

    def test_part_time_is_not_emailed(self):
        self.assertFalse(self.analyse("AWS", work_type="Part time")["visa_ready"])


class EmployerMatch(unittest.TestCase):
    ROWS = [
        {"employerName": "BANK OF NEW ZEALAND", "tradingName": "Bank of New Zealand"},
        {"employerName": "Reserve Bank of New Zealand", "tradingName": "Reserve Bank of New Zealand"},
        {"employerName": "XERO LIMITED", "tradingName": "Xero"},
    ]

    def test_alias_and_suffixes(self):
        self.assertEqual(_match("BNZ", self.ROWS)["employerName"], "BANK OF NEW ZEALAND")
        self.assertEqual(_match("Xero Ltd", self.ROWS)["employerName"], "XERO LIMITED")

    def test_no_false_match(self):
        self.assertIsNone(_match("Pulse Energy Alliance LP", self.ROWS))

    def test_normalise(self):
        self.assertEqual(normalise("Datacom Group Ltd (NZ)"), "datacom")


if __name__ == "__main__":
    unittest.main()
