import os
import time
import pandas as pd
import numpy as np
from binance.client import Client

API_KEY = os.environ.get('BINANCE_TR_API_KEY')
API_SECRET = os.environ.get('BINANCE_TR_API_SECRET')

client = Client(API_KEY, API_SECRET, tld='tr')
SYMBOL = 'BTCTRY'
TRADE_SIZE_TRY = 10000

def get_market_data():
    klines = client.get_klines(symbol=SYMBOL, interval=Client.KLINE_INTERVAL_1MINUTE, limit=30)
    df = pd.DataFrame(klines, columns=['time', 'open', 'high', 'low', 'close', 'volume', '_', '_', '_', '_', '_', '_'])
    df['close'] = df['close'].astype(float)
    
    df['MB'] = df['close'].rolling(window=21).mean()
    df['STD'] = df['close'].rolling(window=21).std()
    df['UP'] = df['MB'] + (df['STD'] * 2)
    df['DN'] = df['MB'] - (df['STD'] * 2)
    
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=6).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=6).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    return df.iloc[-1]

def run_bot():
    print("Bot baslatildi. Pusuya yatildi...")
    while True:
        try:
            data = get_market_data()
            price = data['close']
            rsi = data['RSI']
            dn = data['DN']
            up = data['UP']
            band_margin = up - dn
            
            print(f"Fiyat: {price} | RSI: {rsi:.2f} | Bant Margin: {band_margin:.2f}")
            
            if rsi < 30 and price <= dn and band_margin >= 18000:
                print(f"SINYAL! Alim yapiliyor... Fiyat: {price}")
                
                buy_order = client.order_market_buy(symbol=SYMBOL, quoteOrderQty=TRADE_SIZE_TRY)
                executed_price = float(buy_order['fills'][0]['price'])
                qty = float(buy_order['executedQty'])
                
                take_profit_price = round(executed_price + 15000, 2)
                stop_price = round(executed_price - 8000, 2)
                stop_limit_price = round(stop_price - 1000, 2)
                
                client.create_oco_order(
                    symbol=SYMBOL,
                    side='SELL',
                    quantity=qty,
                    price=str(take_profit_price),
                    stopPrice=str(stop_price),
                    stopLimitPrice=str(stop_limit_price),
                    stopLimitTimeInForce='GTC'
                )
                print(f"OCO Emri Kuruldu! TP: {take_profit_price}, Stop: {stop_price}")
                time.sleep(300)
                
            time.sleep(3)
        except Exception as e:
            print(f"Hata: {e}")
            time.sleep(5)

if __name__ == '__main__':
    run_bot()