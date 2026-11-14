"""PDFium rendering and true image-only scan construction."""
import io
import math
import random
from dataclasses import asdict
from pathlib import Path
from .geometry import Affine
from .identity import ContractError,digest,file_digest,write_json

def render_packets(packets,root,output):
    import pypdfium2 as pdfium
    from PIL import Image,ImageFilter
    from reportlab.pdfgen.canvas import Canvas
    from reportlab.lib.utils import ImageReader
    root=Path(root);output=Path(output);output.mkdir(parents=True,exist_ok=True)
    rows=[]
    rng=random.Random(2801)
    for packet in sorted(packets,key=lambda p:p["id"]):
        pdf=pdfium.PdfDocument(root/packet["pdf_path"])
        for idx in packet["page_indices"]:
            page=pdf[idx];width,height=page.get_size()
            image=page.render(scale=2).to_pil().convert("RGB")
            page_id=f'{packet["id"]}-p{idx}'
            native_path=output/(page_id+"-digital.png");image.save(native_path)
            base=Affine("canonical","digital",image.width/width,0,0,image.height/height)
            angle=rng.choice([-1.5,1.5]);scan=image.rotate(angle,resample=Image.Resampling.BICUBIC,expand=True,fillcolor="white").filter(ImageFilter.GaussianBlur(.4))
            c=math.cos(math.radians(angle));s=math.sin(math.radians(angle))
            rotation=Affine("digital","scan",c,-s,s,c,scan.width/2-c*image.width/2-s*image.height/2,scan.height/2+s*image.width/2-c*image.height/2)
            buf=io.BytesIO();scan.save(buf,format="JPEG",quality=75);buf.seek(0)
            scan_pdf=output/(page_id+"-scan.pdf")
            canvas=Canvas(str(scan_pdf),pagesize=(scan.width/2,scan.height/2),invariant=1)
            canvas.drawImage(ImageReader(buf),0,0,width=scan.width/2,height=scan.height/2);canvas.save()
            sp=pdfium.PdfDocument(scan_pdf);tp=sp[0].get_textpage();scan_text=tp.get_text_range();tp.close()
            if scan_text.strip():raise ContractError("Scan unexpectedly retains a text layer")
            scan_image=sp[0].render(scale=2).to_pil().convert("RGB")
            scan_path=output/(page_id+"-scan.png");scan_image.save(scan_path)
            for variant,path,img,transform in [("digital",native_path,image,base),("scan",scan_path,scan_image,base.then(rotation))]:
                rows.append({"id":page_id+"-"+variant,"page_id":page_id,"packet_id":packet["id"],"source_sha256":packet["sha256"],"physical_page_index":idx,"rendering":variant,"sha256":file_digest(path),"path":str(path.relative_to(root)).replace("\\","/"),"width":img.width,"height":img.height,"canonical_width":width,"canonical_height":height,"transform":asdict(transform),"dpi":144,"scan_angle":angle if variant=="scan" else 0,"scan_text_characters":len(scan_text) if variant=="scan" else None,"execution_mode":"generated_rendering"})
            sp.close();page.close()
        pdf.close()
    return {"schema_version":1,"pages":rows,"render_manifest_digest":digest(rows)}
