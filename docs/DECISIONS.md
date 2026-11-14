# Decision journal

2026-11-07: The selected project is Day 28 pagebound. The workspace contained no implementation.

2026-11-07: An installed Python 3.12.13 interpreter runs. Default launcher and uv trampoline creation failed. Standard venv creation succeeded. Direct downloads could not resolve pypi.org in the restricted executor. No model execution is claimed.

2026-11-07: Created a dedicated pagebound project under the existing Neon Free organization with bounded compute and storage quotas. No connection or durability success is inferred from provisioning.

2026-11-07: Keep the full versus compact profile undecided until actual probe receipts exist. Do not choose a profile from assumed CPU performance.
# 2026-11-14: recover the unpushed implementation

## CPU image operator compatibility

The first real runner probe (43554406019) completed OCR but failed layout and VLM initialization with `RuntimeError: operator torchvision::nms does not exist`. Its retained environment contains torch 2.15.0+cpu and torchvision 0.29.2 from the general package index. Pin the documented torch 2.14.1 and torchvision 0.29.1 CPU pair from the PyTorch CPU index, constrain subsequent worker resolution, and execute a real NMS operator before model probes. The compatibility change follows observed initialization failures. It does not replace model inference with fixtures or change a registered study; no study is frozen yet. Source: https://pytorch.org/get-started/previous-versions/ (checked 2026-11-14).

Add isolated Postgres integration checks for independent-process readback, immutable receipt replay, concurrent reservations, stage reuse, budget/expiry refusal, and exact assisted-review binding. These run only against a new CI database named pagebound_ci on localhost. They do not exercise the live connected database or claim real model execution.

The repository contained only its initial README. Recover the existing local source, API, evaluator, synthetic generator, and inspection interface into a draft review branch. Preserve the incomplete completion checklist. Do not treat this source recovery as evidence of live OCR, layout, visual inference, or a completed registered study.

Add one dependency-free validation entry point and CI that retains contract failures. Check the runtime source for evaluator imports and answer-key path literals, with positive, negative, and empty-source tests. This static check supplements the existing retrieval isolation tests; it is not a claim of full runtime isolation coverage.

The synthetic preview job regenerates original fixtures and native extraction. It does not export evaluator annotations. Model probes remain separate real executions on a standard CPU runner, with their success or failure retained explicitly. No live deployment or release is included in this recovery commit.

