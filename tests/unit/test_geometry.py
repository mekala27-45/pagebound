import sys
import unittest
from pathlib import Path
sys.path.insert(0,str(Path(__file__).resolve().parents[2]/"src"))
from pagebound.geometry import Affine, validate_polygon, pixel_crop, bind_overlay
from pagebound.identity import ContractError

class GeometryTests(unittest.TestCase):
    def test_nonzero_pdf_crop_bottom_left(self):
        native=Affine("pdf","canonical",1,0,0,-1,-20,740)
        raster=Affine("canonical","raster",2,0,0,2)
        self.assertEqual(native.then(raster).point([30,730]),[20,20])
        self.assertEqual(native.then(raster).inverse().point([20,20]),[30,730])

    def test_quarter_turn_landmarks(self):
        rot90=Affine("page","rotated",0,1,-1,0,200,0)
        rot270=Affine("page","rotated",0,-1,1,0,0,100)
        self.assertEqual(rot90.point([10,20]),[180,10])
        self.assertEqual(rot270.point([10,20]),[20,90])

    def test_crop_offset_resize_and_browser(self):
        uncrop=Affine("ocr","raster",2,0,0,2,30,40)
        browser=Affine("raster","browser",0.25,0,0,0.25)
        self.assertEqual(uncrop.then(browser).point([5,10]),[10,15])

    def test_invalid_spaces_and_singular(self):
        with self.assertRaises(ContractError): Affine("a","b",0,0,0,0)
        with self.assertRaises(ContractError): Affine("a","b").then(Affine("c","d"))

    def test_boundary_and_crop_budget(self):
        self.assertEqual(pixel_crop([0.5,0.5,1,1],800,1000),[400,500,800,1000])
        with self.assertRaises(ContractError): pixel_crop([0,0,1,1],800,1000)

    def test_refuse_reordered_missing_nonfinite_outside(self):
        for points in [[],[[0,0],[10,10],[10,0],[0,10]],[[0,0],[float("nan"),2],[1,1]],[[0,0],[11,0],[10,10]]]:
            with self.assertRaises(ContractError): validate_polygon(points,10,10)
        with self.assertRaises(ContractError): validate_polygon([[0,0],[1,0],[1,1]],0,10)

    def test_digest_binding(self):
        e={"render_digest":"a"*64,"polygon":[[0,0],[10,0],[10,10],[0,10]]}
        self.assertEqual(len(bind_overlay(e,{"sha256":"a"*64,"width":10,"height":10})),4)
        with self.assertRaises(ContractError): bind_overlay(e,{"sha256":"b"*64,"width":10,"height":10})

if __name__ == "__main__": unittest.main()
