# /// script
# requires-python = ">=3.12"
# dependencies = []
# ///
"""Write `stale_after` into capacity.json: `refreshed_at` plus the interval and margin in ../freshness.json.

Every reader (a lookup, the night shift, model-steward) compares against this one timestamp, so the
freshness rule has one home. The margin covers the scheduled job's retry slot: a week whose run succeeds
only on its last retry must not look stale.
"""

import json
from datetime import datetime, timedelta
from pathlib import Path

CAPACITY = Path.home() / ".local" / "state" / "ai-capacity" / "capacity.json"
FRESHNESS = Path(__file__).resolve().parent.parent / "freshness.json"

rule = json.loads(FRESHNESS.read_text())
facts = json.loads(CAPACITY.read_text())
refreshed = datetime.fromisoformat(facts["refreshed_at"])
facts["stale_after"] = (refreshed + timedelta(days=rule["refresh_every_days"] + rule["margin_days"])).isoformat(timespec="minutes")
CAPACITY.write_text(json.dumps(facts, indent=2, ensure_ascii=False) + "\n")
print(f"stale_after: {facts['stale_after']}")
