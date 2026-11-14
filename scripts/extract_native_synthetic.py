import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from pagebound.identity import read_json,write_json,digest
from pagebound.extraction.native import extract_page

if __name__=="__main__":
    packets={p["id"]:p for p in read_json(ROOT/"artifacts/manifests/synthetic-packets.json")}
    renders=read_json(ROOT/"artifacts/public-small/render-manifest.json")["pages"]
    rows=[];pages=[]
    for r in renders:
        if r["rendering"]=="scan":path=ROOT/"artifacts/public-small/pages"/(r["id"]+".pdf");idx=0
        else:path=ROOT/packets[r["packet_id"]]["pdf_path"];idx=r["physical_page_index"]
        result=extract_page(path,idx,r);rows.extend(result);pages.append({"rendering_id":r["id"],"region_count":len(result),"execution_mode":"native_extraction"})
    write_json(ROOT/"artifacts/public-small/extraction.json",{"regions":rows,"pages":pages,"digest":digest(rows),"mode":"native_only"})
    print(json.dumps({"pages":len(pages),"regions":len(rows),"scans_with_native_text":sum(p["region_count"]>0 for p in pages if p["rendering_id"].endswith("scan"))}))
