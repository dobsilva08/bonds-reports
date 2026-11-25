import unittest
import pandas as pd
from scripts.bonds.analytics_engine import curve_metrics
from scripts.bonds.report_engine import build_daily_report
from scripts.bonds.macro_engine import macro_context

class ProfessionalReportTests(unittest.TestCase):
    def test_report_and_context(self):
        data={
          "US2Y":pd.DataFrame({"date":pd.date_range("2026-01-01",periods=65),"yield_pct":[4.0+i*.001 for i in range(65)]}),
          "US10Y":pd.DataFrame({"date":pd.date_range("2026-01-01",periods=65),"yield_pct":[4.5+i*.002 for i in range(65)]}),
          "US30Y":pd.DataFrame({"date":pd.date_range("2026-01-01",periods=65),"yield_pct":[5.0+i*.003 for i in range(65)]})}
        metrics=curve_metrics(data)
        report=build_daily_report(metrics)
        context=macro_context(metrics)
        self.assertIn("US TREASURY",report)
        self.assertIn("MARKET SNAPSHOT",report)
        self.assertIn("MARKET INTERPRETATION",report)
        self.assertIn("ANALYTICAL LIMITS",report)
        self.assertIn("Inclinação",context)
        self.assertIn("Curvatura",context)
if __name__=="__main__": unittest.main()
