# Fixture notes — candle timestamp semantics

Recorded via `python scripts/record_fixtures.py` against live public endpoints on
2026-08-30 (~04:26 UTC / 13:26 KST). All 22 targets returned real, successful
responses on the first try — no URL/param fixes were needed. One line per
exchange below: timestamp field, unit, OPEN vs CLOSE, and timezone/day-boundary.

- **upbit** (`/v1/candles/days`, `/v1/candles/minutes/1`) — `candle_date_time_utc`
  (+ mirrored `candle_date_time_kst`) is the candle **OPEN** time, ISO-8601 string
  with no offset suffix; the separate `timestamp` field (epoch **ms**) is the last
  trade tick inside the candle, not a boundary. 🚨 Daily candles reset at **00:00
  UTC = 09:00 KST**, i.e. UTC midnight — NOT KST midnight.
  Array order: newest-first (descending).

- **bithumb** (`/v1/candles/days`) — same field shape as Upbit
  (`candle_date_time_utc`/`_kst` = **OPEN**, ISO string, no offset; `timestamp` =
  last tick, epoch ms). 🚨 Unlike Upbit, daily candles reset at **00:00 KST
  (= 15:00 UTC the previous day)** — despite identical field names, Upbit and
  Bithumb use different daily boundaries. Array order: newest-first (descending).

- **korbit** (`/v2/candles`) — only one time field, `timestamp` (epoch **ms**,
  UTC). Confirmed **OPEN** (and confirmed KST-midnight day boundary, matching
  Bithumb) by cross-checking identical epoch values against Bithumb's
  `candle_date_time_utc` for the same three days (1787842800000 /
  1787929200000 / 1788015600000 → 2026-08-27/28/29T15:00:00 UTC each = 00:00
  KST next day). Array order: oldest-first (ascending).

- **binance** (`/fapi/v1/klines`, linear/USDT-M futures) — kline array index 0 is
  **open** time (epoch **ms**, UTC); index 6 is close time (= next open − 1ms,
  verified in the fixture). Array order: oldest-first (ascending).

- **okx** (`/api/v5/market/candles`, SWAP) — array index 0 (`ts`) is the
  **opening**/start time of the candle, epoch **ms**, UTC. Array order:
  newest-first (descending).

- **bitget** (`/api/v2/mix/market/candles`, USDT-FUTURES) — array index 0
  (`ts`) is the candle **start/open** time, epoch **ms**, UTC. Array order:
  oldest-first (ascending).

## Summary for later parsers
All six exchanges' raw candle timestamps are candle **OPEN**, not close — this
matches the project convention (`Candle.timestamp` = bar-open UTC epoch ms), so
no shift is needed when mapping raw → unified `Candle`. The one real trap is
**Upbit vs. Bithumb/Korbit daily-bar day boundary**: Upbit resets at 00:00 UTC
(09:00 KST) while Bithumb and Korbit reset at 00:00 KST (15:00 UTC previous
day). This does not change the timestamp *value* semantics (still OPEN, still
UTC ms) but means "the daily candle for a given KST calendar date" picks a
different underlying bar on Upbit than on Bithumb/Korbit — parser tests should
not assume the three Korean exchanges' daily bars are calendar-aligned.
