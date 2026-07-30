import os
import sys
import time
import math
import random
import logging

# Set up clean logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)]
)

try:
    from binance.client import Client
    from binance.exceptions import BinanceAPIException, BinanceOrderException
except ImportError:
    logging.warning("python-binance is not installed. Live trading mode will raise errors.")
    Client = None

# =====================================================================
# CONFIGURATION & HARDCODED KEYS
# =====================================================================
API_KEY = "Your_Binance_API_Key_Here"
API_SECRET = "Your_Binance_API_Secret_Here"

SYMBOL = "BTCUSDT"
TRADE_AMOUNT_USDT = 50.0   # Base trade size in USDT
PROFIT_TARGET_PCT = 0.008  # 0.80% Take-Profit Target
TIMEOUT_SECONDS = 300      # Time before chasing order (5 minutes)
TEST_MODE = True           # Set to False ONLY when ready for real execution

# =====================================================================
# BOT ENGINE
# =====================================================================
class RefactoredTradingEngine:
    def __init__(self, api_key: str, api_secret: str, symbol: str, test_mode: bool = True):
        self.symbol = symbol
        self.test_mode = test_mode
        self.client = None
        
        # Symbol filter precisions
        self.price_precision = 2
        self.qty_precision = 5
        self.min_notional = 10.0

        if not self.test_mode:
            if not Client:
                raise RuntimeError("python-binance dependency missing. Run `pip install python-binance`.")
            self.client = Client(api_key, api_secret)
            self._load_symbol_filters()
            logging.info(f"Initialized Live Trading Engine for {self.symbol}")
        else:
            logging.info(f"Initialized Paper Trading Simulator for {self.symbol}")

    def _load_symbol_filters(self):
        """Fetch step size and tick size filters directly from Binance."""
        try:
            info = self.client.get_symbol_info(self.symbol)
            for f in info['filters']:
                if f['filterType'] == 'PRICE_FILTER':
                    tick_size = float(f['tickSize'])
                    self.price_precision = int(round(-math.log10(tick_size)))
                elif f['filterType'] == 'LOT_SIZE':
                    step_size = float(f['stepSize'])
                    self.qty_precision = int(round(-math.log10(step_size)))
                elif f['filterType'] == 'NOTIONAL' or f['filterType'] == 'MIN_NOTIONAL':
                    self.min_notional = float(f.get('minNotional', 10.0))
        except Exception as e:
            logging.error(f"Failed to fetch market filters: {e}. Using defaults.")

    def get_current_price(self) -> float:
        """Fetch ticker price or generate simulated market price."""
        if not self.test_mode:
            try:
                ticker = self.client.get_symbol_ticker(symbol=self.symbol)
                return float(ticker['price'])
            except BinanceAPIException as e:
                logging.error(f"API exception while fetching price: {e}")
                return 0.0
        else:
            # Fixed simulated price point for baseline
            return 64250.00

    def place_maker_limit_order(self, side: str, amount: float, target_price: float = None, 
                                is_quantity: bool = False) -> dict:
        """
        Place a Limit Maker (Post-Only) order.
        If target_price is omitted, order is priced at or slightly inside the spread.
        """
        current_mkt_price = self.get_current_price()
        if current_mkt_price <= 0:
            return {"status": "FAILED", "reason": "Invalid market price"}

        # Calculate Price & Quantity
        if side.upper() == "BUY":
            price = target_price if target_price else round(current_mkt_price * 0.9998, self.price_precision)
        else:
            price = target_price if target_price else round(current_mkt_price * 1.0002, self.price_precision)

        if is_quantity:
            qty = round(amount, self.qty_precision)
        else:
            qty = round(amount / price, self.qty_precision)

        # Check Minimum Notional Requirement
        if (qty * price) < self.min_notional:
            logging.error(f"Order value ${qty * price:.2f} is below minimum notional requirement ${self.min_notional}")
            return {"status": "FAILED", "reason": "MIN_NOTIONAL_FAILURE"}

        logging.info(f"[{'TEST' if self.test_mode else 'LIVE'}] Placing LIMIT_MAKER {side} Order: {qty} {self.symbol} @ ${price}")

        if self.test_mode:
            return {
                "orderId": random.randint(1000000, 9999999),
                "symbol": self.symbol,
                "side": side.upper(),
                "price": price,
                "origQty": qty,
                "status": "NEW"
            }

        try:
            order = self.client.create_order(
                symbol=self.symbol,
                side=side.upper(),
                type="LIMIT_MAKER",
                quantity=f"{qty:.{self.qty_precision}f}",
                price=f"{price:.{self.price_precision}f}"
            )
            return order
        except BinanceAPIException as e:
            logging.error(f"Binance Order Execution Error: {e}")
            return {"status": "FAILED", "reason": str(e)}

    def cancel_order(self, order_id: int) -> bool:
        """Cancel an open order on the exchange."""
        if self.test_mode:
            logging.info(f"[TEST] Cancelled order #{order_id}")
            return True
        try:
            self.client.cancel_order(symbol=self.symbol, orderId=order_id)
            return True
        except BinanceAPIException as e:
            logging.error(f"Failed to cancel order #{order_id}: {e}")
            return False

    def chase_order(self, side: str, qty: float, timeout: int = 300) -> dict:
        """
        If a Limit Maker order goes unfilled within timeout, update the order price
        closer to current market level without triggering matching engine rejects.
        """
        logging.info(f"Initiating order chase logic for {side} {qty} {self.symbol}...")
        start_time = time.time()
        
        while time.time() - start_time < timeout:
            mkt_price = self.get_current_price()
            # Standard Limit order (IOC/GTC) instead of LIMIT_MAKER to guarantee fill during a chase
            adjusted_price = round(mkt_price * (1.0001 if side.upper() == "BUY" else 0.9999), self.price_precision)
            
            if self.test_mode:
                logging.info(f"[TEST] Chased order filled at ${adjusted_price}")
                return {"status": "FILLED", "price": adjusted_price, "executedQty": qty}

            try:
                # Execution via standard LIMIT order for aggressive fill
                order = self.client.create_order(
                    symbol=self.symbol,
                    side=side.upper(),
                    type="LIMIT",
                    timeInForce="IOC",
                    quantity=f"{qty:.{self.qty_precision}f}",
                    price=f"{adjusted_price:.{self.price_precision}f}"
                )
                if order.get("status") in ["FILLED", "PARTIALLY_FILLED"]:
                    return order
            except BinanceAPIException as e:
                logging.warning(f"Chase attempt failed: {e}. Retrying in 5s...")
            
            time.sleep(5)

        return {"status": "FAILED", "reason": "Chase timeout reached"}

    def simulate_unbiased_price_tick(self, current_price: float) -> float:
        """Symmetric random walk (Unbiased Gaussian Drift) for realistic testing."""
        drift = random.gauss(0, 0.0005) # 0 mean, 0.05% standard deviation
        return round(current_price * (1 + drift), self.price_precision)

    def run_cycle(self):
        """Execute one full Buy-then-Sell trade cycle."""
        logging.info("==========================================")
        logging.info("Starting Execution Cycle")
        logging.info("==========================================")

        # 1. Place Limit Maker BUY
        buy_order = self.place_maker_limit_order(side="BUY", amount=TRADE_AMOUNT_USDT)
        if buy_order.get("status") == "FAILED":
            logging.error("Failed to place initial buy order. Aborting cycle.")
            return

        order_id = buy_order.get("orderId")
        buy_price = float(buy_order.get("price"))
        qty = float(buy_order.get("origQty"))

        # 2. Monitor or Chase Buy Order
        filled = False
        start_time = time.time()
        curr_sim_price = buy_price

        while time.time() - start_time < TIMEOUT_SECONDS:
            if self.test_mode:
                curr_sim_price = self.simulate_unbiased_price_tick(curr_sim_price)
                if curr_sim_price <= buy_price:
                    filled = True
                    logging.info(f"[TEST] Limit Buy filled @ ${buy_price}")
                    break
            else:
                # Check actual status on Binance
                check = self.client.get_order(symbol=self.symbol, orderId=order_id)
                if check.get("status") == "FILLED":
                    filled = True
                    logging.info(f"Live Limit Buy filled @ ${buy_price}")
                    break

            time.sleep(2)

        if not filled:
            logging.info("Buy order not filled within timeout. Cancelling and chasing...")
            self.cancel_order(order_id)
            chase_result = self.chase_order(side="BUY", qty=qty, timeout=60)
            if chase_result.get("status") != "FILLED":
                logging.error("Failed to acquire position during chase. Aborting cycle.")
                return
            buy_price = float(chase_result.get("price", buy_price))

        # 3. Calculate Take Profit Target
        tp_price = round(buy_price * (1 + PROFIT_TARGET_PCT), self.price_precision)
        logging.info(f"Target acquired. Profit Target set to: ${tp_price:.2f} (+{PROFIT_TARGET_PCT*100:.2f}%)")

        # 4. Place Take Profit SELL Order
        sell_order = self.place_maker_limit_order(
            side="SELL", 
            amount=qty, 
            target_price=tp_price, 
            is_quantity=True
        )
        if sell_order.get("status") == "FAILED":
            logging.error("Failed to place sell order. Manual intervention required!")
            return

        sell_order_id = sell_order.get("orderId")

        # 5. Monitor Take Profit Execution
        tp_filled = False
        start_time = time.time()
        
        while time.time() - start_time < TIMEOUT_SECONDS:
            if self.test_mode:
                curr_sim_price = self.simulate_unbiased_price_tick(curr_sim_price)
                if curr_sim_price >= tp_price:
                    tp_filled = True
                    logging.info(f"[TEST] Take-profit target reached @ ${tp_price}!")
                    break
            else:
                check = self.client.get_order(symbol=self.symbol, orderId=sell_order_id)
                if check.get("status") == "FILLED":
                    tp_filled = True
                    logging.info(f"Live Take-profit filled @ ${tp_price}!")
                    break
            
            time.sleep(2)

        if not tp_filled:
            logging.info("Take-profit target not reached. Exiting via order chase...")
            self.cancel_order(sell_order_id)
            self.chase_order(side="SELL", qty=qty, timeout=60)

        logging.info("Cycle complete.\n")


# =====================================================================
# ENTRY POINT
# =====================================================================
if __name__ == "__main__":
    bot = RefactoredTradingEngine(
        api_key=API_KEY, 
        api_secret=API_SECRET, 
        symbol=SYMBOL, 
        test_mode=TEST_MODE
    )
    
    # Run a test cycle
    bot.run_cycle()
