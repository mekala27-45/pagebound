import json
import unittest
from pagebound.gates import parse_answer,arithmetic,runtime_gates
from pagebound.identity import ContractError

class GateTests(unittest.TestCase):
    def test_schema(self):
        good={"disposition":"answer","atoms":[{"type":"number","value":"12","unit":"kPa","evidence_ids":["r1"]}],"evidence_ids":["r1"]}
        self.assertEqual(parse_answer(json.dumps(good),{"r1"}),good)
        for raw in ["", "null", "{}",json.dumps({**good,"evidence_ids":["unseen"]})]:
            with self.assertRaises(ContractError):parse_answer(raw,{"r1"})
    def test_unit_aware_arithmetic(self):
        op=[{"op":"subtract","left":"a","right":"b"}]
        self.assertEqual(arithmetic(op,{"a":{"value":"0.3","unit":"kPa"},"b":{"value":"0.1","unit":"kPa"}})["value"],"0.2")
        for operands in [{},{"a":{"value":2,"unit":"Pa"},"b":{"value":1,"unit":"kPa"}}]:
            with self.assertRaises(ContractError):arithmetic(op,operands)
        with self.assertRaises(ContractError):arithmetic([{"op":"divide","left":"a","right":"b"}],{"a":{"value":1,"unit":"Pa"},"b":{"value":0,"unit":"Pa"}})
    def test_no_dynamic_execution(self):
        with self.assertRaises(ContractError):arithmetic([{"op":"eval","left":"a","right":"b"}],{"a":{"value":1,"unit":"1"},"b":{"value":1,"unit":"1"}})
    def test_valid_geometry_does_not_grade_semantics(self):
        evidence=[{"id":"r1","polygon":[[0,0],[10,0],[10,10],[0,10]],"image_width":10,"image_height":10}]
        a=json.dumps({"disposition":"answer","atoms":[{"type":"text","value":"wrong answer","evidence_ids":["r1"]}],"evidence_ids":["r1"]})
        _,g=runtime_gates(a,evidence)
        self.assertTrue(g["geometry"]);self.assertEqual(g["semantic_support"],"not_evaluated")
