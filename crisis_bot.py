#!/usr/bin/env python3
"""
CRISIS ARBITRAGE SCALPER v12.0 - FIXED + BACKTESTABLE
============================================================
FIXES from v11:
- Removed duplicate confidence condition (was counted twice,
  artificially inflating "passing conditions")
- Crisis/FSI bonus no longer counts toward the trading decision
  (it was a constant +1 every cycle since the "top opportunity"
  never changes trade to trade, and FSI has no causal link to
  BTC price) - kept only for logging/context
- Fixed inverted stop-loss bound that silently disabled the
  ATR-adaptive stop widening
- Added a fee-aware expectancy check before sizing a trade
- Added a backtester (run in test mode against real historical
  klines) so you can measure win rate/expectancy BEFORE risking
  money, instead of assuming it
- Default entrypoint now runs the backtest, not live trading
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
# FSI 2024 DATA (subset) - context/logging only, NOT a trading signal
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
    if value <= 0:
        return "0.00000000"
    return f"{Decimal(str(value)):.8f}"

def format_price(value: float) -> str:
    return f"{Decimal(str(value)):.2f}"

# ========================================================================
# CRISIS SCORING ENGINE (context/logging only - see note below)
# ========================================================================

class CrisisScoringEngine:
    @staticmethod
    def get_crisis_score(iso: str) -> Dict:
        return FSI_2024.get(iso)

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
                "iso": iso, "name": data["name"], "flag": data["flag"],
                "fsi_score": data["fsi_score"], "wst_class": data["wst_class"],
                "recovery_rate": data["recovery_rate"], "opportunity_score": score,
            })
        opportunities.sort(key=lambda x: x["opportunity_score"], reverse=True)
        return opportunities[:limit]

# ========================================================================
# POSITION SIZING MATH
# ========================================================================

class EinsteinMath:
    @staticmethod
    def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
        if avg_loss == 0:
            return 0.02
        b = avg_win / avg_loss
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b
        half_kelly = max(0.005, min(0.05, kelly * 0.5))
        return half_kelly

    @staticmethod
    def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        avg_return = sum(returns) / len(returns)
        std_dev = statistics.stdev(returns) if len(returns) > 1 else 0.001
        if std_dev == 0:
            return 0.0
        return (avg_return - risk_free_rate) / std_dev

    @staticmethod
    def optimal_stop_loss(atr: float, volatility: float, confidence: float) -> float:
        base_stop = atr * 2.0
        vol_multiplier = 1 + (volatility * 5)
        confidence_adjust = 1 - (confidence * 0.2)
        optimal_stop = base_stop * vol_multiplier * confidence_adjust
        return min(max(optimal_stop, atr * 0.8), atr * 4.0)

# ========================================================================
# TECHNICAL ANALYSIS
# ========================================================================

class AdvancedTA:
    @staticmethod
    def get_klines(symbol: str, base_url: str, interval: str = "1m", limit: int = 300,
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
    def calculate_macd(closes: List[float]) -> Dict:
        if len(closes) < 26:
            return {"macd": 0, "signal": 0, "histogram": 0, "bullish_cross": False, "bearish_cross": False}
        ema_12 = AdvancedTA.calculate_ema(closes, 12)
        ema_26 = AdvancedTA.calculate_ema(closes, 26)
        macd_line = ema_12 - ema_26
        signal_line = AdvancedTA.calculate_ema([macd_line], 9)
        histogram = macd_line - signal_line
        if len(closes) >= 30:
            ema_12_prev = AdvancedTA.calculate_ema(closes[:-1], 12)
            ema_26_prev = AdvancedTA.calculate_ema(closes[:-1], 26)
            macd_prev = ema_12_prev - ema_26_prev
            signal_prev = AdvancedTA.calculate_ema([macd_prev], 9)
            bullish_cross = macd_line > signal_line and macd_prev <= signal_prev
            bearish_cross = macd_line < signal_line and macd_prev >= signal_prev
        else:
            bullish_cross = False
            bearish_cross = False
        return {"macd": macd_line, "signal": signal_line, "histogram": histogram,
                "bullish_cross": bullish_cross, "bearish_cross": bearish_cross}

    @staticmethod
    def calculate_bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2) -> Dict:
        if len(closes) < period:
            last = closes[-1] if closes else 0
            return {"upper": last, "middle": last, "lower": last, "position": 0.5, "width": 0, "squeeze": False}
        middle = sum(closes[-period:]) / period
        squared_deviations = [(x - middle) ** 2 for x in closes[-period:]]
        std = (sum(squared_deviations) / period) ** 0.5
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        position = (closes[-1] - lower) / (upper - lower) if upper != lower else 0.5
        width = (upper - lower) / middle if middle else 0
        return {"upper": upper, "middle": middle, "lower": lower, "position": position,
                "width": width, "squeeze": width < 0.02}

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
    def calculate_support_resistance(highs, lows, closes) -> Dict:
        if len(closes) < 20:
            return {"support": min(lows), "resistance": max(highs), "near_support": False,
                    "near_resistance": False, "support_strength": 0, "resistance_strength": 0}
        lookback = 10
        supports, resistances = [], []
        for i in range(lookback, len(closes) - lookback):
            if lows[i] < min(lows[i-lookback:i] + lows[i+1:i+lookback+1]):
                supports.append(lows[i])
            if highs[i] > max(highs[i-lookback:i] + highs[i+1:i+lookback+1]):
                resistances.append(highs[i])
        recent_support = supports[-1] if supports else min(lows)
        recent_resistance = resistances[-1] if resistances else max(highs)
        current_price = closes[-1]
        near_support = abs(current_price - recent_support) / current_price < 0.001
        near_resistance = abs(current_price - recent_resistance) / current_price < 0.001
        support_strength = len([s for s in supports if abs(s - recent_support) / recent_support < 0.001])
        resistance_strength = len([r for r in resistances if abs(r - recent_resistance) / recent_resistance < 0.001])
        return {"support": recent_support, "resistance": recent_resistance, "near_support": near_support,
                "near_resistance": near_resistance, "support_strength": min(5, support_strength),
                "resistance_strength": min(5, resistance_strength)}

    @staticmethod
    def calculate_stochastic(closes, highs, lows, period: int = 14) -> float:
        if len(closes) < period:
            return 50.0
        highest_high = max(highs[-period:])
        lowest_low = min(lows[-period:])
        if highest_high == lowest_low:
            return 50.0
        return ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100

    @staticmethod
    def calculate_volume_profile(volumes: List[float]) -> Dict:
        if not volumes:
            return {"ratio": 1, "trend": 1, "spike": False, "strength": 0}
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        if len(volumes) >= 10:
            recent_volume_avg = sum(volumes[-10:]) / 10
            older_volume_avg = sum(volumes[-20:-10]) / 10 if len(volumes) >= 20 else recent_volume_avg
            volume_trend = recent_volume_avg / older_volume_avg if older_volume_avg > 0 else 1
        else:
            volume_trend = 1
        return {"ratio": volume_ratio, "trend": volume_trend, "spike": volume_ratio > 2.0,
                "strength": min(1.0, volume_ratio / 3.0)}

# ========================================================================
# STRATEGY - FIXED: no duplicate confidence condition, no fake crisis edge
# ========================================================================

class EinsteinStrategy:
    """
    NOTE ON THE FSI/crisis_score ARGUMENTS:
    These are accepted for logging/context only. They no longer influence
    the trading decision. A country's Fragile States Index score has no
    causal relationship to BTC/USDT price action, and in the old version
    the "top opportunity" never changed between cycles, so the crisis bonus
    was a constant +1 that made the filter easier to pass than it looked.
    """

    @staticmethod
    def analyze_market(klines: Dict, crisis_score: float = 0.0, wst_class: str = "Periphery") -> Dict:
        if not klines or len(klines['closes']) < 50:
            return {"signal": "neutral", "confidence": 0, "reason": "Insufficient data",
                    "passing_conditions": 0, "total_conditions": 9, "reasons": [],
                    "expected_win_rate": 0.5, "kelly_fraction": 0.01, "atr": 0, "atr_pct": 0,
                    "volatility": 0.001, "crisis_bonus": 0, "sr": {"near_resistance": False, "resistance": 0}}

        closes = klines['closes']
        highs = klines['highs']
        lows = klines['lows']
        volumes = klines['volumes']
        current_price = closes[-1]

        rsi = AdvancedTA.calculate_rsi(closes)
        macd = AdvancedTA.calculate_macd(closes)
        bb = AdvancedTA.calculate_bollinger_bands(closes)
        atr = AdvancedTA.calculate_atr(highs, lows, closes)
        vwap = AdvancedTA.calculate_vwap(highs, lows, closes, volumes)
        sr = AdvancedTA.calculate_support_resistance(highs, lows, closes)
        stochastic = AdvancedTA.calculate_stochastic(closes, highs, lows)
        volume_profile = AdvancedTA.calculate_volume_profile(volumes)

        sma_5 = sum(closes[-5:]) / 5
        sma_10 = sum(closes[-10:]) / 10
        sma_20 = sum(closes[-20:]) / 20
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma_20

        momentum_5 = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0

        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        volatility = statistics.stdev(returns[-30:]) if len(returns) >= 30 else 0.001

        # Context only - NOT added to bullish_signals/passing_conditions anymore
        crisis_bonus = 0
        if crisis_score > 0.6:
            crisis_bonus += 1
        if crisis_score > 0.7:
            crisis_bonus += 1
        if wst_class == "Periphery":
            crisis_bonus += 1
        elif wst_class == "Semi":
            crisis_bonus += 0.5

        bullish_signals = 0
        bearish_signals = 0
        strong_bullish = 0
        signal_reasons = []

        if rsi < 30 and current_price < sma_20:
            bullish_signals += 2; strong_bullish += 1
            signal_reasons.append(f"RSI extreme oversold ({rsi:.1f})")
        elif rsi < 35 and current_price < sma_20:
            bullish_signals += 1
            signal_reasons.append(f"RSI oversold ({rsi:.1f})")
        elif rsi < 45:
            bullish_signals += 1
            signal_reasons.append(f"RSI low ({rsi:.1f})")
        elif rsi > 75:
            bearish_signals += 1
            signal_reasons.append(f"RSI high ({rsi:.1f}) - wait")
        else:
            signal_reasons.append(f"RSI neutral ({rsi:.1f})")

        if macd['bullish_cross']:
            bullish_signals += 2; strong_bullish += 1
            signal_reasons.append("MACD bullish crossover")
        elif macd['histogram'] > 0:
            bullish_signals += 1
            signal_reasons.append("MACD positive")
        else:
            bearish_signals += 1
            signal_reasons.append("MACD negative")

        if bb['position'] < 0.20 and current_price < sma_20:
            bullish_signals += 2; strong_bullish += 1
            signal_reasons.append(f"At lower BB ({bb['position']:.2f})")
        elif bb['position'] < 0.35:
            bullish_signals += 1
            signal_reasons.append(f"Near lower BB ({bb['position']:.2f})")
        elif bb['position'] > 0.85:
            bearish_signals += 1
            signal_reasons.append(f"Near upper BB ({bb['position']:.2f})")
        else:
            signal_reasons.append(f"BB neutral ({bb['position']:.2f})")

        if current_price > sma_5 > sma_10 > sma_20:
            bullish_signals += 2; strong_bullish += 1
            signal_reasons.append("Trend alignment")
        elif current_price > sma_20:
            bullish_signals += 1
            signal_reasons.append("Above SMA20 - uptrend")
        elif current_price < sma_20:
            bearish_signals += 1
            signal_reasons.append("Below SMA20 - skip")

        if sr['near_support'] and sr['support_strength'] >= 2:
            bullish_signals += 2; strong_bullish += 1
            signal_reasons.append(f"Strong support (${sr['support']:.2f})")
        elif sr['near_support']:
            bullish_signals += 1
            signal_reasons.append(f"Near support (${sr['support']:.2f})")
        elif sr['near_resistance']:
            bearish_signals += 1
            signal_reasons.append(f"Near resistance (${sr['resistance']:.2f})")

        if current_price > vwap:
            bullish_signals += 1
            signal_reasons.append("Above VWAP")
        else:
            bearish_signals += 1
            signal_reasons.append("Below VWAP")

        if stochastic < 25 and current_price < sma_20:
            bullish_signals += 1; strong_bullish += 1
            signal_reasons.append(f"Stochastic oversold ({stochastic:.1f})")
        elif stochastic > 80:
            bearish_signals += 1
            signal_reasons.append(f"Stochastic overbought ({stochastic:.1f})")

        if volume_profile['spike'] and current_price > sma_20:
            bullish_signals += 1
            signal_reasons.append("Volume spike confirmation")

        if momentum_5 > 0.001:
            bullish_signals += 1
            signal_reasons.append("Positive momentum")
        elif momentum_5 < -0.002:
            bearish_signals += 1
            signal_reasons.append("Negative momentum")

        atr_pct = atr / current_price if current_price > 0 else 0
        if atr_pct < 0.005:
            bullish_signals += 1
            signal_reasons.append(f"Low volatility ({atr_pct*100:.2f}%)")
        elif atr_pct > 0.02:
            bearish_signals += 1
            signal_reasons.append(f"High volatility ({atr_pct*100:.2f}%) - risky")

        total_signals = bullish_signals + bearish_signals
        raw_confidence = (bullish_signals - bearish_signals) / total_signals if total_signals > 0 else 0
        confidence = max(-1, min(1, raw_confidence))

        # FIX: 9 genuinely distinct conditions. Removed the duplicate
        # confidence check and the always-true crisis_bonus check that
        # were in v11.
        passing_conditions = 0
        total_conditions = 9
        if raw_confidence > 0.10:
            passing_conditions += 1
        if strong_bullish >= 1:
            passing_conditions += 1
        if bullish_signals >= 3:
            passing_conditions += 1
        if bearish_signals <= 4:
            passing_conditions += 1
        if bb['position'] < 0.50:
            passing_conditions += 1
        if rsi < 60:
            passing_conditions += 1
        if current_price > sma_20:
            passing_conditions += 1
        if current_price > vwap:
            passing_conditions += 1
        if macd['histogram'] > 0:
            passing_conditions += 1

        if passing_conditions >= 6:
            signal = "BUY"; signal_strength = "strong"; expected_win_rate = 0.55
        elif passing_conditions >= 5:
            signal = "BUY"; signal_strength = "moderate"; expected_win_rate = 0.52
        elif passing_conditions >= 4:
            signal = "CONSIDER"; signal_strength = "weak"; expected_win_rate = 0.50
        else:
            signal = "NEUTRAL"; signal_strength = "weak"; expected_win_rate = 0.45

        # NOTE: expected_win_rate above is still a rough heuristic, not a
        # measured statistic. Use run_backtest() to replace it with a real
        # number for your actual signal thresholds before trusting it.
        if signal == "BUY":
            kelly_fraction = EinsteinMath.kelly_criterion(expected_win_rate, 0.012, 0.008)
        else:
            kelly_fraction = 0.01

        return {
            "signal": signal, "strength": signal_strength, "confidence": abs(confidence),
            "premium": passing_conditions >= 5, "passing_conditions": passing_conditions,
            "total_conditions": total_conditions, "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals, "strong_bullish": strong_bullish,
            "reasons": signal_reasons, "expected_win_rate": expected_win_rate,
            "kelly_fraction": kelly_fraction, "rsi": rsi, "macd": macd, "bb": bb, "atr": atr,
            "atr_pct": atr_pct, "vwap": vwap, "sr": sr, "stochastic": stochastic,
            "current_price": current_price, "sma_20": sma_20, "sma_50": sma_50,
            "volatility": volatility, "momentum_5": momentum_5, "crisis_bonus": crisis_bonus,
        }

# ========================================================================
# SCALPER BOT - FIXED
# ========================================================================

class ScalperBotV12:

    def __init__(self, api_key: str, api_secret: str, symbol: str = "BTCUSDT",
                 exchange_region: str = "us", log_level: str = "INFO"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.test_mode = False

        self.crisis_engine = CrisisScoringEngine()
        top = self.crisis_engine.get_top_opportunities(1)
        self.context_country = top[0] if top else None

        log_filename = f"crisis_scalper_{datetime.now().strftime('%Y%m%d')}.log"
        logging.basicConfig(filename=log_filename, level=getattr(logging, log_level.upper()),
                             format='%(asctime)s - %(levelname)s - %(message)s', datefmt='%Y-%m-%d %H:%M:%S')
        self.logger = logging.getLogger(__name__)
        console = logging.StreamHandler()
        console.setLevel(logging.INFO)
        console.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
        self.logger.addHandler(console)

        if exchange_region.lower() == "us":
            self.base_url = "https://api.binance.us"
        elif exchange_region.lower() == "global":
            self.base_url = "https://api.binance.com"
        else:
            raise ValueError('exchange_region must be "us" or "global"')

        self.total_balance_usdt = 50.0
        self.min_order_usdt = 8.0
        self.max_order_usdt = 20.0

        self.stop_loss_pct = 0.008
        self.target_profit_pct = 0.012

        self.base_risk_per_trade = 0.015
        self.max_risk_per_trade = 0.035
        self.min_risk_per_trade = 0.01

        # FIX: threshold rescaled to the new 9-condition total (was 5/10)
        self.min_passing_conditions = 5
        self.min_confidence = 0.15

        self.max_drawdown_pct = 0.12
        self.max_consecutive_losses = 5
        self.max_skips_before_pause = 40
        self.target_consecutive_wins = 7

        self.chase_timeout_sec = 60
        self.stop_loss_poll_sec = 2
        self.maker_fee_rate = 0.001
        self.taker_fee_rate = 0.001

        self._price_cache = {}
        self._price_cache_time = 0
        self._price_cache_ttl = 1

        self._min_qty = 0.00001
        self._tick_size = 0.01
        self._min_notional = 10.0

        self.active_order_id = None
        self.buy_price = None
        self.buy_qty = None
        self.last_known_qty = 0.0

        self.running_pnl = 0.0
        self.current_balance = 0.0
        self.peak_balance = 0.0
        self.starting_balance = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.balance_fetched = False
        self.stopped = False
        self.skipped_count = 0

        self.trade_history = []
        self.win_count = 0
        self.loss_count = 0
        self.total_trades = 0
        self.skipped_trades = 0
        self.total_fees = 0.0

        self.cycle_stats = {"total_cycles": 0, "successful_cycles": 0, "failed_cycles": 0,
                             "total_profit": 0.0, "total_loss": 0.0, "net_profit": 0.0,
                             "start_time": None, "end_time": None, "cycle_results": []}

        self.logger.info("="*70)
        self.logger.info("CRISIS ARBITRAGE SCALPER v12.0 - FIXED")
        self.logger.info("="*70)
        self.logger.info(f"   Symbol: {symbol}")
        if self.context_country:
            self.logger.info(f"   Context only (not a signal): {self.context_country['flag']} "
                              f"{self.context_country['name']} FSI {self.context_country['fsi_score']:.1f}")
        self.logger.info(f"   Target: {self.target_profit_pct*100:.1f}% | Stop: {self.stop_loss_pct*100:.1f}%")
        self.logger.info(f"   Passing Conditions needed: {self.min_passing_conditions}/9")
        self.logger.info("="*70)

    def _check_connectivity(self):
        self.logger.info("Running startup connectivity check...")
        ticker = self.get_order_book_ticker()
        if not ticker:
            self.logger.error("STARTUP CHECK FAILED - fix exchange_region / API key / network before trading live.")
            raise SystemExit("Aborting: fix connectivity before running live cycles.")
        self.logger.info("Connectivity OK.")

    def _get_exchange_info(self):
        try:
            resp = requests.get(f"{self.base_url}/api/v3/exchangeInfo", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for symbol_info in data.get("symbols", []):
                    if symbol_info["symbol"] == self.symbol:
                        for f in symbol_info.get("filters", []):
                            if f["filterType"] == "LOT_SIZE":
                                self._min_qty = float(f.get("minQty", 0.00001))
                            if f["filterType"] == "PRICE_FILTER":
                                self._tick_size = float(f.get("tickSize", 0.01))
                            if f["filterType"] == "MIN_NOTIONAL":
                                self._min_notional = float(f.get("minNotional", 10.0))
                        self.logger.info("Exchange info loaded")
                        break
        except Exception as e:
            self.logger.warning(f"Could not fetch exchange info: {e}")

    def _initialize_balance(self):
        try:
            balances = self.get_account_balance()
            if balances.get("USDT", 0) > 0:
                self.current_balance = balances["USDT"]
                self.starting_balance = self.current_balance
                self.peak_balance = self.current_balance
                self.total_balance_usdt = self.current_balance
                self.balance_fetched = True
                self.logger.info(f"Starting Balance: ${self.current_balance:.2f}")
                return True
            self.logger.warning("Could not fetch valid balance")
            return False
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            return False

    def _update_balance(self):
        try:
            balances = self.get_account_balance()
            if balances.get("USDT", 0) > 0:
                self.current_balance = balances["USDT"]
                self.total_balance_usdt = self.current_balance
                self.balance_fetched = True
                if self.current_balance > self.peak_balance:
                    self.peak_balance = self.current_balance
            else:
                self.balance_fetched = False
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            self.balance_fetched = False

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
                        time.sleep(2 ** attempt); continue
                    return {"error": "Invalid JSON response", "status_code": response.status_code}

                if isinstance(data, dict) and "code" in data and "msg" in data:
                    error_code = data.get("code")
                    if error_code in [-1003, -1001, -1016]:
                        time.sleep(2 ** attempt); continue
                    if error_code == -2010:
                        self._update_balance()
                        return {"error": data.get("msg"), "code": error_code, "insufficient": True}
                    return {"error": data.get("msg"), "code": error_code}
                return data
            except requests.exceptions.RequestException as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt); continue
                return {"error": str(e)}
            except Exception as e:
                if attempt < retries - 1:
                    time.sleep(2 ** attempt); continue
                return {"error": str(e)}
        return {"error": "Max retries exceeded"}

    def get_order_book_ticker(self) -> Optional[dict]:
        now = time.time()
        if now - self._price_cache_time < self._price_cache_ttl and 'ticker' in self._price_cache:
            return self._price_cache['ticker']
        url = f"{self.base_url}/api/v3/ticker/bookTicker"
        try:
            resp = requests.get(url, params={"symbol": self.symbol}, timeout=5)
            if resp.status_code != 200:
                self.logger.warning(f"Ticker request failed ({resp.status_code}): {resp.text[:200]}")
                return None
            data = resp.json()
            if "bidPrice" in data and "askPrice" in data:
                ticker_data = {"bid": float(data["bidPrice"]), "ask": float(data["askPrice"])}
                self._price_cache = {'ticker': ticker_data}
                self._price_cache_time = now
                return ticker_data
            return None
        except Exception as e:
            self.logger.warning(f"Error fetching ticker: {e}")
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
            for b in resp["balances"]:
                free = float(b["free"])
                if free > 0:
                    balances[b["asset"]] = free
            return balances
        return {"USDT": 0.0}

    def get_order_fill_price(self, order_id: str) -> Optional[float]:
        status = self._send_signed_request("GET", "/api/v3/order", {"symbol": self.symbol, "orderId": order_id})
        if status.get("status") == "FILLED":
            cum_quote = float(status.get("cummulativeQuoteQty", 0))
            executed_qty = float(status.get("executedQty", 0))
            if executed_qty > 0 and cum_quote > 0:
                return cum_quote / executed_qty
        return None

    def place_limit_order_entry(self, side: str, amount: float) -> dict:
        ticker = self.get_order_book_ticker()
        if not ticker:
            return {"error": "Failed to get market price"}
        limit_price = ticker["bid"] * 0.9995 if side.upper() == "BUY" else ticker["ask"] * 1.0005
        limit_price = round_to_tick(limit_price, self._tick_size)
        qty = round_to_step(amount / limit_price, self._min_qty)
        if qty < self._min_qty:
            qty = self._min_qty
        params = {"symbol": self.symbol, "side": side.upper(), "type": "LIMIT",
                  "quantity": format_quantity(qty), "price": format_price(limit_price), "timeInForce": "GTC"}
        response = self._send_signed_request("POST", "/api/v3/order", params)
        if "error" in response:
            return response
        return {"orderId": response.get("orderId"), "price": str(limit_price), "origQty": str(qty),
                "executedQty": "0", "status": response.get("status", "NEW"), "side": side}

    def place_market_order(self, side: str, amount: float, is_quantity: bool = False) -> dict:
        ticker = self.get_order_book_ticker()
        if not ticker:
            return {"error": "Failed to get market price"}
        price = ticker["ask"] if side.upper() == "BUY" else ticker["bid"]
        if amount <= 0:
            return {"error": "Invalid amount", "code": -1003}
        qty = amount if is_quantity else amount / price
        qty = round_to_step(qty, self._min_qty)
        if qty < self._min_qty:
            qty = self._min_qty
        self.last_known_qty = qty
        params = {"symbol": self.symbol, "side": side.upper(), "type": "MARKET", "quantity": format_quantity(qty)}
        response = self._send_signed_request("POST", "/api/v3/order", params)
        if "error" in response:
            return response
        order_id = response.get("orderId")
        if order_id:
            time.sleep(0.5)
            fill_price = self.get_order_fill_price(order_id)
            price = str(fill_price) if fill_price else str(price)
        return {"orderId": order_id, "price": price, "executedQty": response.get("executedQty", str(qty)),
                "origQty": response.get("origQty", str(qty)), "status": response.get("status", "FILLED"), "side": side}

    def place_limit_order(self, side: str, quantity: float, price: float) -> dict:
        if quantity <= 0:
            return {"error": "Invalid quantity", "code": -1003}
        if quantity * price < self._min_notional:
            quantity = round_to_step(self._min_notional / price, self._min_qty)
        qty = round_to_step(quantity, self._min_qty)
        if qty < self._min_qty:
            qty = self._min_qty
        self.last_known_qty = qty
        limit_price = round_to_tick(price, self._tick_size)
        params = {"symbol": self.symbol, "side": side.upper(), "type": "LIMIT",
                  "quantity": format_quantity(qty), "price": format_price(limit_price), "timeInForce": "GTC"}
        response = self._send_signed_request("POST", "/api/v3/order", params)
        if "error" in response:
            return response
        return {"orderId": response.get("orderId"), "price": str(limit_price), "origQty": str(qty),
                "executedQty": "0", "status": response.get("status", "NEW"), "side": side}

    def cancel_order(self, order_id: str) -> dict:
        if not order_id or order_id == "0" or "ERR_" in str(order_id):
            return {"status": "CANCELED", "orderId": order_id}
        response = self._send_signed_request("DELETE", "/api/v3/order", {"symbol": self.symbol, "orderId": order_id})
        if response.get("code") == -2011:
            return {"status": "CANCELED", "orderId": order_id}
        return response

    def get_order_status(self, order_id: str) -> dict:
        if not order_id or order_id == "0" or "ERR_" in str(order_id):
            return {"status": "FILLED", "orderId": order_id}
        return self._send_signed_request("GET", "/api/v3/order", {"symbol": self.symbol, "orderId": order_id})

    def calculate_position_size(self, analysis: Dict) -> float:
        kelly_fraction = analysis.get('kelly_fraction', 0.015)
        risk_pct = max(self.min_risk_per_trade, min(self.max_risk_per_trade, kelly_fraction))
        loss_penalty = max(0.5, 1.0 - (self.consecutive_losses * 0.10))
        risk_pct = risk_pct * loss_penalty
        win_bonus = min(1.2, 1.0 + (self.consecutive_wins * 0.03))
        risk_pct = min(self.max_risk_per_trade, risk_pct * win_bonus)
        position_size = max(self.min_order_usdt, min(self.max_order_usdt, self.current_balance * risk_pct))
        self.logger.info(f"Position: ${position_size:.2f} ({risk_pct*100:.2f}% of balance)")
        return position_size

    def _has_positive_expectancy(self, analysis: Dict) -> bool:
        """FIX: require the trade to actually clear round-trip fees with
        margin, using the analysis's own (heuristic, not yet validated)
        win-rate estimate. This won't make the strategy profitable by
        itself, but it stops taking trades that can't possibly be net
        positive even in the best case for this signal."""
        win_rate = analysis.get('expected_win_rate', 0.5)
        round_trip_fee_pct = self.maker_fee_rate + self.taker_fee_rate
        net_target = self.target_profit_pct - round_trip_fee_pct
        net_stop = self.stop_loss_pct + round_trip_fee_pct
        expectancy = (win_rate * net_target) - ((1 - win_rate) * net_stop)
        return expectancy > 0

    def run_cycle(self, cycle_number: int = 0) -> dict:
        if self.stopped:
            return {"success": False, "error": "Bot stopped"}

        self.logger.info(f"\n{'='*60}\nCYCLE {cycle_number}\n{'='*60}")
        self._update_balance()

        if not self.balance_fetched or self.current_balance <= 0:
            self.logger.error("Invalid balance"); self.stopped = True
            return {"success": False, "error": "Invalid balance"}

        if self.peak_balance > 0:
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            if drawdown > self.max_drawdown_pct:
                self.logger.error(f"Max drawdown exceeded: {drawdown*100:.1f}%"); self.stopped = True
                return {"success": False, "error": "Max drawdown exceeded"}

        if self.consecutive_losses >= self.max_consecutive_losses:
            self.logger.error(f"Too many consecutive losses: {self.consecutive_losses}"); self.stopped = True
            return {"success": False, "error": "Too many consecutive losses"}

        if self.current_balance < self.min_order_usdt:
            self.logger.error(f"Balance too low: ${self.current_balance:.2f}"); self.stopped = True
            return {"success": False, "error": "Balance too low"}

        klines = AdvancedTA.get_klines(self.symbol, self.base_url, interval="1m", limit=300)
        if not klines:
            self.logger.warning("Could not fetch market data - skipping")
            self.skipped_trades += 1; self.skipped_count += 1
            return {"success": False, "error": "No market data", "skipped": True}

        crisis_score = self.context_country["opportunity_score"] if self.context_country else 0
        wst_class = self.context_country["wst_class"] if self.context_country else "Periphery"
        analysis = EinsteinStrategy.analyze_market(klines, crisis_score, wst_class)

        self.logger.info(f"Signal: {analysis['signal']} ({analysis['strength']}) | "
                          f"Passing: {analysis['passing_conditions']}/{analysis['total_conditions']} | "
                          f"Confidence: {analysis['confidence']:.2f}")

        passing = analysis['passing_conditions']
        if passing < self.min_passing_conditions:
            self.logger.info(f"Only {passing}/{analysis['total_conditions']} passing - skipping")
            self.skipped_trades += 1; self.skipped_count += 1
            if self.skipped_count >= self.max_skips_before_pause:
                self.logger.warning(f"{self.skipped_count} consecutive skips - pausing 60s")
                time.sleep(60); self.skipped_count = 0
            return {"success": False, "error": "Not enough conditions passing", "skipped": True}

        # FIX: new expectancy gate, on top of the condition-count filter
        if not self._has_positive_expectancy(analysis):
            self.logger.info("Signal passes condition count but fails fee-aware expectancy check - skipping")
            self.skipped_trades += 1; self.skipped_count += 1
            return {"success": False, "error": "Non-positive expectancy after fees", "skipped": True}

        self.skipped_count = 0
        current_price = self.get_current_price()
        if not current_price:
            return {"success": False, "error": "No price data"}

        position_size = self.calculate_position_size(analysis)
        buy_amount = min(position_size, self.current_balance * 0.30)

        self.logger.info(f"Placing BUY LIMIT order for ~${buy_amount:.2f}")
        buy_order = self.place_limit_order_entry(side="BUY", amount=buy_amount)
        if "error" in buy_order:
            self.logger.error(f"Failed to place buy order: {buy_order}")
            return {"success": False, "error": buy_order.get("error", "Buy order failed")}

        order_id = buy_order.get("orderId")
        if not order_id:
            return {"success": False, "error": "Missing orderId"}

        filled = False
        start_time = time.time()
        while not filled:
            status = self.get_order_status(order_id)
            if status.get("status") == "FILLED":
                filled = True
                executed_qty = float(status.get("executedQty", 0))
                cum_quote = float(status.get("cummulativeQuoteQty", 0))
                if executed_qty > 0 and cum_quote > 0:
                    self.buy_price = cum_quote / executed_qty
                    self.buy_qty = executed_qty
                else:
                    self.buy_price = float(status.get("price", current_price))
                    self.buy_qty = float(status.get("origQty", 0))
                self.logger.info(f"BUY Filled: {self.buy_qty:.8f} @ ${self.buy_price:.2f}")
                break
            if status.get("status") == "CANCELED":
                self.logger.warning("Order cancelled"); break

            current_mid = self.get_current_price()
            if current_mid and self.buy_price:
                if abs(current_mid - self.buy_price) / self.buy_price > 0.002:
                    self.logger.info("Price moved, adjusting order..."); self.cancel_order(order_id); break

            time.sleep(1)
            if time.time() - start_time > 60:
                self.logger.warning("Limit order taking too long, converting to market...")
                self.cancel_order(order_id)
                market_buy = self.place_market_order("BUY", buy_amount, is_quantity=False)
                if "error" in market_buy:
                    return {"success": False, "error": "Market buy failed"}
                self.buy_price = float(market_buy.get("price", current_price))
                self.buy_qty = float(market_buy.get("executedQty", 0))
                filled = True; break

        if not filled or not self.buy_qty or self.buy_qty <= 0:
            return {"success": False, "error": "Buy order failed"}

        self.last_known_qty = self.buy_qty

        atr_stop = EinsteinMath.optimal_stop_loss(analysis['atr'], analysis['volatility'], analysis['confidence'])
        stop_price = self.buy_price - atr_stop
        target_price = self.buy_price * (1 + self.target_profit_pct)

        # FIX: min_stop/max_stop were swapped in v11, which silently
        # disabled ATR-adaptive widening. min_stop = the tightest allowed
        # stop (closest to entry); max_stop = the widest allowed stop
        # (furthest from entry). Both expressed as prices below entry.
        min_stop = self.buy_price * (1 - self.stop_loss_pct)   # tightest (closest)
        max_stop = self.buy_price * (1 - 0.02)                  # widest (furthest)
        stop_price = min(min_stop, max(max_stop, stop_price))

        if analysis['sr']['near_resistance']:
            resistance = analysis['sr']['resistance']
            if resistance < target_price:
                target_price = min(target_price, resistance * 0.998)

        actual_risk = self.buy_price - stop_price
        actual_reward = target_price - self.buy_price
        rr_ratio = actual_reward / actual_risk if actual_risk > 0 else 0
        self.logger.info(f"Target: ${target_price:.2f} | Stop: ${stop_price:.2f} | R:R 1:{rr_ratio:.2f}")

        sell_qty = self.buy_qty
        sell_order = self.place_limit_order(side="SELL", quantity=sell_qty, price=target_price)

        stopped_out = False
        if "error" in sell_order:
            fallback_sell = self.place_market_order("SELL", sell_qty, is_quantity=True)
            if "error" in fallback_sell:
                return {"success": False, "error": "Sell order failed"}
            exit_price = float(fallback_sell.get("price", self.buy_price)) or self.buy_price
        else:
            sell_order_id = sell_order.get("orderId")
            if not sell_order_id:
                return {"success": False, "error": "Missing sell orderId"}

            sell_filled = False
            sell_start = time.time()
            exit_price = target_price
            while not sell_filled:
                now = time.time()
                status = self.get_order_status(sell_order_id)
                if status.get("status") == "FILLED":
                    sell_filled = True
                    cum_quote = float(status.get("cummulativeQuoteQty", 0))
                    executed_qty = float(status.get("executedQty", 0))
                    exit_price = cum_quote / executed_qty if executed_qty > 0 and cum_quote > 0 else float(status.get("price", target_price))
                    self.logger.info(f"SELL Filled @ ${exit_price:.2f}")
                    break

                if now - sell_start > 1:
                    current_price = self.get_current_price()
                    if current_price and current_price <= stop_price:
                        self.logger.warning(f"STOP-LOSS hit: ${current_price:.2f}")
                        self.cancel_order(sell_order_id)
                        exit_res = self.place_market_order("SELL", self.buy_qty, is_quantity=True)
                        if "error" in exit_res:
                            time.sleep(1); continue
                        sell_filled = True; stopped_out = True
                        exit_price = float(exit_res.get("price", current_price)) or current_price
                        self.logger.info(f"Stopped out @ ${exit_price:.2f}")
                        break

                if now - sell_start > self.chase_timeout_sec:
                    self.cancel_order(sell_order_id)
                    exit_res = self.place_market_order("SELL", self.buy_qty, is_quantity=True)
                    if "error" in exit_res:
                        time.sleep(1); continue
                    sell_filled = True
                    exit_price = float(exit_res.get("price", self.buy_price)) or self.buy_price
                    self.logger.info(f"SELL Filled @ ${exit_price:.2f} (chased)")
                    break

                time.sleep(1)

        realized_pnl = (exit_price - self.buy_price) * self.buy_qty
        fee_estimate = (self.buy_qty * self.buy_price * self.maker_fee_rate) + (self.buy_qty * exit_price * self.taker_fee_rate)
        net_pnl = realized_pnl - fee_estimate
        self.total_fees += fee_estimate

        self.logger.info(f"P&L: ${realized_pnl:.4f} (net ${net_pnl:.4f})" + (" [stopped]" if stopped_out else ""))

        self.running_pnl += net_pnl
        self.current_balance = max(0, self.total_balance_usdt + self.running_pnl)
        self.total_trades += 1

        if net_pnl > 0:
            self.win_count += 1; self.consecutive_wins += 1; self.consecutive_losses = 0
            if self.current_balance > self.peak_balance:
                self.peak_balance = self.current_balance
        else:
            self.loss_count += 1; self.consecutive_losses += 1; self.consecutive_wins = 0

        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        self.logger.info(f"Win Rate: {win_rate:.1f}% ({self.win_count}W/{self.loss_count}L) | Balance: ${self.current_balance:.2f}")

        result = {"success": True, "cycle": cycle_number, "entry_price": self.buy_price, "exit_price": exit_price,
                  "quantity": self.buy_qty, "profit": realized_pnl, "net_profit": net_pnl, "fees": fee_estimate,
                  "profit_percent": (realized_pnl / (self.buy_price * self.buy_qty)) * 100 if self.buy_price * self.buy_qty > 0 else 0,
                  "stopped_out": stopped_out, "balance_after": self.current_balance,
                  "consecutive_wins": self.consecutive_wins, "consecutive_losses": self.consecutive_losses,
                  "win_rate": win_rate, "passing_conditions": analysis['passing_conditions'],
                  "timestamp": datetime.now().isoformat()}

        self.cycle_stats["total_cycles"] += 1
        if net_pnl > 0:
            self.cycle_stats["successful_cycles"] += 1; self.cycle_stats["total_profit"] += net_pnl
        else:
            self.cycle_stats["failed_cycles"] += 1; self.cycle_stats["total_loss"] += abs(net_pnl)
        self.cycle_stats["net_profit"] += net_pnl
        self.cycle_stats["cycle_results"].append(result)
        self.trade_history.append(result)
        return result

    def run_forever(self, delay_between_cycles: int = 10):
        self._check_connectivity()
        self._get_exchange_info()
        self._initialize_balance()

        self.logger.info("\nStarting live trading loop. Press Ctrl+C to stop.")
        self.cycle_stats["start_time"] = datetime.now()
        cycle_num = 1
        while not self.stopped:
            try:
                result = self.run_cycle(cycle_number=cycle_num)
                if not result.get("skipped") and result.get("success"):
                    self.logger.info(f"Trade completed. Net profit: ${result.get('net_profit', 0):.4f}")
                self.export_results_to_csv()
                if self.consecutive_wins >= self.target_consecutive_wins:
                    self.logger.info(f"Target of {self.target_consecutive_wins} consecutive wins reached.")
                    self.stopped = True; break
                wait_time = delay_between_cycles + random.uniform(0, 3)
                time.sleep(wait_time)
                cycle_num += 1
            except KeyboardInterrupt:
                self.logger.info("Stopped by user"); break
            except Exception as e:
                self.logger.error(f"Error: {e}")
                time.sleep(delay_between_cycles * 2)
                cycle_num += 1

        self.cycle_stats["end_time"] = datetime.now()
        self.print_final_summary()
        self.export_final_report()

    def print_final_summary(self):
        stats = self.cycle_stats
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        self.logger.info("\n" + "="*70)
        self.logger.info(f"Total Cycles: {stats['total_cycles']} | Win Rate: {win_rate:.1f}%")
        self.logger.info(f"Net Profit: ${stats['net_profit']:.4f} | Fees Paid: ${self.total_fees:.4f}")
        self.logger.info(f"Final Balance: ${self.current_balance:.2f} (started ${self.starting_balance:.2f})")
        self.logger.info("="*70)

    def export_results_to_csv(self):
        if not self.cycle_stats["cycle_results"]:
            return
        filename = f"crisis_scalper_results_{datetime.now().strftime('%Y%m%d')}.csv"
        file_exists = os.path.isfile(filename)
        with open(filename, 'a', newline='') as csvfile:
            fieldnames = ['cycle', 'timestamp', 'entry_price', 'exit_price', 'quantity', 'profit',
                          'net_profit', 'fees', 'profit_percent', 'stopped_out', 'balance_after',
                          'consecutive_wins', 'consecutive_losses', 'win_rate', 'passing_conditions', 'success']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
            if not file_exists:
                writer.writeheader()
            latest = self.cycle_stats["cycle_results"][-1]
            writer.writerow({k: latest.get(k, '') for k in fieldnames})

    def export_final_report(self):
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        report = {"version": "12.0", "starting_balance": self.starting_balance,
                  "final_balance": self.current_balance, "peak_balance": self.peak_balance,
                  "win_rate": win_rate, "total_trades": self.total_trades, "wins": self.win_count,
                  "losses": self.loss_count, "total_fees": self.total_fees, "summary": self.cycle_stats,
                  "trade_history": self.trade_history[-20:]}
        filename = f"crisis_scalper_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)
        self.logger.info(f"Report exported to: {filename}")

    # ====================================================================
    # BACKTESTER - run this before trusting the strategy with real money
    # ====================================================================

    def run_backtest(self, days_back: int = 3, verbose: bool = False) -> dict:
        """
        Walks forward through real historical 1-minute candles, applies the
        exact same analyze_market() decision logic used live, and simulates
        entries/exits with the same target/stop/fee assumptions. This does
        NOT guarantee future results will match, but it replaces "we assume
        a 55% win rate" with an actual measurement on real data, which is
        the minimum bar before trading a strategy like this with money.
        """
        print(f"Fetching ~{days_back} day(s) of 1m history for {self.symbol}...")
        candles_needed = days_back * 24 * 60
        all_klines = {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}

        end_time = None
        fetched = 0
        while fetched < candles_needed:
            batch = AdvancedTA.get_klines(self.symbol, self.base_url, interval="1m", limit=1000, end_time_ms=end_time)
            if not batch or not batch["timestamps"]:
                break
            for k in all_klines:
                all_klines[k] = batch[k] + all_klines[k]
            fetched += len(batch["timestamps"])
            end_time = batch["timestamps"][0] - 1
            time.sleep(0.2)  # be nice to the public endpoint

        total = len(all_klines["closes"])
        if total < 350:
            print("Not enough historical data returned to backtest.")
            return {}

        print(f"Backtesting over {total} candles (~{total/1440:.1f} days)...")

        trades = []
        i = 300  # need history for indicators
        in_position = False
        entry_price = entry_i = stop_price = target_price = None
        crisis_score = self.context_country["opportunity_score"] if self.context_country else 0
        wst_class = self.context_country["wst_class"] if self.context_country else "Periphery"
        round_trip_fee_pct = self.maker_fee_rate + self.taker_fee_rate

        while i < total:
            window = {k: all_klines[k][max(0, i-300):i] for k in all_klines}
            if not in_position:
                analysis = EinsteinStrategy.analyze_market(window, crisis_score, wst_class)
                if (analysis['passing_conditions'] >= self.min_passing_conditions
                        and self._has_positive_expectancy(analysis)):
                    entry_price = all_klines["closes"][i]
                    atr_stop = EinsteinMath.optimal_stop_loss(analysis['atr'], analysis['volatility'], analysis['confidence'])
                    min_stop = entry_price * (1 - self.stop_loss_pct)
                    max_stop = entry_price * (1 - 0.02)
                    stop_price = min(min_stop, max(max_stop, entry_price - atr_stop))
                    target_price = entry_price * (1 + self.target_profit_pct)
                    in_position = True
                    entry_i = i
            else:
                high = all_klines["highs"][i]
                low = all_klines["lows"][i]
                exit_price = None
                if low <= stop_price:
                    exit_price = stop_price
                elif high >= target_price:
                    exit_price = target_price
                elif i - entry_i > 240:  # 4-hour max hold, mirrors chase_timeout intent
                    exit_price = all_klines["closes"][i]

                if exit_price is not None:
                    gross_pnl_pct = (exit_price - entry_price) / entry_price
                    net_pnl_pct = gross_pnl_pct - round_trip_fee_pct
                    trades.append(net_pnl_pct)
                    if verbose:
                        print(f"  trade @{entry_i}: entry {entry_price:.2f} exit {exit_price:.2f} net {net_pnl_pct*100:.3f}%")
                    in_position = False
            i += 1

        if not trades:
            print("No trades were triggered by the strategy over this window.")
            return {"trades": 0}

        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        win_rate = len(wins) / len(trades)
        avg_win = sum(wins) / len(wins) if wins else 0
        avg_loss = sum(losses) / len(losses) if losses else 0
        expectancy_pct = sum(trades) / len(trades)

        print("\n" + "="*60)
        print("BACKTEST RESULTS (net of estimated fees)")
        print("="*60)
        print(f"  Trades:          {len(trades)}")
        print(f"  Win rate:        {win_rate*100:.1f}%")
        print(f"  Avg win:         {avg_win*100:.3f}%")
        print(f"  Avg loss:        {avg_loss*100:.3f}%")
        print(f"  Expectancy/trade:{expectancy_pct*100:.3f}%")
        print(f"  Total return:    {sum(trades)*100:.2f}% (naive, no compounding/sizing)")
        print("="*60)
        if expectancy_pct <= 0:
            print("Expectancy is NOT positive on this historical window.")
            print("Do not run this live as-is - the filter/thresholds need more work,")
            print("or this approach may not have a real edge on this symbol/timeframe.")
        else:
            print("Expectancy is positive on this window, but this is one sample of")
            print("history, on default parameters, with no walk-forward validation.")
            print("Treat this as a first checkpoint, not proof of a working system.")

        return {"trades": len(trades), "win_rate": win_rate, "avg_win": avg_win,
                "avg_loss": avg_loss, "expectancy_pct": expectancy_pct, "total_return_pct": sum(trades)}

# ========================================================================
# MAIN
# ========================================================================

if __name__ == "__main__":
    import sys

    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"

    if not API_KEY or not API_SECRET:
        print("API KEYS NOT FOUND"); sys.exit(1)

    bot = ScalperBotV12(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol="BTCUSDT",
        exchange_region="us",
        log_level="INFO",
    )

    # Default entrypoint runs a backtest, NOT live trading. This is
    # deliberate: the previous version went straight to run_forever()
    # with an unvalidated strategy and lost money. Look at the numbers
    # this prints, and only call bot.run_forever(...) yourself once
    # you've decided the expectancy is something you're willing to risk
    # real money on - and ideally after testing on a longer/different
    # historical window than the 3 days below.
    bot.run_backtest(days_back=3, verbose=False)

    # Uncomment only after reviewing the backtest output above:
    # bot.run_forever(delay_between_cycles=10)
