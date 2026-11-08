import unittest
from unittest import mock

import river_monitor


@mock.patch("river_monitor.load_area", return_value={"id": "tefe"})
@mock.patch("river_monitor.pipeline")
class TestCommandLine(unittest.TestCase):
    def test_update_with_options(self, pipeline, load_area):
        river_monitor.main(["update", "--area", "x", "--workers", "4", "--limit", "3", "--redo"])
        load_area.assert_called_once_with("x")
        pipeline.update.assert_called_once_with({"id": "tefe"}, 4, 3, True)

    def test_default_area_and_other_commands(self, pipeline, load_area):
        river_monitor.main(["communities"])
        river_monitor.main(["reevaluate"])
        river_monitor.main(["watch", "--hours", "1.5"])
        load_area.assert_called_with("tefe")
        pipeline.communities.assert_called_once_with({"id": "tefe"})
        pipeline.reevaluate.assert_called_once_with({"id": "tefe"})
        pipeline.watch.assert_called_once_with({"id": "tefe"}, 1.5, 2)

    def test_unknown_command_is_rejected(self, pipeline, load_area):
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            river_monitor.main(["download"])
        load_area.assert_not_called()


if __name__ == "__main__":
    unittest.main()
