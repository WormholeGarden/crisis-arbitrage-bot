import time
from binance.client import Client
from binance.enums import *
from binance.exceptions import BinanceAPIException

# Use your Binance Testnet API keys for safety
API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"

# Initialize client (testnet=True prevents real funds from being used)
client = Client(api_key, api_secret, testnet=True)

symbol = 'BTCUSDT'
target_buy_price = 60000.0  # Example trigger price
quantity_to_buy = 0.001     # Amount of BTC to purchase

def check_and_trade():
    try:
        # Fetch current ticker price
        ticker = client.get_symbol_ticker(symbol=symbol)
        current_price = float(ticker['price'])
        print(f"Current {symbol} price: {current_price}")

        # Trading strategy logic
        if current_price <= target_buy_price:
            print("Target price reached! Placing market buy order...")
            
            # Use create_test_order to validate without executing, 
            # or client.order_market_buy for real testnet execution
            order = client.order_market_buy(
                symbol=symbol,
                quantity=quantity_to_buy
            )
            print("Order successful:", order)
        else:
            print("Price above target. Holding...")

    except BinanceAPIException as e:
        print(f"Binance API Error: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Run loop every 60 seconds
if __name__ == "__main__":
    while True:
        check_and_trade()
        time.sleep(60)
