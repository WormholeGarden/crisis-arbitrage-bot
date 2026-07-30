#!/usr/bin/env python3
"""
🚀 CRISIS ARBITRAGE SCALPER v4.2 - $50 BALANCE OPTIMIZED - FINAL
- Increased max drawdown to 40% for small accounts
- Better position sizing for volatility
- Fixed quantity formatting (no scientific notation)
- Optimized for small account ($50 USDT)
"""

import hashlib
import hmac
import os
import random
import time
import urllib.parse
import csv
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
import requests
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

# ========================================================================
# 📊 FSI 2024 DATA (179 COUNTRIES)
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
    """Format quantity without scientific notation"""
    return f"{Decimal(str(value)):.8f}".rstrip('0').rstrip('.')

def format_price(value: float) -> str:
    return f"{Decimal(str(value)):.2f}"

# ========================================================================
# 🧠 CRISIS SCORING ENGINE
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
# 🤖 SCALPER BOT - FULLY FIXED WITH BETTER DRAWDOWN MANAGEMENT
# ========================================================================

class ScalperBotV40:

    def __init__(self, api_key: str, api_secret: str, symbol: str = "BTCUSDT",
                 test_mode: bool = True, exchange_region: str = "us",
                 log_level: str = "INFO"):
        """
        exchange_region: "us" -> api.binance.us, "global" -> api.binance.com
        Optimized for $50 USDT balance
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.test_mode = test_mode

        # Setup logging
        log_filename = f"crisis_scalper_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            filename=log_filename,
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
        # Also log to console
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(levelname)s - %(message)s')
        console.setFormatter(formatter)
        self.logger.addHandler(console)

        if exchange_region.lower() == "us":
            self.base_url = "https://api.binance.us"
        elif exchange_region.lower() == "global":
            self.base_url = "https://api.binance.com"
        else:
            raise ValueError('exchange_region must be "us" or "global"')

        # 💰 OPTIMIZED FOR $50 BALANCE - MORE FORGIVING DRAWDOWN
        self.total_balance_usdt = 50.0
        self.max_risk_per_trade = 0.10  # Reduced from 15% to 10%
        self.trade_amount_usdt = 5.00   # Reduced from $7.50
        
        # Conservative risk parameters for small account
        self.target_profit_pct = 0.005  # 0.5% (lower target for small account)
        self.stop_loss_pct = 0.004      # 0.4% stop loss (tighter)
        self.max_drawdown_pct = 0.40    # Increased to 40% for small accounts
        
        self.max_chase_attempts = 5
        self.chase_timeout_sec = 300
        self.stop_loss_poll_sec = 3
        self.maker_fee_rate = 0.001
        
        # Price cache
        self._price_cache = {}
        self._price_cache_time = 0
        self._price_cache_ttl = 2

        # Exchange info cache
        self._min_qty = 0.00001
        self._tick_size = 0.01

        # Internal state
        self.active_order_id = None
        self.buy_price = None
        self.buy_qty = None
        self.crisis_engine = CrisisScoringEngine()
        
        # Track running P&L
        self.running_pnl = 0.0
        self.peak_balance = self.total_balance_usdt
        self.current_balance = self.total_balance_usdt
        self.consecutive_losses = 0
        self.max_consecutive_losses = 5  # Stop if 5 losses in a row

        # Statistics tracking
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

        self.logger.info(f"🚀 CRISIS ARBITRAGE SCALPER v4.2 - $50 BALANCE")
        self.logger.info(f"   Symbol: {symbol}")
        self.logger.info(f"   Exchange: {self.base_url}")
        self.logger.info(f"   Mode: {'🧪 PAPER TRADING' if test_mode else '💰 LIVE TRADING'}")
        self.logger.info(f"   Total Balance: ${self.total_balance_usdt:.2f}")
        self.logger.info(f"   Trade Amount: ${self.trade_amount_usdt:.2f} ({self.max_risk_per_trade*100:.0f}% of balance)")
        self.logger.info(f"   Target Profit: {self.target_profit_pct*100:.1f}% per cycle")
        self.logger.info(f"   Stop Loss: {self.stop_loss_pct*100:.1f}%")
        self.logger.info(f"   Max Drawdown: {self.max_drawdown_pct*100:.0f}%")
        self.logger.info(f"   Max Consecutive Losses: {self.max_consecutive_losses}")
        self.logger.info("="*60)

        if not test_mode:
            self._check_connectivity()
            self._get_exchange_info()
            self._update_balance()

    def _update_balance(self):
        """Update current balance from exchange"""
        if self.test_mode:
            return
        
        balances = self.get_account_balance()
        if "USDT" in balances:
            self.current_balance = balances["USDT"]
            self.total_balance_usdt = self.current_balance
            self.trade_amount_usdt = min(
                self.current_balance * self.max_risk_per_trade,
                self.trade_amount_usdt
            )
            # Ensure minimum trade amount
            if self.trade_amount_usdt < 2.0:
                self.trade_amount_usdt = 2.0
            self.logger.info(f"💰 Current Balance: ${self.current_balance:.2f}")
            self.logger.info(f"💰 Trade Amount: ${self.trade_amount_usdt:.2f}")

    def _check_connectivity(self):
        """Fail loudly at startup"""
        self.logger.info("🔍 Running startup connectivity check...")
        ticker = self.get_order_book_ticker()
        if not ticker:
            self.logger.error("❌ STARTUP CHECK FAILED: could not fetch a ticker")
            raise SystemExit("Aborting: fix connectivity before running live cycles.")
        self.logger.info(f"✅ Connectivity OK. {self.symbol} bid={ticker['bid']} ask={ticker['ask']}")

    def _get_exchange_info(self):
        """Get exchange info for symbol validation"""
        if self.test_mode:
            return
        
        try:
            resp = requests.get(f"{self.base_url}/api/v3/exchangeInfo", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for symbol_info in data.get("symbols", []):
                    if symbol_info["symbol"] == self.symbol:
                        for filter_data in symbol_info.get("filters", []):
                            if filter_data["filterType"] == "LOT_SIZE":
                                self._min_qty = float(filter_data.get("minQty", 0.00001))
                            if filter_data["filterType"] == "PRICE_FILTER":
                                self._tick_size = float(filter_data.get("tickSize", 0.01))
                        self.logger.info(f"✅ Exchange info loaded: min_qty={self._min_qty}, tick_size={self._tick_size}")
                        break
        except Exception as e:
            self.logger.warning(f"Could not fetch exchange info: {e}")

    def _generate_signature(self, params: dict) -> str:
        query_string = urllib.parse.urlencode(params)
        return hmac.new(
            self.api_secret.encode("utf-8"),
            query_string.encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

    def _send_signed_request(self, method: str, endpoint: str, params: dict = None, retries: int = 3) -> dict:
        if params is None:
            params = {}
        
        # Format quantities properly before sending
        if "quantity" in params:
            params["quantity"] = format_quantity(float(params["quantity"]))
        if "price" in params:
            params["price"] = format_price(float(params["price"]))
        
        for attempt in range(retries):
            try:
                params["timestamp"] = int(time.time() * 1000)
                params["signature"] = self._generate_signature(params)

                headers = {"X-MBX-APIKEY": self.api_key}
                url = f"{self.base_url}{endpoint}"

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
                    self.logger.error(f"Failed to decode JSON (status {response.status_code}): {response.text[:300]}")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return {"error": "Invalid JSON response", "status_code": response.status_code}

                if isinstance(data, dict) and "code" in data and "msg" in data:
                    error_code = data.get("code")
                    if error_code in [-1003, -1001, -1016]:
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Rate limit hit (code {error_code}), waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    self.logger.error(f"Binance API error {error_code}: {data.get('msg')}")
                    return {"error": data.get("msg"), "code": error_code}

                return data
                
            except requests.exceptions.RequestException as e:
                self.logger.error(f"Network error (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {"error": str(e)}
            except Exception as e:
                self.logger.error(f"API Error (attempt {attempt+1}/{retries}): {e}")
                if attempt < retries - 1:
                    time.sleep(2 ** attempt)
                    continue
                return {"error": str(e)}
        
        return {"error": "Max retries exceeded"}

    def get_order_book_ticker(self) -> Optional[dict]:
        now = time.time()
        if now - self._price_cache_time < self._price_cache_ttl:
            if 'ticker' in self._price_cache:
                return self._price_cache['ticker']
        
        url = f"{self.base_url}/api/v3/ticker/bookTicker"
        try:
            resp = requests.get(url, params={"symbol": self.symbol}, timeout=5)
            if resp.status_code != 200:
                self.logger.error(f"Ticker request failed (status {resp.status_code}): {resp.text[:300]}")
                return None
            
            data = resp.json()
            if "bidPrice" in data and "askPrice" in data:
                ticker_data = {
                    "bid": float(data["bidPrice"]),
                    "ask": float(data["askPrice"]),
                }
                self._price_cache = {'ticker': ticker_data, 'time': now}
                self._price_cache_time = now
                return ticker_data
            
            self.logger.error(f"Unexpected ticker response: {data}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching ticker: {e}")
            return None

    def get_current_price(self) -> Optional[float]:
        now = time.time()
        if now - self._price_cache_time < self._price_cache_ttl:
            if 'mid' in self._price_cache:
                return self._price_cache['mid']
        
        ticker = self.get_order_book_ticker()
        if not ticker:
            return None
        
        mid = (ticker["bid"] + ticker["ask"]) / 2
        self._price_cache['mid'] = mid
        self._price_cache_time = now
        return mid

    def get_account_balance(self) -> Dict[str, float]:
        if self.test_mode:
            return {"USDT": self.total_balance_usdt, "BTC": 0.0}
        
        resp = self._send_signed_request("GET", "/api/v3/account")
        if "balances" in resp and not resp.get("error"):
            balances = {}
            for balance in resp["balances"]:
                if float(balance["free"]) > 0 or float(balance["locked"]) > 0:
                    balances[balance["asset"]] = float(balance["free"])
            return balances
        return {"USDT": 0.0}

    def place_maker_limit_order(self, side: str, amount: float, target_price: float = None, is_quantity: bool = False) -> dict:
        """Place a LIMIT_MAKER order with proper quantity formatting"""
        if self.test_mode:
            simulated_id = f"SIM_{int(time.time() * 1000)}"
            price = target_price or (64000.0 + random.uniform(-500, 500))
            qty = amount if is_quantity else amount / price
            if qty < self._min_qty:
                qty = self._min_qty
            self.logger.info(f"[TEST MODE] {side} LIMIT_MAKER @ ${price:.2f} | Qty: {qty:.8f}")
            return {
                "orderId": simulated_id,
                "price": str(price),
                "origQty": str(qty),
                "executedQty": str(qty),
                "status": "NEW",
                "side": side,
            }

        ticker = self.get_order_book_ticker()
        if not ticker:
            return {"error": "Failed to get market price"}

        # Check balance
        if side.upper() == "BUY":
            balances = self.get_account_balance()
            if balances.get("USDT", 0) < amount:
                self.logger.warning(f"Insufficient balance: {balances.get('USDT', 0)} USDT < {amount}")
                return {"error": "Insufficient balance"}

        if side.upper() == "BUY":
            limit_price = target_price if target_price else ticker["bid"] * 0.9995
        else:
            limit_price = target_price if target_price else ticker["ask"] * 1.0005

        limit_price = round_to_tick(limit_price, self._tick_size)

        if is_quantity:
            qty = round_to_step(amount, self._min_qty)
        else:
            qty = round_to_step(amount / limit_price, self._min_qty)

        if qty < self._min_qty:
            qty = self._min_qty
            self.logger.info(f"Quantity adjusted to minimum: {qty:.8f}")

        # Format quantity without scientific notation
        qty_str = format_quantity(qty)
        price_str = format_price(limit_price)

        self.logger.info(f"Placing {side} order: {qty_str} @ ${price_str}")

        params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "LIMIT_MAKER",
            "quantity": qty_str,
            "price": price_str,
        }

        response = self._send_signed_request("POST", "/api/v3/order", params)
        
        if "error" in response:
            return response
        
        return {
            "orderId": response.get("orderId", f"ERR_{int(time.time())}"),
            "price": str(response.get("price", limit_price)),
            "origQty": str(response.get("origQty", qty)),
            "executedQty": str(response.get("executedQty", "0")),
            "status": response.get("status", "NEW"),
            "side": side,
        }

    def place_market_order(self, side: str, quantity: float) -> dict:
        if self.test_mode:
            simulated_id = f"SIM_MKT_{int(time.time() * 1000)}"
            price = 64000.0 + random.uniform(-500, 500)
            self.logger.info(f"[TEST MODE] {side} MARKET | Qty: {quantity:.8f} @ ~${price:.2f}")
            return {
                "orderId": simulated_id,
                "price": str(price),
                "executedQty": str(quantity),
                "status": "FILLED",
                "side": side,
            }

        qty = round_to_step(quantity, self._min_qty)
        if qty < self._min_qty:
            qty = self._min_qty

        qty_str = format_quantity(qty)

        params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": qty_str,
        }
        response = self._send_signed_request("POST", "/api/v3/order", params)
        
        if "error" in response:
            return response
        
        return {
            "orderId": response.get("orderId", f"ERR_{int(time.time())}"),
            "price": str(response.get("price", 0)),
            "executedQty": str(response.get("executedQty", qty)),
            "status": response.get("status", "FILLED"),
            "side": side,
        }

    def cancel_order(self, order_id: str) -> dict:
        if self.test_mode:
            self.logger.info(f"[TEST MODE] Cancelled Order ID: {order_id}")
            return {"status": "CANCELED", "orderId": order_id}

        params = {"symbol": self.symbol, "orderId": order_id}
        return self._send_signed_request("DELETE", "/api/v3/order", params)

    def chase_order(self, side: str, current_qty: float, last_order_id: str) -> dict:
        self.logger.info(f"Chasing {side} order...")
        self.cancel_order(last_order_id)
        return self.place_maker_limit_order(
            side=side,
            amount=current_qty,
            target_price=None,
            is_quantity=True,
        )

    def run_cycle(self, iso: str = None, cycle_number: int = 0) -> dict:
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔄 CYCLE {cycle_number}/100")
        self.logger.info(f"{'='*60}")

        # Check balance and risk limits
        if not self.test_mode:
            self._update_balance()
            
            # Check max drawdown (now 40%)
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance if self.peak_balance > 0 else 0
            if drawdown > self.max_drawdown_pct:
                self.logger.error(f"❌ Max drawdown exceeded: {drawdown*100:.1f}% > {self.max_drawdown_pct*100:.0f}%")
                self.logger.error(f"   Current Balance: ${self.current_balance:.2f}")
                self.logger.error(f"   Peak Balance: ${self.peak_balance:.2f}")
                self.logger.error("   Stopping trading to preserve capital")
                return {"success": False, "error": "Max drawdown exceeded"}
            
            # Check for too many consecutive losses
            if self.consecutive_losses >= self.max_consecutive_losses:
                self.logger.error(f"❌ Too many consecutive losses: {self.consecutive_losses}")
                self.logger.error("   Stopping trading to prevent further losses")
                return {"success": False, "error": "Too many consecutive losses"}
            
            if self.current_balance < 5.0:
                self.logger.error("❌ Balance too low to continue trading")
                return {"success": False, "error": "Balance too low"}

        # Select country
        if iso:
            country = CrisisScoringEngine.get_crisis_score(iso)
            if not country:
                self.logger.error(f"Country {iso} not found in FSI data")
                return {"success": False, "error": "Country not found"}
            opp_score = CrisisScoringEngine.score_opportunity(iso)
            self.logger.info(f"🎯 Trading: {country['flag']} {country['name']} (FSI: {country['fsi_score']}, WST: {country['wst_class']})")
            self.logger.info(f"   Opportunity Score: {opp_score:.2f}")
        else:
            top_opportunities = CrisisScoringEngine.get_top_opportunities(20)
            if not top_opportunities:
                self.logger.error("No opportunities found")
                return {"success": False, "error": "No opportunities"}
            idx = (cycle_number - 1) % len(top_opportunities)
            country = top_opportunities[idx]
            iso = country["iso"]
            self.logger.info(f"🎯 Trading: {country['flag']} {country['name']} (FSI: {country['fsi_score']}, WST: {country['wst_class']})")
            self.logger.info(f"   Opportunity Score: {country['opportunity_score']:.2f}")

        # Place Buy Order
        buy_amount = self.trade_amount_usdt * (1 + random.uniform(-0.05, 0.05))
        buy_order = self.place_maker_limit_order(
            side="BUY",
            amount=buy_amount,
            target_price=None,
            is_quantity=False,
        )

        if "error" in buy_order:
            self.logger.error(f"Failed to place buy order: {buy_order}")
            return {"success": False, "error": buy_order.get("error", "Buy order failed")}

        order_id = buy_order.get("orderId")
        if not order_id:
            self.logger.error(f"Missing orderId in response: {buy_order}")
            return {"success": False, "error": "Missing orderId"}

        self.buy_price = float(buy_order.get("price", 0))
        self.buy_qty = float(buy_order.get("origQty", 0))
        
        if self.buy_price == 0 or self.buy_qty == 0:
            self.logger.error(f"Invalid price or quantity: {buy_order}")
            return {"success": False, "error": "Invalid price or quantity"}

        self.logger.info(f"📈 BUY Order: {self.buy_qty:.8f} BTC @ ${self.buy_price:.2f}")

        # Monitor Buy Fill
        self.logger.info("⏳ Waiting for buy fill...")
        filled = False
        start_time = time.time()

        while not filled:
            if time.time() - start_time > self.chase_timeout_sec:
                chase_res = self.chase_order("BUY", self.buy_qty, order_id)
                if "error" not in chase_res and chase_res.get("orderId"):
                    order_id = chase_res["orderId"]
                    self.buy_price = float(chase_res.get("price", self.buy_price))
                start_time = time.time()

            if self.test_mode:
                time.sleep(1.0 + random.uniform(0, 1.0))
                filled = True
                self.logger.info(f"✅ [TEST] BUY Filled @ ${self.buy_price:.2f}")
            else:
                status = self._send_signed_request("GET", "/api/v3/order", {
                    "symbol": self.symbol,
                    "orderId": order_id,
                })
                if status.get("status") == "FILLED":
                    filled = True
                    self.buy_price = float(status.get("price", self.buy_price))
                    self.buy_qty = float(status.get("executedQty", self.buy_qty))
                    self.logger.info(f"✅ BUY Filled @ ${self.buy_price:.2f}")
                elif status.get("status") == "CANCELED":
                    self.logger.warning("Buy order was cancelled, retrying...")
                    chase_res = self.chase_order("BUY", self.buy_qty, order_id)
                    if "error" not in chase_res and chase_res.get("orderId"):
                        order_id = chase_res["orderId"]
                        self.buy_price = float(chase_res.get("price", self.buy_price))
                    start_time = time.time()
                time.sleep(2)

        # Calculate Exit Levels
        target_profit_pct = self.target_profit_pct * (1 + random.uniform(-0.1, 0.1))
        target_price = self.buy_price * (1 + target_profit_pct)
        stop_price = self.buy_price * (1 - self.stop_loss_pct)

        self.logger.info(f"🎯 Target: ${target_price:.2f} (+{target_profit_pct*100:.1f}%)")
        self.logger.info(f"🛑 Stop:   ${stop_price:.2f} (-{self.stop_loss_pct*100:.1f}%)")

        # Place Sell Order
        sell_order = self.place_maker_limit_order(
            side="SELL",
            amount=self.buy_qty,
            target_price=target_price,
            is_quantity=True,
        )

        if "error" in sell_order:
            self.logger.error(f"Failed to place sell order: {sell_order}")
            return {"success": False, "error": sell_order.get("error", "Sell order failed")}

        sell_order_id = sell_order.get("orderId")
        if not sell_order_id:
            self.logger.error(f"Missing orderId in sell response: {sell_order}")
            return {"success": False, "error": "Missing sell orderId"}

        self.logger.info(f"📉 SELL Order placed @ ${target_price:.2f}")

        # Monitor for target fill OR stop-loss
        sell_filled = False
        sell_start = time.time()
        exit_price = target_price
        stopped_out = False
        last_stop_check = 0.0

        while not sell_filled:
            now = time.time()

            if now - sell_start > self.chase_timeout_sec:
                chase_res = self.chase_order("SELL", self.buy_qty, sell_order_id)
                if "error" not in chase_res and chase_res.get("orderId"):
                    sell_order_id = chase_res["orderId"]
                sell_start = time.time()

            if self.test_mode:
                time.sleep(1.0 + random.uniform(0, 1.0))
                sim_price = self.buy_price * (1 + random.uniform(-0.015, 0.015))
                if sim_price <= stop_price:
                    exit_price = stop_price
                    stopped_out = True
                    self.logger.info(f"🛑 [TEST] STOP-LOSS hit @ ${exit_price:.2f}")
                elif sim_price >= target_price:
                    exit_price = target_price
                    self.logger.info(f"✅ [TEST] SELL Filled @ ${target_price:.2f}")
                else:
                    self.logger.info(f"[TEST] Price moved to ${sim_price:.2f}, waiting...")
                    time.sleep(1)
                    continue
                sell_filled = True
            else:
                status = self._send_signed_request("GET", "/api/v3/order", {
                    "symbol": self.symbol,
                    "orderId": sell_order_id,
                })
                
                if status.get("status") == "FILLED":
                    sell_filled = True
                    exit_price = float(status.get("price", target_price))
                    self.logger.info(f"✅ SELL Filled @ ${exit_price:.2f}")
                    break

                if now - last_stop_check > self.stop_loss_poll_sec:
                    last_stop_check = now
                    current_price = self.get_current_price()
                    if current_price is not None and current_price <= stop_price:
                        self.logger.warning(f"🛑 STOP-LOSS breached: current ${current_price:.2f} <= stop ${stop_price:.2f}")
                        self.cancel_order(sell_order_id)
                        exit_res = self.place_market_order("SELL", self.buy_qty)
                        if "error" in exit_res:
                            self.logger.error(f"Stop-loss exit failed: {exit_res}")
                            time.sleep(2)
                            continue
                        sell_filled = True
                        stopped_out = True
                        exit_price = float(exit_res.get("price", current_price))
                        self.logger.info(f"🛑 Stopped out @ ${exit_price:.2f}")
                        break

                time.sleep(2)

        # Calculate P&L
        realized_pnl = (exit_price - self.buy_price) * self.buy_qty
        self.logger.info(f"💰 P&L: ${realized_pnl:.4f}" + (" (stop-loss exit)" if stopped_out else ""))
        
        # Update balance and track consecutive losses
        self.running_pnl += realized_pnl
        self.current_balance = self.total_balance_usdt + self.running_pnl
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
            self.consecutive_losses = 0  # Reset on new peak
        elif realized_pnl < 0:
            self.consecutive_losses += 1
        else:
            self.consecutive_losses = 0  # Reset on win
        
        self.logger.info(f"💰 Current Balance: ${self.current_balance:.2f}")
        self.logger.info(f"📊 Consecutive Losses: {self.consecutive_losses}")
        self.logger.info("=== Cycle Complete ===")

        # Update country performance
        if iso not in self.country_performance:
            self.country_performance[iso] = {
                "name": country["name"],
                "flag": country["flag"],
                "trades": 0,
                "total_profit": 0,
                "wins": 0,
                "losses": 0,
                "stopped_out": 0
            }

        self.country_performance[iso]["trades"] += 1
        self.country_performance[iso]["total_profit"] += realized_pnl
        if realized_pnl > 0:
            self.country_performance[iso]["wins"] += 1
        else:
            self.country_performance[iso]["losses"] += 1
        if stopped_out:
            self.country_performance[iso]["stopped_out"] += 1

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
            "balance_after": self.current_balance,
            "consecutive_losses": self.consecutive_losses,
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
        self.logger.info("\n🎯 TOP CRISIS OPPORTUNITIES")
        self.logger.info("="*60)
        top = CrisisScoringEngine.get_top_opportunities(10)
        for i, opp in enumerate(top, 1):
            self.logger.info(f"{i}. {opp['flag']} {opp['name']}")
            self.logger.info(f"   FSI: {opp['fsi_score']:.1f} | WST: {opp['wst_class']} | Recovery: {opp['recovery_rate']*100:.0f}%")
            self.logger.info(f"   Opportunity Score: {opp['opportunity_score']:.2f}")

    def run_100_cycles(self, delay_between_cycles: int = 5):
        self.logger.info("\n" + "="*60)
        self.logger.info("🚀 STARTING 100 CYCLES EXECUTION")
        self.logger.info("="*60)

        self.cycle_stats["start_time"] = datetime.now()
        top_countries = CrisisScoringEngine.get_top_opportunities(30)

        for cycle_num in range(1, 101):
            try:
                # Check if we should continue
                if not self.test_mode:
                    if self.cycle_stats.get("failed_cycles", 0) > 50:
                        self.logger.error("❌ Too many failed cycles, stopping")
                        break
                    
                    if self.current_balance < 5.0:
                        self.logger.error("❌ Balance critically low, stopping")
                        break

                country_idx = (cycle_num - 1) % len(top_countries)
                selected_country = top_countries[country_idx]["iso"]

                self.logger.info(f"\n📊 Cycle {cycle_num}/100 - Trading {top_countries[country_idx]['flag']} {top_countries[country_idx]['name']}")

                result = self.run_cycle(iso=selected_country, cycle_number=cycle_num)

                if not result.get("success", False):
                    self.logger.error(f"⚠️ Cycle {cycle_num} failed: {result.get('error', 'Unknown error')}")
                else:
                    self.logger.info(f"✅ Cycle {cycle_num} completed successfully!")
                    self.logger.info(f"   Profit: ${result.get('profit', 0):.4f} ({result.get('profit_percent', 0):.2f}%)")

                self.print_current_stats()
                self.export_results_to_csv()

                if cycle_num < 100:
                    wait_time = delay_between_cycles + random.uniform(0, 2)
                    self.logger.info(f"\n⏳ Waiting {wait_time:.1f} seconds before next cycle...")
                    time.sleep(wait_time)

            except KeyboardInterrupt:
                self.logger.info("\n⚠️ Execution interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in cycle {cycle_num}: {e}")
                if cycle_num < 100:
                    wait_time = delay_between_cycles * 2
                    self.logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)

        self.cycle_stats["end_time"] = datetime.now()
        self.print_final_summary()
        self.export_final_report()

    def print_current_stats(self):
        stats = self.cycle_stats
        self.logger.info(f"\n📊 CURRENT STATISTICS:")
        self.logger.info(f"   Total Cycles: {stats['total_cycles']}")
        self.logger.info(f"   Successful: {stats['successful_cycles']}")
        self.logger.info(f"   Failed: {stats['failed_cycles']}")
        self.logger.info(f"   Net Profit: ${stats['net_profit']:.4f}")
        self.logger.info(f"   Current Balance: ${self.current_balance:.2f}")
        self.logger.info(f"   Consecutive Losses: {self.consecutive_losses}")
        if stats['total_cycles'] > 0:
            win_rate = (stats['successful_cycles'] / stats['total_cycles']) * 100
            self.logger.info(f"   Win Rate: {win_rate:.1f}%")

    def print_final_summary(self):
        stats = self.cycle_stats
        duration = (stats['end_time'] - stats['start_time']).total_seconds()
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60

        self.logger.info("\n" + "="*70)
        self.logger.info("🎯 FINAL SUMMARY - 100 CYCLES COMPLETE")
        self.logger.info("="*70)
        self.logger.info(f"📅 Start Time: {stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"📅 End Time:   {stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"⏱️  Duration:   {int(hours)}h {int(minutes)}m {int(seconds)}s")
        self.logger.info("-"*70)
        self.logger.info(f"📊 Total Cycles:       {stats['total_cycles']}")
        self.logger.info(f"✅ Successful Cycles:  {stats['successful_cycles']}")
        self.logger.info(f"❌ Failed Cycles:      {stats['failed_cycles']}")
        if stats['total_cycles'] > 0:
            win_rate = (stats['successful_cycles'] / stats['total_cycles']) * 100
            self.logger.info(f"🏆 Win Rate:           {win_rate:.1f}%")
        self.logger.info("-"*70)
        self.logger.info(f"💰 Starting Balance:   ${self.total_balance_usdt:.2f}")
        self.logger.info(f"💰 Final Balance:      ${self.current_balance:.2f}")
        self.logger.info(f"📈 Total Profit:       ${stats['net_profit']:.4f}")
        
        if stats['total_cycles'] > 0:
            avg_profit = stats['net_profit'] / stats['total_cycles']
            self.logger.info(f"📊 Avg Profit/Cycle:   ${avg_profit:.4f}")
            roi = (stats['net_profit'] / self.total_balance_usdt) * 100
            self.logger.info(f"📊 ROI:                {roi:.1f}%")
        
        self.logger.info(f"📊 Max Drawdown:       {(self.peak_balance - self.current_balance) / self.peak_balance * 100:.1f}%")
        self.logger.info(f"📊 Consecutive Losses: {self.consecutive_losses}")

        self.logger.info("\n🌍 COUNTRY PERFORMANCE:")
        self.logger.info("-"*70)
        sorted_countries = sorted(self.country_performance.items(), key=lambda x: x[1]["total_profit"], reverse=True)
        for iso, data in sorted_countries[:10]:
            win_rate_country = (data["wins"] / data["trades"]) * 100 if data["trades"] > 0 else 0
            stop_rate = (data.get("stopped_out", 0) / data["trades"]) * 100 if data["trades"] > 0 else 0
            self.logger.info(f"   {data['flag']} {data['name']}: {data['trades']} trades, ${data['total_profit']:.4f}, {win_rate_country:.1f}% win, {stop_rate:.1f}% stopped")

        self.logger.info("="*70)

    def export_results_to_csv(self):
        if not self.cycle_stats["cycle_results"]:
            return

        filename = f"crisis_scalper_results_{datetime.now().strftime('%Y%m%d')}.csv"
        file_exists = os.path.isfile(filename)

        with open(filename, 'a', newline='') as csvfile:
            fieldnames = ['cycle', 'timestamp', 'country', 'country_name', 'fsi_score',
                         'wst_class', 'entry_price', 'exit_price', 'quantity',
                         'profit', 'profit_percent', 'stopped_out', 'balance_after', 
                         'consecutive_losses', 'success']
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
                'quantity': f"{latest['quantity']:.8f}",
                'profit': f"{latest['profit']:.4f}",
                'profit_percent': f"{latest['profit_percent']:.2f}",
                'stopped_out': latest.get('stopped_out', False),
                'balance_after': f"{latest.get('balance_after', 0):.2f}",
                'consecutive_losses': latest.get('consecutive_losses', 0),
                'success': latest['success']
            })

    def export_final_report(self):
        report = {
            "starting_balance": self.total_balance_usdt,
            "final_balance": self.current_balance,
            "peak_balance": self.peak_balance,
            "max_drawdown_percent": ((self.peak_balance - self.current_balance) / self.peak_balance * 100) if self.peak_balance > 0 else 0,
            "consecutive_losses": self.consecutive_losses,
            "roi_percent": ((self.current_balance - self.total_balance_usdt) / self.total_balance_usdt) * 100,
            "summary": self.cycle_stats,
            "country_performance": self.country_performance,
            "top_trades": sorted(self.cycle_stats["cycle_results"], key=lambda x: x.get('profit', 0), reverse=True)[:10],
            "worst_trades": sorted(self.cycle_stats["cycle_results"], key=lambda x: x.get('profit', 0))[:10]
        }

        filename = f"crisis_scalper_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"\n📄 Detailed report exported to: {filename}")

# ========================================================================
# 🚀 MAIN EXECUTION
# ========================================================================

if __name__ == "__main__":
    # ⚠️ WARNING: Replace these with your own API keys!
    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"

    bot = ScalperBotV40(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol="BTCUSDT",
        test_mode=False,
        exchange_region="us",
        log_level="INFO"
    )

    bot.run_scanner()
    bot.run_100_cycles(delay_between_cycles=5)
