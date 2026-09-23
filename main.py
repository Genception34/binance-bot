import requests


API_URL = "https://api.binance.me/api/v3/ticker/price"
SYMBOL = "BTCTRY"


def main() -> None:
    response = requests.get(
        API_URL,
        params={"symbol": SYMBOL},
        timeout=10,
    )
    response.raise_for_status()

    ticker = response.json()
    print(f"{ticker['symbol']}: {ticker['price']} TRY")


if __name__ == "__main__":
    main()