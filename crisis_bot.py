#!/usr/bin/env python3
"""
🚀 CRISIS ARBITRAGE SCALPER v10.0 - COMPLETE EDITION
============================================================
INTEGRATES:
- WST (World Systems Theory) structural scoring
- FSI 2024 (Fragile States Index) country risk
- 5 Conditions trading strategy
- Einstein-level mathematical analysis
- Advanced technical indicators
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
    if value <= 0:
        return "0.00000000"
    formatted = f"{Decimal(str(value)):.8f}"
    return formatted

def format_price(value: float) -> str:
    return f"{Decimal(str(value)):.2f}"

# ========================================================================
# 🧠 CRISIS SCORING ENGINE (FSI + WST)
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
# 🧠 EINSTEIN-LEVEL MATHEMATICAL ANALYSIS
# ========================================================================

class EinsteinMath:
    """Pure mathematical edge - no emotion, just numbers"""
    
    @staticmethod
    def kelly_criterion(win_rate: float, avg_win: float, avg_loss: float) -> float:
        if avg_loss == 0:
            return 0.02
        b = avg_win / avg_loss
        q = 1 - win_rate
        kelly = (win_rate * b - q) / b
        half_kelly = max(0.01, min(0.10, kelly * 0.5))
        return half_kelly
    
    @staticmethod
    def sharpe_ratio(returns: List[float], risk_free_rate: float = 0.0) -> float:
        if not returns or len(returns) < 2:
            return 0.0
        avg_return = sum(returns) / len(returns)
        std_dev = statistics.stdev(returns) if len(returns) > 1 else 0.001
        if std_dev == 0:
            return 0.0
        sharpe = (avg_return - risk_free_rate) / std_dev
        return sharpe
    
    @staticmethod
    def risk_of_ruin(win_rate: float, risk_per_trade: float, account_size: float, max_loss: float) -> float:
        if win_rate >= 0.5:
            q = 1 - win_rate
            p = win_rate
            if p == q:
                return 1.0
            advantage = p - q
            ruin_prob = math.exp(-2 * advantage * (account_size / max_loss))
            return max(0, min(1, ruin_prob))
        else:
            return 1.0
    
    @staticmethod
    def optimal_stop_loss(atr: float, volatility: float, confidence: float) -> float:
        base_stop = atr * 1.5
        vol_multiplier = 1 + (volatility * 10)
        confidence_adjust = 1 - (confidence * 0.3)
        optimal_stop = base_stop * vol_multiplier * confidence_adjust
        return min(max(optimal_stop, atr * 0.5), atr * 3.0)

# ========================================================================
# 📊 ADVANCED TECHNICAL ANALYSIS
# ========================================================================

class AdvancedTA:
    """Multi-timeframe analysis with 8+ indicators"""
    
    @staticmethod
    def get_klines(symbol: str, base_url: str, interval: str = "1m", limit: int = 300) -> Optional[Dict]:
        try:
            url = f"{base_url}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": interval,
                "limit": limit
            }
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
    
    @staticmethod
    def calculate_macd(closes: List[float]) -> Dict:
        if len(closes) < 26:
            return {"macd": 0, "signal": 0, "histogram": 0}
        
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
        
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
            "bullish_cross": bullish_cross,
            "bearish_cross": bearish_cross
        }
    
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
    def calculate_bollinger_bands(closes: List[float], period: int = 20, std_dev: float = 2) -> Dict:
        if len(closes) < period:
            return {"upper": closes[-1] if closes else 0, "middle": closes[-1] if closes else 0, "lower": closes[-1] if closes else 0}
        
        middle = sum(closes[-period:]) / period
        squared_deviations = [(x - middle) ** 2 for x in closes[-period:]]
        std = (sum(squared_deviations) / period) ** 0.5
        
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        position = (closes[-1] - lower) / (upper - lower) if upper != lower else 0.5
        width = (upper - lower) / middle
        
        return {
            "upper": upper,
            "middle": middle,
            "lower": lower,
            "position": position,
            "width": width,
            "squeeze": width < 0.02
        }
    
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
    def calculate_vwap(highs: List[float], lows: List[float], closes: List[float], volumes: List[float]) -> float:
        if not volumes:
            return closes[-1] if closes else 0
        
        typical_prices = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        
        start = max(0, len(typical_prices) - 50)
        typical_prices = typical_prices[start:]
        volumes_used = volumes[start:]
        
        if not volumes_used or sum(volumes_used) == 0:
            return closes[-1] if closes else 0
        
        vwap = sum(tp * v for tp, v in zip(typical_prices, volumes_used)) / sum(volumes_used)
        return vwap
    
    @staticmethod
    def calculate_support_resistance(highs: List[float], lows: List[float], closes: List[float]) -> Dict:
        if len(closes) < 20:
            return {"support": min(lows), "resistance": max(highs)}
        
        lookback = 10
        supports = []
        resistances = []
        
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
        
        return {
            "support": recent_support,
            "resistance": recent_resistance,
            "near_support": near_support,
            "near_resistance": near_resistance,
            "support_strength": min(5, support_strength),
            "resistance_strength": min(5, resistance_strength)
        }
    
    @staticmethod
    def calculate_stochastic(closes: List[float], highs: List[float], lows: List[float], period: int = 14) -> float:
        if len(closes) < period:
            return 50.0
        
        highest_high = max(highs[-period:])
        lowest_low = min(lows[-period:])
        
        if highest_high == lowest_low:
            return 50.0
        
        stochastic = ((closes[-1] - lowest_low) / (highest_high - lowest_low)) * 100
        return stochastic
    
    @staticmethod
    def calculate_volume_profile(volumes: List[float]) -> Dict:
        if not volumes:
            return {"trend": "neutral", "strength": 0}
        
        avg_volume = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        current_volume = volumes[-1]
        volume_ratio = current_volume / avg_volume if avg_volume > 0 else 1
        
        if len(volumes) >= 10:
            recent_volume_avg = sum(volumes[-10:]) / 10
            older_volume_avg = sum(volumes[-20:-10]) / 10 if len(volumes) >= 20 else recent_volume_avg
            volume_trend = recent_volume_avg / older_volume_avg if older_volume_avg > 0 else 1
        else:
            volume_trend = 1
        
        return {
            "ratio": volume_ratio,
            "trend": volume_trend,
            "spike": volume_ratio > 2.0,
            "strength": min(1.0, volume_ratio / 3.0)
        }

# ========================================================================
# 📊 5 CONDITIONS STRATEGY WITH WST/FSI INTEGRATION
# ========================================================================

class EinsteinStrategy:
    """5 CONDITIONS - With WST/FSI crisis scoring"""
    
    @staticmethod
    def analyze_market(klines: Dict, crisis_score: float = 0.0, wst_class: str = "Periphery") -> Dict:
        if not klines or len(klines['closes']) < 50:
            return {"signal": "neutral", "confidence": 0, "reason": "Insufficient data"}
        
        closes = klines['closes']
        highs = klines['highs']
        lows = klines['lows']
        volumes = klines['volumes']
        current_price = closes[-1]
        
        # Calculate ALL indicators
        rsi = AdvancedTA.calculate_rsi(closes)
        macd = AdvancedTA.calculate_macd(closes)
        bb = AdvancedTA.calculate_bollinger_bands(closes)
        atr = AdvancedTA.calculate_atr(highs, lows, closes)
        vwap = AdvancedTA.calculate_vwap(highs, lows, closes, volumes)
        sr = AdvancedTA.calculate_support_resistance(highs, lows, closes)
        stochastic = AdvancedTA.calculate_stochastic(closes, highs, lows)
        volume_profile = AdvancedTA.calculate_volume_profile(volumes)
        
        # Multi-timeframe moving averages
        sma_5 = sum(closes[-5:]) / 5
        sma_10 = sum(closes[-10:]) / 10
        sma_20 = sum(closes[-20:]) / 20
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma_20
        
        # Momentum
        momentum_5 = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0
        momentum_10 = (closes[-1] - closes[-10]) / closes[-10] if len(closes) >= 10 else 0
        
        # Volatility
        returns = [(closes[i] - closes[i-1]) / closes[i-1] for i in range(1, len(closes))]
        volatility = statistics.stdev(returns[-30:]) if len(returns) >= 30 else 0.001
        
        # ============ WST/FSI CRISIS ADJUSTMENTS ============
        crisis_bonus = 0
        
        # Higher FSI = more crisis = more volatility = more opportunity
        if crisis_score > 0.6:
            crisis_bonus += 1
        if crisis_score > 0.7:
            crisis_bonus += 1
        
        # Periphery countries have more volatility
        if wst_class == "Periphery":
            crisis_bonus += 1
        elif wst_class == "Semi":
            crisis_bonus += 0.5
        
        # ============ BUILD SIGNAL ============
        bullish_signals = 0
        bearish_signals = 0
        strong_bullish = 0
        signal_reasons = []
        
        # Signal 1: RSI
        if rsi < 25 and current_price < sma_20:
            bullish_signals += 2
            strong_bullish += 1
            signal_reasons.append(f"🔥 RSI EXTREME OVERSOLD ({rsi:.1f})")
        elif rsi < 30 and current_price < sma_20:
            bullish_signals += 2
            signal_reasons.append(f"📊 RSI oversold ({rsi:.1f}) - BUY")
        elif rsi < 35:
            bullish_signals += 1
            signal_reasons.append(f"RSI low ({rsi:.1f}) - Good")
        elif rsi > 70:
            bearish_signals += 1
            signal_reasons.append(f"RSI high ({rsi:.1f}) - Not ideal")
        else:
            signal_reasons.append(f"RSI neutral ({rsi:.1f})")
        
        # Signal 2: MACD
        if macd['bullish_cross']:
            bullish_signals += 2
            strong_bullish += 1
            signal_reasons.append("🔥 MACD BULLISH CROSSOVER")
        elif macd['histogram'] > 0 and closes[-1] > closes[-2]:
            bullish_signals += 1
            signal_reasons.append("MACD positive - Good momentum")
        else:
            bearish_signals += 1
            signal_reasons.append("MACD negative")
        
        # Signal 3: Bollinger Bands
        if bb['position'] < 0.15 and current_price < sma_20:
            bullish_signals += 2
            strong_bullish += 1
            signal_reasons.append(f"🔥 AT LOWER BB ({bb['position']:.2f})")
        elif bb['position'] < 0.25:
            bullish_signals += 1
            signal_reasons.append(f"Near lower BB ({bb['position']:.2f})")
        elif bb['position'] > 0.80:
            bearish_signals += 1
            signal_reasons.append(f"⚠️ Near upper BB ({bb['position']:.2f})")
        else:
            signal_reasons.append(f"BB neutral ({bb['position']:.2f})")
        
        # Signal 4: Moving Averages
        if current_price > sma_5 > sma_10 > sma_20 > sma_50:
            bullish_signals += 2
            strong_bullish += 1
            signal_reasons.append("🔥 PERFECT TREND ALIGNMENT - ALL MAs UPTREND")
        elif current_price > sma_20 and current_price > sma_50:
            bullish_signals += 1
            signal_reasons.append("Uptrend confirmed")
        elif current_price < sma_20:
            bearish_signals += 1
            signal_reasons.append("Downtrend - Skip")
        else:
            signal_reasons.append("MA mixed")
        
        # Signal 5: Support/Resistance
        if sr['near_support'] and sr['support_strength'] >= 2:
            bullish_signals += 2
            strong_bullish += 1
            signal_reasons.append(f"🔥 STRONG SUPPORT (${sr['support']:.2f})")
        elif sr['near_support']:
            bullish_signals += 1
            signal_reasons.append(f"Near support (${sr['support']:.2f})")
        elif sr['near_resistance']:
            bearish_signals += 1
            signal_reasons.append(f"⚠️ Near resistance (${sr['resistance']:.2f})")
        
        # Signal 6: VWAP
        if current_price > vwap * 1.002:
            bullish_signals += 1
            signal_reasons.append("Above VWAP - Institutional support")
        elif current_price < vwap * 0.998:
            bearish_signals += 1
            signal_reasons.append("Below VWAP - Institutional pressure")
        else:
            signal_reasons.append("At VWAP level")
        
        # Signal 7: Stochastic
        if stochastic < 20 and current_price < sma_20:
            bullish_signals += 1
            strong_bullish += 1
            signal_reasons.append(f"🔥 STOCHASTIC OVERSOLD ({stochastic:.1f})")
        elif stochastic > 80:
            bearish_signals += 1
            signal_reasons.append(f"Stochastic overbought ({stochastic:.1f})")
        else:
            signal_reasons.append(f"Stochastic neutral ({stochastic:.1f})")
        
        # Signal 8: Volume
        if volume_profile['spike'] and current_price > sma_20:
            bullish_signals += 1
            signal_reasons.append("Volume spike confirmation")
        
        # Signal 9: Momentum
        if momentum_5 > 0.002 and momentum_10 > 0:
            bullish_signals += 1
            signal_reasons.append("Strong momentum - GOOD")
        elif momentum_5 > 0.001:
            bullish_signals += 1
            signal_reasons.append("Positive momentum")
        elif momentum_5 < -0.002:
            bearish_signals += 1
            signal_reasons.append("Negative momentum - Bad")
        
        # Signal 10: Volatility
        atr_pct = atr / current_price if current_price > 0 else 0
        if atr_pct < 0.004:
            bullish_signals += 1
            signal_reasons.append(f"Low volatility ({atr_pct*100:.2f}%) - Safe")
        elif atr_pct > 0.015:
            bearish_signals += 1
            signal_reasons.append(f"High volatility ({atr_pct*100:.2f}%) - Risky")
        
        # ============ CRISIS BONUS ============
        if crisis_bonus > 0:
            bullish_signals += crisis_bonus
            signal_reasons.append(f"🌍 CRISIS OPPORTUNITY BONUS: +{crisis_bonus}")
        
        # ============ 5 CONDITIONS DECISION ============
        total_signals = bullish_signals + bearish_signals
        if total_signals > 0:
            raw_confidence = (bullish_signals - bearish_signals) / total_signals
        else:
            raw_confidence = 0
        
        confidence = max(-1, min(1, raw_confidence))
        
        # Calculate how many conditions are PASSING
        passing_conditions = 0
        total_conditions = 10
        
        if raw_confidence > 0.15:
            passing_conditions += 1
        if strong_bullish >= 1:
            passing_conditions += 1
        if bullish_signals >= 3:
            passing_conditions += 1
        if bearish_signals <= 5:
            passing_conditions += 1
        if confidence > 0.15:
            passing_conditions += 1
        if bb['position'] < 0.55:
            passing_conditions += 1
        if 15 <= rsi <= 58:
            passing_conditions += 1
        if current_price > sma_20:
            passing_conditions += 1
        if current_price > vwap:
            passing_conditions += 1
        if crisis_bonus >= 1:
            passing_conditions += 1
        
        if passing_conditions >= 6:
            signal = "BUY"
            signal_strength = "strong"
            expected_win_rate = 0.62
        elif passing_conditions >= 5:
            signal = "BUY"
            signal_strength = "moderate"
            expected_win_rate = 0.58
        elif passing_conditions >= 4:
            signal = "CONSIDER"
            signal_strength = "weak"
            expected_win_rate = 0.50
        else:
            signal = "NEUTRAL"
            signal_strength = "weak"
            expected_win_rate = 0.45
        
        if signal == "BUY":
            kelly_fraction = EinsteinMath.kelly_criterion(expected_win_rate, 0.02, 0.008)
        else:
            kelly_fraction = 0.01
        
        return {
            "signal": signal,
            "strength": signal_strength,
            "confidence": abs(confidence),
            "premium": passing_conditions >= 5,
            "passing_conditions": passing_conditions,
            "total_conditions": total_conditions,
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "strong_bullish": strong_bullish,
            "reasons": signal_reasons,
            "expected_win_rate": expected_win_rate,
            "kelly_fraction": kelly_fraction,
            "rsi": rsi,
            "macd": macd,
            "bb": bb,
            "atr": atr,
            "atr_pct": atr_pct,
            "vwap": vwap,
            "sr": sr,
            "stochastic": stochastic,
            "current_price": current_price,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "volatility": volatility,
            "momentum_5": momentum_5,
            "crisis_bonus": crisis_bonus,
        }

# ========================================================================
# 🤖 SCALPER BOT WITH WST/FSI INTEGRATION
# ========================================================================

class ScalperBotV100:

    def __init__(self, api_key: str, api_secret: str, symbol: str = "BTCUSDT",
                 exchange_region: str = "us", log_level: str = "INFO"):
        """
        COMPLETE EDITION - With WST/FSI brain
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.test_mode = False
        
        # WST/FSI Engine
        self.crisis_engine = CrisisScoringEngine()
        self.selected_country = "SOM"  # Default: Somalia (highest FSI)
        self.crisis_score = 0.74
        self.wst_class = "Periphery"

        # Setup logging
        log_filename = f"crisis_scalper_{datetime.now().strftime('%Y%m%d')}.log"
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

        # 💰 OPTIMIZED PARAMETERS
        self.total_balance_usdt = 50.0
        
        # MINIMUM ORDER SIZE
        self.min_order_usdt = 10.0
        self.max_order_usdt = 25.0
        
        # RISK:REWARD = 1:3
        self.stop_loss_pct = 0.005
        self.target_profit_pct = 0.015
        
        # Position sizing
        self.base_risk_per_trade = 0.02
        self.max_risk_per_trade = 0.05
        self.min_risk_per_trade = 0.01
        
        # 5 CONDITIONS with WST bonus
        self.min_passing_conditions = 5
        self.min_confidence = 0.20
        self.min_signal_strength = "moderate"
        self.min_strong_signals = 0
        
        # Safety limits
        self.max_drawdown_pct = 0.08
        self.max_consecutive_losses = 4
        self.max_skips_before_pause = 50
        self.target_consecutive_wins = 7
        
        # Trade management
        self.chase_timeout_sec = 60
        self.stop_loss_poll_sec = 2
        self.maker_fee_rate = 0.001
        
        # Price cache
        self._price_cache = {}
        self._price_cache_time = 0
        self._price_cache_ttl = 1

        # Exchange info cache
        self._min_qty = 0.00001
        self._tick_size = 0.01
        self._min_notional = 10.0

        # Internal state
        self.active_order_id = None
        self.buy_price = None
        self.buy_qty = None
        self.last_known_qty = 0.0
        
        # Track running P&L
        self.running_pnl = 0.0
        self.current_balance = 0.0
        self.peak_balance = 0.0
        self.starting_balance = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.balance_fetched = False
        self.stopped = False
        self.initialized = False
        self.skipped_count = 0
        
        # Advanced performance metrics
        self.trade_history = []
        self.returns = []
        self.win_count = 0
        self.loss_count = 0
        self.total_trades = 0
        self.skipped_trades = 0
        self.total_fees = 0.0
        
        # Statistics tracking
        self.cycle_stats = {
            "total_cycles": 0,
            "successful_cycles": 0,
            "failed_cycles": 0,
            "skipped_cycles": 0,
            "total_profit": 0.0,
            "total_loss": 0.0,
            "net_profit": 0.0,
            "start_time": None,
            "end_time": None,
            "cycle_results": []
        }

        self.logger.info("="*70)
        self.logger.info("🚀 CRISIS ARBITRAGE SCALPER v10.0 - COMPLETE EDITION")
        self.logger.info("="*70)
        self.logger.info(f"   Symbol: {symbol}")
        self.logger.info(f"   Mode: 💰 LIVE TRADING")
        
        # Show WST/FSI brain
        top_opportunities = self.crisis_engine.get_top_opportunities(1)
        if top_opportunities:
            opp = top_opportunities[0]
            self.selected_country = opp["iso"]
            self.crisis_score = opp["opportunity_score"]
            self.wst_class = opp["wst_class"]
            self.logger.info(f"   🌍 Crisis Opportunity: {opp['flag']} {opp['name']}")
            self.logger.info(f"   📊 FSI Score: {opp['fsi_score']:.1f}")
            self.logger.info(f"   🏛️ WST Class: {opp['wst_class']}")
            self.logger.info(f"   🎯 Opportunity Score: {opp['opportunity_score']:.2f}")
        
        self.logger.info(f"   Min Order: ${self.min_order_usdt:.2f}")
        self.logger.info(f"   Target Profit: {self.target_profit_pct*100:.1f}%")
        self.logger.info(f"   Stop Loss: {self.stop_loss_pct*100:.1f}%")
        self.logger.info(f"   Risk:Reward: 1:{self.target_profit_pct/self.stop_loss_pct:.1f}")
        self.logger.info(f"   Passing Conditions: {self.min_passing_conditions}/10")
        self.logger.info(f"   Max Drawdown: {self.max_drawdown_pct*100:.0f}%")
        self.logger.info("="*70)

        # Auto-initialize
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
                self.total_balance_usdt = self.current_balance
                self.balance_fetched = True
                self.initialized = True
                self.logger.info(f"💰 Starting Balance: ${self.current_balance:.2f}")
                return True
            else:
                self.logger.warning("⚠️ Could not fetch valid balance")
                self.balance_fetched = False
                return False
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            self.balance_fetched = False
            return False

    def _update_balance(self):
        try:
            balances = self.get_account_balance()
            if "USDT" in balances and balances["USDT"] > 0:
                self.current_balance = balances["USDT"]
                self.total_balance_usdt = self.current_balance
                self.balance_fetched = True
                if self.peak_balance == 0 or self.current_balance > self.peak_balance:
                    self.peak_balance = self.current_balance
                self.logger.info(f"💰 Current Balance: ${self.current_balance:.2f}")
            else:
                self.logger.warning("⚠️ Could not fetch valid balance")
                self.balance_fetched = False
        except Exception as e:
            self.logger.error(f"Error fetching balance: {e}")
            self.balance_fetched = False

    def _check_connectivity(self):
        self.logger.info("🔍 Running startup connectivity check...")
        ticker = self.get_order_book_ticker()
        if not ticker:
            self.logger.error("❌ STARTUP CHECK FAILED")
            raise SystemExit("Aborting: fix connectivity before running live cycles.")
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
                        self.logger.info(f"   Min Qty: {self._min_qty}")
                        self.logger.info(f"   Min Notional: ${self._min_notional:.2f}")
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
        
        if "quantity" in params:
            try:
                qty_val = float(params["quantity"])
                if qty_val <= 0:
                    self.logger.error(f"❌ Invalid quantity: {params['quantity']}")
                    return {"error": "Invalid quantity", "code": -1003}
                params["quantity"] = format_quantity(qty_val)
            except (ValueError, TypeError):
                self.logger.error(f"❌ Invalid quantity format: {params['quantity']}")
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
                    self.logger.error(f"Failed to decode JSON (status {response.status_code})")
                    if attempt < retries - 1:
                        time.sleep(2 ** attempt)
                        continue
                    return {"error": "Invalid JSON response", "status_code": response.status_code}

                if isinstance(data, dict) and "code" in data and "msg" in data:
                    error_code = data.get("code")
                    if error_code in [-1003, -1001, -1016]:
                        wait_time = 2 ** attempt
                        self.logger.warning(f"Rate limit hit, waiting {wait_time}s...")
                        time.sleep(wait_time)
                        continue
                    if error_code == -2010:
                        self.logger.error(f"Insufficient balance: {data.get('msg')}")
                        self._update_balance()
                        return {"error": data.get("msg"), "code": error_code, "insufficient": True}
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
        
        if amount <= 0:
            self.logger.error(f"❌ Invalid amount: {amount}")
            return {"error": "Invalid amount", "code": -1003}
        
        if amount < self.min_order_usdt:
            self.logger.info(f"⚠️ Amount ${amount:.2f} below minimum, adjusting to ${self.min_order_usdt:.2f}")
            amount = self.min_order_usdt
        
        if amount > self.max_order_usdt and self.current_balance > 50:
            amount = self.max_order_usdt
        
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
        
        self.last_known_qty = qty
        
        qty_str = format_quantity(qty)
        
        self.logger.info(f"Placing {side} MARKET order: {qty_str} (${qty * price:.2f})")

        params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": qty_str,
        }
        
        response = self._send_signed_request("POST", "/api/v3/order", params)
        
        if "error" in response:
            if response.get("insufficient"):
                reduced_qty = qty * 0.9
                reduced_qty = round_to_step(reduced_qty, self._min_qty)
                if reduced_qty >= self._min_qty:
                    self.logger.info(f"⚠️ Retrying with reduced quantity: {format_quantity(reduced_qty)}")
                    params["quantity"] = format_quantity(reduced_qty)
                    response = self._send_signed_request("POST", "/api/v3/order", params)
                    if "error" not in response:
                        self.last_known_qty = reduced_qty
                        qty = reduced_qty
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
        if quantity <= 0:
            self.logger.error(f"❌ Invalid quantity: {quantity}")
            return {"error": "Invalid quantity", "code": -1003}
        
        if quantity * price < self._min_notional:
            quantity = self._min_notional / price
            quantity = round_to_step(quantity, self._min_qty)

        qty = round_to_step(quantity, self._min_qty)
        if qty < self._min_qty:
            qty = self._min_qty

        self.last_known_qty = qty

        limit_price = round_to_tick(price, self._tick_size)
        qty_str = format_quantity(qty)
        price_str = format_price(limit_price)

        self.logger.info(f"Placing {side} LIMIT order: {qty_str} @ ${price_str} (${qty * limit_price:.2f})")

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
            "orderId": response.get("orderId", f"ERR_{int(time.time())}"),
            "price": str(response.get("price", limit_price)),
            "origQty": str(response.get("origQty", qty)),
            "executedQty": str(response.get("executedQty", "0")),
            "status": response.get("status", "NEW"),
            "side": side,
        }

    def cancel_order(self, order_id: str) -> dict:
        if not order_id or order_id == "0" or "ERR_" in str(order_id):
            self.logger.info(f"⚠️ Skipping cancel for invalid order ID: {order_id}")
            return {"status": "CANCELED", "orderId": order_id}
        
        params = {"symbol": self.symbol, "orderId": order_id}
        response = self._send_signed_request("DELETE", "/api/v3/order", params)
        
        if response.get("code") == -2011:
            self.logger.info(f"⚠️ Order {order_id} already canceled or doesn't exist")
            return {"status": "CANCELED", "orderId": order_id}
        
        return response

    def get_order_status(self, order_id: str) -> dict:
        if not order_id or order_id == "0" or "ERR_" in str(order_id):
            return {"status": "FILLED", "orderId": order_id}
        
        params = {"symbol": self.symbol, "orderId": order_id}
        return self._send_signed_request("GET", "/api/v3/order", params)

    def calculate_position_size(self, analysis: Dict) -> float:
        kelly_fraction = analysis.get('kelly_fraction', 0.02)
        risk_pct = max(self.min_risk_per_trade, min(self.max_risk_per_trade, kelly_fraction))
        
        loss_penalty = max(0.5, 1.0 - (self.consecutive_losses * 0.15))
        risk_pct = risk_pct * loss_penalty
        
        win_bonus = min(1.3, 1.0 + (self.consecutive_wins * 0.05))
        risk_pct = min(self.max_risk_per_trade, risk_pct * win_bonus)
        
        position_size = self.current_balance * risk_pct
        position_size = max(self.min_order_usdt, position_size)
        position_size = min(self.max_order_usdt, position_size)
        
        self.logger.info(f"📊 Position Size: ${position_size:.2f} ({risk_pct*100:.2f}% of balance)")
        return position_size

    def run_cycle(self, cycle_number: int = 0) -> dict:
        if self.stopped:
            return {"success": False, "error": "Bot stopped"}
            
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔄 CYCLE {cycle_number}")
        self.logger.info(f"{'='*60}")

        # Show current WST/FSI opportunity
        top_opportunities = self.crisis_engine.get_top_opportunities(1)
        if top_opportunities:
            opp = top_opportunities[0]
            self.logger.info(f"🌍 Crisis Opportunity: {opp['flag']} {opp['name']}")
            self.logger.info(f"   FSI: {opp['fsi_score']:.1f} | WST: {opp['wst_class']}")
            self.logger.info(f"   Opportunity Score: {opp['opportunity_score']:.2f}")

        self._update_balance()
        
        if not self.balance_fetched or self.current_balance <= 0:
            self.logger.error("❌ Invalid balance")
            self.stopped = True
            return {"success": False, "error": "Invalid balance"}
        
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
            if drawdown > self.max_drawdown_pct:
                self.logger.error(f"❌ Max drawdown exceeded: {drawdown*100:.1f}%")
                self.stopped = True
                return {"success": False, "error": "Max drawdown exceeded"}
        
        if self.consecutive_losses >= self.max_consecutive_losses:
            self.logger.error(f"❌ Too many consecutive losses: {self.consecutive_losses}")
            self.stopped = True
            return {"success": False, "error": "Too many consecutive losses"}
        
        if self.current_balance < self.min_order_usdt:
            self.logger.error(f"❌ Balance too low: ${self.current_balance:.2f}")
            self.stopped = True
            return {"success": False, "error": "Balance too low"}

        # Get market data
        klines = AdvancedTA.get_klines(self.symbol, self.base_url, interval="1m", limit=300)
        if not klines:
            self.logger.warning("⚠️ Could not fetch market data - skipping")
            self.skipped_trades += 1
            self.skipped_count += 1
            return {"success": False, "error": "No market data", "skipped": True}
        
        # Analyze with 5 conditions strategy + WST/FSI crisis scoring
        crisis_score = self.crisis_score
        wst_class = self.wst_class
        analysis = EinsteinStrategy.analyze_market(klines, crisis_score, wst_class)
        
        self.logger.info(f"📊 MARKET ANALYSIS:")
        self.logger.info(f"   Signal: {analysis['signal']} ({analysis['strength']})")
        self.logger.info(f"   Passing Conditions: {analysis['passing_conditions']}/{analysis['total_conditions']}")
        self.logger.info(f"   Confidence: {analysis['confidence']:.2f}")
        self.logger.info(f"   Bullish/Bearish: {analysis['bullish_signals']}/{analysis['bearish_signals']}")
        self.logger.info(f"   Crisis Bonus: +{analysis['crisis_bonus']}")
        self.logger.info(f"   RSI: {analysis['rsi']:.1f}")
        self.logger.info(f"   BB Position: {analysis['bb']['position']:.2f}")
        
        for reason in analysis['reasons'][:6]:
            self.logger.info(f"   → {reason}")
        
        # Check conditions
        passing = analysis['passing_conditions']
        needed = self.min_passing_conditions
        
        if passing >= needed:
            self.logger.info(f"✅ {passing}/{analysis['total_conditions']} conditions PASSING - TRADING!")
            self.skipped_count = 0
        else:
            self.logger.info(f"⏭️ Only {passing}/{analysis['total_conditions']} passing (need {needed}) - SKIPPING")
            self.skipped_trades += 1
            self.skipped_count += 1
            
            if self.skipped_count >= self.max_skips_before_pause:
                self.logger.warning(f"⚠️ {self.skipped_count} consecutive skips - taking a break...")
                time.sleep(60)
                self.skipped_count = 0
            
            return {"success": False, "error": "Not enough conditions passing", "skipped": True}

        # Get current price
        current_price = self.get_current_price()
        if not current_price:
            return {"success": False, "error": "No price data"}

        # Calculate position size
        position_size = self.calculate_position_size(analysis)
        buy_amount = min(position_size, self.current_balance * 0.40)
        
        self.logger.info(f"📈 Placing BUY MARKET order for ~${buy_amount:.2f}")
        
        buy_order = self.place_market_order(
            side="BUY",
            amount=buy_amount,
            is_quantity=False,
        )

        if "error" in buy_order:
            self.logger.error(f"Failed to place buy order: {buy_order}")
            return {"success": False, "error": buy_order.get("error", "Buy order failed")}

        order_id = buy_order.get("orderId")
        if not order_id:
            return {"success": False, "error": "Missing orderId"}

        self.buy_price = float(buy_order.get("price", 0))
        self.buy_qty = float(buy_order.get("executedQty", buy_order.get("origQty", 0)))
        
        if self.buy_qty <= 0:
            self.logger.error(f"❌ Invalid quantity from buy order: {self.buy_qty}")
            return {"success": False, "error": "Invalid quantity"}
        
        if self.buy_price == 0 and order_id:
            fill_price = self.get_order_fill_price(order_id)
            if fill_price:
                self.buy_price = fill_price
            else:
                self.buy_price = self.get_current_price() or 64000.0
        
        self.last_known_qty = self.buy_qty

        self.logger.info(f"✅ BUY Filled: {self.buy_qty:.8f} BTC @ ${self.buy_price:.2f} (${self.buy_qty * self.buy_price:.2f})")

        # Calculate Exit Levels
        atr_stop = EinsteinMath.optimal_stop_loss(
            analysis['atr'], 
            analysis['volatility'], 
            analysis['confidence']
        )
        
        stop_price = self.buy_price - atr_stop
        target_price = self.buy_price * (1 + self.target_profit_pct)
        
        min_stop = self.buy_price * (1 - self.stop_loss_pct)
        max_stop = self.buy_price * (1 - 0.015)
        stop_price = max(min_stop, min(max_stop, stop_price))
        
        if analysis['sr']['near_resistance']:
            resistance = analysis['sr']['resistance']
            if resistance < target_price:
                target_price = min(target_price, resistance * 0.998)
                self.logger.info(f"📊 Adjusted target due to resistance: ${target_price:.2f}")
        
        actual_risk = self.buy_price - stop_price
        actual_reward = target_price - self.buy_price
        rr_ratio = actual_reward / actual_risk if actual_risk > 0 else 0
        
        self.logger.info(f"🎯 Target: ${target_price:.2f} (+{((target_price/self.buy_price)-1)*100:.2f}%)")
        self.logger.info(f"🛑 Stop: ${stop_price:.2f} (-{((1 - stop_price/self.buy_price))*100:.2f}%)")
        self.logger.info(f"📊 Risk:Reward: 1:{rr_ratio:.2f}")

        # Place SELL LIMIT order
        sell_qty = self.buy_qty
        self.logger.info(f"📉 Placing SELL LIMIT order @ ${target_price:.2f} for {sell_qty:.8f} BTC")
        
        sell_order = self.place_limit_order(
            side="SELL",
            quantity=sell_qty,
            price=target_price,
        )

        if "error" in sell_order:
            self.logger.error(f"Failed to place sell order: {sell_order}")
            self.logger.info("Attempting market sell as fallback...")
            fallback_sell = self.place_market_order("SELL", sell_qty, is_quantity=True)
            if "error" in fallback_sell:
                return {"success": False, "error": "Sell order failed"}
            exit_price = float(fallback_sell.get("price", self.buy_price))
            if exit_price == 0:
                exit_price = self.buy_price
            sell_filled = True
            stopped_out = False
        else:
            sell_order_id = sell_order.get("orderId")
            if not sell_order_id:
                return {"success": False, "error": "Missing sell orderId"}

            sell_filled = False
            sell_start = time.time()
            exit_price = target_price
            stopped_out = False

            while not sell_filled:
                now = time.time()
                
                status = self.get_order_status(sell_order_id)
                if status.get("status") == "FILLED":
                    sell_filled = True
                    cum_quote = float(status.get("cummulativeQuoteQty", 0))
                    executed_qty = float(status.get("executedQty", 0))
                    if executed_qty > 0 and cum_quote > 0:
                        exit_price = cum_quote / executed_qty
                    else:
                        exit_price = float(status.get("price", target_price))
                    self.logger.info(f"✅ SELL Filled @ ${exit_price:.2f}")
                    break
                
                if now - sell_start > 2:
                    current_price = self.get_current_price()
                    if current_price and current_price <= stop_price:
                        self.logger.warning(f"🛑 STOP-LOSS breached: ${current_price:.2f}")
                        self.cancel_order(sell_order_id)
                        exit_res = self.place_market_order("SELL", self.buy_qty, is_quantity=True)
                        if "error" in exit_res:
                            self.logger.error(f"Stop-loss exit failed: {exit_res}")
                            time.sleep(1)
                            continue
                        sell_filled = True
                        stopped_out = True
                        exit_price = float(exit_res.get("price", current_price))
                        if exit_price == 0:
                            exit_price = current_price
                        self.logger.info(f"🛑 Stopped out @ ${exit_price:.2f}")
                        break
                
                if now - sell_start > self.chase_timeout_sec:
                    self.logger.info("Sell order taking too long, converting to market...")
                    self.cancel_order(sell_order_id)
                    exit_res = self.place_market_order("SELL", self.buy_qty, is_quantity=True)
                    if "error" in exit_res:
                        self.logger.error(f"Chase sell failed: {exit_res}")
                        time.sleep(1)
                        continue
                    sell_filled = True
                    exit_price = float(exit_res.get("price", self.buy_price))
                    if exit_price == 0:
                        exit_price = self.buy_price
                    self.logger.info(f"✅ SELL Filled @ ${exit_price:.2f} (chased)")
                    break
                
                time.sleep(1)

        # Calculate P&L
        realized_pnl = (exit_price - self.buy_price) * self.buy_qty
        fee_estimate = (self.buy_qty * self.buy_price * 0.001) + (self.buy_qty * exit_price * 0.001)
        net_pnl = realized_pnl - fee_estimate
        self.total_fees += fee_estimate
        
        self.logger.info(f"💰 P&L: ${realized_pnl:.4f} (net: ${net_pnl:.4f})" + (" (stop-loss exit)" if stopped_out else ""))
        self.logger.info(f"📊 Fees: ${fee_estimate:.4f}")
        
        # Update metrics
        self.running_pnl += net_pnl
        self.current_balance = max(0, self.total_balance_usdt + self.running_pnl)
        self.total_trades += 1
        
        if net_pnl > 0:
            self.win_count += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            if self.current_balance > self.peak_balance:
                self.peak_balance = self.current_balance
        else:
            self.loss_count += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        self.logger.info(f"📊 Win Rate: {win_rate:.1f}% ({self.win_count}W/{self.loss_count}L)")
        self.logger.info(f"📊 Consecutive Wins: {self.consecutive_wins} | Losses: {self.consecutive_losses}")
        self.logger.info(f"💰 Current Balance: ${self.current_balance:.2f}")

        result = {
            "success": True,
            "cycle": cycle_number,
            "entry_price": self.buy_price,
            "exit_price": exit_price,
            "quantity": self.buy_qty,
            "profit": realized_pnl,
            "net_profit": net_pnl,
            "fees": fee_estimate,
            "profit_percent": (realized_pnl / (self.buy_price * self.buy_qty)) * 100 if self.buy_price * self.buy_qty > 0 else 0,
            "stopped_out": stopped_out,
            "balance_after": self.current_balance,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "win_rate": win_rate,
            "passing_conditions": analysis['passing_conditions'],
            "crisis_bonus": analysis['crisis_bonus'],
            "timestamp": datetime.now().isoformat()
        }

        self.cycle_stats["total_cycles"] += 1
        if net_pnl > 0:
            self.cycle_stats["successful_cycles"] += 1
            self.cycle_stats["total_profit"] += net_pnl
        else:
            self.cycle_stats["failed_cycles"] += 1
            self.cycle_stats["total_loss"] += abs(net_pnl)

        self.cycle_stats["net_profit"] += net_pnl
        self.cycle_stats["cycle_results"].append(result)
        self.trade_history.append(result)

        return result

    def run_forever(self, delay_between_cycles: int = 8):
        """Run continuously"""
        self.logger.info("\n" + "="*70)
        self.logger.info("🚀 CRISIS ARBITRAGE SCALPER v10.0 - COMPLETE EDITION")
        self.logger.info("   With WST/FSI Crisis Scoring Brain")
        self.logger.info("   Press Ctrl+C to stop")
        self.logger.info("="*70)

        self.cycle_stats["start_time"] = datetime.now()
        
        cycle_num = 1
        while not self.stopped:
            try:
                self.logger.info(f"\n📊 Cycle {cycle_num}")
                self.logger.info(f"   Streak: {self.consecutive_wins} wins | {self.consecutive_losses} losses")
                self.logger.info(f"   Skips: {self.skipped_count} in a row")
                self.logger.info(f"   Balance: ${self.current_balance:.2f}")
                
                result = self.run_cycle(cycle_number=cycle_num)

                if result.get("skipped", False):
                    self.logger.info(f"⏭️ Waiting for conditions... ({self.skipped_count} skips)")
                elif not result.get("success", False):
                    self.logger.error(f"⚠️ Cycle failed: {result.get('error', 'Unknown error')}")
                else:
                    self.logger.info(f"✅ TRADE COMPLETED! Profit: ${result.get('net_profit', 0):.4f}")

                self.print_current_stats()
                self.export_results_to_csv()

                if self.consecutive_wins >= self.target_consecutive_wins:
                    self.logger.info("\n" + "="*70)
                    self.logger.info("🎉🎉🎉 TARGET ACHIEVED! 7 CONSECUTIVE WINS! 🎉🎉🎉")
                    self.logger.info("="*70)
                    self.stopped = True
                    break

                wait_time = delay_between_cycles + random.uniform(0, 2)
                self.logger.info(f"\n⏳ Waiting {wait_time:.1f} seconds...")
                time.sleep(wait_time)
                cycle_num += 1

            except KeyboardInterrupt:
                self.logger.info("\n⚠️ Stopped by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Error: {e}")
                time.sleep(delay_between_cycles * 2)
                cycle_num += 1

        self.cycle_stats["end_time"] = datetime.now()
        self.print_final_summary()
        self.export_final_report()

    def print_current_stats(self):
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        self.logger.info(f"\n📊 CURRENT STATISTICS:")
        self.logger.info(f"   Total Cycles: {self.cycle_stats['total_cycles']}")
        self.logger.info(f"   Skipped: {self.cycle_stats.get('skipped_cycles', 0)}")
        self.logger.info(f"   Wins: {self.win_count} | Losses: {self.loss_count}")
        self.logger.info(f"   Win Rate: {win_rate:.1f}%")
        self.logger.info(f"   Consecutive Wins: {self.consecutive_wins} | Losses: {self.consecutive_losses}")
        self.logger.info(f"   Net Profit: ${self.cycle_stats['net_profit']:.4f}")
        self.logger.info(f"   Current Balance: ${self.current_balance:.2f}")

    def print_final_summary(self):
        stats = self.cycle_stats
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        duration = (stats['end_time'] - stats['start_time']).total_seconds()
        hours = duration // 3600
        minutes = (duration % 3600) // 60
        seconds = duration % 60

        self.logger.info("\n" + "="*70)
        self.logger.info("🚀 FINAL SUMMARY - v10.0 COMPLETE EDITION")
        self.logger.info("="*70)
        self.logger.info(f"📅 Start Time: {stats['start_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"📅 End Time:   {stats['end_time'].strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"⏱️  Duration:   {int(hours)}h {int(minutes)}m {int(seconds)}s")
        self.logger.info("-"*70)
        self.logger.info(f"📊 Total Cycles:       {stats['total_cycles']}")
        self.logger.info(f"✅ Successful Cycles:  {stats['successful_cycles']}")
        self.logger.info(f"❌ Failed Cycles:      {stats['failed_cycles']}")
        self.logger.info(f"⏭️ Skipped Cycles:     {stats.get('skipped_cycles', 0)}")
        self.logger.info(f"🏆 Win Rate:           {win_rate:.1f}%")
        self.logger.info(f"📊 Consecutive Wins:   {self.consecutive_wins}")
        self.logger.info("-"*70)
        self.logger.info(f"💰 Starting Balance:   ${self.starting_balance:.2f}")
        self.logger.info(f"💰 Final Balance:      ${self.current_balance:.2f}")
        self.logger.info(f"💰 Peak Balance:       ${self.peak_balance:.2f}")
        self.logger.info(f"📈 Total Profit:       ${stats['net_profit']:.4f}")
        self.logger.info(f"📊 Total Fees:         ${self.total_fees:.4f}")
        
        if stats['total_cycles'] > 0:
            avg_profit = stats['net_profit'] / max(1, stats['total_cycles'])
            self.logger.info(f"📊 Avg Profit/Cycle:   ${avg_profit:.4f}")
        
        if self.starting_balance > 0:
            roi = (stats['net_profit'] / self.starting_balance) * 100
            self.logger.info(f"📊 ROI:                {roi:.1f}%")
        
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance * 100
            self.logger.info(f"📊 Max Drawdown:       {drawdown:.1f}%")
        
        self.logger.info("-"*70)
        self.logger.info(f"📊 Total Trades:        {self.total_trades}")
        self.logger.info("="*70)

    def export_results_to_csv(self):
        if not self.cycle_stats["cycle_results"]:
            return

        filename = f"crisis_scalper_results_{datetime.now().strftime('%Y%m%d')}.csv"
        file_exists = os.path.isfile(filename)

        with open(filename, 'a', newline='') as csvfile:
            fieldnames = ['cycle', 'timestamp', 'entry_price', 'exit_price', 'quantity',
                         'profit', 'net_profit', 'fees', 'profit_percent', 'stopped_out', 
                         'balance_after', 'consecutive_wins', 'consecutive_losses', 'win_rate',
                         'passing_conditions', 'crisis_bonus', 'success']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            latest = self.cycle_stats["cycle_results"][-1]
            writer.writerow({
                'cycle': latest['cycle'],
                'timestamp': latest['timestamp'],
                'entry_price': f"{latest['entry_price']:.2f}",
                'exit_price': f"{latest['exit_price']:.2f}",
                'quantity': f"{latest['quantity']:.8f}",
                'profit': f"{latest['profit']:.4f}",
                'net_profit': f"{latest.get('net_profit', 0):.4f}",
                'fees': f"{latest.get('fees', 0):.4f}",
                'profit_percent': f"{latest['profit_percent']:.2f}",
                'stopped_out': latest.get('stopped_out', False),
                'balance_after': f"{latest.get('balance_after', 0):.2f}",
                'consecutive_wins': latest.get('consecutive_wins', 0),
                'consecutive_losses': latest.get('consecutive_losses', 0),
                'win_rate': f"{latest.get('win_rate', 0):.1f}",
                'passing_conditions': latest.get('passing_conditions', 0),
                'crisis_bonus': latest.get('crisis_bonus', 0),
                'success': latest['success']
            })

    def export_final_report(self):
        roi_percent = 0.0
        if self.starting_balance > 0:
            roi_percent = ((self.current_balance - self.starting_balance) / self.starting_balance) * 100
        
        max_drawdown_percent = 0.0
        if self.peak_balance > 0:
            max_drawdown_percent = ((self.peak_balance - self.current_balance) / self.peak_balance * 100)
        
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        
        report = {
            "version": "10.0",
            "name": "Complete Edition with WST/FSI Brain",
            "wst_fsi_integration": {
                "selected_country": self.selected_country,
                "crisis_score": self.crisis_score,
                "wst_class": self.wst_class,
                "top_opportunities": self.crisis_engine.get_top_opportunities(5)
            },
            "starting_balance": self.starting_balance,
            "final_balance": self.current_balance,
            "peak_balance": self.peak_balance,
            "max_drawdown_percent": max_drawdown_percent,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "roi_percent": roi_percent,
            "win_rate": win_rate,
            "total_trades": self.total_trades,
            "wins": self.win_count,
            "losses": self.loss_count,
            "skipped_trades": self.skipped_trades,
            "total_fees": self.total_fees,
            "target_achieved": self.consecutive_wins >= self.target_consecutive_wins,
            "bot_stopped": self.stopped,
            "settings": {
                "min_order_usdt": self.min_order_usdt,
                "target_profit_pct": self.target_profit_pct,
                "stop_loss_pct": self.stop_loss_pct,
                "risk_reward": self.target_profit_pct / self.stop_loss_pct,
                "min_passing_conditions": self.min_passing_conditions,
            },
            "summary": self.cycle_stats,
            "trade_history": self.trade_history[-20:]  # Last 20 trades
        }

        filename = f"crisis_scalper_report_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w') as f:
            json.dump(report, f, indent=2, default=str)

        self.logger.info(f"\n📄 Detailed report exported to: {filename}")

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
        print("\nCreate a .env file with:")
        print("BINANCE_API_KEY=your_api_key")
        print("BINANCE_API_SECRET=your_api_secret")
        print("="*70)
        sys.exit(1)
    
    print("="*70)
    print("🚀 CRISIS ARBITRAGE SCALPER v10.0 - COMPLETE EDITION")
    print("="*70)
    print("\nINTEGRATED SYSTEMS:")
    print("1. ✅ WST (World Systems Theory) Structural Scoring")
    print("2. ✅ FSI 2024 (Fragile States Index) Country Risk")
    print("3. ✅ 5 Conditions Trading Strategy")
    print("4. ✅ Einstein-Level Mathematical Analysis")
    print("5. ✅ Advanced Technical Indicators")
    print("="*70)
    
    print("\n🤖 Starting COMPLETE EDITION in 3 seconds...")
    time.sleep(3)
    
    bot = ScalperBotV100(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol="BTCUSDT",
        exchange_region="us",
        log_level="INFO"
    )

    bot.run_forever(delay_between_cycles=8)
