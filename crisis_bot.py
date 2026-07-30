#!/usr/bin/env python3
"""
🚀 GOLDEN SCALPER BOT v10.5 - FINAL WORKING
============================================================
FIXES:
- Fixed undefined sell_order_id variable
- Proper error handling for sell order failures
- Better balance tracking with ETH accumulation
- Only buy if ETH balance is low
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
# TECHNICAL ANALYSIS
# ========================================================================

class AdvancedTA:
    @staticmethod
    def get_klines(symbol: str, base_url: str, interval: str = "4h", limit: int = 500) -> Optional[Dict]:
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
        except Exception:
            return None
    
    @staticmethod
    def calculate_rsi(closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        gains, losses = [], []
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
        return 100 - (100 / (1 + rs))
    
    @staticmethod
    def calculate_ema(closes: List[float], period: int) -> float:
        if not closes:
            return 0
        if len(closes) < period:
            return sum(closes) / len(closes)
        multiplier = 2 / (period + 1)
        ema = sum(closes[:period]) / period
        for price in closes[period:]:
            ema = (price * multiplier) + (ema * (1 - multiplier))
        return ema
    
    @staticmethod
    def calculate_macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        if len(closes) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0, "bullish": False}
        ema_fast = AdvancedTA.calculate_ema(closes, fast)
        ema_slow = AdvancedTA.calculate_ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = AdvancedTA.calculate_ema([macd_line], signal)
        histogram = macd_line - signal_line
        return {"macd": macd_line, "signal": signal_line, "histogram": histogram, "bullish": macd_line > signal_line}
    
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
        return sum(tr_values[-period:]) / period
    
    @staticmethod
    def calculate_bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2) -> Dict:
        if len(closes) < period:
            return {"upper": closes[-1] if closes else 0, "middle": closes[-1] if closes else 0, "lower": closes[-1] if closes else 0}
        middle = sum(closes[-period:]) / period
        squared_deviations = [(x - middle) ** 2 for x in closes[-period:]]
        std = (sum(squared_deviations) / period) ** 0.5
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        position = (closes[-1] - lower) / (upper - lower) if upper != lower else 0.5
        return {"upper": upper, "middle": middle, "lower": lower, "position": position}
    
    @staticmethod
    def calculate_adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 25.0
        plus_dm, minus_dm, tr = [], [], []
        for i in range(1, len(closes)):
            up = highs[i] - highs[i-1]
            down = lows[i-1] - lows[i]
            plus_dm.append(up if up > down and up > 0 else 0)
            minus_dm.append(down if down > up and down > 0 else 0)
            tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
        tr_ema = AdvancedTA.calculate_ema(tr[-period:], period)
        if tr_ema == 0:
            return 25.0
        plus_di = 100 * (AdvancedTA.calculate_ema(plus_dm[-period:], period) / tr_ema)
        minus_di = 100 * (AdvancedTA.calculate_ema(minus_dm[-period:], period) / tr_ema)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        return AdvancedTA.calculate_ema([dx] * period, period)

# ========================================================================
# STRATEGIES
# ========================================================================

class StrategyBreakout:
    name = "Breakout"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows = data['closes'], data['highs'], data['lows']
        current = closes[-1]
        donchian_high = max(highs[-20:])
        donchian_low = min(lows[-20:])
        adx = AdvancedTA.calculate_adx(highs, lows, closes, 14)
        rsi = AdvancedTA.calculate_rsi(closes, 14)
        buy = 0
        if current > donchian_high: buy += 1
        if adx > 25: buy += 1
        if rsi < 70: buy += 1
        if current > AdvancedTA.calculate_ema(closes, 50): buy += 1
        confidence = buy / 4
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence, "stop": donchian_low, "target": current + (current - donchian_low) * 1.5}

class StrategyMeanReversion:
    name = "MeanRev"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows, volumes = data['closes'], data['highs'], data['lows'], data['volumes']
        current = closes[-1]
        bb = AdvancedTA.calculate_bollinger_bands(closes, 20, 2)
        rsi = AdvancedTA.calculate_rsi(closes, 14)
        atr = AdvancedTA.calculate_atr(highs, lows, closes, 14)
        vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        buy = 0
        if current < bb['lower'] * 1.02: buy += 1
        if 20 < rsi < 40: buy += 1
        if volumes[-1] > vol_avg * 1.2: buy += 1
        if current < AdvancedTA.calculate_ema(closes, 20): buy += 1
        confidence = buy / 4
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence, "stop": current - atr * 1.5, "target": current + (bb['middle'] - bb['lower']) * 0.5}

class StrategyTrendFollowing:
    name = "Trend"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes = data['closes']
        current = closes[-1]
        macd = AdvancedTA.calculate_macd(closes, 12, 26, 9)
        ema9 = AdvancedTA.calculate_ema(closes, 9)
        ema21 = AdvancedTA.calculate_ema(closes, 21)
        ema50 = AdvancedTA.calculate_ema(closes, 50)
        rsi = AdvancedTA.calculate_rsi(closes, 14)
        buy = 0
        if macd['bullish']: buy += 1
        if current > ema9 > ema21: buy += 1
        if current > ema50: buy += 1
        if 40 < rsi < 70: buy += 1
        confidence = buy / 4
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence, "stop": ema21 * 0.98, "target": current * 1.04}

class StrategyVolumeAccumulation:
    name = "VolumeAcc"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows, volumes = data['closes'], data['highs'], data['lows'], data['volumes']
        current = closes[-1]
        vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        buy = 0
        if volumes[-1] > vol_avg * 1.1: buy += 1
        if current > AdvancedTA.calculate_ema(closes, 20): buy += 1
        if AdvancedTA.calculate_rsi(closes, 14) < 65: buy += 1
        confidence = buy / 3
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence, "stop": current * 0.97, "target": current * 1.05}

class EnsembleVoter:
    @staticmethod
    def analyze(data: Dict, min_votes: int = 1, min_confidence: float = 0.2) -> Dict:
        strategies = [StrategyBreakout(), StrategyMeanReversion(), StrategyTrendFollowing(), StrategyVolumeAccumulation()]
        signals, votes = [], []
        for strategy in strategies:
            try:
                result = strategy.signal(data)
                if result and result.get('signal') == "BUY":
                    signals.append({'name': strategy.name, 'confidence': result.get('confidence', 0), 
                                   'stop': result.get('stop'), 'target': result.get('target')})
                    votes.append(result.get('confidence', 0))
            except Exception:
                continue
        ensemble_buy = len(signals) >= min_votes
        avg_confidence = sum(votes) / len(votes) if votes else 0
        stops = [s['stop'] for s in signals if s.get('stop')]
        targets = [s['target'] for s in signals if s.get('target')]
        final_stop = statistics.median(stops) if stops else data['closes'][-1] * 0.97
        final_target = statistics.median(targets) if targets else data['closes'][-1] * 1.04
        return {
            "signal": "BUY" if ensemble_buy and avg_confidence >= min_confidence else "NEUTRAL",
            "confidence": avg_confidence,
            "votes": len(signals),
            "voting_strategies": [s['name'] for s in signals],
            "stop_price": final_stop,
            "target_price": final_target,
        }

# ========================================================================
# GOLDEN SCALPER BOT - FINAL WORKING
# ========================================================================

class GoldenScalperBot:

    def __init__(self, api_key: str, api_secret: str, 
                 symbol: str = "ETHUSDT", exchange_region: str = "us", 
                 log_level: str = "INFO", interval: str = "4h"):
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.interval = interval
        self.base_asset = symbol.replace("USDT", "")
        
        # Golden strategy parameters
        self.min_votes = 1
        self.min_confidence = 0.2
        
        # Position sizing
        self.min_order_usdt = 10.0
        self.max_order_usdt = 30.0
        
        # Target & Stop - Optimized for 4h
        self.target_profit_pct = 0.015  # 1.5% target
        self.stop_loss_pct = 0.008      # 0.8% stop (wider for 4h)
        
        # Safety
        self.max_drawdown_pct = 0.12
        self.max_consecutive_losses = 4
        
        # Exchange
        if exchange_region.lower() == "us":
            self.base_url = "https://api.binance.us"
        elif exchange_region.lower() == "global":
            self.base_url = "https://api.binance.com"
        else:
            raise ValueError('exchange_region must be "us" or "global"')
        
        self.maker_fee_rate = 0.001
        self.taker_fee_rate = 0.001
        
        # Cache
        self._min_qty = 0.00001
        self._tick_size = 0.01
        self._min_notional = 10.0
        self._price_cache = {}
        self._price_cache_time = 0
        self._price_cache_ttl = 60
        
        # State
        self.buy_price = None
        self.buy_qty = None
        self.current_balance_usdt = 0.0
        self.current_balance_eth = 0.0
        self.starting_balance = 0.0
        self.peak_balance = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.balance_fetched = False
        self.stopped = False
        self.skipped_count = 0
        self.in_position = False
        self.sell_order_id = None
        
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
        log_filename = f"golden_scalper_{datetime.now().strftime('%Y%m%d')}.log"
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
        self.logger.info("🏆 GOLDEN SCALPER BOT v10.5 - FINAL WORKING")
        self.logger.info("="*70)
        self.logger.info(f"   Symbol: {symbol}")
        self.logger.info(f"   Interval: {interval}")
        self.logger.info(f"   Target: {self.target_profit_pct*100:.1f}%")
        self.logger.info(f"   Stop: {self.stop_loss_pct*100:.1f}%")
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
                self.current_balance_eth = balances[self.base_asset]
            else:
                self.current_balance_eth = 0.0
            
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
            if self.current_balance_eth < quantity * 0.99:
                self.logger.error(f"❌ Insufficient {self.base_asset}: {self.current_balance_eth:.8f} (need {quantity:.8f})")
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

    def run_cycle(self, cycle_number: int = 0) -> dict:
        if self.stopped:
            return {"success": False, "error": "Bot stopped"}
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔄 CYCLE {cycle_number}")
        self.logger.info(f"{'='*60}")

        self._update_balances()
        
        self.logger.info(f"💰 USDT: ${self.current_balance_usdt:.2f} | {self.base_asset}: {self.current_balance_eth:.8f}")
        
        # Check if we already have too much ETH (position from previous cycle)
        if self.current_balance_eth > 0.01:  # More than 0.01 ETH (~$19)
            self.logger.info(f"⏭️ Already have {self.current_balance_eth:.8f} {self.base_asset} - waiting for sell")
            self.skipped_count += 1
            return {"success": False, "error": "Already in position", "skipped": True}
        
        if self.current_balance_usdt < self.min_order_usdt:
            self.logger.error(f"❌ Insufficient USDT: ${self.current_balance_usdt:.2f}")
            self.stopped = True
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

        # Get market data
        klines = AdvancedTA.get_klines(self.symbol, self.base_url, interval=self.interval, limit=500)
        if not klines:
            self.logger.warning("⚠️ No market data")
            self.skipped_count += 1
            return {"success": False, "error": "No data", "skipped": True}
        
        # Analyze
        signal = EnsembleVoter.analyze(klines, self.min_votes, self.min_confidence)
        
        self.logger.info(f"📊 Signal: {signal['signal']} | Confidence: {signal['confidence']:.2f} | Votes: {signal['votes']}")
        for strategy in signal.get('voting_strategies', []):
            self.logger.info(f"   ✅ {strategy} voted BUY")
        
        if signal['signal'] != "BUY":
            self.logger.info("⏭️ No signal - skipping")
            self.skipped_count += 1
            return {"success": False, "error": "No signal", "skipped": True}
        
        self.skipped_count = 0
        
        # Get current price
        current_price = self.get_current_price()
        if not current_price:
            return {"success": False, "error": "No price"}

        # Calculate position size - use less since we already have some ETH
        position_usdt = min(self.max_order_usdt, self.current_balance_usdt * 0.15)
        position_usdt = max(self.min_order_usdt, position_usdt)
        
        self.logger.info(f"📈 Buying ${position_usdt:.2f} worth of {self.base_asset}")
        
        # BUY
        buy_order = self.place_market_order(side="BUY", amount=position_usdt, is_quantity=False)
        
        if "error" in buy_order:
            self.logger.error(f"❌ Buy failed: {buy_order}")
            return {"success": False, "error": buy_order.get("error", "Buy failed")}
        
        self.buy_price = float(buy_order.get("price", 0))
        self.buy_qty = float(buy_order.get("executedQty", 0))
        
        if self.buy_qty <= 0 or self.buy_price <= 0:
            self.logger.error(f"❌ Invalid buy: qty={self.buy_qty}, price={self.buy_price}")
            return {"success": False, "error": "Invalid buy"}
        
        self.logger.info(f"✅ BUY Filled: {self.buy_qty:.8f} {self.base_asset} @ ${self.buy_price:.2f}")
        
        self._update_balances()
        self.logger.info(f"💰 After BUY - {self.base_asset}: {self.current_balance_eth:.8f}")

        # Calculate exit levels
        stop_price = max(self.buy_price * (1 - self.stop_loss_pct), signal['stop_price'])
        target_price = min(self.buy_price * (1 + self.target_profit_pct), signal['target_price'])
        
        # Use actual balance for selling - sell what we bought
        sell_qty = min(self.buy_qty, self.current_balance_eth * 0.995)
        sell_qty = round_to_step(sell_qty, self._min_qty)
        
        if sell_qty <= 0:
            self.logger.error(f"❌ No {self.base_asset} to sell")
            return {"success": False, "error": "No ETH to sell"}
        
        self.logger.info(f"📊 Selling {sell_qty:.8f} {self.base_asset}")
        self.logger.info(f"🎯 Target: ${target_price:.2f} (+{((target_price/self.buy_price)-1)*100:.2f}%)")
        self.logger.info(f"🛑 Stop: ${stop_price:.2f} (-{((1 - stop_price/self.buy_price))*100:.2f}%)")
        
        # Place SELL LIMIT order
        sell_order = self.place_limit_order(side="SELL", quantity=sell_qty, price=target_price)
        
        if "error" in sell_order:
            self.logger.error(f"❌ Sell limit failed: {sell_order}")
            self.logger.info("🔄 Trying market sell as fallback...")
            # Try market sell as fallback
            sell_order = self.place_market_order(side="SELL", amount=sell_qty, is_quantity=True)
            if "error" in sell_order:
                self.logger.error(f"❌ Market sell also failed: {sell_order}")
                return {"success": False, "error": "Sell failed"}
            exit_price = float(sell_order.get("price", current_price))
            self.logger.info(f"✅ Market SELL filled @ ${exit_price:.2f}")
            # Calculate P&L and exit early
            realized_pnl = (exit_price - self.buy_price) * sell_qty
            fee_estimate = (sell_qty * self.buy_price * self.maker_fee_rate) + (sell_qty * exit_price * self.taker_fee_rate)
            net_pnl = realized_pnl - fee_estimate
            self.total_fees += fee_estimate
            self._update_balances()
            
            self.logger.info(f"💰 P&L: ${realized_pnl:.4f} (net: ${net_pnl:.4f})")
            
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
            self.logger.info(f"📊 Win Rate: {win_rate:.1f}% ({self.win_count}W/{self.loss_count}L)")
            
            result = {
                "success": True,
                "cycle": cycle_number,
                "entry_price": self.buy_price,
                "exit_price": exit_price,
                "quantity": sell_qty,
                "profit": realized_pnl,
                "net_profit": net_pnl,
                "fees": fee_estimate,
                "profit_percent": (realized_pnl / (self.buy_price * sell_qty)) * 100 if self.buy_price * sell_qty > 0 else 0,
                "stopped_out": False,
                "balance_after": self.current_balance_usdt,
                "consecutive_wins": self.consecutive_wins,
                "consecutive_losses": self.consecutive_losses,
                "win_rate": win_rate,
                "timestamp": datetime.now().isoformat()
            }
            self.cycle_stats["total_cycles"] += 1
            if net_pnl > 0:
                self.cycle_stats["successful_cycles"] += 1
            else:
                self.cycle_stats["failed_cycles"] += 1
            self.cycle_stats["net_profit"] += net_pnl
            self.cycle_stats["cycle_results"].append(result)
            self.trade_history.append(result)
            return result
        
        self.sell_order_id = sell_order.get("orderId")
        if not self.sell_order_id:
            return {"success": False, "error": "No sell orderId"}
        
        self.logger.info(f"✅ SELL LIMIT order placed: {self.sell_order_id}")
        self.logger.info(f"⏳ Waiting for target price ${target_price:.2f} to be hit...")
        self.logger.info(f"   Order is GTC (Good 'til Canceled) - will stay active")
        self.logger.info(f"   Will cancel if stop-loss ${stop_price:.2f} is hit")
        
        # Monitor the position
        sell_filled = False
        stopped_out = False
        exit_price = target_price
        highest_price = self.buy_price
        check_interval = 30  # Check every 30 seconds for 4h
        max_checks = 2880  # 24 hours (30 * 2880 = 86400 seconds)
        checks = 0
        
        while not sell_filled and checks < max_checks:
            checks += 1
            
            # Check order status
            status = self.get_order_status(self.sell_order_id)
            status_val = status.get("status")
            
            if status_val == "FILLED":
                sell_filled = True
                cum_quote = float(status.get("cummulativeQuoteQty", 0))
                executed_qty = float(status.get("executedQty", 0))
                if executed_qty > 0 and cum_quote > 0:
                    exit_price = cum_quote / executed_qty
                else:
                    exit_price = float(status.get("price", target_price))
                self.logger.info(f"✅ SELL Filled @ ${exit_price:.2f}")
                break
            
            if status_val == "CANCELED" or status_val == "EXPIRED":
                self.logger.warning(f"⚠️ Sell order {status_val}")
                break
            
            # Check current price
            current_price = self.get_current_price()
            if current_price:
                if current_price > highest_price:
                    highest_price = current_price
                
                # Check stop-loss
                if current_price <= stop_price:
                    self.logger.warning(f"🛑 STOP-LOSS triggered: ${current_price:.2f}")
                    self.cancel_order(self.sell_order_id)
                    exit_res = self.place_market_order(side="SELL", amount=sell_qty, is_quantity=True)
                    if "error" not in exit_res:
                        exit_price = float(exit_res.get("price", current_price))
                        sell_filled = True
                        stopped_out = True
                        self.logger.info(f"🛑 Stopped out @ ${exit_price:.2f}")
                    break
            
            # Log progress every hour
            if checks % 120 == 0:
                elapsed_hours = (checks * check_interval) / 3600
                self.logger.info(f"⏳ Position open for {elapsed_hours:.1f}h | Price: ${current_price:.2f} | Target: ${target_price:.2f}")
            
            time.sleep(check_interval)
        
        # If order still not filled after max checks
        if not sell_filled:
            status = self.get_order_status(self.sell_order_id)
            if status.get("status") == "NEW":
                self.logger.info("📊 Order still open - continuing to next cycle")
                return {"success": False, "error": "Order still open", "skipped": True}

        if not sell_filled:
            return {"success": False, "error": "Sell never filled"}

        # Calculate P&L
        realized_pnl = (exit_price - self.buy_price) * sell_qty
        fee_estimate = (sell_qty * self.buy_price * self.maker_fee_rate) + (sell_qty * exit_price * self.taker_fee_rate)
        net_pnl = realized_pnl - fee_estimate
        self.total_fees += fee_estimate
        
        self._update_balances()
        
        self.logger.info(f"💰 P&L: ${realized_pnl:.4f} (net: ${net_pnl:.4f})")
        self.logger.info(f"💰 USDT: ${self.current_balance_usdt:.2f} | {self.base_asset}: {self.current_balance_eth:.8f}")
        
        # Update metrics
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
        self.logger.info(f"📊 Win Rate: {win_rate:.1f}% ({self.win_count}W/{self.loss_count}L)")

        result = {
            "success": True,
            "cycle": cycle_number,
            "entry_price": self.buy_price,
            "exit_price": exit_price,
            "quantity": sell_qty,
            "profit": realized_pnl,
            "net_profit": net_pnl,
            "fees": fee_estimate,
            "profit_percent": (realized_pnl / (self.buy_price * sell_qty)) * 100 if self.buy_price * sell_qty > 0 else 0,
            "stopped_out": stopped_out,
            "balance_after": self.current_balance_usdt,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "win_rate": win_rate,
            "timestamp": datetime.now().isoformat()
        }

        self.cycle_stats["total_cycles"] += 1
        if net_pnl > 0:
            self.cycle_stats["successful_cycles"] += 1
        else:
            self.cycle_stats["failed_cycles"] += 1
        self.cycle_stats["net_profit"] += net_pnl
        self.cycle_stats["cycle_results"].append(result)
        self.trade_history.append(result)

        return result

    def run_forever(self, delay_between_cycles: int = 600):
        self.logger.info("\n" + "="*70)
        self.logger.info("🚀 GOLDEN SCALPER BOT v10.5 - RUNNING")
        self.logger.info("   ETH 4h - Golden Strategy")
        self.logger.info("   Press Ctrl+C to stop")
        self.logger.info("="*70)

        self.cycle_stats["start_time"] = datetime.now()
        cycle_num = 1
        
        while not self.stopped:
            try:
                result = self.run_cycle(cycle_number=cycle_num)
                
                if result.get("success", False):
                    self.logger.info(f"✅ TRADE COMPLETED! Net: ${result.get('net_profit', 0):.4f}")
                elif result.get("skipped", False):
                    self.logger.info(f"⏭️ Skipped ({self.skipped_count} skips)")
                else:
                    self.logger.error(f"⚠️ Failed: {result.get('error', 'Unknown')}")
                
                if self.total_trades > 0:
                    win_rate = (self.win_count / self.total_trades) * 100
                    self.logger.info(f"📊 STATS: {self.total_trades} trades, {win_rate:.1f}% win, ${self.cycle_stats['net_profit']:.4f}")
                
                if self.consecutive_wins >= 7:
                    self.logger.info("🎉🎉🎉 7 CONSECUTIVE WINS! 🎉🎉🎉")
                    self.stopped = True
                    break
                
                wait_time = delay_between_cycles + random.uniform(0, 60)
                self.logger.info(f"\n⏳ Waiting {wait_time/60:.1f} minutes...")
                time.sleep(wait_time)
                cycle_num += 1
                
            except KeyboardInterrupt:
                self.logger.info("⚠️ Stopped by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(delay_between_cycles)
                cycle_num += 1

        self.cycle_stats["end_time"] = datetime.now()
        self.print_final_summary()

    def print_final_summary(self):
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        self.logger.info("\n" + "="*70)
        self.logger.info("🏆 GOLDEN STRATEGY - FINAL SUMMARY")
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
    print("🏆 GOLDEN SCALPER BOT v10.5 - FINAL WORKING")
    print("="*70)
    print("\n🎯 ETH 4h - Golden Strategy")
    print("   ✅ Fixed undefined variable error")
    print("   ✅ Better error handling")
    print("   ✅ Handles accumulating ETH")
    print("\n🚀 Starting in 3 seconds...")
    time.sleep(3)
    
    bot = GoldenScalperBot(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol="ETHUSDT",
        exchange_region="us",
        log_level="INFO",
        interval="4h"
    )
    
    bot.run_forever(delay_between_cycles=600)
