"""Only validated planned rows may contribute to numeric result claims."""
from collections import Counter
from .identity import ContractError, digest, require_digest

TERMINAL={"completed","failed","timeout","invalid","unavailable","missing"}
POLICIES={"native_text","layout_ocr","visual_grounded"}

def joined_rows(plan, actual):
    if not plan or not plan.get("trials"):
        raise ContractError("No planned inventory")
    plan_hash=require_digest(plan["plan_hash"])
    expected={}
    for row in plan["trials"]:
        key=row["trial_id"]
        if key in expected or row["policy"] not in POLICIES:
            raise ContractError("Duplicate plan or unknown policy")
        expected[key]=row
    got={}
    for row in actual:
        key=row["trial_id"]
        if key in got or key not in expected:
            raise ContractError("Duplicate or unexpected result")
        if row.get("plan_hash")!=plan_hash or any(row.get(k)!=expected[key].get(k) for k in ("policy","rendering","question_id")):
            raise ContractError("Mixed plan, policy or rendering")
        if row.get("status") not in TERMINAL or row.get("execution_mode")!="recorded_model_inference":
            raise ContractError("Nonterminal result or fixture used as inference")
        if row.get("status")=="completed" and (not row.get("invocation_completed") or not row.get("model_bundle")):
            raise ContractError("Completion lacks actual invocation evidence")
        got[key]=row
    return [{**r,**got.get(k,{"status":"missing","execution_mode":"not_run"})} for k,r in sorted(expected.items())]

def metrics(rows):
    if not rows: raise ContractError("Empty score inventory")
    answerable=[r for r in rows if r.get("answerable")]
    accepted=[r for r in rows if r.get("accepted")]
    def fraction(n,d): return {"numerator":n,"denominator":d,"value":n/d if d else None}
    return {
        "planned":len(rows),"statuses":dict(sorted(Counter(r["status"] for r in rows).items())),
        "completed":sum(bool(r.get("invocation_completed")) for r in rows),
        "answer_accuracy":fraction(sum(bool(r.get("answer_correct")) for r in answerable),len(answerable)),
        "grounded_success":fraction(sum(bool(r.get("grounded_correct")) for r in answerable),len(answerable)),
        "coverage":fraction(len(accepted),len(rows)),
        "selective_error":fraction(sum(not r.get("answer_correct",False) for r in accepted),len(accepted)),
        "query_digest":digest({"query":"metrics-v1","rows":rows})
    }

def validate_execution(receipt, component):
    if not receipt or receipt.get("execution_mode")!="learned_inference" or receipt.get("component")!=component:
        raise ContractError("No learned invocation receipt")
    if receipt.get("status")!="completed" or not receipt.get("forward_calls",0)>0:
        raise ContractError("No completed forward calls")
    for key in ("model_bundle","input_digest","output_digest"):
        require_digest(receipt.get(key))
    if component=="vlm_visual" and not receipt.get("image_tensor_elements",0)>0:
        raise ContractError("Visual trial has no image tensor")
    if component=="vlm_text" and receipt.get("image_tensor_elements",0)!=0:
        raise ContractError("Text trial contains an image tensor")
    return receipt
