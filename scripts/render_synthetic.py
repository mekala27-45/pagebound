import sys,json
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from pagebound.identity import read_json,write_json
from pagebound.rendering import render_packets
if __name__=="__main__":
    result=render_packets(read_json(ROOT/"artifacts/manifests/synthetic-packets.json"),ROOT,ROOT/"artifacts/public-small/pages")
    write_json(ROOT/"artifacts/public-small/render-manifest.json",result)
    print(json.dumps({"renderings":len(result["pages"]),"digest":result["render_manifest_digest"]}))
