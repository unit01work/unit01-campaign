# UNIT-01 — Temporary Broadcast Campaign

Throwaway repo that broadcasts the APEX RACE 01 "INVITE ONLY" drop to all LINE
followers, 3×/day (09:00 / 13:00 / 19:00 Asia/Bangkok) on **16–20 Nov 2026**.

- `send.py` — builds the 2 Flex messages and calls the LINE Messaging API.
- `config/campaign.json` — the 15 rounds, prices, access code, image + link.
- `images/` — hero images, served publicly via `raw.githubusercontent.com`.
- `.github/workflows/broadcast.yml` — the scheduler (cron, UTC) + manual run.
- `.github/workflows/cleanup.yml` — self-wipes the repo on 21 Nov 2026.

The LINE channel access token is **not** stored here — it lives in the repo
secret `LINE_CHANNEL_ACCESS_TOKEN`. `LINE_TEST_USER_ID` is used by manual tests.

Separate from the main shop app on purpose; delete this repo anytime after the drop.
