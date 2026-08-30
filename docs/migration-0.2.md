# Migrating from 0.1.x to 0.2.0

## Symbols must be canonical

Every public per-symbol method (`fetch_ticker`, `fetch_order_book`,
`fetch_candles`, `fetch_trades`, `create_order`, `cancel_order`,
`fetch_order`, `fetch_open_orders`, `fetch_my_trades`, ...) now requires the
canonical notation — spot `BASE/QUOTE` (e.g. `BTC/USDT`), linear perpetual
`BASE/QUOTE:SETTLE` (e.g. `BTC/USDT:USDT`) — on **every** adapter, not just
some. Passing an exchange-native symbol raises `SymbolNotFoundError` instead
of succeeding.

```diff
- ex.fetch_ticker_sync("BTCUSDT")     # Binance/Bybit/Bitget native
- ex.fetch_ticker_sync("BTC-USDT")    # OKX native
- ex.fetch_ticker_sync("KRW-BTC")     # Upbit/Bithumb native
+ ex.fetch_ticker_sync("BTC/USDT")    # canonical, works on every adapter
```

Every returned model's `.symbol` field is likewise always canonical now — if
you were parsing `order.symbol`/`ticker.symbol` expecting native notation,
update that logic too.

## Hand-written `_sync` methods were removed

0.1.x adapters implemented their `<method>_sync` twins by hand. In 0.2.0
every one of them is generated automatically by
`BaseExchange.__init_subclass__` from the async method of the same name —
functionally identical (same signature, same blocking behavior, still raises
`RuntimeError` if called from inside a running event loop), but if you
subclassed an adapter and overrode a `_sync` method directly, that override
is no longer picked up unless you also override the underlying async method
(the sync twin always delegates to `self.<name>(...)`).

## `testnet=`/`demo=` are deprecated

Every adapter constructor now takes a single `sandbox: bool` flag. The old
per-exchange kwargs (`testnet=` on Binance/Bybit, `demo=` on OKX/Bitget)
still work but emit a `DeprecationWarning` and map onto `sandbox=`:

```diff
- Binance(api_key=..., secret=..., testnet=True)
- OKX(api_key=..., secret=..., passphrase=..., demo=True)
+ Binance(api_key=..., secret=..., sandbox=True)
+ OKX(api_key=..., secret=..., passphrase=..., sandbox=True)
```

The CLI's `--testnet` flag is likewise deprecated in favor of `--sandbox`
(same warning, same mapping). `PYCEX_TESTNET` (CLI/MCP env var) still works
as a fallback for `PYCEX_SANDBOX`.

## New in 0.2.0 (not breaking, but worth knowing about)

- Three new spot-only KRW exchanges: `Upbit`, `Bithumb`, `Korbit`.
- USDT-margined linear perpetuals on `Binance`/`OKX`/`Bitget` via
  `market_type="linear"`, plus the new `fetch_positions`/`fetch_funding_rate`
  methods (raise `NotSupportedError` on spot and on the three KRW exchanges).
- `fetch_markets()` (unified `Market` model) and `fetch_my_trades()`
  (unified `MyTrade` model) are now part of the base interface on every
  adapter, not just some.
- `fetch_candles(..., since=..., until=...)` paginates automatically.
- `pycex.factory.create_exchange(name, ...)` — one function to construct any
  of the seven adapters by name, with per-exchange env var fallback. The CLI
  and MCP server both use it internally.

See `CHANGELOG.md` for the full list of additions and fixes in this release.
