#!/usr/bin/env python3
"""깨알이 재테크툰 릴스: 스펙 JSON → queue/<날짜>/<ID>/reel.mp4 + reel_cover.png (+ post.json 갱신)

11/26 방향 전환(500개 계정 조사: 돈+툰/캐릭터 소형 계정 릴스 조회 중앙값 1,744 vs 정보카드 268).
사용: python tools/reels/make_toon.py <spec.json> --date 2026-11-27 --at 2026-11-27T12:30+09:00
스펙: {"pid","title","topbar":[줄...],"panels":[{"expr":"shock","say":"말풍선","narr":"아래 설명","dur":2.2}...],
       "cta":"마지막 컷 아래 한 줄(선택)","caption":"...","music_seed":숫자(선택)}
 - topbar 줄은 문자열 또는 [["강조","#FFC531"]] 형식
 - expr 은 tools/char/kkaeal.py PRESETS 이름
"""
import argparse, json, os, subprocess, sys, tempfile, html
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "char"))
import kkaeal  # noqa: E402

FD = os.path.join(ROOT, "tools", "cards", "fonts")
W, H = 1080, 1920


def rich(line):
    if isinstance(line, str):
        return html.escape(line)
    out = ""
    for p in line:
        if isinstance(p, str):
            out += html.escape(p)
        else:
            out += f'<span style="color:{p[1] if len(p) > 1 else "#FFC531"}">{html.escape(p[0])}</span>'
    return out


def panel_html(spec, i):
    p = spec["panels"][i]
    n = len(spec["panels"])
    top = "<br>".join(rich(x) for x in spec["topbar"])
    dots = "".join(f'<i class="{"on" if k <= i else ""}"></i>' for k in range(n))
    say = html.escape(p.get("say", "")).replace("\n", "<br>")
    narr = html.escape(p.get("narr", "")).replace("\n", "<br>").replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")
    cta = ""
    if i == n - 1 and spec.get("cta"):
        cta = f'<div class="cta" style="display:block">{html.escape(spec["cta"]).replace(chr(10), "<br>")}</div>'
    bubble = f'<div class="say">{say}</div>' if say else ""
    char = kkaeal.expr(p["expr"], 640)
    return f"""<!doctype html><meta charset="utf-8"><style>
@font-face{{font-family:P;font-weight:900;src:url(file://{FD}/Pretendard-Black.otf)}}
@font-face{{font-family:P;font-weight:800;src:url(file://{FD}/Pretendard-ExtraBold.otf)}}
@font-face{{font-family:P;font-weight:700;src:url(file://{FD}/Pretendard-Bold.otf)}}
*{{box-sizing:border-box}}body{{margin:0;width:{W}px;height:{H}px;background:#FFF8E6;font-family:P,sans-serif;position:relative;overflow:hidden;color:#4A2E1B}}
.head{{position:absolute;top:150px;left:84px;right:84px;display:flex;justify-content:space-between;align-items:center}}
.name{{font-weight:900;font-size:54px;letter-spacing:-1px}}.name small{{font-size:34px;font-weight:800;color:#B08A5A;margin-left:10px}}
.tag{{background:#F5B82E;color:#4A2E1B;font-weight:900;font-size:36px;padding:10px 26px;border-radius:40px;border:5px solid #4A2E1B}}
.bar{{position:absolute;top:250px;left:0;right:0;height:330px;background:#24346B;color:#fff;font-weight:900;font-size:86px;line-height:1.24;letter-spacing:-2px;display:flex;align-items:center;justify-content:center;text-align:center;padding:0 50px}}
.panel{{position:absolute;top:620px;left:60px;right:60px;height:690px;background:#fff;border:8px solid #4A2E1B;border-radius:44px;overflow:hidden}}
.panel svg{{position:absolute;left:50%;bottom:-75px;transform:translateX(-50%)}}
.say{{position:absolute;top:34px;left:40px;right:40px;background:#fff;border:7px solid #4A2E1B;border-radius:40px;padding:22px 30px;font-weight:900;font-size:58px;line-height:1.25;text-align:center;letter-spacing:-1px;z-index:2}}
.say:after{{content:"";position:absolute;bottom:-34px;left:50%;margin-left:-20px;border:20px solid transparent;border-top:28px solid #4A2E1B}}
.narr{{position:absolute;top:1335px;left:84px;right:84px;font-weight:800;font-size:50px;line-height:1.32;text-align:center;letter-spacing:-1px}}
.narr b{{color:#E0611F}}
.cta{{position:absolute;top:1335px;left:84px;right:84px;font-weight:900;font-size:56px;line-height:1.3;text-align:center;color:#E0611F;display:none}}
.dots{{position:absolute;top:1590px;left:0;right:0;display:flex;justify-content:center;gap:14px}}.dots i{{width:22px;height:22px;border-radius:50%;background:#E9DCC0}}.dots i.on{{background:#4A2E1B}}
</style>
<div class="head"><div class="name">깨알이<small>사회초년생 재테크툰</small></div><div class="tag">{html.escape(spec.get("series", "깨알 정보"))}</div></div>
<div class="bar"><div>{top}</div></div>
<div class="panel">{bubble}{char}</div>
<div class="narr">{narr}</div>{cta}
<div class="dots">{dots}</div>"""


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("--date", required=True); ap.add_argument("--at", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    od = a.out or os.path.join(ROOT, "queue", a.date, spec["pid"])
    os.makedirs(od, exist_ok=True)
    tmp = tempfile.mkdtemp()
    from playwright.sync_api import sync_playwright
    paths = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()
        pg = b.new_page(viewport={"width": W, "height": H})
        for i in range(len(spec["panels"])):
            hp = os.path.join(tmp, f"p{i}.html")
            open(hp, "w", encoding="utf-8").write(panel_html(spec, i))
            pg.goto("file://" + hp); pg.wait_for_timeout(250)
            pp = os.path.join(tmp, f"p{i}.png"); pg.screenshot(path=pp); paths.append(pp)
        b.close()
    import shutil
    shutil.copy(paths[0], os.path.join(od, "reel_cover.png"))
    durs = [float(p.get("dur", 2.2)) for p in spec["panels"]]
    fps, XF = 30, 0.25
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p, d in zip(paths, durs):
        cmd += ["-loop", "1", "-t", f"{d}", "-i", p]
    total = sum(durs) - XF * (len(durs) - 1)
    sys.path.insert(0, HERE)
    import music  # noqa: E402
    wav = os.path.join(tmp, "music.wav")
    music.save(wav, music.make(total + 0.2, seed=int(spec.get("music_seed", sum(map(ord, spec["pid"]))))))
    cmd += ["-i", wav]
    fl = [f"[{i}:v]scale={W}:{H},fps={fps},setsar=1,format=yuv420p[v{i}]" for i in range(len(paths))]
    prev, off = "v0", 0.0
    for i in range(1, len(paths)):
        off += durs[i - 1] - XF
        fl.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XF}:offset={off:.2f}[x{i}]")
        prev = f"x{i}"
    cmd += ["-filter_complex", ";".join(fl), "-map", f"[{prev}]", "-map", f"{len(paths)}:a",
            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(fps), "-b:v", "6M",
            "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", os.path.join(od, "reel.mp4")]
    subprocess.run(cmd, check=True)
    pj = os.path.join(od, "post.json")
    post = json.load(open(pj, encoding="utf-8")) if os.path.exists(pj) else {
        "id": f"{a.date}_{spec['pid']}", "title": spec.get("title", ""), "publish_at": a.at, "channels": {}}
    post["title"] = spec.get("title", post.get("title", ""))
    post["publish_at"] = a.at
    post["channels"]["instagram_reel"] = {"video": "reel.mp4", "caption": spec["caption"], "cover": "reel_cover.png"}
    json.dump(post, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          os.path.join(od, "reel.mp4")], capture_output=True, text=True).stdout.strip()
    print(json.dumps({"dir": os.path.relpath(od, ROOT), "panels": len(paths), "duration": dur,
                      "hashtags": spec["caption"].count("#"), "frames": paths}, ensure_ascii=False))


if __name__ == "__main__":
    main()
