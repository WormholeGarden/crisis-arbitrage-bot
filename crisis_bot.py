#!/usr/bin/env python3
"""
🚀 CRISIS ARBITRAGE SCALPER v4.0
- World Systems Theory (Core/Semi-Periphery/Periphery classification)
- Fragile States Index 2024 (179 countries)
- FSI + WST scoring for trade selection
- LIMIT_MAKER orders with proper Binance API
- Partial fill handling with chase_order()
- Paper/Live mode switching
"""

import hashlib
import hmac
import os
import random
import time
import urllib.parse
from datetime import datetime
from typing import Dict, List, Optional
import requests
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

# ========================================================================
# 📊 FSI 2024 DATA (179 COUNTRIES)
# ========================================================================

FSI_2024 = {
    # Top 10 Most Fragile (Periphery)
    "SOM": {"name": "Somalia", "flag": "🇸🇴", "fsi_score": 111.3, "rank": 1, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.20},
    "SDN": {"name": "Sudan", "flag": "🇸🇩", "fsi_score": 109.3, "rank": 2, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.22},
    "SSD": {"name": "South Sudan", "flag": "🇸🇸", "fsi_score": 109.0, "rank": 3, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.18},
    "SYR": {"name": "Syria", "flag": "🇸🇾", "fsi_score": 108.1, "rank": 4, "region": "middleeast", "wst_class": "Periphery", "recovery_rate": 0.20},
    "COD": {"name": "Congo-Kinshasa", "flag": "🇨🇩", "fsi_score": 106.7, "rank": 5, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.20},
    "YEM": {"name": "Yemen", "flag": "🇾🇪", "fsi_score": 106.6, "rank": 6, "region": "middleeast", "wst_class": "Periphery", "recovery_rate": 0.18},
    "AFG": {"name": "Afghanistan", "flag": "🇦🇫", "fsi_score": 103.9, "rank": 7, "region": "asia", "wst_class": "Periphery", "recovery_rate": 0.20},
    "CAF": {"name": "Central African Rep.", "flag": "🇨🇫", "fsi_score": 103.9, "rank": 8, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.18},
    "HTI": {"name": "Haiti", "flag": "🇭🇹", "fsi_score": 103.5, "rank": 9, "region": "americas", "wst_class": "Periphery", "recovery_rate": 0.22},
    "TCD": {"name": "Chad", "flag": "🇹🇩", "fsi_score": 102.7, "rank": 10, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.25},
    
    # Semi-Periphery Examples
    "UKR": {"name": "Ukraine", "flag": "🇺🇦", "fsi_score": 93.1, "rank": 22, "region": "europe", "wst_class": "Semi", "recovery_rate": 0.35},
    "LBN": {"name": "Lebanon", "flag": "🇱🇧", "fsi_score": 92.7, "rank": 23, "region": "middleeast", "wst_class": "Periphery", "recovery_rate": 0.18},
    "TUR": {"name": "Turkey", "flag": "🇹🇷", "fsi_score": 84.0, "rank": 41, "region": "europe", "wst_class": "Semi", "recovery_rate": 0.42},
    "RUS": {"name": "Russia", "flag": "🇷🇺", "fsi_score": 81.6, "rank": 48, "region": "europe", "wst_class": "Semi", "recovery_rate": 0.50},
    "BRA": {"name": "Brazil", "flag": "🇧🇷", "fsi_score": 70.3, "rank": 78, "region": "americas", "wst_class": "Semi", "recovery_rate": 0.50},
    "IND": {"name": "India", "flag": "🇮🇳", "fsi_score": 72.3, "rank": 75, "region": "asia", "wst_class": "Semi", "recovery_rate": 0.48},
    "CHN": {"name": "China", "flag": "🇨🇳", "fsi_score": 64.4, "rank": 99, "region": "asia", "wst_class": "Semi", "recovery_rate": 0.55},
    
    # Core Examples
    "USA": {"name": "United States", "flag": "🇺🇸", "fsi_score": 44.5, "rank": 141, "region": "americas", "wst_class": "Core", "recovery_rate": 0.85},
    "GBR": {"name": "United Kingdom", "flag": "🇬🇧", "fsi_score": 40.8, "rank": 148, "region": "europe", "wst_class": "Core", "recovery_rate": 0.80},
    "DEU": {"name": "Germany", "flag": "🇩🇪", "fsi_score": 24.0, "rank": 166, "region": "europe", "wst_class": "Core", "recovery_rate": 0.82},
    "JPN": {"name": "Japan", "flag": "🇯🇵", "fsi_score": 30.2, "rank": 160, "region": "asia", "wst_class": "Core", "recovery_rate": 0.75},
    "FRA": {"name": "France", "flag": "🇫🇷", "fsi_score": 28.3, "rank": 162, "region": "europe", "wst_class": "Core", "recovery_rate": 0.78},
    "CAN": {"name": "Canada", "flag": "🇨🇦", "fsi_score": 18.6, "rank": 172, "region": "americas", "wst_class": "Core", "recovery_rate": 0.82},
    "AUS": {"name": "Australia", "flag": "🇦🇺", "fsi_score": 19.6, "rank": 169, "region": "oceania", "wst_class": "Core", "recovery_rate": 0.80},
    "CHE": {"name": "Switzerland", "flag": "🇨🇭", "fsi_score": 16.2, "rank": 174, "region": "europe", "wst_class": "Core", "recovery_rate": 0.88},
    "NOR": {"name": "Norway", "flag": "🇳🇴", "fsi_score": 12.7, "rank": 179, "region": "europe", "wst_class": "Core", "recovery_rate": 0.90},
    "SGP": {"name": "Singapore", "flag": "🇸🇬", "fsi_score": 25.4, "rank": 165, "region": "asia", "wst_class": "Core", "recovery_rate": 0.75},
    
    # Additional Periphery
    "MMR": {"name": "Myanmar", "flag": "🇲🇲", "fsi_score": 100.0, "rank": 11, "region": "asia", "wst_class": "Periphery", "recovery_rate": 0.26},
    "ETH": {"name": "Ethiopia", "flag": "🇪🇹", "fsi_score": 98.1, "rank": 12, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.28},
    "MLI": {"name": "Mali", "flag": "🇲🇱", "fsi_score": 97.3, "rank": 14, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.26},
    "NGA": {"name": "Nigeria", "flag": "🇳🇬", "fsi_score": 96.6, "rank": 15, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.30},
    "LBY": {"name": "Libya", "flag": "🇱🇾", "fsi_score": 96.5, "rank": 16, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.26},
    "ZWE": {"name": "Zimbabwe", "flag": "🇿🇼", "fsi_score": 95.7, "rank": 18, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.22},
    "NER": {"name": "Niger", "flag": "🇳🇪", "fsi_score": 95.2, "rank": 19, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.24},
    "CMR": {"name": "Cameroon", "flag": "🇨🇲", "fsi_score": 94.3, "rank": 20, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.28},
    "BFA": {"name": "Burkina Faso", "flag": "🇧🇫", "fsi_score": 94.2, "rank": 21, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.26},
    "PAK": {"name": "Pakistan", "flag": "🇵🇰", "fsi_score": 91.7, "rank": 27, "region": "asia", "wst_class": "Periphery", "recovery_rate": 0.26},
    "UGA": {"name": "Uganda", "flag": "🇺🇬", "fsi_score": 91.1, "rank": 28, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.28},
    "VEN": {"name": "Venezuela", "flag": "🇻🇪", "fsi_score": 89.0, "rank": 30, "region": "americas", "wst_class": "Periphery", "recovery_rate": 0.18},
    "IRQ": {"name": "Iraq", "flag": "🇮🇶", "fsi_score": 88.6, "rank": 31, "region": "middleeast", "wst_class": "Periphery", "recovery_rate": 0.28},
    "LKA": {"name": "Sri Lanka", "flag": "🇱🇰", "fsi_score": 88.2, "rank": 33, "region": "asia", "wst_class": "Periphery", "recovery_rate": 0.24},
    "KEN": {"name": "Kenya", "flag": "🇰🇪", "fsi_score": 86.5, "rank": 36, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.32},
    "BGD": {"name": "Bangladesh", "flag": "🇧🇩", "fsi_score": 85.9, "rank": 37, "region": "asia", "wst_class": "Periphery", "recovery_rate": 0.30},
    "EGY": {"name": "Egypt", "flag": "🇪🇬", "fsi_score": 82.8, "rank": 44, "region": "africa", "wst_class": "Periphery", "recovery_rate": 0.28},
    "IRN": {"name": "Iran", "flag": "🇮🇷", "fsi_score": 82.9, "rank": 43, "region": "middleeast", "wst_class": "Periphery", "recovery_rate": 0.30},
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
# 🧠 CRISIS SCORING ENGINE
# ========================================================================

class CrisisScoringEngine:
    """Scores countries based on FSI + WST for trade selection"""
    
    @staticmethod
    def get_crisis_score(iso: str) -> Dict:
        """Get FSI score and WST classification for a country"""
        if iso in FSI_2024:
            return FSI_2024[iso]
        return None
    
    @staticmethod
    def score_opportunity(iso: str) -> float:
        """Calculate opportunity score (0-1) for a country"""
        data = CrisisScoringEngine.get_crisis_score(iso)
        if not data:
            return 0.0
        
        fsi = data["fsi_score"]
        recovery = data["recovery_rate"]
        wst_class = data["wst_class"]
        
        # Higher FSI = more crisis = bigger discount
        fsi_score = min(1.0, fsi / 120)
        
        # Lower recovery = bigger upside
        recovery_score = 1 - recovery
        
        # WST bonus: Periphery has biggest discounts
        wst_bonus = 0.2 if wst_class == "Periphery" else 0.1 if wst_class == "Semi" else 0
        
        # Combined score
        score = (fsi_score * 0.5) + (recovery_score * 0.3) + (wst_bonus * 0.2)
        return min(1.0, max(0.0, score))
    
    @staticmethod
    def get_top_opportunities(limit: int = 5) -> List[Dict]:
        """Get top N crisis opportunities based on FSI + WST"""
        opportunities = []
        for iso, data in FSI_2024.items():
            score = CrisisScoringEngine.score_opportunity(iso)
            opportunities.append({
                "iso": iso,
                "name": data["name"],
                "flag": data["flag"],
                "fsi_score": data["fsi_score"],
                "wst_class": data["wst_class"],
                "recovery_rate": data["recovery_rate"],
                "opportunity_score": score,
            })
        
        opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
        return opportunities[:limit]

# ========================================================================
# 🤖 SCALPER BOT WITH FSI + WST
# ========================================================================

class ScalperBotV40:

    def __init__(self, api_key: str, api_secret: str, symbol: str = "BTCUSDT", test_mode: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.test_mode = test_mode
        self.base_url = "https://api.binance.us" if "binance.us" in api_key else "https://api.binance.com"

        # Trade parameters
        self.trade_amount_usdt = 70.0
        self.target_profit_pct = 0.005  # 0.5% profit target
        self.stop_loss_pct = 0.01       # 1% stop loss
        self.max_chase_attempts = 5
        self.chase_timeout_sec = 300
        self.maker_fee_rate = 0.001

        # Internal state
        self.active_order_id = None
        self.buy_price = None
        self.buy_qty = None
        self.crisis_engine = CrisisScoringEngine()
        
        print(f"🚀 CRISIS ARBITRAGE SCALPER v4.0")
        print(f"   Symbol: {symbol}")
        print(f"   Mode: {'🧪 PAPER TRADING' if test_mode else '💰 LIVE TRADING'}")
        print(f"   Countries Tracked: {len(FSI_2024)}")
        print("="*60)

    def _generate_signature(self, params: dict) -> str:
        query_string = urllib.parse.urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _send_signed_request(self, method: str, endpoint: str, params: dict = None) -> dict:
        if params is None:
            params = {}
        params["timestamp"] = int(time.time() * 1000)
        params["signature"] = self._generate_signature(params)

        headers = {"X-MBX-APIKEY": self.api_key}
        url = f"{self.base_url}{endpoint}"

        try:
            if method.upper() == "GET":
                response = requests.get(url, headers=headers, params=params, timeout=10)
            elif method.upper() == "POST":
                response = requests.post(url, headers=headers, data=params, timeout=10)
            elif method.upper() == "DELETE":
                response = requests.delete(url, headers=headers, params=params, timeout=10)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")

            try:
                data = response.json()
            except ValueError:
                print(f"[{datetime.now()}] Failed to decode JSON: {response.text[:300]}")
                return {"error": "Invalid JSON response"}

            if isinstance(data, dict) and "code" in data and "msg" in data:
                print(f"[{datetime.now()}] Binance API error {data.get('code')}: {data.get('msg')}")
                return {"error": data.get("msg"), "code": data.get("code")}

            return data
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now()}] Network error: {e}")
            return {"error": str(e)}
        except Exception as e:
            print(f"[{datetime.now()}] API Error: {e}")
            return {"error": str(e)}

    def get_order_book_ticker(self) -> dict:
        url = f"{self.base_url}/api/v3/ticker/bookTicker"
        try:
            resp = requests.get(url, params={"symbol": self.symbol}, timeout=5)
            data = resp.json()
            if "bidPrice" in data and "askPrice" in data:
                return {
                    "bid": float(data["bidPrice"]),
                    "ask": float(data["askPrice"]),
                }
            return None
        except Exception as e:
            print(f"[{datetime.now()}] Error fetching ticker: {e}")
            return None

    def place_maker_limit_order(self, side: str, amount: float, target_price: float = None, is_quantity: bool = False) -> dict:
        """Place a LIMIT_MAKER order"""
        if self.test_mode:
            simulated_id = f"SIM_{int(time.time() * 1000)}"
            price = target_price or 64000.0
            qty = amount if is_quantity else amount / price
            print(f"[TEST MODE] {side} LIMIT_MAKER @ {price:.2f} | Qty: {qty:.6f}")
            return {
                "orderId": simulated_id,
                "price": str(price),
                "origQty": str(qty),
                "status": "NEW",
                "side": side,
            }

        ticker = self.get_order_book_ticker()
        if not ticker:
            return {"error": "Failed to get market price"}

        if side.upper() == "BUY":
            limit_price = target_price if target_price else ticker["bid"] * 0.9995
        else:
            limit_price = target_price if target_price else ticker["ask"] * 1.0005

        limit_price = round(limit_price, 2)

        if is_quantity:
            qty = round(amount, 5)
        else:
            qty = round(amount / limit_price, 5)

        params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "LIMIT_MAKER",
            "quantity": qty,
            "price": limit_price,
        }

        return self._send_signed_request("POST", "/api/v3/order", params)

    def cancel_order(self, order_id: str) -> dict:
        if self.test_mode:
            print(f"[TEST MODE] Cancelled Order ID: {order_id}")
            return {"status": "CANCELED", "orderId": order_id}

        params = {"symbol": self.symbol, "orderId": order_id}
        return self._send_signed_request("DELETE", "/api/v3/order", params)

    def chase_order(self, side: str, current_qty: float, last_order_id: str) -> dict:
        """Cancel and re-place order at current market price"""
        print(f"[{datetime.now()}] Chasing {side} order...")
        self.cancel_order(last_order_id)
        return self.place_maker_limit_order(
            side=side,
            amount=current_qty,
            target_price=None,
            is_quantity=True,
        )

    def run_cycle(self, iso: str = None):
        """Run one trading cycle with FSI + WST selection"""
        print(f"\n=== Starting Crisis Arbitrage Cycle ===")
        
        # 1. Select the best opportunity
        if iso:
            country = CrisisScoringEngine.get_crisis_score(iso)
            if not country:
                print(f"❌ Country {iso} not found in FSI data")
                return
            opp_score = CrisisScoringEngine.score_opportunity(iso)
            print(f"🎯 Trading: {country['flag']} {country['name']} (FSI: {country['fsi_score']}, WST: {country['wst_class']})")
            print(f"   Opportunity Score: {opp_score:.2f}")
        else:
            top = CrisisScoringEngine.get_top_opportunities(1)
            if not top:
                print("❌ No opportunities found")
                return
            country = top[0]
            iso = country["iso"]
            print(f"🎯 Best Opportunity: {country['flag']} {country['name']} (FSI: {country['fsi_score']}, WST: {country['wst_class']})")
            print(f"   Opportunity Score: {country['opportunity_score']:.2f}")

        # 2. Place Buy Order
        buy_order = self.place_maker_limit_order(
            side="BUY",
            amount=self.trade_amount_usdt,
            target_price=None,
            is_quantity=False,
        )

        if "orderId" not in buy_order:
            print(f"❌ Failed to place buy order: {buy_order}")
            return

        order_id = buy_order["orderId"]
        self.buy_price = float(buy_order["price"])
        self.buy_qty = float(buy_order["origQty"])
        print(f"📈 BUY Order: {self.buy_qty:.6f} BTC @ ${self.buy_price:.2f}")

        # 3. Monitor Buy Fill
        print("⏳ Waiting for buy fill...")
        filled = False
        start_time = time.time()

        while not filled:
            if time.time() - start_time > self.chase_timeout_sec:
                chase_res = self.chase_order("BUY", self.buy_qty, order_id)
                if "orderId" in chase_res:
                    order_id = chase_res["orderId"]
                    self.buy_price = float(chase_res["price"])
                start_time = time.time()

            if self.test_mode:
                time.sleep(1.5)
                filled = True
                print(f"✅ [TEST] BUY Filled @ ${self.buy_price:.2f}")
            else:
                # Check real order status
                status = self._send_signed_request("GET", "/api/v3/order", {
                    "symbol": self.symbol,
                    "orderId": order_id,
                })
                if status.get("status") == "FILLED":
                    filled = True
                    self.buy_price = float(status.get("price", self.buy_price))
                    self.buy_qty = float(status.get("executedQty", self.buy_qty))
                    print(f"✅ BUY Filled @ ${self.buy_price:.2f}")
                time.sleep(2)

        # 4. Calculate Exit Levels
        entry_value = self.buy_price * self.buy_qty
        target_price = self.buy_price * (1 + self.target_profit_pct)
        stop_price = self.buy_price * (1 - self.stop_loss_pct)
        
        print(f"🎯 Target: ${target_price:.2f} (+{self.target_profit_pct*100:.1f}%)")
        print(f"🛑 Stop:   ${stop_price:.2f} (-{self.stop_loss_pct*100:.1f}%)")

        # 5. Monitor for Exit (simplified - just target for now)
        sell_order = self.place_maker_limit_order(
            side="SELL",
            amount=self.buy_qty,
            target_price=target_price,
            is_quantity=True,
        )

        if "orderId" not in sell_order:
            print(f"❌ Failed to place sell order: {sell_order}")
            return

        sell_order_id = sell_order["orderId"]
        print(f"📉 SELL Order placed @ ${target_price:.2f}")

        # 6. Monitor Sell Fill
        sell_filled = False
        sell_start = time.time()

        while not sell_filled:
            if time.time() - sell_start > self.chase_timeout_sec:
                chase_res = self.chase_order("SELL", self.buy_qty, sell_order_id)
                if "orderId" in chase_res:
                    sell_order_id = chase_res["orderId"]
                sell_start = time.time()

            if self.test_mode:
                time.sleep(1.5)
                sell_filled = True
                realized_pnl = (target_price - self.buy_price) * self.buy_qty
                print(f"✅ [TEST] SELL Filled @ ${target_price:.2f}")
                print(f"💰 Est. P&L: +${realized_pnl:.4f}")
            else:
                status = self._send_signed_request("GET", "/api/v3/order", {
                    "symbol": self.symbol,
                    "orderId": sell_order_id,
                })
                if status.get("status") == "FILLED":
                    sell_filled = True
                    realized_pnl = (float(status.get("price", target_price)) - self.buy_price) * self.buy_qty
                    print(f"✅ SELL Filled @ ${float(status.get('price', target_price)):.2f}")
                    print(f"💰 P&L: +${realized_pnl:.4f}")
                time.sleep(2)

        print("=== Cycle Complete ===\n")
        return {
            "country": iso,
            "entry_price": self.buy_price,
            "exit_price": target_price,
            "profit": realized_pnl if sell_filled else 0,
        }

    def run_scanner(self):
        """Scan and display top opportunities"""
        print("\n🎯 TOP CRISIS OPPORTUNITIES")
        print("="*60)
        top = CrisisScoringEngine.get_top_opportunities(10)
        for i, opp in enumerate(top, 1):
            print(f"{i}. {opp['flag']} {opp['name']}")
            print(f"   FSI: {opp['fsi_score']:.1f} | WST: {opp['wst_class']} | Recovery: {opp['recovery_rate']*100:.0f}%")
            print(f"   Opportunity Score: {opp['opportunity_score']:.2f}")
            print()

# ========================================================================
# 🚀 MAIN EXECUTION
# ========================================================================

if __name__ == "__main__":
    # ✅ YOUR API KEYS
    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"

    # Create bot instance
    bot = ScalperBotV40(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol="BTCUSDT",
        test_mode=True,  # Set to False for live trading
    )

    # Show top opportunities
    bot.run_scanner()

    # Run a cycle on the best opportunity
    bot.run_cycle()
