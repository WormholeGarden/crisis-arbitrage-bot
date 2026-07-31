#!/usr/bin/env python3
"""
ENSEMBLE STRATEGY - HONEST VALIDATION
============================================================
This takes the 10-strategy ensemble voter from your "Golden Ticket"
run and re-tests it properly. The indicator/strategy code is reused
almost as-is (it's reasonable); what's fixed is the SEARCH
METHODOLOGY, which is where the previous result fell apart:

  1. The original optimizer tested ~160 parameter combos x 8
     symbol/timeframe pairs (~1,280 total) and reported whichever
     ONE scored highest on a SINGLE train/test split, with no
     correction for how many things were tried. That's exactly the
     multiple-comparisons trap: test ~1,280 things and some will
     look great by chance alone.
  2. It reported Sharpe/Sortino using sqrt(252), which assumes daily
     return sampling. These are per-trade returns from ~20 trades -
     that annualization inflates the numbers and isn't meaningful at
     this sample size regardless.

This script instead:
  - Tests a SMALL, pre-specified set of parameter variants (not a
    1,280-wide sweep) around what was reported as promising.
  - Splits each symbol's history into multiple NON-OVERLAPPING
    blocks and requires consistency across most of them.
  - Pools out-of-sample trades and runs a significance test with a
    Bonferroni correction sized to the ACTUAL number of combinations
    tested here (symbols x param variants).
  - Reports honestly if there isn't enough trade volume at 4h to
    validate anything meaningfully - which is a real risk given the
    original run only produced 18-29 trades per symbol over the
    ENTIRE test window, before any block-splitting.

If nothing survives this, that is the answer, not a reason to widen
the search further.
============================================================
"""

import time
import math
import statistics
from typing import Dict, List, Optional
import requests

# ========================================================================
# INDICATORS (reused from your script - these are fine as-is)
# ========================================================================

class Indicators:
    @staticmethod
    def get_klines(symbol: str, base_url: str, interval: str = "4h", limit: int = 1000,
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
    def atr(highs, lows, closes, period: int = 14) -> float:
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
            last = closes[-1] if closes else 0
            return {"upper": last, "middle": last, "lower": last, "position": 0.5}
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
    def adx(highs, lows, closes, period: int = 14) -> float:
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
    def vwap(highs, lows, closes, volumes) -> float:
        if not volumes or sum(volumes) == 0:
            return closes[-1] if closes else 0
        typical = [(h + l + c) / 3 for h, l, c in zip(highs, lows, closes)]
        return sum(t * v for t, v in zip(typical, volumes)) / sum(volumes)

    @staticmethod
    def chop(highs, lows, closes, period: int = 14) -> float:
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
# THE 10 STRATEGIES (reused as-is from your script, unchanged logic)
# ========================================================================

class StrategyBreakout:
    name = "Breakout"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows = data['closes'], data['highs'], data['lows']
        current = closes[-1]
        donchian_high = max(highs[-20:]); donchian_low = min(lows[-20:])
        adx_val = Indicators.adx(highs, lows, closes, 14)
        rsi_val = Indicators.rsi(closes, 14)
        buy = 0; total = 4
        if current > donchian_high: buy += 1
        if adx_val > 25: buy += 1
        if rsi_val < 70: buy += 1
        if current > Indicators.ema(closes, 50): buy += 1
        confidence = buy / total
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence,
                "stop": donchian_low, "target": current + (current - donchian_low) * 1.5}

class StrategyMeanReversion:
    name = "MeanRev"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows, volumes = data['closes'], data['highs'], data['lows'], data['volumes']
        current = closes[-1]
        bb = Indicators.bollinger(closes, 20, 2)
        rsi_val = Indicators.rsi(closes, 14)
        atr_val = Indicators.atr(highs, lows, closes, 14)
        vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        buy = 0; total = 4
        if current < bb['lower'] * 1.02: buy += 1
        if 20 < rsi_val < 40: buy += 1
        if volumes[-1] > vol_avg * 1.2: buy += 1
        if current < Indicators.ema(closes, 20): buy += 1
        confidence = buy / total
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence,
                "stop": current - atr_val * 1.5, "target": current + (bb['middle'] - bb['lower']) * 0.5}

class StrategyVolumeAccumulation:
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
        price_change = (closes[-1] - closes[-20]) / closes[-20] if len(closes) >= 20 else 0
        obv_change = (obv_values[-1] - obv_values[-20]) / (abs(obv_values[-20]) + 0.001) if len(obv_values) >= 20 else 0
        buy = 0; total = 4
        if obv_values[-1] > obv_ema: buy += 1
        if current > vwap_val: buy += 1
        if price_change < 0 and obv_change > 0: buy += 1
        if volumes[-1] > sum(volumes[-10:]) / 10: buy += 1
        confidence = buy / total
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence,
                "stop": current * 0.97, "target": current * 1.05}

class StrategyTrendFollowing:
    name = "Trend"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes = data['closes']
        current = closes[-1]
        macd = Indicators.macd(closes, 12, 26, 9)
        ema9 = Indicators.ema(closes, 9); ema21 = Indicators.ema(closes, 21); ema50 = Indicators.ema(closes, 50)
        rsi_val = Indicators.rsi(closes, 14)
        buy = 0; total = 4
        if macd['bullish']: buy += 1
        if current > ema9 > ema21: buy += 1
        if current > ema50: buy += 1
        if 40 < rsi_val < 70: buy += 1
        confidence = buy / total
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence,
                "stop": ema21 * 0.98, "target": current * 1.04}

class StrategyVolatilityBreakout:
    name = "VolBreak"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows = data['closes'], data['highs'], data['lows']
        current = closes[-1]
        atr_val = Indicators.atr(highs, lows, closes, 14)
        atr_pct = atr_val / current if current > 0 else 0
        range_high = max(highs[-10:]); range_low = min(lows[-10:])
        range_size = (range_high - range_low) / current if current > 0 else 0
        vol_avg = sum([(highs[i] - lows[i]) / closes[i] for i in range(-20, -1)]) / 20 if len(closes) >= 20 else 0
        buy = 0; total = 4
        if current > range_high: buy += 1
        if atr_pct > 0.02: buy += 1
        if range_size > vol_avg * 0.5: buy += 1
        if Indicators.chop(highs, lows, closes, 14) < 40: buy += 1
        confidence = buy / total
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence,
                "stop": current - atr_val * 1.5, "target": current + atr_val * 2.5}

class StrategyPullback:
    name = "Pullback"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows = data['closes'], data['highs'], data['lows']
        current = closes[-1]
        ema21 = Indicators.ema(closes, 21); ema50 = Indicators.ema(closes, 50)
        rsi_val = Indicators.rsi(closes, 14)
        buy = 0; total = 4
        if current > ema50: buy += 1
        if current > ema21: buy += 1
        if abs(current - ema21) / ema21 < 0.01: buy += 1
        if 30 < rsi_val < 50: buy += 1
        confidence = buy / total
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence,
                "stop": ema21 * 0.97, "target": current * 1.04}

class StrategyDivergence:
    name = "Divergence"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes = data['closes']
        current = closes[-1]
        if len(closes) < 30:
            return {"signal": "NEUTRAL", "confidence": 0}
        macd = Indicators.macd(closes, 12, 26, 9)
        price_min = min(closes[-20:])
        buy = 0; total = 3
        if (price_min < min(closes[-21:-19]) if len(closes) > 20 else False) and macd['histogram'] > 0:
            buy += 1
        if macd['bullish']: buy += 1
        if Indicators.rsi(closes, 14) < 45: buy += 1
        confidence = buy / total
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence,
                "stop": current * 0.97, "target": current * 1.05}

class StrategyOpeningRange:
    name = "OpenRange"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, highs, lows = data['closes'], data['highs'], data['lows']
        current = closes[-1]
        if len(closes) < 4:
            return {"signal": "NEUTRAL", "confidence": 0}
        range_high = max(highs[-4:]); range_low = min(lows[-4:])
        range_size = range_high - range_low
        buy = 0; total = 3
        if current > range_high: buy += 1
        if range_size > 0.005 * current: buy += 1
        if Indicators.rsi(closes, 14) < 70: buy += 1
        confidence = buy / total
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence,
                "stop": range_low, "target": range_high + range_size * 1.5}

class StrategyStatArb:
    name = "StatArb"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes = data['closes']
        current = closes[-1]
        if len(closes) < 20:
            return {"signal": "NEUTRAL", "confidence": 0}
        zscore = Indicators.zscore(closes, 20)
        rsi_val = Indicators.rsi(closes, 14)
        buy = 0; total = 3
        if zscore < -2: buy += 1
        if rsi_val < 35: buy += 1
        if zscore < -1 and current < Indicators.ema(closes, 20): buy += 1
        confidence = buy / total
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence,
                "stop": current * 0.97, "target": current * (1 - zscore * 0.01)}

class StrategyMultiTimeframe:
    name = "MultiTF"
    @staticmethod
    def signal(data: Dict) -> Dict:
        closes, volumes = data['closes'], data['volumes']
        current = closes[-1]
        conditions = []
        if current > Indicators.ema(closes, 10): conditions.append(1)
        if current > Indicators.ema(closes, 20): conditions.append(1)
        if current > Indicators.ema(closes, 50): conditions.append(1)
        if Indicators.macd(closes, 12, 26, 9)['bullish']: conditions.append(1)
        vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        if volumes[-1] > vol_avg * 1.1: conditions.append(1)
        buy = len(conditions); total = 5
        confidence = buy / total
        return {"signal": "BUY" if confidence >= 0.5 else "NEUTRAL", "confidence": confidence,
                "stop": current * 0.97, "target": current * 1.04}

ALL_STRATEGIES = [StrategyBreakout(), StrategyMeanReversion(), StrategyVolumeAccumulation(),
                   StrategyTrendFollowing(), StrategyVolatilityBreakout(), StrategyPullback(),
                   StrategyDivergence(), StrategyOpeningRange(), StrategyStatArb(), StrategyMultiTimeframe()]

class EnsembleVoter:
    @staticmethod
    def analyze(data: Dict, min_votes: int, min_confidence: float) -> Dict:
        signals = []
        for strategy in ALL_STRATEGIES:
            try:
                result = strategy.signal(data)
                if result and result.get('signal') == "BUY":
                    signals.append(result)
            except Exception:
                continue
        votes = [s.get('confidence', 0) for s in signals]
        avg_confidence = sum(votes) / len(votes) if votes else 0
        stops = [s['stop'] for s in signals if s.get('stop')]
        targets = [s['target'] for s in signals if s.get('target')]
        final_stop = statistics.median(stops) if stops else data['closes'][-1] * 0.97
        final_target = statistics.median(targets) if targets else data['closes'][-1] * 1.04
        ensemble_buy = len(signals) >= min_votes and avg_confidence >= min_confidence
        return {"signal": "BUY" if ensemble_buy else "NEUTRAL", "votes": len(signals),
                "confidence": avg_confidence, "stop_price": final_stop, "target_price": final_target}

# ========================================================================
# ROBUST MULTI-BLOCK VALIDATOR (this is what's actually new/fixed)
# ========================================================================

MAKER_FEE = 0.001
TAKER_FEE = 0.001
ROUND_TRIP_FEE = MAKER_FEE + TAKER_FEE

def fetch_history(symbol: str, interval: str, days_back: int, base_url: str = "https://api.binance.us") -> Dict:
    interval_minutes = {"1h": 60, "2h": 120, "4h": 240, "6h": 360, "8h": 480, "12h": 720, "1d": 1440}
    candles_per_day = 1440 // interval_minutes.get(interval, 240)
    needed = days_back * candles_per_day
    print(f"  Fetching ~{days_back}d ({needed} candles) of {interval} {symbol}...")
    all_data = {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
    end_time = None
    while len(all_data["closes"]) < needed:
        batch = Indicators.get_klines(symbol, base_url, interval, limit=1000, end_time_ms=end_time)
        if not batch or not batch["timestamps"]:
            break
        for k in all_data:
            all_data[k] = batch[k] + all_data[k]
        end_time = batch["timestamps"][0] - 1
        time.sleep(0.2)
    return all_data


def precompute_ensemble_signals(klines: Dict, min_votes_options: List[int]) -> Dict[int, List[Optional[Dict]]]:
    """Precompute per-strategy votes ONCE per candle (the expensive part),
    then derive results for each min_votes threshold cheaply. min_confidence
    and trailing params don't affect the vote count, so this only needs to
    vary over min_votes to avoid redundant work."""
    total = len(klines["closes"])
    raw_votes: List[Optional[List[Dict]]] = [None] * total
    for i in range(300, total):
        window = {k: klines[k][i-300:i] for k in klines}
        signals = []
        for strategy in ALL_STRATEGIES:
            try:
                result = strategy.signal(window)
                if result and result.get('signal') == "BUY":
                    signals.append(result)
            except Exception:
                continue
        raw_votes[i] = signals
    return raw_votes


def simulate(klines: Dict, raw_votes: List[Optional[List[Dict]]], min_votes: int,
             min_confidence: float, trailing_stop: bool, trailing_pct: float,
             max_hold_bars: int = 48) -> List[float]:
    closes, highs, lows = klines["closes"], klines["highs"], klines["lows"]
    total = len(closes)
    trades = []
    in_position = False
    entry_price = entry_i = stop_price = target_price = highest = None

    for i in range(300, total):
        if not in_position:
            signals = raw_votes[i] or []
            votes = [s.get('confidence', 0) for s in signals]
            avg_conf = sum(votes) / len(votes) if votes else 0
            if len(signals) >= min_votes and avg_conf >= min_confidence:
                stops = [s['stop'] for s in signals if s.get('stop')]
                targets = [s['target'] for s in signals if s.get('target')]
                entry_price = closes[i]
                stop_price = statistics.median(stops) if stops else entry_price * 0.97
                target_price = statistics.median(targets) if targets else entry_price * 1.04
                highest = entry_price
                entry_i = i
                in_position = True
        else:
            if closes[i] > highest:
                highest = closes[i]
            exit_price = None
            if lows[i] <= stop_price:
                exit_price = stop_price
            elif highs[i] >= target_price:
                exit_price = target_price
            if trailing_stop and exit_price is None:
                trail_stop = highest * (1 - trailing_pct * 0.02)
                if lows[i] <= trail_stop:
                    exit_price = trail_stop
            if exit_price is None and (i - entry_i) > max_hold_bars:
                exit_price = closes[i]
            if exit_price is not None:
                gross = (exit_price - entry_price) / entry_price
                trades.append(gross - ROUND_TRIP_FEE)
                in_position = False
    return trades


def summarize(trades: List[float]) -> Dict:
    if not trades:
        return {"trades": 0, "win_rate": 0, "expectancy_pct": 0}
    wins = [t for t in trades if t > 0]
    return {"trades": len(trades), "win_rate": len(wins) / len(trades),
            "expectancy_pct": sum(trades) / len(trades)}


def run_robust_ensemble_validation(symbols_intervals_days, param_variants, n_folds=3,
                                    alpha=0.05, min_trades_per_fold=6):
    """
    symbols_intervals_days: list of (symbol, interval, days_back)
    param_variants: list of dicts with min_votes/min_confidence/trailing_stop/trailing_pct

    Deliberately small (not 1,280-combo) search: n_symbols * n_variants total
    tests, corrected with Bonferroni for exactly that count.
    """
    n_combos = len(symbols_intervals_days) * len(param_variants)
    bonferroni_alpha = alpha / n_combos
    normal = statistics.NormalDist()
    print(f"Testing {n_combos} total (symbol, params) combinations.")
    print(f"Bonferroni-corrected significance bar: p < {bonferroni_alpha:.6f} (uncorrected alpha={alpha})\n")

    all_results = []

    for symbol, interval, days_back in symbols_intervals_days:
        print(f"\n{'='*70}\n{symbol} {interval}\n{'='*70}")
        klines = fetch_history(symbol, interval, days_back)
        total = len(klines["closes"])
        if total < 300 * (n_folds + 1):
            print(f"  Not enough data ({total} candles) for {n_folds} blocks - skipping.")
            continue

        block_size = total // n_folds
        blocks = []
        for f in range(n_folds):
            start = f * block_size
            end = total if f == n_folds - 1 else (f + 1) * block_size
            lookback_start = max(0, start - 300)
            blocks.append({k: klines[k][lookback_start:end] for k in klines})

        min_votes_needed = sorted(set(v['min_votes'] for v in param_variants))
        print(f"  Precomputing strategy votes per block for min_votes in {min_votes_needed}...")
        block_votes = [precompute_ensemble_signals(b, min_votes_needed) for b in blocks]

        for params in param_variants:
            pooled_trades = []
            blocks_positive = 0
            blocks_tested = 0
            for block, raw_votes in zip(blocks, block_votes):
                trades = simulate(block, raw_votes, params['min_votes'], params['min_confidence'],
                                   params['trailing_stop'], params['trailing_pct'])
                if len(trades) < min_trades_per_fold:
                    continue
                blocks_tested += 1
                s = summarize(trades)
                if s['expectancy_pct'] > 0:
                    blocks_positive += 1
                pooled_trades.extend(trades)

            label = (f"votes>={params['min_votes']} conf>={params['min_confidence']:.1f} "
                     f"trail={params['trailing_pct']:.1f}% trail_stop={params['trailing_stop']}")

            if blocks_tested < max(2, n_folds - 1) or len(pooled_trades) < min_trades_per_fold * 2:
                print(f"  [{label}] insufficient trade volume to validate "
                      f"({len(pooled_trades)} pooled trades across {blocks_tested}/{n_folds} usable blocks) - SKIP")
                continue

            mean_ret = sum(pooled_trades) / len(pooled_trades)
            stdev_ret = statistics.stdev(pooled_trades) if len(pooled_trades) > 1 else 0
            if stdev_ret == 0:
                continue
            se = stdev_ret / (len(pooled_trades) ** 0.5)
            z = mean_ret / se
            p_value = 2 * (1 - normal.cdf(abs(z)))
            consistency_ok = blocks_positive >= max(2, int(0.8 * blocks_tested))
            significant = mean_ret > 0 and p_value < bonferroni_alpha

            status = "PASS" if (consistency_ok and significant) else "fail"
            print(f"  [{label}] {len(pooled_trades)} trades, positive in {blocks_positive}/{blocks_tested} "
                  f"blocks, mean/trade={mean_ret*100:.3f}%, p={p_value:.5f}  -> {status}")

            if consistency_ok and significant:
                all_results.append({"symbol": symbol, "interval": interval, **params,
                                     "pooled_trades": len(pooled_trades), "blocks_positive": blocks_positive,
                                     "blocks_tested": blocks_tested, "mean_return_pct": mean_ret,
                                     "p_value": p_value})

    print("\n" + "="*70)
    if not all_results:
        print("RESULT: Nothing survived multi-block consistency + Bonferroni-corrected")
        print("significance testing. Given the original run only produced 18-29 total")
        print("trades per symbol over the WHOLE test window, splitting into blocks for")
        print("a proper consistency check often leaves too few trades per block to")
        print("reach any real conclusion at 4h - that data scarcity, not a broken test,")
        print("is very plausibly the honest limiting factor here.")
        print("="*70)
        return []

    all_results.sort(key=lambda r: r["p_value"])
    print(f"RESULT: {len(all_results)} combination(s) passed:")
    for r in all_results:
        print(f"  {r['symbol']} {r['interval']} votes>={r['min_votes']} conf>={r['min_confidence']:.1f} "
              f"trail={r['trailing_pct']:.1f}% | {r['pooled_trades']} trades | "
              f"{r['blocks_positive']}/{r['blocks_tested']} blocks positive | p={r['p_value']:.6f}")
    print("="*70)
    return all_results


if __name__ == "__main__":
    # Deliberately small, pre-specified variants around what the original
    # run flagged - NOT a re-run of the 160-combo grid. Bonferroni below
    # is sized to exactly this many tests.
    param_variants = [
        {"min_votes": 1, "min_confidence": 0.2, "trailing_stop": False, "trailing_pct": 0.3},
        {"min_votes": 1, "min_confidence": 0.3, "trailing_stop": False, "trailing_pct": 0.3},
        {"min_votes": 2, "min_confidence": 0.3, "trailing_stop": False, "trailing_pct": 0.3},
        {"min_votes": 2, "min_confidence": 0.3, "trailing_stop": True, "trailing_pct": 0.5},
    ]

    # Longer history than the original 180 days, so blocks have a chance
    # of containing enough trades to say anything at all.
    symbols_intervals_days = [
        ("ETHUSDT", "4h", 700),
        ("BTCUSDT", "4h", 700),
        ("LINKUSDT", "4h", 700),
        ("SOLUSDT", "4h", 700),
    ]

    run_robust_ensemble_validation(symbols_intervals_days, param_variants, n_folds=3)
