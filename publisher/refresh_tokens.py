#!/usr/bin/env python3
"""인스타·스레드 장기 토큰(60일)을 연장하고 GitHub Secret을 새 값으로 바꾼다.
필요: IG_TOKEN, THREADS_TOKEN(있는 것만), GH_PAT(이 저장소 secrets 쓰기 권한), GITHUB_REPOSITORY
토큰 값은 로그에 찍지 않는다."""
import os, subprocess, sys
import requests

def refresh(url, grant, token):
    r = requests.get(url, params={"grant_type": grant, "access_token": token}, timeout=30)
    d = r.json()
    if r.status_code >= 400 or "access_token" not in d:
        raise RuntimeError(f"HTTP {r.status_code}: {d.get('error', d)}")
    return d["access_token"], d.get("expires_in")

def set_secret(name, value):
    env = dict(os.environ, GH_TOKEN=os.environ["GH_PAT"])
    subprocess.run(["gh", "secret", "set", name, "--repo", os.environ["GITHUB_REPOSITORY"]],
                   input=value.encode(), env=env, check=True, capture_output=True)

fail = 0
for name, url, grant in [("IG_TOKEN", "https://graph.instagram.com/refresh_access_token", "ig_refresh_token"),
                         ("THREADS_TOKEN", "https://graph.threads.net/refresh_access_token", "th_refresh_token")]:
    tok = os.environ.get(name, "").strip()
    if not tok:
        print(f"{name}: 없음, 건너뜀"); continue
    try:
        new, exp = refresh(url, grant, tok)
        set_secret(name, new)
        print(f"{name}: 연장 완료 (만료까지 {int(exp or 0)//86400}일)")
    except Exception as e:
        fail += 1
        print(f"{name}: 연장 실패 — {e}")
sys.exit(1 if fail else 0)
