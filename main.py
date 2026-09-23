import os
import time

import ccxt
import numpy as np
import pandas as pd


if not hasattr(ccxt, "binancetr"):
    ccxt.binancetr = ccxt.binance

exchange = ccxt.binancetr({
    "apiKey": os.environ.get("BINANCE_TR_API_KEY"),
    "secret": os.environ.get("BINANCE_SECRET_KEY"),
    "enableRateLimit": True,
    "options": {
        "fetchCurrencies": False,
        "fetchMargins": False,
        "fetchMarkets": {
            "types": ["spot"],
        },
    },
})

# ccxt's Binance TR adapter is not available in every release. The supported
# Binance TR spot API host is api.binance.me.
exchange.urls["api"]["public"] = "https://api.binance.me/api/v3"
exchange.urls["api"]["private"] = "https://api.binance.me/api/v3"
exchange.load_markets()

SYMBOL = "BTC/TRY"
TRADE_SIZE_TRY = 10000


def wilder_rma(series, period):
    valid = series.dropna()
    rma = pd.Series(np.nan, index=series.index, dtype=float)

    if len(valid) < period:
        return rma

    previous = valid.iloc[:period].mean()
    seed_index = valid.index[period - 1]
    rma.loc[seed_index] = previous

    for index, value in valid.iloc[period:].items():
        previous = ((period - 1) * previous + value) / period
        rma.loc[index] = previous

    return rma


def get_market_data():
    ohlcv = exchange.fetch_ohlcv(SYMBOL, timeframe="1m", limit=100)
    df = pd.DataFrame(
        ohlcv,
        columns=["time", "open", "high", "low", "close", "volume"],
    )
    df["close"] = df["close"].astype(float)

    df["MB"] = df["close"].rolling(window=21).mean()
    df["STD"] = df["close"].rolling(window=21).std()
    df["UP"] = df["MB"] + (df["STD"] * 2)
    df["DN"] = df["MB"] - (df["STD"] * 2)

    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = wilder_rma(gain, 6)
    average_loss = wilder_rma(loss, 6)

    rs = average_gain / average_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((average_loss == 0) & (average_gain > 0), 100)
    rsi = rsi.mask((average_gain == 0) & (average_loss > 0), 0)
    rsi = rsi.mask((average_gain == 0) & (average_loss == 0), 50)
    df["RSI"] = rsi

    return df.iloc[-1]


def place_oco_order(quantity, take_profit_price, stop_price, stop_limit_price):
    market = exchange.market(SYMBOL)
    return exchange.private_post_order_oco({
        "symbol": market["id"],
        "side": "SELL",
        "quantity": exchange.amount_to_precision(SYMBOL, quantity),
        "price": exchange.price_to_precision(SYMBOL, take_profit_price),
        "stopPrice": exchange.price_to_precision(SYMBOL, stop_price),
        "stopLimitPrice": exchange.price_to_precision(SYMBOL, stop_limit_price),
        "stopLimitTimeInForce": "GTC",
    })


def run_bot():
    print("🚀 Bot baslatildi. BTCTRY takibi aktif...")
    while True:
        try:
            data = get_market_data()
            price = float(data["close"])
            rsi = float(data["RSI"])
            dn = float(data["DN"])
            up = float(data["UP"])
            band_margin = up - dn

            print(
                f"Fiyat: {price:,.2f} | "
                f"RSI: {rsi:.2f} | "
                f"Band Margin: {band_margin:,.2f}"
            )

            if (rsi < 15 and band_margin >= 18000) or (
                rsi < 30 and price <= dn * 1.001 and band_margin >= 18000
            ):
                print(f"🔥 ALIM SINYALI! Fiyat: {price}")

                buy_amount = TRADE_SIZE_TRY / price
                buy_order = exchange.create_market_buy_order(
                    SYMBOL,
                    exchange.amount_to_precision(SYMBOL, buy_amount),
                )
                executed_price = float(
                    buy_order.get("average")
                    or buy_order.get("price")
                    or price
                )
                quantity = float(
                    buy_order.get("filled")
                    or buy_order.get("amount")
                    or buy_amount
                )

                take_profit_price = round(
                    executed_price + ((up - executed_price) * 0.8),
                    2,
                )
                stop_price = round(dn * (1 - 0.015), 2)
                stop_limit_price = round(stop_price * (1 - 0.002), 2)

                place_oco_order(
                    quantity,
                    take_profit_price,
                    stop_price,
                    stop_limit_price,
                )
                print(
                    f"🎯 OCO Emri Aktif! "
                    f"TP: {take_profit_price}, Stop: {stop_price}"
                )
                time.sleep(300)

            time.sleep(3)
        except Exception as error:
            print(f"⚠️ Hata: {error}")
            time.sleep(5)


if __name__ == "__main__":
    run_bot()