# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

## [0.1.0] - 2025-05-19

### Added

- Binance exchange adapter with full spot API support
- Bybit V5 exchange adapter with full spot API support
- OKX V5 exchange adapter with full spot API support
- Unified Pydantic models: `Ticker`, `OrderBook`, `Balance`, `Order`, `Candle`, `Trade`
- Sync and async API for all exchange operations
- Context manager support (`with` / `async with`) for automatic cleanup
- Token bucket rate limiter built into `HTTPClient`
- MCP server for Claude Desktop and AI assistant integration
- CLI tool (`pycex`) for terminal-based exchange operations
- PEP 561 `py.typed` marker for full type safety
- Exception hierarchy: `PyCexError`, `ExchangeError`, `RateLimitError`, etc.
- Testnet/demo mode support for all exchanges
- `.raw` field on all models for accessing original exchange responses

[Unreleased]: https://github.com/Jaeminyx-Stoa/pycex/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Jaeminyx-Stoa/pycex/releases/tag/v0.1.0
