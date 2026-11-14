import unittest
from pagebound.reporting import joined_rows,metrics,validate_execution
from pagebound.identity import ContractError

class ReportingTests(unittest.TestCase):
    def setUp(self):
        self.row={"trial_id":"t1","policy":"native_text","rendering":"scan","question_id":"q1","answerable":True}
        self.plan={"plan_hash":"a"*64,"trials":[self.row]}
        self.actual={**self.row,"plan_hash":"a"*64,"status":"failed","execution_mode":"recorded_model_inference"}
    def test_failure_retained(self):
        m=metrics(joined_rows(self.plan,[self.actual]))
        self.assertEqual(m["grounded_success"],{"numerator":0,"denominator":1,"value":0})
        self.assertIsNone(m["selective_error"]["value"])
    def test_missing_left_join(self):
        self.assertEqual(joined_rows(self.plan,[])[0]["status"],"missing")
    def test_duplicate_mixed_and_forged(self):
        for rows in [[self.actual,self.actual],[{**self.actual,"plan_hash":"b"*64}],[{**self.actual,"rendering":"digital"}],[{**self.actual,"status":"completed"}],[{**self.actual,"execution_mode":"fixture"}]]:
            with self.assertRaises(ContractError): joined_rows(self.plan,rows)
    def test_missing_plan_refuses(self):
        with self.assertRaises(ContractError): joined_rows({},[])
        with self.assertRaises(ContractError): metrics([])
    def test_execution_gate(self):
        r={"component":"vlm_visual","execution_mode":"learned_inference","status":"completed","forward_calls":1,"image_tensor_elements":12,"model_bundle":"a"*64,"input_digest":"b"*64,"output_digest":"c"*64}
        validate_execution(r,"vlm_visual")
        for bad in [{},{**r,"execution_mode":"fixture"},{**r,"image_tensor_elements":0}]:
            with self.assertRaises(ContractError): validate_execution(bad,"vlm_visual")
