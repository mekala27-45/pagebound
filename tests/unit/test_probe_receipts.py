import importlib.util
from pathlib import Path
import shutil
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[2]
SPEC = importlib.util.spec_from_file_location("pagebound_check_probes", ROOT / "scripts/check_probes.py")
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class ProbeReceiptTests(unittest.TestCase):
    def test_exact_retained_receipts(self):
        manifest, probes = MODULE.verify(ROOT)
        self.assertEqual(manifest["benchmark_trials"], 0)
        self.assertEqual(len(probes["vlm"]["result"]["trials"]), 6)

    def test_missing_evidence_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaises(FileNotFoundError):
                MODULE.verify(Path(temporary))

    def test_changed_raw_output_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            shutil.copytree(ROOT / "artifacts/probes", root / "artifacts/probes")
            shutil.copytree(ROOT / "locks", root / "locks")
            with (root / "artifacts/probes/vlm.json").open("a") as stream:
                stream.write(" ")
            with self.assertRaisesRegex(MODULE.ContractError, "bytes changed"):
                MODULE.verify(root)
