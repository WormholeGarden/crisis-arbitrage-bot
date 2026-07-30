#!/usr/bin/env python3
"""
CRISIS ARBITRAGE SCALPER v12.2 - MULTI-TIMEFRAME + ALTCOIN SEARCH
================================================================
v12.2 additions:
- Automated 4h and 1d testing with wider parameter ranges
- Altcoin support (ETH, SOL) for finding actual edge
- Comprehensive reporting of what actually works
- No fake results — if nothing works, it says so honestly
================================================================
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
# CRISIS SCORING ENGINE (context/logging only)
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
# TECHNICAL ANALYSIS - Generalized for ANY interval
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
# STRATEGY
# ========================================================================

class EinsteinStrategy:
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
# SCALPER BOT - with validation framework
# ========================================================================

class ScalperBotV12:

    def __init__(self, api_key: str, api_secret: str, symbol: str = "BTCUSDT",
                 exchange_region: str = "us", log_level: str = "INFO",
                 interval: str = "1m"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.interval = interval
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
        self.logger.info(f"CRISIS ARBITRAGE SCALPER v12.2 - {symbol} - {interval}")
        self.logger.info("="*70)

    def _check_connectivity(self):
        self.logger.info("Running startup connectivity check...")
        ticker = self.get_order_book_ticker()
        if not ticker:
            self.logger.error("STARTUP CHECK FAILED")
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
        win_rate = analysis.get('expected_win_rate', 0.5)
        round_trip_fee_pct = self.maker_fee_rate + self.taker_fee_rate
        net_target = self.target_profit_pct - round_trip_fee_pct
        net_stop = self.stop_loss_pct + round_trip_fee_pct
        expectancy = (win_rate * net_target) - ((1 - win_rate) * net_stop)
        return expectancy > 0

    def run_cycle(self, cycle_number: int = 0) -> dict:
        # Live trading method - kept for compatibility
        pass

    def run_forever(self, delay_between_cycles: int = 10):
        self._check_connectivity()
        self._get_exchange_info()
        self._initialize_balance()
        self.logger.info("\nStarting live trading loop. Press Ctrl+C to stop.")
        # Live trading implementation would go here
        pass

    def print_final_summary(self):
        pass

    def export_results_to_csv(self):
        pass

    def export_final_report(self):
        pass

    # ====================================================================
    # BACKTESTER - Core validation framework
    # ====================================================================

    def _fetch_historical_klines(self, days_back: int) -> Dict:
        print(f"Fetching ~{days_back} day(s) of {self.interval} history for {self.symbol}...")

        interval_limits = {"1m": 1440, "3m": 1440, "5m": 1440, "15m": 1440, "30m": 1440,
                           "1h": 1440, "2h": 1440, "4h": 1440, "6h": 1440, "8h": 1440,
                           "12h": 1440, "1d": 1440, "3d": 1440, "1w": 1440}
        max_candles_per_request = interval_limits.get(self.interval, 1440)

        interval_minutes = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
                            "1h": 60, "2h": 120, "4h": 240, "6h": 360, "8h": 480,
                            "12h": 720, "1d": 1440, "3d": 4320, "1w": 10080}
        candles_per_day = 1440 // interval_minutes.get(self.interval, 1)
        candles_needed = days_back * candles_per_day

        all_klines = {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
        end_time = None
        fetched = 0
        while fetched < candles_needed:
            batch = AdvancedTA.get_klines(self.symbol, self.base_url, interval=self.interval,
                                          limit=min(max_candles_per_request, candles_needed - fetched),
                                          end_time_ms=end_time)
            if not batch or not batch["timestamps"]:
                break
            for k in all_klines:
                all_klines[k] = batch[k] + all_klines[k]
            fetched += len(batch["timestamps"])
            end_time = batch["timestamps"][0] - 1
            time.sleep(0.2)
        return all_klines

    def _precompute_analyses(self, klines: Dict, label: str = "") -> List[Optional[Dict]]:
        total = len(klines["closes"])
        crisis_score = self.context_country["opportunity_score"] if self.context_country else 0
        wst_class = self.context_country["wst_class"] if self.context_country else "Periphery"
        analyses: List[Optional[Dict]] = [None] * total

        report_every = max(1, (total - 300) // 10)
        for i in range(300, total):
            window = {k: klines[k][i-300:i] for k in klines}
            analyses[i] = EinsteinStrategy.analyze_market(window, crisis_score, wst_class)
            if label and (i - 300) % report_every == 0:
                pct = (i - 300) / max(1, total - 300) * 100
                print(f"  [{label}] analyzing candles: {pct:.0f}%")
        return analyses

    def _simulate_trades_from_analyses(self, analyses: List[Optional[Dict]], klines: Dict,
                                        min_passing_conditions: int, stop_loss_pct: float,
                                        target_profit_pct: float) -> List[float]:
        total = len(klines["closes"])
        trades = []
        in_position = False
        entry_price = entry_i = stop_price = target_price = None
        round_trip_fee_pct = self.maker_fee_rate + self.taker_fee_rate

        for i in range(300, total):
            if not in_position:
                analysis = analyses[i]
                win_rate = analysis.get('expected_win_rate', 0.5)
                net_target = target_profit_pct - round_trip_fee_pct
                net_stop = stop_loss_pct + round_trip_fee_pct
                positive_expectancy = (win_rate * net_target) - ((1 - win_rate) * net_stop) > 0

                if analysis['passing_conditions'] >= min_passing_conditions and positive_expectancy:
                    entry_price = klines["closes"][i]
                    atr_stop = EinsteinMath.optimal_stop_loss(analysis['atr'], analysis['volatility'], analysis['confidence'])
                    min_stop = entry_price * (1 - stop_loss_pct)
                    max_stop = entry_price * (1 - 0.02)
                    stop_price = min(min_stop, max(max_stop, entry_price - atr_stop))
                    target_price = entry_price * (1 + target_profit_pct)
                    in_position = True
                    entry_i = i
            else:
                high = klines["highs"][i]
                low = klines["lows"][i]
                exit_price = None
                if low <= stop_price:
                    exit_price = stop_price
                elif high >= target_price:
                    exit_price = target_price
                # Allow longer holds for larger intervals
                max_hold = 48 if self.interval in ["1h", "2h", "4h"] else 24 if self.interval in ["1m", "5m", "15m", "30m"] else 12
                if i - entry_i > max_hold:
                    exit_price = klines["closes"][i]

                if exit_price is not None:
                    gross_pnl_pct = (exit_price - entry_price) / entry_price
                    trades.append(gross_pnl_pct - round_trip_fee_pct)
                    in_position = False

        return trades

    @staticmethod
    def _summarize_trades(trades: List[float]) -> Dict:
        if not trades:
            return {"trades": 0, "win_rate": 0, "avg_win": 0, "avg_loss": 0, "expectancy_pct": 0, "total_return_pct": 0}
        wins = [t for t in trades if t > 0]
        losses = [t for t in trades if t <= 0]
        return {
            "trades": len(trades),
            "win_rate": len(wins) / len(trades),
            "avg_win": sum(wins) / len(wins) if wins else 0,
            "avg_loss": sum(losses) / len(losses) if losses else 0,
            "expectancy_pct": sum(trades) / len(trades),
            "total_return_pct": sum(trades),
        }

    def run_robust_validation(self, days_back: int = 90, n_folds: int = 5,
                               alpha: float = 0.05, min_trades_per_fold: int = 5,
                               condition_options: List[int] = None,
                               stop_options: List[float] = None,
                               target_options: List[float] = None) -> List[Dict]:
        """Run robust multi-block validation with custom parameter ranges."""
        
        all_klines = self._fetch_historical_klines(days_back)
        total = len(all_klines["closes"])
        if total < 300 * (n_folds + 1):
            print(f"Not enough historical data for {n_folds} blocks with proper lookback.")
            return []

        # Use provided ranges or auto-detect
        if condition_options is None:
            condition_options = [3, 4, 5, 6, 7]
        
        if stop_options is None or target_options is None:
            # Auto-detect based on interval
            if self.interval in ["1m", "3m", "5m"]:
                stop_options = [0.005, 0.008, 0.010, 0.012, 0.015]
                target_options = [0.008, 0.012, 0.015, 0.020, 0.025]
            elif self.interval in ["15m", "30m", "1h"]:
                stop_options = [0.008, 0.012, 0.018, 0.025, 0.032]
                target_options = [0.015, 0.022, 0.030, 0.040, 0.050]
            elif self.interval in ["2h", "4h", "6h", "8h", "12h"]:
                stop_options = [0.015, 0.022, 0.030, 0.040, 0.050]
                target_options = [0.025, 0.035, 0.050, 0.065, 0.080]
            else:  # 1d, 3d, 1w
                stop_options = [0.025, 0.035, 0.050, 0.070, 0.090]
                target_options = [0.040, 0.060, 0.080, 0.100, 0.120]

        print(f"\nTesting {self.symbol} - {self.interval}")
        print(f"  min_conditions: {condition_options}")
        print(f"  stop_loss: {[f'{s*100:.1f}%' for s in stop_options]}")
        print(f"  target_profit: {[f'{t*100:.1f}%' for t in target_options]}")

        block_size = total // n_folds
        blocks = []
        for f in range(n_folds):
            start = f * block_size
            end = total if f == n_folds - 1 else (f + 1) * block_size
            lookback_start = max(0, start - 300)
            block = {k: all_klines[k][lookback_start:end] for k in all_klines}
            blocks.append((block, start - lookback_start))

        n_combos = len(condition_options) * len(stop_options) * len(target_options)
        bonferroni_alpha = alpha / n_combos
        print(f"  Testing {n_combos} combinations. Bonferroni-corrected: p < {bonferroni_alpha:.5f}")
        print(f"  {n_folds} blocks of ~{block_size / self._candles_per_day():.1f} days each")

        print("\nPrecomputing indicators for each block...")
        block_analyses = []
        for idx, (block, offset) in enumerate(blocks):
            analyses = self._precompute_analyses(block, label=f"block {idx+1}/{n_folds}")
            block_analyses.append(analyses)

        normal = statistics.NormalDist()
        results = []

        for min_cond in condition_options:
            for stop_pct in stop_options:
                for target_pct in target_options:
                    pooled_trades = []
                    blocks_positive = 0
                    blocks_tested = 0

                    for (block, offset), analyses in zip(blocks, block_analyses):
                        trades = self._simulate_trades_from_analyses(
                            analyses, block, min_cond, stop_pct, target_pct)
                        if len(trades) < min_trades_per_fold:
                            continue
                        blocks_tested += 1
                        block_summary = self._summarize_trades(trades)
                        if block_summary["expectancy_pct"] > 0:
                            blocks_positive += 1
                        pooled_trades.extend(trades)

                    if blocks_tested < n_folds - 1 or len(pooled_trades) < min_trades_per_fold * 2:
                        continue

                    consistency_ok = blocks_positive >= max(3, int(0.7 * blocks_tested))

                    mean_ret = sum(pooled_trades) / len(pooled_trades)
                    if len(pooled_trades) > 1:
                        stdev_ret = statistics.stdev(pooled_trades)
                    else:
                        stdev_ret = 0
                    if stdev_ret == 0:
                        continue
                    se = stdev_ret / (len(pooled_trades) ** 0.5)
                    z = mean_ret / se
                    p_value = 2 * (1 - normal.cdf(abs(z)))

                    significant = (mean_ret > 0) and (p_value < bonferroni_alpha)

                    if consistency_ok and significant:
                        results.append({
                            "min_passing_conditions": min_cond,
                            "stop_loss_pct": stop_pct,
                            "target_profit_pct": target_pct,
                            "blocks_positive": blocks_positive,
                            "blocks_tested": blocks_tested,
                            "pooled_trades": len(pooled_trades),
                            "mean_return_pct": mean_ret,
                            "p_value": p_value,
                            "win_rate": len([t for t in pooled_trades if t > 0]) / len(pooled_trades),
                            "total_return_pct": sum(pooled_trades),
                        })

        results.sort(key=lambda r: r["p_value"])
        return results

    def _candles_per_day(self) -> float:
        interval_minutes = {"1m": 1, "3m": 3, "5m": 5, "15m": 15, "30m": 30,
                            "1h": 60, "2h": 120, "4h": 240, "6h": 360, "8h": 480,
                            "12h": 720, "1d": 1440, "3d": 4320, "1w": 10080}
        return 1440 / interval_minutes.get(self.interval, 1)

# ========================================================================
# SEARCH ENGINE - Test multiple symbols and intervals
# ========================================================================

def run_full_search(api_key: str, api_secret: str):
    """Test multiple combinations to find something that actually works."""
    
    print("="*70)
    print("FULL STRATEGY SEARCH - FINDING WHAT ACTUALLY WORKS")
    print("="*70)
    print("\nThis will test multiple symbols and intervals with rigorous")
    print("multi-block validation. This takes time but finds real edge.")
    print("Fee drag: 0.2% round-trip on Binance US")
    print("="*70)
    
    # Configuration: (symbol, interval, days_back, custom_ranges)
    tests = [
        # BTC on longer timeframes
        ("BTCUSDT", "4h", 180, None, None, None),
        ("BTCUSDT", "1d", 365, None, None, None),
        
        # ETH - more volatile, might have edge
        ("ETHUSDT", "1h", 90, None, None, None),
        ("ETHUSDT", "4h", 180, None, None, None),
        ("ETHUSDT", "1d", 365, None, None, None),
        
        # SOL - even more volatile, altcoin edge
        ("SOLUSDT", "1h", 90, None, None, None),
        ("SOLUSDT", "4h", 180, None, None, None),
    ]
    
    all_results = {}
    best_overall = None
    best_score = -999
    
    for symbol, interval, days, cond_opts, stop_opts, target_opts in tests:
        print("\n" + "="*70)
        print(f"TESTING: {symbol} - {interval} ({days} days)")
        print("="*70)
        
        try:
            bot = ScalperBotV12(
                api_key=api_key,
                api_secret=api_secret,
                symbol=symbol,
                exchange_region="us",
                log_level="WARNING",
                interval=interval
            )
            
            # Custom parameter ranges for altcoins (wider to capture volatility)
            if "ETH" in symbol or "SOL" in symbol:
                if interval in ["1h"]:
                    stop_opts = [0.010, 0.015, 0.022, 0.030, 0.040]
                    target_opts = [0.020, 0.030, 0.040, 0.055, 0.070]
                elif interval in ["4h"]:
                    stop_opts = [0.020, 0.030, 0.040, 0.055, 0.070]
                    target_opts = [0.035, 0.050, 0.065, 0.085, 0.100]
                else:  # 1d
                    stop_opts = [0.030, 0.045, 0.060, 0.080, 0.100]
                    target_opts = [0.050, 0.070, 0.090, 0.120, 0.150]
            
            results = bot.run_robust_validation(
                days_back=days,
                n_folds=5,
                min_trades_per_fold=5,
                condition_options=[3, 4, 5, 6, 7],
                stop_options=stop_opts,
                target_options=target_opts
            )
            
            key = f"{symbol}_{interval}"
            all_results[key] = results
            
            if results:
                print(f"\n✅ FOUND {len(results)} CANDIDATE(S) for {key}")
                for r in results[:3]:
                    print(f"  conditions>={r['min_passing_conditions']} stop={r['stop_loss_pct']*100:.1f}% "
                          f"target={r['target_profit_pct']*100:.1f}%  |  "
                          f"mean return/trade={r['mean_return_pct']*100:.4f}%  |  "
                          f"win rate={r['win_rate']*100:.1f}%  |  "
                          f"p={r['p_value']:.6f}")
                    
                    # Score: prioritize mean return * win rate * trades
                    score = r['mean_return_pct'] * r['win_rate'] * min(1, r['pooled_trades']/20)
                    if score > best_score:
                        best_score = score
                        best_overall = (symbol, interval, r)
            else:
                print(f"\n❌ No valid candidates for {key}")
                
        except Exception as e:
            print(f"Error testing {symbol} {interval}: {e}")
    
    # Final summary
    print("\n" + "="*70)
    print("FINAL SEARCH SUMMARY")
    print("="*70)
    
    if best_overall:
        symbol, interval, params = best_overall
        print("\n🏆 BEST OVERALL CANDIDATE:")
        print(f"  Symbol: {symbol}")
        print(f"  Interval: {interval}")
        print(f"  min_passing_conditions: {params['min_passing_conditions']}")
        print(f"  stop_loss_pct: {params['stop_loss_pct']:.3f} ({params['stop_loss_pct']*100:.1f}%)")
        print(f"  target_profit_pct: {params['target_profit_pct']:.3f} ({params['target_profit_pct']*100:.1f}%)")
        print(f"  Mean return per trade: {params['mean_return_pct']*100:.3f}%")
        print(f"  Win rate: {params['win_rate']*100:.1f}%")
        print(f"  Total trades across blocks: {params['pooled_trades']}")
        print(f"  p-value: {params['p_value']:.6f}")
        print("\nTo use this live, set these parameters in your bot:")
        print(f"  bot.min_passing_conditions = {params['min_passing_conditions']}")
        print(f"  bot.stop_loss_pct = {params['stop_loss_pct']}")
        print(f"  bot.target_profit_pct = {params['target_profit_pct']}")
        print(f"  # And change symbol to '{symbol}', interval to '{interval}'")
    else:
        print("\n❌ NO VALID CANDIDATES FOUND IN ANY CONFIGURATION.")
        print("\nThis is an honest result. It means with 0.2% round-trip fees,")
        print("this indicator set does not produce a statistically significant")
        print("edge on any tested symbol/timeframe combination.")
        print("\nNext steps:")
        print("  1. Try a different indicator set (e.g., volume profile, order flow)")
        print("  2. Use a lower-fee exchange (Binance US is already low at 0.2%)")
        print("  3. Try higher timeframes (4h, 1d) with even wider parameters")
        print("  4. Consider a completely different strategy (not mean-reversion)")
    
    print("\n" + "="*70)

# ========================================================================
# MAIN
# ========================================================================

if __name__ == "__main__":
    import sys

    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"

    if not API_KEY or not API_SECRET:
        print("API KEYS NOT FOUND")
        sys.exit(1)

    # Run the full search across multiple symbols and timeframes
    run_full_search(API_KEY, API_SECRET)
