import unittest
from pagebound.admission import validate_request
from pagebound.identity import ContractError

class AdmissionTests(unittest.TestCase):
    def setUp(self):
        self.m={"status":"frozen","pages":[{"id":"s1-scan","page_id":"s1","sha256":"a"*64,"width":1000,"height":1000}]}
        self.p={"page_id":"s1","rendering_id":"s1-scan","render_digest":"a"*64,"bounds":[.1,.1,.2,.2],"idempotency_key":"key1"}
    def test_good_and_identity(self):
        a=validate_request(self.p,self.m)
        self.assertEqual(a[1],[100,100,200,200])
        self.assertEqual(a[2],validate_request({**self.p,"idempotency_key":"key2"},self.m)[2])
        self.assertNotEqual(a[2],validate_request({**self.p,"bounds":[.1,.1,.3,.3]},self.m)[2])
    def test_refuse_unknown_stale_missing_excessive(self):
        for p in [{},{**self.p,"url":"https://example.com"},{**self.p,"page_id":"../secret"},{**self.p,"render_digest":"b"*64},{**self.p,"bounds":[0,0,1,1]}]:
            with self.assertRaises(ContractError):validate_request(p,self.m)
    def test_unready_fails_closed(self):
        with self.assertRaises(ContractError):validate_request(self.p,{"status":"planned"})
