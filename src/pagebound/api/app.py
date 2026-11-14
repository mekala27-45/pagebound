import os
from pathlib import Path
from fastapi import FastAPI,HTTPException,Header,Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel,ConfigDict,Field
from pagebound.identity import ContractError,read_json,inside
from pagebound.persistence.store import Store,Conflict,BudgetExceeded,InProgress
from pagebound.api.service import OCRService

ROOT=Path(os.environ.get("PAGEBOUND_ROOT",Path(__file__).resolve().parents[3]))
app=FastAPI(title="pagebound",version="0.1.0")
app.add_middleware(CORSMiddleware,allow_origins=["https://mekala27-45.github.io"],allow_methods=["GET","POST"],allow_headers=["Content-Type","Authorization"])

class OCRRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    page_id:str=Field(min_length=1,max_length=96)
    rendering_id:str=Field(min_length=1,max_length=96)
    render_digest:str=Field(pattern="^[a-f0-9]{64}$")
    bounds:list[float]=Field(min_length=4,max_length=4)
    idempotency_key:str=Field(min_length=1,max_length=96)

class SearchRequest(BaseModel):
    model_config=ConfigDict(extra="forbid",strict=True)
    packet_id:str=Field(min_length=1,max_length=96)
    rendering:str=Field(pattern="^(digital|scan)$")
    query:str=Field(min_length=1,max_length=1000)

@app.middleware("http")
async def body_limit(request:Request,call_next):
    from starlette.responses import JSONResponse
    if request.method=="POST":
        body=await request.body()
        if len(body)>8192:return JSONResponse({"detail":"Request too large"},status_code=413)
    response=await call_next(request)
    response.headers["Cache-Control"]="no-store"
    response.headers["X-Content-Type-Options"]="nosniff"
    return response

@app.get("/health")
def health():return {"status":"alive","build":os.environ.get("VERCEL_GIT_COMMIT_SHA","local"),"model_readiness":"check /ready"}

@app.get("/ready")
def ready():
    try:
        if not OCRService(ROOT).ready():raise ContractError("Not ready")
    except Exception:raise HTTPException(503,"Pinned artifacts and persistence are not ready")
    return {"status":"ready"}

@app.get("/catalog")
def catalog():
    m=read_json(ROOT/"config/api-demo-manifest.json")
    return {"status":m["status"],"pages":[{k:v for k,v in p.items() if k!="path"} for p in m["pages"]],"statement":(ROOT/"config/statement.txt").read_text()}

@app.post("/session")
def session():
    try:return {"capability":Store().session(),"expires_in_seconds":900}
    except Exception:raise HTTPException(503,"Persistent admission unavailable")

@app.post("/ocr")
def ocr(payload:OCRRequest,authorization:str=Header(default="")):
    if not authorization.startswith("Bearer "):raise HTTPException(401,"Session capability required")
    try:return OCRService(ROOT).execute(payload.model_dump(),authorization[7:])
    except Conflict as exc:raise HTTPException(409,str(exc))
    except InProgress as exc:raise HTTPException(409,str(exc))
    except BudgetExceeded as exc:raise HTTPException(429,str(exc))
    except ContractError as exc:raise HTTPException(422,str(exc))
    except Exception:raise HTTPException(503,"Inference admission or persistent storage unavailable")

@app.get("/receipts/{receipt_id}")
def receipt(receipt_id:str):
    try:value=Store().receipt(receipt_id)
    except ContractError as exc:raise HTTPException(422,str(exc))
    except Exception:raise HTTPException(503,"Receipt store unavailable")
    if value is None:raise HTTPException(404,"Receipt not found")
    return value

@app.post("/search")
def search(payload:SearchRequest):
    from pagebound.retrieval import RegionIndex
    path=ROOT/"artifacts/public-small/extraction.json"
    if not path.exists():raise HTTPException(503,"Extraction index unavailable")
    data=read_json(path)
    rows=[r for r in data["regions"] if r["packet_id"]==payload.packet_id and r["rendering"]==payload.rendering]
    return {"execution_mode":"fresh_region_search","regions":RegionIndex(rows,payload.packet_id,payload.rendering,data["digest"]).search(payload.query)}

@app.get("/runs/{run_id}")
def run_record(run_id:str):
    from pagebound.identity import require_id
    try:require_id(run_id)
    except ContractError:raise HTTPException(422,"Invalid run ID")
    path=inside(ROOT/"artifacts/public-small/runs",run_id+".json")
    if not path.exists():raise HTTPException(404,"Recorded run unavailable")
    value=read_json(path)
    if value.get("execution_mode")!="recorded_model_inference":raise HTTPException(503,"Invalid recorded evidence")
    return value
