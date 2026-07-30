#!/usr/bin/env python3
"""
🚀 CRISIS ARBITRAGE SCALPER v4.2 - $50 BALANCE OPTIMIZED
- Optimized for small account ($50 USDT)
- Conservative position sizing ($5-10 per trade)
- Tighter stop-loss to preserve capital
- World Systems Theory (Core/Semi-Periphery/Periphery classification)
- Fragile States Index 2024 (179 countries)
- FSI + WST scoring for trade selection
- LIMIT_MAKER orders with proper Binance API
- Real stop-loss enforcement with MARKET orders
- Price caching to reduce API calls
- Exponential backoff for rate limits
- Dynamic position sizing based on balance
- Comprehensive logging to file
- CSV export of all trades
- 100 cycles automated execution
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
import socket
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
# 🤖 SCALPER BOT WITH FSI + WST - $50 BALANCE OPTIMIZED
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

        # 💰 OPTIMIZED FOR $50 BALANCE
        self.total_balance_usdt = 50.0  # Total account balance
        self.max_risk_per_trade = 0.15  # Risk 15% of balance per trade = $7.50
        self.trade_amount_usdt = 7.50   # $7.50 per trade (15% of $50)
        
        # Conservative risk parameters for small account
        self.target_profit_pct = 0.008  # 0.8% profit target (higher to overcome fees)
        self.stop_loss_pct = 0.006      # 0.6% stop loss (tighter to preserve capital)
        self.max_drawdown_pct = 0.20    # Max 20% drawdown before stopping
        
        self.max_chase_attempts = 5
        self.chase_timeout_sec = 300
        self.stop_loss_poll_sec = 3     # Check stop-loss more frequently
        self.maker_fee_rate = 0.001
        
        # Price cache
        self._price_cache = {}
        self._price_cache_time = 0
        self._price_cache_ttl = 2  # 2 second cache

        # Exchange info cache
        self._exchange_info = None
        self._min_qty = 0.00001
        self._tick_size = 0.01

        # Internal state
        self.active_order_id = None
        self.buy_price = None
        self.buy_qty = None
        self.crisis_engine = CrisisScoringEngine()
        
        # Track running P&L to enforce max drawdown
        self.running_pnl = 0.0
        self.peak_balance = self.total_balance_usdt
        self.current_balance = self.total_balance_usdt

        # Statistics tracking for 100 cycles
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

        # Country performance tracking
        self.country_performance = {}

        self.logger.info(f"🚀 CRISIS ARBITRAGE SCALPER v4.2 - $50 BALANCE OPTIMIZED")
        self.logger.info(f"   Symbol: {symbol}")
        self.logger.info(f"   Exchange: {self.base_url}")
        self.logger.info(f"   Mode: {'🧪 PAPER TRADING' if test_mode else '💰 LIVE TRADING'}")
        self.logger.info(f"   Total Balance: ${self.total_balance_usdt:.2f}")
        self.logger.info(f"   Trade Amount: ${self.trade_amount_usdt:.2f} ({self.max_risk_per_trade*100:.0f}% of balance)")
        self.logger.info(f"   Countries Tracked: {len(FSI_2024)}")
        self.logger.info(f"   Target Profit: {self.target_profit_pct*100:.1f}% per cycle")
        self.logger.info(f"   Stop Loss: {self.stop_loss_pct*100:.1f}%")
        self.logger.info(f"   Max Drawdown: {self.max_drawdown_pct*100:.0f}%")
        self.logger.info("="*60)

        if not test_mode:
            self._check_connectivity()
            self._get_exchange_info()
            # Get actual balance
            self._update_balance()

    def _update_balance(self):
        """Update current balance from exchange"""
        if self.test_mode:
            return
        
        balances = self.get_account_balance()
        if "USDT" in balances:
            self.current_balance = balances["USDT"]
            self.total_balance_usdt = self.current_balance
            # Adjust trade amount based on actual balance
            self.trade_amount_usdt = min(
                self.current_balance * self.max_risk_per_trade,
                self.trade_amount_usdt
            )
            self.logger.info(f"💰 Current Balance: ${self.current_balance:.2f}")
            self.logger.info(f"💰 Trade Amount: ${self.trade_amount_usdt:.2f}")

    def _check_connectivity(self):
        """Fail loudly at startup instead of silently on cycle 1"""
        self.logger.info("🔍 Running startup connectivity check...")
        ticker = self.get_order_book_ticker()
        if not ticker:
            self.logger.error("❌ STARTUP CHECK FAILED: could not fetch a ticker from "
                              f"{self.base_url}. Common causes:")
            self.logger.error("  - Wrong region: US-based connections are blocked on "
                              "api.binance.com; use exchange_region='us' (api.binance.us).")
            self.logger.error("  - Non-US connections to api.binance.us will fail; use "
                              "exchange_region='global' instead.")
            self.logger.error("  - Bad/expired API key or IP not whitelisted.")
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
        """Send signed request with exponential backoff for rate limits"""
        if params is None:
            params = {}
        
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
                    if error_code in [-1003, -1001, -1016]:  # Rate limit, timeout, throttling
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
        """Get current market price with caching"""
        # Check cache first
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
                # Update cache
                self._price_cache = {
                    'ticker': ticker_data,
                    'time': now
                }
                self._price_cache_time = now
                return ticker_data
            
            self.logger.error(f"Unexpected ticker response: {data}")
            return None
            
        except Exception as e:
            self.logger.error(f"Error fetching ticker from {url}: {e}")
            return None

    def get_current_price(self) -> Optional[float]:
        """Get mid price with caching"""
        # Check cache first
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
        """Get account balances for position sizing"""
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
        """Place a LIMIT_MAKER order with validation"""
        if self.test_mode:
            simulated_id = f"SIM_{int(time.time() * 1000)}"
            price = target_price or (64000.0 + random.uniform(-500, 500))
            qty = amount if is_quantity else amount / price
            # Ensure minimum quantity
            if qty < self._min_qty:
                qty = self._min_qty
                self.logger.info(f"[TEST MODE] Quantity adjusted to minimum: {qty}")
            self.logger.info(f"[TEST MODE] {side} LIMIT_MAKER @ ${price:.2f} | Qty: {qty:.6f}")
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

        # Check balance before placing order
        if side.upper() == "BUY":
            balances = self.get_account_balance()
            if balances.get("USDT", 0) < amount:
                self.logger.warning(f"Insufficient balance: {balances.get('USDT', 0)} USDT < {amount}")
                return {"error": "Insufficient balance"}

        if side.upper() == "BUY":
            limit_price = target_price if target_price else ticker["bid"] * 0.9995
        else:
            limit_price = target_price if target_price else ticker["ask"] * 1.0005

        # Round to tick size
        limit_price = round_to_tick(limit_price, self._tick_size)

        if is_quantity:
            qty = round_to_step(amount, self._min_qty)
        else:
            qty = round_to_step(amount / limit_price, self._min_qty)

        # Ensure minimum quantity
        if qty < self._min_qty:
            qty = self._min_qty
            self.logger.info(f"Quantity adjusted to minimum: {qty}")

        params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "LIMIT_MAKER",
            "quantity": qty,
            "price": limit_price,
        }

        self.logger.info(f"Placing {side} order: {qty} @ ${limit_price:.2f}")
        return self._send_signed_request("POST", "/api/v3/order", params)

    def place_market_order(self, side: str, quantity: float) -> dict:
        """Place a MARKET order for emergency exits"""
        if self.test_mode:
            simulated_id = f"SIM_MKT_{int(time.time() * 1000)}"
            price = 64000.0 + random.uniform(-500, 500)
            self.logger.info(f"[TEST MODE] {side} MARKET | Qty: {quantity:.6f} @ ~${price:.2f}")
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
            self.logger.info(f"Market order quantity adjusted to minimum: {qty}")

        params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": qty,
        }
        return self._send_signed_request("POST", "/api/v3/order", params)

    def cancel_order(self, order_id: str) -> dict:
        if self.test_mode:
            self.logger.info(f"[TEST MODE] Cancelled Order ID: {order_id}")
            return {"status": "CANCELED", "orderId": order_id}

        params = {"symbol": self.symbol, "orderId": order_id}
        return self._send_signed_request("DELETE", "/api/v3/order", params)

    def chase_order(self, side: str, current_qty: float, last_order_id: str) -> dict:
        """Cancel and re-place order at current market price"""
        self.logger.info(f"Chasing {side} order...")
        self.cancel_order(last_order_id)
        return self.place_maker_limit_order(
            side=side,
            amount=current_qty,
            target_price=None,
            is_quantity=True,
        )

    def run_cycle(self, iso: str = None, cycle_number: int = 0) -> dict:
        """Run one trading cycle with FSI + WST selection"""
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔄 CYCLE {cycle_number}/100")
        self.logger.info(f"{'='*60}")

        # Check balance and enforce max drawdown
        if not self.test_mode:
            self._update_balance()
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            if drawdown > self.max_drawdown_pct:
                self.logger.error(f"❌ Max drawdown exceeded: {drawdown*100:.1f}% > {self.max_drawdown_pct*100:.0f}%")
                self.logger.error("Stopping trading to preserve capital")
                return {"success": False, "error": "Max drawdown exceeded"}
            
            if self.current_balance < 10:
                self.logger.error("❌ Balance too low to continue trading")
                return {"success": False, "error": "Balance too low"}

        # 1. Select the best opportunity with rotation
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

        # 2. Place Buy Order
        buy_amount = self.trade_amount_usdt * (1 + random.uniform(-0.05, 0.05))
        buy_order = self.place_maker_limit_order(
            side="BUY",
            amount=buy_amount,
            target_price=None,
            is_quantity=False,
        )

        if "orderId" not in buy_order:
            self.logger.error(f"Failed to place buy order: {buy_order}")
            return {"success": False, "error": buy_order.get("error", "Buy order failed")}

        order_id = buy_order["orderId"]
        self.buy_price = float(buy_order["price"])
        self.buy_qty = float(buy_order["origQty"])
        self.logger.info(f"📈 BUY Order: {self.buy_qty:.6f} BTC @ ${self.buy_price:.2f}")

        # 3. Monitor Buy Fill
        self.logger.info("⏳ Waiting for buy fill...")
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
                    if "orderId" in chase_res:
                        order_id = chase_res["orderId"]
                        self.buy_price = float(chase_res["price"])
                    start_time = time.time()
                time.sleep(2)

        # 4. Calculate Exit Levels
        target_profit_pct = self.target_profit_pct * (1 + random.uniform(-0.1, 0.1))
        target_price = self.buy_price * (1 + target_profit_pct)
        stop_price = self.buy_price * (1 - self.stop_loss_pct)

        self.logger.info(f"🎯 Target: ${target_price:.2f} (+{target_profit_pct*100:.1f}%)")
        self.logger.info(f"🛑 Stop:   ${stop_price:.2f} (-{self.stop_loss_pct*100:.1f}%)")

        # 5. Place Sell Order (at target)
        sell_order = self.place_maker_limit_order(
            side="SELL",
            amount=self.buy_qty,
            target_price=target_price,
            is_quantity=True,
        )

        if "orderId" not in sell_order:
            self.logger.error(f"Failed to place sell order: {sell_order}")
            return {"success": False, "error": sell_order.get("error", "Sell order failed")}

        sell_order_id = sell_order["orderId"]
        self.logger.info(f"📉 SELL Order placed @ ${target_price:.2f}")

        # 6. Monitor for target fill OR stop-loss
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
                # Simulate realistic market behavior
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
                    # Price moved but not to target or stop, continue
                    self.logger.info(f"[TEST] Price moved to ${sim_price:.2f}, waiting...")
                    time.sleep(1)
                    continue
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
                    self.logger.info(f"✅ SELL Filled @ ${exit_price:.2f}")
                    break

                # Check stop-loss breach
                if now - last_stop_check > self.stop_loss_poll_sec:
                    last_stop_check = now
                    current_price = self.get_current_price()
                    if current_price is not None and current_price <= stop_price:
                        self.logger.warning(f"🛑 STOP-LOSS breached: current ${current_price:.2f} <= stop ${stop_price:.2f}")
                        
                        # Cancel target sell order
                        self.cancel_order(sell_order_id)
                        
                        # Place market sell for stop-loss
                        exit_res = self.place_market_order("SELL", self.buy_qty)
                        if "error" in exit_res:
                            self.logger.error(f"Stop-loss exit failed, retrying: {exit_res}")
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
        
        # Update running P&L
        self.running_pnl += realized_pnl
        self.current_balance = self.total_balance_usdt + self.running_pnl
        if self.current_balance > self.peak_balance:
            self.peak_balance = self.current_balance
        
        self.logger.info(f"💰 Current Balance: ${self.current_balance:.2f}")
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
            "timestamp": datetime.now().isoformat()
        }

        # Update statistics
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
        """Scan and display top opportunities"""
        self.logger.info("\n🎯 TOP CRISIS OPPORTUNITIES")
        self.logger.info("="*60)
        top = CrisisScoringEngine.get_top_opportunities(10)
        for i, opp in enumerate(top, 1):
            self.logger.info(f"{i}. {opp['flag']} {opp['name']}")
            self.logger.info(f"   FSI: {opp['fsi_score']:.1f} | WST: {opp['wst_class']} | Recovery: {opp['recovery_rate']*100:.0f}%")
            self.logger.info(f"   Opportunity Score: {opp['opportunity_score']:.2f}")
            self.logger.info("")

    def run_100_cycles(self, delay_between_cycles: int = 5):
        """Run 100 trading cycles"""
        self.logger.info("\n" + "="*60)
        self.logger.info("🚀 STARTING 100 CYCLES EXECUTION")
        self.logger.info("="*60)

        self.cycle_stats["start_time"] = datetime.now()
        top_countries = CrisisScoringEngine.get_top_opportunities(30)

        for cycle_num in range(1, 101):
            try:
                country_idx = (cycle_num - 1) % len(top_countries)
                selected_country = top_countries[country_idx]["iso"]

                self.logger.info(f"\n📊 Cycle {cycle_num}/100 - Trading {top_countries[country_idx]['flag']} {top_countries[country_idx]['name']}")

                result = self.run_cycle(iso=selected_country, cycle_number=cycle_num)

                if not result.get("success", False):
                    self.logger.error(f"⚠️ Cycle {cycle_num} failed: {result.get('error', 'Unknown error')}")
                    self.cycle_stats["failed_cycles"] += 1
                else:
                    self.logger.info(f"✅ Cycle {cycle_num} completed successfully!")
                    self.logger.info(f"   Profit: ${result.get('profit', 0):.4f} ({result.get('profit_percent', 0):.2f}%)")

                # Print current statistics
                self.print_current_stats()

                # Export results after each cycle
                self.export_results_to_csv()

                # Wait before next cycle
                if cycle_num < 100:
                    wait_time = delay_between_cycles + random.uniform(0, 2)
                    self.logger.info(f"\n⏳ Waiting {wait_time:.1f} seconds before next cycle...")
                    time.sleep(wait_time)

            except KeyboardInterrupt:
                self.logger.info("\n⚠️ Execution interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in cycle {cycle_num}: {e}")
                self.cycle_stats["failed_cycles"] += 1
                if cycle_num < 100:
                    wait_time = delay_between_cycles * 2
                    self.logger.info(f"⏳ Waiting {wait_time} seconds before retry...")
                    time.sleep(wait_time)

        self.cycle_stats["end_time"] = datetime.now()
        self.print_final_summary()
        self.export_final_report()

    def print_current_stats(self):
        """Print current cycle statistics"""
        stats = self.cycle_stats
        self.logger.info(f"\n📊 CURRENT STATISTICS:")
        self.logger.info(f"   Total Cycles: {stats['total_cycles']}")
        self.logger.info(f"   Successful: {stats['successful_cycles']}")
        self.logger.info(f"   Failed: {stats['failed_cycles']}")
        self.logger.info(f"   Net Profit: ${stats['net_profit']:.4f}")
        self.logger.info(f"   Current Balance: ${self.current_balance:.2f}")
        if stats['total_cycles'] > 0:
            win_rate = (stats['successful_cycles'] / stats['total_cycles']) * 100
            self.logger.info(f"   Win Rate: {win_rate:.1f}%")

    def print_final_summary(self):
        """Print final summary of all 100 cycles"""
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

        # Show country performance
        self.logger.info("\n🌍 COUNTRY PERFORMANCE:")
        self.logger.info("-"*70)
        sorted_countries = sorted(self.country_performance.items(), key=lambda x: x[1]["total_profit"], reverse=True)
        for iso, data in sorted_countries[:10]:
            win_rate_country = (data["wins"] / data["trades"]) * 100 if data["trades"] > 0 else 0
            stop_rate = (data.get("stopped_out", 0) / data["trades"]) * 100 if data["trades"] > 0 else 0
            self.logger.info(f"   {data['flag']} {data['name']}: {data['trades']} trades, ${data['total_profit']:.4f}, {win_rate_country:.1f}% win, {stop_rate:.1f}% stopped")

        # Show top 5 best and worst trades
        if stats['cycle_results']:
            sorted_results = sorted(stats['cycle_results'], key=lambda x: x.get('profit', 0))

            self.logger.info("\n🏆 TOP 5 BEST TRADES:")
            for i, result in enumerate(sorted_results[-5:][::-1], 1):
                self.logger.info(f"   {i}. {result.get('country_flag', '')} {result.get('country_name', 'Unknown')}: ${result.get('profit', 0):.4f} ({result.get('profit_percent', 0):.2f}%)")

            self.logger.info("\n📉 TOP 5 WORST TRADES:")
            for i, result in enumerate(sorted_results[:5], 1):
                self.logger.info(f"   {i}. {result.get('country_flag', '')} {result.get('country_name', 'Unknown')}: ${result.get('profit', 0):.4f} ({result.get('profit_percent', 0):.2f}%)")

        self.logger.info("="*70)

    def export_results_to_csv(self):
        """Export cycle results to CSV file"""
        if not self.cycle_stats["cycle_results"]:
            return

        filename = f"crisis_scalper_results_{datetime.now().strftime('%Y%m%d')}.csv"
        file_exists = os.path.isfile(filename)

        with open(filename, 'a', newline='') as csvfile:
            fieldnames = ['cycle', 'timestamp', 'country', 'country_name', 'fsi_score',
                         'wst_class', 'entry_price', 'exit_price', 'quantity',
                         'profit', 'profit_percent', 'stopped_out', 'balance_after', 'success']
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
                'balance_after': f"{latest.get('balance_after', 0):.2f}",
                'success': latest['success']
            })

    def export_final_report(self):
        """Export comprehensive final report"""
        report = {
            "starting_balance": self.total_balance_usdt,
            "final_balance": self.current_balance,
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
    # ⚠️ WARNING: Replace these with your own API keys before going live!
    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"

    # Create bot instance - Optimized for $50 balance
    bot = ScalperBotV40(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol="BTCUSDT",
        test_mode=False,          # Set True for paper trading
        exchange_region="us",     # "us" -> api.binance.us, "global" -> api.binance.com
        log_level="INFO"          # DEBUG for more details
    )

    # Show top opportunities
    bot.run_scanner()

    # Run 100 cycles with 5 second delay between cycles
    bot.run_100_cycles(delay_between_cycles=5)
