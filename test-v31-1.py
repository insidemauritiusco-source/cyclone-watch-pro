import datetime as dt, unittest
from update import retrieve,warning,storm
from broadcast_gate import current
class Reliability(unittest.TestCase):
    def test_retry_parser(self):
        good='<h2>Current Cyclone</h2><p>No cyclone warning is in force in Mauritius</p><h2>Weather</h2>'
        pages=iter(['<html>Unavailable</html>',good]); delays=[]
        self.assertEqual(retrieve('test',warning,lambda _:next(pages),delays.append),'No warning reported')
        self.assertEqual(delays,[2])
    def test_retry_bounded(self):
        calls=[]; delays=[]
        def bad(p):
            calls.append(p)
            raise OSError('fixture unavailable')
        with self.assertRaises(ValueError): retrieve('test',warning,bad,delays.append)
        self.assertEqual(len(calls),3)
        self.assertEqual(delays,[2,4])
    def test_unverified_warning(self):
        with self.assertRaises(ValueError):
            retrieve('test',warning,lambda _: '<h2>Current Cyclone</h2><p>unknown</p><h2>Weather</h2>',lambda _:None)
    def test_gate(self):
        now=dt.datetime.now(dt.timezone.utc)
        d=dict(checked_at=now.isoformat(),source_status='ok',errors=[],warning='No warning reported',storm=None)
        self.assertTrue(current(d,now))
        for bad in [dict(d,source_status='incomplete'),dict(d,errors=['missing body']),dict(d,warning='Unknown'),dict(d,checked_at=(now-dt.timedelta(hours=1)).isoformat()),dict(d,storm=dict(lat=40,lon=70,name='test',observed='dated'))]:
            self.assertFalse(current(bad,now))
    def test_workflow_order(self):
        from pathlib import Path
        s=Path('.github/workflows/video.yml').read_text()
        self.assertLess(s.index('blocked immediately before rendering'),s.index('          python video.py'))
        self.assertLess(s.index('post-render official freshness recheck'),s.index('node v31-review.cjs draft'))
        self.assertLess(s.index('node v31-review.cjs draft'),s.index('actions/upload-artifact'))
if __name__=='__main__': unittest.main()
