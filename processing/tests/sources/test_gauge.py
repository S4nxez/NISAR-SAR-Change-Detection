import datetime as dt
import unittest
from unittest import mock

import requests

from lifeline.sources.gauge import level_on, parse_gauge, refresh_gauge

from ..helpers import FakeResponse


def ana_xml(rows):
    body = "".join(f"<DadosHidrometereologicos><DataHora>{d}</DataHora><Nivel>{n}</Nivel></DadosHidrometereologicos>"
                   for d, n in rows)
    return f'<DataSet xmlns="http://MRCS/"><diffgram><DocumentElement>{body}</DocumentElement></diffgram></DataSet>'.encode()


AREA = {"gauge": {"name": "Tefé-Missões (Solimões)", "ana_code": "12900001"}}


class TestParseGauge(unittest.TestCase):
    def test_daily_median_and_empty_levels_skipped(self):
        xml = ana_xml([("2026-10-23 07:00:00", "800.00"), ("2026-10-23 08:00:00", "802.00"),
                       ("2026-10-23 09:00:00", "900.00"), ("2026-10-24 07:00:00", ""),
                       ("2026-10-25 07:00:00", "790.00")])
        self.assertEqual(parse_gauge(xml), {"2026-10-23": 802.0, "2026-10-25": 790.0})

    def test_no_rows(self):
        self.assertEqual(parse_gauge(ana_xml([])), {})


@mock.patch("lifeline.sources.gauge.log")
class TestRefreshGauge(unittest.TestCase):
    def cat(self):
        return {"passes": [{"date": "2026-10-23"}, {"date": "2026-07-07"}],
                "gauge": {"name": "old", "series": [["2026-01-01", 1.0]]}}

    def test_series_requested_from_before_the_first_pass_and_stored(self, _log):
        seen = {}

        def get(url, params, timeout, headers):
            seen.update(params)
            return FakeResponse(content=ana_xml([("2026-10-23 07:00:00", "801.04")]))

        cat = self.cat()
        refresh_gauge(AREA, cat, get=get, today=dt.date(2026, 11, 8))
        self.assertEqual(seen, {"codEstacao": "12900001", "dataInicio": "22/06/2026", "dataFim": "08/11/2026"})
        self.assertEqual(cat["gauge"]["series"], [["2026-10-23", 801.0]])
        self.assertEqual(cat["gauge"]["source"], "ANA telemetry, station 12900001")

    def test_failures_keep_the_previous_series(self, _log):
        for answer in (FakeResponse(500), FakeResponse(content=b"<html>maintenance"),
                       FakeResponse(content=ana_xml([("2026-10-23 07:00:00", "n/a")]))):
            cat = self.cat()
            refresh_gauge(AREA, cat, get=lambda *a, answer=answer, **k: answer)
            self.assertEqual(cat["gauge"]["name"], "old")

    def test_network_error_keeps_the_previous_series(self, _log):
        def get(*a, **k):
            raise requests.ConnectionError("down")
        cat = self.cat()
        refresh_gauge(AREA, cat, get=get)
        self.assertEqual(cat["gauge"]["name"], "old")

    def test_new_passes_extend_the_series_back(self, _log):
        seen = {}

        def get(url, params, timeout, headers):
            seen.update(params)
            return FakeResponse(content=ana_xml([("2025-11-04 07:00:00", "1105.5")]))
        cat = {"passes": []}
        refresh_gauge(AREA, cat, get=get, today=dt.date(2026, 11, 8), dates=["2025-11-04"])
        self.assertEqual(seen["dataInicio"], "20/10/2025")
        self.assertEqual(cat["gauge"]["series"], [["2025-11-04", 1105.5]])

    def test_nothing_to_do_without_gauge_or_passes(self, _log):
        get = mock.Mock()
        refresh_gauge({}, self.cat(), get=get)
        refresh_gauge(AREA, {"passes": []}, get=get)
        get.assert_not_called()


class TestLevelOn(unittest.TestCase):
    def test_the_day_else_the_closest_within_max_days(self):
        series = [["2026-08-30", 900.0], ["2026-09-01", 880.0]]
        self.assertEqual(level_on(series, "2026-08-30"), 900.0)
        self.assertIn(level_on(series, "2026-08-31"), (900.0, 880.0))
        self.assertIsNone(level_on(series, "2026-09-05"))
        self.assertEqual(level_on(series, "2026-09-05", max_days=4), 880.0)
        self.assertIsNone(level_on(None, "2026-08-30"))


if __name__ == "__main__":
    unittest.main()
