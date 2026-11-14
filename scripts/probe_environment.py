"""Actual probe-only execution; these inputs never enter benchmark counts."""
import importlib.metadata as metadata
import json
import os
import platform
import subprocess
import sys
import time
import traceback
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from pagebound.identity import digest,file_digest,write_json

OUT=ROOT/"artifacts/probes"
OUT.mkdir(parents=True,exist_ok=True)

def attempt(name,fn):
    start=time.monotonic()
    try: record={"status":"completed","result":fn()}
    except Exception as exc:
        record={"status":"failed","error":type(exc).__name__+": "+str(exc),"traceback":traceback.format_exc()}
    record.update({"probe":name,"seconds":time.monotonic()-start,"execution_environment":platform.platform(),"code_revision":os.environ.get("GITHUB_SHA","local")})
    write_json(OUT/(name+".json"),record)
    print(json.dumps({"probe":name,"status":record["status"],"seconds":record["seconds"]}),flush=True)
    return record

def fixture():
    from PIL import Image,ImageDraw
    from reportlab.pdfgen.canvas import Canvas
    img=Image.new("RGB",(384,240),"white")
    d=ImageDraw.Draw(img)
    d.text((20,25),"PROBE ONLY",fill="black",font_size=24)
    d.text((20,75),"SYN-PROBE | 12 kPa",fill="black",font_size=22)
    d.text((20,125),"SYN-CHECK | 7 kPa",fill="black",font_size=22)
    img.save(OUT/"probe.png")
    c=Canvas(str(OUT/"probe.pdf"),pagesize=(384,240),invariant=1)
    c.setFont("Helvetica",16)
    c.drawString(20,210,"PROBE ONLY")
    for y in [70,110,150,190]:c.line(20,y,364,y)
    for x in [20,190,364]:c.line(x,70,x,190)
    c.drawString(30,165,"Equipment");c.drawString(200,165,"Pressure kPa")
    c.drawString(30,125,"SYN-PROBE");c.drawString(200,125,"12")
    c.drawString(30,85,"SYN-CHECK");c.drawString(200,85,"7")
    c.save()
    return img

def ocr():
    from pagebound.extraction.ocr import OCREngine
    image=fixture();engine=OCREngine()
    rows,receipt=engine.infer(image)
    return {"rows":rows,"receipt":receipt,"artifacts":engine.files}

def layout():
    import torch
    import onnxruntime as ort
    from docling.datamodel.base_models import InputFormat
    from docling.datamodel.pipeline_options import PdfPipelineOptions,RapidOcrOptions,TableFormerMode
    from docling.datamodel.accelerator_options import AcceleratorOptions,AcceleratorDevice
    from docling.document_converter import DocumentConverter,PdfFormatOption
    options=PdfPipelineOptions(do_ocr=True,do_table_structure=True)
    options.accelerator_options=AcceleratorOptions(num_threads=2,device=AcceleratorDevice.CPU)
    options.table_structure_options.mode=TableFormerMode.FAST
    import docling.datamodel.pipeline_options as po
    options.ocr_options=RapidOcrOptions(mode=po.OcrMode.FULL_PAGE) if hasattr(po,"OcrMode") else RapidOcrOptions(force_full_page_ocr=True)
    counter={}
    def hook(module,*_):
        name=type(module).__module__+"."+type(module).__name__
        if any(k in name.lower() for k in ("docling","tableformer","rt_detr","rt-detr","detr","layout")):
            counter[name]=counter.get(name,0)+1
    handle=torch.nn.modules.module.register_module_forward_pre_hook(hook)
    try:
        converter=DocumentConverter(format_options={InputFormat.PDF:PdfFormatOption(pipeline_options=options)})
        result=converter.convert(OUT/"probe.pdf")
    finally:handle.remove()
    document=result.document.export_to_dict()
    write_json(OUT/"docling-document.json",document)
    model_files=[]
    cache=Path(os.environ.get("HF_HOME",str(Path.home()/".cache/huggingface")))
    for p in sorted(cache.rglob("*")):
        if p.is_file() and p.suffix in (".safetensors",".pt",".pth",".onnx",".json"):
            model_files.append({"path":str(p.relative_to(cache)),"sha256":file_digest(p),"bytes":p.stat().st_size})
    return {"status":str(result.status),"module_forward_calls":counter,"tables":len(document.get("tables",[])),"output_digest":digest(document),"models":model_files,"options":options.model_dump(mode="json")}

def vlm():
    from pagebound.multimodal.model import VLM
    model=VLM();img=fixture();results=[]
    evidence="probe-table: SYN-PROBE pressure 12 kPa. SYN-CHECK pressure 7 kPa."
    for policy in ["native_text","layout_ocr","visual_grounded"]:
        for idx in range(2):
            raw,receipt=model.infer("What pressure is shown for SYN-PROBE?",evidence,[img] if policy=="visual_grounded" else [],192)
            results.append({"policy":policy,"probe_index":idx,"raw":raw,"receipt":receipt})
            write_json(OUT/"vlm-partial.json",results)
    worst=max(r["receipt"]["seconds"] for r in results)
    full=worst*72*1.5;compact=worst*36*1.5
    profile="full" if full<=5400 else "compact" if compact<=5400 else None
    return {"revision":model.revision,"bundle_digest":model.bundle,"artifacts":model.artifacts,"trials":results,"projected_full_seconds":full,"projected_compact_seconds":compact,"profile":profile,"safety_factor":1.5}

def main():
    packages={d.metadata["Name"]:d.version for d in metadata.distributions()}
    write_json(OUT/"environment.json",{"python":sys.version,"platform":platform.platform(),"logical_cpus":os.cpu_count(),"packages":dict(sorted(packages.items()))})
    fixture()
    records=[attempt("ocr",ocr),attempt("layout",layout),attempt("vlm",vlm)]
    write_json(OUT/"summary.json",records)
    if not all(x["status"]=="completed" for x in records):sys.exit(1)

if __name__=="__main__":main()
