"""Run dependency-free contracts; report partial validation without claiming model work."""
from __future__ import annotations

import ast
import contextlib
import io
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
sys.path.insert(0, str(ROOT))


def check_runtime_isolation(root: Path) -> int:
    paths = sorted((root / "src/pagebound").rglob("*.py"))
    if not paths:
        raise ValueError("No runtime source files found")
    for path in paths:
        tree = ast.parse(path.read_text(encoding="utf-8"), filename=str(path))
        for node in ast.walk(tree):
            imports = []
            if isinstance(node, ast.Import):
                imports = [alias.name for alias in node.names]
            elif isinstance(node, ast.ImportFrom):
                imports = [node.module or ""]
            if any(name == "evaluator" or name.startswith("evaluator.") for name in imports):
                raise ValueError(f"Runtime imports evaluator: {path.relative_to(root)}")
            if isinstance(node, ast.Constant) and isinstance(node.value, str):
                value = node.value.replace("\\", "/")
                if "evaluator/annotations" in value:
                    raise ValueError(f"Runtime refers to answer-key path: {path.relative_to(root)}")
    return len(paths)


def main() -> int:
    log = io.StringIO()
    suite = unittest.defaultTestLoader.discover(str(ROOT / "tests/unit"))
    with contextlib.redirect_stdout(log), contextlib.redirect_stderr(log):
        result = unittest.TextTestRunner(stream=log, verbosity=2).run(suite)
    passed = result.testsRun > 0 and result.wasSuccessful() and not result.skipped
    isolation = {"passed": False}
    try:
        isolation = {"passed": True, "runtime_modules": check_runtime_isolation(ROOT),
                     "scope": "static import and literal path checks; runtime integration remains required"}
    except (ValueError, SyntaxError) as error:
        isolation["error"] = str(error)
    passed = passed and isolation["passed"]
    receipt = {"schema_version": 1, "execution_mode": "contract_validation", "passed": passed,
               "source_commit": os.environ.get("GITHUB_SHA", "local-uncommitted"),
               "python": sys.version.split()[0], "tests": result.testsRun,
               "failures": len(result.failures), "errors": len(result.errors),
               "skipped": len(result.skipped), "runtime_isolation": isolation,
               "actual_model_inference_verified": False, "live_service_verified": False,
               "completed_release": False}
    out = ROOT / "artifacts/validation"
    out.mkdir(parents=True, exist_ok=True)
    (out / "contracts.log").write_text(log.getvalue(), encoding="utf-8")
    (out / "contracts.json").write_text(json.dumps(receipt, indent=2) + "\n", encoding="utf-8")
    print(log.getvalue())
    print(json.dumps(receipt))
    return 0 if passed else 1


if __name__ == "__main__":
    raise SystemExit(main())
