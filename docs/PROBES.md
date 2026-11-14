# Pagebound development model probes

These are real model readiness probes on an authored fixture. They are not benchmark scores or live-service checks.

Source: `a761bef6026b8322105c50ed568179929645ca97`. [Workflow](https://github.com/mekala27-45/pagebound/actions/runs/43555069117).

| Component | Status | Probe wall seconds |
| --- | --- | ---: |
| ocr | completed | 1.460 |
| layout | completed | 15.677 |
| vlm | completed | 56.625 |

| VLM policy | Forward calls | Image tensor elements | Inference seconds |
| --- | ---: | ---: | ---: |
| native_text | 31 | 0 | 2.040 |
| native_text | 31 | 0 | 2.031 |
| layout_ocr | 31 | 0 | 2.030 |
| layout_ocr | 31 | 0 | 2.044 |
| visual_grounded | 6 | 13631488 | 15.903 |
| visual_grounded | 6 | 13631488 | 16.043 |

The full study remains unexecuted. Model output correctness and evidence support are not assessed by these readiness probes.
The prior failed runs are retained as 43554406019 and 43554771730. Exact artifact hashes are in artifacts/probes/accepted.json.
