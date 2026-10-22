#!/usr/bin/env python3
"""카드 스펙 JSON → queue/<날짜>/<글ID>/ (01.png… + post.json)

사용: python tools/cards/make_post.py <spec.json> --date 2026-10-24 --at 2026-10-24T08:30+09:00 [--slot 오전]
스펙 형식은 GUIDE.md / example_spec.json. 넘침·작은 글씨가 있으면 실패 코드 1로 끝난다.
"""
import argparse, json, os, re, sys
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, HERE)
import cardkit as CK  # noqa: E402

ap = argparse.ArgumentParser()
ap.add_argument("spec"); ap.add_argument("--date", required=True); ap.add_argument("--at", required=True)
ap.add_argument("--slot", default="")
a = ap.parse_args()
d = json.load(open(a.spec, encoding="utf-8"))
pid = d["pid"]
root = os.path.abspath(os.path.join(HERE, "..", ".."))
od = os.path.join(root, "queue", a.date, pid)
os.makedirs(od, exist_ok=True)
CK.REPORT.clear()
paths = CK.render_cards(d["spec"], od)
bad = [r for r in CK.REPORT if r["overflow"] or r["below_min_font"]]
tags = re.findall(r"(?<!\S)#[^\s#]+", d["caption"])
post = {"id": f"{a.date}_{pid}", "title": d.get("title", ""), "slot": a.slot, "publish_at": a.at,
        "channels": {"instagram": {"images": [os.path.basename(p) for p in paths], "caption": d["caption"]},
                     "threads": {"text": d["threads"]}}}
json.dump(post, open(os.path.join(od, "post.json"), "w", encoding="utf-8"), ensure_ascii=False, indent=1)
print(json.dumps({"dir": os.path.relpath(od, root), "cards": len(paths), "caption_len": len(d["caption"]),
                  "threads_len": len(d["threads"]), "hashtags": len(tags), "problems": bad}, ensure_ascii=False))
problems = bool(bad) or len(tags) > 5 or len(d["caption"]) > 2200 or len(d["threads"]) > 500
sys.exit(1 if problems else 0)
