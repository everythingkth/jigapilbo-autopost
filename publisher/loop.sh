#!/usr/bin/env bash
# 깃허브 예약 실행은 몇 시간씩 밀리기 때문에, 한 번 시작되면 이 안에서 20분마다 계속 확인한다.
# LOOP_MINUTES 동안 돌고 끝나면 워크플로가 자기 자신을 다시 실행한다.
set -u
git config user.name "jigapilbo-bot"
git config user.email "jigapilbo-bot@users.noreply.github.com"
END=$((SECONDS + ${LOOP_MINUTES:-330} * 60))
save() {
  cp state/published.json "$RUNNER_TEMP/mine.json" 2>/dev/null || return 0
  for i in 1 2 3 4 5; do
    git fetch -q origin main && git reset -q --hard origin/main
    python publisher/merge_state.py "$RUNNER_TEMP/mine.json" state/published.json
    git add state/published.json
    git diff --cached --quiet && return 0
    git commit -q -m "게시 기록 업데이트" && git push -q origin HEAD:main && return 0
    sleep $((i * 3))
  done
  return 1
}
while :; do
  git fetch -q origin main && git reset -q --hard origin/main
  echo "== $(TZ=Asia/Seoul date '+%m-%d %H:%M') 확인"
  python publisher/publish.py || true
  [ "${DRY_RUN:-0}" = "1" ] && break
  [ -n "${ONLY:-}" ] && { save; break; }
  save || echo "기록 저장 실패"
  [ $SECONDS -ge $END ] && break
  sleep 1200
done
