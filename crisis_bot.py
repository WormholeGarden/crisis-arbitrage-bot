#!/usr/bin/env python3
"""
ML ENSEMBLE STRATEGY - HONEST VALIDATION (fixes v4.0's methodology)
============================================================
What was wrong with v4.0, concretely:
  - min_trades=3 per block let near-empty samples count as "valid"
  - No significance test anywhere - just picked whichever of ~800
    tested (symbol x parameter) combinations scored highest, with
    zero correction for how many things were tried
  - The reported "winner" (AVAXUSDT 1d) had 14 total trades, from
    as few as 2-3 usable blocks - a profit factor of 4.16 on that
    sample size is well within what pure noise produces routinely
  - 0.05%/0.05% fees assumed a fee tier most retail accounts don't
    have

This script keeps the same 15-indicator ensemble (the indicator math
itself isn't the problem) and replaces the validation methodology:
  - Realistic minimum trade counts per block (not 3)
  - A small, PRE-SPECIFIED parameter set (not an 800-wide sweep)
  - Bonferroni-corrected significance test on pooled out-of-sample
    trades, sized to the actual number of combinations tested here
  - Default fees restored to 0.1%/0.1% - check your own account's
    real fee tier and adjust if you have solid evidence it's lower
  - Precomputes each candle's indicator signal ONCE (independent of
    min_signals/trailing/hold parameters) so the sweep is fast

This can still - and quite plausibly will - come back with nothing.
That's the honest answer if nothing here holds up.
============================================================
"""

import time
import math
import statistics
from datetime import datetime
from typing import Dict, List, Optional
import requests

MAKER_FEE = 0.001   # 0.1% - adjust only if you've confirmed your actual account tier
TAKER_FEE = 0.001   # 0.1%
ROUND_TRIP_FEE = MAKER_FEE + TAKER_FEE

# ========================================================================
# INDICATORS (reused from v4.0 - the math here is reasonable)
# ========================================================================

class AdvancedIndicators:
    @staticmethod
    def get_klines(symbol: str, base_url: str, interval: str = "1d", limit: int = 1000,
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
                    "timestamps": [c[0] for c in data], "opens": [float(c[1]) for c in data],
                    "highs": [float(c[2]) for c in data], "lows": [float(c[3]) for c in data],
                    "closes": [float(c[4]) for c in data], "volumes": [float(c[5]) for c in data],
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
    def atr(highs, lows, closes, period: int = 14) -> float:
        if len(closes) < period + 1:
            return (max(highs) - min(lows)) if highs and lows else 0
        tr_values = []
        for i in range(1, len(closes)):
            tr_values.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        return sum(tr_values[-period:]) / period

    @staticmethod
    def macd(closes: List[float], fast=12, slow=26, signal=9) -> Dict:
        if len(closes) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0, "bullish": False}
        ema_fast = AdvancedIndicators.ema(closes, fast)
        ema_slow = AdvancedIndicators.ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = AdvancedIndicators.ema([macd_line] * signal, signal)
        return {"macd": macd_line, "signal": signal_line, "histogram": macd_line - signal_line,
                "bullish": macd_line > signal_line}

    @staticmethod
    def bollinger(closes: List[float], period: int = 20, std_dev: float = 2) -> Dict:
        if len(closes) < period:
            last = closes[-1] if closes else 0
            return {"upper": last, "middle": last, "lower": last, "position": 0.5}
        middle = sum(closes[-period:]) / period
        squared = [(x - middle) ** 2 for x in closes[-period:]]
        std = (sum(squared) / period) ** 0.5
        upper = middle + std * std_dev
        lower = middle - std * std_dev
        return {"upper": upper, "middle": middle, "lower": lower,
                "position": (closes[-1]-lower)/(upper-lower) if upper != lower else 0.5}

    @staticmethod
    def stochastic(closes, highs, lows, period: int = 14) -> float:
        if len(closes) < period:
            return 50.0
        hh, ll = max(highs[-period:]), min(lows[-period:])
        return ((closes[-1]-ll)/(hh-ll))*100 if hh != ll else 50.0

    @staticmethod
    def adx(highs, lows, closes, period: int = 14) -> float:
        if len(closes) < period + 1:
            return 25.0
        plus_dm, minus_dm, tr = [], [], []
        for i in range(1, len(closes)):
            up = highs[i]-highs[i-1]; down = lows[i-1]-lows[i]
            plus_dm.append(up if up > down and up > 0 else 0)
            minus_dm.append(down if down > up and down > 0 else 0)
            tr.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        tr_ema = AdvancedIndicators.ema(tr[-period:], period)
        if tr_ema == 0:
            return 25.0
        plus_di = 100*(AdvancedIndicators.ema(plus_dm[-period:], period)/tr_ema)
        minus_di = 100*(AdvancedIndicators.ema(minus_dm[-period:], period)/tr_ema)
        dx = 100*abs(plus_di-minus_di)/(plus_di+minus_di) if (plus_di+minus_di) > 0 else 0
        return AdvancedIndicators.ema([dx]*period, period)

    @staticmethod
    def obv(closes: List[float], volumes: List[float]) -> List[float]:
        if not closes or not volumes:
            return []
        vals = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]: vals.append(vals[-1]+volumes[i])
            elif closes[i] < closes[i-1]: vals.append(vals[-1]-volumes[i])
            else: vals.append(vals[-1])
        return vals

    @staticmethod
    def vwap(highs, lows, closes, volumes) -> float:
        if not volumes or sum(volumes) == 0:
            return closes[-1] if closes else 0
        typical = [(h+l+c)/3 for h, l, c in zip(highs, lows, closes)]
        return sum(t*v for t, v in zip(typical, volumes))/sum(volumes)

    @staticmethod
    def chop(highs, lows, closes, period: int = 14) -> float:
        if len(closes) < period:
            return 50.0
        tr_sum = sum(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
                      for i in range(len(closes)-period, len(closes)))
        hh, ll = max(highs[-period:]), min(lows[-period:])
        if hh == ll:
            return 50.0
        return max(0, min(100, 100*math.log10(tr_sum/(hh-ll))/math.log10(period)))

    @staticmethod
    def zscore(data: List[float], period: int = 20) -> float:
        if len(data) < period:
            return 0
        window = data[-period:]
        mean = sum(window)/period
        std = statistics.stdev(window) if period > 1 else 0.001
        return (data[-1]-mean)/std if std > 0 else 0

    @staticmethod
    def keltner(highs, lows, closes, period: int = 20) -> Dict:
        if len(closes) < period:
            last = closes[-1] if closes else 0
            return {"upper": last, "middle": last, "lower": last}
        middle = AdvancedIndicators.ema(closes, period)
        atr_val = AdvancedIndicators.atr(highs, lows, closes, 10)
        return {"upper": middle+atr_val*1.5, "middle": middle, "lower": middle-atr_val*1.5}

    @staticmethod
    def ichimoku(highs, lows, closes) -> Dict:
        if len(closes) < 52:
            last = closes[-1] if closes else 0
            return {"tenkan": last, "kijun": last, "senkou_a": last, "senkou_b": last}
        tenkan = (max(highs[-9:])+min(lows[-9:]))/2
        kijun = (max(highs[-26:])+min(lows[-26:]))/2
        return {"tenkan": tenkan, "kijun": kijun, "senkou_a": (tenkan+kijun)/2,
                "senkou_b": (max(highs[-52:])+min(lows[-52:]))/2}

    @staticmethod
    def vortex(highs, lows, closes, period: int = 14) -> Dict:
        if len(closes) < period+1:
            return {"vi_plus": 0, "vi_minus": 0}
        vm_plus, vm_minus, tr = [], [], []
        for i in range(1, len(closes)):
            vm_plus.append(abs(highs[i]-lows[i-1])); vm_minus.append(abs(lows[i]-highs[i-1]))
            tr.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        s_tr = sum(tr[-period:])
        return {"vi_plus": sum(vm_plus[-period:])/s_tr if s_tr > 0 else 0,
                "vi_minus": sum(vm_minus[-period:])/s_tr if s_tr > 0 else 0}

    @staticmethod
    def cci(closes, highs, lows, period: int = 20) -> float:
        if len(closes) < period:
            return 0
        tp = [(h+l+c)/3 for h, l, c in zip(highs, lows, closes)]
        sma_tp = sum(tp[-period:])/period
        mean_dev = sum(abs(x-sma_tp) for x in tp[-period:])/period
        return (tp[-1]-sma_tp)/(0.015*mean_dev) if mean_dev > 0 else 0

    @staticmethod
    def dmi(highs, lows, closes, period: int = 14) -> Dict:
        adx = AdvancedIndicators.adx(highs, lows, closes, period)
        plus_dm, minus_dm, tr = [], [], []
        for i in range(1, len(closes)):
            up = highs[i]-highs[i-1]; down = lows[i-1]-lows[i]
            plus_dm.append(up if up > down and up > 0 else 0)
            minus_dm.append(down if down > up and down > 0 else 0)
            tr.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        tr_smooth = AdvancedIndicators.ema(tr[-period:], period)
        plus_di = 100*(AdvancedIndicators.ema(plus_dm[-period:], period)/tr_smooth) if tr_smooth > 0 else 0
        minus_di = 100*(AdvancedIndicators.ema(minus_dm[-period:], period)/tr_smooth) if tr_smooth > 0 else 0
        return {"adx": adx, "plus_di": plus_di, "minus_di": minus_di}

# ========================================================================
# ML ENSEMBLE - signal generation split from the min_signals threshold,
# since the 15-indicator computation itself doesn't depend on any of the
# parameters being swept (min_signals, trailing, hold days)
# ========================================================================

def compute_ml_features(data: Dict) -> Dict:
    closes, highs, lows, volumes = data['closes'], data['highs'], data['lows'], data['volumes']
    current = closes[-1]

    ema_9 = AdvancedIndicators.ema(closes, 9)
    ema_21 = AdvancedIndicators.ema(closes, 21)
    ema_50 = AdvancedIndicators.ema(closes, 50)

    signals, weights = [], []

    if current > ema_9 > ema_21 > ema_50:
        signals.append(1); weights.append(1.5)
    elif current > ema_50:
        signals.append(1); weights.append(1.0)
    else:
        signals.append(0); weights.append(1.0)

    macd = AdvancedIndicators.macd(closes)
    signals.append(1 if macd['bullish'] else 0); weights.append(1.5)

    rsi = AdvancedIndicators.rsi(closes, 14)
    if 30 < rsi < 70: signals.append(1 if rsi < 50 else 0.5)
    elif rsi < 30: signals.append(1)
    else: signals.append(0)
    weights.append(1.2)

    bb = AdvancedIndicators.bollinger(closes)
    if current < bb['lower']*1.02: signals.append(1)
    elif current > bb['upper']*0.98: signals.append(0)
    else: signals.append(0.5)
    weights.append(1.0)

    adx = AdvancedIndicators.adx(highs, lows, closes)
    signals.append(1 if adx > 25 else 0); weights.append(1.3)

    stoch = AdvancedIndicators.stochastic(closes, highs, lows)
    signals.append(1 if stoch < 30 else 0.3 if stoch < 50 else 0); weights.append(0.8)

    obv_values = AdvancedIndicators.obv(closes, volumes)
    if len(obv_values) >= 20:
        obv_ema = AdvancedIndicators.ema(obv_values, 10)
        signals.append(1 if obv_values[-1] > obv_ema else 0)
    else:
        signals.append(0)
    weights.append(1.0)

    vwap = AdvancedIndicators.vwap(highs, lows, closes, volumes)
    signals.append(1 if current > vwap else 0); weights.append(0.8)

    chop = AdvancedIndicators.chop(highs, lows, closes)
    signals.append(1 if chop < 40 else 0); weights.append(1.0)

    zscore = AdvancedIndicators.zscore(closes, 20)
    signals.append(1 if zscore < -1 else 0); weights.append(0.7)

    kc = AdvancedIndicators.keltner(highs, lows, closes)
    signals.append(1 if current < kc['lower']*1.01 else 0); weights.append(0.9)

    ichi = AdvancedIndicators.ichimoku(highs, lows, closes)
    signals.append(1 if current > ichi['tenkan'] and current > ichi['kijun'] else 0); weights.append(1.2)

    vortex = AdvancedIndicators.vortex(highs, lows, closes)
    signals.append(1 if vortex['vi_plus'] > vortex['vi_minus'] else 0); weights.append(0.9)

    cci = AdvancedIndicators.cci(closes, highs, lows)
    signals.append(1 if cci < -100 else 0); weights.append(0.7)

    dmi = AdvancedIndicators.dmi(highs, lows, closes)
    signals.append(1 if dmi['plus_di'] > dmi['minus_di'] and dmi['adx'] > 20 else 0); weights.append(1.1)

    weighted_sum = sum(s*w for s, w in zip(signals, weights))
    confidence = weighted_sum / sum(weights)
    signal_count = sum(1 for s in signals if s > 0.5)

    atr = AdvancedIndicators.atr(highs, lows, closes, 14)
    recent_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
    stop = min(current - atr*1.5, recent_low*0.98)
    target = current + atr*(3.0 if adx > 30 else 2.0)
    risk = current - stop
    reward = target - current
    rr_ratio = reward / risk if risk > 0 else 0

    return {"signal_count": signal_count, "confidence": confidence, "stop": stop,
            "target": target, "rr_ratio": rr_ratio}

# ========================================================================
# ROBUST VALIDATION
# ========================================================================

def fetch_history(symbol: str, interval: str, days_back: int, base_url: str = "https://api.binance.us") -> Dict:
    interval_minutes = {"1d": 1440, "3d": 4320, "1w": 10080}
    candles_per_day = 1440 // interval_minutes.get(interval, 1440)
    needed = max(1, days_back * candles_per_day)
    print(f"  Fetching ~{days_back}d ({needed} candles) of {interval} {symbol}...")
    all_data = {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
    end_time = None
    while len(all_data["closes"]) < needed:
        batch = AdvancedIndicators.get_klines(symbol, base_url, interval, limit=1000, end_time_ms=end_time)
        if not batch or not batch["timestamps"]:
            break
        for k in all_data:
            all_data[k] = batch[k] + all_data[k]
        end_time = batch["timestamps"][0] - 1
        time.sleep(0.2)
    return all_data


def precompute_features(klines: Dict, lookback: int = 100, label: str = "") -> List[Optional[Dict]]:
    total = len(klines["closes"])
    features: List[Optional[Dict]] = [None] * total
    report_every = max(1, (total - lookback) // 5)
    for i in range(lookback, total):
        window = {k: klines[k][i-lookback:i] for k in klines}
        features[i] = compute_ml_features(window)
        if label and (i - lookback) % report_every == 0:
            print(f"    [{label}] {int((i-lookback)/(max(1,total-lookback))*100)}%")
    return features


def simulate(klines: Dict, features: List[Optional[Dict]], min_signals: int,
             trailing_stop: bool, trailing_pct: float, max_hold_days: int,
             min_rr: float = 1.5, min_confidence: float = 0.5, lookback: int = 100) -> List[float]:
    closes, highs, lows = klines["closes"], klines["highs"], klines["lows"]
    total = len(closes)
    trades = []
    in_position = False
    entry_price = entry_i = stop_price = target_price = highest = trail = None

    for i in range(lookback, total):
        if not in_position:
            f = features[i]
            if (f['signal_count'] >= min_signals and f['confidence'] > min_confidence
                    and f['rr_ratio'] > min_rr):
                entry_price = closes[i]
                stop_price = f['stop']
                target_price = f['target']
                highest = entry_price
                trail = stop_price
                entry_i = i
                in_position = True
        else:
            if closes[i] > highest:
                highest = closes[i]
            if trailing_stop:
                candidate = highest * (1 - trailing_pct * 0.02)
                if candidate > trail:
                    trail = candidate
            current_stop = trail if trailing_stop else stop_price

            exit_price = None
            if lows[i] <= current_stop:
                exit_price = current_stop
            elif highs[i] >= target_price:
                exit_price = target_price
            elif (i - entry_i) > max_hold_days:
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
    return {"trades": len(trades), "win_rate": len(wins)/len(trades), "expectancy_pct": sum(trades)/len(trades)}


def run_robust_ml_validation(symbols_days, param_variants, n_folds: int = 4,
                              alpha: float = 0.05, min_trades_per_fold: int = 8,
                              min_pooled_trades: int = 25):
    """
    symbols_days: list of (symbol, interval, days_back)
    param_variants: list of dicts with min_signals/trailing_stop/trailing_pct/max_hold_days

    Fixes vs v4.0: realistic min_trades_per_fold (8, not 3), an additional
    floor on total pooled trades (25) before any conclusion is drawn at
    all, and a Bonferroni-corrected significance test instead of picking
    the max of an uncorrected score across ~800 combinations.
    """
    n_combos = len(symbols_days) * len(param_variants)
    bonferroni_alpha = alpha / n_combos
    normal = statistics.NormalDist()
    print(f"Testing {n_combos} total (symbol, params) combinations.")
    print(f"Bonferroni-corrected significance bar: p < {bonferroni_alpha:.6f}\n")

    passing = []

    for symbol, interval, days_back in symbols_days:
        print(f"\n{'='*70}\n{symbol} {interval}\n{'='*70}")
        klines = fetch_history(symbol, interval, days_back)
        total = len(klines["closes"])
        if total < 100 * (n_folds + 1):
            print(f"  Not enough data ({total} candles) for {n_folds} blocks - skipping.")
            continue

        block_size = total // n_folds
        blocks = []
        for f in range(n_folds):
            start = f * block_size
            end = total if f == n_folds - 1 else (f + 1) * block_size
            lookback_start = max(0, start - 100)
            blocks.append({k: klines[k][lookback_start:end] for k in klines})

        print("  Precomputing 15-indicator features per block...")
        block_features = [precompute_features(b, label=f"block {i+1}/{n_folds}") for i, b in enumerate(blocks)]

        for params in param_variants:
            pooled_trades = []
            blocks_positive = 0
            blocks_tested = 0
            for block, feats in zip(blocks, block_features):
                trades = simulate(block, feats, params['min_signals'], params['trailing_stop'],
                                   params['trailing_pct'], params['max_hold_days'])
                if len(trades) < min_trades_per_fold:
                    continue
                blocks_tested += 1
                s = summarize(trades)
                if s['expectancy_pct'] > 0:
                    blocks_positive += 1
                pooled_trades.extend(trades)

            label = (f"signals>={params['min_signals']} trail={params['trailing_pct']:.1f}% "
                     f"hold<={params['max_hold_days']}d trail_stop={params['trailing_stop']}")

            if blocks_tested < max(2, n_folds - 1) or len(pooled_trades) < min_pooled_trades:
                print(f"  [{label}] {len(pooled_trades)} pooled trades, {blocks_tested}/{n_folds} usable "
                      f"blocks - INSUFFICIENT DATA to evaluate, skipping")
                continue

            mean_ret = sum(pooled_trades) / len(pooled_trades)
            stdev_ret = statistics.stdev(pooled_trades) if len(pooled_trades) > 1 else 0
            if stdev_ret == 0:
                continue
            se = stdev_ret / (len(pooled_trades) ** 0.5)
            z = mean_ret / se
            p_value = 2 * (1 - normal.cdf(abs(z)))
            consistency_ok = blocks_positive >= max(2, int(0.75 * blocks_tested))
            significant = mean_ret > 0 and p_value < bonferroni_alpha

            status = "PASS" if (consistency_ok and significant) else "fail"
            print(f"  [{label}] {len(pooled_trades)} trades, {blocks_positive}/{blocks_tested} blocks "
                  f"positive, mean/trade={mean_ret*100:.3f}%, p={p_value:.5f} -> {status}")

            if consistency_ok and significant:
                passing.append({"symbol": symbol, "interval": interval, **params,
                                 "pooled_trades": len(pooled_trades), "blocks_positive": blocks_positive,
                                 "blocks_tested": blocks_tested, "mean_return_pct": mean_ret, "p_value": p_value})

    print("\n" + "="*70)
    if not passing:
        print("RESULT: Nothing survived realistic trade-count minimums, multi-block")
        print("consistency, AND Bonferroni-corrected significance testing.")
        print()
        print("Given the earlier run's 'winner' had only 14 total trades, it's quite")
        print("plausible that daily-candle crypto data over the available history")
        print("just doesn't produce enough trade volume for this indicator-count-vote")
        print("approach to be validated at all, in either direction. That's a real,")
        print("useful answer: it means you can't currently DISPROVE the strategy is")
        print("worthless, but you also can't claim it's proven - the honest stance is")
        print("'unknown, insufficient data,' not 'ready for live trading.'")
        print("="*70)
        return []

    passing.sort(key=lambda r: r["p_value"])
    print(f"RESULT: {len(passing)} combination(s) passed:")
    for r in passing:
        print(f"  {r['symbol']} {r['interval']} signals>={r['min_signals']} trail={r['trailing_pct']:.1f}% "
              f"hold<={r['max_hold_days']}d | {r['pooled_trades']} trades | "
              f"{r['blocks_positive']}/{r['blocks_tested']} blocks | p={r['p_value']:.6f}")
    print("="*70)
    return passing


if __name__ == "__main__":
    # Small, pre-specified set (not an 800-wide sweep). Bonferroni above
    # is sized to exactly len(symbols_days) * len(param_variants).
    param_variants = [
        {"min_signals": 7, "trailing_stop": False, "trailing_pct": 0.5, "max_hold_days": 30},
        {"min_signals": 8, "trailing_stop": False, "trailing_pct": 0.5, "max_hold_days": 30},
        {"min_signals": 8, "trailing_stop": True, "trailing_pct": 0.5, "max_hold_days": 45},
        {"min_signals": 9, "trailing_stop": True, "trailing_pct": 0.7, "max_hold_days": 45},
    ]

    # 1d candles need a LOT of calendar time to produce enough trades.
    # 730 days (v4.0's setting) produced only 14 trades for the "winner" -
    # using more history here to give the significance test a fair shot,
    # while being upfront that even this may not be enough.
    symbols_days = [
        ("BTCUSDT", "1d", 1500),
        ("ETHUSDT", "1d", 1500),
        ("SOLUSDT", "1d", 1500),
        ("LINKUSDT", "1d", 1500),
        ("AVAXUSDT", "1d", 1500),
    ]

    run_robust_ml_validation(symbols_days, param_variants, n_folds=4)
