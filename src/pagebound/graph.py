"""Actual typed LangGraph with primitive-only Postgres checkpoints."""
import json
import re
from contextlib import contextmanager
from typing import TypedDict
from pagebound.identity import ContractError,canonical,digest

class State(TypedDict,total=False):
    run_id:str
    bindings_digest:str
    request:dict
    image:dict
    crop:dict
    ocr:dict
    result:dict
    events:list

def graph_builder(stages):
    from langgraph.graph import StateGraph,START,END
    names=list(stages)
    if not names:raise ContractError("No graph stages")
    builder=StateGraph(State)
    for name,fn in stages.items():builder.add_node(name,fn)
    builder.add_edge(START,names[0])
    for left,right in zip(names,names[1:]):builder.add_edge(left,right)
    builder.add_edge(names[-1],END)
    return builder

@contextmanager
def checkpoint_store(dsn):
    import psycopg
    from psycopg.rows import dict_row
    from langgraph.checkpoint.postgres import PostgresSaver
    from langgraph.checkpoint.serde.base import SerializerProtocol
    class PrimitiveSerializer(SerializerProtocol):
        def dumps_typed(self,obj):return ("json",canonical(obj))
        def loads_typed(self,data):
            if data[0]!="json":raise ContractError("Unsupported checkpoint type")
            return json.loads(data[1],parse_constant=lambda _:(_ for _ in ()).throw(ContractError("Nonfinite checkpoint")))
    class QualifiedSaver(PostgresSaver):pass
    names=("checkpoint_migrations","checkpoint_blobs","checkpoint_writes","checkpoints")
    for cls in reversed(PostgresSaver.__mro__):
        for key,value in vars(cls).items():
            if not key.isupper():continue
            def qualify(s):
                for name in names:s=re.sub(r"(?<![.\w])"+name+r"(?![\w])","pagebound."+name,s)
                return s
            if isinstance(value,str):setattr(QualifiedSaver,key,qualify(value))
            elif isinstance(value,list) and all(isinstance(x,str) for x in value):setattr(QualifiedSaver,key,[qualify(x) for x in value])
    with psycopg.connect(dsn,autocommit=True,prepare_threshold=0,row_factory=dict_row,connect_timeout=5) as conn:
        saver=QualifiedSaver(conn,serde=PrimitiveSerializer())
        saver.setup()
        yield saver

def run(stages,state,dsn):
    with checkpoint_store(dsn) as saver:
        graph=graph_builder(stages).compile(checkpointer=saver)
        config={"configurable":{"thread_id":state["run_id"]}}
        prior=graph.get_state(config)
        if prior.values:
            if prior.values.get("bindings_digest")!=state["bindings_digest"]:raise ContractError("Stale graph generation")
            return graph.invoke(None,config) if prior.next else prior.values
        return graph.invoke(state,config)
