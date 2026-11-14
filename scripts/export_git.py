"""Export committed source changes for the authorized GitHub connector."""
import json
import subprocess
import sys

def git(*args):return subprocess.check_output(["git",*args]).decode("utf-8").strip()
base=sys.argv[1] if len(sys.argv)>1 else None
revs=git("rev-list","--reverse",f"{base}..HEAD" if base else "HEAD").splitlines()
pack=[]
for rev in revs:
    names=git("diff-tree","--root","--no-commit-id","--name-only","-r",rev).splitlines()
    entries=[]
    for name in names:
        try: content=subprocess.check_output(["git","show",f"{rev}:{name}"]).decode("utf-8")
        except subprocess.CalledProcessError:
            entries.append({"path":name,"mode":"100644","type":"blob","sha":None});continue
        entries.append({"path":name,"mode":"100644","type":"blob","content":content})
    pack.append({"local_sha":rev,"message":git("show","-s","--format=%s",rev),"entries":entries})
print(json.dumps(pack))
