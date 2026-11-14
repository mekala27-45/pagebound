"""Runtime validity checks. Deliberately no semantic correctness decision."""
import json
from decimal import Decimal,InvalidOperation,localcontext
from pagebound.identity import ContractError
from pagebound.geometry import validate_polygon

def parse_answer(raw,allowed_ids):
    if not isinstance(raw,str) or not raw.strip() or len(raw)>16000:raise ContractError("Missing or oversized model output")
    text=raw.strip()
    if text.startswith("```json\n") and text.endswith("\n```"):text=text[8:-4]
    try:
        obj=json.loads(text,parse_constant=lambda _:(_ for _ in ()).throw(ContractError("Nonfinite output")))
    except (ValueError,RecursionError) as exc:raise ContractError("Malformed structured answer") from exc
    if not isinstance(obj,dict) or set(obj)-{"disposition","atoms","evidence_ids","program"}:raise ContractError("Unknown answer fields")
    if obj.get("disposition") not in {"answer","insufficient_evidence","unsupported_premise"}:raise ContractError("Invalid disposition")
    atoms=obj.get("atoms");refs=obj.get("evidence_ids")
    if not isinstance(atoms,list) or len(atoms)>8 or not isinstance(refs,list) or len(refs)>8:raise ContractError("Missing or oversized answer arrays")
    if any(not isinstance(x,str) or x not in allowed_ids for x in refs):raise ContractError("Citation not supplied to model")
    if obj["disposition"]=="answer" and (not atoms or not refs):raise ContractError("Answer lacks atoms or evidence")
    if obj["disposition"]=="insufficient_evidence" and atoms:raise ContractError("Abstention contains answer atoms")
    for atom in atoms:
        if not isinstance(atom,dict) or set(atom)-{"type","value","unit","evidence_ids","source","destination","relation"}:raise ContractError("Unknown atom field")
        if atom.get("type") not in {"text","number","relation"}:raise ContractError("Invalid atom type")
        ar=atom.get("evidence_ids")
        if not isinstance(ar,list) or not ar or len(ar)>8 or any(x not in refs for x in ar):raise ContractError("Atom lacks supplied support")
        if atom["type"]=="relation":
            if any(not isinstance(atom.get(k),str) or not atom[k] or len(atom[k])>200 for k in ("source","destination","relation")):raise ContractError("Malformed relation")
        elif not isinstance(atom.get("value"),(str,int,float)) or isinstance(atom.get("value"),bool) or len(str(atom["value"]))>500:raise ContractError("Malformed atom")
        if atom["type"]=="number":
            try:v=Decimal(str(atom["value"]))
            except InvalidOperation as exc:raise ContractError("Invalid numeric atom") from exc
            if not v.is_finite() or not isinstance(atom.get("unit"),str) or len(atom["unit"])>40:raise ContractError("Missing unit or nonfinite value")
    return obj

def arithmetic(program,operands):
    if not isinstance(program,list) or not 1<=len(program)<=3:raise ContractError("Missing or oversized program")
    values={};used=set()
    with localcontext() as ctx:
        ctx.prec=28
        for idx,step in enumerate(program):
            if not isinstance(step,dict) or set(step)!={"op","left","right"}:raise ContractError("Invalid instruction")
            args=[]
            for key in (step["left"],step["right"]):
                if not isinstance(key,str):raise ContractError("Operands must be references")
                if key in values:args.append(values[key]);continue
                if key not in operands:raise ContractError("Unknown operand")
                used.add(key)
                if len(used)>4:raise ContractError("Operand budget")
                value=operands[key]
                if not value.get("unit") or "value" not in value:raise ContractError("Missing operand value or unit")
                try:n=Decimal(str(value["value"]))
                except InvalidOperation as exc:raise ContractError("Bad decimal") from exc
                if not n.is_finite() or abs(n.adjusted())>100:raise ContractError("Unbounded number")
                args.append((n,value["unit"]))
            (a,u),(b,v)=args;op=step["op"]
            if op in {"add","subtract","minimum","maximum"}:
                if u!=v:raise ContractError("Incompatible units")
                n={"add":lambda:a+b,"subtract":lambda:a-b,"minimum":lambda:min(a,b),"maximum":lambda:max(a,b)}[op]();unit=u
            elif op=="multiply":n=a*b;unit=v if u=="1" else u if v=="1" else u+"*"+v
            elif op=="divide":
                if not b:raise ContractError("Division by zero")
                n=a/b;unit="1" if u==v else u if v=="1" else u+"/"+v
            else:raise ContractError("Operation not allowed")
            values["$"+str(idx)]=(n,unit)
    return {"value":str(n),"unit":unit,"operand_ids":sorted(used)}

def runtime_gates(answer,evidence):
    refs={r["id"]:r for r in evidence}
    results={"schema":False,"membership":False,"geometry":False,"semantic_support":"not_evaluated"}
    try:
        parsed=parse_answer(answer,set(refs));results["schema"]=True;results["membership"]=True
        for rid in parsed["evidence_ids"]:
            r=refs[rid];validate_polygon(r["polygon"],r["image_width"],r["image_height"])
        results["geometry"]=True
        return parsed,results
    except (ContractError,KeyError) as exc:
        results["reason"]=str(exc);return None,results
