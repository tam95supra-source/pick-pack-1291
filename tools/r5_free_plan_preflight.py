#!/usr/bin/env python3
"""Read-only account-plan guard before R5 deployment; never print API credentials."""
from __future__ import annotations
import json
import os
import re
import sys
from datetime import datetime, timezone
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


def read_api(account: str, token: str, path: str) -> dict:
    req = Request(f"https://api.cloudflare.com/client/v4/accounts/{account}/{path}",
                  headers={"Authorization": f"Bearer {token}"}, method="GET")
    try:
        with urlopen(req, timeout=20) as response:
            payload = json.load(response)
        if payload.get("success") is not True:
            return {"ok": False, "error_codes": [x.get("code") for x in payload.get("errors", [])]}
        return {"ok": True, "result": payload.get("result"), "result_info": payload.get("result_info", {})}
    except HTTPError as error:
        return {"ok": False, "http_status": error.code}
    except (URLError, TimeoutError, ValueError):
        return {"ok": False, "error": "TRANSPORT_OR_INVALID_RESPONSE"}


def main() -> None:
    account = os.environ.get("CLOUDFLARE_ACCOUNT_ID", "")
    token = os.environ.get("CLOUDFLARE_API_TOKEN", "")
    if not re.fullmatch(r"[a-fA-F0-9]{32}", account) or not token:
        raise SystemExit("R5_PLAN_PREFLIGHT_MISSING_ACCOUNT_OR_TOKEN")
    subscriptions = read_api(account, token, "subscriptions")
    settings = read_api(account, token, "workers/account-settings")
    result = {"status": "PLAN_UNVERIFIED", "observed_at": datetime.now(timezone.utc).isoformat(),
              "read_only": True, "api_calls": 2, "configuration_writes": 0,
              "subscriptions_read": {k: v for k, v in subscriptions.items() if k not in {"result", "result_info"}},
              "settings_read": {k: v for k, v in settings.items() if k not in {"result", "result_info"}},
              "source": "Cloudflare accounts subscriptions + Workers account-settings"}
    rows = subscriptions.get("result")
    if subscriptions.get("ok") and isinstance(rows, list) and settings.get("ok") and isinstance(settings.get("result"), dict):
        info = subscriptions.get("result_info") or {}
        total = info.get("total_count", len(rows))
        if not isinstance(total, int) or total > len(rows):
            result["reason"] = "SUBSCRIPTION_LIST_INCOMPLETE"
        else:
            workers = []
            for row in rows:
                plan = row.get("rate_plan") or {}
                labels = " ".join(str(plan.get(k, "")) for k in ("id", "public_name", "scope", "sets"))
                if re.search(r"workers|durable.?objects|\bd1\b", labels, re.I):
                    workers.append({"plan_id": plan.get("id"), "name": plan.get("public_name"),
                                    "state": row.get("state"), "price": row.get("price"),
                                    "is_contract": plan.get("is_contract", False)})
            model = settings["result"].get("default_usage_model")
            result["workers_subscriptions"] = workers
            result["default_usage_model"] = model
            active = [r for r in workers if r["state"] not in {"Expired", "Failed"}]
            paid = any((isinstance(r["price"], (int, float)) and r["price"] > 0) or r["is_contract"] or
                       re.search(r"paid|standard|unbound|enterprise", str(r["plan_id"])+" "+str(r["name"]), re.I)
                       for r in active)
            explicit_free = active and all("free" in (str(r["plan_id"])+" "+str(r["name"])).lower() and r["price"] == 0 for r in active)
            if paid or model in {"standard", "unbound"}:
                result.update(status="BLOCKED_NON_FREE", reason="OWNER_REQUIRES_FREE_PLAN")
            elif explicit_free:
                result.update(status="PASS", classification="EXPLICIT_FREE_SUBSCRIPTION")
            elif not active and model == "bundled":
                result.update(status="PASS", classification="NO_PAID_WORKERS_SUBSCRIPTION_AND_BUNDLED_MODEL")
            else:
                result["reason"] = "UNRECOGNIZED_PLAN_EVIDENCE"
    else:
        result["reason"] = "PLAN_READ_NOT_AUTHORIZED_OR_UNAVAILABLE"
    path = Path(sys.argv[1])
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(result, ensure_ascii=False, indent=2)+"\n")
    print(json.dumps(result, ensure_ascii=False))
    if result["status"] != "PASS":
        raise SystemExit(65)


if __name__ == "__main__":
    main()
