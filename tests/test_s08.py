import copy
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from types import SimpleNamespace

from citybrain.planner.route_scorer import RouteScorer
from experiments.runners.compare import ROOT, initial_result
from experiments.runners.s08_audit import ScoreRecorder, S08Audit, decision_reason, encode_evidence, validate_evidence
from experiments.runners.s08_validation import committed_revision, expected_keys, strict_json, validate_checkpoint, validate_complete


class S08Tests(unittest.TestCase):
    def test_matrix_has_exactly_60_unique_trials(self):
        definition=strict_json(ROOT/'experiments/configs/s08-validation.json')
        keys=expected_keys(definition)
        self.assertEqual(len(keys),60)
        rows=[initial_result(scenario,strategy,seed,profile) for scenario,profile,seed,strategy in keys]
        validate_complete(rows,definition)
        with self.assertRaises(ValueError):validate_complete(rows[:-1],definition)
        with self.assertRaises(ValueError):validate_complete(rows+[rows[0]],definition)

    def test_clean_revision_rejects_tracked_and_untracked_changes(self):
        with tempfile.TemporaryDirectory() as temp:
            root=Path(temp)
            def git(*args):return subprocess.check_output(['git',*args],cwd=root,stderr=subprocess.DEVNULL,text=True)
            git('init');git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','--allow-empty','-m','init')
            self.assertEqual(committed_revision(root),git('rev-parse','HEAD').strip())
            (root/'file').write_text('changed')
            with self.assertRaises(ValueError):committed_revision(root)
            git('add','file');git('-c','user.name=Test','-c','user.email=test@example.invalid','commit','-m','file')
            (root/'file').write_text('modified')
            with self.assertRaises(ValueError):committed_revision(root)

    def test_scorer_records_real_calls_without_changing_values(self):
        scorer=RouteScorer();recorded=ScoreRecorder(scorer)
        state={'roads':{'a':{'travel_time':10,'congestion':'MEDIUM','blocked':False}}}
        self.assertEqual(recorded.calculate_score(['a'],state),scorer.calculate_score(['a'],state))
        self.assertEqual(recorded.records,[{'route':['a'],'score':15,'valid':True}])

    def test_environment_changes_latch_each_declared_edge_once(self):
        audit=S08Audit()
        roads={e:{'travel_time':10,'blocked':False} for e in ('E7','E11')}
        self.assertEqual(audit.observe_changes(301,roads),[])
        roads['E7']['travel_time']=14
        self.assertEqual(audit.observe_changes(305,roads),[])
        roads['E7']['travel_time']=16
        first=audit.observe_changes(308,roads)
        self.assertEqual(first[0]['edge'],'E7')
        roads['E11']['blocked']=True
        second=audit.observe_changes(318,roads)
        self.assertEqual(second[0]['change_ordinal'],2)
        self.assertEqual(audit.observe_changes(320,roads),[])

    def test_static_cannot_claim_replanning(self):
        row=initial_result('S08','static',1,'normal')
        row['replan_checks']=1
        with self.assertRaises(ValueError):validate_checkpoint(row,('S08','normal',1,'static'))
        with self.assertRaises(ValueError):validate_evidence(row,[])

    def test_two_successive_applications_require_matching_sumo_suffixes(self):
        row=initial_result('S08','dynamic',1,'normal')
        row.update(replan_checks=2,successful_route_changes=2,number_of_replans=2,candidate_evaluations=2)
        events=[]
        for now,edge,target in [(311,'E5','E19'),(321,'E19','E27')]:
            events.append(dict(kind='EVALUATION',time=now,decision='APPLY',gate_passed=True,
                candidate_route=[edge,target],physical_edge=edge,distance_travelled_m=100,
                observed_roads={e:{'blocked':False} for e in (edge,target)},current_route_invalid=False,
                predicted_benefit=20,threshold_seconds=5,candidate_evaluations=[{'route':[edge,target]}],
                application={'time':now,'route_after':['E13',edge,target], 'route_index_after':1,
                             'remaining_route_after':[edge,target]}))
        validate_evidence(row,events)
        infinite=copy.deepcopy(events)
        infinite[0].update(old_eta=float('inf'),candidate_eta=20,
                           predicted_benefit=float('inf'),threshold_seconds=float('inf'))
        with tempfile.TemporaryDirectory() as temporary:
            from experiments.runners.storage import write_json
            path=Path(temporary)/'events.json'
            write_json(path,encode_evidence(infinite))
            restored=strict_json(path)
            self.assertEqual(restored[0]['old_eta'],'Infinity')
            validate_evidence(row,restored)
            restored[0]['old_eta']=30
            with self.assertRaises(ValueError):validate_evidence(row,restored)
        events[1]['application']['remaining_route_after']=['wrong']
        with self.assertRaises(ValueError):validate_evidence(row,events)

    def test_evidence_distinguishes_infinite_cost_from_missing_value(self):
        self.assertEqual(encode_evidence({'cost':float('inf'),'missing':None}),
                         {'cost':'Infinity','missing':None})
        with self.assertRaises(ValueError):encode_evidence(float('nan'))

    def test_keep_reasons_are_specific(self):
        candidate=SimpleNamespace(route=['a','b'])
        self.assertEqual(decision_reason(candidate,['a','c'],False,20,5,2),'minimum_commitment_not_elapsed')
        self.assertEqual(decision_reason(candidate,['a','c'],False,1,5,12),'predicted_benefit_below_threshold')
        self.assertEqual(decision_reason(None,['a'],True,None,5,12),'no_valid_reachable_candidate')

    def test_malformed_checkpoints_and_nonfinite_json_rejected(self):
        row=initial_result('S08','static',1,'normal');row['completed']='False'
        with self.assertRaises(ValueError):validate_checkpoint(row,('S08','normal',1,'static'))
        with tempfile.TemporaryDirectory() as temp:
            path=Path(temp)/'result.json'
            for text in ('{"x":NaN}','{"x":1,"x":2}'):
                path.write_text(text)
                with self.assertRaises(ValueError):strict_json(path)

    def test_official_resume_retains_all_60_checkpoints_without_reruns(self):
        from unittest.mock import patch
        from experiments.runners.s08_validation import run
        from experiments.runners.storage import write_json
        with tempfile.TemporaryDirectory() as temporary:
            output=Path(temporary)/'official'
            def fake_trial(scenario,strategy,seed,profile,directory,**kwargs):
                row=initial_result(scenario,strategy,seed,profile)
                write_json(directory/'events.json',[])
                write_json(directory/'result.json',row)
                return row
            with patch('experiments.runners.s08_validation.committed_revision',return_value='test-revision'), patch('experiments.runners.s08_validation.trial',side_effect=fake_trial) as runner:
                run(output);self.assertEqual(runner.call_count,60)
                from experiments.analysis.s08 import audit
                audited, _, _ = audit(output)
                self.assertEqual(len(audited),60)
                mtimes={p:p.stat().st_mtime_ns for p in output.glob('*/result.json')}
                runner.reset_mock();run(output,resume=True);runner.assert_not_called()
                self.assertEqual(mtimes,{p:p.stat().st_mtime_ns for p in mtimes})
                aggregate=(output/'results.csv').read_bytes()
                route=output/'S08_peak_10_dynamic/routes.rou.xml';route.write_text(route.read_text()+'\n')
                with self.assertRaises(ValueError):run(output,resume=True)
                runner.assert_not_called()
                self.assertEqual((output/'results.csv').read_bytes(),aggregate)
