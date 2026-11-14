"""RapidOCR adapter. Instrument ONNX session execution independently of parsing."""
import hashlib
import time
from pathlib import Path
from pagebound.identity import ContractError,digest,file_digest

class OCREngine:
    def __init__(self, model_manifest=None):
        import rapidocr
        from rapidocr import RapidOCR
        self.engine=RapidOCR(params={"EngineConfig.onnxruntime.intra_op_num_threads":2,"EngineConfig.onnxruntime.inter_op_num_threads":1})
        root=Path(rapidocr.__file__).parent
        files=sorted(root.rglob("*.onnx"))
        if not files: raise ContractError("OCR package has no pinned ONNX files")
        self.files=[{"path":str(f.relative_to(root)),"sha256":file_digest(f),"bytes":f.stat().st_size} for f in files]
        self.bundle=digest(self.files)
        if model_manifest and self.bundle!=model_manifest["bundle_digest"]:
            raise ContractError("OCR artifact hash mismatch")

    def infer(self,image):
        import numpy as np
        import onnxruntime as ort
        calls=[]
        original=ort.InferenceSession.run
        def counted(session,*args,**kwargs):
            start=time.monotonic()
            result=original(session,*args,**kwargs)
            calls.append({"model":str(getattr(session,"_model_path","unknown")),"seconds":time.monotonic()-start,"shapes":[list(x.shape) for x in result if hasattr(x,"shape")]})
            return result
        # Each adapter is process-exclusive. The API also serializes inference.
        ort.InferenceSession.run=counted
        start=time.monotonic()
        try: output=self.engine(np.asarray(image.convert("RGB")))
        finally: ort.InferenceSession.run=original
        if not calls: raise ContractError("OCR produced no ONNX invocation evidence")
        boxes=getattr(output,"boxes",None)
        texts=getattr(output,"txts",None)
        scores=getattr(output,"scores",None)
        rows=[]
        if boxes is not None and texts is not None:
            for i,(poly,txt) in enumerate(zip(boxes,texts)):
                rows.append({"text":str(txt),"polygon":np.asarray(poly).tolist(),"recognition_confidence":float(scores[i]) if scores is not None else None})
        receipt={"component":"ocr","execution_mode":"learned_inference","status":"completed","forward_calls":len(calls),"model_bundle":self.bundle,"input_digest":hashlib.sha256(image.convert("RGB").tobytes()).hexdigest(),"output_digest":digest(rows),"seconds":time.monotonic()-start,"invocations":calls}
        return rows,receipt
