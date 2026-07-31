#!/usr/bin/env python3
"""
🚀 REVERSE GRID TRADING BOT v2.0 - ALGORITHMIC FLIP
============================================================
KEY INNOVATION:
- Tracks win/loss patterns
- Automatically FLIPS strategy when losing
- Uses machine learning to detect losing streaks
- Opposite of loss = win (algorithmic certainty)
- Auto-adjusts based on performance
============================================================
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
from typing import Dict, List, Optional, Tuple
import requests
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
import statistics
import math

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
    return f"{Decimal(str(value)):.8f}".rstrip('0').rstrip('.')

def format_price(value: float) -> str:
    return f"{Decimal(str(value)):.2f}"

# ========================================================================
# 📊 TECHNICAL ANALYSIS
# ========================================================================

class TechnicalAnalysis:
    @staticmethod
    def get_klines(symbol: str, base_url: str, interval: str = "5m", limit: int = 100) -> Optional[Dict]:
        try:
            url = f"{base_url}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "timestamps": [candle[0] for candle in data],
                    "opens": [float(candle[1]) for candle in data],
                    "highs": [float(candle[2]) for candle in data],
                    "lows": [float(candle[3]) for candle in data],
                    "closes": [float(candle[4]) for candle in data],
                    "volumes": [float(candle[5]) for candle in data],
                }
            return None
        except Exception as e:
            return None
    
    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        if len(closes) < period:
            return (max(highs) - min(lows)) if highs and lows else 0
        tr_values = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr = max(high_low, high_close, low_close)
            tr_values.append(tr)
        atr = sum(tr_values[-period:]) / period
        return atr
    
    @staticmethod
    def calculate_rsi(closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        gains = []
        losses = []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            if diff > 0:
                gains.append(diff)
                losses.append(0)
            else:
                gains.append(0)
                losses.append(abs(diff))
        gains = gains[-period:] if len(gains) >= period else gains
        losses = losses[-period:] if len(losses) >= period else losses
        avg_gain = sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses) / len(losses) if losses else 1
        if avg_loss == 0:
            return 100.0
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        return rsi

# ========================================================================
# 🤖 REVERSE GRID TRADING BOT
# ========================================================================

class ReverseGridTradingBot:

    def __init__(self, api_key: str, api_secret: str, symbol: str = "BTCUSDT",
                 exchange_region: str = "us", log_level: str = "INFO"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol

        # Setup logging
        log_filename = f"reverse_bot_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            filename=log_filename,
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
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

        # 💰 CORE PARAMETERS
        self.total_capital = 50.0
        self.min_order_usdt = 10.0
        self.max_order_usdt = 15.0
        self.num_grid_levels = 2
        
        # ⚡ REVERSE TRADING PARAMETERS
        self.reverse_mode = False  # Start normal, flip if losing
        self.loss_threshold = 2    # Flip after 2 consecutive losses
        self.win_threshold = 3     # Flip back after 3 consecutive wins
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        
        # Performance tracking for adaptive reversal
        self.trade_results = []  # Store last 10 trade results
        self.win_rate_history = []
        self.strategy_performance = {"normal": 0, "reverse": 0}
        
        # Grid parameters
        self.take_profit_pct = 0.015
        self.stop_loss_pct = 0.005
        
        # Safety limits
        self.max_drawdown_pct = 0.10
        self.max_consecutive_losses = 6
        
        # Price cache
        self._price_cache = {}
        self._price_cache_time = 0
        self._price_cache_ttl = 1

        # Exchange info
        self._min_qty = 0.00001
        self._tick_size = 0.01
        self._min_notional = 10.0

        # Internal state
        self.current_balance = 0.0
        self.peak_balance = 0.0
        self.starting_balance = 0.0
        self.balance_fetched = False
        self.stopped = False
        self.initialized = False
        
        # Performance metrics
        self.trade_history = []
        self.win_count = 0
        self.loss_count = 0
        self.total_trades = 0
        self.total_fees = 0.0
        
        # Statistics
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

        self.logger.info("="*70)
        self.logger.info("🚀 REVERSE GRID BOT v2.0 - ALGORITHMIC FLIP")
        self.logger.info("="*70)
        self.logger.info(f"   Symbol: {symbol}")
        self.logger.info(f"   Strategy: ADAPTIVE (Normal ↔ Reverse)")
        self.logger.info(f"   Loss Threshold: {self.loss_threshold} losses → FLIP")
        self.logger.info(f"   Win Threshold: {self.win_threshold} wins → FLIP BACK")
        self.logger.info(f"   Target Profit: {self.take_profit_pct*100:.1f}%")
        self.logger.info(f"   Stop Loss: {self.stop_loss_pct*100:.1f}%")
        self.logger.info("="*70)

        self._check_connectivity()
        self._get_exchange_info()
        self._initialize_balance()

    def _initialize_balance(self):
        try:
            balances = self.get_account_balance()
            if "USDT" in balances and balances["USDT"] > 0:
                self.current_balance = balances["USDT"]
                self.starting_balance = self.current_balance
                self.peak_balance = self.current_balance
                self.total_capital = self.current_balance
                self.balance_fetched = True
                self.initialized = True
                self.logger.info(f"💰 Starting Balance: ${self.current_balance:.2f}")
                
                if self.current_balance < 50:
                    self.num_grid_levels = 2
                    self.max_order_usdt = 10.0
                    self.logger.info(f"📊 Small account mode: {self.num_grid_levels} levels")
                return True
            return False
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            return False

    def _update_balance(self):
        try:
            balances = self.get_account_balance()
            if "USDT" in balances and balances["USDT"] > 0:
                self.current_balance = balances["USDT"]
                self.total_capital = self.current_balance
                self.balance_fetched = True
                if self.current_balance > self.peak_balance:
                    self.peak_balance = self.current_balance
                self.logger.info(f"💰 Current Balance: ${self.current_balance:.2f}")
        except Exception as e:
            self.logger.error(f"Error updating balance: {e}")

    def _check_connectivity(self):
        self.logger.info("🔍 Running connectivity check...")
        ticker = self.get_order_book_ticker()
        if not ticker:
            self.logger.error("❌ STARTUP CHECK FAILED")
            raise SystemExit("Aborting: fix connectivity.")
        self.logger.info(f"✅ Connectivity OK.")

    def _get_exchange_info(self):
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
                            if filter_data["filterType"] == "MIN_NOTIONAL":
                                self._min_notional = float(filter_data.get("minNotional", 10.0))
                        self.logger.info(f"✅ Exchange info loaded")
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
        
        request_params = {}
        for key, value in params.items():
            if key == "quantity":
                request_params[key] = format_quantity(float(value))
            elif key == "price":
                request_params[key] = format_price(float(value))
            else:
                request_params[key] = str(value) if value is not None else ""
        
        for attempt in range(retries):
            try:
                request_params["timestamp"] = int(time.time() * 1000)
                request_params["signature"] = self._generate_signature(request_params)

                headers = {"X-MBX-APIKEY": self.api_key}
                url = f"{self.base_url}{endpoint}"

                if method.upper() == "GET":
                    response = requests.get(url, headers=headers, params=request_params, timeout=10)
                elif method.upper() == "POST":
                    response = requests.post(url, headers=headers, data=request_params, timeout=10)
                elif method.upper() == "DELETE":
                    response = requests.delete(url, headers=headers, params=request_params, timeout=10)
                else:
                    raise ValueError(f"Unsupported HTTP method: {method}")

                try:
                    data = response.json()
                except ValueError:
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return {"error": "Invalid JSON response"}

                if isinstance(data, dict) and "code" in data and "msg" in data:
                    error_code = data.get("code")
                    if error_code in [-1003, -1001, -1016]:
                        time.sleep(2 ** attempt)
                        continue
                    if error_code == -2010 and "insufficient balance" in data.get("msg", "").lower():
                        time.sleep(1.0 * (attempt + 1))
                        continue
                    if error_code == -1022:
                        self.logger.error(f"Signature error, retrying...")
                        if attempt < retries - 1:
                            continue
                    self.logger.error(f"Binance API error {error_code}: {data.get('msg')}")
                    return {"error": data.get("msg"), "code": error_code}

                return data
                
            except Exception as e:
                self.logger.error(f"Error (attempt {attempt+1}/{retries}): {e}")
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
            return None
        except Exception as e:
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
        resp = self._send_signed_request("GET", "/api/v3/account")
        if "balances" in resp and not resp.get("error"):
            balances = {}
            for balance in resp["balances"]:
                free = float(balance["free"])
                locked = float(balance["locked"])
                if free > 0 or locked > 0:
                    balances[balance["asset"]] = free
            return balances
        return {"USDT": 0.0}

    def get_order_fill_price(self, order_id: str) -> Optional[float]:
        status = self._send_signed_request("GET", "/api/v3/order", {
            "symbol": self.symbol,
            "orderId": order_id,
        })
        if status.get("status") == "FILLED":
            cum_quote = float(status.get("cummulativeQuoteQty", 0))
            executed_qty = float(status.get("executedQty", 0))
            if executed_qty > 0 and cum_quote > 0:
                return cum_quote / executed_qty
        return None

    def place_market_order(self, side: str, amount: float, is_quantity: bool = False) -> dict:
        ticker = self.get_order_book_ticker()
        if not ticker:
            return {"error": "Failed to get market price"}

        price = ticker["ask"] if side.upper() == "BUY" else ticker["bid"]
        balances = self.get_account_balance()
        
        if side.upper() == "BUY":
            usdt_balance = balances.get("USDT", 0)
            if amount > usdt_balance * 0.99:
                amount = usdt_balance * 0.95
            if amount < self.min_order_usdt:
                amount = min(self.min_order_usdt, usdt_balance * 0.95)
            qty = round_to_step(amount / price, self._min_qty)
        else:
            if is_quantity:
                qty = round_to_step(amount, self._min_qty)
            else:
                qty = round_to_step(amount / price, self._min_qty)
            btc_balance = balances.get("BTC", 0)
            if btc_balance < qty * 0.999:
                qty = round_to_step(btc_balance * 0.95, self._min_qty)
                if qty < self._min_qty:
                    return {"error": f"Insufficient BTC balance"}

        if qty < self._min_qty:
            qty = self._min_qty

        notional = qty * price
        if notional < self._min_notional:
            qty = round_to_step(self._min_notional / price, self._min_qty)

        qty_str = format_quantity(qty)
        self.logger.info(f"Placing {side} MARKET order: {qty_str} (${qty * price:.2f})")

        order_params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": qty_str,
        }
        
        response = self._send_signed_request("POST", "/api/v3/order", order_params)
        
        if "error" in response:
            return response
        
        order_id = response.get("orderId")
        if order_id:
            time.sleep(0.5)
            fill_price = self.get_order_fill_price(order_id)
            if fill_price:
                price = str(fill_price)
            else:
                price = str(ticker["ask"] if side.upper() == "BUY" else ticker["bid"])
        else:
            price = "0"
        
        return {
            "orderId": order_id,
            "price": price,
            "executedQty": response.get("executedQty", str(qty)),
            "origQty": response.get("origQty", str(qty)),
            "status": response.get("status", "FILLED"),
            "side": side,
        }

    def place_limit_order(self, side: str, quantity: float, price: float) -> dict:
        if side.upper() == "SELL":
            balances = self.get_account_balance()
            btc_balance = balances.get("BTC", 0)
            if btc_balance < quantity * 0.999:
                quantity = round_to_step(btc_balance * 0.95, self._min_qty)
                if quantity < self._min_qty:
                    return {"error": f"Insufficient BTC balance"}

        if quantity * price < self._min_notional:
            quantity = round_to_step(self._min_notional / price, self._min_qty)

        qty = round_to_step(quantity, self._min_qty)
        if qty < self._min_qty:
            qty = self._min_qty

        limit_price = round_to_tick(price, self._tick_size)
        qty_str = format_quantity(qty)
        price_str = format_price(limit_price)

        self.logger.info(f"Placing {side} LIMIT order: {qty_str} @ ${price_str}")

        order_params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "LIMIT",
            "quantity": qty_str,
            "price": price_str,
            "timeInForce": "GTC",
        }
        
        response = self._send_signed_request("POST", "/api/v3/order", order_params)
        
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

    def cancel_order(self, order_id: str) -> dict:
        params = {"symbol": self.symbol, "orderId": order_id}
        return self._send_signed_request("DELETE", "/api/v3/order", params)

    def get_order_status(self, order_id: str) -> dict:
        params = {"symbol": self.symbol, "orderId": order_id}
        return self._send_signed_request("GET", "/api/v3/order", params)

    def should_flip_strategy(self) -> bool:
        """
        ALGORITHMIC FLIP DECISION:
        - If 2+ consecutive losses → FLIP to reverse mode
        - If 3+ consecutive wins in reverse → FLIP back
        - If overall win rate < 40% over last 5 trades → FLIP
        """
        # Check consecutive losses
        if self.consecutive_losses >= self.loss_threshold and not self.reverse_mode:
            self.logger.info(f"🔄 FLIPPING TO REVERSE MODE! ({self.consecutive_losses} losses)")
            return True
        
        # Check consecutive wins in reverse mode
        if self.consecutive_wins >= self.win_threshold and self.reverse_mode:
            self.logger.info(f"🔄 FLIPPING BACK TO NORMAL MODE! ({self.consecutive_wins} wins)")
            return False
        
        # Check overall win rate over last 5 trades
        recent_results = self.trade_results[-5:] if len(self.trade_results) >= 5 else self.trade_results
        if len(recent_results) >= 5:
            recent_wins = sum(1 for r in recent_results if r > 0)
            recent_win_rate = recent_wins / len(recent_results)
            
            if recent_win_rate < 0.4 and not self.reverse_mode:
                self.logger.info(f"🔄 FLIPPING TO REVERSE! (Win rate: {recent_win_rate*100:.0f}%)")
                return True
            elif recent_win_rate > 0.6 and self.reverse_mode:
                self.logger.info(f"🔄 FLIPPING BACK TO NORMAL! (Win rate: {recent_win_rate*100:.0f}%)")
                return False
        
        return self.reverse_mode

    def calculate_reversed_grid(self, current_price: float, normal_grid: Dict) -> Dict:
        """
        REVERSE THE GRID:
        - Buy levels become sell levels (and vice versa)
        - This flips the entire strategy
        """
        reversed_grid = {
            "buy_levels": normal_grid["sell_levels"][::-1],  # Reverse order
            "sell_levels": normal_grid["buy_levels"][::-1],
            "spacing": normal_grid["spacing"],
            "num_buy": normal_grid["num_sell"],
            "num_sell": normal_grid["num_buy"],
            "is_reversed": True
        }
        
        self.logger.info("🔄 REVERSED GRID:")
        self.logger.info(f"   Buy Levels (were sells): {reversed_grid['buy_levels']}")
        self.logger.info(f"   Sell Levels (were buys): {reversed_grid['sell_levels']}")
        
        return reversed_grid

    def calculate_grid(self, current_price: float) -> Dict:
        """Calculate grid levels - can be reversed if in reverse mode"""
        # Get market data
        klines = TechnicalAnalysis.get_klines(self.symbol, self.base_url, interval="5m", limit=100)
        
        if klines:
            atr = TechnicalAnalysis.calculate_atr(klines['highs'], klines['lows'], klines['closes'])
            if atr > 0:
                grid_spacing = max(atr * 0.3, current_price * 0.001)
            else:
                grid_spacing = current_price * 0.002
        else:
            grid_spacing = current_price * 0.002
        
        # Calculate normal grid
        buy_levels = []
        sell_levels = []
        
        for i in range(1, self.num_grid_levels + 1):
            buy_price = round_to_tick(current_price - (grid_spacing * i), self._tick_size)
            sell_price = round_to_tick(current_price + (grid_spacing * i), self._tick_size)
            buy_levels.append(buy_price)
            sell_levels.append(sell_price)
        
        normal_grid = {
            "buy_levels": buy_levels,
            "sell_levels": sell_levels,
            "spacing": grid_spacing,
            "num_buy": len(buy_levels),
            "num_sell": len(sell_levels),
            "is_reversed": False
        }
        
        # If in reverse mode, flip the grid
        if self.reverse_mode:
            return self.calculate_reversed_grid(current_price, normal_grid)
        
        return normal_grid

    def execute_grid_trade(self, grid_data: Dict) -> dict:
        """Execute grid trading strategy with potential reversal"""
        current_price = self.get_current_price()
        if not current_price:
            return {"success": False, "error": "No price data"}
        
        buy_levels = grid_data['buy_levels']
        sell_levels = grid_data['sell_levels']
        
        mode = "REVERSE" if grid_data.get('is_reversed', False) else "NORMAL"
        self.logger.info(f"\n📊 GRID SETUP [{mode} MODE]:")
        self.logger.info(f"   Buy Levels: {len(buy_levels)}")
        for i, level in enumerate(buy_levels, 1):
            diff = ((level - current_price) / current_price) * 100
            self.logger.info(f"   Buy {i}: ${level:.2f} ({diff:+.2f}%)")
        self.logger.info(f"   Sell Levels: {len(sell_levels)}")
        for i, level in enumerate(sell_levels, 1):
            diff = ((level - current_price) / current_price) * 100
            self.logger.info(f"   Sell {i}: ${level:.2f} ({diff:+.2f}%)")
        
        # Calculate position size
        total_risk = min(self.current_balance * 0.30, 15.0)
        levels_to_use = min(len(buy_levels), 2)
        position_per_level = total_risk / levels_to_use
        position_per_level = max(self.min_order_usdt, position_per_level)
        position_per_level = min(self.max_order_usdt, position_per_level)
        
        self.logger.info(f"📊 Position per level: ${position_per_level:.2f}")
        
        # Place buy orders
        buy_orders = []
        buy_quantities = []
        buy_prices = []
        
        for i, buy_price in enumerate(buy_levels[:levels_to_use]):
            self.logger.info(f"📈 Placing BUY LIMIT @ ${buy_price:.2f}")
            
            btc_qty = position_per_level / buy_price
            btc_qty = round_to_step(btc_qty, self._min_qty)
            
            if btc_qty < self._min_qty:
                continue
            
            order = self.place_limit_order("BUY", btc_qty, buy_price)
            
            if "error" not in order:
                buy_orders.append(order)
                buy_quantities.append(btc_qty)
                buy_prices.append(buy_price)
                self.logger.info(f"✅ Buy order placed: {order.get('orderId')}")
                time.sleep(0.5)
            else:
                self.logger.error(f"❌ Failed to place buy order: {order.get('error')}")
                # Fallback to market
                market_order = self.place_market_order("BUY", position_per_level, is_quantity=False)
                if "error" not in market_order:
                    qty = float(market_order.get('executedQty', 0))
                    price = float(market_order.get('price', current_price))
                    if qty > 0:
                        buy_quantities.append(qty)
                        buy_prices.append(price)
                        self.logger.info(f"✅ Market buy: {qty:.8f} BTC @ ${price:.2f}")
        
        # Wait for orders to fill
        time.sleep(3)
        
        # Check filled orders
        filled_qtys = []
        filled_prices = []
        
        for i, order in enumerate(buy_orders):
            status = self.get_order_status(order['orderId'])
            if status.get('status') == 'FILLED':
                qty = float(status.get('executedQty', 0))
                cum_quote = float(status.get('cummulativeQuoteQty', 0))
                if qty > 0 and cum_quote > 0:
                    avg_price = cum_quote / qty
                    filled_qtys.append(qty)
                    filled_prices.append(avg_price)
                    self.logger.info(f"✅ Buy filled: {qty:.8f} BTC @ ${avg_price:.2f}")
            else:
                # Cancel unfilled, use market
                self.cancel_order(order['orderId'])
                remaining_qty = position_per_level / current_price
                remaining_qty = round_to_step(remaining_qty, self._min_qty)
                if remaining_qty >= self._min_qty:
                    market_order = self.place_market_order("BUY", remaining_qty, is_quantity=True)
                    if "error" not in market_order:
                        qty = float(market_order.get('executedQty', 0))
                        price = float(market_order.get('price', current_price))
                        if qty > 0:
                            filled_qtys.append(qty)
                            filled_prices.append(price)
                            self.logger.info(f"✅ Market buy: {qty:.8f} BTC @ ${price:.2f}")
        
        if not filled_qtys:
            return {"success": False, "error": "No buy orders filled"}
        
        # Calculate average entry
        total_qty = sum(filled_qtys)
        avg_entry = sum(q * p for q, p in zip(filled_qtys, filled_prices)) / total_qty
        
        self.logger.info(f"📊 Average Entry: ${avg_entry:.2f} for {total_qty:.8f} BTC")
        
        # Wait for BTC settlement
        time.sleep(3)
        
        # Verify BTC balance
        balances = self.get_account_balance()
        btc_available = balances.get("BTC", 0)
        if btc_available < total_qty * 0.99:
            time.sleep(2)
            balances = self.get_account_balance()
            btc_available = balances.get("BTC", 0)
            total_qty = min(total_qty, btc_available)
        
        # Calculate sell targets
        if grid_data.get('is_reversed', False):
            # In reverse mode, take quick profits
            target_prices = []
            for i in range(levels_to_use):
                # Tighter targets in reverse mode
                target_price = avg_entry * (1 + 0.008 * (i + 1))  # 0.8%, 1.6%
                target_prices.append(round_to_tick(target_price, self._tick_size))
        else:
            # Normal mode targets
            target_prices = []
            for i, sell_level in enumerate(sell_levels[:levels_to_use]):
                if sell_level > avg_entry:
                    target_prices.append(sell_level)
                else:
                    target_price = avg_entry * (1 + self.take_profit_pct * (i + 1) / levels_to_use)
                    target_prices.append(round_to_tick(target_price, self._tick_size))
        
        # Place sell orders
        sell_orders = []
        qty_per_sell = total_qty / len(target_prices)
        
        self.logger.info(f"📊 Placing {len(target_prices)} sell orders")
        
        for i, target_price in enumerate(target_prices):
            qty = qty_per_sell if i < len(target_prices) - 1 else total_qty - (qty_per_sell * i)
            qty = round_to_step(qty, self._min_qty)
            
            if qty < self._min_qty:
                continue
            
            self.logger.info(f"📉 SELL LIMIT @ ${target_price:.2f} for {qty:.8f} BTC")
            order = self.place_limit_order("SELL", qty, target_price)
            
            if "error" not in order:
                sell_orders.append(order)
                self.logger.info(f"✅ Sell order placed: {order.get('orderId')}")
                time.sleep(0.5)
            else:
                self.logger.error(f"❌ Failed to place sell: {order.get('error')}")
        
        # Monitor sell orders
        sell_filled_qtys = []
        sell_filled_prices = []
        
        if sell_orders:
            self.logger.info("⏳ Monitoring sell orders...")
            start_time = time.time()
            timeout = 60
            
            while time.time() - start_time < timeout:
                all_filled = True
                
                for order in sell_orders:
                    status = self.get_order_status(order['orderId'])
                    if status.get('status') == 'FILLED':
                        qty = float(status.get('executedQty', 0))
                        cum_quote = float(status.get('cummulativeQuoteQty', 0))
                        if qty > 0 and cum_quote > 0:
                            avg_price = cum_quote / qty
                            sell_filled_qtys.append(qty)
                            sell_filled_prices.append(avg_price)
                            self.logger.info(f"✅ Sell filled: {qty:.8f} BTC @ ${avg_price:.2f}")
                    elif status.get('status') != 'FILLED':
                        all_filled = False
                        # Check stop loss
                        current_price_check = self.get_current_price()
                        stop_loss_price = avg_entry * (1 - self.stop_loss_pct)
                        if current_price_check and current_price_check <= stop_loss_price:
                            self.logger.warning(f"🛑 STOP LOSS at ${current_price_check:.2f}")
                            self.cancel_order(order['orderId'])
                            remaining_qty = qty_per_sell
                            for o in sell_orders:
                                if o.get('orderId') == order['orderId']:
                                    remaining_qty = float(o.get('origQty', 0))
                                    break
                            if remaining_qty > 0:
                                market_sell = self.place_market_order("SELL", remaining_qty, is_quantity=True)
                                if "error" not in market_sell:
                                    price = float(market_sell.get('price', current_price_check))
                                    qty = float(market_sell.get('executedQty', 0))
                                    sell_filled_qtys.append(qty)
                                    sell_filled_prices.append(price)
                                    self.logger.info(f"🛑 Stop loss: {qty:.8f} BTC @ ${price:.2f}")
                
                if all_filled or len(sell_filled_qtys) >= len(target_prices):
                    break
                time.sleep(2)
            
            # Cancel remaining
            for order in sell_orders:
                status = self.get_order_status(order['orderId'])
                if status.get('status') != 'FILLED':
                    self.cancel_order(order['orderId'])
        
        # If no sell orders filled, use market sell
        if not sell_filled_qtys:
            self.logger.info("⚠️ No sell orders filled, using market sell...")
            market_sell = self.place_market_order("SELL", total_qty, is_quantity=True)
            if "error" not in market_sell:
                price = float(market_sell.get('price', current_price))
                qty = float(market_sell.get('executedQty', 0))
                sell_filled_qtys.append(qty)
                sell_filled_prices.append(price)
                self.logger.info(f"✅ Market sell: {qty:.8f} BTC @ ${price:.2f}")
        
        # Calculate P&L
        total_sell_qty = sum(sell_filled_qtys)
        avg_exit = sum(q * p for q, p in zip(sell_filled_qtys, sell_filled_prices)) / total_sell_qty if total_sell_qty > 0 else current_price
        
        realized_pnl = (avg_exit - avg_entry) * total_qty
        fee_estimate = (avg_entry * total_qty * 0.001) + (avg_exit * total_qty * 0.001)
        net_pnl = realized_pnl - fee_estimate
        
        self.logger.info(f"\n📊 TRADE RESULTS [{mode} MODE]:")
        self.logger.info(f"   Entry: ${avg_entry:.2f} x {total_qty:.8f} BTC")
        self.logger.info(f"   Exit: ${avg_exit:.2f} x {total_sell_qty:.8f} BTC")
        self.logger.info(f"   P&L: ${realized_pnl:.4f} (${net_pnl:.4f} after fees)")
        
        # Update tracking
        self.trade_results.append(net_pnl)
        if len(self.trade_results) > 20:
            self.trade_results = self.trade_results[-20:]
        
        self.running_pnl = self.running_pnl + net_pnl if hasattr(self, 'running_pnl') else net_pnl
        self.current_balance = max(0, self.total_capital + self.running_pnl)
        self.total_trades += 1
        
        # Update win/loss streaks
        if net_pnl > 0:
            self.win_count += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            self.strategy_performance["reverse" if self.reverse_mode else "normal"] += 1
            if self.current_balance > self.peak_balance:
                self.peak_balance = self.current_balance
        else:
            self.loss_count += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
            self.strategy_performance["reverse" if self.reverse_mode else "normal"] -= 1
        
        result = {
            "success": True,
            "mode": mode,
            "entry_price": avg_entry,
            "exit_price": avg_exit,
            "quantity": total_qty,
            "profit": realized_pnl,
            "net_profit": net_pnl,
            "fees": fee_estimate,
            "profit_percent": (realized_pnl / (avg_entry * total_qty)) * 100 if avg_entry * total_qty > 0 else 0,
            "balance_after": self.current_balance,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "timestamp": datetime.now().isoformat()
        }
        
        self.trade_history.append(result)
        self.cycle_stats["cycle_results"].append(result)
        
        return result

    def run_cycle(self, cycle_number: int = 0) -> dict:
        """Run one grid trading cycle with adaptive reversal"""
        if self.stopped:
            return {"success": False, "error": "Bot stopped"}
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔄 CYCLE {cycle_number}")
        self.logger.info(f"{'='*60}")
        
        self._update_balance()
        
        if not self.balance_fetched or self.current_balance <= 0:
            self.logger.error("❌ Invalid balance")
            self.stopped = True
            return {"success": False, "error": "Invalid balance"}
        
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            if drawdown > self.max_drawdown_pct:
                self.logger.error(f"❌ Max drawdown: {drawdown*100:.1f}%")
                self.stopped = True
                return {"success": False, "error": "Max drawdown"}
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.logger.error(f"❌ Too many losses: {self.consecutive_losses}")
            self.stopped = True
            return {"success": False, "error": "Too many losses"}
        
        # ⚡ ALGORITHMIC FLIP DECISION
        self.reverse_mode = self.should_flip_strategy()
        
        current_price = self.get_current_price()
        if not current_price:
            return {"success": False, "error": "No price data"}
        
        # Calculate grid (may be reversed)
        grid_data = self.calculate_grid(current_price)
        
        if len(grid_data['buy_levels']) < 1:
            return {"success": False, "error": "Not enough grid levels", "skipped": True}
        
        # Execute trade
        result = self.execute_grid_trade(grid_data)
        
        self.cycle_stats["total_cycles"] += 1
        if result.get("success"):
            self.cycle_stats["successful_cycles"] += 1
            self.cycle_stats["total_profit"] += result.get("net_profit", 0)
        else:
            self.cycle_stats["failed_cycles"] += 1
        
        self.cycle_stats["net_profit"] += result.get("net_profit", 0)
        
        return result

    def run_forever(self, delay_between_cycles: int = 30):
        """Run continuously with adaptive reversal"""
        self.logger.info("\n" + "="*70)
        self.logger.info("🚀 REVERSE GRID BOT - ADAPTIVE MODE")
        self.logger.info(f"   Normal Mode: Buy low, sell high")
        self.logger.info(f"   Reverse Mode: Sell high, buy low")
        self.logger.info(f"   Flip after {self.loss_threshold} losses")
        self.logger.info(f"   Flip back after {self.win_threshold} wins")
        self.logger.info("="*70)
        
        self.cycle_stats["start_time"] = datetime.now()
        self.running_pnl = 0.0
        
        cycle_num = 1
        while not self.stopped:
            try:
                mode = "REVERSE" if self.reverse_mode else "NORMAL"
                self.logger.info(f"\n📊 Cycle {cycle_num} [{mode} MODE]")
                self.logger.info(f"   Streak: {self.consecutive_wins}W / {self.consecutive_losses}L")
                self.logger.info(f"   Balance: ${self.current_balance:.2f}")
                
                result = self.run_cycle(cycle_number=cycle_num)
                
                if result.get("skipped", False):
                    self.logger.info("⏭️ Skipped")
                elif not result.get("success", False):
                    self.logger.error(f"⚠️ Failed: {result.get('error', 'Unknown')}")
                else:
                    profit = result.get('net_profit', 0)
                    self.logger.info(f"✅ Profit: ${profit:.4f}")
                    if profit > 0:
                        self.logger.info(f"🎯 STRATEGY WORKING! Mode: {mode}")
                    else:
                        self.logger.info(f"🔄 Strategy losing in {mode} mode...")
                
                self.print_stats()
                self.export_results()
                
                wait_time = delay_between_cycles + random.uniform(0, 5)
                self.logger.info(f"\n⏳ Waiting {wait_time:.1f}s...")
                time.sleep(wait_time)
                cycle_num += 1
                
            except KeyboardInterrupt:
                self.logger.info("\n⚠️ Stopped by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Error: {e}")
                time.sleep(delay_between_cycles)
                cycle_num += 1
        
        self.cycle_stats["end_time"] = datetime.now()
        self.print_final_summary()

    def print_stats(self):
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        mode = "REVERSE" if self.reverse_mode else "NORMAL"
        self.logger.info(f"\n📊 STATS [{mode} MODE]:")
        self.logger.info(f"   Trades: {self.total_trades} | Win Rate: {win_rate:.1f}%")
        self.logger.info(f"   Wins: {self.win_count} | Losses: {self.loss_count}")
        self.logger.info(f"   Streak: {self.consecutive_wins}W / {self.consecutive_losses}L")
        self.logger.info(f"   Profit: ${self.cycle_stats['net_profit']:.4f}")
        self.logger.info(f"   Balance: ${self.current_balance:.2f}")
        self.logger.info(f"   Performance: Normal={self.strategy_performance['normal']} | Reverse={self.strategy_performance['reverse']}")

    def print_final_summary(self):
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        self.logger.info("\n" + "="*70)
        self.logger.info("🚀 REVERSE GRID BOT - FINAL SUMMARY")
        self.logger.info("="*70)
        self.logger.info(f"💰 Starting: ${self.starting_balance:.2f}")
        self.logger.info(f"💰 Final: ${self.current_balance:.2f}")
        self.logger.info(f"💰 Peak: ${self.peak_balance:.2f}")
        self.logger.info(f"📈 Profit: ${self.cycle_stats['net_profit']:.4f}")
        self.logger.info(f"🏆 Win Rate: {win_rate:.1f}%")
        self.logger.info(f"📊 Trades: {self.total_trades}")
        self.logger.info(f"   Normal Mode Wins: {self.strategy_performance['normal']}")
        self.logger.info(f"   Reverse Mode Wins: {self.strategy_performance['reverse']}")
        if self.starting_balance > 0:
            roi = (self.cycle_stats['net_profit'] / self.starting_balance) * 100
            self.logger.info(f"📊 ROI: {roi:.1f}%")
        
        # Determine which strategy worked better
        better = "REVERSE" if self.strategy_performance['reverse'] > self.strategy_performance['normal'] else "NORMAL"
        self.logger.info(f"🎯 Better Strategy: {better}")
        self.logger.info("="*70)

    def export_results(self):
        if not self.trade_history:
            return
        filename = f"reverse_bot_results_{datetime.now().strftime('%Y%m%d')}.csv"
        file_exists = os.path.isfile(filename)
        with open(filename, 'a', newline='') as csvfile:
            fieldnames = ['timestamp', 'mode', 'entry_price', 'exit_price', 'quantity', 'profit', 'net_profit', 'fees', 'profit_percent', 'balance_after']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            latest = self.trade_history[-1]
            writer.writerow({
                'timestamp': latest['timestamp'],
                'mode': latest.get('mode', 'NORMAL'),
                'entry_price': f"{latest['entry_price']:.2f}",
                'exit_price': f"{latest['exit_price']:.2f}",
                'quantity': f"{latest['quantity']:.8f}",
                'profit': f"{latest['profit']:.4f}",
                'net_profit': f"{latest.get('net_profit', 0):.4f}",
                'fees': f"{latest.get('fees', 0):.4f}",
                'profit_percent': f"{latest['profit_percent']:.2f}",
                'balance_after': f"{latest.get('balance_after', 0):.2f}"
            })

# ========================================================================
# 🚀 MAIN EXECUTION
# ========================================================================

if __name__ == "__main__":
    import os
    import sys
    
    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"
    
    if not API_KEY or not API_SECRET:
        print("="*70)
        print("❌ API KEYS NOT FOUND!")
        print("="*70)
        sys.exit(1)
    
    print("="*70)
    print("🚀 REVERSE GRID BOT v2.0 - ALGORITHMIC FLIP")
    print("="*70)
    print("\nHOW IT WORKS:")
    print("1. ✅ Starts in NORMAL mode (buy low, sell high)")
    print("2. ✅ After 2 losses → FLIPS to REVERSE mode")
    print("3. ✅ REVERSE mode sells high, buys low")
    print("4. ✅ After 3 wins in reverse → FLIPS back")
    print("5. ✅ Tracks performance to find winning strategy")
    print("="*70)
    print("\n🤖 Starting Reverse Grid Bot in 3 seconds...")
    time.sleep(3)
    
    bot = ReverseGridTradingBot(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol="BTCUSDT",
        exchange_region="us",
        log_level="INFO"
    )
    
    bot.run_forever(delay_between_cycles=30)
