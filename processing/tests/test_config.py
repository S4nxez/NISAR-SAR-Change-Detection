import os
import unittest

from lifeline.config import PROCESSING_DIR, SCHEMA_VERSION, STATUS, STATUS_NAME, areas_dir, data_dir


class TestFolders(unittest.TestCase):
    def test_defaults_are_inside_the_source_checkout(self):
        self.assertTrue(os.path.isfile(os.path.join(PROCESSING_DIR, "pyproject.toml")))
        self.assertEqual(areas_dir({}), os.path.join(PROCESSING_DIR, "areas"))
        self.assertEqual(data_dir({}), os.path.join(PROCESSING_DIR, "output"))

    def test_environment_variables_win(self):
        env = {"MONITOR_AREAS_DIR": "/app/areas", "MONITOR_DATA_DIR": "/data/monitor"}
        self.assertEqual(areas_dir(env), "/app/areas")
        self.assertEqual(data_dir(env), "/data/monitor")

    def test_an_empty_variable_falls_back_to_the_default(self):
        self.assertEqual(data_dir({"MONITOR_DATA_DIR": ""}), os.path.join(PROCESSING_DIR, "output"))


class TestContract(unittest.TestCase):
    def test_status_codes_are_a_two_way_table(self):
        self.assertEqual(STATUS, {"no_data": 0, "connected": 1, "at_risk": 2, "isolated": 3})
        self.assertEqual({STATUS[name]: name for name in STATUS}, STATUS_NAME)

    def test_schema_version_matches_the_backend(self):
        # the backend refuses catalogs of another version: both sides must change together
        java = os.path.join(PROCESSING_DIR, "..", "server", "src", "main", "java", "com", "nisarsar", "domain",
                            "services", "MonitorRecordService.java")
        with open(java, encoding="utf-8") as f:
            self.assertIn(f"SCHEMA_VERSION = {SCHEMA_VERSION};", f.read())


if __name__ == "__main__":
    unittest.main()
