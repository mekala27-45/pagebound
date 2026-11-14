# pagebound

Use Python 3.12. Runtime code in src/pagebound must never read evaluator/annotations.
Run python scripts/validate.py for dependency-free contract checks and the available validation report.
For direct unittest discovery, set PYTHONPATH=src before python -m unittest discover -s tests/unit.
Run python scripts/render_claims.py to derive result documents from artifacts.
Run uvicorn pagebound.api.app:app --app-dir src for the API.
Real inference receipts and test fixtures have different execution labels.
Do not erase failed or missing planned trials. Never add gold to retrieval.
All identifiers bind exact source, raster, extraction, model and plan digests.
Use the existing public-action authorization. Do not send posts or email.
No paid services, no card, no fabricated measurements or model results.
