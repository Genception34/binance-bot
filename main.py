import os
import time
import pandas as pd
import numpy as np
from binance.client import Client

API_KEY = os.environ.get('BINANCE_TR_API_KEY') or os.environ.get('BINANCE_API_KEY')
API_SECRET = os.environ.get('BINANCE_SECRET_KEY')

# Binance TR's supported API host is api.binance.me in this environment.
client = Client(API_KEY, API_SECRET, tld='me')
SYMBOL = 'BTCTRY'
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
    klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_1MINUTE, limit=100)
    df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', '_', '_', '_', '_', '_', '_'])
    df['close'] = df['close'].astype(float)
    
    df['MB'] = df['close'].rolling(window=21).mean()
    df['STD'] = df['close'].rolling(window=21).std()
    df['UP'] = df['MB'] + (df['STD'] * 2)
    df['DN'] = df['MB'] - (df['STD'] * 2)
    
    delta = df['close'].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)
    average_gain = wilder_rma(gain, 6)
    average_loss = wilder_rma(loss, 6)

    rs = average_gain / average_loss.replace(0, np.nan)
    rsi = 100 - (100 / (1 + rs))
    rsi = rsi.mask((average_loss == 0) & (average_gain > 0), 100)
    rsi = rsi.mask((average_gain == 0) & (average_loss > 0), 0)
    rsi = rsi.mask((average_gain == 0) & (average_loss == 0), 50)
    df['RSI'] = rsi
    
    return df.iloc[-1]

def run_bot():
    print("🚀 Bot baslatildi. BTCTRY takibi aktif...")
    while True:
        try:
            data = get_market_data()
            price = data['close']
            rsi = data['RSI']
            dn = data['DN']
            up = data['UP']
            band_margin = up - dn
            
            print(f"Fiyat: {price:,.2f} | RSI: {rsi:.2f} | Band Margin: {band_margin:,.2f}")
            
            if (rsi < 15 and band_margin >= 18000) or (
                rsi < 30 and price <= dn * 1.001 and band_margin >= 18000
            ):
                print(f"🔥 ALIM SINYALI! Fiyat: {price}")
                
                buy_order = client.order_market_buy(symbol=SYMBOL, quoteOrderQty=TRADE_SIZE_TRY)
                executed_price = float(buy_order['fills'][0]['price'])
                qty = float(buy_order['executedQty'])
                
                take_profit_price = round(
                    executed_price + ((up - executed_price) * 0.8),
                    2,
                )
                stop_price = round(dn * (1 - 0.015), 2)
                stop_limit_price = round(stop_price * (1 - 0.002), 2)
                
                client.create_oco_order(
                    symbol=SYMBOL,
                    side='SELL',
                    quantity=qty,
                    price=str(take_profit_price),
                    stopPrice=str(stop_price),
                    stopLimitPrice=str(stop_limit_price),
                    stopLimitTimeInForce='GTC'
                )
                print(f"🎯 OCO Emri Aktif! TP: {take_profit_price}, Stop: {stop_price}")
                time.sleep(300)
                
            time.sleep(3)
        except Exception as e:
            print(f"⚠️ Hata: {e}")
            time.sleep(5)

if __name__ == '__main__':
    run_bot()