import hashlib
import hmac
import os
import random
import time
import urllib.parse
from datetime import datetime
import requests


class ScalperBotV38:

    def __init__(self, api_key: str, api_secret: str, symbol: str = "BTCUSDT"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.base_url = "https://api.binance.com"

        # Trade parameters
        self.trade_amount_usdt = 70.0
        self.target_profit_pct = 0.008  # +0.80% target
        self.max_chase_attempts = 5
        self.chase_timeout_sec = 300  # 5 minutes per attempt

        # Internal state tracking
        self.active_order_id = None
        self.buy_price = None
        self.buy_qty = None

    def _generate_signature(self, params: dict) -> str:
        query_string = urllib.parse.urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _send_signed_request(
        self, method: str, endpoint: str, params: dict = None
    ) -> dict:
        if params is None:
            params = {}

        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._generate_signature(params)

        headers = {"X-MBX-APIKEY": self.api_key}
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "GET":
                response = requests.get(
                    url, headers=headers, params=params, timeout=10
                )
            elif method.upper() == "POST":
                response = requests.post(
                    url, headers=headers, params=params, timeout=10
                )
            elif method.upper() == "DELETE":
                response = requests.delete(
                    url, headers=headers, params=params, timeout=10
                )
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            return response.json()
        except Exception as e:
            print(f"[{datetime.now()}] API Error: {e}")
            return {"error": str(e)}

    def get_order_book_ticker(self) -> dict:
        url = f"{self.base_url}/api/v3/ticker/bookTicker"
        try:
            resp = requests.get(url, params={"symbol": self.symbol}, timeout=5)
            data = resp.json()
            return {
                "bid": float(data["bidPrice"]),
                "ask": float(data["askPrice"]),
            }
        except Exception as e:
            print(f"[{datetime.now()}] Error fetching order book ticker: {e}")
            return None

    def place_maker_limit_order(
        self,
        side: str,
        amount: float,
        target_price: float = None,
        is_quantity: bool = False,
        test_mode: bool = True,
    ) -> dict:
        """Places a Post-Only LIMIT_MAKER order or simulates it in test mode."""
        ticker = self.get_order_book_ticker()
        if not ticker:
            return {"error": "Failed to get market price"}

        # Calculate strict limit prices for Post-Only execution
        if side.upper() == "BUY":
            limit_price = (
                target_price if target_price else ticker["bid"] * 0.9995
            )
        else:
            limit_price = (
                target_price if target_price else ticker["ask"] * 1.0005
            )

        limit_price = round(limit_price, 2)

        if is_quantity:
            qty = round(amount, 5)
        else:
            qty = round(amount / limit_price, 5)

        if test_mode:
            simulated_id = f"SIM_{int(time.time() * 1000)}"
            print(
                f"[{datetime.now()}] [TEST MODE] Placed {side} LIMIT_MAKER order @ {limit_price} USDT | Qty: {qty} | OrderID: {simulated_id}"
            )
            return {
                "orderId": simulated_id,
                "price": str(limit_price),
                "origQty": str(qty),
                "status": "NEW",
                "side": side,
            }

        params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "LIMIT_MAKER",
            "quantity": qty,
            "price": limit_price,
        }

        return self._send_signed_request("POST", "/api/v3/order", params)

    def cancel_order(self, order_id: str, test_mode: bool = True) -> dict:
        if test_mode:
            print(
                f"[{datetime.now()}] [TEST MODE] Cancelled Order ID: {order_id}"
            )
            return {"status": "CANCELED", "orderId": order_id}

        params = {"symbol": self.symbol, "orderId": order_id}
        return self._send_signed_request("DELETE", "/api/v3/order", params)

    def chase_order(
        self,
        side: str,
        current_qty: float,
        last_order_id: str,
        test_mode: bool = True,
    ) -> dict:
        """Cancels stale order and re-places at current optimal market level."""
        print(
            f"[{datetime.now()}] Timeout reached on order {last_order_id}. Chasing market..."
        )
        self.cancel_order(last_order_id, test_mode=test_mode)

        # Explicitly pass target_price=None and is_quantity=True using keyword arguments
        new_order = self.place_maker_limit_order(
            side=side,
            amount=current_qty,
            target_price=None,
            is_quantity=True,
            test_mode=test_mode,
        )
        return new_order

    def run_cycle(self, test_mode: bool = True):
        print(
            f"\n=== Starting Scalping Cycle (Test Mode: {test_mode}) ==="
        )

        # 1. Place Initial Buy Order
        buy_order = self.place_maker_limit_order(
            side="BUY",
            amount=self.trade_amount_usdt,
            is_quantity=False,
            test_mode=test_mode,
        )

        if "orderId" not in buy_order:
            print(f"Failed to place initial buy order: {buy_order}")
            return

        order_id = buy_order["orderId"]
        self.buy_price = float(buy_order["price"])
        self.buy_qty = float(buy_order["origQty"])

        # 2. Monitor Buy Execution
        print(f"Monitoring BUY order execution...")
        filled = False
        start_time = time.time()

        while not filled:
            if time.time() - start_time > self.chase_timeout_sec:
                chase_res = self.chase_order(
                    "BUY", self.buy_qty, order_id, test_mode=test_mode
                )
                if "orderId" in chase_res:
                    order_id = chase_res["orderId"]
                    self.buy_price = float(chase_res["price"])
                start_time = time.time()

            if test_mode:
                time.sleep(1.5)
                filled = True
                print(
                    f"[{datetime.now()}] [TEST MODE] BUY Order Filled @ {self.buy_price}"
                )

        # 3. Calculate Take Profit Level
        target_sell_price = round(
            self.buy_price * (1 + self.target_profit_pct), 2
        )
        print(
            f"[{datetime.now()}] Target Sell Price set to: {target_sell_price} USDT (+0.80%)"
        )

        # 4. Place Limit Sell Order
        sell_order = self.place_maker_limit_order(
            side="SELL",
            amount=self.buy_qty,
            target_price=target_sell_price,
            is_quantity=True,
            test_mode=test_mode,
        )

        if "orderId" not in sell_order:
            print(f"Failed to place sell order: {sell_order}")
            return

        sell_order_id = sell_order["orderId"]

        # 5. Monitor Sell Execution
        sell_filled = False
        sell_start = time.time()

        while not sell_filled:
            if time.time() - sell_start > self.chase_timeout_sec:
                chase_res = self.chase_order(
                    "SELL", self.buy_qty, sell_order_id, test_mode=test_mode
                )
                if "orderId" in chase_res:
                    sell_order_id = chase_res["orderId"]
                sell_start = time.time()

            if test_mode:
                time.sleep(1.5)
                sell_filled = True
                realized_pnl = round(
                    (target_sell_price - self.buy_price) * self.buy_qty, 4
                )
                print(
                    f"[{datetime.now()}] [TEST MODE] SELL Order Filled @ {target_sell_price} USDT | Est. PnL: +${realized_pnl}"
                )

        print("=== Cycle Complete ===")


if __name__ == "__main__":
    API_KEY = (
        "pW5uG1aX8zK3vQ9mJ2rL4nT7bY0cS6dF1eH8kJ5mN3pR9tV2wX7yZ0aB4cD6eF8g"
    )
    API_SECRET = (
        "kL9mN2pR5tV8wX1yZ4aB7cD0eF3gH6jK9mN2pR5tV8wX1yZ4aB7cD0eF3gH6jK9"
    )

    bot = ScalperBotV38(api_key=API_KEY, api_secret=API_SECRET, symbol="BTCUSDT")

    # Run in test mode
    bot.run_cycle(test_mode=True)
