"""Validate the structured ReAct boundary without hosted calls or code execution."""
import json
import unittest
from unittest.mock import patch
from src.master import parse,validate,snapshot
from src.simulation import Harbour,Ship

def wire(action='assign_workers("B2", 4)',**overrides):
    data={'Thought':'Allocate workers to cargo.','Action':action,'Final Report':'B2: ship=3 cargo=9'}
    data.update(overrides)
    return json.dumps(data)

def state():
    h=Harbour(1,'utility')
    h.ships=[Ship(3,0,9,'B2',0)]
    h.berths['B2']=3
    return snapshot(h)

class ProtocolTests(unittest.TestCase):
    def test_json_react_round_trip(self):
        actions,final=parse(wire())
        self.assertEqual(actions,[('assign_workers',['B2',4])])
        self.assertEqual(final,'B2: ship=3 cargo=9')
        validate(actions,state())

    def test_json_fields_must_be_exact_strings(self):
        cases=[
            {'Thought':'Decision','Action':'warn_storm()'},
            {'Thought':'Decision','Action':'warn_storm()','Final Report':'x','approval':True},
            {'Thought':'Decision','Action':['warn_storm()'],'Final Report':'x'},
            {'Thought':None,'Action':'warn_storm()','Final Report':'x'},
            {'Thought':'Decision','Action':'warn_storm()','Final Report':7},
            {'Thought':'Decision\nInvented extra turn','Action':'warn_storm()','Final Report':'x'},
            {'Action':'warn_storm()','Thought':'Decision','Final Report':'x'},
        ]
        for case in cases:
            with self.subTest(case=case),self.assertRaises(ValueError):
                parse(json.dumps(case))

    def test_duplicate_json_fields_are_rejected(self):
        with self.assertRaises(ValueError):
            parse('{"Thought":"one","Thought":"two","Action":"close_harbour()","Final Report":"x"}')

    def test_json_cannot_hide_unknown_or_excessive_actions(self):
        actions,_=parse(wire('erase_harbour()'))
        with self.assertRaises(ValueError): validate(actions,state())
        with self.assertRaises(ValueError): parse(wire(';'.join(['close_harbour()']*4)))
        actions,_=parse(wire(';'.join(['assign_workers("B2", 5)']*3)))
        with self.assertRaises(ValueError): validate(actions,state())

    def test_json_payload_is_never_evaluated(self):
        with patch('os.system') as system:
            for action in ['__import__("os").system("echo danger")',
                           'assign_workers("B2", (lambda: 4)())']:
                with self.subTest(action=action),self.assertRaises(ValueError): parse(wire(action))
            system.assert_not_called()

    def test_legacy_react_remains_parseable_for_inspection(self):
        actions,final=parse('Thought: Allocate cargo.\nAction: assign_workers("B2", 4)\nFinal Report: B2: ship=3 cargo=9')
        validate(actions,state())
        self.assertEqual(final,'B2: ship=3 cargo=9')

if __name__=='__main__': unittest.main()
