"""Docling output normalization preserves predicted cells and header ancestry."""
from pagebound.identity import ContractError,digest

def normalize_document(document,render):
    result=[]
    for kind in ("texts","tables","pictures"):
        for item in document.get(kind,[]):
            for prov in item.get("prov",[]):
                if prov.get("page_no")!=render["physical_page_index"]+1 and prov.get("page_no")!=1:continue
                box=prov.get("bbox",{});coords=[box.get(k) for k in ("l","t","r","b")]
                if any(v is None for v in coords):continue
                left,top,right,bottom=coords
                if str(box.get("coord_origin","")).upper().endswith("BOTTOMLEFT"):
                    top,bottom=render["canonical_height"]-top,render["canonical_height"]-bottom
                top,bottom=min(top,bottom),max(top,bottom)
                t=render["transform"]
                # Scan conversion yields coordinates in scan PDF points, not original canonical points.
                if render["rendering"]=="scan":poly=[[2*x,2*y] for x,y in [(left,top),(right,top),(right,bottom),(left,bottom)]]
                else:poly=[[t["a"]*x+t["c"]*y+t["e"],t["b"]*x+t["d"]*y+t["f"]] for x,y in [(left,top),(right,top),(right,bottom),(left,bottom)]]
                text=item.get("text","");cells=[]
                if kind=="tables":
                    raw=item.get("data",{}).get("table_cells",[])
                    for i,cell in enumerate(raw):
                        parents=[j for j,h in enumerate(raw) if h.get("column_header") and h.get("end_row_offset_idx",0)<=cell.get("start_row_offset_idx",0) and h.get("start_col_offset_idx",0)<=cell.get("start_col_offset_idx",0)<h.get("end_col_offset_idx",0)]
                        cells.append({"id":f"cell-{i}","text":cell.get("text",""),"row_start":cell.get("start_row_offset_idx"),"row_end":cell.get("end_row_offset_idx"),"column_start":cell.get("start_col_offset_idx"),"column_end":cell.get("end_col_offset_idx"),"header_ancestors":[f"cell-{j}" for j in parents],"predicted_header":cell.get("column_header",False),"raw_bbox":cell.get("bbox"),"coordinate_source":"docling_predicted"})
                    text="\n".join("row "+str(c["row_start"])+" col "+str(c["column_start"])+" headers "+",".join(c["header_ancestors"])+": "+c["text"] for c in cells)
                row={"packet_id":render["packet_id"],"page_id":render["page_id"],"rendering":render["rendering"],"render_digest":render["sha256"],"source_digest":render["source_sha256"],"kind":kind,"text":text,"raw_text":item.get("text",""),"cells":cells,"polygon":poly,"image_width":render["width"],"image_height":render["height"],"execution_mode":"learned_extraction"}
                row["id"]="r-"+digest(row)[:24];result.append(row)
    return result
