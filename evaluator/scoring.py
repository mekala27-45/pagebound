"""Independent semantic checks and polygon intersection; no runtime gate imports."""
from decimal import Decimal,InvalidOperation
import math
import random
import unicodedata

def norm(value):return " ".join(unicodedata.normalize("NFC",str(value)).casefold().split())

def atom_equal(actual,expected,gold):
    if actual.get("type")!=expected.get("type"):return False
    if expected["type"]=="number":
        if actual.get("unit")!=expected.get("unit"):return False
        try:
            a,b=Decimal(str(actual["value"])),Decimal(str(expected["value"]))
            atol=Decimal(gold.get("absolute_tolerance","0"));rtol=Decimal(gold.get("relative_tolerance","0"))
            return a.is_finite() and b.is_finite() and abs(a-b)<=max(atol,rtol*abs(b))
        except (KeyError,InvalidOperation):return False
    if expected["type"]=="relation":return all(norm(actual.get(k,""))==norm(expected[k]) for k in ("source","destination","relation"))
    return norm(actual.get("value","")) in {norm(x) for x in [expected["value"],*expected.get("aliases",[])]}

def semantic(answer,gold):
    if not isinstance(answer,dict) or answer.get("disposition")!=gold["disposition"]:return False
    if gold["disposition"]!="answer":return not answer.get("atoms")
    expected=gold["atoms"];actual=answer.get("atoms",[])
    if len(actual)!=len(expected):return False
    def match(index,unused):
        if index==len(expected):return True
        return any(atom_equal(actual[j],expected[index],gold) and match(index+1,unused-{j}) for j in unused)
    return match(0,set(range(len(actual))))

def polygon_area(points):
    return abs(sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points))))/2 if len(points)>2 else 0

def signed_area(points):return sum(points[i][0]*points[(i+1)%len(points)][1]-points[(i+1)%len(points)][0]*points[i][1] for i in range(len(points)))/2

def intersect(subject,clip):
    # Sutherland-Hodgman against an independently defined convex reference polygon.
    output=list(subject);orientation=1 if signed_area(clip)>0 else -1
    for i,a in enumerate(clip):
        b=clip[(i+1)%len(clip)];incoming=output;output=[]
        if not incoming:break
        def side(p):return orientation*((b[0]-a[0])*(p[1]-a[1])-(b[1]-a[1])*(p[0]-a[0]))
        p=incoming[-1]
        for q in incoming:
            sp,sq=side(p),side(q)
            if (sp>=0)!=(sq>=0):
                t=sp/(sp-sq);output.append([p[0]+t*(q[0]-p[0]),p[1]+t*(q[1]-p[1])])
            if sq>=0:output.append(q)
            p=q
    return output

def reference_polygon(box,transform):
    x0,y0,x1,y1=box;t=transform
    return [[t["a"]*x+t["c"]*y+t["e"],t["b"]*x+t["d"]*y+t["f"]] for x,y in [(x0,y0),(x1,y0),(x1,y1),(x0,y1)]]

def score(answer,gold,citations,renders,coverage_threshold,excess_area_threshold):
    correct=semantic(answer,gold)
    selected=set(answer.get("evidence_ids",[])) if isinstance(answer,dict) else set()
    cited=[c for c in citations if c["id"] in selected]
    required=set(gold["required_pages"])
    complete=required.issubset({c["page_id"] for c in cited})
    support=[]
    for piece in gold.get("evidence",[]):
        passed=False
        for citation in cited:
            if citation["page_id"]!=piece["page_id"]:continue
            render=renders.get(citation.get("render_digest"))
            if not render or render["page_id"]!=piece["page_id"]:continue
            ref=reference_polygon(piece["canonical_box"],render["transform"])
            poly=citation["polygon"];overlap=polygon_area(intersect(poly,ref));gold_area=polygon_area(ref);cite_area=polygon_area(poly)
            coverage=overlap/gold_area if gold_area else 0
            excess=cite_area/gold_area if gold_area else math.inf
            if coverage>=coverage_threshold and excess<=excess_area_threshold:passed=True
        support.append(passed)
    spatial=bool(support) and all(support)
    return {"answer_correct":correct,"evidence_complete":complete,"spatial_support":spatial,"grounded_correct":correct and complete and spatial,"accepted":isinstance(answer,dict) and answer.get("disposition")=="answer"}

def paired_cluster_interval(rows,left,right,seed=2801,samples=2000):
    groups={}
    for row in rows:
        if row["policy"] in {left,right}:
            groups.setdefault(row["packet_id"],{}).setdefault((row["question_id"],row["rendering"]),{})[row["policy"]]=float(row.get("grounded_correct",False))
    packet_differences=[]
    for packet,inputs in sorted(groups.items()):
        if any(set(v)!={left,right} for v in inputs.values()):raise ValueError("Unmatched planned comparison")
        packet_differences.append(sum(v[left]-v[right] for v in inputs.values())/len(inputs))
    if not packet_differences:return {"difference":None,"interval":None,"clusters":0}
    rng=random.Random(seed);n=len(packet_differences)
    draws=sorted(sum(rng.choice(packet_differences) for _ in range(n))/n for _ in range(samples))
    return {"difference":sum(packet_differences)/n,"interval":[draws[int(.025*(samples-1))],draws[int(.975*(samples-1))]],"clusters":n,"method":"paired packet cluster bootstrap","limitation":"Exploratory interval; few clusters give coarse unstable uncertainty"}
