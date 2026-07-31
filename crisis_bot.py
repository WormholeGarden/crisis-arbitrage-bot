#!/usr/bin/env python3
"""
🚀 GOLDEN SCALPER BOT v11.3 - FINAL CONFIDENCE FIX
============================================================
FIXES:
- Dead market confidence threshold: 15% (was 25%)
- Weak trend confidence: 20% (was 30%)
- Strong trend confidence: 30% (was 35%)
- This will trigger trades with just RSI + Bollinger
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

GOLDEN_CONFIG = {
    "symbol": "AVAXUSDT",
    "interval": "4h",
    "min_signals_strong": 6,
    "min_signals_weak": 3,
    "min_signals_dead": 2,
    "min_confidence_dead": 0.12,    # 12% confidence for dead markets (REDUCED!)
    "min_confidence_weak": 0.20,    # 20% for weak trends
    "min_confidence_strong": 0.30,  # 30% for strong trends
    "trailing_pct": 0.3,
    "max_hold_hours": 48,
    "trailing_stop": False,
    "target_profit_pct": 0.025,
    "stop_loss_pct": 0.015,
    "min_order_usdt": 10.0,
    "max_order_usdt": 50.0,
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
# ADVANCED INDICATORS
# ========================================================================

class AdvancedIndicators:
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
        ema_val = sum(data[:period]) / period
        for price in data[period:]:
            ema_val = price * alpha + ema_val * (1 - alpha)
        return ema_val

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
    def macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        if len(closes) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0, "bullish": False, "bearish": False}
        ema_fast = AdvancedIndicators.ema(closes, fast)
        ema_slow = AdvancedIndicators.ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = AdvancedIndicators.ema([macd_line] * signal, signal)
        histogram = macd_line - signal_line
        return {
            "macd": macd_line,
            "signal": signal_line,
            "histogram": histogram,
            "bullish": macd_line > signal_line,
            "bearish": macd_line < signal_line
        }

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
        tr_ema = AdvancedIndicators.ema(tr[-period:], period)
        if tr_ema == 0:
            return 25.0
        plus_di = 100 * (AdvancedIndicators.ema(plus_dm[-period:], period) / tr_ema)
        minus_di = 100 * (AdvancedIndicators.ema(minus_dm[-period:], period) / tr_ema)
        dx = 100 * abs(plus_di - minus_di) / (plus_di + minus_di) if (plus_di + minus_di) > 0 else 0
        return AdvancedIndicators.ema([dx] * period, period)

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
    def stochastic(closes: List[float], highs: List[float], lows: List[float], period: int = 14) -> float:
        if len(closes) < period:
            return 50.0
        highest = max(highs[-period:])
        lowest = min(lows[-period:])
        if highest == lowest:
            return 50.0
        return ((closes[-1] - lowest) / (highest - lowest)) * 100

    @staticmethod
    def zscore(data: List[float], period: int = 20) -> float:
        if len(data) < period:
            return 0
        window = data[-period:]
        mean = sum(window) / period
        std = statistics.stdev(window) if period > 1 else 0.001
        return (data[-1] - mean) / std if std > 0 else 0

    @staticmethod
    def keltner(highs: List[float], lows: List[float], closes: List[float], period: int = 20) -> Dict:
        if len(closes) < period:
            return {"upper": closes[-1], "middle": closes[-1], "lower": closes[-1]}
        middle = AdvancedIndicators.ema(closes, period)
        atr_val = AdvancedIndicators.atr(highs, lows, closes, 10)
        return {"upper": middle + atr_val * 1.5, "middle": middle, "lower": middle - atr_val * 1.5}

    @staticmethod
    def ichimoku(highs: List[float], lows: List[float], closes: List[float]) -> Dict:
        if len(closes) < 52:
            return {"tenkan": closes[-1], "kijun": closes[-1], "senkou_a": closes[-1], "senkou_b": closes[-1]}
        tenkan = (max(highs[-9:]) + min(lows[-9:])) / 2
        kijun = (max(highs[-26:]) + min(lows[-26:])) / 2
        senkou_a = (tenkan + kijun) / 2
        senkou_b = (max(highs[-52:]) + min(lows[-52:])) / 2
        return {"tenkan": tenkan, "kijun": kijun, "senkou_a": senkou_a, "senkou_b": senkou_b}

    @staticmethod
    def vortex(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Dict:
        if len(closes) < period + 1:
            return {"vi_plus": 0, "vi_minus": 0}
        vm_plus, vm_minus, tr = [], [], []
        for i in range(1, len(closes)):
            vm_plus.append(abs(highs[i] - lows[i-1]))
            vm_minus.append(abs(lows[i] - highs[i-1]))
            tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
        sum_vm_plus = sum(vm_plus[-period:])
        sum_vm_minus = sum(vm_minus[-period:])
        sum_tr = sum(tr[-period:])
        return {"vi_plus": sum_vm_plus / sum_tr if sum_tr > 0 else 0, "vi_minus": sum_vm_minus / sum_tr if sum_tr > 0 else 0}

    @staticmethod
    def cci(closes: List[float], highs: List[float], lows: List[float], period: int = 20) -> float:
        if len(closes) < period:
            return 0
        tp = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        sma_tp = sum(tp[-period:]) / period
        mean_dev = sum([abs(x - sma_tp) for x in tp[-period:]]) / period
        return (tp[-1] - sma_tp) / (0.015 * mean_dev) if mean_dev > 0 else 0

    @staticmethod
    def dmi(highs: List[float], lows: List[float], closes: List[float], period: int = 14) -> Dict:
        adx = AdvancedIndicators.adx(highs, lows, closes, period)
        plus_dm, minus_dm = [], []
        for i in range(1, len(closes)):
            up = highs[i] - highs[i-1]
            down = lows[i-1] - lows[i]
            plus_dm.append(up if up > down and up > 0 else 0)
            minus_dm.append(down if down > up and down > 0 else 0)
        tr = []
        for i in range(1, len(closes)):
            tr.append(max(highs[i] - lows[i], abs(highs[i] - closes[i-1]), abs(lows[i] - closes[i-1])))
        tr_smooth = AdvancedIndicators.ema(tr[-period:], period)
        plus_di = 100 * (AdvancedIndicators.ema(plus_dm[-period:], period) / tr_smooth) if tr_smooth > 0 else 0
        minus_di = 100 * (AdvancedIndicators.ema(minus_dm[-period:], period) / tr_smooth) if tr_smooth > 0 else 0
        return {"adx": adx, "plus_di": plus_di, "minus_di": minus_di}

# ========================================================================
# FINAL CONFIDENCE-FIXED STRATEGY
# ========================================================================

class FinalConfidenceStrategy:
    @staticmethod
    def signal(data: Dict, params: Dict = None, verbose: bool = True) -> Dict:
        if params is None:
            params = {
                'min_signals_strong': 6,
                'min_signals_weak': 3,
                'min_signals_dead': 2,
                'min_confidence_dead': 0.12,
                'min_confidence_weak': 0.20,
                'min_confidence_strong': 0.30,
            }
        
        closes = data['closes']
        highs = data['highs']
        lows = data['lows']
        volumes = data['volumes']
        current = closes[-1]
        
        # Calculate market regime
        adx = AdvancedIndicators.adx(highs, lows, closes, 14)
        chop = AdvancedIndicators.chop(highs, lows, closes, 14)
        
        # Determine regime with more granularity
        if adx > 25 and chop < 40:
            regime = "TRENDING 📈"
            min_signals = params.get('min_signals_strong', 6)
            min_confidence = params.get('min_confidence_strong', 0.30)
            position_multiplier = 1.0
            target_multiplier = 1.0
            regime_type = "strong"
        elif adx > 15 and chop < 50:
            regime = "WEAK TREND 📊"
            min_signals = params.get('min_signals_weak', 3)
            min_confidence = params.get('min_confidence_weak', 0.20)
            position_multiplier = 0.85
            target_multiplier = 0.9
            regime_type = "weak"
        elif adx < 10 and chop > 45:
            regime = "DEAD/FLAT 💤 (using aggressive mode)"
            min_signals = params.get('min_signals_dead', 2)
            min_confidence = params.get('min_confidence_dead', 0.12)  # REDUCED!
            position_multiplier = 0.6
            target_multiplier = 0.7
            regime_type = "dead"
        else:
            regime = "NEUTRAL ⚖️"
            min_signals = params.get('min_signals_weak', 3)
            min_confidence = params.get('min_confidence_weak', 0.20)
            position_multiplier = 0.8
            target_multiplier = 0.85
            regime_type = "neutral"
        
        # Calculate all indicators
        signal_results = {}
        signals = []
        weights = []
        signal_names = []
        
        # 1. EMA Trend
        ema_9 = AdvancedIndicators.ema(closes, 9)
        ema_21 = AdvancedIndicators.ema(closes, 21)
        ema_50 = AdvancedIndicators.ema(closes, 50)
        
        ema_trend = 1 if current > ema_9 > ema_21 > ema_50 else 0.5 if current > ema_50 else 0
        signals.append(ema_trend)
        weights.append(1.5)
        signal_names.append("EMA_Trend")
        signal_results["EMA_Trend"] = {"value": ema_trend, "weight": 1.5, "status": "✅" if ema_trend > 0.5 else "❌"}
        
        # 2. MACD
        macd = AdvancedIndicators.macd(closes)
        macd_val = 1 if macd['bullish'] else 0
        signals.append(macd_val)
        weights.append(1.5)
        signal_names.append("MACD")
        signal_results["MACD"] = {"value": macd_val, "weight": 1.5, "status": "✅" if macd_val else "❌"}
        
        # 3. RSI
        rsi = AdvancedIndicators.rsi(closes, 14)
        if 30 < rsi < 70:
            rsi_val = 1 if rsi < 50 else 0.5
        elif rsi < 30:
            rsi_val = 1
        else:
            rsi_val = 0
        signals.append(rsi_val)
        weights.append(1.2)
        signal_names.append("RSI")
        signal_results["RSI"] = {"value": rsi_val, "weight": 1.2, "status": "✅" if rsi_val > 0.5 else "❌", "raw": f"{rsi:.1f}"}
        
        # 4. Bollinger
        bb = AdvancedIndicators.bollinger(closes)
        if current < bb['lower'] * 1.02:
            bb_val = 1
        elif current > bb['upper'] * 0.98:
            bb_val = 0
        else:
            bb_val = 0.5
        signals.append(bb_val)
        weights.append(1.0)
        signal_names.append("Bollinger")
        signal_results["Bollinger"] = {"value": bb_val, "weight": 1.0, "status": "✅" if bb_val > 0.5 else "❌"}
        
        # 5. ADX
        adx_val = 1 if adx > 20 else 0
        signals.append(adx_val)
        weights.append(1.3)
        signal_names.append("ADX")
        signal_results["ADX"] = {"value": adx_val, "weight": 1.3, "status": "✅" if adx_val else "❌", "raw": f"{adx:.1f}"}
        
        # 6. Stochastic
        stoch = AdvancedIndicators.stochastic(closes, highs, lows)
        stoch_val = 1 if stoch < 30 else 0.3 if stoch < 50 else 0
        signals.append(stoch_val)
        weights.append(0.8)
        signal_names.append("Stochastic")
        signal_results["Stochastic"] = {"value": stoch_val, "weight": 0.8, "status": "✅" if stoch_val > 0.5 else "❌", "raw": f"{stoch:.1f}"}
        
        # 7. OBV
        obv_values = AdvancedIndicators.obv(closes, volumes)
        if len(obv_values) >= 20:
            obv_ema = AdvancedIndicators.ema(obv_values, 10)
            obv_val = 1 if obv_values[-1] > obv_ema else 0
        else:
            obv_val = 0
        signals.append(obv_val)
        weights.append(1.0)
        signal_names.append("OBV")
        signal_results["OBV"] = {"value": obv_val, "weight": 1.0, "status": "✅" if obv_val else "❌"}
        
        # 8. VWAP
        vwap = AdvancedIndicators.vwap(highs, lows, closes, volumes)
        vwap_val = 1 if current > vwap else 0
        signals.append(vwap_val)
        weights.append(0.8)
        signal_names.append("VWAP")
        signal_results["VWAP"] = {"value": vwap_val, "weight": 0.8, "status": "✅" if vwap_val else "❌"}
        
        # 9. Choppiness
        chop_val = 1 if chop < 40 else 0
        signals.append(chop_val)
        weights.append(1.0)
        signal_names.append("Chop")
        signal_results["Chop"] = {"value": chop_val, "weight": 1.0, "status": "✅" if chop_val else "❌", "raw": f"{chop:.1f}"}
        
        # 10. Z-Score
        zscore = AdvancedIndicators.zscore(closes, 20)
        zscore_val = 1 if zscore < -0.5 else 0
        signals.append(zscore_val)
        weights.append(0.7)
        signal_names.append("ZScore")
        signal_results["ZScore"] = {"value": zscore_val, "weight": 0.7, "status": "✅" if zscore_val else "❌", "raw": f"{zscore:.2f}"}
        
        # 11. Keltner
        kc = AdvancedIndicators.keltner(highs, lows, closes)
        kc_val = 1 if current < kc['lower'] * 1.01 else 0
        signals.append(kc_val)
        weights.append(0.9)
        signal_names.append("Keltner")
        signal_results["Keltner"] = {"value": kc_val, "weight": 0.9, "status": "✅" if kc_val else "❌"}
        
        # 12. Ichimoku
        ichi = AdvancedIndicators.ichimoku(highs, lows, closes)
        ichi_val = 1 if current > ichi['tenkan'] and current > ichi['kijun'] else 0
        signals.append(ichi_val)
        weights.append(1.2)
        signal_names.append("Ichimoku")
        signal_results["Ichimoku"] = {"value": ichi_val, "weight": 1.2, "status": "✅" if ichi_val else "❌"}
        
        # 13. Vortex
        vortex = AdvancedIndicators.vortex(highs, lows, closes)
        vortex_val = 1 if vortex['vi_plus'] > vortex['vi_minus'] else 0
        signals.append(vortex_val)
        weights.append(0.9)
        signal_names.append("Vortex")
        signal_results["Vortex"] = {"value": vortex_val, "weight": 0.9, "status": "✅" if vortex_val else "❌"}
        
        # 14. CCI
        cci = AdvancedIndicators.cci(closes, highs, lows)
        cci_val = 1 if cci < -50 else 0
        signals.append(cci_val)
        weights.append(0.7)
        signal_names.append("CCI")
        signal_results["CCI"] = {"value": cci_val, "weight": 0.7, "status": "✅" if cci_val else "❌", "raw": f"{cci:.1f}"}
        
        # 15. DMI
        dmi = AdvancedIndicators.dmi(highs, lows, closes)
        dmi_val = 1 if dmi['plus_di'] > dmi['minus_di'] and dmi['adx'] > 15 else 0
        signals.append(dmi_val)
        weights.append(1.1)
        signal_names.append("DMI")
        signal_results["DMI"] = {"value": dmi_val, "weight": 1.1, "status": "✅" if dmi_val else "❌"}
        
        # Calculate weighted score
        weighted_sum = sum(s * w for s, w in zip(signals, weights))
        total_weight = sum(weights)
        confidence = weighted_sum / total_weight
        signal_count = sum(1 for s in signals if s > 0.5)
        
        # Stop and target
        atr = AdvancedIndicators.atr(highs, lows, closes, 14)
        recent_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        
        if regime_type == "dead":
            stop_multiplier = 1.2
            target_multiplier = 2.0
        elif regime_type == "weak":
            stop_multiplier = 1.5
            target_multiplier = 2.5
        else:
            stop_multiplier = 1.5
            target_multiplier = 2.5
        
        stop = max(current - atr * stop_multiplier, recent_low * 0.98)
        target = current + atr * target_multiplier
        
        risk = current - stop
        reward = target - current
        rr_ratio = reward / risk if risk > 0 else 0
        
        # FINAL DECISION - with reduced confidence thresholds
        buy_signal = False
        signal_type = "NO SIGNAL"
        
        if regime_type == "dead":
            # Dead market: 2 signals, 12% confidence
            if signal_count >= min_signals and confidence >= min_confidence and rr_ratio > 1.2:
                buy_signal = True
                signal_type = "DEAD MARKET SIGNAL 💤 (aggressive)"
        elif regime_type == "weak":
            # Weak trend: 3 signals, 20% confidence
            if signal_count >= min_signals and confidence >= min_confidence and rr_ratio > 1.3:
                buy_signal = True
                signal_type = "WEAK TREND SIGNAL 📊"
        else:
            # Strong/Neutral: appropriate thresholds
            if signal_count >= min_signals and confidence >= min_confidence and rr_ratio > 1.5:
                buy_signal = True
                signal_type = "STRONG SIGNAL 🚀"
        
        # Build result
        result = {
            "signal": "BUY" if buy_signal else "NEUTRAL",
            "signal_type": signal_type,
            "confidence": confidence,
            "signal_count": signal_count,
            "total_signals": len(signals),
            "min_signals_used": min_signals,
            "min_confidence_used": min_confidence,
            "regime": regime,
            "regime_type": regime_type,
            "adx": adx,
            "chop": chop,
            "stop": stop,
            "target": target,
            "rr_ratio": rr_ratio,
            "rsi": rsi,
            "position_multiplier": position_multiplier,
            "target_multiplier": target_multiplier,
            "signal_names": [name for name, sig in zip(signal_names, signals) if sig > 0.5],
            "signal_results": signal_results,
            "weighted_sum": weighted_sum,
            "total_weight": total_weight,
        }
        
        # Print detailed breakdown if verbose
        if verbose:
            print("\n" + "="*70)
            print("📊 SIGNAL BREAKDOWN")
            print("="*70)
            print(f"Current Price: ${current:.2f}")
            print(f"Market Regime: {regime}")
            print(f"ADX: {adx:.1f} | Chop: {chop:.1f}")
            print(f"Required Signals: {min_signals}/{len(signals)} ({regime_type.upper()} mode)")
            print(f"Required Confidence: {min_confidence*100:.0f}%")
            print(f"Current Signals: {signal_count}/{len(signals)}")
            print(f"Current Confidence: {confidence:.2%}")
            print(f"R:R Ratio: {rr_ratio:.2f}")
            print(f"Position Size: {position_multiplier*100:.0f}% of normal")
            print("-"*70)
            print("INDIVIDUAL SIGNALS:")
            for name, data in signal_results.items():
                status = data['status']
                raw = f" ({data.get('raw', '')})" if data.get('raw') else ""
                bar = "█" * int(data['value'] * 10) + "░" * (10 - int(data['value'] * 10))
                print(f"  {status} {name:12} {bar}  {data['value']:.1f}x{data['weight']:.1f}{raw}")
            print("-"*70)
            
            if buy_signal:
                print(f"🎯 {signal_type}")
                print(f"   Target: ${target:.2f} (+{((target/current)-1)*100:.1f}%)")
                print(f"   Stop: ${stop:.2f} (-{((1-stop/current))*100:.1f}%)")
                print(f"   Active Signals: {', '.join(result['signal_names'][:8])}")
                if len(result['signal_names']) > 8:
                    print(f"   ... and {len(result['signal_names']) - 8} more")
            else:
                if signal_count < min_signals:
                    print(f"❌ NOT ENOUGH SIGNALS: {signal_count}/{min_signals} needed")
                    print(f"💡 Need {min_signals - signal_count} more signal(s)")
                elif confidence < min_confidence:
                    print(f"❌ LOW CONFIDENCE: {confidence:.2%} (need > {min_confidence*100:.0f}%)")
                elif rr_ratio <= 1.2:
                    print(f"❌ POOR RISK/REWARD: {rr_ratio:.2f} (need > 1.2)")
                else:
                    print("❌ OTHER CONDITIONS NOT MET")
                
                if signal_count > 0:
                    print(f"   Active: {', '.join(result['signal_names'][:5])}")
            print("="*70)
        
        return result

# ========================================================================
# GOLDEN SCALPER BOT - FINAL VERSION
# ========================================================================

class GoldenScalperBot:

    def __init__(self, api_key: str, api_secret: str, 
                 symbol: str = GOLDEN_CONFIG["symbol"],
                 exchange_region: str = "us", 
                 log_level: str = "INFO", 
                 interval: str = GOLDEN_CONFIG["interval"]):
        
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.interval = interval
        self.base_asset = symbol.replace("USDT", "")
        
        self.min_signals_strong = GOLDEN_CONFIG["min_signals_strong"]
        self.min_signals_weak = GOLDEN_CONFIG["min_signals_weak"]
        self.min_signals_dead = GOLDEN_CONFIG["min_signals_dead"]
        self.min_confidence_dead = GOLDEN_CONFIG["min_confidence_dead"]
        self.min_confidence_weak = GOLDEN_CONFIG["min_confidence_weak"]
        self.min_confidence_strong = GOLDEN_CONFIG["min_confidence_strong"]
        self.max_hold_hours = GOLDEN_CONFIG["max_hold_hours"]
        
        self.min_order_usdt = GOLDEN_CONFIG["min_order_usdt"]
        self.max_order_usdt = GOLDEN_CONFIG["max_order_usdt"]
        self.target_profit_pct = GOLDEN_CONFIG["target_profit_pct"]
        self.stop_loss_pct = GOLDEN_CONFIG["stop_loss_pct"]
        
        self.max_drawdown_pct = 0.15
        self.max_consecutive_losses = 4
        
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
        
        self.current_balance_usdt = 0.0
        self.current_balance_asset = 0.0
        self.starting_balance = 0.0
        self.peak_balance = 0.0
        self.consecutive_losses = 0
        self.consecutive_wins = 0
        self.balance_fetched = False
        self.stopped = False
        self.skipped_count = 0
        
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
        self.logger.info("🚀 GOLDEN SCALPER BOT v11.3 - FINAL CONFIDENCE FIX")
        self.logger.info("="*70)
        self.logger.info(f"   Symbol: {symbol}")
        self.logger.info(f"   Interval: {interval}")
        self.logger.info(f"   Dead Market: {self.min_signals_dead} signals, {self.min_confidence_dead*100:.0f}% confidence")
        self.logger.info(f"   Weak Trend: {self.min_signals_weak} signals, {self.min_confidence_weak*100:.0f}% confidence")
        self.logger.info(f"   Strong Trend: {self.min_signals_strong} signals, {self.min_confidence_strong*100:.0f}% confidence")
        self.logger.info(f"   Target: {self.target_profit_pct*100:.1f}%")
        self.logger.info(f"   Stop: {self.stop_loss_pct*100:.1f}%")
        self.logger.info("="*70)
        
        self._check_connectivity()
        self._get_exchange_info()
        self._update_balances()
        self._check_existing_orders()

    def _check_existing_orders(self):
        try:
            resp = self._send_signed_request("GET", "/api/v3/openOrders", {"symbol": self.symbol})
            if "error" not in resp and resp:
                for order in resp:
                    if order.get("side") == "SELL" and order.get("status") == "NEW":
                        self.has_open_position = True
                        self.position_order_id = order.get("orderId")
                        self.position_target_price = float(order.get("price", 0))
                        self.logger.info(f"📊 Found existing SELL order: {self.position_order_id} @ ${self.position_target_price:.2f}")
                        self._get_position_details()
                        break
        except Exception as e:
            self.logger.warning(f"Could not check existing orders: {e}")

    def _get_position_details(self):
        try:
            resp = self._send_signed_request("GET", "/api/v3/myTrades", {"symbol": self.symbol, "limit": 1})
            if "error" not in resp and resp:
                buys = [t for t in resp if t.get("isBuyer")]
                if buys:
                    self.position_entry_price = float(buys[-1].get("price", 0))
                    self.position_entry_qty = float(buys[-1].get("qty", 0))
                    self.position_open_time = datetime.now()
                    self.logger.info(f"📊 Position entry: {self.position_entry_qty:.8f} @ ${self.position_entry_price:.2f}")
        except Exception:
            pass

        if self.position_entry_price > 0:
            if not self.position_stop_price or self.position_stop_price <= 0:
                self.position_stop_price = self.position_entry_price * (1 - self.stop_loss_pct)
                self.logger.info(f"🛠️ Recomputed stop-loss: ${self.position_stop_price:.2f}")
            if not self.position_target_price or self.position_target_price <= 0:
                self.position_target_price = self.position_entry_price * (1 + self.target_profit_pct)
                self.logger.info(f"🛠️ Recomputed target: ${self.position_target_price:.2f}")

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

    def analyze_signal(self, verbose: bool = True) -> Dict:
        klines = AdvancedIndicators.get_klines(self.symbol, self.base_url, interval=self.interval, limit=500)
        if not klines:
            return {"signal": "NEUTRAL", "error": "No data"}
        
        params = {
            'min_signals_strong': self.min_signals_strong,
            'min_signals_weak': self.min_signals_weak,
            'min_signals_dead': self.min_signals_dead,
            'min_confidence_dead': self.min_confidence_dead,
            'min_confidence_weak': self.min_confidence_weak,
            'min_confidence_strong': self.min_confidence_strong,
        }
        signal = FinalConfidenceStrategy.signal(klines, params, verbose=verbose)
        return signal

    def run_cycle(self, cycle_number: int = 0) -> dict:
        if self.stopped:
            return {"success": False, "error": "Bot stopped"}
        
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔄 CYCLE {cycle_number} - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        self.logger.info(f"{'='*60}")

        # Check if we have an open position
        if self.has_open_position:
            if self.position_entry_price > 0 and (not self.position_stop_price or self.position_stop_price <= 0):
                self.position_stop_price = self.position_entry_price * (1 - self.stop_loss_pct)
                self.logger.warning(f"🛠️ Recomputed stop-loss: ${self.position_stop_price:.2f}")
            if self.position_entry_price > 0 and (not self.position_target_price or self.position_target_price <= 0):
                self.position_target_price = self.position_entry_price * (1 + self.target_profit_pct)
                self.logger.warning(f"🛠️ Recomputed target: ${self.position_target_price:.2f}")

            live_price = self.get_current_price()
            hours_held = (datetime.now() - self.position_open_time).total_seconds() / 3600 if self.position_open_time else 0
            
            self.logger.info(f"📊 Position is OPEN - {hours_held:.1f}h / {self.max_hold_hours}h")
            self.logger.info(f"   Entry: ${self.position_entry_price:.2f}")
            self.logger.info(f"   Target: ${self.position_target_price:.2f}")
            self.logger.info(f"   Stop: ${self.position_stop_price:.2f}")
            if live_price:
                unrealized_pct = ((live_price / self.position_entry_price) - 1) * 100
                self.logger.info(f"   Current: ${live_price:.2f}  ({unrealized_pct:+.2f}% vs entry)")
            
            # Check order status
            if self.position_order_id:
                status = self.get_order_status(self.position_order_id)
                if status.get("status") == "FILLED":
                    self.has_open_position = False
                    self.logger.info("✅ Position closed! Processing...")
                    cum_quote = float(status.get("cummulativeQuoteQty", 0))
                    executed_qty = float(status.get("executedQty", 0))
                    if executed_qty > 0 and cum_quote > 0:
                        exit_price = cum_quote / executed_qty
                        realized_pnl = (exit_price - self.position_entry_price) * self.position_entry_qty
                        fee_estimate = (self.position_entry_qty * self.position_entry_price * 0.001) + (self.position_entry_qty * exit_price * 0.001)
                        net_pnl = realized_pnl - fee_estimate
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
                        self._update_balances()
                        return {
                            "success": True,
                            "cycle": cycle_number,
                            "entry_price": self.position_entry_price,
                            "exit_price": exit_price,
                            "quantity": self.position_entry_qty,
                            "profit": realized_pnl,
                            "net_profit": net_pnl,
                            "fees": fee_estimate,
                            "balance_after": self.current_balance_usdt,
                            "win_rate": win_rate,
                        }
            
            # Check stop-loss
            current_price = live_price if live_price else self.get_current_price()
            if current_price and self.position_stop_price > 0:
                if current_price <= self.position_stop_price:
                    self.logger.warning(f"🛑 STOP-LOSS triggered: ${current_price:.2f}")
                    if self.position_order_id:
                        self.cancel_order(self.position_order_id)
                    exit_res = self.place_market_order(side="SELL", amount=self.position_entry_qty, is_quantity=True)
                    if "error" not in exit_res:
                        exit_price = float(exit_res.get("price", current_price))
                        self.has_open_position = False
                        realized_pnl = (exit_price - self.position_entry_price) * self.position_entry_qty
                        fee_estimate = (self.position_entry_qty * self.position_entry_price * 0.001) + (self.position_entry_qty * exit_price * 0.001)
                        net_pnl = realized_pnl - fee_estimate
                        self.logger.info(f"🛑 Stopped out @ ${exit_price:.2f} | P&L: ${net_pnl:.4f}")
                        
                        self.running_pnl += net_pnl
                        self.current_balance_usdt = max(0, self.starting_balance + self.running_pnl)
                        self.total_trades += 1
                        self.loss_count += 1
                        self.consecutive_losses += 1
                        self.consecutive_wins = 0
                        self._update_balances()
                        return {"success": True, "stopped_out": True, "net_profit": net_pnl}
            
            # Check time exit
            if self.position_open_time:
                hours_held = (datetime.now() - self.position_open_time).total_seconds() / 3600
                if hours_held >= self.max_hold_hours:
                    self.logger.info(f"⏰ TIME EXIT: {hours_held:.1f}h exceeded max {self.max_hold_hours}h")
                    if self.position_order_id:
                        self.cancel_order(self.position_order_id)
                    exit_res = self.place_market_order(side="SELL", amount=self.position_entry_qty, is_quantity=True)
                    if "error" not in exit_res:
                        exit_price = float(exit_res.get("price", current_price))
                        self.has_open_position = False
                        realized_pnl = (exit_price - self.position_entry_price) * self.position_entry_qty
                        fee_estimate = (self.position_entry_qty * self.position_entry_price * 0.001) + (self.position_entry_qty * exit_price * 0.001)
                        net_pnl = realized_pnl - fee_estimate
                        self.logger.info(f"⏰ Time exit @ ${exit_price:.2f} | P&L: ${net_pnl:.4f}")
                        
                        self.running_pnl += net_pnl
                        self.current_balance_usdt = max(0, self.starting_balance + self.running_pnl)
                        self.total_trades += 1
                        if net_pnl > 0:
                            self.win_count += 1
                            self.consecutive_wins += 1
                            self.consecutive_losses = 0
                        else:
                            self.loss_count += 1
                            self.consecutive_losses += 1
                            self.consecutive_wins = 0
                        self._update_balances()
                        return {"success": True, "stopped_out": False, "net_profit": net_pnl, "time_exit": True}
            
            self.logger.info("⏳ Position still open - monitoring...")
            return {"success": False, "error": "Position open", "skipped": True}

        # No position - check for new signal
        self._update_balances()
        self.logger.info(f"💰 USDT: ${self.current_balance_usdt:.2f} | {self.base_asset}: {self.current_balance_asset:.8f}")
        
        if self.current_balance_usdt < self.min_order_usdt:
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

        # Get detailed signal analysis (verbose = True shows full breakdown)
        self.logger.info("📊 Analyzing market for entry signal...")
        signal = self.analyze_signal(verbose=True)
        
        if "error" in signal:
            self.logger.warning(f"⚠️ {signal['error']}")
            return {"success": False, "error": signal['error'], "skipped": True}
        
        if signal['signal'] != "BUY":
            # Log why no signal (with details from breakdown)
            signal_count = signal.get('signal_count', 0)
            min_signals = signal.get('min_signals_used', 2)
            min_confidence = signal.get('min_confidence_used', 0.12)
            confidence = signal.get('confidence', 0)
            rr_ratio = signal.get('rr_ratio', 0)
            regime = signal.get('regime', 'Unknown')
            
            self.logger.info(f"⏭️ No BUY signal - Market: {regime}")
            
            if signal_count < min_signals:
                self.logger.info(f"   ❌ Only {signal_count}/{min_signals} signals active (need {min_signals})")
            elif confidence < min_confidence:
                self.logger.info(f"   ❌ Confidence {confidence:.2%} (need > {min_confidence*100:.0f}%)")
            elif rr_ratio <= 1.2:
                self.logger.info(f"   ❌ Risk/Reward {rr_ratio:.2f} (need > 1.2)")
            else:
                self.logger.info(f"   ❌ Other conditions not met")
            
            # Show active signals summary
            active_signals = signal.get('signal_names', [])
            if active_signals:
                self.logger.info(f"   ✅ Active signals: {', '.join(active_signals)}")
            
            return {"success": False, "error": "No signal", "skipped": True}
        
        # BUY SIGNAL! Execute trade
        signal_type = signal.get('signal_type', 'BUY SIGNAL')
        position_multiplier = signal.get('position_multiplier', 0.6)
        
        self.logger.info(f"🚀 {signal_type} CONFIRMED! Executing trade...")
        self.logger.info(f"   Position size: {position_multiplier*100:.0f}% of normal")
        
        current_price = self.get_current_price()
        if not current_price:
            return {"success": False, "error": "No price"}

        # Adaptive position sizing
        position_usdt = min(self.max_order_usdt, self.current_balance_usdt * 0.15 * position_multiplier)
        position_usdt = max(self.min_order_usdt, position_usdt)
        
        self.logger.info(f"📈 Buying ${position_usdt:.2f} worth of {self.base_asset}")
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

        # Use adaptive target/stop
        regime_type = signal.get('regime_type', 'dead')
        if regime_type == "dead":
            target_multiplier = 0.7
            stop_multiplier = 1.2
        elif regime_type == "weak":
            target_multiplier = 0.85
            stop_multiplier = 1.0
        else:
            target_multiplier = 1.0
            stop_multiplier = 1.0
        
        if signal.get('stop') and signal.get('target'):
            stop_price = max(self.buy_price * (1 - self.stop_loss_pct * stop_multiplier), signal['stop'])
            target_price = min(self.buy_price * (1 + self.target_profit_pct * target_multiplier), signal['target'])
        else:
            stop_price = self.buy_price * (1 - self.stop_loss_pct * stop_multiplier)
            target_price = self.buy_price * (1 + self.target_profit_pct * target_multiplier)
        
        sell_qty = min(self.buy_qty, self.current_balance_asset * 0.995)
        sell_qty = round_to_step(sell_qty, self._min_qty)
        
        if sell_qty <= 0:
            self.logger.error(f"❌ No {self.base_asset} to sell")
            return {"success": False, "error": "No asset to sell"}
        
        self.logger.info(f"📊 Selling {sell_qty:.8f} {self.base_asset}")
        self.logger.info(f"🎯 Target: ${target_price:.2f} (+{((target_price/self.buy_price)-1)*100:.2f}%)")
        self.logger.info(f"🛑 Stop: ${stop_price:.2f} (-{((1 - stop_price/self.buy_price))*100:.2f}%)")
        
        sell_order = self.place_limit_order(side="SELL", quantity=sell_qty, price=target_price)
        
        if "error" in sell_order:
            self.logger.error(f"❌ Sell limit failed: {sell_order}")
            self.logger.info("🔄 Trying market sell as fallback...")
            sell_order = self.place_market_order(side="SELL", amount=sell_qty, is_quantity=True)
            if "error" in sell_order:
                self.logger.error(f"❌ Market sell also failed: {sell_order}")
                return {"success": False, "error": "Sell failed"}
            exit_price = float(sell_order.get("price", current_price))
            self.logger.info(f"✅ Market SELL filled @ ${exit_price:.2f}")
            
            realized_pnl = (exit_price - self.buy_price) * sell_qty
            fee_estimate = (sell_qty * self.buy_price * self.maker_fee_rate) + (sell_qty * exit_price * self.taker_fee_rate)
            net_pnl = realized_pnl - fee_estimate
            self.total_fees += fee_estimate
            self._update_balances()
            
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
                "balance_after": self.current_balance_usdt,
                "win_rate": win_rate,
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
        
        self.position_order_id = sell_order.get("orderId")
        if not self.position_order_id:
            return {"success": False, "error": "No sell orderId"}
        
        self.has_open_position = True
        self.position_entry_price = self.buy_price
        self.position_entry_qty = sell_qty
        self.position_target_price = target_price
        self.position_stop_price = stop_price
        self.position_open_time = datetime.now()
        
        self.logger.info(f"✅ SELL LIMIT order placed: {self.position_order_id}")
        self.logger.info(f"⏳ Position open - waiting for target ${target_price:.2f}")
        self.logger.info(f"   Stop-loss at ${stop_price:.2f}")
        self.logger.info(f"   Max hold: {self.max_hold_hours} hours")

        return {"success": True, "position_open": True, "order_id": self.position_order_id}

    def run_forever(self):
        self.logger.info("\n" + "="*70)
        self.logger.info("🚀 GOLDEN SCALPER BOT v11.3 - FINAL CONFIDENCE FIX")
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
                    if self.has_open_position:
                        self.logger.info(f"⏳ Position open - monitoring every 60s...")
                    else:
                        self.logger.info(f"⏭️ No signal - checking every 5 minutes")
                else:
                    self.logger.error(f"⚠️ Failed: {result.get('error', 'Unknown')}")
                
                if self.total_trades > 0:
                    win_rate = (self.win_count / self.total_trades) * 100
                    self.logger.info(f"📊 STATS: {self.total_trades} trades, {win_rate:.1f}% win, ${self.cycle_stats['net_profit']:.4f}")
                
                if self.consecutive_wins >= 10:
                    self.logger.info("🎉🎉🎉 10 CONSECUTIVE WINS! 🎉🎉🎉")
                    self.stopped = True
                    break
                
                if self.has_open_position:
                    wait_time = 60
                    self.logger.info(f"⏳ Monitoring position - next check in {wait_time}s")
                else:
                    wait_time = 300
                    self.logger.info(f"⏳ No position - next check in {wait_time//60} minutes")
                
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
    print("🚀 GOLDEN SCALPER BOT v11.3 - FINAL CONFIDENCE FIX")
    print("="*70)
    print(f"\n🎯 {GOLDEN_CONFIG['symbol']} {GOLDEN_CONFIG['interval']}")
    print(f"   ✅ DEAD MARKET: 2 signals, 12% confidence (was 25%)")
    print(f"   ✅ WEAK TREND: 3 signals, 20% confidence (was 30%)")
    print(f"   ✅ STRONG TREND: 6 signals, 30% confidence (was 35%)")
    print(f"   ✅ This will trigger with just RSI + Bollinger!")
    print(f"\n🚀 Starting in 3 seconds...")
    time.sleep(3)
    
    bot = GoldenScalperBot(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol=GOLDEN_CONFIG["symbol"],
        exchange_region="us",
        log_level="INFO",
        interval=GOLDEN_CONFIG["interval"]
    )
    
    bot.run_forever()
