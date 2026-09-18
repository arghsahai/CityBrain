import tempfile
import unittest
from pathlib import Path
import xml.etree.ElementTree as ET
from experiments.outcomes import classify_step
from experiments.runners.compare import prepare_config

class ExperimentTests(unittest.TestCase):
    def test_teleport_overrides_arrival(self):
        self.assertEqual(classify_step('a', [], ['a'], ['a']), 'TELEPORTED')
        self.assertEqual(classify_step('a', [], ['a'], [], True), 'TELEPORTED')

    def test_disappearance_is_failure(self):
        self.assertEqual(classify_step('a', [], [], []), 'FAILED_BLOCKED')
        self.assertEqual(classify_step('a', [], ['a'], []), 'SUCCESS')
        self.assertIsNone(classify_step('a', ['a'], [], []))

    def test_configs_and_resources(self):
        with tempfile.TemporaryDirectory() as temp:
            for scenario in ('S01','S02','S03','S04','S05','S06','S07'):
                config = prepare_config(Path(temp)/scenario, scenario, 'normal')
                inputs = ET.parse(config).getroot().find('input')
                self.assertTrue(Path(inputs.find('net-file').get('value')).is_file())
                routes = ET.parse(config.parent/'routes.rou.xml').getroot()
                if scenario != 'S01':
                    self.assertIsNotNone(routes.find("vehicle[@id='ambulance0']"))
                    self.assertIsNotNone(routes.find("vehicle[@id='accident_blocker']"))
                if scenario in ('S04','S05','S06'):
                    self.assertIsNotNone(routes.find("vehicle[@id='dynamic_blocker']"))

    def test_summary_excludes_failed_and_teleported_arrivals(self):
        import csv
        from experiments.analysis.summarize import summarize
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp)/'results.csv'
            fields = ['scenario','profile','strategy','completion_status','completed','teleported','actual_travel_time','eta_error']
            with path.open('w', newline='') as stream:
                writer = csv.DictWriter(stream, fieldnames=fields)
                writer.writeheader()
                for status, completed, teleported, travel in [('SUCCESS','True','False',20), ('TELEPORTED','False','True',600), ('TIMEOUT','False','False',900)]:
                    writer.writerow(dict(zip(fields,['S05','normal','static',status,completed,teleported,travel,2])))
            text = summarize(path).read_text()
            self.assertIn('| 3 | 1 | 1 | 20.00 |', text)

    def test_departure_order(self):
        with tempfile.TemporaryDirectory() as temp:
            for scenario in ('S04','S06','S07'):
                config = prepare_config(Path(temp)/scenario, scenario, 'normal')
                records = [e for e in ET.parse(config.parent/'routes.rou.xml').getroot() if e.tag in ('flow','vehicle')]
                times = [float(e.get('begin', e.get('depart','0'))) for e in records]
                self.assertEqual(times, sorted(times))
