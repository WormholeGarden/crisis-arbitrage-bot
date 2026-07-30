import time
import hmac
import hashlib
import requests
import json
import math
import random
from typing import Dict, Any, Optional, Tuple

class BinanceTrader:
    def __init__(self, api_key: str, api_secret: str, test_mode: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.test_mode = test_mode
        
        # Base URLs for Spot Live vs Spot Testnet
        if self.test_mode:
            self.base_url = "https://testnet.binance.vision"
        else:
            self.base_url = "https://api.binance.com"
            
        self.session = requests.Session()
        self.session.headers.update({
            "X-MBX-APIKEY": self.api_key,
            "Content-Type": "application/x-www-form-urlencoded"
        })

    def _generate_signature(self, params: Dict[str, Any]) -> str:
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256
        ).hexdigest()

    def _send_request(self, method: str, endpoint: str, params: Optional[Dict[str, Any]] = None, signed: bool = False) -> Dict[str, Any]:
        if params is None:
            params = {}
            
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._generate_signature(params)

        url = f"{self.base_url}{endpoint}"
        try:
            if method.upper() == "GET":
                response = self.session.get(url, params=params, timeout=10)
            elif method.upper() == "POST":
                response = self.session.post(url, data=params, timeout=10)
            elif method.upper() == "DELETE":
                response = self.session.delete(url, params=params, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            if hasattr(e, 'response') and e.response is not None:
                print(f"[API ERROR] {e.response.status_code}: {e.response.text}")
            else:
                print(f"[NETWORK ERROR] {str(e)}")
            return {"error": str(e)}

    def get_btc_price((self) -> float:
        """Fetches current BTCUSDT spot price."""
        if self.test_mode:
            # Fallback simulated price if testnet public endpoints fluctuate
            res = self._send_request("GET", "/api/v3/ticker/price", {"symbol": "BTCUSDT"})
            if "price" in res:
                return float(res["price"])
            return 64250.00
        
        res = self._send_request("GET", "/api/v3/ticker/price", {"symbol": "BTCUSDT"})
        return float(res.get("price", 0.0))

    def get_order_book(self) -> Dict[str, float]:
        """Fetches top bid/ask prices to prevent Post-Only limit maker rejections."""
        res = self._send_request("GET", "/api/v3/ticker/bookTicker", {"symbol": "BTCUSDT"})
        if "bidPrice" in res and "askPrice" in res:
            return {
                "bid": float(res["bidPrice"]),
                "ask": float(res["askPrice"])
            }
        # Fallback
        price = self.get_btc_price()
        return {"bid": price - 0.5, "ask": price + 0.5}

    def _format_price(self, price: float) -> str:
        """Truncates price to Binance 2 decimal places tick size."""
        return f"{price:.2f}"

    def _format_quantity(self, qty: float) -> str:
        """Truncates BTC quantity to 5 decimal places step size."""
        return f"{qty:.5f}"

    def place_maker_limit_order(
        self,
        side: str,
        amount: float,
        target_price: Optional[float] = None,
        is_quantity: bool = False,
        test_mode: Optional[bool] = None
    ) -> Dict[str, Any]:
        """
        Places a LIMIT_MAKER (Post-Only) order on Binance.
        Ensures execution won't cross the spread to trigger API Error -2010.
        """
        is_test = self.test_mode if test_mode is None else test_mode
        book = self.get_order_book()
        
        # Calculate pricing
        if side.upper() == "BUY":
            # Must be placed at or below best bid to guarantee Post-Only status
            limit_price = target_price if target_price and target_price <= book["bid"] else book["bid"]
        else: # SELL
            # Must be placed at or above best ask
            limit_price = target_price if target_price and target_price >= book["ask"] else book["ask"]

        # Determine quantity
        if is_quantity:
            btc_qty = amount
        else:
            btc_qty = amount / limit_price

        formatted_price = self._format_price(limit_price)
        formatted_qty = self._format_quantity(btc_qty)

        print(f"[{'TEST' if is_test else 'LIVE'}] Submitting LIMIT_MAKER {side}: {formatted_qty} BTC @ ${formatted_price}")

        if is_test:
            # Simulate local paper trading order object
            return {
                "symbol": "BTCUSDT",
                "orderId": random.randint(100000, 999999),
                "side": side.upper(),
                "price": formatted_price,
                "origQty": formatted_qty,
                "status": "NEW",
                "type": "LIMIT_MAKER"
            }

        params = {
            "symbol": "BTCUSDT",
            "side": side.upper(),
            "type": "LIMIT_MAKER",
            "quantity": formatted_qty,
            "price": formatted_price
        }

        return self._send_request("POST", "/api/v3/order", params=params, signed=True)

    def cancel_order(self, order_id: int) -> Dict[str, Any]:
        if self.test_mode:
            return {"symbol": "BTCUSDT", "orderId": order_id, "status": "CANCELED"}
            
        params = {"symbol": "BTCUSDT", "orderId": order_id}
        return self._send_request("DELETE", "/api/v3/order", params=params, signed=True)

    def chase_order(self, side: str, current_qty: float, max_attempts: int = 3) -> Optional[Dict[str, Any]]:
        """
        Attempts to update order placement if maker order remains unfilled.
        Fixed parameter signature so is_quantity=True is explicitly assigned.
        """
        print(f"[CHASE] Updating {side} limit maker order for {current_qty:.5f} BTC...")
        
        for attempt in range(1, max_attempts + 1):
            print(f"[CHASE] Attempt {attempt}/{max_attempts}")
            
            # FIXED: Explicit keyword arguments prevent target_price receiving positional booleans
            result = self.place_maker_limit_order(
                side=side,
                amount=current_qty,
                target_price=None,
                is_quantity=True,
                test_mode=self.test_mode
            )
            
            if "orderId" in result:
                return result
            time.sleep(1)
            
        return None

class TradingStrategy:
    def __init__(self, api_key: str, api_secret: str, test_mode: bool = True):
        self.test_mode = test_mode
        self.trader = BinanceTrader(api_key, api_secret, test_mode=test_mode)

    def evaluate_market() -> Dict[str, Any]:
        """Evaluates entry targets relative to current BTC spot price."""
        current_btc_price = self.trader.get_btc_price()
        
        # In live mode, targets should be within real market spread thresholds
        target_discount = 0.0005 if not self.test_mode else 0.001 
        target_entry = current_btc_price * (1 - target_discount)
        
        return {
            "current_price": current_btc_price,
            "target_entry": target_entry,
            "should_trade": True
        }

    def run_cycle(self, trade_amount_usdt: float = 100.0) -> None:
        print("\n==========================================")
        print(f" Starting Cycle | Mode: {'PAPER TRADING' if self.test_mode else 'LIVE TRADING'}")
        print("==========================================")

        market = self.evaluate_market()
        current_price = market["current_price"]
        entry_target = market["target_entry"]

        print(f"BTC Spot Price : ${current_price:,.2f}")
        print(f"Target Entry   : ${entry_target:,.2f}")

        # Step 1: Place Buy Order
        buy_order = self.trader.place_maker_limit_order(
            side="BUY",
            amount=trade_amount_usdt,
            target_price=entry_target,
            is_quantity=False
        )

        if "orderId" not in buy_order:
            print("[ERROR] Failed to place buy order. Aborting cycle.")
            return

        order_id = buy_order["orderId"]
        btc_qty = float(buy_order["origQty"])
        fill_price = float(buy_order["price"])

        # Step 2: Wait/Simulate Fill
        print(f"Order #{order_id} active. Waiting for fill...")
        time.sleep(2)

        # In paper mode, simulate an unbiased price oscillation
        if self.test_mode:
            # FIXED: Removed (+0.002) positive drift bias to reflect balanced market movement
            simulated_movement = random.uniform(-0.0015, 0.0015)
            simulated_price = fill_price * (1 + simulated_movement)
            print(f"[PAPER SIM] Price updated to ${simulated_price:,.2f}")
        
        # Step 3: Handle Take Profit
        take_profit_target = fill_price * 1.008  # +0.80% TP target
        print(f"Target Exit (+0.80%): ${take_profit_target:,.2f}")

        sell_order = self.trader.place_maker_limit_order(
            side="SELL",
            amount=btc_qty,
            target_price=take_profit_target,
            is_quantity=True
        )

        if "orderId" not in sell_order:
            print("[WARNING] Sell order failed. Triggering order chase...")
            chase_result = self.trader.chase_order(side="SELL", current_qty=btc_qty)
            if chase_result:
                print(f"[SUCCESS] Order chased and re-placed: Order #{chase_result['orderId']}")
            else:
                print("[CRITICAL] Order chase failed.")
        else:
            print(f"[SUCCESS] Take Profit order active: Order #{sell_order['orderId']}")

# ==========================================
# Script Execution
# ==========================================
if __name__ == "__main__":
    # Credentials (Use Binance Spot Testnet keys when test_mode=True)
    API_KEY = "YOUR_BINANCE_API_KEY"
    API_SECRET = "YOUR_BINANCE_API_SECRET"

    # Set test_mode=True to execute via paper mode / Binance Spot Testnet
    # Set test_mode=False for Live Exchange Trading
    bot = TradingStrategy(api_key=API_KEY, api_secret=API_SECRET, test_mode=True)
    
    # Run a test cycle with $100 allocation
    bot.run_cycle(trade_amount_usdt=100.0)
