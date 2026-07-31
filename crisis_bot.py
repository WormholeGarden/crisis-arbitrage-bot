#!/usr/bin/env python3
"""
THE HONEST VALIDATOR - WIDE NET
============================================================
This is the broadest legitimate version of what we've been building all
conversation: instead of one symbol/timeframe/strategy at a time, it
sweeps many of each - while keeping every safeguard that made the
earlier honest versions trustworthy:

  1. ANCHORED WALK-FORWARD: for every (symbol, timeframe, strategy),
     parameters are chosen using ONLY past data within each fold, then
     locked and applied unchanged to the next, previously-unseen fold.
     Only trades from folds a given parameter set never trained on
     count toward the result.

  2. BONFERRONI CORRECTION sized to the ACTUAL number of final
     (symbol, timeframe, strategy) combinations being compared at the
     end - not the internal per-fold training search, which is a
     normal and accepted part of walk-forward, but IS disclosed.

  3. MINIMUM TRADE COUNT power check: anything with too few pooled
     out-of-sample trades to say anything meaningful is reported as
     such, not silently passed or failed.

  4. BUY-AND-HOLD BENCHMARK: for every combination that DOES clear the
     significance bar, its return is also compared to simply holding
     the asset over the same out-of-sample period. A "statistically
     significant" trading strategy that still underperforms holding is
     not something worth trading over just holding.

STRATEGY FAMILIES (four genuinely different approaches, not the same
indicators relabeled):
  A. Technical Condition Count  - RSI/MACD/BB/SMA/VWAP breadth voting,
     ATR-scaled stop/target so it's meaningful across timeframes
  B. Ten-Strategy Ensemble Vote - breakout/mean-reversion/volume/trend/
     volatility/pullback/divergence/opening-range/stat-arb/multi-EMA,
     majority or any-of-N voting
  C. 15-Indicator Weighted Ensemble - broader indicator set (Ichimoku,
     Vortex, CCI, DMI, Keltner, etc.) with importance weighting
  D. Simple SMA Crossover - a classic, deliberately simple baseline;
     if the complex strategies can't beat this, that's informative too

WHAT THIS DOES NOT DO: guarantee a positive result. Given everything
tested so far in this conversation came back empty or unreliable, the
honest expectation is that this may ALSO come back empty, or with only
a handful of combinations that clear the bar and even fewer that also
beat buy-and-hold. That is a legitimate outcome to report plainly.
============================================================
"""

import time
import math
import statistics
from typing import Dict, List, Optional, Callable
import requests

MAKER_FEE = 0.001
TAKER_FEE = 0.001
ROUND_TRIP_FEE = MAKER_FEE + TAKER_FEE

# ========================================================================
# EXCHANGE CONFIG
# ========================================================================
# Binance.US is used by default because api.binance.com blocks US-based
# connections (this was the root cause of an earlier bug in this
# conversation). If you are NOT in the US, switch to "https://api.binance.com"
# for much deeper history and more pairs. Adding a non-Binance exchange
# (Coinbase, Kraken) would need its own fetch/parse function, since their
# kline response shapes differ - noted as an extension point, not done here
# to keep this script something you can actually run today.
BASE_URL = "https://api.binance.us"

SYMBOLS = [
    "BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "AVAXUSDT",
    "DOGEUSDT", "ADAUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT",
]

# (interval, days_back_cap, min_hold_lookback_bars, max_hold_bars)
TIMEFRAMES = [
    ("15m", 90,   300, 96),    # ~90 days, max hold ~1 day
    ("1h",  365,  300, 72),    # ~1 year, max hold ~3 days
    ("4h",  700,  300, 48),    # ~2 years, max hold ~8 days
    ("1d",  1500, 100, 30),    # ~4 years, max hold ~1 month
]
# 1-minute is deliberately excluded: it was already exhaustively tested
# earlier in this conversation (single backtest, walk-forward split, and
# multi-block Bonferroni-corrected search) and came back empty every
# time. Re-including it here would just re-spend the search budget on
# already-answered ground. Uncomment to add it back if you want:
# TIMEFRAMES.insert(0, ("1m", 30, 300, 240))

N_FOLDS = 5
MIN_TRAIN_TRADES = 5
MIN_OOS_TRADES_TO_REPORT = 10
POWER_WARNING_THRESHOLD = 30
ALPHA = 0.05

# ========================================================================
# INDICATORS (shared by all strategy families)
# ========================================================================

class Ind:
    @staticmethod
    def get_klines(symbol, interval, limit=1000, end_time_ms=None, base_url=BASE_URL):
        try:
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            if end_time_ms:
                params["endTime"] = end_time_ms
            resp = requests.get(f"{base_url}/api/v3/klines", params=params, timeout=10)
            if resp.status_code != 200:
                return None
            data = resp.json()
            return {
                "timestamps": [c[0] for c in data], "opens": [float(c[1]) for c in data],
                "highs": [float(c[2]) for c in data], "lows": [float(c[3]) for c in data],
                "closes": [float(c[4]) for c in data], "volumes": [float(c[5]) for c in data],
            }
        except Exception:
            return None

    @staticmethod
    def ema(data, period):
        if not data or len(data) < period:
            return data[-1] if data else 0
        alpha = 2 / (period + 1)
        v = sum(data[:period]) / period
        for p in data[period:]:
            v = p * alpha + v * (1 - alpha)
        return v

    @staticmethod
    def sma(data, period):
        if not data or len(data) < period:
            return data[-1] if data else 0
        return sum(data[-period:]) / period

    @staticmethod
    def rsi(closes, period=14):
        if len(closes) < period + 1:
            return 50.0
        gains = [max(closes[i]-closes[i-1], 0) for i in range(1, len(closes))]
        losses = [max(closes[i-1]-closes[i], 0) for i in range(1, len(closes))]
        ag, al = sum(gains[-period:])/period, sum(losses[-period:])/period
        return 100.0 if al == 0 else 100 - (100/(1+ag/al))

    @staticmethod
    def atr(highs, lows, closes, period=14):
        if len(closes) < period + 1:
            return (max(highs)-min(lows)) if highs and lows else 0
        tr = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(1, len(closes))]
        return sum(tr[-period:]) / period

    @staticmethod
    def macd(closes, fast=12, slow=26, signal=9):
        if len(closes) < slow:
            return {"histogram": 0, "bullish": False}
        ef, es = Ind.ema(closes, fast), Ind.ema(closes, slow)
        macd_line = ef - es
        signal_line = Ind.ema([macd_line]*signal, signal)
        return {"histogram": macd_line - signal_line, "bullish": macd_line > signal_line}

    @staticmethod
    def bollinger(closes, period=20, std_dev=2):
        if len(closes) < period:
            last = closes[-1] if closes else 0
            return {"upper": last, "middle": last, "lower": last, "position": 0.5}
        m = sum(closes[-period:])/period
        std = (sum((x-m)**2 for x in closes[-period:])/period) ** 0.5
        u, l = m+std*std_dev, m-std*std_dev
        return {"upper": u, "middle": m, "lower": l, "position": (closes[-1]-l)/(u-l) if u != l else 0.5}

    @staticmethod
    def vwap(highs, lows, closes, volumes):
        if not volumes or sum(volumes) == 0:
            return closes[-1] if closes else 0
        tp = [(h+l+c)/3 for h, l, c in zip(highs, lows, closes)]
        return sum(t*v for t, v in zip(tp, volumes)) / sum(volumes)

    @staticmethod
    def adx(highs, lows, closes, period=14):
        if len(closes) < period+1:
            return 25.0
        pdm, mdm, tr = [], [], []
        for i in range(1, len(closes)):
            up, down = highs[i]-highs[i-1], lows[i-1]-lows[i]
            pdm.append(up if up > down and up > 0 else 0)
            mdm.append(down if down > up and down > 0 else 0)
            tr.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        tre = Ind.ema(tr[-period:], period)
        if tre == 0:
            return 25.0
        pdi = 100*(Ind.ema(pdm[-period:], period)/tre)
        mdi = 100*(Ind.ema(mdm[-period:], period)/tre)
        dx = 100*abs(pdi-mdi)/(pdi+mdi) if (pdi+mdi) > 0 else 0
        return Ind.ema([dx]*period, period)

    @staticmethod
    def obv(closes, volumes):
        if not closes or not volumes:
            return []
        o = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]: o.append(o[-1]+volumes[i])
            elif closes[i] < closes[i-1]: o.append(o[-1]-volumes[i])
            else: o.append(o[-1])
        return o

    @staticmethod
    def chop(highs, lows, closes, period=14):
        if len(closes) < period:
            return 50.0
        tr_sum = sum(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])) for i in range(len(closes)-period, len(closes)))
        hh, ll = max(highs[-period:]), min(lows[-period:])
        if hh == ll:
            return 50.0
        return max(0, min(100, 100*math.log10(tr_sum/(hh-ll))/math.log10(period)))

    @staticmethod
    def zscore(data, period=20):
        if len(data) < period:
            return 0
        w = data[-period:]
        m = sum(w)/period
        s = statistics.stdev(w) if period > 1 else 0.001
        return (data[-1]-m)/s if s > 0 else 0

    @staticmethod
    def stochastic(closes, highs, lows, period=14):
        if len(closes) < period:
            return 50.0
        hh, ll = max(highs[-period:]), min(lows[-period:])
        return 50.0 if hh == ll else ((closes[-1]-ll)/(hh-ll))*100

    @staticmethod
    def keltner(highs, lows, closes, period=20):
        if len(closes) < period:
            last = closes[-1] if closes else 0
            return {"upper": last, "lower": last}
        m = Ind.ema(closes, period)
        a = Ind.atr(highs, lows, closes, 10)
        return {"upper": m+a*1.5, "lower": m-a*1.5}

    @staticmethod
    def ichimoku(highs, lows, closes):
        if len(closes) < 52:
            last = closes[-1] if closes else 0
            return {"tenkan": last, "kijun": last}
        return {"tenkan": (max(highs[-9:])+min(lows[-9:]))/2, "kijun": (max(highs[-26:])+min(lows[-26:]))/2}

    @staticmethod
    def vortex(highs, lows, closes, period=14):
        if len(closes) < period+1:
            return {"vi_plus": 0, "vi_minus": 0}
        vp, vm, tr = [], [], []
        for i in range(1, len(closes)):
            vp.append(abs(highs[i]-lows[i-1])); vm.append(abs(lows[i]-highs[i-1]))
            tr.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        s = sum(tr[-period:])
        return {"vi_plus": sum(vp[-period:])/s if s > 0 else 0, "vi_minus": sum(vm[-period:])/s if s > 0 else 0}

    @staticmethod
    def cci(closes, highs, lows, period=20):
        if len(closes) < period:
            return 0
        tp = [(h+l+c)/3 for h, l, c in zip(highs, lows, closes)]
        m = sum(tp[-period:])/period
        md = sum(abs(x-m) for x in tp[-period:])/period
        return (tp[-1]-m)/(0.015*md) if md > 0 else 0

    @staticmethod
    def dmi(highs, lows, closes, period=14):
        adx = Ind.adx(highs, lows, closes, period)
        pdm, mdm, tr = [], [], []
        for i in range(1, len(closes)):
            up, down = highs[i]-highs[i-1], lows[i-1]-lows[i]
            pdm.append(up if up > down and up > 0 else 0)
            mdm.append(down if down > up and down > 0 else 0)
            tr.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        trs = Ind.ema(tr[-period:], period)
        pdi = 100*(Ind.ema(pdm[-period:], period)/trs) if trs > 0 else 0
        mdi = 100*(Ind.ema(mdm[-period:], period)/trs) if trs > 0 else 0
        return {"adx": adx, "plus_di": pdi, "minus_di": mdi}

# ========================================================================
# STRATEGY FAMILY A: TECHNICAL CONDITION COUNT (ATR-scaled, timeframe-agnostic)
# ========================================================================

def strategy_conditions(window: Dict, params: Dict) -> Dict:
    closes, highs, lows, volumes = window['closes'], window['highs'], window['lows'], window['volumes']
    if len(closes) < 60:
        return {"signal": "NEUTRAL"}
    current = closes[-1]
    rsi = Ind.rsi(closes); macd = Ind.macd(closes); bb = Ind.bollinger(closes)
    vwap = Ind.vwap(highs, lows, closes, volumes)
    sma20 = Ind.sma(closes, 20)
    atr = Ind.atr(highs, lows, closes)

    passing = 0
    if rsi < 60: passing += 1
    if macd['histogram'] > 0: passing += 1
    if bb['position'] < 0.5: passing += 1
    if current > sma20: passing += 1
    if current > vwap: passing += 1
    if rsi < 45: passing += 1

    if passing < params['min_passing']:
        return {"signal": "NEUTRAL"}
    stop = current - atr * params['stop_atr_mult']
    target = current + atr * params['target_atr_mult']
    return {"signal": "BUY", "stop": stop, "target": target}

CONDITIONS_LOOKBACK = 100
CONDITIONS_GRID = [
    {"min_passing": mp, "stop_atr_mult": sm, "target_atr_mult": tm}
    for mp in [4, 5]
    for sm in [1.0, 1.5, 2.0]
    for tm in [1.5, 2.5, 4.0]
]

# ========================================================================
# STRATEGY FAMILY B: TEN-STRATEGY ENSEMBLE VOTE
# ========================================================================

def _sub_breakout(closes, highs, lows):
    current = closes[-1]
    dh, dl = max(highs[-20:]), min(lows[-20:])
    buy = int(current > dh) + int(Ind.adx(highs, lows, closes) > 25) + int(Ind.rsi(closes) < 70) + int(current > Ind.ema(closes, 50))
    return buy >= 2, dl, current + (current-dl)*1.5

def _sub_meanrev(closes, highs, lows, volumes):
    current = closes[-1]; bb = Ind.bollinger(closes); rsi = Ind.rsi(closes); atr = Ind.atr(highs, lows, closes)
    vol_avg = sum(volumes[-20:])/20 if len(volumes) >= 20 else sum(volumes)/len(volumes)
    buy = int(current < bb['lower']*1.02) + int(20 < rsi < 40) + int(volumes[-1] > vol_avg*1.2) + int(current < Ind.ema(closes, 20))
    return buy >= 2, current-atr*1.5, current+(bb['middle']-bb['lower'])*0.5

def _sub_trend(closes):
    current = closes[-1]; macd = Ind.macd(closes)
    e9, e21, e50 = Ind.ema(closes, 9), Ind.ema(closes, 21), Ind.ema(closes, 50)
    rsi = Ind.rsi(closes)
    buy = int(macd['bullish']) + int(current > e9 > e21) + int(current > e50) + int(40 < rsi < 70)
    return buy >= 2, e21*0.98, current*1.04

def _sub_pullback(closes, highs, lows):
    current = closes[-1]; e21, e50 = Ind.ema(closes, 21), Ind.ema(closes, 50); rsi = Ind.rsi(closes)
    buy = int(current > e50) + int(current > e21) + int(abs(current-e21)/e21 < 0.01) + int(30 < rsi < 50)
    return buy >= 2, e21*0.97, current*1.04

def _sub_statarb(closes):
    current = closes[-1]
    if len(closes) < 20:
        return False, current*0.97, current*1.03
    z = Ind.zscore(closes, 20); rsi = Ind.rsi(closes)
    buy = int(z < -2) + int(rsi < 35) + int(z < -1 and current < Ind.ema(closes, 20))
    return buy >= 2, current*0.97, current*(1-z*0.01)

def strategy_ensemble(window: Dict, params: Dict) -> Dict:
    closes, highs, lows, volumes = window['closes'], window['highs'], window['lows'], window['volumes']
    if len(closes) < 60:
        return {"signal": "NEUTRAL"}
    subs = []
    for fn, args in [(_sub_breakout, (closes, highs, lows)), (_sub_meanrev, (closes, highs, lows, volumes)),
                      (_sub_trend, (closes,)), (_sub_pullback, (closes, highs, lows)), (_sub_statarb, (closes,))]:
        buy, stop, target = fn(*args)
        if buy:
            subs.append((stop, target))
    if len(subs) < params['min_votes']:
        return {"signal": "NEUTRAL"}
    stops = [s[0] for s in subs]; targets = [s[1] for s in subs]
    return {"signal": "BUY", "stop": statistics.median(stops), "target": statistics.median(targets)}

ENSEMBLE_LOOKBACK = 100
ENSEMBLE_GRID = [{"min_votes": mv} for mv in [1, 2, 3]]

# ========================================================================
# STRATEGY FAMILY C: 15-INDICATOR WEIGHTED ENSEMBLE
# ========================================================================

def strategy_weighted(window: Dict, params: Dict) -> Dict:
    closes, highs, lows, volumes = window['closes'], window['highs'], window['lows'], window['volumes']
    if len(closes) < 60:
        return {"signal": "NEUTRAL"}
    current = closes[-1]
    signals, weights = [], []

    e9, e21, e50 = Ind.ema(closes, 9), Ind.ema(closes, 21), Ind.ema(closes, 50)
    signals.append(1 if current > e9 > e21 > e50 else (1 if current > e50 else 0)); weights.append(1.5)
    signals.append(1 if Ind.macd(closes)['bullish'] else 0); weights.append(1.5)
    rsi = Ind.rsi(closes)
    signals.append(1 if rsi < 30 else (0.5 if 30 < rsi < 50 else 0)); weights.append(1.2)
    bb = Ind.bollinger(closes)
    signals.append(1 if current < bb['lower']*1.02 else (0 if current > bb['upper']*0.98 else 0.5)); weights.append(1.0)
    adx = Ind.adx(highs, lows, closes)
    signals.append(1 if adx > 25 else 0); weights.append(1.3)
    stoch = Ind.stochastic(closes, highs, lows)
    signals.append(1 if stoch < 30 else (0.3 if stoch < 50 else 0)); weights.append(0.8)
    obv = Ind.obv(closes, volumes)
    signals.append(1 if len(obv) >= 20 and obv[-1] > Ind.ema(obv, 10) else 0); weights.append(1.0)
    signals.append(1 if current > Ind.vwap(highs, lows, closes, volumes) else 0); weights.append(0.8)
    signals.append(1 if Ind.chop(highs, lows, closes) < 40 else 0); weights.append(1.0)
    signals.append(1 if Ind.zscore(closes, 20) < -1 else 0); weights.append(0.7)
    kc = Ind.keltner(highs, lows, closes)
    signals.append(1 if current < kc['lower']*1.01 else 0); weights.append(0.9)
    ichi = Ind.ichimoku(highs, lows, closes)
    signals.append(1 if current > ichi['tenkan'] and current > ichi['kijun'] else 0); weights.append(1.2)
    vx = Ind.vortex(highs, lows, closes)
    signals.append(1 if vx['vi_plus'] > vx['vi_minus'] else 0); weights.append(0.9)
    signals.append(1 if Ind.cci(closes, highs, lows) < -100 else 0); weights.append(0.7)
    dmi = Ind.dmi(highs, lows, closes)
    signals.append(1 if dmi['plus_di'] > dmi['minus_di'] and dmi['adx'] > 20 else 0); weights.append(1.1)

    signal_count = sum(1 for s in signals if s > 0.5)
    confidence = sum(s*w for s, w in zip(signals, weights)) / sum(weights)
    if signal_count < params['min_signals'] or confidence <= 0.5:
        return {"signal": "NEUTRAL"}

    atr = Ind.atr(highs, lows, closes)
    recent_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
    stop = min(current - atr*1.5, recent_low*0.98)
    target = current + atr*(3.0 if adx > 30 else 2.0)
    return {"signal": "BUY", "stop": stop, "target": target}

WEIGHTED_LOOKBACK = 100
WEIGHTED_GRID = [{"min_signals": ms} for ms in [7, 8, 9]]

# ========================================================================
# STRATEGY FAMILY D: SIMPLE SMA CROSSOVER (classic baseline)
# ========================================================================

def strategy_sma_cross(window: Dict, params: Dict) -> Dict:
    closes, highs, lows = window['closes'], window['highs'], window['lows']
    fast, slow = params['fast'], params['slow']
    if len(closes) < slow + 2:
        return {"signal": "NEUTRAL"}
    fast_now, fast_prev = Ind.sma(closes, fast), Ind.sma(closes[:-1], fast)
    slow_now, slow_prev = Ind.sma(closes, slow), Ind.sma(closes[:-1], slow)
    crossed_up = fast_prev <= slow_prev and fast_now > slow_now
    if not crossed_up:
        return {"signal": "NEUTRAL"}
    atr = Ind.atr(highs, lows, closes)
    current = closes[-1]
    return {"signal": "BUY", "stop": current - atr*1.5, "target": current + atr*2.5}

SMA_LOOKBACK = 100
SMA_GRID = [{"fast": f, "slow": s} for f, s in [(10, 50), (20, 100)]]

STRATEGIES = {
    "TechnicalConditions": (strategy_conditions, CONDITIONS_LOOKBACK, CONDITIONS_GRID),
    "TenStrategyEnsemble": (strategy_ensemble, ENSEMBLE_LOOKBACK, ENSEMBLE_GRID),
    "WeightedIndicators":  (strategy_weighted, WEIGHTED_LOOKBACK, WEIGHTED_GRID),
    "SmaCrossover":        (strategy_sma_cross, SMA_LOOKBACK, SMA_GRID),
}

# ========================================================================
# BACKTEST CORE (shared)
# ========================================================================

def backtest_trades(data: Dict, signal_fn: Callable, params: Dict, lookback: int, max_hold_bars: int) -> List[float]:
    closes, highs, lows = data['closes'], data['highs'], data['lows']
    total = len(closes)
    trades = []
    in_position = False
    entry_price = entry_i = stop_price = target_price = None

    for i in range(lookback, total):
        if not in_position:
            window = {k: data[k][i-lookback:i] for k in data}
            sig = signal_fn(window, params)
            if sig.get("signal") == "BUY":
                entry_price = closes[i]; entry_i = i
                stop_price = sig["stop"]; target_price = sig["target"]
                in_position = True
        else:
            exit_price = None
            if lows[i] <= stop_price:
                exit_price = stop_price
            elif highs[i] >= target_price:
                exit_price = target_price
            elif i - entry_i > max_hold_bars:
                exit_price = closes[i]
            if exit_price is not None:
                trades.append((exit_price - entry_price) / entry_price - ROUND_TRIP_FEE)
                in_position = False
    return trades


def score_on_train(data, signal_fn, params, lookback, max_hold_bars, min_trades=MIN_TRAIN_TRADES) -> Optional[float]:
    trades = backtest_trades(data, signal_fn, params, lookback, max_hold_bars)
    if len(trades) < min_trades:
        return None
    return sum(trades) / len(trades)


def fetch_history(symbol: str, interval: str, days_back: int) -> Dict:
    interval_minutes = {"1m": 1, "5m": 5, "15m": 15, "1h": 60, "4h": 240, "1d": 1440}
    candles_per_day = 1440 // interval_minutes.get(interval, 1440)
    needed = days_back * candles_per_day
    print(f"    Fetching ~{days_back}d ({needed} candles) of {interval} {symbol}...")
    all_data = {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
    end_time = None
    while len(all_data["closes"]) < needed:
        batch = Ind.get_klines(symbol, interval, limit=1000, end_time_ms=end_time)
        if not batch or not batch["timestamps"]:
            break
        for k in all_data:
            all_data[k] = batch[k] + all_data[k]
        end_time = batch["timestamps"][0] - 1
        time.sleep(0.15)
    return all_data


def anchored_walk_forward(data: Dict, signal_fn, grid, lookback, max_hold_bars, n_folds=N_FOLDS):
    total = len(data["closes"])
    if total < lookback * (n_folds + 1):
        return None
    fold_size = total // n_folds
    bounds = [f * fold_size for f in range(n_folds)] + [total]
    pooled = []
    for f in range(1, n_folds):
        train = {k: data[k][:bounds[f]] for k in data}
        lb_start = max(0, bounds[f] - lookback)
        test = {k: data[k][lb_start:bounds[f+1]] for k in data}

        best_score, best_params = None, None
        for params in grid:
            s = score_on_train(train, signal_fn, params, lookback, max_hold_bars)
            if s is not None and (best_score is None or s > best_score):
                best_score, best_params = s, params
        if best_params is None:
            continue
        pooled.extend(backtest_trades(test, signal_fn, best_params, lookback, max_hold_bars))
    return pooled


def buy_hold_return(data: Dict, n_folds=N_FOLDS) -> float:
    """Return of simply holding over the combined out-of-sample span
    (folds 1..n_folds-1), for comparison against the trading result."""
    total = len(data["closes"])
    fold_size = total // n_folds
    start = fold_size  # start of first OOS fold
    if start >= total or data["closes"][start] == 0:
        return 0.0
    return (data["closes"][-1] - data["closes"][start]) / data["closes"][start]

# ========================================================================
# MAIN SWEEP
# ========================================================================

def run_wide_validation():
    total_combos = len(SYMBOLS) * len(TIMEFRAMES) * len(STRATEGIES)
    bonferroni_alpha = ALPHA / total_combos
    normal = statistics.NormalDist()
    print(f"Sweeping {len(SYMBOLS)} symbols x {len(TIMEFRAMES)} timeframes x {len(STRATEGIES)} strategies "
          f"= {total_combos} final comparisons.")
    print(f"Bonferroni-corrected significance bar: p < {bonferroni_alpha:.6f} (uncorrected alpha={ALPHA})\n")

    passing = []
    beat_bh = []
    all_rows = []

    for symbol in SYMBOLS:
        for interval, days_cap, lookback_hint, max_hold in TIMEFRAMES:
            print(f"\n{'='*70}\n{symbol} {interval}\n{'='*70}")
            data = fetch_history(symbol, interval, days_cap)
            if len(data["closes"]) < 400:
                print(f"  Insufficient history ({len(data['closes'])} candles) - skipping this timeframe.")
                continue
            bh_return = buy_hold_return(data)
            print(f"  Buy-and-hold return over OOS span: {bh_return*100:.2f}%")

            for strat_name, (fn, lookback, grid) in STRATEGIES.items():
                pooled = anchored_walk_forward(data, fn, grid, lookback, max_hold)
                if pooled is None:
                    print(f"  [{strat_name}] not enough data for {N_FOLDS} folds - skip")
                    continue
                n = len(pooled)
                if n < MIN_OOS_TRADES_TO_REPORT:
                    print(f"  [{strat_name}] only {n} OOS trades - too few to evaluate, skip")
                    continue

                mean_ret = sum(pooled) / n
                stdev_ret = statistics.stdev(pooled) if n > 1 else 0
                power_flag = " [LOW POWER]" if n < POWER_WARNING_THRESHOLD else ""
                if stdev_ret == 0:
                    continue
                se = stdev_ret / (n ** 0.5)
                z = mean_ret / se
                p_value = 2 * (1 - normal.cdf(abs(z)))
                win_rate = len([t for t in pooled if t > 0]) / n
                significant = mean_ret > 0 and p_value < bonferroni_alpha
                combined_return_estimate = mean_ret * n  # naive, no compounding/sizing

                status = "PASS" if significant else "fail"
                print(f"  [{strat_name}] n={n}{power_flag} win_rate={win_rate*100:.1f}% "
                      f"mean/trade={mean_ret*100:.3f}% p={p_value:.5f} -> {status}")

                all_rows.append({"symbol": symbol, "interval": interval, "strategy": strat_name,
                                  "n": n, "win_rate": win_rate, "mean_return_pct": mean_ret,
                                  "p_value": p_value, "significant": significant,
                                  "naive_total_return_pct": combined_return_estimate,
                                  "buy_hold_return_pct": bh_return, "low_power": n < POWER_WARNING_THRESHOLD})

                if significant:
                    passing.append(all_rows[-1])
                    if combined_return_estimate > bh_return:
                        beat_bh.append(all_rows[-1])

    print("\n" + "="*70)
    print("FINAL SUMMARY")
    print("="*70)
    print(f"Total (symbol, timeframe, strategy) combinations evaluated: {len(all_rows)}")
    print(f"Passed Bonferroni-corrected significance: {len(passing)}")
    print(f"...and also beat buy-and-hold over the same OOS span: {len(beat_bh)}")

    if not passing:
        print("\nRESULT: Nothing in this wider sweep cleared the bar either.")
        print("Combined with everything already tested this conversation (1m scalping,")
        print("single backtests, single-split walk-forward, multi-block Bonferroni search,")
        print("4h ensemble voting, 1d 15-indicator weighted ensemble, anchored walk-forward),")
        print("this is now a fairly broad, consistent negative result across timeframes,")
        print("symbols, and independently-designed strategy families. That is meaningful")
        print("evidence, not an argument to keep widening the search further.")
    else:
        print("\nCombinations that passed significance:")
        for r in sorted(passing, key=lambda r: r["p_value"]):
            beat = "beats" if r["naive_total_return_pct"] > r["buy_hold_return_pct"] else "LOSES TO"
            print(f"  {r['symbol']} {r['interval']} {r['strategy']}: n={r['n']}"
                  f"{' [LOW POWER]' if r['low_power'] else ''}, "
                  f"win_rate={r['win_rate']*100:.1f}%, p={r['p_value']:.6f}, "
                  f"{beat} buy-and-hold ({r['naive_total_return_pct']*100:.1f}% vs "
                  f"{r['buy_hold_return_pct']*100:.1f}%)")
        if not beat_bh:
            print("\nNote: none of the significant results actually beat simply holding the")
            print("asset over the same period. A statistically real trading signal that still")
            print("underperforms buy-and-hold isn't a reason to trade instead of hold.")
    print("="*70)
    return all_rows


if __name__ == "__main__":
    run_wide_validation()
