import unittest
from update import section, warning, storm, retrieve

def page(title, body):
    return ("<html><nav><a>Current Cyclone</a><a>Current Storm/Cyclone</a></nav>"
            "<main><h2>"+title+"</h2>"+body+"</main>"
            "<aside><h2>Weather</h2><p>Sidebar</p></aside></html>")

class MMSParser(unittest.TestCase):
    def test_explicit_warning(self):
        self.assertEqual(warning(page('Current Cyclone',
            '<p>No cyclone warning is in force in Mauritius.</p>')), 'No warning reported')
    def test_explicit_class(self):
        self.assertEqual(warning(page('Current Cyclone',
            '<p>Cyclone warning class II is in force in Mauritius.</p>')), 'Class II')
    def test_observation(self):
        html=page('Current Storm/Cyclone',
            '<div><h3>Current tropical system</h3><p>Tropical Disturbance (B03)</p>'
            '<p>Date and Time 24 November 2026 04 PM</p>'
            '<p>Position 10.4 S, 77.5 E</p><p>Estimated Central Pressure 1006 hPa</p></div>')
        s=storm(html)
        self.assertEqual(s['name'], 'Tropical Disturbance (B03)')
        self.assertEqual((s['lat'],s['lon']),(-10.4,77.5))
    def test_navigation_not_body(self):
        with self.assertRaises(ValueError):
            section('<nav><a>Current Storm/Cyclone</a></nav><h2>Weather</h2>', 'Current Storm/Cyclone')
    def test_heading_only_rejected(self):
        with self.assertRaises(ValueError):
            storm(page('Current Storm/Cyclone',''))
    def test_missing_warning_rejected(self):
        with self.assertRaises(ValueError):
            retrieve('current-cyclone.php',warning,lambda _:page('Current Cyclone','<p>Unknown</p>'),lambda _:None)
    def test_heading_changed_rejected(self):
        with self.assertRaises(ValueError):
            section(page('Different heading','<p>Tropical Disturbance (B03)</p>'),'Current Storm/Cyclone')

if __name__=='__main__': unittest.main()
