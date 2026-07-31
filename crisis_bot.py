#!/usr/bin/env python3
"""
WIDE-NET HONEST VALIDATOR
============================================================
The widest legitimate search we can run without repeating the mistake
from every prior "discovery" in this thread: testing many things
without correcting for how many things were tested, or confirming on
data the search already saw.

SCOPE OF THE SEARCH:
  - 12 symbols (BTC, ETH, SOL, LINK, AVAX, BNB, ADA, DOGE, MATIC, DOT,
    LTC, XRP - all vs USDT)
  - 3 timeframes (1h, 4h, 1d)
  - 2 exchange endpoints per symbol (api.binance.us and api.binance.com),
    using whichever returns more historical depth for that symbol -
    this is public market data, no account/API key involved
  - = up to 36 (symbol, timeframe) combinations

METHOD (same discipline as the last honest validator, just run wider):
  - ANCHORED WALK-FORWARD per (symbol, timeframe): for each fold,
    strategy parameters are selected using ONLY data strictly before
    that fold, then locked and applied unchanged to the fold the
    selection process never saw. Only those trades count as
    out-of-sample.
  - Bonferroni correction sized to the ACTUAL number of (symbol,
    timeframe) combinations tested here (up to 36) - not the 800-1280
    combinations tested in the earlier "Golden Ticket" scripts.
  - Every result reports its pooled out-of-sample trade count
    explicitly. Under ~30 trades, ANY p-value is flagged as low-power
    and not to be trusted at face value, regardless of what it says.

This is a genuinely wider search than anything run so far in this
thread, and it can still legitimately return nothing. If it does,
that is the most informative possible outcome of this whole
exercise: an unusually thorough, correctly-controlled search across
symbols, timeframes, and available history found no exploitable edge
in these technical-indicator strategies.

No API key, no order placement, no live trading anywhere in this file.
============================================================
"""

import time
import math
import statistics
from typing import Dict, List, Optional
import requests

MAKER_FEE = 0.001
TAKER_FEE = 0.001
ROUND_TRIP_FEE = MAKER_FEE + TAKER_FEE

EXCHANGE_ENDPOINTS = ["https://api.binance.us", "https://api.binance.com"]

SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "AVAXUSDT", "BNBUSDT",
           "ADAUSDT", "DOGEUSDT", "MATICUSDT", "DOTUSDT", "LTCUSDT", "XRPUSDT"]

# Per-timeframe config: how many candles/day, how far back to try fetching,
# and a hold-time grid expressed in CANDLES (not days) sized sensibly for
# that timeframe.
TIMEFRAME_CONFIG = {
    "1h": {"candles_per_day": 24, "days_back": 400, "lookback": 150, "hold_options": [24, 48, 96]},
    "4h": {"candles_per_day": 6, "days_back": 700, "lookback": 150, "hold_options": [12, 24, 48]},
    "1d": {"candles_per_day": 1, "days_back": 1500, "lookback": 100, "hold_options": [20, 30, 45]},
}

# ========================================================================
# INDICATORS
# ========================================================================

class Ind:
    @staticmethod
    def get_klines(symbol, base_url, interval, limit=1000, end_time_ms=None):
        try:
            url = f"{base_url}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            if end_time_ms:
                params["endTime"] = end_time_ms
            resp = requests.get(url, params=params, timeout=10)
            if resp.status_code == 200:
                data = resp.json()
                if not data:
                    return None
                return {
                    "timestamps": [c[0] for c in data], "opens": [float(c[1]) for c in data],
                    "highs": [float(c[2]) for c in data], "lows": [float(c[3]) for c in data],
                    "closes": [float(c[4]) for c in data], "volumes": [float(c[5]) for c in data],
                }
            return None
        except Exception:
            return None

    @staticmethod
    def ema(data, period):
        if not data or len(data) < period:
            return data[-1] if data else 0
        alpha = 2 / (period + 1)
        ema_val = sum(data[:period]) / period
        for price in data[period:]:
            ema_val = price * alpha + ema_val * (1 - alpha)
        return ema_val

    @staticmethod
    def rsi(closes, period=14):
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
    def atr(highs, lows, closes, period=14):
        if len(closes) < period + 1:
            return (max(highs) - min(lows)) if highs and lows else 0
        tr = [max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
              for i in range(1, len(closes))]
        return sum(tr[-period:]) / period

    @staticmethod
    def macd(closes, fast=12, slow=26, signal=9):
        if len(closes) < slow:
            return {"bullish": False}
        ema_fast = Ind.ema(closes, fast); ema_slow = Ind.ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = Ind.ema([macd_line]*signal, signal)
        return {"bullish": macd_line > signal_line}

    @staticmethod
    def bollinger(closes, period=20, std_dev=2):
        if len(closes) < period:
            last = closes[-1] if closes else 0
            return {"upper": last, "lower": last}
        middle = sum(closes[-period:]) / period
        std = (sum((x-middle)**2 for x in closes[-period:]) / period) ** 0.5
        return {"upper": middle+std*std_dev, "lower": middle-std*std_dev}

    @staticmethod
    def stochastic(closes, highs, lows, period=14):
        if len(closes) < period:
            return 50.0
        hh, ll = max(highs[-period:]), min(lows[-period:])
        return 50.0 if hh == ll else ((closes[-1]-ll)/(hh-ll))*100

    @staticmethod
    def adx(highs, lows, closes, period=14):
        if len(closes) < period + 1:
            return 25.0
        plus_dm, minus_dm, tr = [], [], []
        for i in range(1, len(closes)):
            up = highs[i]-highs[i-1]; down = lows[i-1]-lows[i]
            plus_dm.append(up if up > down and up > 0 else 0)
            minus_dm.append(down if down > up and down > 0 else 0)
            tr.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        tr_ema = Ind.ema(tr[-period:], period)
        if tr_ema == 0:
            return 25.0
        plus_di = 100*(Ind.ema(plus_dm[-period:], period)/tr_ema)
        minus_di = 100*(Ind.ema(minus_dm[-period:], period)/tr_ema)
        dx = 100*abs(plus_di-minus_di)/(plus_di+minus_di) if (plus_di+minus_di) > 0 else 0
        return Ind.ema([dx]*period, period)

    @staticmethod
    def obv(closes, volumes):
        if not closes or not volumes:
            return []
        vals = [0]
        for i in range(1, len(closes)):
            if closes[i] > closes[i-1]:
                vals.append(vals[-1] + volumes[i])
            elif closes[i] < closes[i-1]:
                vals.append(vals[-1] - volumes[i])
            else:
                vals.append(vals[-1])
        return vals

    @staticmethod
    def vwap(highs, lows, closes, volumes):
        if not volumes or sum(volumes) == 0:
            return closes[-1] if closes else 0
        typical = [(h+l+c)/3 for h, l, c in zip(highs, lows, closes)]
        return sum(t*v for t, v in zip(typical, volumes)) / sum(volumes)

    @staticmethod
    def chop(highs, lows, closes, period=14):
        if len(closes) < period:
            return 50.0
        tr_sum = sum(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1]))
                     for i in range(len(closes)-period, len(closes)))
        hh, ll = max(highs[-period:]), min(lows[-period:])
        if hh == ll:
            return 50.0
        return max(0, min(100, 100*math.log10(tr_sum/(hh-ll))/math.log10(period)))

    @staticmethod
    def zscore(data, period=20):
        if len(data) < period:
            return 0
        window = data[-period:]
        mean = sum(window)/period
        std = statistics.stdev(window) if period > 1 else 0.001
        return (data[-1]-mean)/std if std > 0 else 0

# ========================================================================
# 15-INDICATOR ENSEMBLE STRATEGY (same logic used earlier in this thread)
# ========================================================================

def ensemble_signal(data: Dict, params: Dict) -> Dict:
    closes, highs, lows, volumes = data['closes'], data['highs'], data['lows'], data['volumes']
    current = closes[-1]
    signals, weights = [], []

    ema_9 = Ind.ema(closes, 9); ema_21 = Ind.ema(closes, 21); ema_50 = Ind.ema(closes, 50)
    if current > ema_9 > ema_21 > ema_50:
        signals.append(1); weights.append(1.5)
    elif current > ema_50:
        signals.append(1); weights.append(1.0)
    else:
        signals.append(0); weights.append(1.0)

    signals.append(1 if Ind.macd(closes)['bullish'] else 0); weights.append(1.5)

    rsi = Ind.rsi(closes, 14)
    if 30 < rsi < 70:
        signals.append(1 if rsi < 50 else 0.5)
    elif rsi < 30:
        signals.append(1)
    else:
        signals.append(0)
    weights.append(1.2)

    bb = Ind.bollinger(closes)
    if current < bb['lower']*1.02:
        signals.append(1)
    elif current > bb['upper']*0.98:
        signals.append(0)
    else:
        signals.append(0.5)
    weights.append(1.0)

    adx = Ind.adx(highs, lows, closes)
    signals.append(1 if adx > 25 else 0); weights.append(1.3)

    stoch = Ind.stochastic(closes, highs, lows)
    signals.append(1 if stoch < 30 else 0.3 if stoch < 50 else 0); weights.append(0.8)

    obv_values = Ind.obv(closes, volumes)
    if len(obv_values) >= 20:
        signals.append(1 if obv_values[-1] > Ind.ema(obv_values, 10) else 0)
    else:
        signals.append(0)
    weights.append(1.0)

    signals.append(1 if current > Ind.vwap(highs, lows, closes, volumes) else 0); weights.append(0.8)
    signals.append(1 if Ind.chop(highs, lows, closes) < 40 else 0); weights.append(1.0)
    signals.append(1 if Ind.zscore(closes, 20) < -1 else 0); weights.append(0.7)

    weighted_sum = sum(s*w for s, w in zip(signals, weights))
    confidence = weighted_sum / sum(weights)
    signal_count = sum(1 for s in signals if s > 0.5)
    buy_signal = signal_count >= params.get('min_signals', 6) and confidence > 0.5

    atr = Ind.atr(highs, lows, closes, 14)
    recent_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
    stop = min(current - atr*1.5, recent_low*0.98)
    target = current + atr*(3.0 if adx > 30 else 2.0)
    risk = current - stop
    reward = target - current
    rr_ratio = reward/risk if risk > 0 else 0

    return {"signal": "BUY" if buy_signal and rr_ratio > 1.5 else "NEUTRAL",
            "stop": stop, "target": target}

# ========================================================================
# BACKTEST / WALK-FORWARD MACHINERY
# ========================================================================

def backtest_trades(data: Dict, params: Dict, lookback: int) -> List[float]:
    closes, highs, lows = data['closes'], data['highs'], data['lows']
    total = len(closes)
    trades = []
    in_position = False
    entry_price = entry_index = stop_price = target_price = highest_price = None
    trailing_level = None

    for i in range(lookback, total):
        if not in_position:
            window = {k: data[k][i-lookback:i] for k in data}
            sig = ensemble_signal(window, params)
            if sig['signal'] == "BUY":
                entry_price = closes[i]; entry_index = i
                stop_price = sig['stop']; target_price = sig['target']
                highest_price = entry_price; trailing_level = stop_price
                in_position = True
        else:
            if closes[i] > highest_price:
                highest_price = closes[i]
            if params.get('trailing_stop'):
                trail = highest_price * (1 - params['trailing_pct'] * 0.02)
                if trail > trailing_level:
                    trailing_level = trail
            current_stop = trailing_level if params.get('trailing_stop') else stop_price

            exit_price = None
            if lows[i] <= current_stop:
                exit_price = current_stop
            elif highs[i] >= target_price:
                exit_price = target_price
            elif (i - entry_index) > params.get('max_hold_candles', 30):
                exit_price = closes[i]

            if exit_price is not None:
                trades.append((exit_price - entry_price) / entry_price - ROUND_TRIP_FEE)
                in_position = False
    return trades


def score_on_train(data, params, lookback, min_trades=5):
    trades = backtest_trades(data, params, lookback)
    if len(trades) < min_trades:
        return None
    return sum(trades) / len(trades)


def fetch_best_history(symbol: str, interval: str, days_back: int) -> Optional[Dict]:
    """Try each exchange endpoint (public market data, no key needed) and
    keep whichever returns more historical candles for this symbol."""
    candles_per_day = TIMEFRAME_CONFIG[interval]["candles_per_day"]
    needed = days_back * candles_per_day
    best = None
    for base_url in EXCHANGE_ENDPOINTS:
        all_data = {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
        end_time = None
        attempts = 0
        while len(all_data["closes"]) < needed and attempts < 60:
            batch = Ind.get_klines(symbol, base_url, interval, limit=1000, end_time_ms=end_time)
            attempts += 1
            if not batch or not batch["timestamps"]:
                break
            for k in all_data:
                all_data[k] = batch[k] + all_data[k]
            end_time = batch["timestamps"][0] - 1
            time.sleep(0.15)
        n = len(all_data["closes"])
        if n > 0 and (best is None or n > len(best["closes"])):
            best = all_data
            best_source = base_url
        if n >= needed:
            break  # already got everything we asked for, no need to try the other endpoint
    if best:
        print(f"    -> got {len(best['closes'])} candles")
    return best


def anchored_walk_forward(symbol: str, interval: str, param_grid: List[Dict], n_folds: int = 5,
                           min_trades_train: int = 5) -> Dict:
    cfg = TIMEFRAME_CONFIG[interval]
    data = fetch_best_history(symbol, interval, cfg["days_back"])
    if not data:
        return {"symbol": symbol, "interval": interval, "pooled_trades": [], "ok": False,
                "reason": "no data returned from either exchange endpoint"}

    total = len(data["closes"])
    lookback = cfg["lookback"]
    if total < lookback * (n_folds + 1):
        return {"symbol": symbol, "interval": interval, "pooled_trades": [], "ok": False,
                "reason": f"only {total} candles available, not enough for {n_folds} folds"}

    fold_size = total // n_folds
    boundaries = [f * fold_size for f in range(n_folds)] + [total]
    pooled = []
    fold_notes = []

    for f in range(1, n_folds):
        train_end = boundaries[f]
        test_start, test_end = boundaries[f], boundaries[f+1] if f+1 < len(boundaries) else total
        train_data = {k: data[k][:train_end] for k in data}
        test_data = {k: data[k][max(0, test_start-lookback):test_end] for k in data}

        best_score, best_params = None, None
        for params in param_grid:
            s = score_on_train(train_data, params, lookback, min_trades_train)
            if s is not None and (best_score is None or s > best_score):
                best_score, best_params = s, params

        if best_params is None:
            fold_notes.append(f"    fold {f}: no combo had enough train trades - skipped")
            continue

        oos = backtest_trades(test_data, best_params, lookback)
        pooled.extend(oos)
        fold_notes.append(f"    fold {f}: {len(oos)} OOS trades"
                           + (f", mean={100*sum(oos)/len(oos):.3f}%" if oos else ""))

    return {"symbol": symbol, "interval": interval, "pooled_trades": pooled,
            "fold_notes": fold_notes, "ok": True}


def run_wide_net_validation(symbols=SYMBOLS, intervals=("1h", "4h", "1d"),
                             n_folds=5, alpha=0.05):
    param_grid_by_interval = {}
    for interval in intervals:
        hold_opts = TIMEFRAME_CONFIG[interval]["hold_options"]
        param_grid_by_interval[interval] = [
            {"min_signals": ms, "trailing_pct": tp, "max_hold_candles": mh, "trailing_stop": ts}
            for ms in [5, 6, 7]
            for tp in [0.3, 0.5, 0.7]
            for mh in hold_opts
            for ts in [True, False]
        ]

    total_combos = len(symbols) * len(intervals)
    bonferroni_alpha = alpha / total_combos
    print(f"WIDE-NET SEARCH: {len(symbols)} symbols x {len(intervals)} timeframes "
          f"= {total_combos} (symbol, timeframe) combinations.")
    print(f"Per-fold training search per combo: ~{len(param_grid_by_interval[intervals[0]])} param sets "
          f"(selected using ONLY prior data per fold).")
    print(f"Bonferroni-corrected significance bar: p < {bonferroni_alpha:.6f} (uncorrected alpha={alpha})")
    print("="*70)

    normal = statistics.NormalDist()
    all_results = []
    skipped = []

    for symbol in symbols:
        for interval in intervals:
            print(f"\n{symbol} {interval}")
            r = anchored_walk_forward(symbol, interval, param_grid_by_interval[interval], n_folds)
            if not r["ok"]:
                print(f"  SKIP: {r['reason']}")
                skipped.append((symbol, interval, r["reason"]))
                continue
            for note in r["fold_notes"]:
                print(note)

            trades = r["pooled_trades"]
            n = len(trades)
            print(f"  Pooled OOS trades: {n}")
            if n < 10:
                print("  Too few trades to test. SKIP.")
                continue
            if n < 30:
                print(f"  LOW POWER WARNING (n={n}): treat any p-value here with real skepticism.")

            mean_ret = sum(trades) / n
            stdev_ret = statistics.stdev(trades) if n > 1 else 0
            if stdev_ret == 0:
                continue
            se = stdev_ret / (n ** 0.5)
            z = mean_ret / se
            p_value = 2 * (1 - normal.cdf(abs(z)))
            win_rate = len([t for t in trades if t > 0]) / n
            significant = mean_ret > 0 and p_value < bonferroni_alpha

            print(f"  mean/trade={mean_ret*100:.3f}% win_rate={win_rate*100:.1f}% p={p_value:.5f} "
                  f"-> {'PASS' if significant else 'fail'}")

            all_results.append({"symbol": symbol, "interval": interval, "n_trades": n,
                                 "mean_return_pct": mean_ret, "win_rate": win_rate,
                                 "p_value": p_value, "low_power": n < 30, "significant": significant})

    print("\n" + "="*70)
    print(f"SEARCHED: {total_combos - len(skipped)}/{total_combos} combinations "
          f"({len(skipped)} skipped for insufficient data)")
    passing = [r for r in all_results if r["significant"]]

    if not passing:
        print("RESULT: Across every symbol, timeframe, and available exchange history")
        print("tested, NOTHING cleared a Bonferroni-corrected significance bar under")
        print("genuine anchored walk-forward testing.")
        print()
        print("This is the widest honest search run in this whole exercise. Combined")
        print("with the earlier scalping and swing-trading results, the consistent,")
        print("repeated finding is: these technical-indicator ensembles do not have a")
        print("demonstrable edge on these instruments with retail-accessible history.")
        print("That's a real answer about this approach, not a reason to widen further -")
        print("at some point continuing to search is just p-hacking with extra steps.")
        if skipped:
            print(f"\n({len(skipped)} combos skipped for data availability - see log above -")
            print("so 'nothing found' is bounded by what history exists, not a claim about")
            print("instruments that couldn't be tested at all.)")
        print("="*70)
        return []

    passing.sort(key=lambda r: r["p_value"])
    print(f"RESULT: {len(passing)} combination(s) passed:")
    for r in passing:
        flag = " [LOW POWER - treat with skepticism]" if r["low_power"] else ""
        print(f"  {r['symbol']} {r['interval']}: {r['n_trades']} OOS trades, "
              f"mean={r['mean_return_pct']*100:.3f}%, win_rate={r['win_rate']*100:.1f}%, "
              f"p={r['p_value']:.6f}{flag}")
    print()
    print("Next honest step for any non-low-power pass: paper-trade it forward in")
    print("real time for several weeks before committing capital. A backtest passing,")
    print("even this rigorously, is evidence - not a guarantee the edge persists live.")
    print("="*70)
    return passing


if __name__ == "__main__":
    run_wide_net_validation(SYMBOLS, intervals=("1h", "4h", "1d"), n_folds=5)
