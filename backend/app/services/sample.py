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


class SampleService:
    def list_entries(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> tuple[list[dict[str, Any]], int]:
        rows = store.rows(MODULE)
        if keyword:
            rows = [row for row in rows if keyword in str(row.get("样品编号", ""))]
        if status:
            rows = [row for row in rows if row.get("status") == status]
        total = len(rows)
        start = max(page - 1, 0) * size
        return rows[start:start + size], total

    def get_entry(self, entry_id: int) -> dict[str, Any] | None:
        return store.find(MODULE, entry_id)

    def overview(
        self,
        *,
        keyword: str | None = None,
        status: str | None = None,
        page: int = 1,
        size: int = 20,
    ) -> dict[str, Any]:
        """概览视图数据：统计卡片与筛选列表在同一次读取里完成，数量口径不会互相打架。

        统计指标始终基于当前全量记录实时计算（今日接收按接收日期=今天、待接收样品按
        流转状态=待接收），列表则按调用方给的条件过滤；两者同源，多次打开也不会出现
        卡片数字和记录对不上的情况。
        """
        items, total = self.list_entries(keyword=keyword, status=status, page=page, size=size)
        rows = store.rows(MODULE)
        today = date.today().isoformat()
        stats = [
            {"label": "样品总数", "value": len(rows)},
            {"label": "今日接收", "value": sum(1 for row in rows if str(row.get("接收日期") or "")[:10] == today)},
            {"label": "待接收样品", "value": sum(1 for row in rows if row.get("status") == STATUS_ORDER[0])},
        ]
        # 列表里的接收状态以流转状态为准，和统计卡片保持同一口径；原始字段不改动。
        display_items = [{**item, "接收状态": item.get("status")} for item in items]
        return {"stats": stats, "items": display_items, "total": total, "page": page, "size": size}

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
