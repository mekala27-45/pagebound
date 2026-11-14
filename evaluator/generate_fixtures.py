"""Original synthetic truth and PDF generation. Never import from runtime."""
import json
import random
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/"src"))
from pagebound.identity import digest,file_digest,write_json

def generate(root=ROOT):
    from reportlab.pdfgen.canvas import Canvas
    out=root/"artifacts/fixture-pdfs";out.mkdir(parents=True,exist_ok=True)
    gold=[];questions=[];packets=[]
    names={"S1":"Equipment test and unit legend","S2":"Merged group headers and note","S3":"Directed process and glossary","S4":"Revision comparison and revision note","S5":"Same row labels across two panels","S6":"Rotated figure and companion legend"}
    for n,(family,title) in enumerate(names.items(),1):
        rng=random.Random(2801+n);a,b,c=[rng.randint(11,29) for _ in range(3)]
        path=out/(family+".pdf");pdf=Canvas(str(path),pagesize=(480,600),invariant=1,pageCompression=0)
        pdf.setTitle("Original synthetic document packet")
        def heading(label):
            pdf.setFillColorRGB(.12,.1,.16);pdf.setFont("Helvetica-Bold",18);pdf.drawString(30,558,"SYNTHETIC FIXTURE: "+family)
            pdf.setFont("Helvetica",12);pdf.drawString(30,532,label)
        def text(x,y,value,size=15):pdf.setFont("Helvetica",size);pdf.drawString(x,y,str(value))
        heading(title)
        bounds=[30,150,450,440]
        unit="kPa"
        if family=="S3":
            labels=["Receive","Inspect","Release"]
            for i,label in enumerate(labels):
                y=425-i*95;pdf.rect(150,y,180,45);text(174,y+16,label)
                if i<2:
                    pdf.line(240,y,240,y-50);pdf.line(240,y-50,234,y-40);pdf.line(240,y-50,246,y-40)
            text(30,105,"The arrows show the required process order.",12)
            values=["Receive","Inspect","Release"]
        elif family=="S6":
            pdf.saveState();pdf.translate(240,300);pdf.rotate(90)
            pdf.rect(-145,-170,290,340);text(-125,130,"Rotated pressure chart")
            for i,(code,value) in enumerate(zip(["SYN-RIG-A","SYN-RIG-B","SYN-RIG-C"],[a,b,c])):
                text(-125,75-i*65,code+"   "+str(value))
            pdf.restoreState();values=[a,b,c]
        else:
            labels=["SYN-RIG-A","SYN-RIG-B","SYN-RIG-C"]
            if family=="S2":
                pdf.rect(30,400,420,40);text(160,413,"Pressure measurements")
                pdf.rect(30,360,210,40);pdf.rect(240,360,210,40);text(45,373,"Equipment");text(255,373,"Run B reading")
            elif family=="S4":
                text(45,450,"Revision A");text(255,450,"Revision B")
                text(45,425,"Use the current revision note.",12)
            elif family=="S5":
                text(45,450,"Panel A: kPa");text(255,450,"Panel B: bar")
                text(45,425,"Same equipment appears in both panels.",12)
            else:text(45,430,"Equipment");text(255,430,"Reading")
            for i,(code,value) in enumerate(zip(labels,[a,b,c])):
                y=310-i*70;pdf.rect(30,y,420,55);pdf.line(240,y,240,y+55)
                text(45,y+19,code)
                if family=="S4":text(255,y+19,str(value-3)+"  /  "+str(value))
                elif family=="S5":text(255,y+19,str(value)+"  /  "+str(value/10))
                else:text(255,y+19,value)
            values=[a,b,c]
        pdf.showPage();heading("Companion notes and legend")
        if family=="S3":
            lines=["Release means dispatch the tested equipment.","Inspect follows Receive.","No reject branch is specified."]
        else:
            lines=["The selected readings use kPa.","Apply scale factor 2 to selected readings.","The scale applies to every listed equipment row."]
            if family=="S4":lines.insert(0,"Revision B is current. Use the right value.")
            if family=="S5":lines.insert(0,"Use Panel A. Panel B is a separate bar reading.")
        for i,line in enumerate(lines):text(35,465-i*44,line,14)
        text(35,140,"No operating temperature is specified.",13)
        text(35,105,"This is invented data for evaluation only.",12)
        pdf.save()
        packet={"id":family,"family":"synthetic","split":"development" if family in {"S1","S3","S5"} else "heldout","pdf_path":str(path.relative_to(root)).replace("\\","/"),"sha256":file_digest(path),"page_indices":[0,1],"title":title,"rights":"Original synthetic fixtures, CC0-1.0"}
        packets.append(packet)
        for q in range(1,9):
            qid=f"{family}-Q{q}";pages=[family+"-p0"];expected=[];disposition="answer"
            if family=="S3":
                qs=["Which process starts the diagram?","Which process is in the middle?","Which process ends the diagram?","Which process directly follows Receive?","Which process directly precedes Release?","What does the process immediately after Inspect mean, using the companion glossary?","What operating temperature is specified?","Why does the diagram begin with Release?"]
                ans=["Receive","Inspect","Release","Inspect","Inspect","dispatch the tested equipment",None,None]
                if q<=6:expected=[{"type":"text","value":ans[q-1]}]
            else:
                context=" Use Panel A." if family=="S5" else " Use Revision B." if family=="S4" else ""
                qs=[f"What selected reading is shown for SYN-RIG-{code}?"+context for code in "ABC"]+["Which unit applies to the selected readings?","What scale factor applies to the selected readings?","What scaled pressure applies to SYN-RIG-A using both the table and companion note?"+context,"What operating temperature is specified?","Why are the selected readings in degrees Celsius?"]
                if q<=3:expected=[{"type":"number","value":str(values[q-1]),"unit":"kPa"}];pages=[family+"-p0",family+"-p1"]
                elif q==4:expected=[{"type":"text","value":"kPa"}];pages=[family+"-p1"]
                elif q==5:expected=[{"type":"number","value":"2","unit":"1"}];pages=[family+"-p1"]
                elif q==6:expected=[{"type":"number","value":str(a*2),"unit":"kPa"}]
            if q==6:pages=[family+"-p0",family+"-p1"]
            if q==7:disposition="insufficient_evidence";pages=[]
            if q==8:disposition="unsupported_premise";pages=[family+"-p0",family+"-p1"] if family!="S3" else [family+"-p0"]
            questions.append({"id":qid,"packet_id":family,"text":f"According to this synthetic two-page packet: {qs[q-1]}"})
            gold.append({"question_id":qid,"packet_id":family,"split":packet["split"],"source_family":"synthetic","question_type":"Q"+str(q),"answerable":q<=6,"disposition":disposition,"atoms":expected,"required_pages":pages,"evidence":[{"page_id":p,"canonical_box":bounds if p.endswith("p0") else [30,100,450,480],"role":"source structure" if p.endswith("p0") else "unit and scale legend"} for p in pages],"absolute_tolerance":"0","relative_tolerance":"0","annotation_method":"generator truth; visible-page verification pending"})
    write_json(root/"artifacts/manifests/synthetic-packets.json",packets)
    write_json(root/"artifacts/public-small/synthetic-questions.json",questions)
    write_json(root/"evaluator/annotations/synthetic-gold.json",gold)
    return {"packets":len(packets),"questions":len(questions),"gold_digest":digest(gold)}

if __name__=="__main__":print(json.dumps(generate()))
