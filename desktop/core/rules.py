from __future__ import annotations

import hashlib
import json
from pathlib import Path


class RuleConfigurationError(ValueError):
    pass


def load_rule_manifest(path=None):
    path = Path(path) if path else Path(__file__).parents[1] / "config" / "rules.v1.2.json"
    payload = path.read_bytes()
    config = json.loads(payload.decode("utf-8"))
    required = {"version", "effective_from", "numeric_type", "grade_scores", "models", "rules"}
    missing = required - set(config)
    if missing:
        raise RuleConfigurationError(f"規則檔缺少欄位：{', '.join(sorted(missing))}")
    if config["numeric_type"] != "Decimal" or not config.get("first_match_wins"):
        raise RuleConfigurationError("規則必須使用 Decimal 且採第一個命中即停止")
    seen_ids, priorities = set(), set()
    valid_grades = set(config["grade_scores"])
    for rule in config["rules"]:
        for key in ("metric", "priority", "rule_id", "grade", "condition"):
            if key not in rule:
                raise RuleConfigurationError(f"規則缺少 {key}")
        if rule["rule_id"] in seen_ids:
            raise RuleConfigurationError(f"rule_id 重複：{rule['rule_id']}")
        priority_key = (rule["metric"], rule["priority"])
        if priority_key in priorities:
            raise RuleConfigurationError(f"優先序重複：{priority_key}")
        if rule["grade"] not in valid_grades:
            raise RuleConfigurationError(f"未知評等：{rule['grade']}")
        seen_ids.add(rule["rule_id"])
        priorities.add(priority_key)
    config["checksum"] = hashlib.sha256(payload).hexdigest()
    return config
