"""Packet-scoped BM25. No gold fields or source counterpart lookup."""
import math
import re
import unicodedata
from collections import Counter
from pagebound.identity import ContractError,digest

def normalize(text):
    return " ".join(unicodedata.normalize("NFC",text).split())

def tokens(text):
    return re.findall(r"[\w]+(?:[.,][\d]+)?|[%+\-]",normalize(text).lower())

class RegionIndex:
    def __init__(self,regions,packet_id,rendering,extraction_digest):
        self.rows=sorted(regions,key=lambda r:r["id"])
        if len({r["id"] for r in self.rows})!=len(self.rows):raise ContractError("Duplicate region")
        for row in self.rows:
            if row["packet_id"]!=packet_id or row["rendering"]!=rendering:
                raise ContractError("Cross-packet or cross-rendering evidence")
            if any(k in row for k in ("gold","expected","answerability","question_type","accepted_atoms")):
                raise ContractError("Gold field in runtime index")
        self.counts=[Counter(tokens(r["text"])) for r in self.rows]
        self.lengths=[sum(c.values()) for c in self.counts]
        self.average=sum(self.lengths)/len(self.lengths) if self.lengths else 1
        self.df=Counter(t for c in self.counts for t in c)
        self.identity=digest({"regions":self.rows,"extraction":extraction_digest,"tokenizer":"nfc-word-v1"})

    def search(self,query,k=4):
        if not isinstance(query,str) or not query.strip() or len(query)>1000:
            raise ContractError("Query must contain bounded text")
        if not 1<=k<=4:raise ContractError("Region budget exceeded")
        scores=[];N=len(self.rows)
        for row,c,length in zip(self.rows,self.counts,self.lengths):
            score=0
            for t in set(tokens(query)):
                freq=c.get(t,0)
                if freq:
                    idf=math.log(1+(N-self.df[t]+0.5)/(self.df[t]+0.5))
                    score+=idf*freq*2.5/(freq+1.5*(0.25+0.75*length/(self.average or 1)))
            if score>0:scores.append({**row,"retrieval_score":score})
        return sorted(scores,key=lambda r:(-r["retrieval_score"],r["id"]))[:min(8,k)]

def evidence_text(regions):
    return "\n".join(r["id"]+": "+r["text"] for r in regions)

def choose_crops(regions,anchor,margin=12,limit=2):
    if not 0<=margin<=64 or limit!=2:raise ContractError("Unregistered crop rule")
    picked=[]
    for row in regions:
        page=row["page_id"]
        if page in [p["page_id"] for p in picked]:continue
        xy=row["polygon"];w=row["image_width"];h=row["image_height"]
        bounds=[max(0,math.floor(min(p[0] for p in xy)-margin)),max(0,math.floor(min(p[1] for p in xy)-margin)),min(w,math.ceil(max(p[0] for p in xy)+margin)),min(h,math.ceil(max(p[1] for p in xy)+margin))]
        picked.append({"region_id":row["id"],"page_id":page,"render_digest":row["render_digest"],"bounds":bounds,"fallback":False})
        if len(picked)==limit:break
    if not picked:
        picked=[{"region_id":anchor["id"],"page_id":anchor["page_id"],"render_digest":anchor["sha256"],"bounds":[0,0,anchor["width"],anchor["height"]],"fallback":True}]
    return picked
