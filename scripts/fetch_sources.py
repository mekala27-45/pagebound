"""Allowlisted source acquisition. Changed bytes require a new corpus decision."""
import json
import sys
import urllib.request
from datetime import datetime,timezone
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1];sys.path.insert(0,str(ROOT/"src"))
from pagebound.identity import ContractError,file_digest,read_json,write_json

class Redirects(urllib.request.HTTPRedirectHandler):
    def redirect_request(self,req,fp,code,msg,headers,newurl):
        from urllib.parse import urlparse
        if urlparse(newurl).hostname not in {"nvlpubs.nist.gov","www.nasa.gov","nasa.gov"}:raise ContractError("Source redirect outside allowlist")
        return super().redirect_request(req,fp,code,msg,headers,newurl)

def main():
    import pypdfium2 as pdfium
    plan=read_json(ROOT/"config/corpus-plan.json");rows=[]
    folder=ROOT/"artifacts/source-pdfs";folder.mkdir(parents=True,exist_ok=True)
    for source in plan["sources"]:
        target=folder/(source["id"]+".pdf")
        with urllib.request.build_opener(Redirects()).open(source["url"],timeout=30) as response:
            data=response.read(plan["source_byte_limit"]+1);final=response.url
        if len(data)>plan["source_byte_limit"] or not data.startswith(b"%PDF-"):raise ContractError("Invalid source content or size")
        target.write_bytes(data)
        doc=pdfium.PdfDocument(target)
        if len(doc)!=source["expected_pages"]:raise ContractError("Unexpected edition page count")
        rows.append({**source,"sha256":file_digest(target),"bytes":len(data),"pages":len(doc),"retrieved_at":datetime.now(timezone.utc).isoformat(),"final_url":final,"pdf_path":str(target.relative_to(ROOT)).replace("\\","/"),"rights_review":"pending"})
        doc.close()
    old=ROOT/"config/sources.lock"
    if old.exists():
        previous=read_json(old)
        if [(x["id"],x["sha256"]) for x in previous]!=[(x["id"],x["sha256"]) for x in rows]:raise ContractError("Source bytes changed; preserve previous lock and review a new version")
    write_json(ROOT/"artifacts/manifests/source-candidate.json",rows)
    print(json.dumps({"sources":len(rows),"status":"candidate_pending_page_and_rights_review"}))
if __name__=="__main__":main()
