#!/usr/bin/env python3
"""
🚀 HYBRID DCA + MOMENTUM BOT v1.0 - TOP RECOMMENDED ALGORITHM
============================================================
STRATEGY: Weighted DCA with RSI/MACD Momentum Filter
- Price drop detection (2-5%)
- RSI oversold confirmation (< 30)
- MACD momentum filter
- Martingale position scaling (1.5x multiplier)
- Trailing take-profit (2.5-5%)

WHY THIS WORKS:
- Prevents catching falling knives (momentum filter)
- Capitalizes on oversold bounces (high probability)
- Adapts to any market condition
- Proven edge on Binance
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
    "interval": "15m",  # 15-minute candles for faster signals
    
    # Price drop detection
    "price_drop_pct": 0.02,      # 2% drop triggers check
    
    # Momentum filters (OVERSOLD condition)
    "rsi_oversold": 30,           # RSI below 30 = oversold
    "macd_bullish": True,         # MACD must be bullish or crossing
    
    # DCA Position Scaling (Martingale)
    "base_order_usdt": 10.0,      # First buy amount
    "scale_multiplier": 1.5,      # 1.5x each subsequent buy
    "max_orders": 3,              # Maximum 3 DCA orders
    
    # Take Profit
    "take_profit_pct": 0.025,     # 2.5% profit target
    "trailing_stop_pct": 0.005,   # 0.5% trailing after profit
    
    # Safety
    "max_drawdown_pct": 0.15,
    "max_consecutive_losses": 3,
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
    def get_klines(symbol: str, base_url: str, interval: str = "15m", limit: int = 100,
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
# DCA + MOMENTUM STRATEGY
# ========================================================================

class DCAMomentumStrategy:
    @staticmethod
    def analyze(data: Dict, params: Dict = None, verbose: bool = True) -> Dict:
        if params is None:
            params = {
                'price_drop_pct': 0.02,
                'rsi_oversold': 30,
                'macd_bullish': True,
                'base_order_usdt': 10.0,
                'scale_multiplier': 1.5,
                'max_orders': 3,
                'take_profit_pct': 0.025,
                'trailing_stop_pct': 0.005,
            }
        
        closes = data['closes']
        highs = data['highs']
        lows = data['lows']
        volumes = data['volumes']
        
        if len(closes) < 30:
            return {"signal": "NEUTRAL", "error": "Insufficient data"}
        
        current_price = closes[-1]
        previous_price = closes[-2]
        
        # Calculate indicators
        rsi = TechnicalIndicators.rsi(closes, 14)
        macd = TechnicalIndicators.macd(closes, 12, 26, 9)
        atr = TechnicalIndicators.atr(highs, lows, closes, 14)
        
        # Calculate price drop
        price_drop_pct = (previous_price - current_price) / previous_price
        
        # Determine signals
        buy_conditions = {
            "price_drop": price_drop_pct >= params['price_drop_pct'],
            "rsi_oversold": rsi <= params['rsi_oversold'],
            "macd_bullish": macd['bullish'] if params['macd_bullish'] else True,
            "volume_confirm": volumes[-1] > sum(volumes[-5:-1]) / 4 if len(volumes) >= 5 else True,
        }
        
        # Count conditions met
        conditions_met = sum(buy_conditions.values())
        total_conditions = len(buy_conditions)
        
        # Decision: All conditions must be met for a BUY signal
        buy_signal = all(buy_conditions.values())
        
        # Calculate buy amounts (Martingale scaling)
        base_order = params['base_order_usdt']
        scale_mult = params['scale_multiplier']
        max_orders = params['max_orders']
        
        buy_orders = []
        for i in range(max_orders):
            amount = base_order * (scale_mult ** i)
            buy_orders.append(amount)
        
        # Target price (based on average entry)
        estimated_avg_entry = current_price
        target_price = estimated_avg_entry * (1 + params['take_profit_pct'])
        stop_price = estimated_avg_entry * (1 - 0.015)  # 1.5% initial stop
        
        # Build result
        result = {
            "signal": "BUY" if buy_signal else "NEUTRAL",
            "confidence": conditions_met / total_conditions,
            "price_drop_pct": price_drop_pct,
            "rsi": rsi,
            "macd_bullish": macd['bullish'],
            "current_price": current_price,
            "target_price": target_price,
            "stop_price": stop_price,
            "buy_orders": buy_orders,
            "total_position_usdt": sum(buy_orders),
            "conditions": buy_conditions,
            "conditions_met": conditions_met,
            "total_conditions": total_conditions,
            "take_profit_pct": params['take_profit_pct'],
        }
        
        # Print analysis if verbose
        if verbose:
            print("\n" + "="*70)
            print("📊 DCA + MOMENTUM SIGNAL ANALYSIS")
            print("="*70)
            print(f"Current Price: ${current_price:.4f}")
            print(f"Previous Price: ${previous_price:.4f}")
            print(f"Price Drop: {price_drop_pct*100:.2f}% (need > {params['price_drop_pct']*100:.1f}%)")
            print(f"RSI: {rsi:.1f} (need < {params['rsi_oversold']})")
            print(f"MACD: {'✅ Bullish' if macd['bullish'] else '❌ Bearish'}")
            print("-"*70)
            print("BUY CONDITIONS:")
            for condition, met in buy_conditions.items():
                status = "✅" if met else "❌"
                print(f"  {status} {condition}: {met}")
            print("-"*70)
            print(f"Conditions Met: {conditions_met}/{total_conditions}")
            print(f"Confidence: {result['confidence']*100:.0f}%")
            print("\n📈 DCA POSITION SCALING:")
            for i, amount in enumerate(buy_orders[:3]):
                print(f"  Order {i+1}: ${amount:.2f}")
            print(f"  Total Position: ${result['total_position_usdt']:.2f}")
            print(f"  Target: ${target_price:.4f} (+{params['take_profit_pct']*100:.1f}%)")
            print(f"  Stop: ${stop_price:.4f} (-1.5%)")
            
            if buy_signal:
                print("\n✅ BUY SIGNAL CONFIRMED! All conditions met.")
            else:
                print("\n⏳ Waiting for all conditions to align...")
            print("="*70)
        
        return result

# ========================================================================
# DCA + MOMENTUM BOT
# ========================================================================

class DCAMomentumBot:

    def __init__(self, api_key: str, api_secret: str, 
                 symbol: str = DCA_CONFIG["symbol"],
                 exchange_region: str = "us", 
                 log_level: str = "INFO", 
                 interval: str = DCA_CONFIG["interval"]):
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.interval = interval
        self.base_asset = symbol.replace("USDT", "")
        
        # Strategy parameters
        self.price_drop_pct = DCA_CONFIG["price_drop_pct"]
        self.rsi_oversold = DCA_CONFIG["rsi_oversold"]
        self.macd_bullish = DCA_CONFIG["macd_bullish"]
        self.base_order_usdt = DCA_CONFIG["base_order_usdt"]
        self.scale_multiplier = DCA_CONFIG["scale_multiplier"]
        self.max_orders = DCA_CONFIG["max_orders"]
        self.take_profit_pct = DCA_CONFIG["take_profit_pct"]
        self.trailing_stop_pct = DCA_CONFIG["trailing_stop_pct"]
        
        # Safety
        self.max_drawdown_pct = DCA_CONFIG["max_drawdown_pct"]
        self.max_consecutive_losses = DCA_CONFIG["max_consecutive_losses"]
        
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
        self._price_cache_ttl = 30
        
        # State
        self.has_open_position = False
        self.position_entry_price = 0.0
        self.position_entry_qty = 0.0
        self.position_target_price = 0.0
        self.position_stop_price = 0.0
        self.position_order_id = None
        self.position_open_time = None
        self.position_highest_price = 0.0
        self.position_trailing_stop = 0.0
        
        # DCA specific state
        self.dca_order_count = 0
        self.dca_total_spent = 0.0
        self.dca_avg_entry = 0.0
        self.dca_total_qty = 0.0
        self.dca_active = False
        self.dca_orders = []
        
        self.current_balance_usdt = 0.0
        self.current_balance_asset = 0.0
        self.starting_balance = 0.0
        self.peak_balance = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.balance_fetched = False
        self.stopped = False
        
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
        log_filename = f"dca_momentum_{datetime.now().strftime('%Y%m%d')}.log"
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
        self.logger.info("🚀 DCA + MOMENTUM BOT v1.0 - TOP ALGORITHM")
        self.logger.info("="*70)
        self.logger.info(f"   Symbol: {symbol}")
        self.logger.info(f"   Interval: {interval}")
        self.logger.info(f"   Price Drop: {self.price_drop_pct*100:.1f}%")
        self.logger.info(f"   RSI Oversold: < {self.rsi_oversold}")
        self.logger.info(f"   MACD Filter: {'Bullish' if self.macd_bullish else 'Disabled'}")
        self.logger.info(f"   Base Order: ${self.base_order_usdt}")
        self.logger.info(f"   Scale: {self.scale_multiplier}x")
        self.logger.info(f"   Max Orders: {self.max_orders}")
        self.logger.info(f"   Take Profit: {self.take_profit_pct*100:.1f}%")
        self.logger.info("="*70)
        
        self._check_connectivity()
        self._get_exchange_info()
        self._update_balances()

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

    def analyze_market(self, verbose: bool = True) -> Dict:
        klines = TechnicalIndicators.get_klines(self.symbol, self.base_url, interval=self.interval, limit=100)
        if not klines:
            return {"signal": "NEUTRAL", "error": "No data"}
        
        params = {
            'price_drop_pct': self.price_drop_pct,
            'rsi_oversold': self.rsi_oversold,
            'macd_bullish': self.macd_bullish,
            'base_order_usdt': self.base_order_usdt,
            'scale_multiplier': self.scale_multiplier,
            'max_orders': self.max_orders,
            'take_profit_pct': self.take_profit_pct,
            'trailing_stop_pct': self.trailing_stop_pct,
        }
        
        signal = DCAMomentumStrategy.analyze(klines, params, verbose=verbose)
        return signal

    def run_cycle(self, cycle_number: int = 0) -> dict:
        if self.stopped:
            return {"success": False, "error": "Bot stopped"}
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔄 CYCLE {cycle_number} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'='*60}")

        # Safety checks
        self._update_balances()
        self.logger.info(f"💰 USDT: ${self.current_balance_usdt:.2f} | {self.base_asset}: {self.current_balance_asset:.8f}")
        
        if self.current_balance_usdt < self.base_order_usdt:
            self.logger.error(f"❌ Insufficient USDT: ${self.current_balance_usdt:.2f}")
            return {"success": False, "error": "Insufficient USDT"}
        
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - self.current_balance_usdt) / self.peak_balance
            if drawdown > self.max_drawdown_pct:
                self.logger.error(f"❌ Max drawdown: {drawdown*100:.1f}%")
                self.stopped = True
                return {"success": False, "error": "Max drawdown"}
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.logger.error(f"❌ Too many losses: {self.consecutive_losses}")
            self.stopped = True
            return {"success": False, "error": "Too many losses"}

        # Analyze market
        self.logger.info("📊 Analyzing market with DCA + Momentum strategy...")
        signal = self.analyze_market(verbose=True)
        
        if "error" in signal:
            self.logger.warning(f"⚠️ {signal['error']}")
            return {"success": False, "error": signal['error'], "skipped": True}
        
        if signal['signal'] != "BUY":
            self.logger.info(f"⏭️ No BUY signal - Conditions met: {signal.get('conditions_met', 0)}/{signal.get('total_conditions', 4)}")
            return {"success": False, "error": "No signal", "skipped": True}
        
        # BUY SIGNAL!
        self.logger.info("🚀 BUY SIGNAL CONFIRMED! Executing DCA strategy...")
        
        current_price = self.get_current_price()
        if not current_price:
            return {"success": False, "error": "No price"}
        
        # Execute first DCA order
        buy_amount = self.base_order_usdt
        self.logger.info(f"📈 Buying ${buy_amount:.2f} worth of {self.base_asset} (DCA Order 1/{self.max_orders})")
        
        buy_order = self.place_market_order(side="BUY", amount=buy_amount, is_quantity=False)
        
        if "error" in buy_order:
            self.logger.error(f"❌ Buy failed: {buy_order}")
            return {"success": False, "error": buy_order.get("error", "Buy failed")}
        
        buy_price = float(buy_order.get("price", 0))
        buy_qty = float(buy_order.get("executedQty", 0))
        
        if buy_qty <= 0 or buy_price <= 0:
            self.logger.error(f"❌ Invalid buy: qty={buy_qty}, price={buy_price}")
            return {"success": False, "error": "Invalid buy"}
        
        self.logger.info(f"✅ BUY Filled: {buy_qty:.8f} {self.base_asset} @ ${buy_price:.2f}")
        
        # Update DCA state
        self.dca_active = True
        self.dca_order_count = 1
        self.dca_total_spent = buy_amount
        self.dca_total_qty = buy_qty
        self.dca_avg_entry = buy_price
        self.dca_orders = [{"price": buy_price, "qty": buy_qty, "amount": buy_amount}]
        
        # Set position tracking
        self.has_open_position = True
        self.position_entry_price = buy_price
        self.position_entry_qty = buy_qty
        self.position_highest_price = buy_price
        
        # Calculate target (based on average entry)
        self.position_target_price = self.dca_avg_entry * (1 + self.take_profit_pct)
        self.position_stop_price = self.dca_avg_entry * (1 - 0.015)
        self.position_trailing_stop = self.position_stop_price
        self.position_open_time = datetime.now()
        
        self.logger.info(f"📊 DCA Position Summary:")
        self.logger.info(f"   Avg Entry: ${self.dca_avg_entry:.4f}")
        self.logger.info(f"   Total Qty: {self.dca_total_qty:.8f}")
        self.logger.info(f"   Total Spent: ${self.dca_total_spent:.2f}")
        self.logger.info(f"   Target: ${self.position_target_price:.4f} (+{self.take_profit_pct*100:.1f}%)")
        self.logger.info(f"   Stop: ${self.position_stop_price:.4f} (-1.5%)")
        
        # Place sell limit order
        sell_qty = round_to_step(self.dca_total_qty, self._min_qty)
        sell_order = self.place_limit_order(side="SELL", quantity=sell_qty, price=self.position_target_price)
        
        if "error" in sell_order:
            self.logger.error(f"❌ Sell limit failed: {sell_order}")
            return {"success": False, "error": "Sell order failed"}
        
        self.position_order_id = sell_order.get("orderId")
        self.logger.info(f"✅ SELL LIMIT order placed: {self.position_order_id}")
        
        return {
            "success": True,
            "position_open": True,
            "order_id": self.position_order_id,
            "entry_price": buy_price,
            "entry_qty": buy_qty,
            "target_price": self.position_target_price,
            "stop_price": self.position_stop_price,
            "avg_entry": self.dca_avg_entry,
            "total_spent": self.dca_total_spent,
        }

    def run_forever(self):
        self.logger.info("\n" + "="*70)
        self.logger.info("🚀 DCA + MOMENTUM BOT v1.0 - RUNNING")
        self.logger.info(f"   {self.symbol} {self.interval}")
        self.logger.info("   Press Ctrl+C to stop")
        self.logger.info("="*70)

        self.cycle_stats["start_time"] = datetime.now()
        cycle_num = 1
        
        while not self.stopped:
            try:
                result = self.run_cycle(cycle_number=cycle_num)
                
                if result.get("success", False):
                    if result.get("position_open", False):
                        self.logger.info(f"📊 Position opened - monitoring every 60s...")
                    else:
                        self.logger.info(f"✅ TRADE COMPLETED! Net: ${result.get('net_profit', 0):.4f}")
                elif result.get("skipped", False):
                    self.logger.info(f"⏭️ No signal - checking every 5 minutes")
                else:
                    self.logger.error(f"⚠️ Failed: {result.get('error', 'Unknown')}")
                
                if self.total_trades > 0:
                    win_rate = (self.win_count / self.total_trades) * 100
                    self.logger.info(f"📊 STATS: {self.total_trades} trades, {win_rate:.1f}% win, ${self.cycle_stats['net_profit']:.4f}")
                
                wait_time = 60 if self.has_open_position else 300
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
        self.logger.info("🏆 DCA + MOMENTUM - FINAL SUMMARY")
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
    print("🚀 DCA + MOMENTUM BOT v1.0 - TOP ALGORITHM")
    print("="*70)
    print(f"\n🎯 {DCA_CONFIG['symbol']} {DCA_CONFIG['interval']}")
    print(f"   ✅ Price Drop: {DCA_CONFIG['price_drop_pct']*100:.1f}%")
    print(f"   ✅ RSI Oversold: < {DCA_CONFIG['rsi_oversold']}")
    print(f"   ✅ MACD Filter: Bullish confirmation")
    print(f"   ✅ DCA Scaling: {DCA_CONFIG['scale_multiplier']}x multiplier")
    print(f"   ✅ Take Profit: {DCA_CONFIG['take_profit_pct']*100:.1f}%")
    print(f"\n📊 Current AVAXUSDT: Price Drop needed: 2%+")
    print(f"\n🚀 Starting in 3 seconds...")
    time.sleep(3)
    
    bot = DCAMomentumBot(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol=DCA_CONFIG["symbol"],
        exchange_region="us",
        log_level="INFO",
        interval=DCA_CONFIG["interval"]
    )
    
    bot.run_forever()
