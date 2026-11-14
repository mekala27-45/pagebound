import unittest
from evaluator.scoring import semantic,polygon_area,intersect,score,paired_cluster_interval

class EvaluatorTests(unittest.TestCase):
    def test_units_and_missing(self):
        g={"disposition":"answer","atoms":[{"type":"number","value":"12","unit":"kPa"}]}
        self.assertTrue(semantic({"disposition":"answer","atoms":[{"type":"number","value":12,"unit":"kPa"}]},g))
        self.assertFalse(semantic({"disposition":"answer","atoms":[{"type":"number","value":12,"unit":"Pa"}]},g))
        self.assertFalse(semantic(None,g))
    def test_independent_intersection(self):
        a=[[0,0],[10,0],[10,10],[0,10]];b=[[5,5],[15,5],[15,15],[5,15]]
        self.assertEqual(polygon_area(intersect(a,b)),25)
    def test_valid_box_wrong_answer_and_broad_crop(self):
        g={"disposition":"answer","atoms":[{"type":"text","value":"correct"}],"required_pages":["p"],"evidence":[{"page_id":"p","canonical_box":[0,0,10,10]}]}
        r={"h":{"page_id":"p","transform":{"a":1,"b":0,"c":0,"d":1,"e":0,"f":0}}}
        c=[{"id":"c","page_id":"p","render_digest":"h","polygon":[[0,0],[100,0],[100,100],[0,100]]}]
        a={"disposition":"answer","atoms":[{"type":"text","value":"correct"}],"evidence_ids":["c"]}
        out=score(a,g,c,r,.5,4)
        self.assertTrue(out["answer_correct"]);self.assertFalse(out["grounded_correct"])
        a["atoms"][0]["value"]="wrong";c[0]["polygon"]=[[0,0],[10,0],[10,10],[0,10]]
        out=score(a,g,c,r,.5,4)
        self.assertTrue(out["spatial_support"]);self.assertFalse(out["answer_correct"])
    def test_matched_clusters(self):
        rows=[{"packet_id":"p","question_id":"q","rendering":"scan","policy":p,"grounded_correct":v} for p,v in [("a",1),("b",0)]]
        self.assertEqual(paired_cluster_interval(rows,"a","b",samples=20)["difference"],1)
        with self.assertRaises(ValueError):paired_cluster_interval(rows[:1],"a","b")
