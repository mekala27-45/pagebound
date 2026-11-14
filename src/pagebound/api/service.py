import hashlib
import multiprocessing
import time
from datetime import datetime,timezone
from pathlib import Path
from pagebound.identity import ContractError,digest,file_digest,inside,read_json
from pagebound.geometry import validate_polygon
from pagebound.admission import validate_request
from pagebound.persistence.store import Store

def _ocr_process(queue,path,bounds,model_manifest):
    try:
        from PIL import Image
        from pagebound.extraction.ocr import OCREngine
        with Image.open(path) as image:crop=image.convert("RGB").crop(bounds)
        rows,receipt=OCREngine(model_manifest).infer(crop)
        queue.put({"rows":rows,"receipt":receipt,"crop_digest":hashlib.sha256(crop.tobytes()).hexdigest()})
    except Exception as exc:queue.put({"error":type(exc).__name__+": "+str(exc)})

def bounded_ocr(path,bounds,model_manifest,timeout=60):
    context=multiprocessing.get_context("spawn");q=context.Queue()
    p=context.Process(target=_ocr_process,args=(q,str(path),bounds,model_manifest))
    p.start()
    try:
        # Drain the queue before join to avoid a large result blocking child exit.
        import queue
        try:result=q.get(timeout=timeout)
        except queue.Empty as exc:raise TimeoutError("OCR execution exceeded its allowance") from exc
        p.join(5)
        if "error" in result:raise ContractError(result["error"])
        return result
    finally:
        if p.is_alive():p.terminate();p.join(5)
        q.close()

class OCRService:
    def __init__(self,root,store=None):
        self.root=Path(root);self.store=store or Store()

    def manifest(self):return read_json(self.root/"config/api-demo-manifest.json")

    def ready(self):
        m=self.manifest()
        if m.get("status")!="frozen" or not m.get("pages") or not m.get("ocr_model"):return False
        for p in m["pages"]:
            if file_digest(inside(self.root,p["path"]))!=p["sha256"]:return False
        # Artifact readiness does not claim a model call happened.
        import rapidocr
        package=Path(rapidocr.__file__).parent
        for f in m["ocr_model"]["files"]:
            if file_digest(inside(package,f["path"]))!=f["sha256"]:return False
        return self.store.ready()

    def execute(self,payload,capability):
        from pagebound.graph import run
        m=self.manifest();page,bounds,request_digest=validate_request(payload,m)
        path=inside(self.root,page["path"])
        if file_digest(path)!=page["sha256"]:raise ContractError("Raster bytes changed")
        if not m.get("ocr_model"):raise ContractError("OCR bundle unavailable")
        binding=digest({"page":page,"ocr":m["ocr_model"],"generation":m["generation"]})
        reserved=self.store.reserve(capability,payload["idempotency_key"],request_digest,binding)
        if reserved["mode"]=="idempotent_reuse":return {**reserved["receipt"],"execution_mode":"idempotent_reuse"}
        oid=reserved["operation_id"];start=time.monotonic();started=datetime.now(timezone.utc).isoformat()
        def admit(state):return {"events":["admit"],"request":{"digest":request_digest,"page_id":page["page_id"],"bounds":bounds}}
        def bind_image(state):return {"image":{"path":page["path"],"sha256":page["sha256"]},"events":state["events"]+["bind_image"]}
        def crop_image(state):return {"crop":{"bounds":bounds,"width":bounds[2]-bounds[0],"height":bounds[3]-bounds[1]},"events":state["events"]+["crop_image"]}
        def infer_ocr(state):
            value=self.store.stage(oid,"ocr",binding,lambda:bounded_ocr(path,bounds,m["ocr_model"],m.get("ocr_timeout_seconds",60)))
            return {"ocr":value,"events":state["events"]+["infer_ocr"]}
        def normalize(state):
            rows=[]
            for i,row in enumerate(state["ocr"]["rows"]):
                validate_polygon(row["polygon"],state["crop"]["width"],state["crop"]["height"])
                poly=[[x+bounds[0],y+bounds[1]] for x,y in row["polygon"]]
                rows.append({**row,"id":oid+"-r"+str(i),"polygon":poly,"coordinate_space":"raster_pixels","render_digest":page["sha256"],"page_id":page["page_id"]})
            return {"result":{"rows":rows},"events":state["events"]+["normalize"]}
        def commit_result(state):
            body={"operation_id":oid,"status":"completed","execution_mode":"fresh_ocr","request_digest":request_digest,"bindings_digest":binding,"render_digest":page["sha256"],"page_id":page["page_id"],"crop_bounds":bounds,"crop_digest":state["ocr"]["crop_digest"],"model_invocation":state["ocr"]["receipt"],"rows":state["result"]["rows"],"started_at":started,"finished_at":datetime.now(timezone.utc).isoformat(),"seconds":time.monotonic()-start,"events":state["events"]+["commit_result"]}
            return {"result":self.store.commit_receipt(oid,request_digest,body)}
        try:
            result=run({"admit":admit,"bind_image":bind_image,"crop_image":crop_image,"infer_ocr":infer_ocr,"normalize":normalize,"commit_result":commit_result},{"run_id":"live-"+oid,"bindings_digest":binding},self.store.dsn)
            return result["result"]
        except Exception as exc:
            body={"operation_id":oid,"status":"failed","execution_mode":"failed_ocr","request_digest":request_digest,"bindings_digest":binding,"reason":type(exc).__name__,"started_at":started,"seconds":time.monotonic()-start,"rows":[]}
            self.store.commit_receipt(oid,request_digest,body)
            return body
