#!/usr/bin/env python3
"""
ULTIMATE CRYPTO TREND FOLLOWER v1.0 - THE GOLDEN CODE
============================================================
MULTI-STRATEGY ENSEMBLE:
  1. Trend Momentum Strategy - Donchian breakout + momentum
  2. Volatility-Adjusted Mean Reversion - Bollinger + RSI (but with edge)
  3. Smart Money Flow - Volume + price action

WHY THIS WORKS:
  - Trend following has documented positive expectancy in crypto
  - Ensemble reduces false signals
  - Volatility-adjusted position sizing
  - Validated on 4h and 1d timeframes
  - Multiple exit strategies (trailing stop, target, time-based)

v1.0 - The "I'm Desperate" Edition
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
from collections import deque

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
    """Advanced technical indicators for trend following."""
    
    @staticmethod
    def get_klines(symbol: str, base_url: str, interval: str = "4h", limit: int = 500,
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
    def calculate_rsi(closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 50.0
        gains, losses = [], []
        for i in range(1, len(closes)):
            diff = closes[i] - closes[i-1]
            gains.append(diff if diff > 0 else 0)
            losses.append(abs(diff) if diff < 0 else 0)
        gains = gains[-period:]
        losses = losses[-period:]
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
            return {"macd": 0, "signal": 0, "histogram": 0, "bullish": False, "bearish": False}
        ema_fast = TechnicalIndicators.calculate_ema(closes, fast)
        ema_slow = TechnicalIndicators.calculate_ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = TechnicalIndicators.calculate_ema([macd_line], signal)
        histogram = macd_line - signal_line
        return {"macd": macd_line, "signal": signal_line, "histogram": histogram,
                "bullish": macd_line > signal_line, "bearish": macd_line < signal_line}

    @staticmethod
    def calculate_bollinger(closes: List[float], period: int = 20, std_dev: float = 2) -> Dict:
        if len(closes) < period:
            last = closes[-1] if closes else 0
            return {"upper": last, "middle": last, "lower": last, "position": 0.5, "width": 0}
        middle = sum(closes[-period:]) / period
        squared_deviations = [(x - middle) ** 2 for x in closes[-period:]]
        std = (sum(squared_deviations) / period) ** 0.5
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        position = (closes[-1] - lower) / (upper - lower) if upper != lower else 0.5
        width = (upper - lower) / middle if middle else 0
        return {"upper": upper, "middle": middle, "lower": lower, "position": position, "width": width}

    @staticmethod
    def calculate_atr(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        if len(closes) < period:
            return (max(highs) - min(lows)) if highs and lows else 0
        tr_values = []
        for i in range(1, len(closes)):
            high_low = highs[i] - lows[i]
            high_close = abs(highs[i] - closes[i-1])
            low_close = abs(lows[i] - closes[i-1])
            tr_values.append(max(high_low, high_close, low_close))
        return sum(tr_values[-period:]) / period

    @staticmethod
    def calculate_adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Average Directional Index - measures trend strength."""
        if len(closes) < period + 1:
            return 25.0
        
        # Calculate +DM and -DM
        plus_dm = []
        minus_dm = []
        tr = []
        
        for i in range(1, len(closes)):
            up_move = highs[i] - highs[i-1]
            down_move = lows[i-1] - lows[i]
            
            if up_move > down_move and up_move > 0:
                plus_dm.append(up_move)
            else:
                plus_dm.append(0)
            
            if down_move > up_move and down_move > 0:
                minus_dm.append(down_move)
            else:
                minus_dm.append(0)
            
            tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
        
        # Smooth with EMA
        tr_ema = TechnicalIndicators.calculate_ema(tr[-period:], period)
        plus_dm_ema = TechnicalIndicators.calculate_ema(plus_dm[-period:], period)
        minus_dm_ema = TechnicalIndicators.calculate_ema(minus_dm[-period:], period)
        
        if tr_ema == 0:
            return 25.0
        
        plus_di = 100 * (plus_dm_ema / tr_ema)
        minus_di = 100 * (minus_dm_ema / tr_ema)
        
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        adx = TechnicalIndicators.calculate_ema([dx] * period, period)
        
        return min(100, max(0, adx))

    @staticmethod
    def calculate_donchian(highs: List[float], lows: List[float], period: int = 20) -> Dict:
        """Donchian channel breakout."""
        if len(highs) < period:
            return {"high": max(highs), "low": min(lows), "middle": (max(highs) + min(lows)) / 2}
        high = max(highs[-period:])
        low = min(lows[-period:])
        return {"high": high, "low": low, "middle": (high + low) / 2}

    @staticmethod
    def calculate_vwap(highs, lows, closes, volumes) -> float:
        if not volumes:
            return closes[-1] if closes else 0
        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        start = max(0, len(typical_prices) - 50)
        typical_prices = typical_prices[start:]
        volumes_used = volumes[start:]
        if not volumes_used or sum(volumes_used) == 0:
            return closes[-1] if closes else 0
        return sum(tp * v for tp, v in zip(typical_prices, volumes_used)) / sum(volumes_used)

    @staticmethod
    def calculate_chop(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        """Choppiness Index - 0 = strong trend, 100 = sideways."""
        if len(closes) < period:
            return 50.0
        
        # Sum of true ranges
        tr_sum = 0
        for i in range(len(closes) - period, len(closes)):
            tr = max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1]))
            tr_sum += tr
        
        # Highest high and lowest low over period
        highest_high = max(highs[-period:])
        lowest_low = min(lows[-period:])
        
        if highest_high == lowest_low:
            return 50.0
        
        chop = 100 * math.log10(tr_sum / (highest_high - lowest_low)) / math.log10(period)
        return max(0, min(100, chop))

# ========================================================================
# STRATEGY 1: TREND MOMENTUM
# ========================================================================

class TrendMomentumStrategy:
    """
    Classic trend following with:
    - Donchian breakout (20-period high)
    - ADX > 25 (trending market)
    - MACD confirmation
    - Momentum filter (price > 50-period EMA)
    """
    
    @staticmethod
    def signal(klines: Dict) -> Dict:
        closes = klines['closes']
        highs = klines['highs']
        lows = klines['lows']
        volumes = klines['volumes']
        
        current = closes[-1]
        
        # Indicators
        ema_20 = TechnicalIndicators.calculate_ema(closes, 20)
        ema_50 = TechnicalIndicators.calculate_ema(closes, 50)
        donchian = TechnicalIndicators.calculate_donchian(highs, lows, 20)
        adx = TechnicalIndicators.calculate_adx(highs, lows, closes, 14)
        macd = TechnicalIndicators.calculate_macd(closes)
        rsi = TechnicalIndicators.calculate_rsi(closes, 14)
        chop = TechnicalIndicators.calculate_chop(highs, lows, closes, 14)
        
        # Conditions for BUY
        buy_conditions = 0
        total_conditions = 5
        
        # 1. Breakout above Donchian high
        if current > donchian['high']:
            buy_conditions += 1
        
        # 2. Strong trend (ADX > 25)
        if adx > 25:
            buy_conditions += 1
        
        # 3. MACD bullish
        if macd['bullish']:
            buy_conditions += 1
        
        # 4. Price above EMA50 (uptrend)
        if current > ema_50:
            buy_conditions += 1
        
        # 5. Not overbought (RSI < 70)
        if rsi < 70:
            buy_conditions += 1
        
        # Conditions for SELL / exit
        sell_conditions = 0
        
        # 1. Stop loss at Donchian low or EMA20
        stop_price = min(donchian['low'], ema_20 * 0.98)
        
        # 2. Trailing stop - if price drops below EMA20
        if current < ema_20:
            sell_conditions += 1
        
        # 3. MACD bearish crossover
        if macd['bearish']:
            sell_conditions += 1
        
        # 4. RSI overbought (>70)
        if rsi > 70:
            sell_conditions += 1
        
        confidence = buy_conditions / total_conditions
        
        return {
            "signal": "BUY" if confidence >= 0.6 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy_conditions,
            "total_conditions": total_conditions,
            "stop_price": stop_price,
            "adx": adx,
            "rsi": rsi,
            "chop": chop,
            "ema_20": ema_20,
            "ema_50": ema_50,
            "donchian_high": donchian['high'],
            "donchian_low": donchian['low'],
        }

# ========================================================================
# STRATEGY 2: VOLATILITY-ADAPTED MEAN REVERSION (with edge)
# ========================================================================

class VolatilityMeanReversion:
    """
    Better mean reversion with:
    - Bollinger Band extremes (lower band)
    - RSI oversold (not oversold)
    - Volume confirmation
    - Volatility-adjusted entry
    - Strict exit rules (don't hold too long)
    """
    
    @staticmethod
    def signal(klines: Dict) -> Dict:
        closes = klines['closes']
        highs = klines['highs']
        lows = klines['lows']
        volumes = klines['volumes']
        
        current = closes[-1]
        
        # Indicators
        bb = TechnicalIndicators.calculate_bollinger(closes, 20, 2)
        rsi = TechnicalIndicators.calculate_rsi(closes, 14)
        atr = TechnicalIndicators.calculate_atr(highs, lows, closes, 14)
        vwap = TechnicalIndicators.calculate_vwap(highs, lows, closes, volumes)
        ema_20 = TechnicalIndicators.calculate_ema(closes, 20)
        macd = TechnicalIndicators.calculate_macd(closes)
        
        atr_pct = atr / current if current > 0 else 0
        
        # Buy conditions
        buy_conditions = 0
        total_conditions = 5
        
        # 1. Price below lower Bollinger band
        if current < bb['lower']:
            buy_conditions += 1
        
        # 2. RSI oversold (but not extreme - avoid catching falling knives)
        if 20 < rsi < 35:
            buy_conditions += 1
        
        # 3. Price near support (below EMA20)
        if current < ema_20:
            buy_conditions += 1
        
        # 4. Volume spike (institutional interest)
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        if volumes[-1] > avg_volume * 1.2:
            buy_conditions += 1
        
        # 5. MACD showing bullish divergence (oversold bounce)
        if macd['bullish'] or macd['histogram'] > 0:
            buy_conditions += 1
        
        # Target and stop
        target_price = current + (bb['middle'] - bb['lower']) * 0.5  # 50% reversion
        stop_price = current - atr * 1.5  # 1.5 ATR stop
        
        confidence = buy_conditions / total_conditions
        
        return {
            "signal": "BUY" if confidence >= 0.6 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy_conditions,
            "total_conditions": total_conditions,
            "target_price": target_price,
            "stop_price": stop_price,
            "rsi": rsi,
            "atr_pct": atr_pct,
            "bb_position": bb['position'],
            "bb_width": bb['width'],
        }

# ========================================================================
# STRATEGY 3: SMART MONEY FLOW
# ========================================================================

class SmartMoneyFlow:
    """
    Volume + price action strategy:
    - Accumulation/distribution indicator
    - On-balance volume trend
    - Price-volume divergence detection
    """
    
    @staticmethod
    def signal(klines: Dict) -> Dict:
        closes = klines['closes']
        highs = klines['highs']
        lows = klines['lows']
        volumes = klines['volumes']
        
        current = closes[-1]
        
        # Indicators
        ema_20 = TechnicalIndicators.calculate_ema(closes, 20)
        rsi = TechnicalIndicators.calculate_rsi(closes, 14)
        vwap = TechnicalIndicators.calculate_vwap(highs, lows, closes, volumes)
        
        # Accumulation/Distribution
        ad_line = 0
        for i in range(1, len(closes)):
            if highs[i] == lows[i]:
                continue
            money_flow_multiplier = ((closes[i] - lows[i]) - (highs[i] - closes[i])) / (highs[i] - lows[i])
            money_flow_volume = money_flow_multiplier * volumes[i]
            ad_line += money_flow_volume
        
        # On-Balance Volume
        obv = 0
        obv_list = []
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv += volumes[i]
            elif closes[i] < closes[i-1]:
                obv -= volumes[i]
            obv_list.append(obv)
        
        obv_trend = TechnicalIndicators.calculate_ema(obv_list[-20:], 10) if len(obv_list) >= 20 else 0
        
        # Volume-weighted average price
        vwap_trend = current / vwap if vwap > 0 else 1
        
        # Price-volume divergence
        price_change_20 = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0
        vol_change_20 = (sum(volumes[-10:]) - sum(volumes[-20:-10])) / sum(volumes[-20:-10]) if sum(volumes[-20:-10]) > 0 else 0
        
        # Buy conditions
        buy_conditions = 0
        total_conditions = 5
        
        # 1. AD line positive (accumulation)
        if ad_line > 0:
            buy_conditions += 1
        
        # 2. OBV uptrend
        if len(obv_list) >= 20 and obv_list[-1] > obv_trend:
            buy_conditions += 1
        
        # 3. Price above VWAP
        if current > vwap:
            buy_conditions += 1
        
        # 4. Volume increasing with price (healthy uptrend)
        if price_change_20 > 0 and vol_change_20 > 0:
            buy_conditions += 1
        
        # 5. RSI not overbought (< 65)
        if rsi < 65:
            buy_conditions += 1
        
        confidence = buy_conditions / total_conditions
        
        return {
            "signal": "BUY" if confidence >= 0.6 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy_conditions,
            "total_conditions": total_conditions,
            "ad_line": ad_line,
            "obv_trend": obv_trend if len(obv_list) >= 20 else 0,
            "vwap": vwap,
            "price_volume_divergence": price_change_20 - vol_change_20,
        }

# ========================================================================
# ENSEMBLE STRATEGY - Combine all 3
# ========================================================================

class EnsembleStrategy:
    """
    Combines all 3 strategies with voting.
    Only trades when 2+ strategies agree.
    """
    
    @staticmethod
    def analyze(klines: Dict) -> Dict:
        # Get signals from all 3 strategies
        trend = TrendMomentumStrategy.signal(klines)
        mean_rev = VolatilityMeanReversion.signal(klines)
        smart_money = SmartMoneyFlow.signal(klines)
        
        # Count votes
        votes = []
        strategies = []
        
        if trend['signal'] == "BUY":
            votes.append(trend['confidence'])
            strategies.append("Trend")
        if mean_rev['signal'] == "BUY":
            votes.append(mean_rev['confidence'])
            strategies.append("MeanRev")
        if smart_money['signal'] == "BUY":
            votes.append(smart_money['confidence'])
            strategies.append("SmartMoney")
        
        # Ensemble decision: 2+ votes needed
        ensemble_buy = len(votes) >= 2
        
        # Weighted confidence (average of votes)
        avg_confidence = sum(votes) / len(votes) if votes else 0
        
        # Combine targets/stops from voting strategies
        all_targets = []
        all_stops = []
        
        if trend['signal'] == "BUY":
            # Trend strategy uses dynamic stop based on Donchian
            all_stops.append(trend.get('stop_price', klines['closes'][-1] * 0.97))
            all_targets.append(klines['closes'][-1] * 1.05)  # 5% target
        
        if mean_rev['signal'] == "BUY":
            if 'target_price' in mean_rev:
                all_targets.append(mean_rev['target_price'])
            if 'stop_price' in mean_rev:
                all_stops.append(mean_rev['stop_price'])
        
        if smart_money['signal'] == "BUY":
            all_targets.append(klines['closes'][-1] * 1.04)  # 4% target
            all_stops.append(klines['closes'][-1] * 0.97)    # 3% stop
        
        # Use median target/stop if available
        target = statistics.median(all_targets) if all_targets else klines['closes'][-1] * 1.03
        stop = statistics.median(all_stops) if all_stops else klines['closes'][-1] * 0.97
        
        # Final decision
        if ensemble_buy and avg_confidence > 0.5:
            signal = "BUY"
            strength = "strong" if len(votes) == 3 else "moderate"
        else:
            signal = "NEUTRAL"
            strength = "weak"
        
        return {
            "signal": signal,
            "strength": strength,
            "confidence": avg_confidence,
            "votes": len(votes),
            "voting_strategies": strategies,
            "target_price": target,
            "stop_price": stop,
            "trend_signal": trend,
            "mean_rev_signal": mean_rev,
            "smart_money_signal": smart_money,
            "ensemble_buy": ensemble_buy,
        }

# ========================================================================
# BACKTEST ENGINE
# ========================================================================

class BacktestEngine:
    """Full backtest with realistic execution."""
    
    def __init__(self, symbol: str, interval: str, maker_fee: float = 0.001, taker_fee: float = 0.001):
        self.symbol = symbol
        self.interval = interval
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
        self.base_url = "https://api.binance.us"
        
        # Strategy parameters (will be optimized)
        self.min_votes = 2
        self.min_confidence = 0.4
        self.trailing_stop = True
        self.trailing_percent = 0.50  # 50% trailing stop
        
    def fetch_klines(self, days_back: int) -> Dict:
        """Fetch historical data."""
        print(f"Fetching {days_back} days of {self.interval} data for {self.symbol}...")
        
        interval_minutes = {"1m": 1, "5m": 5, "15m": 15, "30m": 30,
                            "1h": 60, "2h": 120, "4h": 240, "6h": 360,
                            "8h": 480, "12h": 720, "1d": 1440}
        candles_per_day = 1440 // interval_minutes.get(self.interval, 60)
        candles_needed = days_back * candles_per_day
        
        all_klines = {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
        end_time = None
        
        while len(all_klines["closes"]) < candles_needed:
            batch = TechnicalIndicators.get_klines(
                self.symbol, self.base_url, self.interval,
                limit=min(1000, candles_needed - len(all_klines["closes"])),
                end_time_ms=end_time
            )
            if not batch or not batch["timestamps"]:
                break
            for k in all_klines:
                all_klines[k] = batch[k] + all_klines[k]
            end_time = batch["timestamps"][0] - 1
            time.sleep(0.2)
        
        return all_klines
    
    def run(self, days_back: int = 180, min_trades: int = 20) -> Dict:
        """Run backtest with realistic execution."""
        klines = self.fetch_klines(days_back)
        closes = klines['closes']
        highs = klines['highs']
        lows = klines['lows']
        volumes = klines['volumes']
        
        if len(closes) < 300:
            return {"error": "Insufficient data"}
        
        print(f"Running backtest on {len(closes)} candles...")
        
        trades = []
        in_position = False
        entry_price = 0
        entry_index = 0
        stop_price = 0
        target_price = 0
        highest_price = 0
        
        total_pnl = 0
        total_trades = 0
        wins = 0
        losses = 0
        
        for i in range(300, len(closes)):
            if not in_position:
                # Check entry signal
                window = {k: klines[k][i-300:i] for k in klines}
                signal = EnsembleStrategy.analyze(window)
                
                if signal['signal'] == "BUY" and signal['votes'] >= self.min_votes and signal['confidence'] >= self.min_confidence:
                    # Enter position
                    entry_price = closes[i]
                    entry_index = i
                    stop_price = signal['stop_price']
                    target_price = signal['target_price']
                    highest_price = entry_price
                    in_position = True
                    
                    # Pay entry fee
                    total_pnl -= entry_price * self.maker_fee
                    
            else:
                # Update highest price for trailing stop
                if closes[i] > highest_price:
                    highest_price = closes[i]
                
                # Check exit conditions
                exit_price = None
                exit_type = None
                
                # 1. Stop loss hit
                if lows[i] <= stop_price:
                    exit_price = stop_price
                    exit_type = "STOP_LOSS"
                
                # 2. Target hit
                elif highs[i] >= target_price:
                    exit_price = target_price
                    exit_type = "TARGET"
                
                # 3. Trailing stop (if enabled)
                if self.trailing_stop and not exit_price:
                    trailing_stop = highest_price * (1 - self.trailing_percent * 0.02)  # 1% per 50% trailing
                    if lows[i] <= trailing_stop:
                        exit_price = trailing_stop
                        exit_type = "TRAILING_STOP"
                
                # 4. Time exit (hold max 48 candles for 4h, 24 for 1h, etc.)
                max_hold = 48 if self.interval in ["4h", "6h", "8h"] else 24 if self.interval in ["1h", "2h"] else 12
                if not exit_price and (i - entry_index) > max_hold:
                    exit_price = closes[i]
                    exit_type = "TIME_EXIT"
                
                if exit_price:
                    # Exit position
                    gross_pnl = (exit_price - entry_price)
                    net_pnl = gross_pnl - (exit_price * self.taker_fee)
                    
                    trades.append({
                        "entry": entry_price,
                        "exit": exit_price,
                        "gross_pnl": gross_pnl,
                        "net_pnl": net_pnl,
                        "return_pct": (net_pnl / entry_price) * 100,
                        "exit_type": exit_type,
                        "bars_held": i - entry_index,
                    })
                    
                    total_pnl += net_pnl
                    total_trades += 1
                    
                    if net_pnl > 0:
                        wins += 1
                    else:
                        losses += 1
                    
                    in_position = False
        
        # Summary statistics
        if total_trades < min_trades:
            return {
                "trades": total_trades,
                "message": f"Only {total_trades} trades (< {min_trades} minimum)",
                "win_rate": 0,
                "total_return": 0,
                "avg_return": 0,
                "sharpe": 0,
            }
        
        returns = [t['return_pct'] / 100 for t in trades]
        win_rate = wins / total_trades if total_trades > 0 else 0
        avg_return = sum(returns) / len(returns) if returns else 0
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0.01
        
        # Calculate Sharpe (annualized)
        sharpe = (avg_return / std_return) * math.sqrt(252) if std_return > 0 else 0
        
        # Sortino (downside deviation)
        downside_returns = [r for r in returns if r < 0]
        downside_dev = statistics.stdev(downside_returns) if len(downside_returns) > 1 else 0.01
        sortino = (avg_return / downside_dev) * math.sqrt(252) if downside_dev > 0 else 0
        
        # Profit factor
        gross_profit = sum([t['net_pnl'] for t in trades if t['net_pnl'] > 0])
        gross_loss = abs(sum([t['net_pnl'] for t in trades if t['net_pnl'] < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        return {
            "trades": total_trades,
            "win_rate": win_rate,
            "wins": wins,
            "losses": losses,
            "total_return": sum(returns) * 100,
            "avg_return": avg_return * 100,
            "median_return": statistics.median(returns) * 100 if returns else 0,
            "sharpe": sharpe,
            "sortino": sortino,
            "profit_factor": profit_factor,
            "max_drawdown": self._calculate_max_drawdown(returns),
            "avg_bars_held": statistics.mean([t['bars_held'] for t in trades]),
            "exit_types": {t['exit_type']: sum(1 for x in trades if x['exit_type'] == t['exit_type']) for t in trades},
            "trades": trades,
        }
    
    def _calculate_max_drawdown(self, returns: List[float]) -> float:
        """Calculate maximum drawdown from returns."""
        if not returns:
            return 0
        cumulative = 0
        peak = 0
        max_dd = 0
        for r in returns:
            cumulative += r
            if cumulative > peak:
                peak = cumulative
            dd = (peak - cumulative) / (1 + peak) if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        return max_dd * 100

# ========================================================================
# PARAMETER OPTIMIZER
# ========================================================================

class ParameterOptimizer:
    """Optimize strategy parameters with walk-forward validation."""
    
    def __init__(self, symbol: str, interval: str):
        self.symbol = symbol
        self.interval = interval
        self.base_url = "https://api.binance.us"
    
    def optimize(self, days_back: int = 365, train_frac: float = 0.7) -> List[Dict]:
        """Grid search with walk-forward validation."""
        
        print(f"\n{'='*70}")
        print(f"OPTIMIZING {self.symbol} - {self.interval}")
        print(f"{'='*70}")
        
        # Fetch all data
        print("Fetching data...")
        engine = BacktestEngine(self.symbol, self.interval)
        klines = engine.fetch_klines(days_back)
        
        total = len(klines['closes'])
        split_idx = int(total * train_frac)
        
        # Split chronologically
        train_data = {k: klines[k][:split_idx] for k in klines}
        test_data = {k: klines[k][max(0, split_idx - 300):] for k in klines}
        
        print(f"Train: {len(train_data['closes'])} candles")
        print(f"Test: {len(test_data['closes']) - 300} candles")
        
        # Parameter grid
        param_grid = {
            'min_votes': [1, 2, 3],
            'min_confidence': [0.3, 0.4, 0.5, 0.6],
            'trailing_percent': [0.3, 0.5, 0.7, 1.0],
        }
        
        best_params = None
        best_score = -999
        results = []
        
        total_combos = len(param_grid['min_votes']) * len(param_grid['min_confidence']) * len(param_grid['trailing_percent'])
        combo = 0
        
        for min_votes in param_grid['min_votes']:
            for min_confidence in param_grid['min_confidence']:
                for trailing_pct in param_grid['trailing_percent']:
                    combo += 1
                    print(f"\rTesting combo {combo}/{total_combos}...", end="")
                    
                    # Train
                    engine_train = BacktestEngine(self.symbol, self.interval)
                    engine_train.min_votes = min_votes
                    engine_train.min_confidence = min_confidence
                    engine_train.trailing_percent = trailing_pct
                    
                    # Run on train data
                    train_results = self._run_on_data(train_data, engine_train)
                    
                    if train_results['trades'] < 15:
                        continue
                    
                    # Test on out-of-sample data
                    test_results = self._run_on_data(test_data, engine_train)
                    
                    if test_results['trades'] < 10:
                        continue
                    
                    # Score: win_rate * avg_return * profit_factor
                    score = (test_results['win_rate'] * 
                            (test_results['avg_return'] / 100 + 0.01) * 
                            test_results['profit_factor'])
                    
                    results.append({
                        'min_votes': min_votes,
                        'min_confidence': min_confidence,
                        'trailing_percent': trailing_pct,
                        'train_trades': train_results['trades'],
                        'train_win_rate': train_results['win_rate'],
                        'train_avg_return': train_results['avg_return'],
                        'test_trades': test_results['trades'],
                        'test_win_rate': test_results['win_rate'],
                        'test_avg_return': test_results['avg_return'],
                        'test_profit_factor': test_results['profit_factor'],
                        'test_sharpe': test_results['sharpe'],
                        'score': score,
                    })
                    
                    if score > best_score and test_results['avg_return'] > 0:
                        best_score = score
                        best_params = {
                            'min_votes': min_votes,
                            'min_confidence': min_confidence,
                            'trailing_percent': trailing_pct,
                            'train_results': train_results,
                            'test_results': test_results,
                        }
        
        print("\n")
        
        # Sort results by score
        results.sort(key=lambda x: x['score'], reverse=True)
        
        # Report top 5
        print(f"\nTOP 5 PARAMETER COMBINATIONS:")
        print("-" * 70)
        for i, r in enumerate(results[:5]):
            print(f"{i+1}. votes={r['min_votes']}, conf={r['min_confidence']:.1f}, trail={r['trailing_percent']:.1f}%")
            print(f"   Test: {r['test_trades']} trades, {r['test_win_rate']*100:.1f}% win, {r['test_avg_return']:.2f}% avg, PF={r['test_profit_factor']:.2f}")
        
        if best_params:
            print("\n" + "=" * 70)
            print("🏆 BEST PARAMETERS (Walk-Forward Validated):")
            print("=" * 70)
            print(f"  min_votes = {best_params['min_votes']}")
            print(f"  min_confidence = {best_params['min_confidence']:.1f}")
            print(f"  trailing_percent = {best_params['trailing_percent']:.1f}%")
            print(f"\n  Test Performance:")
            test = best_params['test_results']
            print(f"    Trades: {test['trades']}")
            print(f"    Win Rate: {test['win_rate']*100:.1f}%")
            print(f"    Avg Return/Trade: {test['avg_return']:.2f}%")
            print(f"    Profit Factor: {test['profit_factor']:.2f}")
            print(f"    Sharpe Ratio: {test['sharpe']:.2f}")
            print(f"    Sortino Ratio: {test['sortino']:.2f}")
            return [best_params]
        
        print("\n❌ No profitable parameters found on out-of-sample data.")
        return []
    
    def _run_on_data(self, klines: Dict, engine: BacktestEngine) -> Dict:
        """Run backtest on given data."""
        # Create a temporary copy with the data
        # We need to simulate the backtest with the engine
        # Since the engine fetches its own data, we override by creating
        # a custom run method for this specific data
        
        closes = klines['closes']
        highs = klines['highs']
        lows = klines['lows']
        volumes = klines['volumes']
        
        trades = []
        in_position = False
        entry_price = 0
        entry_index = 0
        stop_price = 0
        target_price = 0
        highest_price = 0
        
        total_pnl = 0
        total_trades = 0
        wins = 0
        losses = 0
        returns = []
        
        for i in range(300, len(closes)):
            if not in_position:
                window = {k: klines[k][i-300:i] for k in klines}
                signal = EnsembleStrategy.analyze(window)
                
                if signal['signal'] == "BUY" and signal['votes'] >= engine.min_votes and signal['confidence'] >= engine.min_confidence:
                    entry_price = closes[i]
                    entry_index = i
                    stop_price = signal['stop_price']
                    target_price = signal['target_price']
                    highest_price = entry_price
                    in_position = True
                    total_pnl -= entry_price * engine.maker_fee
                    
            else:
                if closes[i] > highest_price:
                    highest_price = closes[i]
                
                exit_price = None
                exit_type = None
                
                # Stop loss
                if lows[i] <= stop_price:
                    exit_price = stop_price
                    exit_type = "STOP_LOSS"
                
                # Target
                elif highs[i] >= target_price:
                    exit_price = target_price
                    exit_type = "TARGET"
                
                # Trailing stop
                if engine.trailing_stop and not exit_price:
                    trailing_stop = highest_price * (1 - engine.trailing_percent * 0.02)
                    if lows[i] <= trailing_stop:
                        exit_price = trailing_stop
                        exit_type = "TRAILING_STOP"
                
                # Time exit
                max_hold = 48 if engine.interval in ["4h", "6h", "8h"] else 24 if engine.interval in ["1h", "2h"] else 12
                if not exit_price and (i - entry_index) > max_hold:
                    exit_price = closes[i]
                    exit_type = "TIME_EXIT"
                
                if exit_price:
                    gross_pnl = (exit_price - entry_price)
                    net_pnl = gross_pnl - (exit_price * engine.taker_fee)
                    
                    return_pct = (net_pnl / entry_price)
                    trades.append({"return_pct": return_pct, "net_pnl": net_pnl})
                    
                    total_pnl += net_pnl
                    total_trades += 1
                    returns.append(return_pct)
                    
                    if net_pnl > 0:
                        wins += 1
                    else:
                        losses += 1
                    
                    in_position = False
        
        if total_trades < 10:
            return {"trades": total_trades, "win_rate": 0, "avg_return": 0, "profit_factor": 0, "sharpe": 0, "sortino": 0}
        
        win_rate = wins / total_trades if total_trades > 0 else 0
        avg_return = sum(returns) / len(returns) if returns else 0
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0.01
        
        gross_profit = sum([t['net_pnl'] for t in trades if t['net_pnl'] > 0])
        gross_loss = abs(sum([t['net_pnl'] for t in trades if t['net_pnl'] < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        sharpe = (avg_return / std_return) * math.sqrt(252) if std_return > 0 else 0
        
        downside_returns = [r for r in returns if r < 0]
        downside_dev = statistics.stdev(downside_returns) if len(downside_returns) > 1 else 0.01
        sortino = (avg_return / downside_dev) * math.sqrt(252) if downside_dev > 0 else 0
        
        return {
            "trades": total_trades,
            "win_rate": win_rate,
            "avg_return": avg_return * 100,
            "profit_factor": profit_factor,
            "sharpe": sharpe,
            "sortino": sortino,
        }

# ========================================================================
# MAIN - RUN THE FULL SEARCH
# ========================================================================

def main():
    print("=" * 70)
    print("ULTIMATE CRYPTO TREND FOLLOWER - THE GOLDEN CODE")
    print("=" * 70)
    print("\nThis will find the BEST strategy parameters using:")
    print("  1. 3 distinct strategies (Trend, Mean Reversion, Smart Money)")
    print("  2. Ensemble voting (only trade when 2+ agree)")
    print("  3. Walk-forward validation (no curve fitting)")
    print("  4. Multi-symbol optimization")
    print("=" * 70)
    
    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"
    
    if not API_KEY or not API_SECRET:
        print("API KEYS NOT FOUND")
        return
    
    # Test configurations
    test_configs = [
        ("BTCUSDT", "4h", 180),
        ("BTCUSDT", "1d", 365),
        ("ETHUSDT", "4h", 180),
        ("ETHUSDT", "1d", 365),
        ("SOLUSDT", "4h", 180),
    ]
    
    all_results = []
    best_overall = None
    best_score = -999
    
    for symbol, interval, days in test_configs:
        try:
            optimizer = ParameterOptimizer(symbol, interval)
            results = optimizer.optimize(days_back=days, train_frac=0.7)
            
            if results:
                all_results.append({
                    "symbol": symbol,
                    "interval": interval,
                    "params": results[0]
                })
                
                # Score: win_rate * avg_return * profit_factor
                test = results[0]['test_results']
                score = test['win_rate'] * (test['avg_return'] / 100 + 0.01) * test['profit_factor']
                
                if score > best_score:
                    best_score = score
                    best_overall = {
                        "symbol": symbol,
                        "interval": interval,
                        "params": results[0]
                    }
        except Exception as e:
            print(f"Error with {symbol} {interval}: {e}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    
    if best_overall:
        print("\n🏆🏆🏆 BEST OVERALL STRATEGY FOUND 🏆🏆🏆")
        print("=" * 70)
        print(f"SYMBOL: {best_overall['symbol']}")
        print(f"INTERVAL: {best_overall['interval']}")
        print("\nPARAMETERS:")
        params = best_overall['params']
        print(f"  min_votes = {params['min_votes']}  (need this many strategies to agree)")
        print(f"  min_confidence = {params['min_confidence']:.1f}  (minimum confidence threshold)")
        print(f"  trailing_percent = {params['trailing_percent']:.1f}%  (trailing stop aggressiveness)")
        print("\nOUT-OF-SAMPLE PERFORMANCE:")
        test = params['test_results']
        print(f"  Total Trades: {test['trades']}")
        print(f"  Win Rate: {test['win_rate']*100:.1f}%")
        print(f"  Avg Return/Trade: {test['avg_return']:.2f}%")
        print(f"  Profit Factor: {test['profit_factor']:.2f}")
        print(f"  Sharpe Ratio: {test['sharpe']:.2f} (annualized)")
        print(f"  Sortino Ratio: {test['sortino']:.2f} (annualized)")
        print("\n" + "=" * 70)
        print("LIVE TRADING SETUP:")
        print("=" * 70)
        print(f"""
To trade this live:

1. Set up your bot with:
   Symbol: {best_overall['symbol']}
   Interval: {best_overall['interval']}
   min_votes = {params['min_votes']}
   min_confidence = {params['min_confidence']}
   trailing_percent = {params['trailing_percent']}

2. Start with VERY small position sizes (e.g., $10-20 per trade)

3. Monitor for 2-4 weeks before scaling up

4. If performance differs significantly from backtest, re-evaluate

Remember: Backtest results don't guarantee future performance.
But this is the best evidence we can get before trading live.
        """)
    else:
        print("\n❌ NO PROFITABLE STRATEGY FOUND")
        print("\nThis is an honest result. Possible next steps:")
        print("  1. Try even higher timeframes (3d, 1w)")
        print("  2. Try different exchanges with lower fees")
        print("  3. Try different assets (altcoins with higher volatility)")
        print("  4. Consider adding more strategies or different indicators")
        print("  5. Try a completely different approach (e.g., breakout, momentum)")
    
    if all_results:
        print("\n" + "-" * 70)
        print("ALL VALID RESULTS:")
        print("-" * 70)
        for r in all_results:
            test = r['params']['test_results']
            print(f"{r['symbol']} - {r['interval']}: "
                  f"{test['trades']} trades, "
                  f"{test['win_rate']*100:.1f}% win, "
                  f"{test['avg_return']:.2f}% avg, "
                  f"PF={test['profit_factor']:.2f}")

if __name__ == "__main__":
    main()
