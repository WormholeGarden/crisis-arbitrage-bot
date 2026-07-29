#!/usr/bin/env python3
"""
🚀 CRISIS ARBITRAGE BOT - SIMPLE MARKET TRADING
FIXED: Handles ZeroDivisionError and proper price extraction
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
    "initial_capital": 9.33,
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
                
                # ✅ EXTRACT PRICE (use market price if price is 0)
                order_price = float(result.get('price', 0))
                if order_price == 0:
                    order_price = btc_price
                    print(f"   Avg Price: Using market price ${order_price:,.2f}")
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
# 🧠 BOT ENGINE
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
    
    def run(self):
        print("\n" + "="*70)
        print("🏦 CRISIS ARBITRAGE BOT - SIMPLE MARKET TRADING")
        print("="*70)
        print(f"📊 Starting Capital: ${self.capital:,.2f}")
        
        btc_price = self.api._get_btc_price()
        print(f"📈 BTC Price: ${btc_price:,.2f}")
        print("="*70)
        
        # ✅ Use ALL capital
        trade_amount = self.capital
        
        print(f"\n🚀 EXECUTING TRADE...")
        print(f"   Trade Amount: ${trade_amount:,.2f} (all capital)")
        
        # 1. BUY BTC
        buy_result = self.api.place_market_order("BUY", trade_amount)
        if "error" in buy_result:
            print(f"❌ Buy failed: {buy_result['error']}")
            return
        
        # ✅ Store trade info with safe price extraction
        btc_amount = buy_result.get('executed_qty', 0)
        buy_price = buy_result.get('price', btc_price)
        
        trade = {
            "buy_order": buy_result,
            "btc_amount": btc_amount,
            "buy_price": buy_price
        }
        
        print(f"\n⏳ Holding for 10 seconds...")
        time.sleep(10)
        
        # Get current BTC price
        current_price = self.api._get_btc_price()
        
        # 2. SELL BTC
        print(f"\n📡 SELLING at current market price...")
        sell_amount = trade["btc_amount"] * current_price
        sell_result = self.api.place_market_order("SELL", sell_amount)
        if "error" in sell_result:
            print(f"❌ Sell failed: {sell_result['error']}")
            return
        
        # ✅ Extract sell price safely
        sell_price = sell_result.get('price', current_price)
        sell_qty = sell_result.get('executed_qty', 0)
        
        trade["sell_order"] = sell_result
        trade["sell_price"] = sell_price
        trade["sell_qty"] = sell_qty
        
        # ✅ Safely calculate profit (avoid division by zero)
        if trade["buy_price"] == 0:
            print("⚠️ Buy price was zero, using current market price for calculation")
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
        
        self.print_summary()
    
    def print_summary(self):
        total = len(self.trades)
        win_rate = (sum(1 for t in self.trades if t["profit"] > 0) / total * 100) if total > 0 else 0
        
        print("\n" + "="*70)
        print("🏆 TRADING SUMMARY")
        print("="*70)
        print(f"💰 Realized P&L: ${self.total_profit:,.4f}")
        print(f"📊 Trades: {total}")
        print(f"✅ Win Rate: {win_rate:.1f}%")
        print(f"📈 ROI: {(self.total_profit / self.config['initial_capital']) * 100:.2f}%")
        print(f"💵 Current Capital: ${self.capital:,.2f}")
        print("="*70)

# ========================================================================
# 🚀 MAIN
# ========================================================================

if __name__ == "__main__":
    bot = CrisisArbitrageBot(CONFIG)
    bot.run()
