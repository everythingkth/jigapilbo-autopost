#!/usr/bin/env python3
"""릴스 스펙 JSON → queue/<날짜>/<글ID>/reel.mp4 + reel_cover.png, post.json 에 instagram_reel 채널 추가

사용: python tools/reels/make_reel.py <reel_spec.json> --date 2026-11-19 --at 2026-11-19T12:30+09:00
스펙: {"pid","date_label","section","hook":[줄...],"beats":[{"big":"90%","text":"설명"}...],"end":"마무리 한 줄","caption":"..."}
 - hook 줄은 문자열 또는 [["강조","#FF5B26"]] 형식(카드와 같은 rich 형식)
 - 1080x1920, 장면마다 살짝 확대 + 0.35초 디졸브
 - v2(11/20 벤치마크 반영): "topbar":[줄,줄] 이 있으면 검은 상단 제목 띠를 영상 내내 고정(첫 화면·그리드에서 이야기가 보이게),
   "cta":"댓글 질문" 이 있으면 마지막 장면에 댓글 유도 문구, "music":false 가 아니면 tools/reels/music.py 배경음을 깐다.
"""
import argparse, json, os, subprocess, sys, tempfile
from PIL import Image, ImageDraw
HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, "..", "cards"))
import brand as B  # noqa: E402

W, H, M = 1080, 1920, 84
SAFE_TOP, SAFE_BOTTOM = 250, 1920 - 420  # 릴스 UI(상단·하단 캡션)에 가리지 않는 영역


def parts(line):
    if isinstance(line, str):
        return [(line, B.INK)]
    out = []
    for p in line:
        if isinstance(p, str):
            out.append((p, B.INK))
        else:
            out.append((p[0], p[1] if len(p) > 1 else B.ACCENT))
    return out


def fit(d, lines, name, start, stop, max_w):
    px = start
    while px > stop:
        f = B.font(name, px)
        if all(sum(B.tw(d, t, f)[0] for t, _ in ln) <= max_w for ln in lines):
            return px
        px -= 4
    return stop


BAR_TOP, BAR_BOT = 250, 610


def topbar(im, d, spec):
    d.rectangle([0, BAR_TOP, W, BAR_BOT], fill=(17, 17, 17))
    lines = [parts(x) for x in spec["topbar"]]
    lines = [[(t, (255, 255, 255) if c == B.INK else c) for t, c in ln] for ln in lines]
    px = fit(d, lines, "black", 104, 60, W - 2 * 60)
    f = B.font("black", px)
    lh = int(px * 1.28)
    y = (BAR_TOP + BAR_BOT) // 2 - lh * len(lines) // 2
    for ln in lines:
        wsum = sum(B.tw(d, t, f)[0] for t, _ in ln)
        x = (W - wsum) // 2
        for t, c in ln:
            d.text((x, y), t, font=f, fill=c)
            x += B.tw(d, t, f)[0]
        y += lh


def base(spec, idx, total):
    im = Image.new("RGB", (W, H), B.PAPER)
    d = ImageDraw.Draw(im)
    if spec.get("topbar"):
        topbar(im, d, spec)
        d.text((M, 150), B.BRAND, font=B.font("mast", 52), fill=B.INK)
        bw = (W - 2 * M - (total - 1) * 12) / total
        for i in range(total):
            x0 = M + i * (bw + 12)
            d.rounded_rectangle([x0, SAFE_BOTTOM + 30, x0 + bw, SAFE_BOTTOM + 42], radius=6,
                                fill=B.INK if i <= idx else B.PAPER_DARK)
        return im, d
    f = B.font("bold", 40)
    d.text((M, SAFE_TOP - 110), B.BRAND, font=B.font("mast", 64), fill=B.INK)
    lab = f"{spec['date_label']} · {spec['section']}"
    d.text((W - M - B.tw(d, lab, f)[0], SAFE_TOP - 96), lab, font=f, fill=B.INK_SOFT)
    d.rectangle([M, SAFE_TOP - 20, W - M, SAFE_TOP - 14], fill=B.INK)
    # 진행 막대
    bw = (W - 2 * M - (total - 1) * 12) / total
    for i in range(total):
        x0 = M + i * (bw + 12)
        d.rounded_rectangle([x0, SAFE_BOTTOM + 30, x0 + bw, SAFE_BOTTOM + 42], radius=6,
                            fill=B.INK if i <= idx else B.PAPER_DARK)
    return im, d


def scene_hook(spec, total):
    im, d = base(spec, 0, total)
    lines = [parts(x) for x in spec["hook"]]
    top = BAR_BOT if spec.get("topbar") else SAFE_TOP
    px = fit(d, lines, "black", 130 if spec.get("topbar") else 150, 70, W - 2 * M)
    f = B.font("black", px)
    lh = int(px * 1.25)
    y = (top + SAFE_BOTTOM) // 2 - lh * len(lines) // 2
    for ln in lines:
        x = M
        for t, c in ln:
            d.text((x, y), t, font=f, fill=c)
            x += B.tw(d, t, f)[0]
        y += lh
    return im


def scene_beat(spec, beat, idx, total):
    im, d = base(spec, idx, total)
    fb = B.font("black", 230)
    big = beat["big"]
    px = 230
    while B.tw(d, big, B.font("black", px))[0] > W - 2 * M and px > 100:
        px -= 10
    fb = B.font("black", px)
    y = (BAR_BOT + 120) if spec.get("topbar") else SAFE_TOP + 220
    d.text((M, y), big, font=fb, fill=B.ACCENT)
    y += int(px * 1.25) + 30
    ft = B.font("bold", 70)
    B.text_block(d, (M, y), beat["text"], ft, B.INK, W - 2 * M, gap=1.35)
    return im


def scene_end(spec, total):
    im, d = base(spec, total - 1, total)
    f = B.font("black", 92 if not spec.get("topbar") else 84)
    y = (BAR_BOT + 140) if spec.get("topbar") else SAFE_TOP + 360
    y = B.text_block(d, (M, y), spec["end"], f, B.INK, W - 2 * M, gap=1.28)
    if spec.get("cta"):
        fs = B.font("black", 62)
        B.text_block(d, (M, y + 70), spec["cta"], fs, B.ACCENT, W - 2 * M, gap=1.35)
    else:
        fs = B.font("bold", 54)
        B.text_block(d, (M, y + 60), "자세한 조건·출처는\n프로필 링크 블로그에", fs, B.INK_SOFT, W - 2 * M, gap=1.4)
    return im


def scene_single(spec):
    """11/22 방법 변경: 한 장 요약형(gamjya.money 34만 조회 형식 참고) — 상단 제목 띠 + 항목 표 + 댓글 질문을 한 화면에."""
    im, d = base(spec, 0, 1)
    y = BAR_BOT + 70
    rows = spec["beats"]
    fb_px, ft_px = (110, 58) if len(rows) <= 3 else (92, 52)
    gap = 36
    for b in rows:
        fb = B.font("black", fb_px)
        bw = B.tw(d, b["big"], fb)[0]
        d.rounded_rectangle([M, y, W - M, y + int(fb_px * 1.55)], radius=28, fill=B.PAPER_DARK)
        d.text((M + 34, y + int(fb_px * 0.2)), b["big"], font=fb, fill=B.ACCENT)
        ft = B.font("bold", ft_px)
        tx = M + 34 + bw + 36
        lines = b["text"].split("\n")
        lh = int(ft_px * 1.25)
        ty = y + int(fb_px * 1.55) // 2 - lh * len(lines) // 2
        for ln in lines:
            d.text((tx, ty), ln, font=ft, fill=B.INK); ty += lh
        y += int(fb_px * 1.55) + gap
    if spec.get("cta"):
        fs = B.font("black", 66)
        B.text_block(d, (M, y + 30), spec["cta"], fs, B.INK, W - 2 * M, gap=1.3)
    return im


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("spec"); ap.add_argument("--date", required=True); ap.add_argument("--at", required=True)
    ap.add_argument("--out", default=None)
    a = ap.parse_args()
    spec = json.load(open(a.spec, encoding="utf-8"))
    root = os.path.abspath(os.path.join(HERE, "..", ".."))
    od = a.out or os.path.join(root, "queue", a.date, spec["pid"])
    os.makedirs(od, exist_ok=True)
    if spec.get("layout") == "single":
        scenes = [(scene_single(spec), float(spec.get("single_dur", 9)))]
    else:
        hook = not spec.get("skip_hook")
        total = len(spec["beats"]) + 1 + (1 if hook else 0)
        scenes = [(scene_hook(spec, total), 2.6)] if hook else []
        off = 1 if hook else 0
        for i, b in enumerate(spec["beats"]):
            scenes.append((scene_beat(spec, b, i + off, total), float(spec.get("beat_dur", 3.2))))
        scenes.append((scene_end(spec, total), float(spec.get("end_dur", 2.8))))
    tmp = tempfile.mkdtemp()
    paths = []
    for i, (im, _) in enumerate(scenes):
        p = os.path.join(tmp, f"s{i}.png"); im.save(p); paths.append(p)
    scenes[0][0].save(os.path.join(od, "reel_cover.png"))
    fps, XF = 30, 0.35
    cmd = ["ffmpeg", "-y", "-loglevel", "error"]
    for p, (_, dur) in zip(paths, scenes):
        cmd += ["-loop", "1", "-t", f"{dur}", "-i", p]
    total_dur = sum(s[1] for s in scenes) - XF * (len(scenes) - 1)
    if spec.get("music", True) is not False:
        sys.path.insert(0, HERE)
        import music  # noqa: E402
        wav = os.path.join(tmp, "music.wav")
        music.save(wav, music.make(total_dur + 0.2, seed=int(spec.get("music_seed", sum(map(ord, spec["pid"]))))))
        cmd += ["-i", wav]
    else:
        cmd += ["-f", "lavfi", "-t", f"{total_dur}", "-i", "anullsrc=r=44100:cl=stereo"]
    fl = []
    for i, (_, dur) in enumerate(scenes):
        # 11/22: zoompan 확대는 프레임마다 좌표가 정수로 반올림돼 화면이 떨렸음(사장님 지적) → 정지 화면 + 디졸브로 변경
        fl.append(f"[{i}:v]scale={W}:{H},fps={fps},setsar=1,format=yuv420p[v{i}]")
    prev, off = "v0", 0.0
    for i in range(1, len(scenes)):
        off += scenes[i - 1][1] - XF
        fl.append(f"[{prev}][v{i}]xfade=transition=fade:duration={XF}:offset={off:.2f}[x{i}]")
        prev = f"x{i}"
    cmd += ["-filter_complex", ";".join(fl), "-map", f"[{prev}]", "-map", f"{len(scenes)}:a",
            "-c:v", "libx264", "-profile:v", "high", "-pix_fmt", "yuv420p", "-r", str(fps), "-b:v", "6M",
            "-c:a", "aac", "-b:a", "128k", "-shortest", "-movflags", "+faststart", os.path.join(od, "reel.mp4")]
    subprocess.run(cmd, check=True)
    pj = os.path.join(od, "post.json")
    post = json.load(open(pj, encoding="utf-8")) if os.path.exists(pj) else {
        "id": f"{a.date}_{spec['pid']}", "title": spec.get("title", ""), "publish_at": a.at, "channels": {}}
    post["publish_at"] = a.at
    post["channels"]["instagram_reel"] = {"video": "reel.mp4", "caption": spec["caption"], "cover": "reel_cover.png"}
    if "instagram" in post["channels"]:
        post["channels"]["instagram"]["enabled"] = False
    json.dump(post, open(pj, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    dur = subprocess.run(["ffprobe", "-v", "error", "-show_entries", "format=duration", "-of", "csv=p=0",
                          os.path.join(od, "reel.mp4")], capture_output=True, text=True).stdout.strip()
    print(json.dumps({"dir": os.path.relpath(od, root), "scenes": len(scenes), "duration": dur,
                      "hashtags": spec["caption"].count("#")}, ensure_ascii=False))


if __name__ == "__main__":
    main()
