# 지갑일보 자동 게시 (맥북 없이 도는 버전)

```
Claude 예약 작업(클라우드, 하루 2회)
  └ 글·카드·쇼츠 제작 → 이 저장소 queue/<날짜>/<ID>/ 에 올림
GitHub Actions (20분마다, 맥북 꺼져 있어도 동작)
  └ publisher/publish.py → 인스타 캐러셀·릴스, 스레드, (유튜브) 게시
  └ 결과 링크를 state/published.json 에 기록 (실제로 올라간 것만)
```

| 채널 | 방식 | 상태 |
|---|---|---|
| 인스타 캐러셀·릴스 | Instagram API (Instagram 로그인) | 토큰 넣으면 자동 |
| 스레드 | Threads API | 토큰 넣으면 자동 |
| 유튜브 쇼츠 | YouTube Data API | 구글 API 감사 통과 전엔 비공개로 잠겨서 꺼둠 |
| 네이버 블로그·티스토리 | 공식 글쓰기 API 없음 | 붙여넣기용 파일만 준비 |

## queue 형식
`queue/2026-10-12/P004/post.json`
```json
{"id": "2026-10-12_P004", "publish_at": "2026-10-12T19:00:00+09:00",
 "channels": {
  "instagram": {"images": ["cards/01.png", "..."], "caption": "..."},
  "instagram_reel": {"video": "https://...mp4", "caption": "...", "cover": "cards/01.png"},
  "threads": {"text": "... (500자 이하)"},
  "youtube": {"video": "https://...mp4", "title": "...", "description": "...", "enabled": false}}}
```
- `publish_at` 이 없거나 지났으면 바로 올림. 채널별 `"enabled": false` 면 건너뜀.
- 인스타 캡션 해시태그는 자동으로 앞의 5개만 남김(앱 제한).
- 수동 실행: Actions → publish → Run workflow (`dry_run`=1 이면 확인만).

## GitHub Secrets (Settings → Secrets and variables → Actions)
`IG_USER_ID`, `IG_TOKEN`, `THREADS_USER_ID`, `THREADS_TOKEN`, `GH_PAT`(토큰 자동 연장용)
유튜브를 켤 때: `YT_CLIENT_ID`, `YT_CLIENT_SECRET`, `YT_REFRESH_TOKEN`

## 인스타 게시 속도 (2026-10-23)
- 인스타 게시는 최소 3시간 간격, 실행 1번에 1개만 (IG_MIN_GAP_MIN=180)
- 인스타가 활동을 제한하면 12시간 쉰 뒤 재시도 (IG_BLOCK_BACKOFF_H=12)
- 이미 같은 캡션으로 올라간 글은 다시 올리지 않고 기록만 채움
