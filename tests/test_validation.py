import copy
import json
from pathlib import Path
import tempfile
import unittest
import xml.etree.ElementTree as ET
from experiments.runners.compare import initial_result, ROOT
from experiments.runners.storage import validate_row, validate_pairs, write_csv, write_json

class ValidationTests(unittest.TestCase):
    def test_failure_cannot_have_arrival(self):
        row = initial_result('S05','static',1,'normal')
        row['ambulance_arrival_time'] = 600
        with self.assertRaises(ValueError): validate_row(row)

    def test_pairing_requires_both_strategies_without_duplicates(self):
        row = initial_result('S05','static',1,'normal')
        with self.assertRaises(ValueError): validate_pairs([row])
        with self.assertRaises(ValueError): validate_pairs([row,row])
        other = dict(row, strategy='dynamic')
        validate_pairs([row,other])
        row.update(initial_route='E5 E7',initial_eta=20)
        other.update(initial_route='E5 E19',initial_eta=20)
        with self.assertRaises(ValueError): validate_pairs([row,other])

    def test_strict_json_and_atomic_csv(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'events.json'
            write_json(path,{'eta':float('inf')})
            self.assertIsNone(json.loads(path.read_text())['eta'])
            output=Path(directory)/'results.csv'
            write_csv(output,[initial_result('S05','static',1,'normal')])
            self.assertNotIn(b'\r',output.read_bytes())
            self.assertFalse(output.with_suffix('.csv.tmp').exists())

    def test_s06_cut_and_research_bypass(self):
        def reachable(network):
            edges=ET.parse(ROOT/f'simulation/network/{network}/city.edg.xml').getroot()
            neighbors={}
            for edge in edges:
                if edge.get('id') not in {'E3','E7','E11'}:
                    neighbors.setdefault(edge.get('from'),[]).append(edge.get('to'))
            seen={'J1'};todo=['J1']
            while todo:
                for node in neighbors.get(todo.pop(),[]):
                    if node not in seen:seen.add(node);todo.append(node)
            return 'J9' in seen
        self.assertFalse(reachable('regression'))
        self.assertTrue(reachable('research'))

    def test_research_candidate_is_connected(self):
        edges={e.get('id'):e for e in ET.parse(ROOT/'simulation/network/research/city.edg.xml').getroot()}
        route=['E13','E5','E19','E27','E33','E30']
        for left,right in zip(route,route[1:]):
            self.assertEqual(edges[left].get('to'),edges[right].get('from'))
        self.assertEqual(edges[route[-1]].get('to'),'J9')

    def test_resume_skips_completed_trials_and_rejects_changed_inputs(self):
        import sys
        from unittest.mock import patch
        from experiments.runners.compare import main
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)/'suite'
            args=['compare','--scenarios','S05','--seeds','1','--output',str(directory)]
            def fake_trial(scenario,strategy,seed,profile,path,**kwargs):
                path.mkdir(parents=True)
                row=initial_result(scenario,strategy,seed,profile)
                write_json(path/'result.json',row)
                return row
            with patch.object(sys,'argv',args), patch('experiments.runners.compare.trial',side_effect=fake_trial) as runner:
                main();self.assertEqual(runner.call_count,2)
            with patch.object(sys,'argv',args+['--resume']), patch('experiments.runners.compare.trial') as runner:
                main();runner.assert_not_called()
            manifest=directory/'manifest.json'
            data=json.loads(manifest.read_text());data['signature']['input_sha256']='changed';write_json(manifest,data)
            with patch.object(sys,'argv',args+['--resume']), self.assertRaises(SystemExit):
                main()

    def test_error_trial_is_retained_with_no_fabricated_metrics(self):
        import sys
        from unittest.mock import patch
        from experiments.runners.compare import main
        with tempfile.TemporaryDirectory() as temporary:
            directory=Path(temporary)/'suite'
            args=['compare','--scenarios','S05','--seeds','1','--output',str(directory)]
            with patch.object(sys,'argv',args), patch('experiments.runners.compare.trial',side_effect=RuntimeError('test failure')):
                main()
            row=json.loads((directory/'S05_normal_1_static/result.json').read_text())
            self.assertEqual(row['completion_status'],'ERROR')
            self.assertEqual(row['actual_travel_time'],'')
            self.assertEqual(row['normal_traffic_time_loss'],'')
