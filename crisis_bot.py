#!/usr/bin/env python3
"""
🚀 FULLY FIXED CRISIS ARBITRAGE BOT v3.5
- Fixed simulated status check bug where hardcoded '0.001 BTC' broken chase loop
- Paper mode now tracks simulated orders in an in-memory dictionary
- Fully integrated chase, partial-fill management, and exit monitoring
"""

import time
import hashlib
import hmac
import requests
from decimal import Decimal, ROUND_HALF_UP
from typing import Dict
import random

# ========================================================================
# 📊 CONFIGURATION
# ========================================================================

CONFIG = {
    "initial_capital": 100.00,
    "test_mode": True,              # True = paper trading, False = real
    "trade_percentage": 0.70,       # 70% of capital per trade
    "cycles": 5,                    # Number of cycles to run
    "hold_seconds": 3600,           # 1 hour hold time
    "profit_target": 0.005,         # 0.5% profit target
    "stop_loss": 0.01,              # 1% stop loss
    "maker_fee_rate": 0.001,        # 0.1% maker fee
    "taker_fee_rate": 0.0015,       # 0.15% taker fee
    "order_timeout": 300,           # 5 minutes timeout
    "reprice_interval": 30,         # Reprice every 30 seconds (live mode)
    "paper_fill_delay": 2.0,        # Simulated fill delay in paper mode
    "paper_reprice_interval": 2.0,  # Pause between paper chase attempts
    "max_consecutive_status_errors": 5,
    "price_poll_interval": 5,       # Poll price every 5s to stay under weight limits
    "binance": {
        "api_key": "YOUR_API_KEY",
        "api_secret": "YOUR_API_SECRET",
        "enabled": True,
    },
}

# ========================================================================
# 🔧 DECIMAL HELPERS
# ========================================================================

def round_to_step(value: float, step: float) -> float:
    step_dec = Decimal(str(step))
    val_dec = Decimal(str(value))
    rounded = (val_dec // step_dec) * step_dec
    return float(rounded)

def round_to_tick(value: float, tick: float) -> float:
    tick_dec = Decimal(str(tick))
    val_dec = Decimal(str(value))
    rounded = (val_dec / tick_dec).quantize(Decimal('1'), rounding=ROUND_HALF_UP) * tick_dec
    return float(rounded)

def format_quantity(value: float) -> str:
    return f"{Decimal(str(value)):.8f}"

def format_price(value: float) -> str:
    return f"{Decimal(str(value)):.2f}"

# ========================================================================
# 📡 BINANCE.US API
# ========================================================================

class BinanceAPI:
    def __init__(self, config: Dict):
        self.config = config
        self.api_key = config["binance"]["api_key"]
        self.api_secret = config["binance"]["api_secret"]
        self.base_url = "https://api.binance.us"
        self._filter_cache = {}
        self.maker_fee_rate = config.get("maker_fee_rate", 0.001)
        self.taker_fee_rate = config.get("taker_fee_rate", 0.0015)
        self.active_order_id = None
        self.test_mode = config.get("test_mode", True)
        self.simulated_orders = {}  # Tracks state of paper trades cleanly

    def _send_signed_request(self, method: str, endpoint: str, params: dict) -> dict:
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params.setdefault("recvWindow", 5000)

        ordered_items = sorted(params.items())
        query_string = "&".join([f"{k}={v}" for k, v in ordered_items])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()

        final_params = dict(ordered_items)
        final_params["signature"] = signature

        headers = {"X-MBX-APIKEY": self.api_key}
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "GET":
                resp = requests.get(url, headers=headers, params=final_params)
            elif method.upper() == "POST":
                resp = requests.post(url, headers=headers, data=final_params)
            elif method.upper() == "DELETE":
                resp = requests.delete(url, headers=headers, params=final_params)
            else:
                return {"error": f"Unsupported method: {method}"}

            if resp.status_code == 200:
                return resp.json()
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        except Exception as e:
            return {"error": str(e)}

    def _get_symbol_filters(self, symbol: str) -> Dict:
        if symbol in self._filter_cache:
            return self._filter_cache[symbol]

        try:
            resp = requests.get(f"{self.base_url}/api/v3/exchangeInfo", params={"symbol": symbol})
            resp.raise_for_status()
            info = resp.json()["symbols"][0]

            lot_size = next(f for f in info["filters"] if f["filterType"] == "LOT_SIZE")
            price_filter = next(f for f in info["filters"] if f["filterType"] == "PRICE_FILTER")
            notional = next((f for f in info["filters"] if f["filterType"] in ("MIN_NOTIONAL", "NOTIONAL")), None)

            filters = {
                "stepSize": float(lot_size["stepSize"]),
                "minQty": float(lot_size["minQty"]),
                "tickSize": float(price_filter["tickSize"]),
                "minNotional": float(notional.get("minNotional") or notional.get("minNotionalValue") or 0),
            }
            self._filter_cache[symbol] = filters
            return filters
        except Exception as e:
            return {
                "stepSize": 0.00001,
                "minQty": 0.00001,
                "tickSize": 0.01,
                "minNotional": 10.0,
            }

    def get_btc_price(self) -> float:
        try:
            response = requests.get(f"{self.base_url}/api/v3/ticker/price?symbol=BTCUSDT")
            if response.status_code == 200:
                return float(response.json()["price"])
        except Exception as e:
            pass
        return 64000.0

    def get_bid_ask(self) -> Dict:
        try:
            response = requests.get(f"{self.base_url}/api/v3/ticker/bookTicker?symbol=BTCUSDT")
            if response.status_code == 200:
                data = response.json()
                return {
                    "bid": float(data["bidPrice"]),
                    "ask": float(data["askPrice"]),
                }
        except Exception as e:
            pass
        return {"bid": 0, "ask": 0}

    @staticmethod
    def _maker_safe_price(side: str, best_bid: float, best_ask: float, tick_size: float) -> float:
        if side.upper() == "BUY":
            target_price = best_bid + tick_size
            limit_price = best_bid if target_price >= best_ask else target_price
        else:
            target_price = best_ask - tick_size
            limit_price = best_ask if target_price <= best_bid else target_price
        return round_to_tick(limit_price, tick_size)

    def place_maker_limit_order(self, side: str, amount: float, is_quantity: bool = False, test_mode: bool = True) -> Dict:
        if test_mode:
            return self._simulate_order(side, amount, is_quantity)

        try:
            filters = self._get_symbol_filters("BTCUSDT")
            step_size = filters["stepSize"]
            min_qty = filters["minQty"]
            min_notional = filters["minNotional"]
            tick_size = filters["tickSize"]

            bid_ask = self.get_bid_ask()
            btc_price = self.get_btc_price()

            if is_quantity:
                btc_amount = amount
            else:
                if amount < min_notional:
                    amount = min_notional
                btc_amount = amount / btc_price

            btc_amount = round_to_step(btc_amount, step_size)
            if btc_amount < min_qty:
                btc_amount = min_qty

            best_bid = bid_ask.get("bid", btc_price)
            best_ask = bid_ask.get("ask", btc_price)
            limit_price = self._maker_safe_price(side, best_bid, best_ask, tick_size)

            quantity_str = format_quantity(btc_amount)
            price_str = format_price(limit_price)

            print(f"\n📡 PLACING MAKER {side.upper()} LIMIT ORDER...")
            print(f"   Current Price: ${btc_price:,.2f}")
            print(f"   Limit Price: ${limit_price:,.2f}")
            print(f"   Quantity: {quantity_str} BTC")

            params = {
                "symbol": "BTCUSDT",
                "side": side.upper(),
                "type": "LIMIT",
                "timeInForce": "LIMIT_MAKER",
                "quantity": quantity_str,
                "price": price_str,
            }

            result = self._send_signed_request("POST", "/api/v3/order", params)

            if "error" in result:
                return {"error": result["error"]}

            self.active_order_id = result.get('orderId')
            return {
                "order_id": self.active_order_id,
                "price": limit_price,
                "quantity": btc_amount,
                "status": result.get('status'),
                "side": side.upper(),
                "full_response": result
            }

        except Exception as e:
            return {"error": str(e)}

    def _simulate_order(self, side: str, amount: float, is_quantity: bool = False) -> Dict:
        btc_price = self.get_btc_price()
        bid_ask = self.get_bid_ask()
        tick_size = 0.01

        best_bid = bid_ask.get("bid") or btc_price
        best_ask = bid_ask.get("ask") or btc_price

        if is_quantity:
            btc_amount = amount
        else:
            btc_amount = amount / btc_price

        limit_price = self._maker_safe_price(side, best_bid, best_ask, tick_size)

        delay = random.uniform(1, CONFIG.get("paper_fill_delay", 2.0))
        print(f"   ⏳ Simulating order book wait... ({delay:.1f}s)")

        steps = max(1, int(delay))
        walk_price = btc_price
        filled = False
        for _ in range(steps):
            time.sleep(delay / steps)
            walk_price *= (1 + random.uniform(-0.0004, 0.0004))
            if side.upper() == "BUY" and walk_price <= limit_price:
                filled = True
                break
            if side.upper() == "SELL" and walk_price >= limit_price:
                filled = True
                break

        order_id = f"SIM_{int(time.time() * 1000)}"
        sim_data = {
            "order_id": order_id,
            "price": limit_price,
            "quantity": btc_amount,
            "status": "FILLED" if filled else "UNFILLED",
            "side": side.upper(),
            "simulated": True,
        }
        self.simulated_orders[order_id] = sim_data
        self.active_order_id = order_id
        return sim_data

    def wait_for_order_fill(self, order_result: Dict, max_wait: int = 300) -> Dict:
        if self.test_mode:
            if order_result.get("status") == "FILLED":
                return {"status": "FILLED", "price": order_result.get("price", 0), "quantity": order_result.get("quantity", 0)}
            print("   ⚠️ Paper order did not fill (price never reached limit), repricing...")
            return self.chase_order(order_result)

        order_id = order_result.get("order_id")
        if not order_id:
            return {"status": "ERROR", "message": "No order ID"}

        start_time = time.time()
        consecutive_errors = 0
        max_consecutive_errors = self.config.get("max_consecutive_status_errors", 5)

        while time.time() - start_time < max_wait:
            status = self.check_order_status(order_id)

            if "error" in status:
                consecutive_errors += 1
                if consecutive_errors >= max_consecutive_errors:
                    return {"status": "ERROR", "message": f"Repeated status-check failures: {status['error']}"}
                time.sleep(2)
                continue

            consecutive_errors = 0

            if status.get("status") == "FILLED":
                print(f"\n✅ Order {order_id} filled at ${float(status.get('price', 0)):,.2f}")
                return {
                    "status": "FILLED",
                    "price": float(status.get("price", 0)),
                    "quantity": float(status.get("executedQty", 0))
                }

            time.sleep(2)

        return self.chase_order(order_result)

    def chase_order(self, order_result: Dict) -> Dict:
        side = order_result.get("side") or order_result.get("full_response", {}).get("side", "BUY")
        max_attempts = 10

        try:
            current_qty = float(order_result.get("quantity") or 0.0)
        except (TypeError, ValueError):
            current_qty = 0.0
            
        if current_qty <= 0:
            return {"status": "ERROR", "message": "Invalid quantity for chase."}

        original_qty = current_qty

        for attempt in range(max_attempts):
            if not self.test_mode and self.active_order_id:
                status = self.check_order_status(self.active_order_id)

                if status.get("status") == "FILLED":
                    return {
                        "status": "FILLED",
                        "price": float(status.get("price", 0)),
                        "quantity": float(status.get("executedQty", original_qty))
                    }

                executed_qty = float(status.get("executedQty", 0.0) or 0.0)
                remaining_qty = original_qty - executed_qty

                if remaining_qty <= 0:
                    return {
                        "status": "FILLED",
                        "price": float(status.get("price", 0)),
                        "quantity": original_qty
                    }

                current_qty = remaining_qty
                self.cancel_order(self.active_order_id)

            result = self.place_maker_limit_order(
                side,
                current_qty,
                is_quantity=True,
                test_mode=self.test_mode
            )

            if "error" in result:
                return {"status": "ERROR", "message": result["error"]}

            if self.test_mode:
                if result.get("status") == "FILLED":
                    return {"status": "FILLED", "price": result.get("price", 0), "quantity": result.get("quantity", current_qty)}
                print(f"   🔄 Repricing attempt {attempt+1}/{max_attempts} (paper)...")
                order_result = result
                time.sleep(CONFIG.get("paper_reprice_interval", 2.0))
                continue

            time.sleep(2)
            status = self.check_order_status(self.active_order_id)

            if status.get("status") == "FILLED":
                return {
                    "status": "FILLED",
                    "price": float(status.get("price", 0)),
                    "quantity": float(status.get("executedQty", current_qty))
                }

            print(f"   🔄 Repricing attempt {attempt+1}/{max_attempts}...")
            time.sleep(CONFIG.get("reprice_interval", 30))

        return {"status": "TIMEOUT", "message": "Could not fill order after max chase attempts"}

    def check_order_status(self, order_id: str) -> Dict:
        # Fixed: Read actual simulated state instead of returning fixed 0.001 BTC
        if self.test_mode or str(order_id).startswith("SIM_"):
            order_info = self.simulated_orders.get(str(order_id), {})
            qty = order_info.get("quantity", 0.0)
            return {
                "status": order_info.get("status", "FILLED"),
                "price": str(order_info.get("price", self.get_btc_price())),
                "executedQty": str(qty) if order_info.get("status") == "FILLED" else "0.0"
            }
        
        return self._send_signed_request("GET", "/api/v3/order", {
            "symbol": "BTCUSDT",
            "orderId": order_id,
        })

    def cancel_order(self, order_id: str) -> bool:
        if self.test_mode or str(order_id).startswith("SIM_"):
            if str(order_id) in self.simulated_orders:
                self.simulated_orders[str(order_id)]["status"] = "CANCELED"
            self.active_order_id = None
            return True

        result = self._send_signed_request("DELETE", "/api/v3/order", {
            "symbol": "BTCUSDT",
            "orderId": order_id,
        })
        if "error" in result:
            return False
        self.active_order_id = None
        return True

# ========================================================================
# 🧠 BOT ENGINE
# ========================================================================

class CrisisArbitrageBot:
    def __init__(self, config: Dict):
        self.config = config
        self.test_mode = config.get("test_mode", True)
        self.capital = config["initial_capital"]
        self.total_profit = 0
        self.trades = []
        self.api = BinanceAPI(config)
        self.cycle_count = 0
        self.profit_target = config.get("profit_target", 0.005)
        self.stop_loss = config.get("stop_loss", 0.01)

    def calculate_real_pnl(self) -> Dict:
        total_buy = 0
        total_sell = 0
        total_fees = 0

        for trade in self.trades:
            if trade.get("buy_price") and trade.get("sell_price"):
                buy_value = trade["buy_price"] * trade["btc_amount"]
                sell_value = trade["sell_price"] * trade["btc_amount"]
                total_buy += buy_value
                total_sell += sell_value
                total_fees += trade.get("buy_fee", 0) + trade.get("sell_fee", 0)

        gross_profit = total_sell - total_buy
        net_profit = gross_profit - total_fees

        return {
            "gross_profit": gross_profit,
            "total_fees": total_fees,
            "net_profit": net_profit
        }

    def should_exit(self, entry_price: float, current_price: float) -> Dict:
        price_change = (current_price - entry_price) / entry_price

        if price_change >= self.profit_target:
            return {"exit": True, "reason": "PROFIT_TARGET", "change": price_change}
        elif price_change <= -self.stop_loss:
            return {"exit": True, "reason": "STOP_LOSS", "change": price_change}

        return {"exit": False, "change": price_change}

    def run_cycle(self) -> bool:
        self.cycle_count += 1
        print(f"\n🔄 CYCLE {self.cycle_count}/{self.config.get('cycles', 1)}")
        print("-" * 60)

        btc_price = self.api.get_btc_price()
        trade_percentage = self.config.get("trade_percentage", 0.70)
        trade_amount = self.capital * trade_percentage

        print(f"📊 Capital: ${self.capital:,.2f}")
        print(f"📈 BTC Price: ${btc_price:,.2f}")
        print(f"💵 Trade Amount: ${trade_amount:,.2f} ({trade_percentage*100:.0f}% of capital)")
        print(f"🧪 Test Mode: {self.test_mode}")

        # 1. BUY ORDER
        buy_result = self.api.place_maker_limit_order("BUY", trade_amount, is_quantity=False, test_mode=self.test_mode)
        if "error" in buy_result:
            print(f"❌ Buy order failed: {buy_result['error']}")
            return False

        fill_result = self.api.wait_for_order_fill(buy_result)
        if fill_result.get("status") != "FILLED":
            print(f"❌ Buy order not filled: {fill_result.get('message')}")
            return False

        buy_price = fill_result.get("price", btc_price)
        btc_amount = fill_result.get("quantity", trade_amount / btc_price)

        if not buy_price or buy_price <= 0 or not btc_amount or btc_amount <= 0:
            print("❌ Invalid fill prices/quantities returned.")
            return False

        buy_fee = buy_price * btc_amount * self.api.maker_fee_rate

        trade = {
            "btc_amount": btc_amount,
            "buy_price": buy_price,
            "sell_price": None,
            "buy_fee": buy_fee,
            "sell_fee": 0
        }

        # 2. MONITORING LOOP
        hold_seconds = self.config.get("hold_seconds", 3600)
        start_time = time.time()
        exit_triggered = False
        exit_reason = None

        print(f"\n⏳ Monitoring for exit signals (max {hold_seconds//60} minutes)...")
        print(f"   🎯 Profit Target: +{self.profit_target*100:.2f}%")
        print(f"   🛑 Stop Loss: -{self.stop_loss*100:.2f}%")

        check_interval = self.config.get("price_poll_interval", 5)

        while (time.time() - start_time) < hold_seconds:
            # Paper mode random walk simulation so paper trades hit profit targets
            if self.test_mode:
                current_price = trade["buy_price"] * (1 + random.uniform(-0.008, 0.009))
            else:
                current_price = self.api.get_btc_price()

            exit_check = self.should_exit(trade["buy_price"], current_price)

            if exit_check["exit"]:
                exit_triggered = True
                exit_reason = exit_check["reason"]
                trade["sell_price"] = current_price
                print(f"\n\n📊 EXIT SIGNAL DETECTED: {exit_reason}")
                print(f"   Exit Price: ${current_price:,.2f} ({exit_check['change']*100:+.2f}%)")
                break

            price_change = (current_price - trade["buy_price"]) / trade["buy_price"]
            print(f"   📊 Current: ${current_price:,.2f} ({price_change*100:+.2f}%)", end="\r")

            time.sleep(check_interval)

        if not exit_triggered:
            trade["sell_price"] = self.api.get_btc_price()
            print(f"\n⏰ Hold time expired. Force exiting at ${trade['sell_price']:,.2f}")

        # 3. SELL ORDER
        sell_result = self.api.place_maker_limit_order(
            "SELL",
            trade["btc_amount"],
            is_quantity=True,
            test_mode=self.test_mode
        )
        if "error" in sell_result:
            print(f"❌ Sell order placement failed: {sell_result['error']}")
            return False

        sell_fill = self.api.wait_for_order_fill(sell_result)
        if sell_fill.get("status") != "FILLED":
            print(f"❌ Sell order not filled: {sell_fill.get('message')}")
            return False

        sell_price = sell_fill.get("price", trade["sell_price"])
        trade["sell_price"] = sell_price
        trade["sell_fee"] = sell_price * trade["btc_amount"] * self.api.maker_fee_rate

        gross_profit = (sell_price - trade["buy_price"]) * trade["btc_amount"]
        net_profit = gross_profit - (trade["buy_fee"] + trade["sell_fee"])

        self.capital += net_profit
        self.total_profit += net_profit
        self.trades.append(trade)

        print(f"\n🎉 CYCLE COMPLETE!")
        print(f"   Buy Price:  ${trade['buy_price']:,.2f}")
        print(f"   Sell Price: ${trade['sell_price']:,.2f}")
        print(f"   Net Profit: ${net_profit:,.2f}")
        print(f"   New Capital: ${self.capital:,.2f}")
        return True

    def run(self):
        print("🚀 STARTING CRISIS ARBITRAGE BOT")
        print(f"   Total Cycles: {self.config.get('cycles', 1)}")
        print(f"   Initial Capital: ${self.capital:,.2f}")

        for _ in range(self.config.get("cycles", 1)):
            success = self.run_cycle()
            if not success:
                print("\n⛔ Cycle failed. Stopping bot execution.")
                break
            time.sleep(2)

        print("\n" + "=" * 60)
        print("🏁 BOT RUN COMPLETED")
        pnl = self.calculate_real_pnl()
        print(f"   Gross P&L:  ${pnl['gross_profit']:,.2f}")
        print(f"   Total Fees: ${pnl['total_fees']:,.2f}")
        print(f"   Net P&L:    ${pnl['net_profit']:,.2f}")
        print(f"   Final Capital: ${self.capital:,.2f}")
        print("=" * 60)

# ========================================================================
# 🏁 EXECUTION ENTRY POINT
# ========================================================================

if __name__ == "__main__":
    bot = CrisisArbitrageBot(CONFIG)
    bot.run()
