"""Real database contracts in a disposable CI database, never a connected account."""
import concurrent.futures
import json
import os
from pathlib import Path
import subprocess
import sys
import unittest
from urllib.parse import urlparse

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "src"))
from pagebound.identity import ContractError, digest
from pagebound.persistence.store import Store, Conflict, BudgetExceeded, InProgress


class PersistenceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.dsn = os.environ.get("PAGEBOUND_TEST_DATABASE_URL", "")
        target = urlparse(cls.dsn)
        if target.hostname not in {"localhost", "127.0.0.1"} or target.path != "/pagebound_ci":
            raise RuntimeError("Integration tests require the disposable local pagebound_ci database")
        cls.store = Store(cls.dsn)
        cls.store.migrate()

    def setUp(self):
        with self.store.connect() as connection:
            connection.execute("TRUNCATE pagebound.reviews, pagebound.stage_outputs, pagebound.receipts, pagebound.operations, pagebound.sessions, pagebound.budgets CASCADE")
        self.token = self.store.session()
        self.request, self.binding = digest({"request": "test"}), digest({"artifact": "test"})

    def reserve(self, key="request-1", **limits):
        return self.store.reserve(self.token, key, self.request, self.binding, **limits)

    def test_committed_receipt_survives_an_independent_process(self):
        operation = self.reserve()["operation_id"]
        body = {"operation_id": operation, "status": "completed", "execution_mode": "contract_fixture"}
        self.store.commit_receipt(operation, self.request, body)
        command = "import json,os,sys;from pagebound.persistence.store import Store;print(json.dumps(Store(os.environ['PAGEBOUND_TEST_DATABASE_URL']).receipt(sys.argv[1])))"
        env = {**os.environ, "PYTHONPATH": str(ROOT / "src")}
        readback = subprocess.check_output([sys.executable, "-c", command, operation], env=env, text=True)
        self.assertEqual(json.loads(readback), body)

    def test_replay_is_immutable_and_does_not_charge_twice(self):
        operation = self.reserve()["operation_id"]
        body = {"status": "completed", "execution_mode": "contract_fixture"}
        self.store.commit_receipt(operation, self.request, body)
        replay = self.reserve()
        self.assertEqual(replay["mode"], "idempotent_reuse")
        self.assertEqual(replay["receipt"], body)
        with self.store.connect() as connection:
            self.assertEqual(connection.execute("SELECT attempts FROM pagebound.budgets").fetchone()["attempts"], 1)
        with self.assertRaises(Conflict):
            self.store.commit_receipt(operation, self.request, {"status": "failed"})
        with self.assertRaises(Conflict):
            self.store.reserve(self.token, "request-1", digest("changed"), self.binding)

    def test_concurrent_reservation_creates_one_operation(self):
        def attempt(_):
            try:
                return self.reserve()["mode"]
            except InProgress:
                return "pending"
        with concurrent.futures.ThreadPoolExecutor(max_workers=2) as pool:
            outcomes = list(pool.map(attempt, range(2)))
        self.assertCountEqual(outcomes, ["new", "pending"])
        with self.store.connect() as connection:
            self.assertEqual(connection.execute("SELECT count(*) AS n FROM pagebound.operations").fetchone()["n"], 1)

    def test_stage_reuse_and_stale_generation(self):
        calls = []
        def produce():
            calls.append(True)
            return {"value": "contract fixture"}
        first = self.store.stage("stage-test", "extract", self.binding, produce)
        self.assertEqual(self.store.stage("stage-test", "extract", self.binding, produce), first)
        self.assertEqual(calls, [True])
        with self.assertRaises(Conflict):
            self.store.stage("stage-test", "extract", digest("new generation"), produce)

    def test_expiry_and_budget_refuse_new_work(self):
        self.reserve(session_limit=1)
        with self.assertRaises(BudgetExceeded):
            self.reserve("request-2", session_limit=1)
        with self.store.connect() as connection:
            connection.execute("UPDATE pagebound.sessions SET expires_at=now()-interval '1 second'")
        with self.assertRaisesRegex(ContractError, "expired"):
            self.reserve("request-3")

    def test_review_binds_exact_original_and_cannot_overwrite_it(self):
        original = {"execution_mode": "contract_fixture", "value": "original"}
        self.store.stage("review-test", "result", self.binding, lambda: original)
        proposal = {"run_id": "review-test", "bindings_digest": self.binding,
                    "original_digest": digest(original), "value": "assisted"}
        authorization = {"mode": "test_assisted", "reviewer": "ci-contract",
                         "proposal_digest": digest(proposal)}
        self.assertEqual(self.store.review(proposal, authorization)["original"], original)
        self.assertEqual(self.store.stage("review-test", "result", self.binding, lambda: None), original)
        with self.assertRaises(Conflict):
            self.store.review(proposal, authorization)
        changed = {**proposal, "value": "changed"}
        with self.assertRaises(ContractError):
            self.store.review(changed, authorization)


if __name__ == "__main__":
    unittest.main()
