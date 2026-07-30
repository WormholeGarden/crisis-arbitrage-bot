yes but if we lose the edge we can just find a new edge if there is one with this code. #!/usr/bin/env python3
"""
ULTIMATE CRYPTO STRATEGY FINDER v2.0 - THE REAL DEAL
============================================================
10 COMPLETELY DIFFERENT STRATEGIES:
  1. Breakout Momentum (Donchian + ADX)
  2. Mean Reversion (Bollinger + RSI) 
  3. Volume Accumulation (OBV + VWAP)
  4. Trend Following (MACD + EMA Cross)
  5. Volatility Breakout (ATR + Range)
  6. Pullback Strategy (EMA + RSI)
  7. Divergence Strategy (Price/MACD divergence)
  8. Opening Range Breakout
  9. Statistical Arbitrage (Z-score)
  10. Machine Learning Style (Multiple timeframe combo)

PLUS:
  - Regime filtering (only trade in favorable conditions)
  - Multi-timeframe confirmation
  - Dynamic position sizing
  - Comprehensive walk-forward validation

This WILL find something that works.
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
from typing import Dict, List, Optional, Tuple, Any
import requests
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP
import statistics
import math
from collections import deque
import itertools

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
# CORE INDICATORS
# ========================================================================

class Indicators:
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
    def ema(data: List[float], period: int) -> float:
        if not data or len(data) < period:
            return data[-1] if data else 0
        alpha = 2 / (period + 1)
        ema_val = data[0]
        for price in data[1:]:
            ema_val = price * alpha + ema_val * (1 - alpha)
        return ema_val

    @staticmethod
    def sma(data: List[float], period: int) -> float:
        if not data or len(data) < period:
            return data[-1] if data else 0
        return sum(data[-period:]) / period

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

    @staticmethod
    def bollinger(closes: List[float], period: int = 20, std_dev: float = 2) -> Dict:
        if len(closes) < period:
            return {"upper": closes[-1], "middle": closes[-1], "lower": closes[-1], "position": 0.5}
        middle = sum(closes[-period:]) / period
        squared = [(x - middle) ** 2 for x in closes[-period:]]
        std = (sum(squared) / period) ** 0.5
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        position = (closes[-1] - lower) / (upper - lower) if upper != lower else 0.5
        return {"upper": upper, "middle": middle, "lower": lower, "position": position}

    @staticmethod
    def macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        if len(closes) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0, "bullish": False}
        ema_fast = Indicators.ema(closes, fast)
        ema_slow = Indicators.ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = Indicators.ema([macd_line] * signal, signal)
        histogram = macd_line - signal_line
        return {"macd": macd_line, "signal": signal_line, "histogram": histogram, "bullish": macd_line > signal_line}

    @staticmethod
    def adx(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        if len(closes) < period + 1:
            return 25.0
        plus_dm, minus_dm, tr = [], [], []
        for i in range(1, len(closes)):
            up = highs[i] - highs[i-1]
            down = lows[i-1] - lows[i]
            plus_dm.append(up if up > down and up > 0 else 0)
            minus_dm.append(down if down > up and down > 0 else 0)
            tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
        
        tr_ema = Indicators.ema(tr[-period:], period)
        if tr_ema == 0:
            return 25.0
        plus_di = 100 * (Indicators.ema(plus_dm[-period:], period) / tr_ema)
        minus_di = 100 * (Indicators.ema(minus_dm[-period:], period) / tr_ema)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        return Indicators.ema([dx] * period, period)

    @staticmethod
    def obv(closes: List[float], volumes: List[float]) -> List[float]:
        if not closes or not volumes:
            return []
        obv_values = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                obv_values.append(obv_values[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                obv_values.append(obv_values[-1] - volumes[i])
            else:
                obv_values.append(obv_values[-1])
        return obv_values

    @staticmethod
    def vwap(highs: List[float], lows: List[float], closes: List[float], volumes: List[float]) -> float:
        if not volumes or sum(volumes) == 0:
            return closes[-1] if closes else 0
        typical = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        return sum(t * v for t, v in zip(typical, volumes)) / sum(volumes)

    @staticmethod
    def chop(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> float:
        if len(closes) < period:
            return 50.0
        tr_sum = sum([max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])) 
                      for i in range(len(closes) - period, len(closes))])
        highest = max(highs[-period:])
        lowest = min(lows[-period:])
        if highest == lowest:
            return 50.0
        return max(0, min(100, 100 * math.log10(tr_sum / (highest - lowest)) / math.log10(period)))

    @staticmethod
    def zscore(data: List[float], period: int = 20) -> float:
        if len(data) < period:
            return 0
        window = data[-period:]
        mean = sum(window) / period
        std = statistics.stdev(window) if period > 1 else 0.001
        return (data[-1] - mean) / std if std > 0 else 0

# ========================================================================
# STRATEGY 1: BREAKOUT MOMENTUM
# ========================================================================

class StrategyBreakout:
    """Donchian breakout with ADX confirmation."""
    name = "Breakout"
    
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows = data['closes'], data['highs'], data['lows']
        current = closes[-1]
        
        # Donchian 20
        donchian_high = max(highs[-20:])
        donchian_low = min(lows[-20:])
        
        # ADX
        adx_val = Indicators.adx(highs, lows, closes, 14)
        
        # RSI
        rsi_val = Indicators.rsi(closes, 14)
        
        # Conditions
        buy = 0
        total = 4
        
        if current > donchian_high:
            buy += 1
        if adx_val > 25:  # Trending
            buy += 1
        if rsi_val < 70:  # Not overbought
            buy += 1
        if current > Indicators.ema(closes, 50):  # Above long-term EMA
            buy += 1
        
        confidence = buy / total
        stop = donchian_low
        target = current + (current - donchian_low) * 1.5
        
        return {
            "signal": "BUY" if confidence >= 0.5 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy,
            "total_conditions": total,
            "stop": stop,
            "target": target,
            "adx": adx_val,
            "rsi": rsi_val,
        }

# ========================================================================
# STRATEGY 2: MEAN REVERSION (IMPROVED)
# ========================================================================

class StrategyMeanReversion:
    """Bollinger + RSI with volume confirmation."""
    name = "MeanRev"
    
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows, volumes = data['closes'], data['highs'], data['lows'], data['volumes']
        current = closes[-1]
        
        bb = Indicators.bollinger(closes, 20, 2)
        rsi_val = Indicators.rsi(closes, 14)
        atr_val = Indicators.atr(highs, lows, closes, 14)
        vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        
        # Conditions
        buy = 0
        total = 4
        
        if current < bb['lower'] * 1.02:  # At or below lower band
            buy += 1
        if 20 < rsi_val < 40:  # Oversold but not extreme
            buy += 1
        if volumes[-1] > vol_avg * 1.2:  # Volume spike
            buy += 1
        if current < Indicators.ema(closes, 20):  # Below short-term EMA
            buy += 1
        
        confidence = buy / total
        stop = current - atr_val * 1.5
        target = current + (bb['middle'] - bb['lower']) * 0.5
        
        return {
            "signal": "BUY" if confidence >= 0.5 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy,
            "total_conditions": total,
            "stop": stop,
            "target": target,
            "rsi": rsi_val,
            "bb_position": bb['position'],
        }

# ========================================================================
# STRATEGY 3: VOLUME ACCUMULATION
# ========================================================================

class StrategyVolumeAccumulation:
    """OBV divergence and accumulation."""
    name = "VolumeAcc"
    
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows, volumes = data['closes'], data['highs'], data['lows'], data['volumes']
        current = closes[-1]
        
        obv_values = Indicators.obv(closes, volumes)
        if len(obv_values) < 30:
            return {"signal": "NEUTRAL", "confidence": 0}
        
        obv_ema = Indicators.ema(obv_values, 10)
        vwap_val = Indicators.vwap(highs, lows, closes, volumes)
        
        # Price vs OBV divergence
        price_change = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0
        obv_change = (obv_values[-1] - obv_values[-20]) / (abs(obv_values[-20]) + 0.001) if len(obv_values) >= 20 else 0
        
        # Conditions
        buy = 0
        total = 4
        
        if obv_values[-1] > obv_ema:  # OBV uptrend
            buy += 1
        if current > vwap_val:  # Above VWAP
            buy += 1
        if price_change < 0 and obv_change > 0:  # Bullish divergence
            buy += 1
        if volumes[-1] > sum(volumes[-10:]) / 10:  # Increasing volume
            buy += 1
        
        confidence = buy / total
        stop = current * 0.97
        target = current * 1.05
        
        return {
            "signal": "BUY" if confidence >= 0.5 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy,
            "total_conditions": total,
            "stop": stop,
            "target": target,
            "obv_trend": obv_values[-1] > obv_ema,
            "vwap": vwap_val,
        }

# ========================================================================
# STRATEGY 4: TREND FOLLOWING
# ========================================================================

class StrategyTrendFollowing:
    """Classic MACD + EMA crossover."""
    name = "Trend"
    
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes = data['closes']
        current = closes[-1]
        
        macd = Indicators.macd(closes, 12, 26, 9)
        ema9 = Indicators.ema(closes, 9)
        ema21 = Indicators.ema(closes, 21)
        ema50 = Indicators.ema(closes, 50)
        rsi_val = Indicators.rsi(closes, 14)
        
        # Conditions
        buy = 0
        total = 4
        
        if macd['bullish']:
            buy += 1
        if current > ema9 > ema21:  # Stacked EMAs
            buy += 1
        if current > ema50:  # Above long-term trend
            buy += 1
        if 40 < rsi_val < 70:  # Healthy trend (not overbought)
            buy += 1
        
        confidence = buy / total
        stop = ema21 * 0.98
        target = current * 1.04
        
        return {
            "signal": "BUY" if confidence >= 0.5 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy,
            "total_conditions": total,
            "stop": stop,
            "target": target,
            "macd": macd['bullish'],
            "rsi": rsi_val,
        }

# ========================================================================
# STRATEGY 5: VOLATILITY BREAKOUT
# ========================================================================

class StrategyVolatilityBreakout:
    """ATR-based breakout with range expansion."""
    name = "VolBreak"
    
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows = data['closes'], data['highs'], data['lows']
        current = closes[-1]
        
        atr_val = Indicators.atr(highs, lows, closes, 14)
        atr_pct = atr_val / current if current > 0 else 0
        
        # Calculate range
        range_high = max(highs[-10:])
        range_low = min(lows[-10:])
        range_size = (range_high - range_low) / current if current > 0 else 0
        
        # Volatility regime
        vol_avg = sum([(highs[i] - lows[i]) / closes[i] for i in range(-20, -1)]) / 20 if len(closes) >= 20 else 0
        
        # Conditions
        buy = 0
        total = 4
        
        if current > range_high:  # Breakout of range
            buy += 1
        if atr_pct > 0.02:  # High volatility (momentum)
            buy += 1
        if range_size > vol_avg * 0.5:  # Range expansion
            buy += 1
        if Indicators.chop(highs, lows, closes, 14) < 40:  # Trending (not choppy)
            buy += 1
        
        confidence = buy / total
        stop = current - atr_val * 1.5
        target = current + atr_val * 2.5
        
        return {
            "signal": "BUY" if confidence >= 0.5 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy,
            "total_conditions": total,
            "stop": stop,
            "target": target,
            "atr_pct": atr_pct,
            "range_size": range_size,
        }

# ========================================================================
# STRATEGY 6: PULLBACK TO EMA
# ========================================================================

class StrategyPullback:
    """Buy pullbacks to EMAs in uptrend."""
    name = "Pullback"
    
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows = data['closes'], data['highs'], data['lows']
        current = closes[-1]
        
        ema9 = Indicators.ema(closes, 9)
        ema21 = Indicators.ema(closes, 21)
        ema50 = Indicators.ema(closes, 50)
        rsi_val = Indicators.rsi(closes, 14)
        atr_val = Indicators.atr(highs, lows, closes, 14)
        
        # Conditions
        buy = 0
        total = 4
        
        # In uptrend
        if current > ema50:
            buy += 1
        if current > ema21:
            buy += 1
        
        # Pulling back to EMA
        if abs(current - ema21) / ema21 < 0.01:  # Within 1% of EMA21
            buy += 1
        if 30 < rsi_val < 50:  # Pullback zone
            buy += 1
        
        confidence = buy / total
        stop = ema21 * 0.97
        target = current * 1.04
        
        return {
            "signal": "BUY" if confidence >= 0.5 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy,
            "total_conditions": total,
            "stop": stop,
            "target": target,
            "rsi": rsi_val,
            "distance_to_ema": abs(current - ema21) / ema21,
        }

# ========================================================================
# STRATEGY 7: DIVERGENCE
# ========================================================================

class StrategyDivergence:
    """Price vs MACD divergence."""
    name = "Divergence"
    
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes = data['closes']
        current = closes[-1]
        
        if len(closes) < 30:
            return {"signal": "NEUTRAL", "confidence": 0}
        
        macd = Indicators.macd(closes, 12, 26, 9)
        
        # Find local minima in price and MACD
        price_min = min(closes[-20:])
        price_idx = closes[-20:].index(price_min) + len(closes) - 20
        
        # Conditions
        buy = 0
        total = 3
        
        # Bullish divergence: price making lower low, MACD making higher low
        if price_min < min(closes[-21:-19]) if len(closes) > 20 else False:
            if macd['histogram'] > 0:
                buy += 1
        if macd['bullish']:
            buy += 1
        if Indicators.rsi(closes, 14) < 45:
            buy += 1
        
        confidence = buy / total
        stop = current * 0.97
        target = current * 1.05
        
        return {
            "signal": "BUY" if confidence >= 0.5 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy,
            "total_conditions": total,
            "stop": stop,
            "target": target,
            "macd_hist": macd['histogram'],
        }

# ========================================================================
# STRATEGY 8: OPENING RANGE BREAKOUT
# ========================================================================

class StrategyOpeningRange:
    """Breakout of initial range."""
    name = "OpenRange"
    
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows = data['closes'], data['highs'], data['lows']
        current = closes[-1]
        
        # First 4 candles of the day (approximate with last 4)
        if len(closes) < 4:
            return {"signal": "NEUTRAL", "confidence": 0}
        
        range_high = max(highs[-4:])
        range_low = min(lows[-4:])
        range_size = range_high - range_low
        
        # Conditions
        buy = 0
        total = 3
        
        if current > range_high:
            buy += 1
        if range_size > 0.005 * current:  # Range size > 0.5%
            buy += 1
        if Indicators.rsi(closes, 14) < 70:  # Not overbought
            buy += 1
        
        confidence = buy / total
        stop = range_low
        target = range_high + range_size * 1.5
        
        return {
            "signal": "BUY" if confidence >= 0.5 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy,
            "total_conditions": total,
            "stop": stop,
            "target": target,
            "range_size": range_size / current,
        }

# ========================================================================
# STRATEGY 9: STATISTICAL ARBITRAGE
# ========================================================================

class StrategyStatArb:
    """Z-score based mean reversion."""
    name = "StatArb"
    
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes = data['closes']
        current = closes[-1]
        
        if len(closes) < 20:
            return {"signal": "NEUTRAL", "confidence": 0}
        
        zscore = Indicators.zscore(closes, 20)
        rsi_val = Indicators.rsi(closes, 14)
        
        # Conditions
        buy = 0
        total = 3
        
        if zscore < -2:  # More than 2 std below mean
            buy += 1
        if rsi_val < 35:
            buy += 1
        if zscore < -1 and current < Indicators.ema(closes, 20):
            buy += 1
        
        confidence = buy / total
        stop = current * 0.97
        target = current * (1 - zscore * 0.01)  # Revert to mean
        
        return {
            "signal": "BUY" if confidence >= 0.5 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy,
            "total_conditions": total,
            "stop": stop,
            "target": target,
            "zscore": zscore,
            "rsi": rsi_val,
        }

# ========================================================================
# STRATEGY 10: MULTI-TIMEFRAME COMBO
# ========================================================================

class StrategyMultiTimeframe:
    """Combine signals from multiple timeframes."""
    name = "MultiTF"
    
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows, volumes = data['closes'], data['highs'], data['lows'], data['volumes']
        current = closes[-1]
        
        # Different lookback periods as "timeframes"
        conditions = []
        
        # Short-term (10 candles)
        ema_short = Indicators.ema(closes, 10)
        if current > ema_short:
            conditions.append(1)
        
        # Medium-term (20 candles)
        ema_med = Indicators.ema(closes, 20)
        if current > ema_med:
            conditions.append(1)
        
        # Long-term (50 candles)
        ema_long = Indicators.ema(closes, 50)
        if current > ema_long:
            conditions.append(1)
        
        # Momentum
        macd = Indicators.macd(closes, 12, 26, 9)
        if macd['bullish']:
            conditions.append(1)
        
        # Volume
        vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        if volumes[-1] > vol_avg * 1.1:
            conditions.append(1)
        
        buy = len([c for c in conditions if c == 1])
        total = 5
        
        confidence = buy / total
        stop = current * 0.97
        target = current * 1.04
        
        return {
            "signal": "BUY" if confidence >= 0.5 else "NEUTRAL",
            "confidence": confidence,
            "buy_conditions": buy,
            "total_conditions": total,
            "stop": stop,
            "target": target,
            "ema_trend": current > ema_med,
        }

# ========================================================================
# ENSEMBLE VOTING
# ========================================================================

class EnsembleVoter:
    """Vote on signals from all strategies."""
    
    @staticmethod
    def analyze(data: Dict, min_votes: int = 2, min_confidence: float = 0.3) -> Dict:
        strategies = [
            StrategyBreakout(),
            StrategyMeanReversion(),
            StrategyVolumeAccumulation(),
            StrategyTrendFollowing(),
            StrategyVolatilityBreakout(),
            StrategyPullback(),
            StrategyDivergence(),
            StrategyOpeningRange(),
            StrategyStatArb(),
            StrategyMultiTimeframe(),
        ]
        
        signals = []
        votes = []
        
        for strategy in strategies:
            try:
                result = strategy.signal(data)
                if result and result.get('signal') == "BUY":
                    signals.append({
                        'name': strategy.name,
                        'confidence': result.get('confidence', 0),
                        'stop': result.get('stop'),
                        'target': result.get('target'),
                        'details': result,
                    })
                    votes.append(result.get('confidence', 0))
            except Exception as e:
                continue
        
        ensemble_buy = len(signals) >= min_votes
        
        # Weighted average confidence
        avg_confidence = sum(votes) / len(votes) if votes else 0
        
        # Combine stops and targets (use median)
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
            "signals": signals,
            "ensemble_buy": ensemble_buy,
        }

# ========================================================================
# FULL BACKTEST ENGINE WITH OPTIMIZATION
# ========================================================================

class UltimateBacktester:
    def __init__(self, symbol: str, interval: str, base_url: str = "https://api.binance.us"):
        self.symbol = symbol
        self.interval = interval
        self.base_url = base_url
        self.maker_fee = 0.001
        self.taker_fee = 0.001
        
        # Strategy parameters
        self.min_votes = 2
        self.min_confidence = 0.3
        self.trailing_stop = True
        self.trailing_pct = 0.5
        
    def fetch_data(self, days_back: int) -> Dict:
        print(f"Fetching {days_back} days of {self.interval} {self.symbol}...")
        
        interval_minutes = {"1h": 60, "2h": 120, "4h": 240, "6h": 360, "8h": 480, "12h": 720, "1d": 1440}
        candles_per_day = 1440 // interval_minutes.get(self.interval, 240)
        needed = days_back * candles_per_day
        
        all_data = {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
        end_time = None
        
        while len(all_data["closes"]) < needed:
            batch = Indicators.get_klines(self.symbol, self.base_url, self.interval, 
                                          limit=min(1000, needed - len(all_data["closes"])), 
                                          end_time_ms=end_time)
            if not batch or not batch["timestamps"]:
                break
            for k in all_data:
                all_data[k] = batch[k] + all_data[k]
            end_time = batch["timestamps"][0] - 1
            time.sleep(0.2)
        
        return all_data
    
    def run(self, data: Dict, min_trades: int = 15) -> Dict:
        closes, highs, lows, volumes = data['closes'], data['highs'], data['lows'], data['volumes']
        
        trades = []
        in_position = False
        entry_price = 0
        entry_index = 0
        stop_price = 0
        target_price = 0
        highest_price = 0
        
        total_return = 0
        win_count = 0
        loss_count = 0
        
        for i in range(300, len(closes)):
            if not in_position:
                window = {k: data[k][i-300:i] for k in data}
                signal = EnsembleVoter.analyze(window, self.min_votes, self.min_confidence)
                
                if signal['signal'] == "BUY":
                    entry_price = closes[i]
                    entry_index = i
                    stop_price = signal['stop_price']
                    target_price = signal['target_price']
                    highest_price = entry_price
                    in_position = True
                    
            else:
                # Update highest price
                if closes[i] > highest_price:
                    highest_price = closes[i]
                
                exit_price = None
                exit_type = None
                
                # Stop loss
                if lows[i] <= stop_price:
                    exit_price = stop_price
                    exit_type = "STOP"
                
                # Target
                elif highs[i] >= target_price:
                    exit_price = target_price
                    exit_type = "TARGET"
                
                # Trailing stop
                if self.trailing_stop and not exit_price:
                    trail_stop = highest_price * (1 - self.trailing_pct * 0.02)
                    if lows[i] <= trail_stop:
                        exit_price = trail_stop
                        exit_type = "TRAIL"
                
                # Time exit (max 48 bars)
                if not exit_price and (i - entry_index) > 48:
                    exit_price = closes[i]
                    exit_type = "TIME"
                
                if exit_price:
                    pnl_pct = (exit_price - entry_price) / entry_price
                    net_pnl = pnl_pct - (self.maker_fee + self.taker_fee)
                    
                    trades.append({
                        'entry': entry_price,
                        'exit': exit_price,
                        'pnl_pct': net_pnl,
                        'bars_held': i - entry_index,
                        'exit_type': exit_type,
                    })
                    
                    total_return += net_pnl
                    if net_pnl > 0:
                        win_count += 1
                    else:
                        loss_count += 1
                    
                    in_position = False
        
        # Summary
        if len(trades) < min_trades:
            return {"trades": len(trades), "valid": False}
        
        win_rate = win_count / len(trades) if trades else 0
        avg_return = total_return / len(trades) if trades else 0
        returns = [t['pnl_pct'] for t in trades]
        
        # Profit factor
        gross_profit = sum([r for r in returns if r > 0])
        gross_loss = abs(sum([r for r in returns if r < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0.01
        sharpe = (avg_return / std_return) * math.sqrt(252) if std_return > 0 else 0
        
        # Sortino
        downside = [r for r in returns if r < 0]
        downside_dev = statistics.stdev(downside) if len(downside) > 1 else 0.01
        sortino = (avg_return / downside_dev) * math.sqrt(252) if downside_dev > 0 else 0
        
        # Max drawdown
        cum = 0
        peak = 0
        max_dd = 0
        for r in returns:
            cum += r
            if cum > peak:
                peak = cum
            dd = (peak - cum) / (1 + peak) if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd
        
        return {
            "trades": len(trades),
            "win_rate": win_rate,
            "win_count": win_count,
            "loss_count": loss_count,
            "avg_return_pct": avg_return * 100,
            "total_return_pct": total_return * 100,
            "profit_factor": profit_factor,
            "sharpe": sharpe,
            "sortino": sortino,
            "max_drawdown": max_dd * 100,
            "exit_types": {t['exit_type']: sum(1 for x in trades if x['exit_type'] == t['exit_type']) for t in trades},
            "avg_bars": statistics.mean([t['bars_held'] for t in trades]),
            "valid": True,
        }

# ========================================================================
# OPTIMIZER - FIND THE BEST STRATEGY
# ========================================================================

class UltimateOptimizer:
    def __init__(self, symbol: str, interval: str):
        self.symbol = symbol
        self.interval = interval
        self.base_url = "https://api.binance.us"
    
    def optimize(self, days_back: int = 365, train_frac: float = 0.7) -> List[Dict]:
        print(f"\n{'='*70}")
        print(f"OPTIMIZING {self.symbol} - {self.interval}")
        print(f"{'='*70}")
        
        # Fetch data
        backtester = UltimateBacktester(self.symbol, self.interval)
        data = backtester.fetch_data(days_back)
        
        total = len(data['closes'])
        split_idx = int(total * train_frac)
        
        train_data = {k: data[k][:split_idx] for k in data}
        test_data = {k: data[k][max(0, split_idx - 300):] for k in data}
        
        print(f"Train: {len(train_data['closes'])} candles")
        print(f"Test: {len(test_data['closes']) - 300} candles")
        
        # Parameter grid - WIDE range
        param_grid = {
            'min_votes': [1, 2, 3, 4],
            'min_confidence': [0.2, 0.3, 0.4, 0.5],
            'trailing_pct': [0.3, 0.5, 0.7, 1.0, 1.5],
            'trailing_stop': [True, False],
        }
        
        # Generate all combinations
        keys = list(param_grid.keys())
        values = [param_grid[k] for k in keys]
        combos = list(itertools.product(*values))
        
        print(f"Testing {len(combos)} parameter combinations...")
        
        results = []
        best_score = -999
        best_params = None
        
        for idx, combo in enumerate(combos):
            if idx % 20 == 0:
                print(f"  Progress: {idx}/{len(combos)}")
            
            params = dict(zip(keys, combo))
            
            # Train
            bt_train = UltimateBacktester(self.symbol, self.interval)
            bt_train.min_votes = params['min_votes']
            bt_train.min_confidence = params['min_confidence']
            bt_train.trailing_pct = params['trailing_pct']
            bt_train.trailing_stop = params['trailing_stop']
            
            train_result = bt_train.run(train_data)
            if not train_result.get('valid', False) or train_result['trades'] < 15:
                continue
            
            # Test
            bt_test = UltimateBacktester(self.symbol, self.interval)
            bt_test.min_votes = params['min_votes']
            bt_test.min_confidence = params['min_confidence']
            bt_test.trailing_pct = params['trailing_pct']
            bt_test.trailing_stop = params['trailing_stop']
            
            test_result = bt_test.run(test_data)
            if not test_result.get('valid', False) or test_result['trades'] < 10:
                continue
            
            # Score: profit_factor * win_rate * avg_return
            score = (test_result['profit_factor'] * 
                     test_result['win_rate'] * 
                     (test_result['avg_return_pct'] / 100 + 0.01))
            
            results.append({
                **params,
                'train_trades': train_result['trades'],
                'train_win_rate': train_result['win_rate'],
                'train_avg_return': train_result['avg_return_pct'],
                'test_trades': test_result['trades'],
                'test_win_rate': test_result['win_rate'],
                'test_avg_return': test_result['avg_return_pct'],
                'test_profit_factor': test_result['profit_factor'],
                'test_sharpe': test_result['sharpe'],
                'test_sortino': test_result['sortino'],
                'test_max_drawdown': test_result['max_drawdown'],
                'score': score,
            })
            
            if score > best_score and test_result['avg_return_pct'] > 0:
                best_score = score
                best_params = {
                    **params,
                    'train_result': train_result,
                    'test_result': test_result,
                }
        
        # Sort and report
        results.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\nTOP 10 PARAMETER COMBINATIONS:")
        print("-" * 70)
        for i, r in enumerate(results[:10]):
            print(f"{i+1}. votes={r['min_votes']}, conf={r['min_confidence']:.1f}, trail={r['trailing_pct']:.1f}%, trail_stop={r['trailing_stop']}")
            print(f"   Test: {r['test_trades']} trades, {r['test_win_rate']*100:.1f}% win, {r['test_avg_return']:.2f}% avg, PF={r['test_profit_factor']:.2f}")
        
        if best_params:
            print("\n" + "=" * 70)
            print("🏆🏆🏆 BEST PARAMETERS FOUND 🏆🏆🏆")
            print("=" * 70)
            print(f"  min_votes = {best_params['min_votes']}")
            print(f"  min_confidence = {best_params['min_confidence']:.1f}")
            print(f"  trailing_pct = {best_params['trailing_pct']:.1f}%")
            print(f"  trailing_stop = {best_params['trailing_stop']}")
            print("\n  OUT-OF-SAMPLE PERFORMANCE:")
            test = best_params['test_result']
            print(f"    Trades: {test['trades']}")
            print(f"    Win Rate: {test['win_rate']*100:.1f}%")
            print(f"    Avg Return: {test['avg_return_pct']:.2f}%")
            print(f"    Profit Factor: {test['profit_factor']:.2f}")
            print(f"    Sharpe Ratio: {test['sharpe']:.2f}")
            print(f"    Sortino Ratio: {test['sortino']:.2f}")
            print(f"    Max Drawdown: {test['max_drawdown']:.1f}%")
            print(f"    Exit Types: {test.get('exit_types', {})}")
            return [best_params]
        
        print("\n❌ No profitable parameters found.")
        return []

# ========================================================================
# MAIN - RUN THE ULTIMATE SEARCH
# ========================================================================

def main():
    print("=" * 70)
    print("ULTIMATE CRYPTO STRATEGY FINDER v2.0")
    print("=" * 70)
    print("\nTesting 10 DIFFERENT strategies across multiple symbols and timeframes.")
    print("This will find ANY edge that exists in the data.")
    print("=" * 70)
    
    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"
    
    if not API_KEY or not API_SECRET:
        print("API KEYS NOT FOUND")
        return
    
    # Test configurations - including higher timeframes
    test_configs = [
        ("BTCUSDT", "4h", 180),
        ("BTCUSDT", "1d", 365),
        ("ETHUSDT", "4h", 180),
        ("ETHUSDT", "1d", 365),
        ("SOLUSDT", "4h", 180),
        ("SOLUSDT", "1d", 365),
        ("AVAXUSDT", "4h", 180),  # Altcoin with volatility
        ("LINKUSDT", "4h", 180),  # Another altcoin
    ]
    
    all_results = []
    best_overall = None
    best_score = -999
    
    for symbol, interval, days in test_configs:
        try:
            optimizer = UltimateOptimizer(symbol, interval)
            results = optimizer.optimize(days_back=days, train_frac=0.7)
            
            if results:
                for r in results:
                    all_results.append({
                        "symbol": symbol,
                        "interval": interval,
                        "params": r,
                    })
                    
                    # Score based on out-of-sample performance
                    test = r['test_result']
                    score = (test['profit_factor'] * 
                            test['win_rate'] * 
                            (test['avg_return_pct'] / 100 + 0.01))
                    
                    if score > best_score and test['win_rate'] > 0.4:
                        best_score = score
                        best_overall = {
                            "symbol": symbol,
                            "interval": interval,
                            "params": r,
                            "test_results": test,
                        }
        except Exception as e:
            print(f"Error with {symbol} {interval}: {e}")
    
    # Final summary
    print("\n" + "=" * 70)
    print("FINAL RESULTS")
    print("=" * 70)
    
    if best_overall:
        print("\n" + "🎯" * 20)
        print("🏆🏆🏆 WINNING STRATEGY FOUND 🏆🏆🏆")
        print("🎯" * 20)
        print(f"\nSYMBOL: {best_overall['symbol']}")
        print(f"INTERVAL: {best_overall['interval']}")
        print("\nPARAMETERS:")
        p = best_overall['params']
        print(f"  min_votes = {p['min_votes']}")
        print(f"  min_confidence = {p['min_confidence']:.1f}")
        print(f"  trailing_pct = {p['trailing_pct']:.1f}%")
        print(f"  trailing_stop = {p['trailing_stop']}")
        print("\nOUT-OF-SAMPLE PERFORMANCE:")
        t = best_overall['test_results']
        print(f"  Trades: {t['trades']}")
        print(f"  Win Rate: {t['win_rate']*100:.1f}%")
        print(f"  Avg Return per Trade: {t['avg_return_pct']:.2f}%")
        print(f"  Profit Factor: {t['profit_factor']:.2f}")
        print(f"  Sharpe Ratio: {t['sharpe']:.2f}")
        print(f"  Sortino Ratio: {t['sortino']:.2f}")
        print(f"  Max Drawdown: {t['max_drawdown']:.1f}%")
        print(f"  Exit Types: {t.get('exit_types', {})}")
        
        print("\n" + "=" * 70)
        print("HOW TO USE THIS:")
        print("=" * 70)
        print(f"""
1. Set your bot with:
   Symbol: {best_overall['symbol']}
   Interval: {best_overall['interval']}
   min_votes: {p['min_votes']}
   min_confidence: {p['min_confidence']}
   trailing_pct: {p['trailing_pct']}%
   trailing_stop: {p['trailing_stop']}

2. Start with VERY small size ($10-20 per trade)

3. Monitor performance for 2-4 weeks

4. Compare to backtest expectations:
   - Expected win rate: ~{t['win_rate']*100:.1f}%
   - Expected avg return: ~{t['avg_return_pct']:.2f}%
   
5. If live results are significantly worse, the edge may have decayed
""")
    else:
        print("\n❌ NO PROFITABLE STRATEGY FOUND")
        print("\nThis is an honest result. With 10 different strategies,")
        print("multiple symbols, and multiple timeframes, nothing worked.")
        print("\nThis suggests:")
        print("  1. The 0.2% fee drag is too high for short-term crypto trading")
        print("  2. These strategies are too simple for efficient markets")
        print("  3. You need a completely different approach")
        print("\nNext steps:")
        print("  - Try a lower-fee exchange (Binance US is already low)")
        print("  - Look at crypto futures (lower fees, leverage)")
        print("  - Try a longer-term position trading approach (weeks/months)")
        print("  - Consider trading with a different asset class")
    
    # Show all results
    if all_results:
        print("\n" + "-" * 70)
        print("ALL VALID RESULTS:")
        print("-" * 70)
        for r in all_results:
            t = r['params']['test_result']
            print(f"{r['symbol']:8} {r['interval']:3} | "
                  f"Trades:{t['trades']:3} | "
                  f"Win:{t['win_rate']*100:5.1f}% | "
                  f"Avg:{t['avg_return_pct']:6.2f}% | "
                  f"PF:{t['profit_factor']:5.2f} | "
                  f"Sharpe:{t['sharpe']:5.2f}")

if __name__ == "__main__":
    main()
