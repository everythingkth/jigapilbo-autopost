#!/usr/bin/env python3
"""게시패키지 폴더 하나를 queue/<날짜>/<ID>/ 로 옮겨 post.json 을 만든다.
사용: enqueue.py <패키지폴더> <날짜 YYYY-MM-DD> <ID> --video URL [--at ISO] [--skip instagram ...]"""
import argparse, json, re, shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
ap = argparse.ArgumentParser()
ap.add_argument("pkg"); ap.add_argument("date"); ap.add_argument("pid")
ap.add_argument("--video", default=None)
ap.add_argument("--at", default=None)
ap.add_argument("--skip", nargs="*", default=[])
a = ap.parse_args()
pkg = Path(a.pkg)
rd = lambda p: (pkg / p).read_text(encoding="utf-8").strip()
out = ROOT / "queue" / a.date / a.pid
(out / "cards").mkdir(parents=True, exist_ok=True)
cards = sorted((pkg / "사진").glob(f"{a.pid}_card_*.png"))
for c in cards:
    shutil.copy2(c, out / "cards" / c.name.split("_card_")[1])
ig = rd("인스타_스레드/인스타_캡션.txt")
yt_desc = rd("유튜브/설명.txt")
yt_title = rd("유튜브/제목.txt")
tags = [t.lstrip("#") for t in re.findall(r"#[^\s#]+", ig) if t != "#Shorts"][:10]
ch = {
    "instagram": {"images": [f"cards/{c.name.split('_card_')[1]}" for c in cards], "caption": ig},
    "threads": {"text": rd("인스타_스레드/스레드.txt")},
}
if a.video:
    ch["instagram_reel"] = {"video": a.video, "caption": ig, "cover": "cards/01.png"}
    ch["youtube"] = {"video": a.video, "title": yt_title, "description": yt_desc, "tags": tags,
                     "privacy": "public", "synthetic_media": True}
for s in a.skip:
    ch[s]["enabled"] = False
post = {"id": f"{a.date}_{a.pid}", "publish_at": a.at, "channels": ch}
(out / "post.json").write_text(json.dumps(post, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
print(out, {k: v.get("enabled", True) for k, v in ch.items()}, "threads chars:", len(ch["threads"]["text"]))
