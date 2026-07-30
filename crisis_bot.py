#!/usr/bin/env python3
"""
CRISIS ARBITRAGE SCALPER v4.1 - FIXED
Changes from v4.0:
  - FIX: base_url was chosen by checking "binance.us" in api_key, which is
    never true for a real key, so it always fell through to api.binance.com.
    That endpoint blocks US-based connections, which is why every buy order
    failed with "Failed to get market price". You now pass the exchange
    region explicitly.
  - FIX: get_order_book_ticker() swallowed the real error/response instead
    of printing it, making this bug invisible. It now logs status code and
    body on failure.
  - FIX: added a startup connectivity check so a bad endpoint/key fails
    loudly before you burn through cycles.
  - FIX: stop_price was computed but never enforced. The sell-monitoring
    loop now polls the market and exits the position if price falls to the
    stop level, instead of waiting forever at the profit target only.
    This means live win rate will NOT be 100% - that number was an artifact
    of paper mode never checking for a loss exit.
"""

import hashlib
import hmac
import os
import random
import time
import urllib.parse
import csv
import json
from datetime import datetime
from typing import Dict, List, Optional
import requests
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

# ========================================================================
# FSI 2024 DATA (subset)
# ========================================================================

FSI_2024 = {
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
    "UKR": {"name": "Ukraine", "flag": "🇺🇦", "fsi_score": 93.1, "rank": 22, "region": "europe", "wst_class": "Semi", "recovery_rate": 0.35},
    "LBN": {"name": "Lebanon", "flag": "🇱🇧", "fsi_score": 92.7, "rank": 23, "region": "middleeast", "wst_class": "Periphery", "recovery_rate": 0.18},
    "TUR": {"name": "Turkey", "flag": "🇹🇷", "fsi_score": 84.0, "rank": 41, "region": "europe", "wst_class": "Semi", "recovery_rate": 0.42},
    "RUS": {"name": "Russia", "flag": "🇷🇺", "fsi_score": 81.6, "rank": 48, "region": "europe", "wst_class": "Semi", "recovery_rate": 0.50},
    "BRA": {"name": "Brazil", "flag": "🇧🇷", "fsi_score": 70.3, "rank": 78, "region": "americas", "wst_class": "Semi", "recovery_rate": 0.50},
    "IND": {"name": "India", "flag": "🇮🇳", "fsi_score": 72.3, "rank": 75, "region": "asia", "wst_class": "Semi", "recovery_rate": 0.48},
    "CHN": {"name": "China", "flag": "🇨🇳", "fsi_score": 64.4, "rank": 99, "region": "asia", "wst_class": "Semi", "recovery_rate": 0.55},
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
# DECIMAL HELPERS
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
# CRISIS SCORING ENGINE
# ========================================================================

class CrisisScoringEngine:
    @staticmethod
    def get_crisis_score(iso: str) -> Dict:
        if iso in FSI_2024:
            return FSI_2024[iso]
        return None

    @staticmethod
    def score_opportunity(iso: str) -> float:
        data = CrisisScoringEngine.get_crisis_score(iso)
        if not data:
            return 0.0
        fsi = data["fsi_score"]
        recovery = data["recovery_rate"]
        wst_class = data["wst_class"]
        fsi_score = min(1.0, fsi / 120)
        recovery_score = 1 - recovery
        wst_bonus = 0.2 if wst_class == "Periphery" else 0.1 if wst_class == "Semi" else 0
        score = (fsi_score * 0.5) + (recovery_score * 0.3) + (wst_bonus * 0.2)
        return min(1.0, max(0.0, score))

    @staticmethod
    def get_top_opportunities(limit: int = 5) -> List[Dict]:
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
# SCALPER BOT
# ========================================================================

class ScalperBotV40:

    def __init__(self, api_key: str, api_secret: str, symbol: str = "BTCUSDT",
                 test_mode: bool = True, exchange_region: str = "us"):
        """
        exchange_region: "us" -> api.binance.us, "global" -> api.binance.com
        This used to be auto-detected by checking a substring of the API key,
        which never matched and silently forced api.binance.com even for US
        users (who get blocked there). Pass it explicitly instead.
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.test_mode = test_mode

        if exchange_region.lower() == "us":
            self.base_url = "https://api.binance.us"
        elif exchange_region.lower() == "global":
            self.base_url = "https://api.binance.com"
        else:
            raise ValueError('exchange_region must be "us" or "global"')

        # Trade parameters
        self.trade_amount_usdt = 70.0
        self.target_profit_pct = 0.005  # 0.5% profit target
        self.stop_loss_pct = 0.01       # 1% stop loss
        self.max_chase_attempts = 5
        self.chase_timeout_sec = 300
        self.stop_loss_poll_sec = 5     # how often to check for stop-loss breach
        self.maker_fee_rate = 0.001

        # Internal state
        self.active_order_id = None
        self.buy_price = None
        self.buy_qty = None
        self.crisis_engine = CrisisScoringEngine()

        self.cycle_stats = {
            "total_cycles": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "net_profit": 0.0,
            "start_time": None,
            "end_time": None,
            "cycle_results": []
        }

        self.country_performance = {}

        print(f"CRISIS ARBITRAGE SCALPER v4.1 - 100 CYCLES MODE")
        print(f"   Symbol: {symbol}")
        print(f"   Exchange: {self.base_url}")
        print(f"   Mode: {'PAPER TRADING' if test_mode else 'LIVE TRADING'}")
        print(f"   Countries Tracked: {len(FSI_2024)}")
        print(f"   Target Profit: {self.target_profit_pct*100:.1f}% per cycle")
        print("="*60)

        if not test_mode:
            self._check_connectivity()

    def _check_connectivity(self):
        """Fail loudly at startup instead of silently on cycle 1 if the
        endpoint, API key, or network is misconfigured."""
        print("Running startup connectivity check...")
        ticker = self.get_order_book_ticker()
        if not ticker:
            print("STARTUP CHECK FAILED: could not fetch a ticker from "
                  f"{self.base_url}. Common causes:")
            print("  - Wrong region: US-based connections are blocked on "
                  "api.binance.com; use exchange_region='us' (api.binance.us).")
            print("  - Non-US connections to api.binance.us will fail; use "
                  "exchange_region='global' instead.")
            print("  - Bad/expired API key or IP not whitelisted.")
            raise SystemExit("Aborting: fix connectivity before running live cycles.")
        print(f"Connectivity OK. {self.symbol} bid={ticker['bid']} ask={ticker['ask']}")

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
                print(f"[{datetime.now()}] Failed to decode JSON "
                      f"(status {response.status_code}): {response.text[:300]}")
                return {"error": "Invalid JSON response", "status_code": response.status_code}

            if isinstance(data, dict) and "code" in data and "msg" in data:
                print(f"[{datetime.now()}] Binance API error {data.get('code')}: {data.get('msg')}")
                return {"error": data.get("msg"), "code": data.get("code")}

            return data
        except requests.exceptions.RequestException as e:
            print(f"[{datetime.now()}] Network error calling {url}: {e}")
            return {"error": str(e)}
        except Exception as e:
            print(f"[{datetime.now()}] API Error calling {url}: {e}")
            return {"error": str(e)}

    def get_order_book_ticker(self) -> Optional[dict]:
        url = f"{self.base_url}/api/v3/ticker/bookTicker"
        try:
            resp = requests.get(url, params={"symbol": self.symbol}, timeout=5)
            if resp.status_code != 200:
                # FIX: this used to be silently discarded - now surfaced.
                print(f"[{datetime.now()}] Ticker request failed "
                      f"(status {resp.status_code}): {resp.text[:300]}")
                return None
            data = resp.json()
            if "bidPrice" in data and "askPrice" in data:
                return {
                    "bid": float(data["bidPrice"]),
                    "ask": float(data["askPrice"]),
                }
            print(f"[{datetime.now()}] Unexpected ticker response: {data}")
            return None
        except Exception as e:
            print(f"[{datetime.now()}] Error fetching ticker from {url}: {e}")
            return None

    def get_current_price(self) -> Optional[float]:
        """Midpoint price, used for stop-loss checks."""
        ticker = self.get_order_book_ticker()
        if not ticker:
            return None
        return (ticker["bid"] + ticker["ask"]) / 2

    def place_maker_limit_order(self, side: str, amount: float, target_price: float = None, is_quantity: bool = False) -> dict:
        if self.test_mode:
            simulated_id = f"SIM_{int(time.time() * 1000)}"
            price = target_price or (64000.0 + random.uniform(-500, 500))
            qty = amount if is_quantity else amount / price
            print(f"[TEST MODE] {side} LIMIT_MAKER @ ${price:.2f} | Qty: {qty:.6f}")
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

    def place_market_order(self, side: str, quantity: float) -> dict:
        """Used for emergency stop-loss exits where we need an immediate
        fill rather than waiting for a maker order to be hit."""
        if self.test_mode:
            simulated_id = f"SIM_MKT_{int(time.time() * 1000)}"
            price = 64000.0 + random.uniform(-500, 500)
            print(f"[TEST MODE] {side} MARKET | Qty: {quantity:.6f} @ ~${price:.2f}")
            return {
                "orderId": simulated_id,
                "price": str(price),
                "executedQty": str(quantity),
                "status": "FILLED",
                "side": side,
            }

        qty = round(quantity, 5)
        params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": qty,
        }
        return self._send_signed_request("POST", "/api/v3/order", params)

    def cancel_order(self, order_id: str) -> dict:
        if self.test_mode:
            print(f"[TEST MODE] Cancelled Order ID: {order_id}")
            return {"status": "CANCELED", "orderId": order_id}

        params = {"symbol": self.symbol, "orderId": order_id}
        return self._send_signed_request("DELETE", "/api/v3/order", params)

    def chase_order(self, side: str, current_qty: float, last_order_id: str) -> dict:
        print(f"[{datetime.now()}] Chasing {side} order...")
        self.cancel_order(last_order_id)
        return self.place_maker_limit_order(
            side=side,
            amount=current_qty,
            target_price=None,
            is_quantity=True,
        )

    def run_cycle(self, iso: str = None, cycle_number: int = 0) -> dict:
        print(f"\n{'='*60}")
        print(f"CYCLE {cycle_number}/100")
        print(f"{'='*60}")

        if iso:
            country = CrisisScoringEngine.get_crisis_score(iso)
            if not country:
                print(f"Country {iso} not found in FSI data")
                return {"success": False, "error": "Country not found"}
            opp_score = CrisisScoringEngine.score_opportunity(iso)
            print(f"Trading: {country['flag']} {country['name']} (FSI: {country['fsi_score']}, WST: {country['wst_class']})")
            print(f"   Opportunity Score: {opp_score:.2f}")
        else:
            top_opportunities = CrisisScoringEngine.get_top_opportunities(20)
            if not top_opportunities:
                print("No opportunities found")
                return {"success": False, "error": "No opportunities"}
            idx = (cycle_number - 1) % len(top_opportunities)
            country = top_opportunities[idx]
            iso = country["iso"]
            print(f"Trading: {country['flag']} {country['name']} (FSI: {country['fsi_score']}, WST: {country['wst_class']})")
            print(f"   Opportunity Score: {country['opportunity_score']:.2f}")

        # 2. Place Buy Order
        buy_amount = self.trade_amount_usdt * (1 + random.uniform(-0.05, 0.05))
        buy_order = self.place_maker_limit_order(
            side="BUY",
            amount=buy_amount,
            target_price=None,
            is_quantity=False,
        )

        if "orderId" not in buy_order:
            print(f"Failed to place buy order: {buy_order}")
            return {"success": False, "error": buy_order.get("error", "Buy order failed")}

        order_id = buy_order["orderId"]
        self.buy_price = float(buy_order["price"])
        self.buy_qty = float(buy_order["origQty"])
        print(f"BUY Order: {self.buy_qty:.6f} BTC @ ${self.buy_price:.2f}")

        # 3. Monitor Buy Fill
        print("Waiting for buy fill...")
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
                time.sleep(1.0 + random.uniform(0, 1.0))
                filled = True
                print(f"[TEST] BUY Filled @ ${self.buy_price:.2f}")
            else:
                status = self._send_signed_request("GET", "/api/v3/order", {
                    "symbol": self.symbol,
                    "orderId": order_id,
                })
                if status.get("status") == "FILLED":
                    filled = True
                    self.buy_price = float(status.get("price", self.buy_price))
                    self.buy_qty = float(status.get("executedQty", self.buy_qty))
                    print(f"BUY Filled @ ${self.buy_price:.2f}")
                time.sleep(2)

        # 4. Calculate Exit Levels
        target_profit_pct = self.target_profit_pct * (1 + random.uniform(-0.1, 0.1))
        target_price = self.buy_price * (1 + target_profit_pct)
        stop_price = self.buy_price * (1 - self.stop_loss_pct)

        print(f"Target: ${target_price:.2f} (+{target_profit_pct*100:.1f}%)")
        print(f"Stop:   ${stop_price:.2f} (-{self.stop_loss_pct*100:.1f}%)")

        # 5. Place Sell Order (at target)
        sell_order = self.place_maker_limit_order(
            side="SELL",
            amount=self.buy_qty,
            target_price=target_price,
            is_quantity=True,
        )

        if "orderId" not in sell_order:
            print(f"Failed to place sell order: {sell_order}")
            return {"success": False, "error": sell_order.get("error", "Sell order failed")}

        sell_order_id = sell_order["orderId"]
        print(f"SELL Order placed @ ${target_price:.2f}")

        # 6. Monitor for either target fill OR stop-loss breach.
        # FIX: previously this loop only ever waited for the target sell to
        # fill, so stop_price was computed but never actually enforced -
        # positions could only "win" or hang open, never realize a loss.
        sell_filled = False
        sell_start = time.time()
        exit_price = target_price
        stopped_out = False
        last_stop_check = 0.0

        while not sell_filled:
            now = time.time()

            if now - sell_start > self.chase_timeout_sec:
                chase_res = self.chase_order("SELL", self.buy_qty, sell_order_id)
                if "orderId" in chase_res:
                    sell_order_id = chase_res["orderId"]
                sell_start = time.time()

            if self.test_mode:
                time.sleep(1.0 + random.uniform(0, 1.0))
                # Simulate a market that can move against us too, so paper
                # mode isn't artificially guaranteed to win every time.
                sim_price = self.buy_price * (1 + random.uniform(-0.012, 0.012))
                if sim_price <= stop_price:
                    exit_price = stop_price
                    stopped_out = True
                    print(f"[TEST] STOP-LOSS hit @ ${exit_price:.2f}")
                else:
                    exit_price = target_price
                    print(f"[TEST] SELL Filled @ ${target_price:.2f}")
                sell_filled = True
            else:
                # Check target order status
                status = self._send_signed_request("GET", "/api/v3/order", {
                    "symbol": self.symbol,
                    "orderId": sell_order_id,
                })
                if status.get("status") == "FILLED":
                    sell_filled = True
                    exit_price = float(status.get("price", target_price))
                    print(f"SELL Filled @ ${exit_price:.2f}")

                # Poll for stop-loss breach independently of the fill check
                elif now - last_stop_check > self.stop_loss_poll_sec:
                    last_stop_check = now
                    current_price = self.get_current_price()
                    if current_price is not None and current_price <= stop_price:
                        print(f"STOP-LOSS breached: current ${current_price:.2f} <= stop ${stop_price:.2f}")
                        self.cancel_order(sell_order_id)
                        exit_res = self.place_market_order("SELL", self.buy_qty)
                        if "error" in exit_res:
                            print(f"Stop-loss exit failed, retrying: {exit_res}")
                            time.sleep(2)
                            continue
                        sell_filled = True
                        stopped_out = True
                        exit_price = float(exit_res.get("price", current_price))
                        print(f"Stopped out @ ${exit_price:.2f}")

                if not sell_filled:
                    time.sleep(2)

        realized_pnl = (exit_price - self.buy_price) * self.buy_qty
        print(f"P&L: ${realized_pnl:.4f}" + (" (stop-loss exit)" if stopped_out else ""))
        print("=== Cycle Complete ===")

        if iso not in self.country_performance:
            self.country_performance[iso] = {
                "name": country["name"],
                "flag": country["flag"],
                "trades": 0,
                "total_profit": 0,
                "wins": 0,
                "losses": 0
            }

        self.country_performance[iso]["trades"] += 1
        self.country_performance[iso]["total_profit"] += realized_pnl
        if realized_pnl > 0:
            self.country_performance[iso]["wins"] += 1
        else:
            self.country_performance[iso]["losses"] += 1

        result = {
            "success": True,
            "cycle": cycle_number,
            "country": iso,
            "country_name": country["name"],
            "country_flag": country["flag"],
            "fsi_score": country["fsi_score"],
            "wst_class": country["wst_class"],
            "entry_price": self.buy_price,
            "exit_price": exit_price,
            "quantity": self.buy_qty,
            "profit": realized_pnl,
            "profit_percent": (realized_pnl / (self.buy_price * self.buy_qty)) * 100,
            "stopped_out": stopped_out,
            "timestamp": datetime.now().isoformat()
        }

        self.cycle_stats["total_cycles"] += 1
        if realized_pnl > 0:
            self.cycle_stats["successful_cycles"] += 1
            self.cycle_stats["total_profit"] += realized_pnl
        else:
            self.cycle_stats["failed_cycles"] += 1
            self.cycle_stats["total_loss"] += abs(realized_pnl)

        self.cycle_stats["net_profit"] += realized_pnl
        self.cycle_stats["cycle_results"].append(result)

        return result

    def run_scanner(self):
        print("\nTOP CRISIS OPPORTUNITIES")
        print("="*60)
        top = CrisisScoringEngine.get_top_opportunities(10)
        for i, opp in enumerate(top, 1):
            print(f"{i}. {opp['flag']} {opp['name']}")
            print(f"   FSI: {opp['fsi_score']:.1f} | WST: {opp['wst_class']} | Recovery: {opp['recovery_rate']*100:.0f}%")
            print(f"   Opportunity Score: {opp['opportunity_score']:.2f}")
            print()

    def run_100_cycles(self, delay_between_cycles: int = 3):
        print("\n" + "="*60)
        print("STARTING 100 CYCLES EXECUTION")
        print("="*60)

        self.cycle_stats["start_time"] = datetime.now()
        top_countries = CrisisScoringEngine.get_top_opportunities(30)

        for cycle_num in range(1, 101):
            try:
                country_idx = (cycle_num - 1) % len(top_countries)
                selected_country = top_countries[country_idx]["iso"]

                print(f"\nCycle {cycle_num}/100 - Trading {top_countries[country_idx]['flag']} {top_countries[country_idx]['name']}")

                result = self.run_cycle(iso=selected_country, cycle_number=cycle_num)

                if not result.get("success", False):
                    print(f"Cycle {cycle_num} failed: {result.get('error', 'Unknown error')}")
                else:
                    print(f"Cycle {cycle_num} completed.")
                    print(f"   Profit: ${result.get('profit', 0):.4f} ({result.get('profit_percent', 0):.2f}%)")

                self.print_current_stats()
                self.export_results_to_csv()

                if cycle_num < 100:
                    wait_time = delay_between_cycles + random.uniform(0, 2)
                    print(f"\nWaiting {wait_time:.1f} seconds before next cycle...")
                    time.sleep(wait_time)

            except KeyboardInterrupt:
                print("\nExecution interrupted by user")
                break
            except Exception as e:
                print(f"Error in cycle {cycle_num}: {e}")
                self.cycle_stats["failed_cycles"] += 1
                if cycle_num < 100:
                    wait_time = delay_between_cycles * 2
                    print(f"Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)

        self.cycle_stats["end_time"] = datetime.now()
        self.print_final_summary()
        self.export_final_report()

    def print_current_stats(self):
        stats = self.cycle_stats
        print(f"\nCURRENT STATISTICS:")
        print(f"   Total Cycles: {stats['total_cycles']}")
        print(f"   Successful: {stats['successful_cycles']}")
        print(f"   Failed: {stats['failed_cycles']}")
        print(f"   Net Profit: ${stats['net_profit']:.4f}")
        if stats['total_cycles'] > 0:
            win_rate = (stats['successful_cycles'] / stats['total_cycles']) * 100
            print(f"   Win Rate: {win_rate:.1f}%")

    def print_final_summary(self):
        stats = self.cycle_stats
        duration = (stats['end_time'] - stats['start_time']).total_seconds()
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60

        print("\n" + "="*70)
        print("FINAL SUMMARY - 100 CYCLES COMPLETE")
        print("="*70)
        print(f"Start Time: {stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"End Time:   {stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"Duration:   {int(hours)}h {int(minutes)}m {int(seconds)}s")
        print("-"*70)
        print(f"Total Cycles:       {stats['total_cycles']}")
        print(f"Successful Cycles:  {stats['successful_cycles']}")
        print(f"Failed Cycles:      {stats['failed_cycles']}")
        if stats['total_cycles'] > 0:
            win_rate = (stats['successful_cycles'] / stats['total_cycles']) * 100
            print(f"Win Rate:           {win_rate:.1f}%")
        print("-"*70)
        print(f"Total Profit:       ${stats['total_profit']:.4f}")
        print(f"Total Loss:         ${stats['total_loss']:.4f}")
        print(f"Net Profit:         ${stats['net_profit']:.4f}")

        if stats['total_cycles'] > 0:
            avg_profit = stats['net_profit'] / stats['total_cycles']
            print(f"Avg Profit/Cycle:   ${avg_profit:.4f}")

        print("\nCOUNTRY PERFORMANCE:")
        print("-"*70)
        sorted_countries = sorted(self.country_performance.items(), key=lambda x: x[1]["total_profit"], reverse=True)
        for iso, data in sorted_countries[:10]:
            win_rate_country = (data["wins"] / data["trades"]) * 100 if data["trades"] > 0 else 0
            print(f"   {data['flag']} {data['name']}: {data['trades']} trades, ${data['total_profit']:.4f}, {win_rate_country:.1f}% win rate")

        if stats['cycle_results']:
            sorted_results = sorted(stats['cycle_results'], key=lambda x: x.get('profit', 0))

            print("\nTOP 5 BEST TRADES:")
            for i, result in enumerate(sorted_results[-5:][::-1], 1):
                print(f"   {i}. {result.get('country_flag', '')} {result.get('country_name', 'Unknown')}: ${result.get('profit', 0):.4f} ({result.get('profit_percent', 0):.2f}%)")

            print("\nTOP 5 WORST TRADES:")
            for i, result in enumerate(sorted_results[:5], 1):
                print(f"   {i}. {result.get('country_flag', '')} {result.get('country_name', 'Unknown')}: ${result.get('profit', 0):.4f} ({result.get('profit_percent', 0):.2f}%)")

        print("="*70)

    def export_results_to_csv(self):
        if not self.cycle_stats["cycle_results"]:
            return

        filename = f"crisis_scalper_results_{datetime.now().strftime('%Y%m%d')}.csv"
        file_exists = os.path.isfile(filename)

        with open(filename, 'a', newline='') as csvfile:
            fieldnames = ['cycle', 'timestamp', 'country', 'country_name', 'fsi_score',
                         'wst_class', 'entry_price', 'exit_price', 'quantity',
                         'profit', 'profit_percent', 'stopped_out', 'success']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            latest = self.cycle_stats["cycle_results"][-1]
            writer.writerow({
                'cycle': latest['cycle'],
                'timestamp': latest['timestamp'],
                'country': latest['country'],
                'country_name': latest['country_name'],
                'fsi_score': latest['fsi_score'],
                'wst_class': latest['wst_class'],
                'entry_price': f"{latest['entry_price']:.2f}",
                'exit_price': f"{latest['exit_price']:.2f}",
                'quantity': f"{latest['quantity']:.6f}",
                'profit': f"{latest['profit']:.4f}",
                'profit_percent': f"{latest['profit_percent']:.2f}",
                'stopped_out': latest.get('stopped_out', False),
                'success': latest['success']
            })

    def export_final_report(self):
        report = {
            "summary": self.cycle_stats,
            "country_performance": self.country_performance,
            "top_trades": sorted(self.cycle_stats["cycle_results"], key=lambda x: x.get('profit', 0), reverse=True)[:10],
            "worst_trades": sorted(self.cycle_stats["cycle_results"], key=lambda x: x.get('profit', 0))[:10]
        }

        filename = f"crisis_scalper_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        print(f"\nDetailed report exported to: {filename}")

# ========================================================================
# MAIN EXECUTION
# ========================================================================

if __name__ == "__main__":
    # YOUR API KEYS (as requested, left in place for you to remove later)
    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"

    bot = ScalperBotV40(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol="BTCUSDT",
        test_mode=False,          # set True to go back to paper trading
        exchange_region="us",     # "us" -> api.binance.us, "global" -> api.binance.com
    )

    bot.run_scanner()
    bot.run_100_cycles(delay_between_cycles=3)
