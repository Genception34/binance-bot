---
name: Binance TR endpoint compatibility
description: Binance TR endpoint and CCXT exchange support are unavailable in this runtime.
---

The configured Binance TR API hostname must be verified as resolvable before restarting the live bot; an unresolved host prevents ccxt market loading and the bot exits before entering its loop.

**Why:** The requested `api.binancetr.com` and `api.trbinance.com` endpoint overrides both caused ccxt to fail at `exchange.load_markets()` with DNS resolution errors, so the bot could not start.

**How to apply:** When changing Binance API hosts, run a public market-data connectivity check first and do not report the live workflow as running unless it reaches its polling loop.

The installed `ccxt 4.5.83` package does not expose `ccxt.binancetr`; only the standard Binance exchange classes are available. Falling back to `ccxt.binance` would use a different exchange and is unsafe for Binance TR credentials.