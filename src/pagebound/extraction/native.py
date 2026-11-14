from pathlib import Path
from pagebound.identity import digest

def extract_page(pdf_path,page_index,render):
    import pypdfium2 as pdfium
    doc=pdfium.PdfDocument(pdf_path);page=doc[page_index];textpage=page.get_textpage()
    regions=[]
    try:
        # Native line-level evidence uses actual character coordinates.
        line=[]
        def flush():
            if not line:return
            text="".join(v[0] for v in line).strip()
            if not text:line.clear();return
            left=min(v[1][0] for v in line);right=max(v[1][2] for v in line)
            top=min(v[1][1] for v in line);bottom=max(v[1][3] for v in line)
            t=render["transform"]
            poly=[[t["a"]*x+t["c"]*y+t["e"],t["b"]*x+t["d"]*y+t["f"]] for x,y in [(left,top),(right,top),(right,bottom),(left,bottom)]]
            r={"page_id":render["page_id"],"packet_id":render["packet_id"],"rendering":render["rendering"],"render_digest":render["sha256"],"source_digest":render["source_sha256"],"text":text,"polygon":poly,"image_width":render["width"],"image_height":render["height"],"kind":"native_line","execution_mode":"native_extraction"}
            r["id"]="r-"+digest(r)[:24];regions.append(r);line.clear()
        for i in range(textpage.count_chars()):
            char=textpage.get_text_range(i,1)
            if char in "\r\n":flush();continue
            x0,y0,x1,y1=textpage.get_charbox(i)
            line.append((char,[x0,page.get_height()-y1,x1,page.get_height()-y0]))
        flush()
    finally:textpage.close();page.close();doc.close()
    return regions
