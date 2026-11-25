import json, tempfile, unittest
from pathlib import Path
from unittest.mock import patch
import update

class SeparateMMSStatus(unittest.TestCase):
    def run_update(self, answers):
        with tempfile.TemporaryDirectory() as folder:
            root=Path(folder)
            (root/'data.json').write_text(json.dumps({'storm':{'name':'Tropical Disturbance (B03)','observed':'yesterday','lat':-10,'lon':77},'history':[]}))
            with patch.object(update,'ROOT',root), patch.object(update,'retrieve',side_effect=answers):
                update.update()
            return json.loads((root/'data.json').read_text())
    def test_empty_storm_page_keeps_verified_warning_separate(self):
        data=self.run_update(['No warning reported',ValueError('current-cyclone.php: Official bulletin body unavailable (title exists, content empty)')])
        self.assertEqual(data['source_status'],'incomplete')
        self.assertEqual(data['warning_status'],'retrieved')
        self.assertEqual(data['storm_status'],'empty_page')
        self.assertEqual(data['warning'],'No warning reported')
        self.assertIsNone(data['storm'])
        self.assertTrue(data['errors'])
    def test_warning_error_does_not_certify_no_warning(self):
        data=self.run_update([ValueError('MMS warning unavailable'),None])
        self.assertEqual(data['warning_status'],'unverified')
        self.assertEqual(data['storm_status'],'explicit_none')
        self.assertEqual(data['source_status'],'incomplete')
        self.assertTrue(data['warning'].startswith('Unknown'))
    def test_explicit_no_storm_and_verified_warning(self):
        data=self.run_update(['No warning reported',None])
        self.assertEqual(data['source_status'],'ok')
        self.assertEqual(data['storm_status'],'explicit_none')
        self.assertEqual(data['errors'],[])
    def test_unverified_storm_not_reused(self):
        data=self.run_update(['Class II',ValueError('page changed')])
        self.assertIsNone(data['storm'])
        self.assertEqual(data['storm_status'],'unverified')
        self.assertEqual(data['source_status'],'incomplete')
    def test_sources_are_official_https(self):
        data=self.run_update(['No warning reported',None])
        self.assertEqual(data['storm_source'],'https://metservice.intnet.mu/current-cyclone.php')
        self.assertEqual(data['warning_source'],'https://metservice.intnet.mu/tropical-cyclone/current-cyclone.php')

if __name__=='__main__': unittest.main()
