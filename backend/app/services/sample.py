"""样品接收业务规则：状态流转、字段校验与筛选口径都收在这里。"""
from __future__ import annotations

from datetime import date
from typing import Any

from app.store import store

MODULE = "sample"
REQUIRED_FIELDS = ["样品编号", "样品名称", "委托单位"]
STATUS_ORDER = ["待接收", "已接收", "已退回", "已废弃"]
ACTION_RULES = {"确认接收": "已接收", "退回样品": "已退回", "废弃样品": "已废弃"}
NEGATIVE_ACTIONS = []
OVERVIEW_FIELDS = ["样品编号", "样品名称", "委托单位", "样品类型"]


class SampleService:
    def _canonical_status(self, row: dict[str, Any]) -> str:
        return str(row.get("status") or row.get("接收状态") or "")

    def _filter_rows(
        self,
        rows: list[dict[str, Any]],
        *,
        keyword: str | None = None,
        status: str | None = None,
        client: str | None = None,
        sample_type: str | None = None,
        sample_name: str | None = None,
    ) -> list[dict[str, Any]]:
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("样品编号", ""))]
        if sample_name:
            rows = [row for row in rows if sample_name in str(row.get("样品名称", ""))]
        if client:
            rows = [row for row in rows if client in str(row.get("委托单位", ""))]
        if sample_type:
            rows = [row for row in rows if sample_type in str(row.get("样品类型", ""))]
        if status:
            rows = [row for row in rows if self._canonical_status(row) == status]
        return rows

    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = self._filter_rows(store.rows(MODULE), keyword=keyword, status=status)
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def overview(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        client: str | None = None,
        sample_type: str | None = None,
        sample_name: str | None = None,
    ) -> dict[str, Any]:
        today = date.today().isoformat()
        rows = self._filter_rows(
            store.rows(MODULE),
            keyword=keyword,
            status=status,
            client=client,
            sample_type=sample_type,
            sample_name=sample_name,
        )
        items = [
            {
                "id": row.get("id"),
                "样品编号": row.get("样品编号"),
                "样品名称": row.get("样品名称"),
                "委托单位": row.get("委托单位"),
                "样品类型": row.get("样品类型"),
                "接收日期": row.get("接收日期"),
                "接收状态": self._canonical_status(row),
            }
            for row in rows
        ]
        received_today = [
            row for row in items
            if row["接收状态"] == "已接收" and str(row.get("接收日期") or "") == today
        ]
        pending = [row for row in items if row["接收状态"] == "待接收"]
        filters = {
            "keyword": keyword or "",
            "status": status or "",
            "client": client or "",
            "sample_type": sample_type or "",
            "sample_name": sample_name or "",
        }
        return {
            "date": today,
            "total": len(items),
            "filters": filters,
            "cards": [
                {"label": "今日接收", "value": len(received_today)},
                {"label": "待接收样品", "value": len(pending)},
            ],
            "items": items,
        }

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def create_entry(self, values: dict[str, Any]) -> tuple[dict[str, Any] | None, list[str]]:
        missing = [field for field in REQUIRED_FIELDS if not str(values.get(field) or "").strip()]
        if missing:
            return None, missing
        rows = store.rows(MODULE)
        entry = {"id": max((int(row.get("id", 0)) for row in rows), default=0) + 1}
        entry.update({field: values.get(field) for field in REQUIRED_FIELDS})
        entry["status"] = STATUS_ORDER[0]
        entry["pending"] = True
        entry["abnormal"] = False
        rows.append(entry)
        return entry, []

    def run_action(self, entry_id: int, action: str) -> tuple[dict[str, Any] | None, str]:
        entry = store.find(MODULE, entry_id)
        if entry is None:
            return None, f"检测样品 {entry_id} 不存在或已归档"
        if action not in ACTION_RULES:
            return None, f"动作「{action}」不属于样品接收可执行范围"
        target = ACTION_RULES[action]
        if target not in STATUS_ORDER:
            return None, f"目标状态「{target}」不在允许的状态序列里"
        entry["status"] = target
        entry["pending"] = target != STATUS_ORDER[-1]
        entry["abnormal"] = action in NEGATIVE_ACTIONS
        return entry, f"检测样品已{action}"
