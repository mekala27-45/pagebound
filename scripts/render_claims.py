"""Render all result numbers from evidence, never from narrative input."""
import json
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from pagebound.identity import read_json,write_json
from pagebound.reporting import joined_rows,metrics

LABELS=[
"Candidate environments, actual model probes and free host route recorded.",
"Claim renderer, statement source and planned-row reporting pass their gates.",
"Public packets, synthetic families, rights and independent gold are frozen.",
"True scan variants and independently tested coordinate transforms exist.",
"Native, OCR, layout and table paths ran on the declared page inventory.",
"Retrieval, structural context and crop selection pass gold-isolation checks.",
"Structured VLM proposals and separate runtime evidence gates are implemented.",
"Actual LangGraph stages persist checkpoints and immutable operation receipts.",
"Live Vercel API executes fresh OCR and survives independent receipt reads.",
"Independent scoring and the final registered evaluation plan are frozen.",
"The selected matched VLM study ran with every planned row accounted for.",
"Process restart, recovery accounting and version-bound review are demonstrated.",
"Quality, uncertainty, resources and failures are reported with honest denominators.",
"The light-table site exposes source pixels, structure and actual result evidence.",
"Browser, theme, keyboard, narrow-width and live failure flows pass.",
"Cards, ADRs, skills, case study, notices and decision history are complete.",
"Clean-worktree rederive and the final live check pass with evidence.",
"Forty meaningful commits and the authorized tag/release are verified."]

def main():
    statement=(ROOT/"config/statement.txt").read_text().strip()
    results_path=ROOT/"artifacts/manifests/completion.json"
    checks=read_json(results_path) if results_path.exists() else {}
    checklist=[]
    for i,label in enumerate(LABELS,1):
        item=checks.get(str(i),{})
        evidence=item.get("evidence",[])
        verified=bool(evidence) and all((ROOT/p).is_file() for p in evidence) and item.get("verified") is True
        checklist.append({"number":i,"status":"done" if verified else "not done","requirement":label,"evidence":evidence,"reason":item.get("reason","No validated completion receipt")})
    summary={"status":"incomplete","study":None,"checklist":checklist,"statement":statement}
    trial_plan=ROOT/"artifacts/manifests/trial-plan.json"
    trial_results=ROOT/"artifacts/manifests/trial-results.json"
    if trial_plan.exists():
        rows=joined_rows(read_json(trial_plan),read_json(trial_results) if trial_results.exists() else [])
        summary["study"]=metrics(rows)
    write_json(ROOT/"artifacts/public-small/summary.json",summary)
    body=["# pagebound results","",statement,"","Build status: incomplete. Release status: not released.","","## Completion evidence",""]
    for item in checklist:
        body.append(f'{item["number"]}. {item["status"]}: {item["requirement"]} Evidence: '+(", ".join(item["evidence"]) or item["reason"]))
    body.extend(["","## Study","",json.dumps(summary["study"],indent=2) if summary["study"] else "Unavailable. No registered model trial inventory has completed.","","Stretch work: not started.",""])
    (ROOT/"RESULTS.md").write_text("\n".join(body),encoding="utf-8")
    print(json.dumps({"checklist_rows":len(checklist),"completed":sum(x["status"]=="done" for x in checklist)}))

if __name__=="__main__": main()
