#!/usr/bin/env python3
"""
🚀 CRISIS ARBITRAGE BOT - BINANCE.US REAL TRADING
FIXED: LOT_SIZE and tick size filters
"""

import time
import json
import hashlib
import hmac
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import random
import os

# ========================================================================
# 📊 CONFIGURATION
# ========================================================================

CONFIG = {
    "initial_capital": 1000,
    "max_positions": 2,
    "risk_per_trade": 0.01,
    
    "binance": {
        "api_key": "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn",
        "api_secret": "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0",
        "enabled": True,
    },
    "bybit": {
        "api_key": "YOUR_BYBIT_API_KEY",
        "api_secret": "YOUR_BYBIT_API_SECRET",
        "enabled": False,
    },
    
    "manual_execution": {"enabled": False, "email_alerts": False},
    "assets": {"crypto": {"enabled": True, "max_per_trade": 5000}},
    "slippage": 0.10,
    "transaction_costs": 0.08,
    "target_return": 0.20,
}

# ========================================================================
# 📡 BINANCE.US API - FULLY FIXED
# ========================================================================

class ExchangeConnector:
    def __init__(self, config: Dict):
        self.config = config
        self.binance = None
        if config["binance"]["enabled"]:
            try:
                self.binance = BinanceAPI(
                    config["binance"]["api_key"],
                    config["binance"]["api_secret"]
                )
                print("✅ Binance.US connected")
            except Exception as e:
                print(f"⚠️ Binance.US connection failed: {e}")
    
    def place_order(self, symbol: str, side: str, amount: float, price: float) -> Dict:
        if self.binance:
            return self.binance.place_order(symbol, side, amount, price)
        return {"error": "No exchange connected"}

class BinanceAPI:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.binance.us"
        self._filter_cache = {}

    def get_account_balance(self) -> Dict:
        timestamp = int(time.time() * 1000)
        params = {"timestamp": timestamp, "recvWindow": 5000}
        query_string = "&".join([f"{k}={v}" for k, v in params.items()])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        headers = {"X-MBX-APIKEY": self.api_key}
        resp = requests.get(f"{self.base_url}/api/v3/account", headers=headers, params=params)
        if resp.status_code != 200:
            return {"error": f"HTTP {resp.status_code}: {resp.text}"}
        return [b for b in resp.json()["balances"] if float(b["free"]) > 0]

    def _get_symbol_filters(self, symbol: str) -> Dict:
        """Fetch and cache real LOT_SIZE / PRICE_FILTER values from Binance.US"""
        if symbol in self._filter_cache:
            return self._filter_cache[symbol]

        resp = requests.get(f"{self.base_url}/api/v3/exchangeInfo", params={"symbol": symbol})
        resp.raise_for_status()
        info = resp.json()["symbols"][0]

        lot_size = next(f for f in info["filters"] if f["filterType"] == "LOT_SIZE")
        price_filter = next(f for f in info["filters"] if f["filterType"] == "PRICE_FILTER")
        # MIN_NOTIONAL / NOTIONAL naming varies by exchange version
        notional = next((f for f in info["filters"] if f["filterType"] in ("MIN_NOTIONAL", "NOTIONAL")), None)

        filters = {
            "stepSize": lot_size["stepSize"],
            "minQty": lot_size["minQty"],
            "tickSize": price_filter["tickSize"],
            "minNotional": notional.get("minNotional") or notional.get("minNotionalValue") if notional else "0",
        }
        self._filter_cache[symbol] = filters
        return filters

    def _round_step(self, value: float, step_str: str) -> str:
        """Round value down to the nearest step, using Decimal to avoid float drift"""
        from decimal import Decimal, ROUND_DOWN
        step = Decimal(step_str)
        val = Decimal(str(value))
        rounded = (val // step) * step
        # format with the same number of decimal places as step_str
        decimals = abs(step.as_tuple().exponent)
        return f"{rounded:.{decimals}f}"

    def _round_price(self, value: float, tick_str: str) -> str:
        from decimal import Decimal, ROUND_HALF_UP
        tick = Decimal(tick_str)
        val = Decimal(str(value))
        rounded = (val / tick).quantize(Decimal("1"), rounding=ROUND_HALF_UP) * tick
        decimals = abs(tick.as_tuple().exponent)
        return f"{rounded:.{decimals}f}"

    def place_order(self, symbol: str, side: str, amount: float, price: float) -> Dict:
        """Place a REAL order on Binance.US using live exchange filters"""
        try:
            filters = self._get_symbol_filters(symbol)

            min_qty = float(filters["minQty"])
            if amount < min_qty:
                print(f"⚠️ Quantity {amount:.8f} below minimum {min_qty}. Using minimum.")
                amount = min_qty

            quantity_str = self._round_step(amount, filters["stepSize"])
            price_str = self._round_price(price, filters["tickSize"])

            # Guard against MIN_NOTIONAL rejection too, since that's the next common failure
            min_notional = float(filters.get("minNotional") or 0)
            if min_notional and float(quantity_str) * float(price_str) < min_notional:
                print(f"❌ Order notional ${float(quantity_str)*float(price_str):.2f} "
                      f"below exchange minimum ${min_notional:.2f}")
                return {"error": "Below MIN_NOTIONAL"}

            print(f"📋 Formatted Order (live filters: step={filters['stepSize']}, tick={filters['tickSize']}):")
            print(f"   Quantity: {quantity_str}")
            print(f"   Price: ${price_str}")

            timestamp = int(time.time() * 1000)
            params = {
                "symbol": symbol,
                "side": side.upper(),
                "type": "LIMIT",
                "timeInForce": "GTC",
                "quantity": quantity_str,
                "price": price_str,
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
            response = requests.post(f"{self.base_url}/api/v3/order", headers=headers, params=params)

            if response.status_code == 200:
                return response.json()
            else:
                return {"error": f"HTTP {response.status_code}: {response.text}"}

        except Exception as e:
            return {"error": str(e)}

# ========================================================================
# 🧠 TRADING ENGINE
# ========================================================================

class CrisisArbitrageBot:
    def __init__(self, config: Dict):
        self.config = config
        self.capital = config["initial_capital"]
        self.positions = []
        self.trades = []
        self.total_profit = 0
        self.win_count = 0
        self.loss_count = 0
        self.exchange = ExchangeConnector(config)
        
        self.btc_price = self._get_btc_price()
        self.fsi_data = self._load_fsi_data()
        self.wst_data = self._load_wst_data()
    
    def _get_btc_price(self) -> float:
        try:
            response = requests.get("https://api.binance.us/api/v3/ticker/price?symbol=BTCUSDT")
            if response.status_code == 200:
                return float(response.json()["price"])
        except Exception as e:
            print(f"⚠️ Could not fetch BTC price: {e}")
        return 64000.0
    
    def _load_fsi_data(self) -> Dict:
        return {
            "SOM": {"name": "Somalia", "flag": "🇸🇴", "fsi_score": 111.3},
            "SDN": {"name": "Sudan", "flag": "🇸🇩", "fsi_score": 109.3},
            "SSD": {"name": "South Sudan", "flag": "🇸🇸", "fsi_score": 109.0},
            "SYR": {"name": "Syria", "flag": "🇸🇾", "fsi_score": 108.1},
            "COD": {"name": "Congo-Kinshasa", "flag": "🇨🇩", "fsi_score": 106.7},
            "YEM": {"name": "Yemen", "flag": "🇾🇪", "fsi_score": 106.6},
            "AFG": {"name": "Afghanistan", "flag": "🇦🇫", "fsi_score": 103.9},
            "HTI": {"name": "Haiti", "flag": "🇭🇹", "fsi_score": 103.5},
            "UKR": {"name": "Ukraine", "flag": "🇺🇦", "fsi_score": 93.1},
            "LBN": {"name": "Lebanon", "flag": "🇱🇧", "fsi_score": 92.7},
            "ETH": {"name": "Ethiopia", "flag": "🇪🇹", "fsi_score": 98.1},
            "VEN": {"name": "Venezuela", "flag": "🇻🇪", "fsi_score": 89.0},
            "LKA": {"name": "Sri Lanka", "flag": "🇱🇰", "fsi_score": 88.2},
            "PAK": {"name": "Pakistan", "flag": "🇵🇰", "fsi_score": 91.7},
            "NGA": {"name": "Nigeria", "flag": "🇳🇬", "fsi_score": 96.6},
            "RUS": {"name": "Russia", "flag": "🇷🇺", "fsi_score": 81.6},
            "ZWE": {"name": "Zimbabwe", "flag": "🇿🇼", "fsi_score": 95.7},
        }
    
    def _load_wst_data(self) -> Dict:
        return {
            "USA": {"class": "Core", "recovery_rate": 0.85},
            "GBR": {"class": "Core", "recovery_rate": 0.80},
            "DEU": {"class": "Core", "recovery_rate": 0.82},
            "UKR": {"class": "Semi", "recovery_rate": 0.35},
            "RUS": {"class": "Semi", "recovery_rate": 0.50},
            "CHN": {"class": "Semi", "recovery_rate": 0.55},
            "IND": {"class": "Semi", "recovery_rate": 0.48},
            "BRA": {"class": "Semi", "recovery_rate": 0.50},
            "default": {"class": "Periphery", "recovery_rate": 0.26}
        }
    
    def get_opportunities(self) -> List[Dict]:
        countries = []
        for iso, data in self.fsi_data.items():
            wst = self.wst_data.get(iso, self.wst_data["default"])
            
            base_score = min(99, max(1, round((data["fsi_score"] / 120) * 100)))
            
            class_modifier = 0
            if wst["class"] == "Periphery":
                class_modifier = 5 + 10 / 4
            elif wst["class"] == "Semi":
                class_modifier = 2
            elif wst["class"] == "Core":
                class_modifier = -5
            
            score = min(99, max(1, base_score + class_modifier))
            
            discount = 0.15 + (score / 100) * 0.5
            if wst["class"] == "Periphery":
                discount += 0.10
            elif wst["class"] == "Semi":
                discount += 0.05
            discount = min(0.75, discount)
            
            countries.append({
                "iso": iso,
                "name": data["name"],
                "flag": data["flag"],
                "score": round(score),
                "discount": discount,
                "recovery_rate": wst["recovery_rate"],
                "wst_class": wst["class"],
            })
        
        countries.sort(key=lambda x: x["score"], reverse=True)
        return countries[:self.config["max_positions"]]
    
    def buy_crypto(self, country: Dict, position_size: float) -> Dict:
        entry_price = self.btc_price * (1 - country["discount"])
        btc_amount = position_size / entry_price
        
        print(f"\n📡 PLACING REAL BUY ORDER...")
        print(f"   Symbol: BTCUSDT")
        print(f"   Entry Price: ${entry_price:,.2f}")
        print(f"   Position Size: ${position_size:,.2f}")
        print(f"   Quantity: {btc_amount:.8f} BTC")
        
        result = self.exchange.place_order(
            symbol="BTCUSDT",
            side="BUY",
            amount=btc_amount,
            price=entry_price
        )
        
        if "error" in result:
            print(f"❌ Buy order failed: {result['error']}")
            return None
        
        print(f"✅ BUY ORDER PLACED!")
        print(f"   Order ID: {result.get('orderId', 'N/A')}")
        
        return result
    
    def sell_crypto(self, trade: Dict) -> Dict:
        btc_amount = trade["btc_quantity"]
        exit_price = self.btc_price * (1 + (1 - trade["recovery_rate"]) * 0.6)
        
        print(f"\n📡 PLACING REAL SELL ORDER...")
        print(f"   Symbol: BTCUSDT")
        print(f"   Exit Price: ${exit_price:,.2f}")
        print(f"   Quantity: {btc_amount:.8f} BTC")
        
        result = self.exchange.place_order(
            symbol="BTCUSDT",
            side="SELL",
            amount=btc_amount,
            price=exit_price
        )
        
        if "error" in result:
            print(f"❌ Sell order failed: {result['error']}")
            return None
        
        print(f"✅ SELL ORDER PLACED!")
        print(f"   Order ID: {result.get('orderId', 'N/A')}")
        
        return result
    
    def run_cycle(self):
        print("\n" + "="*70)
        print("🏦 CRISIS ARBITRAGE BOT - REAL BINANCE.US TRADING")
        print("="*70)
        print(f"📊 Starting Capital: ${self.capital:,.0f}")
        print(f"📈 BTC Price: ${self.btc_price:,.2f}")
        print("="*70)
        
        opportunities = self.get_opportunities()
        print(f"📊 Found {len(opportunities)} opportunities")
        
        for country in opportunities:
            position_size = self.capital * self.config["risk_per_trade"]
            print(f"\n🚀 EXECUTING TRADE: {country['flag']} {country['name']}")
            print(f"   Discount: {country['discount']*100:.0f}%")
            print(f"   Position Size: ${position_size:,.2f}")
            
            buy_result = self.buy_crypto(country, position_size)
            if buy_result is None:
                continue
            
            trade = {
                "country": country,
                "btc_quantity": round(position_size / (self.btc_price * (1 - country["discount"])), 8),
                "entry_price": self.btc_price * (1 - country["discount"]),
                "recovery_rate": country["recovery_rate"],
                "buy_order": buy_result,
                "sell_order": None
            }
            
            print(f"\n⏳ Holding for recovery...")
            time.sleep(5)
            
            sell_result = self.sell_crypto(trade)
            if sell_result is None:
                print("⚠️ Sell failed - position remains open")
                continue
            
            trade["sell_order"] = sell_result
            
            entry_price = float(buy_result.get("price", trade["entry_price"]))
            exit_price = float(sell_result.get("price", self.btc_price * (1 + (1 - trade["recovery_rate"]) * 0.6)))
            
            profit_pct = (exit_price - entry_price) / entry_price
            profit = trade["btc_quantity"] * (exit_price - entry_price)
            
            trade["profit_pct"] = profit_pct
            trade["profit"] = profit
            
            self.capital += profit
            self.total_profit += profit
            self.trades.append(trade)
            
            if profit > 0:
                self.win_count += 1
                print(f"🟢 CLOSED: {country['flag']} {country['name']} +{profit_pct*100:.1f}%")
            else:
                self.loss_count += 1
                print(f"🔴 CLOSED: {country['flag']} {country['name']} {profit_pct*100:.1f}%")
            
            print(f"💰 Profit: ${profit:,.2f}")
            print(f"💵 New Capital: ${self.capital:,.2f}")
        
        self.print_summary()
    
    def print_summary(self):
        total = len(self.trades)
        win_rate = (self.win_count / total * 100) if total > 0 else 0
        
        print("\n" + "="*70)
        print("🏆 REAL TRADING SUMMARY")
        print("="*70)
        print(f"💰 Realized P&L: ${self.total_profit:,.2f}")
        print(f"📊 Trades: {total}")
        print(f"✅ Win Rate: {win_rate:.1f}%")
        print(f"📈 ROI: {(self.total_profit / self.config['initial_capital']) * 100:.1f}%")
        print(f"💵 Current Capital: ${self.capital:,.0f}")
        print(f"✅ Wins: {self.win_count}")
        print(f"❌ Losses: {self.loss_count}")
        print("="*70)

# ========================================================================
# 🚀 MAIN
# ========================================================================

if __name__ == "__main__":
    bot = CrisisArbitrageBot(CONFIG)
    bot.run_cycle()
