"""Validate exact retained development receipts and render their limited claims."""
from collections import Counter
import json
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from pagebound.identity import ContractError, digest, file_digest, inside, read_json
from pagebound.reporting import validate_execution


def verify(root=ROOT):
    manifest = read_json(root / "artifacts/probes/accepted.json")
    if manifest.get("benchmark_trials") != 0 or manifest.get("execution_mode") != "development_model_probes":
        raise ContractError("Probe evidence cannot count as benchmark trials")
    if not re.fullmatch(r"[a-f0-9]{40}", manifest.get("source_commit", "")):
        raise ContractError("Missing exact probe source")
    required = {"artifacts/probes/ocr.json", "artifacts/probes/layout.json", "artifacts/probes/vlm.json",
                "artifacts/probes/environment.json", "artifacts/probes/summary.json",
                "artifacts/probes/docling-document.json", "artifacts/probes/probe.png",
                "artifacts/probes/probe.pdf", "locks/worker.lock"}
    if len(manifest["files"]) != len(required) or {r["path"] for r in manifest["files"]} != required:
        raise ContractError("Incomplete or duplicated probe inventory")
    for row in manifest["files"]:
        path = inside(root, row["path"])
        if path.stat().st_size != row["bytes"] or file_digest(path) != row["sha256"]:
            raise ContractError("Probe artifact bytes changed")
    probes = {name: read_json(root / f"artifacts/probes/{name}.json") for name in ("ocr", "layout", "vlm")}
    for probe in probes.values():
        if probe["status"] != "completed" or probe["code_revision"] != manifest["source_commit"]:
            raise ContractError("Unfinished or mixed-source probe")
    ocr = probes["ocr"]["result"]
    validate_execution(ocr["receipt"], "ocr")
    if ocr["receipt"]["output_digest"] != digest(ocr["rows"]):
        raise ContractError("OCR output digest changed")
    layout = probes["layout"]["result"]
    calls = layout["module_forward_calls"]
    if not layout["models"] or layout["tables"] < 1 or not all(
        any(fragment in name and count > 0 for name, count in calls.items())
        for fragment in ("tableformer", "rt_detr")
    ):
        raise ContractError("Missing learned layout or table invocation")
    if layout["output_digest"] != digest(read_json(root / "artifacts/probes/docling-document.json")):
        raise ContractError("Layout output digest changed")
    vlm = probes["vlm"]["result"]
    if Counter(t["policy"] for t in vlm["trials"]) != {"native_text": 2, "layout_ocr": 2, "visual_grounded": 2}:
        raise ContractError("Wrong probe policy inventory")
    for trial in vlm["trials"]:
        receipt = validate_execution(trial["receipt"], "vlm_visual" if trial["policy"] == "visual_grounded" else "vlm_text")
        if receipt["model_bundle"] != vlm["bundle_digest"] or receipt["output_digest"] != digest(trial["raw"]):
            raise ContractError("VLM artifact or output digest changed")
    return manifest, probes


def render(root=ROOT):
    manifest, probes = verify(root)
    lines = ["# Pagebound development model probes", "",
             "These are real model readiness probes on an authored fixture. They are not benchmark scores or live-service checks.", "",
             f"Source: `{manifest['source_commit']}`. [Workflow](https://github.com/mekala27-45/pagebound/actions/runs/{manifest['run_id']}).", "",
             "| Component | Status | Probe wall seconds |", "| --- | --- | ---: |"]
    lines.extend(f"| {name} | {probe['status']} | {probe['seconds']:.3f} |" for name, probe in probes.items())
    lines.extend(["", "| VLM policy | Forward calls | Image tensor elements | Inference seconds |",
                  "| --- | ---: | ---: | ---: |"])
    for trial in probes["vlm"]["result"]["trials"]:
        receipt = trial["receipt"]
        lines.append(f"| {trial['policy']} | {receipt['forward_calls']} | {receipt['image_tensor_elements']} | {receipt['seconds']:.3f} |")
    lines.extend(["", "The full study remains unexecuted. Model output correctness and evidence support are not assessed by these readiness probes.",
                  "The prior failed runs are retained as 43554406019 and 43554771730. Exact artifact hashes are in artifacts/probes/accepted.json.", ""])
    (root / "docs/PROBES.md").write_text("\n".join(lines), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    result = render()
    print(json.dumps({"verified": True, "source_commit": result["source_commit"], "benchmark_trials": 0}))
