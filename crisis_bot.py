#!/usr/bin/env python3
"""
🚀 HYBRID DCA + RSI/MACD MOMENTUM BOT v1.0
============================================================
TOP RECOMMENDED ALGORITHM FOR BINANCE TRADING BOTS

STRATEGY:
1. Monitor price, RSI (15m), and MACD
2. Buy when: Price drops 2% AND RSI < 30 (oversold)
3. Scale position: 1x, 1.5x, 2.25x (Martingale)
4. Exit: Trailing take-profit at +2.5% from average entry
5. Check every minute for new opportunities

WHY THIS WORKS:
- RSI filter prevents buying in freefall
- DCA scaling lowers average entry
- Trailing stops capture bounces
- Perfect for choppy/dead markets
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
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple, Any
import requests
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
import statistics
import math
from collections import deque

# ========================================================================
# CONFIGURATION
# ========================================================================

DCA_CONFIG = {
    "symbol": "AVAXUSDT",
    "interval": "1m",  # Check every minute
    "price_drop_pct": 0.02,        # 2% price drop required
    "rsi_oversold": 30,            # RSI < 30 to buy
    "take_profit_pct": 0.025,      # 2.5% profit target
    "max_buy_levels": 3,           # Maximum 3 DCA levels
    "martingale_multiplier": 1.5,   # 1.5x scaling
    "base_order_usdt": 10.0,       # First buy $10
    "max_order_usdt": 30.0,        # Max per order
    "max_total_usdt": 60.0,        # Max total in one cycle
    "trailing_stop_pct": 0.5,      # 50% trailing stop
    "min_volume_ratio": 1.2,       # Volume spike confirmation
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
    if value <= 0:
        return "0.00000000"
    return f"{Decimal(str(value)):.8f}"

def format_price(value: float) -> str:
    return f"{Decimal(str(value)):.2f}"

# ========================================================================
# TECHNICAL INDICATORS
# ========================================================================

class TechnicalIndicators:
    @staticmethod
    def get_klines(symbol: str, base_url: str, interval: str = "1m", limit: int = 100,
                    end_time_ms: int = None) -> Optional[Dict]:
        try:
            url = f"{base_url}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            if end_time_ms:
                params["endTime"] = end_time_ms
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                return {
                    "timestamps": [c[0] for c in data],
                    "opens": [float(c[1]) for c in data],
                    "highs": [float(c[2]) for c in data],
                    "lows": [float(c[3]) for c in data],
                    "closes": [float(c[4]) for c in data],
                    "volumes": [float(c[5]) for c in data],
                }
            return None
        except Exception:
            return None

    @staticmethod
    def rsi(closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            gains.append(diff if diff > 0 else 0)
            losses.append(abs(diff) if diff < 0 else 0)
        avg_gain = sum(gains[-period:]) / period
        avg_loss = sum(losses[-period:]) / period
        if avg_loss == 0:
            return 100.0
        return 100 - (100 / (1 + avg_gain / avg_loss))

    @staticmethod
    def ema(data: List[float], period: int) -> float:
        if not data or len(data) < period:
            return data[-1] if data else 0
        alpha = 2 / (period + 1)
        ema_val = sum(data[:period]) / period
        for price in data[period:]:
            ema_val = price * alpha + ema_val * (1 - alpha)
        return ema_val

    @staticmethod
    def macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        if len(closes) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0, "bullish": False, "bearish": False}
        ema_fast = TechnicalIndicators.ema(closes, fast)
        ema_slow = TechnicalIndicators.ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.ema([macd_line] * signal, signal)
        histogram = macd_line - signal_line
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
            "bullish": macd_line > signal_line,
            "bearish": macd_line < signal_line
        }

    @staticmethod
    def atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return (max(highs) - min(lows)) if highs and lows else 0
        tr_values = []
        for i in range(1, len(closes)):
            hl = highs[i] - lows[i]
            hc = abs(highs[i] - closes[i-1])
            lc = abs(lows[i] - closes[i-1])
            tr_values.append(max(hl, hc, lc))
        return sum(tr_values[-period:]) / period

# ========================================================================
# DCA STRATEGY ENGINE
# ========================================================================

class DCAStrategy:
    def __init__(self, config: Dict = None):
        self.config = config or DCA_CONFIG
        self.buy_levels = []
        self.total_qty = 0.0
        self.total_cost = 0.0
        self.avg_price = 0.0
        self.current_level = 0
        self.last_buy_price = 0.0
        self.highest_price = 0.0
        self.trailing_stop = 0.0
        self.position_open = False
        self.entry_time = None
        
    def reset(self):
        """Reset DCA state for new cycle"""
        self.buy_levels = []
        self.total_qty = 0.0
        self.total_cost = 0.0
        self.avg_price = 0.0
        self.current_level = 0
        self.last_buy_price = 0.0
        self.highest_price = 0.0
        self.trailing_stop = 0.0
        self.position_open = False
        self.entry_time = None
    
    def calculate_buy_amount(self, level: int) -> float:
        """Calculate buy amount with Martingale scaling"""
        base = self.config["base_order_usdt"]
        multiplier = self.config["martingale_multiplier"]
        amount = base * (multiplier ** level)
        return min(amount, self.config["max_order_usdt"])
    
    def check_entry_signal(self, data: Dict) -> Dict:
        """Check if entry conditions are met"""
        closes = data['closes']
        highs = data['highs']
        lows = data['lows']
        volumes = data['volumes']
        
        current_price = closes[-1]
        
        # Calculate indicators
        rsi = TechnicalIndicators.rsi(closes, 14)
        macd = TechnicalIndicators.macd(closes, 12, 26, 9)
        atr = TechnicalIndicators.atr(highs, lows, closes, 14)
        
        # Price drop check (from 1 minute ago)
        price_drop = 0
        if len(closes) >= 2:
            price_drop = (closes[-2] - current_price) / closes[-2]
        
        # Volume spike check
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        volume_ratio = volumes[-1] / avg_volume if avg_volume > 0 else 1
        
        # Conditions
        conditions = {
            "price_drop": price_drop >= self.config["price_drop_pct"],
            "rsi_oversold": rsi < self.config["rsi_oversold"],
            "macd_bullish": macd['bullish'] or macd['histogram'] > 0,
            "volume_spike": volume_ratio >= self.config["min_volume_ratio"],
        }
        
        # ENTRY: Price drop + RSI oversold (MACD and volume optional)
        entry_signal = conditions["price_drop"] and conditions["rsi_oversold"]
        
        return {
            "entry": entry_signal,
            "rsi": rsi,
            "price_drop": price_drop,
            "macd_bullish": macd['bullish'],
            "volume_ratio": volume_ratio,
            "current_price": current_price,
            "atr": atr,
            "conditions": conditions,
        }
    
    def check_exit_signal(self, current_price: float) -> Dict:
        """Check if exit conditions are met"""
        if not self.position_open or self.total_qty <= 0:
            return {"exit": False, "reason": "No position"}
        
        # Update highest price
        if current_price > self.highest_price:
            self.highest_price = current_price
            # Update trailing stop
            trail_pct = self.config["trailing_stop_pct"] / 100
            new_stop = self.highest_price * (1 - trail_pct * 2)
            if new_stop > self.trailing_stop:
                self.trailing_stop = new_stop
        
        # Target profit check
        profit_pct = (current_price - self.avg_price) / self.avg_price
        target_profit = self.config["take_profit_pct"]
        
        # Exit conditions
        exit_signal = False
        reason = ""
        
        # 1. Target profit hit
        if profit_pct >= target_profit:
            exit_signal = True
            reason = f"Target profit {profit_pct*100:.2f}% >= {target_profit*100:.1f}%"
        
        # 2. Trailing stop hit (if trailing stop is active)
        elif self.trailing_stop > 0 and current_price <= self.trailing_stop:
            exit_signal = True
            reason = f"Trailing stop hit at ${self.trailing_stop:.2f}"
        
        # 3. Time exit (max 4 hours for 1m timeframe)
        elif self.entry_time:
            time_held = (datetime.now() - self.entry_time).total_seconds() / 3600
            if time_held > 4:  # 4 hours max
                exit_signal = True
                reason = f"Time exit after {time_held:.1f}h"
        
        # 4. Emergency stop loss (1.5x ATR)
        elif self.last_buy_price > 0:
            atr = TechnicalIndicators.atr([0], [0], [0], 14)
            emergency_stop = self.last_buy_price * 0.97  # 3% emergency stop
            if current_price <= emergency_stop:
                exit_signal = True
                reason = f"Emergency stop at ${emergency_stop:.2f}"
        
        return {
            "exit": exit_signal,
            "reason": reason,
            "profit_pct": profit_pct,
            "current_price": current_price,
            "avg_price": self.avg_price,
            "trailing_stop": self.trailing_stop,
            "highest_price": self.highest_price,
            "time_held": (datetime.now() - self.entry_time).total_seconds() / 3600 if self.entry_time else 0,
        }

# ========================================================================
# DCA BOT - PRODUCTION
# ========================================================================

class DCABot:

    def __init__(self, api_key: str, api_secret: str, 
                 symbol: str = DCA_CONFIG["symbol"],
                 exchange_region: str = "us", 
                 log_level: str = "INFO"):
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.base_asset = symbol.replace("USDT", "")
        self.config = DCA_CONFIG
        
        # DCA Strategy
        self.strategy = DCAStrategy(self.config)
        
        if exchange_region.lower() == "us":
            self.base_url = "https://api.binance.us"
        elif exchange_region.lower() == "global":
            self.base_url = "https://api.binance.com"
        else:
            raise ValueError('exchange_region must be "us" or "global"')
        
        self.maker_fee_rate = 0.001
        self.taker_fee_rate = 0.001
        
        self._min_qty = 0.00001
        self._tick_size = 0.01
        self._min_notional = 10.0
        self._price_cache = {}
        self._price_cache_time = 0
        self._price_cache_ttl = 10
        
        # State
        self.has_open_position = False
        self.position_order_id = None
        self.current_balance_usdt = 0.0
        self.current_balance_asset = 0.0
        self.starting_balance = 0.0
        self.peak_balance = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.balance_fetched = False
        self.stopped = False
        self.skipped_count = 0
        self.dca_level = 0
        self.total_invested = 0.0
        
        # Stats
        self.trade_history = []
        self.win_count = 0
        self.loss_count = 0
        self.total_trades = 0
        self.total_fees = 0.0
        self.running_pnl = 0.0
        
        self.cycle_stats = {
            "total_cycles": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "net_profit": 0.0,
            "start_time": None,
            "end_time": None,
            "cycle_results": []
        }
        
        # Logging
        log_filename = f"dca_bot_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(
            filename=log_filename,
            level=getattr(logging, log_level.upper()),
            format='%(asctime)s - %(levelname)s - %(message)s'
        )
        self.logger = logging.getLogger(__name__)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(console)
        
        self.logger.info("="*70)
        self.logger.info("🚀 HYBRID DCA + RSI/MACD BOT v1.0")
        self.logger.info("="*70)
        self.logger.info(f"   Symbol: {symbol}")
        self.logger.info(f"   Check Interval: {self.config['interval']}")
        self.logger.info(f"   Price Drop: {self.config['price_drop_pct']*100:.1f}%")
        self.logger.info(f"   RSI Threshold: < {self.config['rsi_oversold']}")
        self.logger.info(f"   Take Profit: {self.config['take_profit_pct']*100:.1f}%")
        self.logger.info(f"   Max DCA Levels: {self.config['max_buy_levels']}")
        self.logger.info("="*70)
        
        self._check_connectivity()
        self._get_exchange_info()
        self._update_balances()

    def _check_existing_orders(self):
        """Check for any existing open orders"""
        try:
            resp = self._send_signed_request("GET", "/api/v3/openOrders", {"symbol": self.symbol})
            if "error" not in resp and resp:
                for order in resp:
                    if order.get("side") == "SELL" and order.get("status") == "NEW":
                        self.has_open_position = True
                        self.position_order_id = order.get("orderId")
                        self.logger.info(f"📊 Found existing SELL order: {self.position_order_id}")
                        self._get_position_details()
                        break
        except Exception as e:
            self.logger.warning(f"Could not check existing orders: {e}")

    def _get_position_details(self):
        """Get position details from trade history"""
        try:
            resp = self._send_signed_request("GET", "/api/v3/myTrades", {"symbol": self.symbol, "limit": 10})
            if "error" not in resp and resp:
                buys = [t for t in resp if t.get("isBuyer")]
                if buys:
                    total_qty = sum(float(t.get("qty", 0)) for t in buys)
                    total_cost = sum(float(t.get("price", 0)) * float(t.get("qty", 0)) for t in buys)
                    self.strategy.total_qty = total_qty
                    self.strategy.total_cost = total_cost
                    self.strategy.avg_price = total_cost / total_qty if total_qty > 0 else 0
                    self.strategy.position_open = True
                    self.strategy.entry_time = datetime.now()
                    self.strategy.highest_price = self.strategy.avg_price
                    self.strategy.trailing_stop = self.strategy.avg_price * (1 - 0.015)
                    self.logger.info(f"📊 Recovered position: {total_qty:.8f} @ ${self.strategy.avg_price:.2f}")
        except Exception:
            pass

    def _check_connectivity(self):
        self.logger.info("🔍 Running connectivity check...")
        ticker = self.get_order_book_ticker()
        if not ticker:
            self.logger.error("❌ STARTUP CHECK FAILED")
            raise SystemExit("Aborting.")
        self.logger.info("✅ Connectivity OK.")

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

    def _update_balances(self):
        try:
            balances = self.get_account_balance()
            if "USDT" in balances and balances["USDT"] > 0:
                self.current_balance_usdt = balances["USDT"]
                self.balance_fetched = True
            else:
                self.current_balance_usdt = 0.0
            
            if self.base_asset in balances and balances[self.base_asset] > 0:
                self.current_balance_asset = balances[self.base_asset]
            else:
                self.current_balance_asset = 0.0
            
            if self.starting_balance == 0 and self.current_balance_usdt > 0:
                self.starting_balance = self.current_balance_usdt
                self.peak_balance = self.current_balance_usdt
                self.logger.info(f"💰 Starting USDT: ${self.starting_balance:.2f}")
            
            if self.current_balance_usdt > self.peak_balance:
                self.peak_balance = self.current_balance_usdt
            
            return True
        except Exception as e:
            self.logger.error(f"Error fetching balances: {e}")
            return False

    def _generate_signature(self, params: dict) -> str:
        query_string = urllib.parse.urlencode(params)
        return hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()

    def _send_signed_request(self, method: str, endpoint: str, params: dict = None, retries: int = 3) -> dict:
        if params is None:
            params = {}
        if "quantity" in params:
            try:
                qty_val = float(params["quantity"])
                if qty_val <= 0:
                    return {"error": "Invalid quantity", "code": -1003}
                params["quantity"] = format_quantity(qty_val)
            except (ValueError, TypeError):
                return {"error": "Invalid quantity", "code": -1003}
        if "price" in params:
            try:
                price_val = float(params["price"])
                if price_val <= 0:
                    return {"error": "Invalid price", "code": -1003}
                params["price"] = format_price(price_val)
            except (ValueError, TypeError):
                return {"error": "Invalid price", "code": -1003}
        
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
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return {"error": "Invalid JSON response", "status_code": response.status_code}

                if isinstance(data, dict) and "code" in data and "msg" in data:
                    error_code = data.get("code")
                    if error_code in [-1003, -1001, -1016]:
                        time.sleep(2 ** attempt)
                        continue
                    if error_code == -2010:
                        self._update_balances()
                        return {"error": data.get("msg"), "code": error_code, "insufficient": True}
                    return {"error": data.get("msg"), "code": error_code}
                return data
            except Exception as e:
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
                ticker_data = {"bid": float(data["bidPrice"]), "ask": float(data["askPrice"])}
                self._price_cache = {'ticker': ticker_data}
                self._price_cache_time = now
                return ticker_data
            return None
        except Exception:
            return None

    def get_current_price(self) -> Optional[float]:
        ticker = self.get_order_book_ticker()
        if not ticker:
            return None
        return (ticker["bid"] + ticker["ask"]) / 2

    def get_account_balance(self) -> Dict[str, float]:
        resp = self._send_signed_request("GET", "/api/v3/account")
        if "balances" in resp and not resp.get("error"):
            balances = {}
            for balance in resp["balances"]:
                free = float(balance["free"])
                if free > 0:
                    balances[balance["asset"]] = free
            return balances
        return {}

    def get_order_status(self, order_id: str) -> dict:
        if not order_id or order_id == "0" or "ERR_" in str(order_id):
            return {"status": "FILLED", "orderId": order_id}
        params = {"symbol": self.symbol, "orderId": order_id}
        return self._send_signed_request("GET", "/api/v3/order", params)

    def cancel_order(self, order_id: str) -> dict:
        if not order_id or order_id == "0" or "ERR_" in str(order_id):
            return {"status": "CANCELED", "orderId": order_id}
        params = {"symbol": self.symbol, "orderId": order_id}
        response = self._send_signed_request("DELETE", "/api/v3/order", params)
        if response.get("code") == -2011:
            return {"status": "CANCELED", "orderId": order_id}
        return response

    def place_market_order(self, side: str, amount: float, is_quantity: bool = False) -> dict:
        ticker = self.get_order_book_ticker()
        if not ticker:
            return {"error": "Failed to get market price"}
        
        price = ticker["ask"] if side.upper() == "BUY" else ticker["bid"]
        
        if amount <= 0:
            return {"error": "Invalid amount", "code": -1003}
        
        if is_quantity:
            qty = amount
        else:
            qty = amount / price
        
        qty = round_to_step(qty, self._min_qty)
        if qty < self._min_qty:
            qty = self._min_qty
        
        notional = qty * price
        if notional < self._min_notional:
            qty = self._min_notional / price
            qty = round_to_step(qty, self._min_qty)
        
        qty_str = format_quantity(qty)
        self.logger.info(f"📊 Placing {side} MARKET order: {qty_str} @ ~${price:.2f}")
        
        params = {"symbol": self.symbol, "side": side.upper(), "type": "MARKET", "quantity": qty_str}
        response = self._send_signed_request("POST", "/api/v3/order", params)
        
        if "error" in response:
            return response
        
        order_id = response.get("orderId")
        if not order_id:
            return {"error": "No orderId returned"}
        
        self.logger.info(f"⏳ Waiting for {side} order to fill...")
        max_wait = 30
        wait_start = time.time()
        
        while time.time() - wait_start < max_wait:
            status = self.get_order_status(order_id)
            status_val = status.get("status")
            
            if status_val == "FILLED":
                executed_qty = float(status.get("executedQty", 0))
                cum_quote = float(status.get("cummulativeQuoteQty", 0))
                if executed_qty > 0:
                    fill_price = cum_quote / executed_qty if cum_quote > 0 else price
                    self.logger.info(f"✅ {side} order FILLED: {executed_qty:.8f} @ ${fill_price:.2f}")
                    return {
                        "orderId": order_id,
                        "price": str(fill_price),
                        "executedQty": str(executed_qty),
                        "status": "FILLED",
                        "side": side,
                    }
            
            if status_val == "CANCELED" or status_val == "EXPIRED":
                self.logger.error(f"❌ {side} order was {status_val}")
                return {"error": f"Order {status_val}"}
            
            time.sleep(2)
        
        status = self.get_order_status(order_id)
        executed_qty = float(status.get("executedQty", 0))
        cum_quote = float(status.get("cummulativeQuoteQty", 0))
        if executed_qty > 0:
            fill_price = cum_quote / executed_qty if cum_quote > 0 else price
            self.logger.info(f"⚠️ Partial fill: {executed_qty:.8f} @ ${fill_price:.2f}")
            return {
                "orderId": order_id,
                "price": str(fill_price),
                "executedQty": str(executed_qty),
                "status": "PARTIALLY_FILLED",
                "side": side,
            }
        
        return {"error": "Order fill timeout"}

    def place_limit_order(self, side: str, quantity: float, price: float) -> dict:
        if quantity <= 0:
            return {"error": "Invalid quantity", "code": -1003}
        
        if side.upper() == "SELL":
            self._update_balances()
            if self.current_balance_asset < quantity * 0.99:
                self.logger.error(f"❌ Insufficient {self.base_asset}: {self.current_balance_asset:.8f} (need {quantity:.8f})")
                return {"error": f"Insufficient {self.base_asset} balance", "code": -2010}
        
        qty = round_to_step(quantity, self._min_qty)
        if qty < self._min_qty:
            qty = self._min_qty
        
        limit_price = round_to_tick(price, self._tick_size)
        qty_str = format_quantity(qty)
        price_str = format_price(limit_price)
        
        self.logger.info(f"📊 Placing {side} LIMIT order: {qty_str} @ ${price_str}")
        
        params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "LIMIT",
            "quantity": qty_str,
            "price": price_str,
            "timeInForce": "GTC",
        }
        
        response = self._send_signed_request("POST", "/api/v3/order", params)
        if "error" in response:
            return response
        
        return {
            "orderId": response.get("orderId"),
            "price": str(response.get("price", limit_price)),
            "origQty": str(response.get("origQty", qty)),
            "status": response.get("status", "NEW"),
            "side": side,
        }

    def check_market(self) -> Dict:
        """Get market data and analyze entry signal"""
        klines = TechnicalIndicators.get_klines(
            self.symbol, self.base_url, 
            interval=self.config["interval"], 
            limit=100
        )
        if not klines:
            return {"error": "No data"}
        
        signal = self.strategy.check_entry_signal(klines)
        
        # Also get current price
        current_price = self.get_current_price()
        if current_price:
            signal["current_price"] = current_price
        
        return signal

    def execute_dca_buy(self) -> Dict:
        """Execute a DCA buy order"""
        # Check if we've reached max levels
        if self.strategy.current_level >= self.config["max_buy_levels"]:
            return {"success": False, "error": "Max DCA levels reached"}
        
        # Check if we have enough USDT
        self._update_balances()
        
        # Calculate buy amount
        buy_usdt = self.strategy.calculate_buy_amount(self.strategy.current_level)
        
        # Check if this would exceed max total
        if self.strategy.total_cost + buy_usdt > self.config["max_total_usdt"]:
            buy_usdt = self.config["max_total_usdt"] - self.strategy.total_cost
            if buy_usdt < self.config["base_order_usdt"]:
                return {"success": False, "error": "Not enough room for another DCA"}
        
        # Place buy order
        self.logger.info(f"💰 DCA Level {self.strategy.current_level + 1}: Buying ${buy_usdt:.2f}")
        buy_order = self.place_market_order(side="BUY", amount=buy_usdt, is_quantity=False)
        
        if "error" in buy_order:
            return {"success": False, "error": buy_order.get("error", "Buy failed")}
        
        buy_price = float(buy_order.get("price", 0))
        buy_qty = float(buy_order.get("executedQty", 0))
        
        if buy_qty <= 0 or buy_price <= 0:
            return {"success": False, "error": "Invalid buy"}
        
        # Update strategy state
        self.strategy.total_qty += buy_qty
        self.strategy.total_cost += buy_usdt
        self.strategy.avg_price = self.strategy.total_cost / self.strategy.total_qty
        self.strategy.last_buy_price = buy_price
        self.strategy.current_level += 1
        self.strategy.position_open = True
        self.strategy.entry_time = datetime.now()
        
        # Update highest price for trailing stop
        if buy_price > self.strategy.highest_price:
            self.strategy.highest_price = buy_price
            self.strategy.trailing_stop = buy_price * (1 - self.config["trailing_stop_pct"] / 100 * 2)
        
        self.has_open_position = True
        self.total_invested += buy_usdt
        
        self.logger.info(f"✅ DCA BUY {self.strategy.current_level}: {buy_qty:.8f} @ ${buy_price:.2f}")
        self.logger.info(f"   Avg Price: ${self.strategy.avg_price:.2f}, Total: {self.strategy.total_qty:.8f}")
        
        return {
            "success": True,
            "level": self.strategy.current_level,
            "price": buy_price,
            "quantity": buy_qty,
            "avg_price": self.strategy.avg_price,
            "total_qty": self.strategy.total_qty,
            "total_cost": self.strategy.total_cost,
        }

    def exit_position(self, exit_price: float) -> Dict:
        """Exit the entire position at market price"""
        if self.strategy.total_qty <= 0:
            return {"success": False, "error": "No position to exit"}
        
        self.logger.info(f"📊 Exiting position: {self.strategy.total_qty:.8f} @ ${exit_price:.2f}")
        
        # Sell all
        sell_order = self.place_market_order(side="SELL", amount=self.strategy.total_qty, is_quantity=True)
        
        if "error" in sell_order:
            return {"success": False, "error": sell_order.get("error", "Sell failed")}
        
        sell_price = float(sell_order.get("price", exit_price))
        sell_qty = float(sell_order.get("executedQty", self.strategy.total_qty))
        
        if sell_qty <= 0:
            return {"success": False, "error": "Invalid sell"}
        
        # Calculate P&L
        realized_pnl = (sell_price - self.strategy.avg_price) * sell_qty
        fee_estimate = (sell_qty * self.strategy.avg_price * self.maker_fee_rate) + (sell_qty * sell_price * self.taker_fee_rate)
        net_pnl = realized_pnl - fee_estimate
        
        self.logger.info(f"💰 P&L: ${realized_pnl:.4f} (net: ${net_pnl:.4f})")
        
        # Update stats
        self.running_pnl += net_pnl
        self.current_balance_usdt = max(0, self.starting_balance + self.running_pnl)
        self.total_trades += 1
        
        if net_pnl > 0:
            self.win_count += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            if self.current_balance_usdt > self.peak_balance:
                self.peak_balance = self.current_balance_usdt
        else:
            self.loss_count += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        
        # Reset strategy for next cycle
        self.strategy.reset()
        self.has_open_position = False
        self.position_order_id = None
        
        self._update_balances()
        
        return {
            "success": True,
            "entry_price": self.strategy.avg_price,
            "exit_price": sell_price,
            "quantity": sell_qty,
            "profit": realized_pnl,
            "net_profit": net_pnl,
            "fees": fee_estimate,
            "balance_after": self.current_balance_usdt,
            "win_rate": win_rate,
        }

    def run_cycle(self, cycle_number: int = 0) -> dict:
        if self.stopped:
            return {"success": False, "error": "Bot stopped"}
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔄 CYCLE {cycle_number} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'='*60}")

        # Update balances
        self._update_balances()
        
        # Get current price
        current_price = self.get_current_price()
        if not current_price:
            return {"success": False, "error": "No price", "skipped": True}
        
        self.logger.info(f"💰 USDT: ${self.current_balance_usdt:.2f} | {self.base_asset}: {self.current_balance_asset:.8f}")
        self.logger.info(f"📊 Price: ${current_price:.4f}")
        
        # Check if we have an open position
        if self.has_open_position or self.strategy.position_open:
            # Check exit conditions
            exit_check = self.strategy.check_exit_signal(current_price)
            
            self.logger.info(f"📊 Position OPEN - Avg: ${self.strategy.avg_price:.2f}, Qty: {self.strategy.total_qty:.8f}")
            self.logger.info(f"   Current: ${current_price:.2f} ({exit_check.get('profit_pct', 0)*100:.2f}% P&L)")
            if self.strategy.trailing_stop > 0:
                self.logger.info(f"   Trailing Stop: ${self.strategy.trailing_stop:.2f}")
            
            if exit_check.get('exit', False):
                self.logger.info(f"🚪 {exit_check.get('reason', 'Exit triggered')}")
                result = self.exit_position(current_price)
                if result.get('success', False):
                    self.logger.info(f"✅ EXIT COMPLETE! Net: ${result.get('net_profit', 0):.4f}")
                    return {"success": True, **result}
                else:
                    self.logger.error(f"❌ Exit failed: {result.get('error', 'Unknown')}")
                    return {"success": False, "error": result.get('error', 'Exit failed')}
            
            # Check if we should DCA more (price dropped further)
            if self.strategy.current_level < self.config["max_buy_levels"]:
                # Check if price dropped enough from last buy
                if self.strategy.last_buy_price > 0:
                    drop_from_last = (self.strategy.last_buy_price - current_price) / self.strategy.last_buy_price
                    if drop_from_last >= self.config["price_drop_pct"] * 0.8:  # 80% of initial drop
                        self.logger.info(f"📉 Price dropped {drop_from_last*100:.2f}% from last buy")
                        self.logger.info(f"🔄 Executing DCA Level {self.strategy.current_level + 1}")
                        dca_result = self.execute_dca_buy()
                        if dca_result.get('success', False):
                            self.logger.info(f"✅ DCA BUY COMPLETE! Level {dca_result.get('level', 0)}")
                            return {"success": True, "dca": True, **dca_result}
            
            # Position still open
            return {"success": False, "error": "Position open", "skipped": True}
        
        # No position - check for new entry signal
        signal = self.check_market()
        
        if "error" in signal:
            self.logger.warning(f"⚠️ {signal['error']}")
            return {"success": False, "error": signal['error'], "skipped": True}
        
        # Log current conditions
        rsi = signal.get('rsi', 50)
        price_drop = signal.get('price_drop', 0)
        macd_bullish = signal.get('macd_bullish', False)
        volume_ratio = signal.get('volume_ratio', 1)
        
        self.logger.info(f"📊 RSI: {rsi:.1f} {'✅' if rsi < self.config['rsi_oversold'] else '❌'}")
        self.logger.info(f"   Price Drop: {price_drop*100:.2f}% {'✅' if price_drop >= self.config['price_drop_pct'] else '❌'}")
        self.logger.info(f"   MACD: {'✅ Bullish' if macd_bullish else '❌ Bearish'}")
        self.logger.info(f"   Volume Ratio: {volume_ratio:.2f}x {'✅' if volume_ratio >= self.config['min_volume_ratio'] else '❌'}")
        
        if not signal.get('entry', False):
            self.logger.info("⏭️ No entry signal - waiting for conditions")
            return {"success": False, "error": "No signal", "skipped": True}
        
        # ENTRY SIGNAL!
        self.logger.info("🚀 ENTRY SIGNAL DETECTED!")
        self.logger.info(f"   RSI: {rsi:.1f} (oversold)")
        self.logger.info(f"   Price Drop: {price_drop*100:.2f}%")
        
        # Reset strategy for new cycle
        self.strategy.reset()
        
        # Execute first DCA buy
        dca_result = self.execute_dca_buy()
        
        if not dca_result.get('success', False):
            self.logger.error(f"❌ Entry failed: {dca_result.get('error', 'Unknown')}")
            return {"success": False, "error": dca_result.get('error', 'Entry failed')}
        
        self.logger.info(f"✅ ENTRY COMPLETE! Level {dca_result.get('level', 0)}")
        self.logger.info(f"   Avg Price: ${self.strategy.avg_price:.2f}, Qty: {self.strategy.total_qty:.8f}")
        
        # Place take-profit limit order
        take_profit_price = self.strategy.avg_price * (1 + self.config["take_profit_pct"])
        take_profit_price = round_to_tick(take_profit_price, self._tick_size)
        
        self.logger.info(f"🎯 Take Profit: ${take_profit_price:.2f} (+{self.config['take_profit_pct']*100:.1f}%)")
        
        sell_order = self.place_limit_order(
            side="SELL",
            quantity=self.strategy.total_qty,
            price=take_profit_price
        )
        
        if "error" in sell_order:
            self.logger.error(f"❌ Take profit order failed: {sell_order}")
            # Try market sell as fallback
            self.logger.info("🔄 Trying market sell as fallback...")
            exit_result = self.exit_position(self.get_current_price() or self.strategy.avg_price)
            if exit_result.get('success', False):
                return {"success": True, **exit_result}
            return {"success": False, "error": "Sell failed"}
        
        self.position_order_id = sell_order.get("orderId")
        self.has_open_position = True
        
        self.logger.info(f"✅ SELL LIMIT order placed: {self.position_order_id}")
        self.logger.info(f"⏳ Position open - waiting for target ${take_profit_price:.2f}")
        self.logger.info(f"   Max DCA Levels: {self.config['max_buy_levels']}")

        return {"success": True, "position_open": True, "order_id": self.position_order_id}

    def run_forever(self):
        self.logger.info("\n" + "="*70)
        self.logger.info("🚀 HYBRID DCA + RSI/MACD BOT - RUNNING")
        self.logger.info(f"   {self.symbol} - Checking every {self.config['interval']}")
        self.logger.info("   Press Ctrl+C to stop")
        self.logger.info("="*70)

        self.cycle_stats["start_time"] = datetime.now()
        cycle_num = 1
        
        while not self.stopped:
            try:
                result = self.run_cycle(cycle_number=cycle_num)
                
                if result.get("success", False):
                    if result.get("position_open", False) or result.get("dca", False):
                        self.logger.info(f"📊 Position/DCA updated - monitoring...")
                    else:
                        self.logger.info(f"✅ TRADE COMPLETED! Net: ${result.get('net_profit', 0):.4f}")
                elif result.get("skipped", False):
                    if self.has_open_position or self.strategy.position_open:
                        self.logger.info(f"⏳ Position open - monitoring...")
                    else:
                        self.logger.info(f"⏭️ Waiting for signal...")
                else:
                    self.logger.error(f"⚠️ Failed: {result.get('error', 'Unknown')}")
                
                if self.total_trades > 0:
                    win_rate = (self.win_count / self.total_trades) * 100
                    self.logger.info(f"📊 STATS: {self.total_trades} trades, {win_rate:.1f}% win, ${self.cycle_stats['net_profit']:.4f}")
                
                # Always check every minute (like a true DCA bot)
                wait_time = 60
                self.logger.info(f"⏳ Next check in {wait_time}s")
                time.sleep(wait_time)
                cycle_num += 1
                
            except KeyboardInterrupt:
                self.logger.info("⚠️ Stopped by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(60)
                cycle_num += 1

        self.cycle_stats["end_time"] = datetime.now()
        self.print_final_summary()

    def print_final_summary(self):
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        self.logger.info("\n" + "="*70)
        self.logger.info("🏆 DCA STRATEGY - FINAL SUMMARY")
        self.logger.info("="*70)
        self.logger.info(f"📊 Trades: {self.total_trades} | Wins: {self.win_count} | Losses: {self.loss_count}")
        self.logger.info(f"📊 Win Rate: {win_rate:.1f}%")
        self.logger.info(f"💰 Start: ${self.starting_balance:.2f} | Final: ${self.current_balance_usdt:.2f}")
        self.logger.info(f"💰 Net Profit: ${self.cycle_stats['net_profit']:.4f}")
        if self.starting_balance > 0:
            roi = (self.cycle_stats['net_profit'] / self.starting_balance) * 100
            self.logger.info(f"📊 ROI: {roi:.1f}%")
        self.logger.info("="*70)

# ========================================================================
# MAIN
# ========================================================================

if __name__ == "__main__":
    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"
    
    if not API_KEY or not API_SECRET:
        print("❌ API KEYS NOT FOUND!")
        exit(1)
    
    print("="*70)
    print("🚀 HYBRID DCA + RSI/MACD BOT v1.0")
    print("="*70)
    print(f"\n🎯 {DCA_CONFIG['symbol']} - 1 Minute Check")
    print(f"   ✅ Price Drop: {DCA_CONFIG['price_drop_pct']*100:.1f}%")
    print(f"   ✅ RSI Oversold: < {DCA_CONFIG['rsi_oversold']}")
    print(f"   ✅ Take Profit: {DCA_CONFIG['take_profit_pct']*100:.1f}%")
    print(f"   ✅ Max DCA Levels: {DCA_CONFIG['max_buy_levels']}")
    print(f"   ✅ Martingale: {DCA_CONFIG['martingale_multiplier']}x scaling")
    print(f"\n🚀 Starting in 3 seconds...")
    time.sleep(3)
    
    bot = DCABot(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol=DCA_CONFIG["symbol"],
        exchange_region="us",
        log_level="INFO"
    )
    
    bot.run_forever()
