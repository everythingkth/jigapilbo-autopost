#!/usr/bin/env python3
"""지갑일보 자동 게시기.

queue/<날짜>/<ID>/post.json 을 읽어서, 게시 시각이 지났고 아직 안 올린 채널만 올린다.
결과(게시 ID·링크)는 state/published.json 에 기록한다. 실패한 채널은 기록하지 않으므로
다음 실행 때 다시 시도한다(같은 채널을 두 번 올리지 않도록 성공 기록을 먼저 확인).

채널
  instagram        카드 캐러셀 (Instagram API with Instagram Login)
  instagram_reel   릴스 (같은 토큰)
  threads          스레드 글(+선택: 이미지 1장)
  youtube          쇼츠 업로드 (YouTube Data API v3, OAuth refresh token)

환경변수(GitHub Secrets)
  IG_USER_ID, IG_TOKEN
  THREADS_USER_ID, THREADS_TOKEN
  YT_CLIENT_ID, YT_CLIENT_SECRET, YT_REFRESH_TOKEN
  MEDIA_BASE_URL   예: https://raw.githubusercontent.com/<owner>/<repo>/main
옵션
  DRY_RUN=1        API 호출 없이 무엇을 올릴지만 출력
  ONLY=<post id>   특정 글만
"""
import datetime as dt
import json
import os
import re
import sys
import tempfile
import time
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
QUEUE = ROOT / "queue"
STATE = ROOT / "state" / "published.json"
KST = dt.timezone(dt.timedelta(hours=9))

IG_API = "https://graph.instagram.com/v23.0"
TH_API = "https://graph.threads.net/v1.0"
IG_MAX_HASHTAGS = 5          # 인스타 앱이 캡션 해시태그를 5개로 제한
IG_CAPTION_MAX = 2200
THREADS_MAX = 500
DRY = os.environ.get("DRY_RUN") == "1"


class SkipChannel(Exception):
    """설정(시크릿)이 없어서 이 채널은 건너뜀."""


def log(*a):
    print(*a, flush=True)


def env(name):
    v = os.environ.get(name, "").strip()
    if not v:
        raise SkipChannel(f"{name} 없음")
    return v


def load_state():
    if STATE.exists():
        return json.loads(STATE.read_text(encoding="utf-8"))
    return {}


def save_state(st):
    STATE.parent.mkdir(parents=True, exist_ok=True)
    STATE.write_text(json.dumps(st, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")


def media_url(post_dir: Path, rel: str) -> str:
    if rel.startswith("http://") or rel.startswith("https://"):
        return rel
    base = env("MEDIA_BASE_URL").rstrip("/")
    path = (post_dir / rel).resolve().relative_to(ROOT).as_posix()
    return f"{base}/{requests.utils.quote(path)}"


def limit_hashtags(text: str, n: int) -> str:
    seen = 0

    def rep(m):
        nonlocal seen
        seen += 1
        return m.group(0) if seen <= n else ""
    out = re.sub(r"(?<!\S)#[^\s#]+", rep, text)
    out = re.sub(r"[ \t]+\n", "\n", out)
    return re.sub(r"[ \t]{2,}", " ", out).strip()


def check(resp: requests.Response, what: str):
    try:
        data = resp.json()
    except ValueError:
        data = {"raw": resp.text[:500]}
    if resp.status_code >= 400 or (isinstance(data, dict) and "error" in data):
        raise RuntimeError(f"{what} 실패 HTTP {resp.status_code}: {json.dumps(data, ensure_ascii=False)[:800]}")
    return data


# ---------------------------------------------------------------- Instagram
def ig_wait(container_id, token, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = check(requests.get(f"{IG_API}/{container_id}", params={"fields": "status_code,status", "access_token": token}, timeout=30), "IG 상태 확인")
        sc = d.get("status_code")
        if sc == "FINISHED":
            return
        if sc in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"IG 컨테이너 {container_id} {sc}: {d.get('status')}")
        time.sleep(5)
    raise RuntimeError(f"IG 컨테이너 {container_id} 처리 시간 초과")


def ig_publish(container_id, uid, token):
    d = check(requests.post(f"{IG_API}/{uid}/media_publish", data={"creation_id": container_id, "access_token": token}, timeout=60), "IG 게시")
    mid = d["id"]
    link = check(requests.get(f"{IG_API}/{mid}", params={"fields": "permalink", "access_token": token}, timeout=30), "IG 링크").get("permalink")
    return {"id": mid, "url": link}


_RECENT = None


def ig_existing(uid, token, caption, reel):
    """같은 캡션으로 이미 올라간 게시물이 있으면 그 게시물을 돌려준다 (중복 게시 방지)."""
    global _RECENT
    if _RECENT is None:
        d = check(requests.get(f"{IG_API}/{uid}/media", params={"fields": "id,caption,media_type,media_product_type,permalink", "limit": 30, "access_token": token}, timeout=30), "IG 최근 게시물")
        _RECENT = d.get("data", [])
    want = caption.strip()
    for m in _RECENT:
        if (m.get("caption") or "").strip() != want:
            continue
        is_reel = m.get("media_product_type") == "REELS"
        if is_reel == reel:
            return {"id": m["id"], "url": m.get("permalink"), "found_existing": True}
    return None


def do_instagram(post_dir, ch):
    uid, token = env("IG_USER_ID"), env("IG_TOKEN")
    caption = limit_hashtags(ch["caption"], IG_MAX_HASHTAGS)[:IG_CAPTION_MAX]
    urls = [media_url(post_dir, p) for p in ch["images"]]
    if DRY:
        return {"dry": True, "images": urls, "caption": caption}
    ex = ig_existing(uid, token, caption, reel=False)
    if ex:
        return ex
    if len(urls) == 1:
        c = check(requests.post(f"{IG_API}/{uid}/media", data={"image_url": urls[0], "caption": caption, "access_token": token}, timeout=60), "IG 이미지")
        ig_wait(c["id"], token)
        return ig_publish(c["id"], uid, token)
    kids = []
    for u in urls:  # 순서 = 캐러셀 순서
        c = check(requests.post(f"{IG_API}/{uid}/media", data={"image_url": u, "is_carousel_item": "true", "access_token": token}, timeout=60), "IG 카드")
        kids.append(c["id"])
    for k in kids:
        ig_wait(k, token)
    c = check(requests.post(f"{IG_API}/{uid}/media", data={"media_type": "CAROUSEL", "children": ",".join(kids), "caption": caption, "access_token": token}, timeout=60), "IG 캐러셀")
    ig_wait(c["id"], token)
    return ig_publish(c["id"], uid, token)


def do_instagram_reel(post_dir, ch):
    uid, token = env("IG_USER_ID"), env("IG_TOKEN")
    caption = limit_hashtags(ch["caption"], IG_MAX_HASHTAGS)[:IG_CAPTION_MAX]
    video = media_url(post_dir, ch["video"])
    data = {"media_type": "REELS", "video_url": video, "caption": caption, "share_to_feed": "true", "access_token": token}
    if ch.get("cover"):
        data["cover_url"] = media_url(post_dir, ch["cover"])
    if DRY:
        return {"dry": True, "video": video, "caption": caption}
    ex = ig_existing(uid, token, caption, reel=True)
    if ex:
        return ex
    c = check(requests.post(f"{IG_API}/{uid}/media", data=data, timeout=60), "IG 릴스")
    ig_wait(c["id"], token, timeout=900)
    return ig_publish(c["id"], uid, token)


# ---------------------------------------------------------------- Threads
def th_wait(cid, token, timeout=600):
    t0 = time.time()
    while time.time() - t0 < timeout:
        d = check(requests.get(f"{TH_API}/{cid}", params={"fields": "status,error_message", "access_token": token}, timeout=30), "스레드 상태")
        s = d.get("status")
        if s in ("FINISHED", "PUBLISHED"):
            return
        if s in ("ERROR", "EXPIRED"):
            raise RuntimeError(f"스레드 컨테이너 {cid} {s}: {d.get('error_message')}")
        time.sleep(5)
    raise RuntimeError("스레드 처리 시간 초과")


def do_threads(post_dir, ch):
    uid, token = env("THREADS_USER_ID"), env("THREADS_TOKEN")
    text = ch["text"].strip()
    if len(text) > THREADS_MAX:
        raise RuntimeError(f"스레드 글이 {len(text)}자라 500자 제한을 넘음 — 글을 줄여야 함")
    data = {"media_type": "TEXT", "text": text, "access_token": token}
    if ch.get("image"):
        data.update(media_type="IMAGE", image_url=media_url(post_dir, ch["image"]))
    if ch.get("video"):
        data.update(media_type="VIDEO", video_url=media_url(post_dir, ch["video"]))
    if DRY:
        return {"dry": True, "type": data["media_type"], "chars": len(text)}
    c = check(requests.post(f"{TH_API}/{uid}/threads", data=data, timeout=60), "스레드 생성")
    th_wait(c["id"], token)
    d = check(requests.post(f"{TH_API}/{uid}/threads_publish", data={"creation_id": c["id"], "access_token": token}, timeout=60), "스레드 게시")
    link = check(requests.get(f"{TH_API}/{d['id']}", params={"fields": "permalink", "access_token": token}, timeout=30), "스레드 링크").get("permalink")
    return {"id": d["id"], "url": link}


# ---------------------------------------------------------------- YouTube
def yt_access_token():
    r = requests.post("https://oauth2.googleapis.com/token", data={
        "client_id": env("YT_CLIENT_ID"), "client_secret": env("YT_CLIENT_SECRET"),
        "refresh_token": env("YT_REFRESH_TOKEN"), "grant_type": "refresh_token"}, timeout=30)
    return check(r, "유튜브 토큰")["access_token"]


def do_youtube(post_dir, ch):
    for k in ("YT_CLIENT_ID", "YT_CLIENT_SECRET", "YT_REFRESH_TOKEN"):
        env(k)
    src = ch["video"]
    meta = {
        "snippet": {"title": ch["title"][:100], "description": ch["description"][:5000],
                    "tags": ch.get("tags", []), "categoryId": ch.get("category", "25"),
                    "defaultLanguage": "ko", "defaultAudioLanguage": "ko"},
        "status": {"privacyStatus": ch.get("privacy", "public"), "selfDeclaredMadeForKids": False,
                   "containsSyntheticMedia": bool(ch.get("synthetic_media", True))},
    }
    if DRY:
        return {"dry": True, "video": src, "title": meta["snippet"]["title"]}
    token = yt_access_token()
    with tempfile.TemporaryDirectory() as td:
        path = Path(td) / "v.mp4"
        if src.startswith("http"):
            with requests.get(src, stream=True, timeout=120) as r:
                r.raise_for_status()
                with open(path, "wb") as f:
                    for chunk in r.iter_content(1 << 20):
                        f.write(chunk)
        else:
            path = post_dir / src
        size = path.stat().st_size
        init = requests.post(
            "https://www.googleapis.com/upload/youtube/v3/videos?uploadType=resumable&part=snippet,status",
            headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json; charset=UTF-8",
                     "X-Upload-Content-Type": "video/mp4", "X-Upload-Content-Length": str(size)},
            data=json.dumps(meta), timeout=60)
        if init.status_code >= 400:
            check(init, "유튜브 업로드 시작")
        up = init.headers["Location"]
        with open(path, "rb") as f:
            d = check(requests.put(up, headers={"Authorization": f"Bearer {token}", "Content-Type": "video/mp4"}, data=f, timeout=900), "유튜브 업로드")
    vid = d["id"]
    priv = d.get("status", {}).get("privacyStatus")
    return {"id": vid, "url": f"https://youtube.com/shorts/{vid}", "privacy": priv}


HANDLERS = {"instagram": do_instagram, "instagram_reel": do_instagram_reel, "threads": do_threads, "youtube": do_youtube}


def due(post, now):
    at = post.get("publish_at")
    if not at:
        return True
    t = dt.datetime.fromisoformat(at)
    if t.tzinfo is None:
        t = t.replace(tzinfo=KST)
    return now >= t


def main():
    now = dt.datetime.now(KST)
    only = os.environ.get("ONLY")
    st = load_state()
    failures = 0
    for pj in sorted(QUEUE.glob("*/*/post.json")):
        post = json.loads(pj.read_text(encoding="utf-8"))
        pid = post["id"]
        if only and pid != only:
            continue
        if not due(post, now):
            log(f"[{pid}] 예약 {post.get('publish_at')} — 아직")
            continue
        rec = st.setdefault(pid, {})
        for name, ch in post.get("channels", {}).items():
            if ch.get("enabled") is False:
                continue
            if name in rec and rec[name].get("url") or (name in rec and rec[name].get("id")):
                continue
            if ch.get("not_before"):
                if not due({"publish_at": ch["not_before"]}, now):
                    log(f"[{pid}] {name}: {ch['not_before']} 이후")
                    continue
            try:
                res = HANDLERS[name](pj.parent, ch)
            except SkipChannel as e:
                log(f"[{pid}] {name}: 건너뜀 ({e})")
                continue
            except Exception as e:  # noqa: BLE001
                failures += 1
                log(f"[{pid}] {name}: 실패 — {e}")
                rec.setdefault("_errors", {})[name] = {"at": now.isoformat(timespec="seconds"), "error": str(e)[:500]}
                continue
            if DRY:
                log(f"[{pid}] {name}: (DRY) {json.dumps(res, ensure_ascii=False)[:300]}")
                continue
            res["at"] = dt.datetime.now(KST).isoformat(timespec="seconds")
            rec[name] = res
            rec.get("_errors", {}).pop(name, None)
            log(f"[{pid}] {name}: {'이미 올라가 있음(기록만 보완)' if res.get('found_existing') else '게시 완료'} {res.get('url')}")
            save_state(st)  # 채널마다 바로 저장 → 중복 게시 방지
        if not rec:
            st.pop(pid, None)
    if not DRY:
        save_state(st)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
