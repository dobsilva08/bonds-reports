import unittest
import pandas as pd
from scripts.bonds.analytics_engine import curve_metrics

class AnalyticsTests(unittest.TestCase):
    def test_spreads_and_butterfly(self):
        data={
          "US2Y":pd.DataFrame({"date":["2025-01-01","2025-01-02"],"yield_pct":[4.0,4.1]}),
          "US10Y":pd.DataFrame({"date":["2025-01-01","2025-01-02"],"yield_pct":[4.5,4.4]}),
          "US30Y":pd.DataFrame({"date":["2025-01-01","2025-01-02"],"yield_pct":[5.0,5.1]})}
        out=curve_metrics(data)
        self.assertAlmostEqual(out.iloc[-1]["10Y-2Y"],0.3)
        self.assertAlmostEqual(out.iloc[-1]["butterfly"],0.4)
if __name__=="__main__": unittest.main()
