import unittest
from pagebound.identity import ContractError
from pagebound.retrieval import RegionIndex,evidence_text,choose_crops

def row(i,text):return {"id":i,"packet_id":"S1","rendering":"scan","text":text}

class RetrievalTests(unittest.TestCase):
    def test_stable_packet_ranking(self):
        rows=[row("b","pressure 12 kPa"),row("a","pressure 12 kPa"),row("c","speed 4 m/s")]
        ix=RegionIndex(rows,"S1","scan","e")
        self.assertEqual([r["id"] for r in ix.search("pressure")],["a","b"])
        self.assertEqual(evidence_text(ix.search("pressure")),evidence_text(RegionIndex(list(reversed(rows)),"S1","scan","e").search("pressure")))
    def test_gold_and_counterpart_refused(self):
        for bad in [{**row("a","x"),"gold":{}},{**row("a","x"),"rendering":"digital"},{**row("a","x"),"packet_id":"S2"}]:
            with self.assertRaises(ContractError):RegionIndex([bad],"S1","scan","e")
    def test_empty_and_unknown_tokens(self):
        ix=RegionIndex([],"S1","scan","e")
        self.assertEqual(ix.search("pressure"),[])
        with self.assertRaises(ContractError):ix.search("")
    def test_fallback_has_no_gold(self):
        a={"id":"page-S1","page_id":"S1-p1","sha256":"a"*64,"width":100,"height":200}
        self.assertEqual(choose_crops([],a)[0]["bounds"],[0,0,100,200])
