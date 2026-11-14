import hashlib
import os
import secrets
import uuid
from contextlib import contextmanager
from pathlib import Path
from pagebound.identity import ContractError,digest,require_digest

class Conflict(ContractError):pass
class BudgetExceeded(ContractError):pass
class InProgress(ContractError):pass

class Store:
    def __init__(self,dsn=None):
        self.dsn=dsn or os.environ.get("DATABASE_URL")
        if not self.dsn:raise ContractError("Persistent database is not configured")

    @contextmanager
    def connect(self):
        import psycopg
        from psycopg.rows import dict_row
        with psycopg.connect(self.dsn,connect_timeout=5,row_factory=dict_row,options="-c statement_timeout=5000") as conn:
            yield conn

    def migrate(self):
        with self.connect() as c:c.execute((Path(__file__).parent/"schema.sql").read_text())

    def ready(self):
        with self.connect() as c:
            return c.execute("SELECT to_regclass('pagebound.receipts') IS NOT NULL AS ready").fetchone()["ready"]

    def session(self):
        token=secrets.token_urlsafe(32)
        hashed=hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as c:
            c.execute("INSERT INTO pagebound.sessions(capability_hash,expires_at) VALUES (%s,now()+interval '15 minutes')",(hashed,))
        return token

    def reserve(self,token,key,request_digest,bindings_digest,daily_limit=100,session_limit=8):
        require_digest(request_digest);require_digest(bindings_digest)
        capability=hashlib.sha256(token.encode()).hexdigest()
        with self.connect() as c:
            c.execute("SELECT pg_advisory_xact_lock(280100)")
            existing=c.execute("SELECT * FROM pagebound.operations WHERE capability_hash=%s AND idempotency_key=%s",(capability,key)).fetchone()
            if existing:
                if existing["request_digest"]!=request_digest or existing["bindings_digest"]!=bindings_digest:raise Conflict("Key already belongs to another request or artifact generation")
                r=c.execute("SELECT body FROM pagebound.receipts WHERE operation_id=%s",(existing["operation_id"],)).fetchone()
                if r:return {"mode":"idempotent_reuse","receipt":r["body"],"operation_id":str(existing["operation_id"])}
                raise InProgress("Operation is pending or interrupted; physical work is not repeated anonymously")
            s=c.execute("SELECT attempts FROM pagebound.sessions WHERE capability_hash=%s AND expires_at>now() FOR UPDATE",(capability,)).fetchone()
            if not s:raise ContractError("Missing or expired session capability")
            if s["attempts"]>=session_limit:raise BudgetExceeded("Session inference allowance exhausted")
            c.execute("INSERT INTO pagebound.budgets(day,attempts) VALUES (CURRENT_DATE,0) ON CONFLICT DO NOTHING")
            b=c.execute("SELECT attempts FROM pagebound.budgets WHERE day=CURRENT_DATE FOR UPDATE").fetchone()
            if b["attempts"]>=daily_limit:raise BudgetExceeded("Daily inference allowance exhausted")
            oid=str(uuid.uuid4())
            c.execute("UPDATE pagebound.budgets SET attempts=attempts+1 WHERE day=CURRENT_DATE")
            c.execute("UPDATE pagebound.sessions SET attempts=attempts+1 WHERE capability_hash=%s",(capability,))
            c.execute("INSERT INTO pagebound.operations(operation_id,capability_hash,idempotency_key,request_digest,bindings_digest,status,lease_until) VALUES (%s,%s,%s,%s,%s,'reserved',now()+interval '120 seconds')",(oid,capability,key,request_digest,bindings_digest))
            return {"mode":"new","operation_id":oid}

    def commit_receipt(self,oid,request_digest,body):
        from psycopg.types.json import Jsonb
        output_digest=digest(body)
        with self.connect() as c:
            row=c.execute("SELECT * FROM pagebound.operations WHERE operation_id=%s FOR UPDATE",(oid,)).fetchone()
            if not row or row["request_digest"]!=request_digest:raise Conflict("Operation binding changed")
            existing=c.execute("SELECT body,output_digest FROM pagebound.receipts WHERE operation_id=%s",(oid,)).fetchone()
            if existing:
                if existing["output_digest"]!=output_digest:raise Conflict("Immutable receipt differs")
                return existing["body"]
            c.execute("INSERT INTO pagebound.receipts(operation_id,request_digest,output_digest,body) VALUES (%s,%s,%s,%s)",(oid,request_digest,output_digest,Jsonb(body)))
            c.execute("UPDATE pagebound.operations SET status=%s WHERE operation_id=%s",("completed" if body["status"]=="completed" else "failed",oid))
        return body

    def receipt(self,oid):
        try:uuid.UUID(oid)
        except ValueError as exc:raise ContractError("Invalid receipt ID") from exc
        with self.connect() as c:
            r=c.execute("SELECT body FROM pagebound.receipts WHERE operation_id=%s",(oid,)).fetchone()
        return r["body"] if r else None

    def stage(self,run_id,stage,bindings,produce):
        from psycopg.types.json import Jsonb
        # A transaction-scoped lock serializes one logical stage across workers.
        # External computation may repeat after a crash; only one output commits.
        with self.connect() as c:
            c.execute("SET LOCAL statement_timeout='120s'")
            c.execute("SELECT pg_advisory_xact_lock(hashtextextended(%s,2801))",(run_id+":"+stage,))
            prior=c.execute("SELECT * FROM pagebound.stage_outputs WHERE run_id=%s AND stage=%s",(run_id,stage)).fetchone()
            if prior:
                if prior["bindings_digest"]!=bindings:raise Conflict("Stale checkpoint artifact binding")
                if digest(prior["body"])!=prior["output_digest"]:raise Conflict("Stage output corruption")
                return prior["body"]
            body=produce()
            c.execute("INSERT INTO pagebound.stage_outputs(run_id,stage,bindings_digest,output_digest,body) VALUES (%s,%s,%s,%s,%s)",(run_id,stage,bindings,digest(body),Jsonb(body)))
            return body

    def review(self,proposal,authorization):
        from psycopg.types.json import Jsonb
        if not authorization or authorization.get("proposal_digest")!=digest(proposal):raise ContractError("Approval does not bind the exact proposal")
        if authorization.get("mode") not in {"operator_assisted","test_assisted"}:raise ContractError("Unknown review authorization mode")
        with self.connect() as c:
            row=c.execute("SELECT body,output_digest,bindings_digest FROM pagebound.stage_outputs WHERE run_id=%s AND stage='result'",(proposal["run_id"],)).fetchone()
            if not row or row["bindings_digest"]!=proposal["bindings_digest"] or row["output_digest"]!=proposal["original_digest"]:raise Conflict("Stale review source or result")
            body={"execution_mode":authorization["mode"],"reviewer":authorization["reviewer"],"proposal":proposal,"original":row["body"]}
            result=c.execute("INSERT INTO pagebound.reviews(proposal_digest,run_id,bindings_digest,original_digest,assisted_digest,body) VALUES (%s,%s,%s,%s,%s,%s) ON CONFLICT DO NOTHING RETURNING assisted_digest",(digest(proposal),proposal["run_id"],proposal["bindings_digest"],proposal["original_digest"],digest(body),Jsonb(body))).fetchone()
            if not result:raise Conflict("Review already applied")
        return body
