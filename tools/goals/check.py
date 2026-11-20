#!/usr/bin/env python3
"""인스타 일일 목표 점검: 최신 state/insights 로 날짜별(KST) 릴스 성과를 모으고 goals/daily_log.json 목표와 비교한다.
사용: python tools/goals/check.py [YYYY-MM-DD]  (기본: 어제)
미집계 값은 0으로 채우지 않고 '미집계'로 둔다."""
import json, glob, os, sys
from datetime import datetime, timedelta, timezone
KST = timezone(timedelta(hours=9))
root = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
day = sys.argv[1] if len(sys.argv) > 1 else (datetime.now(KST) - timedelta(days=1)).strftime("%Y-%m-%d")
f = sorted(glob.glob(os.path.join(root, "state", "insights", "*.json")))[-1]
ins = json.load(open(f, encoding="utf-8"))
coll = datetime.fromisoformat(ins["collected_at"])
reels, best = [], {"reach": 0, "watch": 0}
for m in ins.get("media", []):
    if m.get("media_product_type") != "REELS":
        continue
    ts = datetime.strptime(m["timestamp"], "%Y-%m-%dT%H:%M:%S%z").astimezone(KST)
    w = m.get("ig_reels_avg_watch_time")
    best["reach"] = max(best["reach"], m.get("reach") or 0)
    if w: best["watch"] = max(best["watch"], w / 1000)
    if ts.strftime("%Y-%m-%d") == day:
        inter = sum((m.get(k) or 0) for k in ("likes", "comments", "saved", "shares"))
        reels.append({"time": ts.strftime("%H:%M"), "hours": round((coll - ts).total_seconds() / 3600, 1),
                      "caption": (m.get("caption_head") or "")[:30], "reach": m.get("reach"), "views": m.get("views"),
                      "avg_watch_sec": round(w / 1000, 2) if w else "미집계", "interactions": inter,
                      "link": m.get("permalink")})
acct = ins["account"]
out = {"day": day, "insights_file": os.path.basename(f), "collected_at": ins["collected_at"],
       "followers": acct.get("followers_count"), "following": acct.get("follows_count"), "media": acct.get("media_count"),
       "reels": reels, "best_ever": best}
log = json.load(open(os.path.join(root, "goals", "daily_log.json"), encoding="utf-8"))
g = (log.get(day) or {}).get("goals")
if g and reels:
    act = {"followers_total": acct.get("followers_count"),
           "best_reel_reach": max(r["reach"] or 0 for r in reels),
           "avg_watch_sec": max((r["avg_watch_sec"] for r in reels if isinstance(r["avg_watch_sec"], float)), default=None),
           "interactions": sum(r["interactions"] for r in reels)}
    out["actual"] = act
    out["achieved"] = {k: (act[k] is not None and act[k] >= v) for k, v in g.items()}
    out["goals"] = g
elif g:
    out["note"] = "목표는 있으나 그날 게시된 릴스가 인사이트에 없음(게시 실패 또는 미수집)"
print(json.dumps(out, ensure_ascii=False, indent=1))
