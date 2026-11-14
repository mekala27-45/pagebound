import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from pagebound.identity import ContractError,digest,read_json,write_json
from pagebound.reporting import validate_execution

def main():
    corpus=read_json(ROOT/"artifacts/manifests/corpus-freeze.json")
    probes=read_json(ROOT/"artifacts/probes/vlm.json")
    if probes["status"]!="completed":raise ContractError("VLM probe not completed")
    result=probes["result"]
    if result["profile"] not in {"full","compact"}:raise ContractError("No profile fits the compute allowance")
    for t in result["trials"]:validate_execution(t["receipt"],"vlm_visual" if t["policy"]=="visual_grounded" else "vlm_text")
    threshold=read_json(ROOT/"artifacts/manifests/development-threshold.json")
    if threshold.get("split")!="development" or not threshold.get("interior_test"):raise ContractError("Missing development threshold sensitivity evidence")
    plan=read_json(ROOT/"config/evaluation-plan.json")
    plan.update({"status":"frozen","profile":result["profile"],"model_bundle":result["bundle_digest"],"model_revision":result["revision"],"bindings":{"corpus":corpus["digest"],"probe":digest(result),"threshold":digest(threshold)},"evidence_coverage_threshold":threshold["coverage"],"excess_area_threshold":threshold["excess_area"]})
    plan_hash=digest(plan)
    split=read_json(ROOT/"config/split-map.json");questions=read_json(ROOT/"config/questions.json")
    types={"Q6","Q7"} if plan["profile"]=="full" else {"Q6"}
    trials=[]
    for q in sorted(questions,key=lambda q:q["id"]):
        if split[q["packet_id"]]!="heldout" or q["id"].split("-")[-1] not in types:continue
        for rendering in ("digital","scan"):
            for policy in plan["policies"]:trials.append({"trial_id":q["id"]+"-"+rendering+"-"+policy,"question_id":q["id"],"packet_id":q["packet_id"],"rendering":rendering,"policy":policy})
    if len(trials)!=(72 if plan["profile"]=="full" else 36):raise ContractError("Wrong matched denominator")
    write_json(ROOT/"config/evaluation-plan.json",plan)
    write_json(ROOT/"artifacts/manifests/trial-plan.json",{"plan_hash":plan_hash,"profile":plan["profile"],"trials":trials})
if __name__=="__main__":main()
