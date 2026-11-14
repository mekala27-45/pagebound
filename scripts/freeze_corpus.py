import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from pagebound.identity import ContractError,digest,file_digest,read_json,write_json

def freeze():
    paths=["config/sources.lock","config/packet-selection.json","config/questions.json","config/split-map.json","evaluator/annotations/public-gold.json","evaluator/annotations/synthetic-gold.json","artifacts/manifests/synthetic-packets.json","artifacts/public-small/render-manifest.json"]
    missing=[p for p in paths if not (ROOT/p).is_file()]
    if missing:raise ContractError("Cannot freeze: missing "+", ".join(missing))
    selected=read_json(ROOT/paths[1]);seen=set()
    if len(selected)!=6:raise ContractError("Public packet inventory incomplete")
    for packet in selected:
        if packet.get("rights_decision")!="approved" or not packet.get("notice") or not packet.get("visual_annotation_review"):raise ContractError("Missing rights or visible-source review")
        for page in packet["page_indices"]:
            key=(packet["source_id"],page)
            if key in seen:raise ContractError("Public page reused across packets")
            seen.add(key)
    split=read_json(ROOT/"config/split-map.json")
    if len(split)!=12 or set(split.values())!={"development","heldout"}:raise ContractError("Incomplete lineage split")
    if list(split.values()).count("development")!=6:raise ContractError("Unexpected split inventory")
    questions=read_json(ROOT/"config/questions.json")
    if len(questions)!=96 or len({q["id"] for q in questions})!=96:raise ContractError("Question inventory incomplete")
    renders=read_json(ROOT/"artifacts/public-small/render-manifest.json")["pages"]
    if len(renders)!=48 or any(r.get("scan_text_characters") for r in renders if r["rendering"]=="scan"):raise ContractError("Render inventory or scan isolation failed")
    binding={p:file_digest(ROOT/p) for p in paths}
    write_json(ROOT/"artifacts/manifests/corpus-freeze.json",{"status":"frozen","bindings":binding,"digest":digest(binding)})
if __name__=="__main__":freeze()
