import importlib.util
from pathlib import Path
import tempfile
import unittest

SCRIPT = Path(__file__).resolve().parents[2] / "scripts/validate.py"
SPEC = importlib.util.spec_from_file_location("pagebound_validate", SCRIPT)
MODULE = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(MODULE)


class RuntimeIsolationTests(unittest.TestCase):
    def check_source(self, source):
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            target = root / "src/pagebound/worker.py"
            target.parent.mkdir(parents=True)
            target.write_text(source, encoding="utf-8")
            return MODULE.check_runtime_isolation(root)

    def test_clean_runtime(self):
        self.assertEqual(self.check_source("from pagebound.identity import digest\n"), 1)

    def test_evaluator_import_refused(self):
        with self.assertRaisesRegex(ValueError, "imports evaluator"):
            self.check_source("from evaluator.scoring import evaluate\n")

    def test_annotation_path_refused(self):
        with self.assertRaisesRegex(ValueError, "answer-key path"):
            self.check_source("path = 'evaluator/annotations/gold.json'\n")

    def test_empty_source_refused(self):
        with tempfile.TemporaryDirectory() as temporary:
            with self.assertRaisesRegex(ValueError, "No runtime"):
                MODULE.check_runtime_isolation(Path(temporary))
