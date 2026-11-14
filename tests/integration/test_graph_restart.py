"""Restart a real checkpointed graph; synthetic work stays explicitly labeled."""
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.parse import urlparse
import uuid

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pagebound.persistence.store import Store

CHILD = r'''
import json,os,sys
from pagebound.graph import run
from pagebound.identity import digest
from pagebound.persistence.store import Store
store=Store(os.environ['PAGEBOUND_TEST_DATABASE_URL'])
run_id,mode=sys.argv[1:]
binding=digest({'mode':'contract_fixture','generation':'one'})
def admit(state):
    return {'request':{'execution_mode':'contract_fixture'},'events':['admit']}
def infer(state):
    def produce():
        if mode=='resume':
            raise AssertionError('Committed physical stage was repeated after restart')
        return {'execution_mode':'contract_fixture','producer_pid':os.getpid()}
    result=store.stage(run_id,'fixture-operation',binding,produce)
    if mode=='crash':
        os._exit(86)
    return {'result':result,'events':state['events']+['resume']}
state=run({'admit':admit,'infer':infer},{'run_id':run_id,'bindings_digest':binding},store.dsn)
print(json.dumps({'state':state,'reader_pid':os.getpid()}))
'''


class GraphRestartTests(unittest.TestCase):
    def test_restart_reuses_committed_stage_from_new_process(self):
        dsn = os.environ.get("PAGEBOUND_TEST_DATABASE_URL", "")
        target = urlparse(dsn)
        if target.hostname not in {"localhost", "127.0.0.1"} or target.path != "/pagebound_ci":
            raise RuntimeError("Graph tests require the disposable local pagebound_ci database")
        Store(dsn).migrate()
        run_id = "restart-" + uuid.uuid4().hex
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        crashed = subprocess.run([sys.executable, "-c", CHILD, run_id, "crash"], env=env,
                                 text=True, capture_output=True, timeout=60)
        self.assertEqual(crashed.returncode, 86, crashed.stderr)
        resumed = subprocess.run([sys.executable, "-c", CHILD, run_id, "resume"], env=env,
                                 text=True, capture_output=True, timeout=60)
        self.assertEqual(resumed.returncode, 0, resumed.stderr)
        result = json.loads(resumed.stdout)
        self.assertEqual(result["state"]["result"]["execution_mode"], "contract_fixture")
        self.assertEqual(result["state"]["events"], ["admit", "resume"])
        self.assertNotEqual(result["reader_pid"], result["state"]["result"]["producer_pid"])
