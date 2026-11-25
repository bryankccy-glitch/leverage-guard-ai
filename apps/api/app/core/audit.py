"""稽核紀錄：只記錄動作與資源 ID，不寫入私人契約內容或個資。"""
from __future__ import annotations

import json
from typing import Any

from fastapi import Request
from sqlalchemy import text

from .db import service_session


def audit(request: Request | None, actor_id: str | None, action: str, resource_type: str,
          resource_id: str | None = None, metadata: dict[str, Any] | None = None, actor_type: str = "user") -> None:
    with service_session() as conn:
        conn.execute(text("""insert into audit_logs (actor_id, actor_type, action, resource_type, resource_id, metadata, request_id)
                             values (:a, :t, :ac, :rt, :ri, cast(:m as jsonb), :rq)"""),
                     {"a": actor_id, "t": actor_type, "ac": action, "rt": resource_type, "ri": resource_id,
                      "m": json.dumps(metadata or {}, ensure_ascii=False, default=str),
                      "rq": getattr(request.state, "request_id", None) if request else None})
