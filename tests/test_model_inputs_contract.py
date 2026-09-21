from pathlib import Path
import sys,unittest,itertools
import numpy as np,pandas as pd
R=Path(__file__).resolve().parents[1];sys.path.insert(0,str(R/'analysis'));sys.path.insert(0,str(R/'tools'))
from national_metrics import peak,factorial,contrast,FACTORS
from gamma_metrics import slope
from verify_model_inputs import THERMAL_COLUMNS
class ModelInputContract(unittest.TestCase):
 def test_lp_constructor_formula(self):
  s=(R/'model/pcv3_build_lp.m').read_text();self.assertIn('cfg.annualDeficitPremium',s);self.assertIn('model.objcon=0',s);self.assertIn('cfg.drFraction',s)
 def test_no_bundled_fixed_reference_dependency(self):
  s=(R/'model/run_public_case.m').read_text();self.assertNotIn('data/gamma',s);self.assertIn('FixedReferenceDir',s);self.assertIn('read_fixed_reference',s)
 def test_fixed_reference_definition(self):
  s=(R/'model/read_fixed_reference.m').read_text();self.assertIn('sum(U.quota_t_per_mwh.*g)',s);self.assertIn('r.gamma==1',s);self.assertIn('RUN_COMPLETE.json',s)
 def test_no_private_input_columns(self):
  self.assertFalse(set(THERMAL_COLUMNS)&{'name','plant_name','longitude','latitude','lon','lat','generation_mwh','fixed_allowance_t'})
 def test_peak_classification(self):
  years=np.arange(2020,2036);e=np.r_[np.arange(10,21),[19,18,17,16,15]]*1e6
  r=peak(pd.DataFrame({'year':years,'emissions_t':e}));self.assertTrue(r['agreed_peak_success']);self.assertEqual(r['peak_year'],2030)
 def test_nonpeaking_path(self):
  self.assertFalse(peak(pd.DataFrame({'year':range(2020,2036),'emissions_t':np.arange(16)*1e6+1}))['agreed_peak_success'])
 def test_factorial_exact_synthetic(self):
  x=list(itertools.product(range(2),range(3),range(2),range(6),range(2),range(2)))
  d=pd.DataFrame(x,columns=FACTORS);d['z']=d.RE*2.+d.CF+3*d.CAP
  r=factorial(d,'z');self.assertAlmostEqual(sum(y['variance_share'] for y in r),1);self.assertEqual(len(r),63)
 def test_no_plotting_runtime(self):
  req=(R/'requirements.txt').read_text().lower();self.assertNotIn('matplotlib',req);self.assertNotIn('pymupdf',req)
 def test_existing_slope_function(self):
  self.assertEqual(slope([2020,2021,2022],[3,5,7]),2)
if __name__=='__main__':unittest.main()
