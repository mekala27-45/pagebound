# Decision journal

2026-11-07: The selected project is Day 28 pagebound. The workspace contained no implementation.

2026-11-07: An installed Python 3.12.13 interpreter runs. Default launcher and uv trampoline creation failed. Standard venv creation succeeded. Direct downloads could not resolve pypi.org in the restricted executor. No model execution is claimed.

2026-11-07: Created a dedicated pagebound project under the existing Neon Free organization with bounded compute and storage quotas. No connection or durability success is inferred from provisioning.

2026-11-07: Keep the full versus compact profile undecided until actual probe receipts exist. Do not choose a profile from assumed CPU performance.
# 2026-11-14: recover the unpushed implementation

The repository contained only its initial README. Recover the existing local source, API, evaluator, synthetic generator, and inspection interface into a draft review branch. Preserve the incomplete completion checklist. Do not treat this source recovery as evidence of live OCR, layout, visual inference, or a completed registered study.

Add one dependency-free validation entry point and CI that retains contract failures. Check the runtime source for evaluator imports and answer-key path literals, with positive, negative, and empty-source tests. This static check supplements the existing retrieval isolation tests; it is not a claim of full runtime isolation coverage.

The synthetic preview job regenerates original fixtures and native extraction. It does not export evaluator annotations. Model probes remain separate real executions on a standard CPU runner, with their success or failure retained explicitly. No live deployment or release is included in this recovery commit.

