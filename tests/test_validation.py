import unittest
import pandas as pd
from scripts.bonds.validation import validate_frame

class ValidationTests(unittest.TestCase):
    def test_duplicates_fail(self):
        frame=pd.DataFrame({"date":["2026-01-01","2026-01-01"],"yield_pct":[4.0,4.1]})
        with self.assertRaises(ValueError): validate_frame(frame,"TEST")
if __name__=="__main__": unittest.main()
