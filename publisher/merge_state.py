#!/usr/bin/env python3
"""게시 기록 합치기: merge_state.py <이번 실행 기록> <main 최신 기록>
main 쪽 기록을 지우지 않고, 이번 실행에서 새로 생긴 채널 기록만 더한다."""
import json
import sys
from pathlib import Path

mine = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8")) if Path(sys.argv[1]).exists() else {}
tp = Path(sys.argv[2])
base = json.loads(tp.read_text(encoding="utf-8")) if tp.exists() else {}
for pid, rec in mine.items():
    b = base.setdefault(pid, {})
    for ch, v in rec.items():
        if ch == "_errors":
            errs = b.setdefault("_errors", {})
            for k, e in v.items():
                if k not in b:  # 이미 성공 기록이 있으면 오류는 버림
                    errs[k] = e
            if not errs:
                b.pop("_errors")
        elif ch not in b:
            b[ch] = v
            b.get("_errors", {}).pop(ch, None)
    if b.get("_errors") == {}:
        b.pop("_errors")
tp.parent.mkdir(parents=True, exist_ok=True)
tp.write_text(json.dumps(base, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
