import runpy
import unittest
from unittest import mock

from lifeline import cli


@mock.patch("lifeline.cli.load_area", return_value={"id": "tefe"})
@mock.patch("lifeline.cli.pipeline")
class TestCommandLine(unittest.TestCase):
    def test_update_with_options(self, pipeline, load_area):
        cli.main(["update", "--area", "x", "--workers", "4", "--limit", "3", "--redo"])
        load_area.assert_called_once_with("x")
        pipeline.update.assert_called_once_with({"id": "tefe"}, 4, 3, True)

    def test_default_area_and_other_commands(self, pipeline, load_area):
        cli.main(["communities"])
        cli.main(["occurrence"])
        cli.main(["reevaluate"])
        cli.main(["watch", "--hours", "1.5"])
        load_area.assert_called_with("tefe")
        pipeline.communities.assert_called_once_with({"id": "tefe"})
        pipeline.occurrence.assert_called_once_with({"id": "tefe"})
        pipeline.reevaluate.assert_called_once_with({"id": "tefe"})
        pipeline.watch.assert_called_once_with({"id": "tefe"}, 1.5, 2)

    def test_benchmark_needs_a_safe_label(self, pipeline, load_area):
        for argv in (["benchmark"], ["benchmark", "--label", "../x"]):
            with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
                cli.main(argv)
        load_area.assert_not_called()

    def test_benchmark_needs_the_cache_and_runs_the_exam(self, pipeline, load_area):
        a = cli.parse_args(["benchmark", "--label", "m4", "--workers", "3", "--skip-real"])
        with self.assertRaises(SystemExit):
            cli.benchmark({"id": "tefe"}, a, environ={})
        with mock.patch("lifeline.benchmark.exam.run", return_value=({"ok": 1}, "j", "m")) as run, \
                mock.patch("lifeline.cli.config.log"):
            self.assertEqual(cli.benchmark({"id": "tefe"}, a, environ={"MONITOR_CACHE_DIR": "/c"}), {"ok": 1})
        run.assert_called_once_with({"id": "tefe"}, "m4", "/c", 3, skip_real=True)

    def test_unknown_command_is_rejected(self, pipeline, load_area):
        with mock.patch("sys.stderr"), self.assertRaises(SystemExit):
            cli.main(["download"])
        load_area.assert_not_called()

    def test_python_dash_m_lifeline_runs_the_same_command_line(self, pipeline, load_area):
        with mock.patch("sys.argv", ["lifeline", "reevaluate", "--area", "y"]):
            runpy.run_module("lifeline", run_name="__main__")
        load_area.assert_called_once_with("y")
        pipeline.reevaluate.assert_called_once_with({"id": "tefe"})


if __name__ == "__main__":
    unittest.main()
