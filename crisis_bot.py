#!/usr/bin/env python3
"""
🚀 CRISIS ARBITRAGE BOT - REAL BINANCE.US TRADING
RUNS 10 CYCLES - SCALED UP!
"""

import time
import hashlib
import hmac
import requests
from typing import Dict

# ========================================================================
# 📊 CONFIGURATION
# ========================================================================

CONFIG = {
    "initial_capital": 13.35,  # Your balance
    "test_mode": False,
    "trade_percentage": 0.80,   # 80% of capital = ~$10.68 per trade
    "cycles": 100,               # ✅ RUN 10 CYCLES
    "hold_seconds": 10,         # Hold time per trade
    "binance": {
        "api_key": "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn",
        "api_secret": "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0",
        "enabled": True,
    },
}

# ========================================================================
# 📡 BINANCE.US API
# ========================================================================

class BinanceAPI:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.binance.us"
        self._filter_cache = {}

    def _get_symbol_filters(self, symbol: str) -> Dict:
        if symbol in self._filter_cache:
            return self._filter_cache[symbol]

        resp = requests.get(f"{self.base_url}/api/v3/exchangeInfo", params={"symbol": symbol})
        resp.raise_for_status()
        info = resp.json()["symbols"][0]

        lot_size = next(f for f in info["filters"] if f["filterType"] == "LOT_SIZE")
        price_filter = next(f for f in info["filters"] if f["filterType"] == "PRICE_FILTER")
        notional = next((f for f in info["filters"] if f["filterType"] in ("MIN_NOTIONAL", "NOTIONAL")), None)

        filters = {
            "stepSize": lot_size["stepSize"],
            "minQty": lot_size["minQty"],
            "tickSize": price_filter["tickSize"],
            "minNotional": notional.get("minNotional") or notional.get("minNotionalValue") if notional else "0",
        }
        self._filter_cache[symbol] = filters
        return filters

    def _round_to_step(self, value: float, step_str: str) -> float:
        step = float(step_str)
        return int(value / step) * step

    def _get_btc_price(self) -> float:
        try:
            response = requests.get(f"{self.base_url}/api/v3/ticker/price?symbol=BTCUSDT")
            if response.status_code == 200:
                return float(response.json()["price"])
        except Exception as e:
            print(f"⚠️ Could not fetch BTC price: {e}")
        return 64000.0

    def place_market_order(self, side: str, amount_usdt: float) -> Dict:
        """Place a REAL MARKET order on Binance.US"""
        try:
            filters = self._get_symbol_filters("BTCUSDT")
            step_size = float(filters["stepSize"])
            min_qty = float(filters["minQty"])
            min_notional = float(filters["minNotional"])

            btc_price = self._get_btc_price()
            
            if amount_usdt < min_notional:
                print(f"⚠️ Amount ${amount_usdt:.2f} below minimum ${min_notional:.2f}")
                amount_usdt = min_notional
                print(f"   Adjusted to ${amount_usdt:.2f}")
            
            btc_amount = amount_usdt / btc_price
            btc_amount = self._round_to_step(btc_amount, filters["stepSize"])
            
            if btc_amount < min_qty:
                print(f"⚠️ Quantity {btc_amount:.8f} below minimum {min_qty}. Using minimum.")
                btc_amount = min_qty
            
            quantity_str = f"{btc_amount:.8f}"
            
            print(f"\n📡 PLACING {side.upper()} MARKET ORDER...")
            print(f"   BTC Price: ${btc_price:,.2f}")
            print(f"   Amount: ${amount_usdt:,.2f}")
            print(f"   Quantity: {quantity_str} BTC")
            
            timestamp = int(time.time() * 1000)
            
            params = {
                "symbol": "BTCUSDT",
                "side": side.upper(),
                "type": "MARKET",
                "quantity": quantity_str,
                "timestamp": timestamp,
                "recvWindow": 5000
            }
            
            query_string = "&".join([f"{k}={v}" for k, v in params.items()])
            signature = hmac.new(
                self.api_secret.encode('utf-8'),
                query_string.encode('utf-8'),
                hashlib.sha256
            ).hexdigest()
            params["signature"] = signature
            
            headers = {"X-MBX-APIKEY": self.api_key}
            response = requests.post(
                f"{self.base_url}/api/v3/order",
                headers=headers,
                params=params
            )
            
            if response.status_code == 200:
                result = response.json()
                print(f"✅ ORDER FILLED!")
                print(f"   Order ID: {result.get('orderId', 'N/A')}")
                
                order_price = float(result.get('price', 0))
                if order_price == 0:
                    order_price = btc_price
                    print(f"   Avg Price: ${order_price:,.2f}")
                else:
                    print(f"   Avg Price: ${order_price:,.2f}")
                
                executed_qty = float(result.get('executedQty', btc_amount))
                print(f"   Executed Qty: {executed_qty:.8f} BTC")
                
                return {
                    "order_id": result.get('orderId'),
                    "price": order_price,
                    "executed_qty": executed_qty,
                    "status": result.get('status'),
                    "full_response": result
                }
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}
                
        except Exception as e:
            return {"error": str(e)}

# ========================================================================
# 🧠 BOT ENGINE - 10 CYCLES
# ========================================================================

class CrisisArbitrageBot:
    def __init__(self, config: Dict):
        self.config = config
        self.capital = config["initial_capital"]
        self.total_profit = 0
        self.trades = []
        self.api = BinanceAPI(
            config["binance"]["api_key"],
            config["binance"]["api_secret"]
        )
        self.cycle_count = 0
    
    def run_cycle(self) -> bool:
        """Run ONE trading cycle"""
        self.cycle_count += 1
        print(f"\n🔄 CYCLE {self.cycle_count}/{self.config.get('cycles', 1)}")
        print("-"*50)
        
        btc_price = self.api._get_btc_price()
        trade_percentage = self.config.get("trade_percentage", 0.80)
        trade_amount = self.capital * trade_percentage
        
        print(f"📊 Capital: ${self.capital:,.2f}")
        print(f"📈 BTC Price: ${btc_price:,.2f}")
        print(f"💵 Trade Amount: ${trade_amount:,.2f} ({trade_percentage*100:.0f}% of capital)")
        
        # 1. BUY BTC
        buy_result = self.api.place_market_order("BUY", trade_amount)
        if "error" in buy_result:
            print(f"❌ Buy failed: {buy_result['error']}")
            return False
        
        # Store trade info
        trade = {
            "buy_order": buy_result,
            "btc_amount": buy_result.get('executed_qty', 0),
            "buy_price": buy_result.get('price', btc_price)
        }
        
        # 2. HOLD
        hold_seconds = self.config.get("hold_seconds", 10)
        print(f"\n⏳ Holding for {hold_seconds} seconds...")
        time.sleep(hold_seconds)
        
        # 3. SELL BTC
        current_price = self.api._get_btc_price()
        print(f"\n📡 SELLING at current market price...")
        sell_amount = trade["btc_amount"] * current_price
        sell_result = self.api.place_market_order("SELL", sell_amount)
        if "error" in sell_result:
            print(f"❌ Sell failed: {sell_result['error']}")
            return False
        
        trade["sell_order"] = sell_result
        trade["sell_price"] = sell_result.get('price', current_price)
        
        # Calculate profit
        if trade["buy_price"] == 0:
            trade["buy_price"] = btc_price
        
        profit_pct = (trade["sell_price"] - trade["buy_price"]) / trade["buy_price"]
        profit = trade["btc_amount"] * (trade["sell_price"] - trade["buy_price"])
        
        trade["profit_pct"] = profit_pct
        trade["profit"] = profit
        
        self.capital += profit
        self.total_profit += profit
        self.trades.append(trade)
        
        if profit > 0:
            print(f"🟢 PROFIT: +{profit_pct*100:.2f}%")
        else:
            print(f"🔴 LOSS: {profit_pct*100:.2f}%")
        
        print(f"💰 Profit: ${profit:,.4f}")
        print(f"💵 New Capital: ${self.capital:,.2f}")
        
        return True
    
    def run(self):
        """Run ALL cycles"""
        print("\n" + "="*70)
        print("🏦 CRISIS ARBITRAGE BOT - REAL TRADING (10 CYCLES)")
        print("="*70)
        print(f"📊 Starting Capital: ${self.capital:,.2f}")
        print(f"🔄 Cycles: {self.config.get('cycles', 1)}")
        print(f"⏱️ Hold Time: {self.config.get('hold_seconds', 10)} seconds")
        print("="*70)
        
        cycles = self.config.get("cycles", 1)
        successful_cycles = 0
        
        for cycle in range(cycles):
            success = self.run_cycle()
            if success:
                successful_cycles += 1
            else:
                print(f"⚠️ Cycle {cycle+1} failed, stopping...")
                break
            
            # Wait between cycles (except after the last one)
            if cycle < cycles - 1:
                wait_time = 2
                print(f"\n⏳ Waiting {wait_time} seconds before next cycle...")
                time.sleep(wait_time)
        
        self.print_summary(successful_cycles, cycles)
    
    def print_summary(self, successful_cycles, total_cycles):
        total = len(self.trades)
        win_rate = (sum(1 for t in self.trades if t.get("profit", 0) > 0) / total * 100) if total > 0 else 0
        
        print("\n" + "="*70)
        print("🏆 FINAL TRADING SUMMARY")
        print("="*70)
        print(f"📊 Cycles Completed: {successful_cycles}/{total_cycles}")
        print(f"💰 Total Realized P&L: ${self.total_profit:,.4f}")
        print(f"📊 Total Trades: {total}")
        print(f"✅ Win Rate: {win_rate:.1f}%")
        print(f"📈 Total ROI: {(self.total_profit / self.config['initial_capital']) * 100:.2f}%")
        print(f"💵 Final Capital: ${self.capital:,.2f}")
        print("="*70)
        
        # Show individual trade results
        if self.trades:
            print("\n📋 TRADE DETAILS:")
            print("-"*70)
            for i, trade in enumerate(self.trades, 1):
                status = "🟢" if trade.get("profit", 0) > 0 else "🔴"
                print(f"{status} Trade {i}: ${trade.get('profit', 0):,.4f} ({trade.get('profit_pct', 0)*100:.2f}%)")

# ========================================================================
# 🚀 MAIN
# ========================================================================

if __name__ == "__main__":
    bot = CrisisArbitrageBot(CONFIG)
    bot.run()
