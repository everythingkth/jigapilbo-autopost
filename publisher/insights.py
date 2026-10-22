#!/usr/bin/env python3
"""지갑일보 인스타 성과·댓글 수집 + 답글 게시.

1) 계정 팔로워 수, 최근 게시물 50개의 좋아요·댓글·도달·저장·공유·조회 → state/insights/<날짜>.json
2) 우리 게시물에 달린 댓글 중 아직 우리가 답하지 않은 것 → state/comments_open.json
3) queue/replies/*.json 의 답글을 게시하고 결과를 state/replies_done.json 에 기록

필요: IG_USER_ID, IG_TOKEN (권한: instagram_business_basic, instagram_business_manage_insights,
      instagram_business_manage_comments). 권한이 없으면 해당 부분만 건너뛴다.
"""
import datetime as dt
import json
import os
import sys
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
STATE = ROOT / "state"
API = "https://graph.instagram.com/v23.0"
KST = dt.timezone(dt.timedelta(hours=9))
METRICS_FEED = ["reach", "saved", "shares", "views", "total_interactions", "likes", "comments"]
METRICS_REEL = METRICS_FEED + ["ig_reels_avg_watch_time"]


def get(path, **params):
    params["access_token"] = os.environ["IG_TOKEN"]
    r = requests.get(f"{API}/{path}", params=params, timeout=30)
    d = r.json()
    if r.status_code >= 400 or "error" in d:
        raise RuntimeError(str(d.get("error", d))[:300])
    return d


def metric(media_id, name):
    try:
        d = get(f"{media_id}/insights", metric=name)
        v = d["data"][0].get("values", [{}])[0].get("value")
        return v if v is not None else d["data"][0].get("total_value", {}).get("value")
    except Exception:
        return None  # 지원 안 되는 지표는 빈칸 (0으로 채우지 않음)


def collect():
    uid = os.environ["IG_USER_ID"]
    now = dt.datetime.now(KST)
    out = {"collected_at": now.isoformat(timespec="minutes"), "account": {}, "media": []}
    try:
        out["account"] = get(uid, fields="username,followers_count,follows_count,media_count")
    except Exception as e:
        out["account_error"] = str(e)
    media = get(f"{uid}/media", fields="id,caption,media_type,media_product_type,timestamp,permalink,like_count,comments_count", limit=50).get("data", [])
    for m in media:
        is_reel = m.get("media_product_type") == "REELS"
        row = {k: m.get(k) for k in ("id", "media_type", "media_product_type", "timestamp", "permalink", "like_count", "comments_count")}
        row["caption_head"] = (m.get("caption") or "").split("\n")[0][:80]
        for name in (METRICS_REEL if is_reel else METRICS_FEED):
            row[name] = metric(m["id"], name)
        out["media"].append(row)
    d = STATE / "insights"
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{now:%Y-%m-%d}.json").write_text(json.dumps(out, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"성과 수집: 게시물 {len(out['media'])}개, 팔로워 {out['account'].get('followers_count')}")
    return media


def open_comments(media):
    me = None
    try:
        me = get(os.environ["IG_USER_ID"], fields="username").get("username")
    except Exception:
        pass
    done = load(STATE / "replies_done.json", {})
    rows = []
    for m in media:
        if not m.get("comments_count"):
            continue
        try:
            cs = get(f"{m['id']}/comments", fields="id,text,username,timestamp,replies{id,username}", limit=50).get("data", [])
        except Exception as e:
            print("댓글 읽기 실패(권한 확인):", e)
            return
        for c in cs:
            if c.get("username") == me or c["id"] in done:
                continue
            replied = any(r.get("username") == me for r in (c.get("replies") or {}).get("data", []))
            if not replied:
                rows.append({"comment_id": c["id"], "media_id": m["id"], "permalink": m.get("permalink"),
                             "post": (m.get("caption") or "").split("\n")[0][:80],
                             "username": c.get("username"), "text": c.get("text"), "timestamp": c.get("timestamp")})
    (STATE / "comments_open.json").write_text(json.dumps(rows, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    print(f"답글 대기 댓글 {len(rows)}개")


def load(p, default):
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else default


def post_replies():
    qd = ROOT / "queue" / "replies"
    if not qd.exists():
        return
    done = load(STATE / "replies_done.json", {})
    for f in sorted(qd.glob("*.json")):
        items = json.loads(f.read_text(encoding="utf-8"))
        for it in items:
            cid, msg = it["comment_id"], it["message"].strip()
            if cid in done or not msg:
                continue
            r = requests.post(f"{API}/{cid}/replies", data={"message": msg[:2200], "access_token": os.environ["IG_TOKEN"]}, timeout=30)
            d = r.json()
            if r.status_code >= 400 or "error" in d:
                print(f"답글 실패 {cid}: {str(d.get('error', d))[:200]}")
                continue
            done[cid] = {"reply_id": d.get("id"), "message": msg, "at": dt.datetime.now(KST).isoformat(timespec="minutes")}
            print(f"답글 완료 {cid}")
    (STATE / "replies_done.json").write_text(json.dumps(done, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


if __name__ == "__main__":
    if not os.environ.get("IG_TOKEN") or not os.environ.get("IG_USER_ID"):
        print("IG 토큰 없음 — 건너뜀")
        sys.exit(0)
    post_replies()
    media = collect()
    open_comments(media)
