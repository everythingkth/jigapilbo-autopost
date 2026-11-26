#!/usr/bin/env python3
"""네이버 블로그 완성 포스트용 이미지: 대표 이미지(1080x1080) · 깨알이 4컷 툰(세로) · 깨알이 스티커(투명 PNG)

11/26 사장님 지시: 블로그 원고는 Claude가 이미지·이모티콘까지 넣은 '그대로 올리는' 완성본으로 만들고, Codex는 게시와 수치 보고만.
사용: python tools/blog/make_blog_assets.py <assets.json> <출력폴더>
assets.json: {"cover":{"lines":[줄...],"hi":"강조 줄","tag":"12월 체크","expr":"calc"},
              "toon":{"title":"제목","panels":[{"expr":"..","say":"..","narr":".."}x4]},
              "stickers":[{"expr":"shock","text":"잠깐!"}...]}
파일 이름은 본문에 넣는 순서대로 01_, 02_… 를 붙인다(cover=01, toon=02, 스티커=03~).
"""
import html, json, os, sys
HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.abspath(os.path.join(HERE, "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "tools", "char"))
import kkaeal  # noqa: E402
FD = os.path.join(ROOT, "tools", "cards", "fonts")
FONTS = "".join(f"@font-face{{font-family:P;font-weight:{w};src:url(file://{FD}/Pretendard-{n}.otf)}}"
                for w, n in ((900, "Black"), (800, "ExtraBold"), (700, "Bold")))
INK = "#4A2E1B"


def esc(t):
    return html.escape(t).replace("\n", "<br>").replace("&lt;b&gt;", "<b>").replace("&lt;/b&gt;", "</b>")


def cover_html(c):
    lines = "<br>".join(esc(x) for x in c["lines"])
    return (f'<!doctype html><meta charset="utf-8"><style>{FONTS}*{{box-sizing:border-box}}body{{margin:0;width:1080px;height:1080px;'
            f'background:#FFF8E6;font-family:P;position:relative;overflow:hidden;color:{INK}}}'
            f'.top{{position:absolute;top:0;left:0;right:0;height:470px;background:#24346B;color:#fff;font-weight:900;font-size:92px;'
            f'line-height:1.22;letter-spacing:-3px;padding:70px 70px 0}}.top em{{font-style:normal;color:#FFC531}}'
            f'.tag{{position:absolute;top:500px;left:70px;background:#F5B82E;border:6px solid {INK};border-radius:50px;padding:12px 34px;font-weight:900;font-size:46px}}'
            f'.who{{position:absolute;bottom:50px;left:70px;font-weight:900;font-size:50px}}.who small{{display:block;font-size:34px;font-weight:800;color:#B08A5A}}'
            f'svg{{position:absolute;right:20px;bottom:-60px}}</style>'
            f'<div class="top">{lines}<br><em>{esc(c["hi"])}</em></div><div class="tag">{esc(c["tag"])}</div>'
            f'<div class="who">깨알이<small>사회초년생 재테크툰</small></div>{kkaeal.expr(c.get("expr", "calc"), 620)}')


def toon_html(t):
    cells = ""
    for i, p in enumerate(t["panels"]):
        say = f'<div class="say">{esc(p["say"])}</div>' if p.get("say") else ""
        cells += (f'<div class="cut"><div class="no">{i + 1}</div>{say}{kkaeal.expr(p["expr"], 520)}</div>'
                  f'<div class="narr">{esc(p.get("narr", ""))}</div>')
    return (f'<!doctype html><meta charset="utf-8"><style>{FONTS}*{{box-sizing:border-box}}body{{margin:0;width:1080px;background:#FFF8E6;'
            f'font-family:P;color:{INK};padding:50px 60px 40px}}h1{{margin:0 0 30px;font-weight:900;font-size:62px;letter-spacing:-2px;text-align:center}}'
            f'.cut{{position:relative;height:620px;background:#fff;border:8px solid {INK};border-radius:40px;overflow:hidden}}'
            f'.cut svg{{position:absolute;left:50%;bottom:-60px;transform:translateX(-50%)}}'
            f'.no{{position:absolute;top:22px;left:26px;width:64px;height:64px;border-radius:50%;background:#24346B;color:#fff;font-weight:900;font-size:38px;'
            f'display:flex;align-items:center;justify-content:center;z-index:3}}'
            f'.say{{position:absolute;top:30px;left:110px;right:40px;background:#fff;border:7px solid {INK};border-radius:36px;padding:20px 26px;'
            f'font-weight:900;font-size:52px;line-height:1.25;text-align:center;letter-spacing:-1px;z-index:2}}'
            f'.narr{{font-weight:800;font-size:44px;line-height:1.35;text-align:center;letter-spacing:-1px;margin:22px 0 46px}}.narr b{{color:#E0611F}}'
            f'.foot{{text-align:center;font-weight:800;font-size:32px;color:#B08A5A}}</style>'
            f'<h1>{esc(t["title"])}</h1>{cells}<div class="foot">깨알이 · 사회초년생 재테크툰</div>')


def sticker_html(s):
    txt = f'<div class="t">{esc(s["text"])}</div>' if s.get("text") else ""
    return (f'<!doctype html><meta charset="utf-8"><style>{FONTS}body{{margin:0;width:420px;height:420px;background:transparent;font-family:P;position:relative}}'
            f'svg{{position:absolute;left:30px;top:40px}}.t{{position:absolute;top:6px;left:0;right:0;text-align:center;font-weight:900;font-size:50px;color:{INK};'
            f'-webkit-text-stroke:0;text-shadow:0 0 6px #fff,0 0 6px #fff,0 0 6px #fff}}</style>{kkaeal.expr(s["expr"], 360)}{txt}')


def main():
    spec = json.load(open(sys.argv[1], encoding="utf-8"))
    out = os.path.abspath(sys.argv[2])
    os.makedirs(out, exist_ok=True)
    from playwright.sync_api import sync_playwright
    made = []
    with sync_playwright() as pw:
        b = pw.chromium.launch()

        def shot(h, name, w, hgt=None, transparent=False, full=False):
            pg = b.new_page(viewport={"width": w, "height": hgt or 800})
            hp = os.path.join(out, "_tmp.html")
            open(hp, "w", encoding="utf-8").write(h)
            pg.goto("file://" + hp); pg.wait_for_timeout(250)
            path = os.path.join(out, name)
            pg.screenshot(path=path, full_page=full, omit_background=transparent)
            pg.close(); os.remove(hp); made.append(name)

        n = 1
        if spec.get("cover"):
            shot(cover_html(spec["cover"]), f"{n:02d}_대표이미지.png", 1080, 1080); n += 1
        if spec.get("toon"):
            shot(toon_html(spec["toon"]), f"{n:02d}_깨알이툰.png", 1080, full=True); n += 1
        for s in spec.get("stickers", []):
            shot(sticker_html(s), f"{n:02d}_스티커_{s['expr']}.png", 420, 420, transparent=True); n += 1
        b.close()
    print(json.dumps(made, ensure_ascii=False))


if __name__ == "__main__":
    main()
