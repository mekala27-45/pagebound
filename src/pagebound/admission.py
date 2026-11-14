from pagebound.identity import ContractError,digest,require_id,require_digest
from pagebound.geometry import pixel_crop

def validate_request(payload,manifest):
    if not isinstance(payload,dict) or set(payload)!={"page_id","rendering_id","render_digest","bounds","idempotency_key"}:raise ContractError("Unknown or missing request fields")
    for key in ("page_id","rendering_id","idempotency_key"):require_id(payload[key])
    require_digest(payload["render_digest"])
    if manifest.get("status")!="frozen":raise ContractError("Demo corpus is not ready")
    matches=[p for p in manifest.get("pages",[]) if p["id"]==payload["rendering_id"] and p["page_id"]==payload["page_id"]]
    if len(matches)!=1:raise ContractError("Page is not in the approved demo")
    page=matches[0]
    if page["sha256"]!=payload["render_digest"]:raise ContractError("Stale rendering")
    bounds=pixel_crop(payload["bounds"],page["width"],page["height"],manifest.get("crop_edge_limit",512))
    normalized={k:v for k,v in payload.items() if k!="idempotency_key"}
    normalized["pixel_bounds"]=bounds
    return page,bounds,digest(normalized)
