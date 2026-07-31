#!/usr/bin/env python3
"""
1D ML ENSEMBLE - HONEST ANCHORED WALK-FORWARD VALIDATION
============================================================
What was wrong with the v4.0 "Ultimate Golden Strategy" search:

  1. ~800 (parameter x symbol) combinations were tested and the winner
     was picked by an arbitrary score, with NO correction for how many
     things were tried.
  2. The parameter search and the "validation" both used the SAME
     blocks of data - there was never a truly untouched holdout. That's
     in-sample selection, not out-of-sample confirmation.
  3. 14 trades (and similarly small counts for other symbols) is far
     too few to say anything with confidence - the standard error on a
     58.9% win rate from 14 trials is roughly +/-13 percentage points.

This script fixes (1) and (2) directly:

  - ANCHORED WALK-FORWARD: for each fold, parameters are chosen using
    ONLY the data before that fold (a search, but confined to the
    past), then locked and applied UNCHANGED to that fold, which the
    search never saw. Only those genuinely out-of-sample trades count
    toward the final result.
  - Bonferroni correction sized to the number of SYMBOLS being
    compared at the final reporting stage (5, here) - the per-fold
    training search itself isn't further corrected, which is standard
    for walk-forward but does mean some optimism can still leak in
    from the training-side search; that's disclosed, not hidden.

It does NOT fix (3), because (3) isn't a code problem. If daily-bar
AVAXUSDT trades roughly once every 50 days, no amount of validation
rigor manufactures more independent trades than history actually
contains. The script will print the pooled trade count plainly so you
can see if there's enough statistical power to trust ANY p-value it
reports - and it may honestly conclude there isn't.
============================================================
"""

import time
import math
import statistics
from datetime import datetime
from typing import Dict, List, Optional
import requests

MAKER_FEE = 0.0005
TAKER_FEE = 0.0005
ROUND_TRIP_FEE = MAKER_FEE + TAKER_FEE

# ========================================================================
# INDICATORS (reused as-is - these implementations are fine)
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
        tr_values = []
        for i in range(1, len(closes)):
            tr_values.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        return sum(tr_values[-period:]) / period

    @staticmethod
    def macd(closes, fast=12, slow=26, signal=9):
        if len(closes) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0, "bullish": False}
        ema_fast = AdvancedIndicators.ema(closes, fast)
        ema_slow = AdvancedIndicators.ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = AdvancedIndicators.ema([macd_line] * signal, signal)
        return {"macd": macd_line, "signal": signal_line, "histogram": macd_line - signal_line,
                "bullish": macd_line > signal_line}

    @staticmethod
    def bollinger(closes, period=20, std_dev=2):
        if len(closes) < period:
            last = closes[-1] if closes else 0
            return {"upper": last, "middle": last, "lower": last, "position": 0.5}
        middle = sum(closes[-period:]) / period
        std = (sum((x-middle)**2 for x in closes[-period:]) / period) ** 0.5
        upper = middle + std*std_dev
        lower = middle - std*std_dev
        position = (closes[-1]-lower)/(upper-lower) if upper != lower else 0.5
        return {"upper": upper, "middle": middle, "lower": lower, "position": position}

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
        tr_ema = AdvancedIndicators.ema(tr[-period:], period)
        if tr_ema == 0:
            return 25.0
        plus_di = 100*(AdvancedIndicators.ema(plus_dm[-period:], period)/tr_ema)
        minus_di = 100*(AdvancedIndicators.ema(minus_dm[-period:], period)/tr_ema)
        dx = 100*abs(plus_di-minus_di)/(plus_di+minus_di) if (plus_di+minus_di) > 0 else 0
        return AdvancedIndicators.ema([dx]*period, period)

    @staticmethod
    def obv(closes, volumes):
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

    @staticmethod
    def keltner(highs, lows, closes, period=20):
        if len(closes) < period:
            last = closes[-1] if closes else 0
            return {"upper": last, "middle": last, "lower": last}
        middle = AdvancedIndicators.ema(closes, period)
        atr_val = AdvancedIndicators.atr(highs, lows, closes, 10)
        return {"upper": middle+atr_val*1.5, "middle": middle, "lower": middle-atr_val*1.5}

    @staticmethod
    def ichimoku(highs, lows, closes):
        if len(closes) < 52:
            last = closes[-1] if closes else 0
            return {"tenkan": last, "kijun": last}
        tenkan = (max(highs[-9:])+min(lows[-9:]))/2
        kijun = (max(highs[-26:])+min(lows[-26:]))/2
        return {"tenkan": tenkan, "kijun": kijun}

    @staticmethod
    def vortex(highs, lows, closes, period=14):
        if len(closes) < period+1:
            return {"vi_plus": 0, "vi_minus": 0}
        vm_plus, vm_minus, tr = [], [], []
        for i in range(1, len(closes)):
            vm_plus.append(abs(highs[i]-lows[i-1]))
            vm_minus.append(abs(lows[i]-highs[i-1]))
            tr.append(max(highs[i]-lows[i], abs(highs[i]-closes[i-1]), abs(lows[i]-closes[i-1])))
        s_tr = sum(tr[-period:])
        return {"vi_plus": sum(vm_plus[-period:])/s_tr if s_tr > 0 else 0,
                "vi_minus": sum(vm_minus[-period:])/s_tr if s_tr > 0 else 0}

    @staticmethod
    def cci(closes, highs, lows, period=20):
        if len(closes) < period:
            return 0
        tp = [(h+l+c)/3 for h, l, c in zip(highs, lows, closes)]
        sma_tp = sum(tp[-period:])/period
        mean_dev = sum(abs(x-sma_tp) for x in tp[-period:])/period
        return (tp[-1]-sma_tp)/(0.015*mean_dev) if mean_dev > 0 else 0

    @staticmethod
    def dmi(highs, lows, closes, period=14):
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
# ML ENSEMBLE STRATEGY (reused as-is)
# ========================================================================

class MLEnsembleStrategy:
    @staticmethod
    def signal(data: Dict, params: Dict) -> Dict:
        closes, highs, lows, volumes = data['closes'], data['highs'], data['lows'], data['volumes']
        current = closes[-1]
        signals, weights = [], []

        ema_9 = AdvancedIndicators.ema(closes, 9); ema_21 = AdvancedIndicators.ema(closes, 21)
        ema_50 = AdvancedIndicators.ema(closes, 50)
        if current > ema_9 > ema_21 > ema_50:
            signals.append(1); weights.append(1.5)
        elif current > ema_50:
            signals.append(1); weights.append(1.0)
        else:
            signals.append(0); weights.append(1.0)

        macd = AdvancedIndicators.macd(closes)
        signals.append(1 if macd['bullish'] else 0); weights.append(1.5)

        rsi = AdvancedIndicators.rsi(closes, 14)
        if 30 < rsi < 70:
            signals.append(1 if rsi < 50 else 0.5)
        elif rsi < 30:
            signals.append(1)
        else:
            signals.append(0)
        weights.append(1.2)

        bb = AdvancedIndicators.bollinger(closes)
        if current < bb['lower']*1.02:
            signals.append(1)
        elif current > bb['upper']*0.98:
            signals.append(0)
        else:
            signals.append(0.5)
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
        total_weight = sum(weights)
        confidence = weighted_sum / total_weight
        signal_count = sum(1 for s in signals if s > 0.5)
        min_signals = params.get('min_signals', 8)
        buy_signal = signal_count >= min_signals and confidence > 0.5

        atr = AdvancedIndicators.atr(highs, lows, closes, 14)
        recent_low = min(lows[-20:]) if len(lows) >= 20 else min(lows)
        stop = min(current - atr*1.5, recent_low*0.98)
        target = current + atr*(3.0 if adx > 30 else 2.0)
        risk = current - stop
        reward = target - current
        rr_ratio = reward/risk if risk > 0 else 0

        return {"signal": "BUY" if buy_signal and rr_ratio > 1.5 else "NEUTRAL",
                "stop": stop, "target": target}

# ========================================================================
# BACKTEST (single param set -> trade list)
# ========================================================================

def backtest_trades(data: Dict, params: Dict, min_hold_lookback: int = 100) -> List[float]:
    closes, highs, lows = data['closes'], data['highs'], data['lows']
    total = len(closes)
    trades = []
    in_position = False
    entry_price = entry_index = stop_price = target_price = highest_price = None
    trailing_stop_level = None

    for i in range(min_hold_lookback, total):
        if not in_position:
            window = {k: data[k][i-min_hold_lookback:i] for k in data}
            signal = MLEnsembleStrategy.signal(window, params)
            if signal['signal'] == "BUY":
                entry_price = closes[i]; entry_index = i
                stop_price = signal['stop']; target_price = signal['target']
                highest_price = entry_price; trailing_stop_level = stop_price
                in_position = True
        else:
            if closes[i] > highest_price:
                highest_price = closes[i]
            if params.get('trailing_stop'):
                trail = highest_price * (1 - params['trailing_pct'] * 0.02)
                if trail > trailing_stop_level:
                    trailing_stop_level = trail
            current_stop = trailing_stop_level if params.get('trailing_stop') else stop_price

            exit_price = None
            if lows[i] <= current_stop:
                exit_price = current_stop
            elif highs[i] >= target_price:
                exit_price = target_price
            elif (i - entry_index) > params.get('max_hold_days', 30):
                exit_price = closes[i]

            if exit_price is not None:
                net = (exit_price - entry_price) / entry_price - ROUND_TRIP_FEE
                trades.append(net)
                in_position = False
    return trades


def score_params_on_train(data: Dict, params: Dict, min_trades: int = 5) -> Optional[float]:
    """Used only to pick parameters WITHIN a training window. Simple and
    transparent on purpose (mean expectancy), since anything fancier here
    just relocates the overfitting risk rather than removing it."""
    trades = backtest_trades(data, params)
    if len(trades) < min_trades:
        return None
    return sum(trades) / len(trades)


def fetch_history(symbol: str, interval: str, days_back: int, base_url: str = "https://api.binance.us") -> Dict:
    print(f"  Fetching ~{days_back}d of {interval} {symbol}...")
    all_data = {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
    end_time = None
    needed = days_back  # 1 candle/day
    while len(all_data["closes"]) < needed:
        batch = AdvancedIndicators.get_klines(symbol, base_url, interval, limit=1000, end_time_ms=end_time)
        if not batch or not batch["timestamps"]:
            break
        for k in all_data:
            all_data[k] = batch[k] + all_data[k]
        end_time = batch["timestamps"][0] - 1
        time.sleep(0.2)
    return all_data


def anchored_walk_forward(symbol: str, interval: str, days_back: int, n_folds: int,
                           param_grid: List[Dict], min_hold_lookback: int = 100,
                           min_trades_train: int = 5) -> Dict:
    """
    For fold f = 1..n_folds-1:
      - train on all candles strictly BEFORE fold f begins
      - pick the param combo with the best TRAIN expectancy (min_trades_train
        trades minimum)
      - apply that combo, UNCHANGED, to fold f only -> genuinely
        out-of-sample trades
    Pool all out-of-sample trades across folds for the final statistic.
    """
    data = fetch_history(symbol, interval, days_back)
    total = len(data["closes"])
    if total < min_hold_lookback * (n_folds + 1):
        print(f"  Not enough {symbol} history ({total} candles) for {n_folds} folds - skipping.")
        return {"symbol": symbol, "pooled_trades": [], "insufficient_data": True}

    fold_size = total // n_folds
    fold_boundaries = [f * fold_size for f in range(n_folds)] + [total]

    pooled_oos_trades = []
    fold_reports = []

    for f in range(1, n_folds):
        train_end = fold_boundaries[f]
        test_start = fold_boundaries[f]
        test_end = fold_boundaries[f + 1] if f + 1 < len(fold_boundaries) else total

        train_data = {k: data[k][:train_end] for k in data}
        lookback_start = max(0, test_start - min_hold_lookback)
        test_data = {k: data[k][lookback_start:test_end] for k in data}

        best_score, best_params = None, None
        for params in param_grid:
            s = score_params_on_train(train_data, params, min_trades_train)
            if s is not None and (best_score is None or s > best_score):
                best_score, best_params = s, params

        if best_params is None:
            fold_reports.append(f"  Fold {f}: no param combo had >= {min_trades_train} train trades - skipped")
            continue

        oos_trades = backtest_trades(test_data, best_params, min_hold_lookback)
        pooled_oos_trades.extend(oos_trades)
        fold_reports.append(
            f"  Fold {f}: trained params min_signals={best_params['min_signals']} "
            f"trail={best_params['trailing_pct']} hold={best_params['max_hold_days']}d "
            f"trail_stop={best_params['trailing_stop']}  ->  {len(oos_trades)} OOS trades, "
            f"OOS mean={100*sum(oos_trades)/len(oos_trades):.3f}%" if oos_trades else
            f"  Fold {f}: trained params selected, but 0 OOS trades occurred in this fold"
        )

    return {"symbol": symbol, "pooled_trades": pooled_oos_trades, "fold_reports": fold_reports,
            "insufficient_data": False}


def run_honest_validation(symbols: List[str], interval: str = "1d", days_back: int = 1000,
                           n_folds: int = 5, alpha: float = 0.05):
    param_grid = [
        {"min_signals": ms, "trailing_pct": tp, "max_hold_days": mh, "trailing_stop": ts}
        for ms in [7, 8, 9]
        for tp in [0.3, 0.5, 0.7]
        for mh in [20, 30, 45]
        for ts in [True, False]
    ]
    print(f"Per-fold training search space: {len(param_grid)} combos (chosen using ONLY prior data per fold).")

    bonferroni_alpha = alpha / len(symbols)
    print(f"Reporting-stage Bonferroni correction across {len(symbols)} symbols: "
          f"p < {bonferroni_alpha:.5f} (uncorrected alpha={alpha})\n")

    normal = statistics.NormalDist()
    results = []

    for symbol in symbols:
        print(f"\n{'='*70}\n{symbol} {interval}\n{'='*70}")
        r = anchored_walk_forward(symbol, interval, days_back, n_folds, param_grid)
        if r["insufficient_data"]:
            continue
        for line in r["fold_reports"]:
            print(line)

        trades = r["pooled_trades"]
        n = len(trades)
        print(f"\n  Pooled genuinely-out-of-sample trades: {n}")
        if n < 30:
            print(f"  WARNING: n={n} is low. Even a 'passing' p-value here should be treated")
            print(f"  with real skepticism - this is a statistical power problem, not something")
            print(f"  the test itself can fix. More history or a higher trade-frequency")
            print(f"  timeframe would be needed to actually resolve this.")

        if n < 10:
            print("  Too few trades to compute anything meaningful. SKIP.")
            continue

        mean_ret = sum(trades) / n
        stdev_ret = statistics.stdev(trades) if n > 1 else 0
        if stdev_ret == 0:
            continue
        se = stdev_ret / (n ** 0.5)
        z = mean_ret / se
        p_value = 2 * (1 - normal.cdf(abs(z)))
        win_rate = len([t for t in trades if t > 0]) / n
        significant = mean_ret > 0 and p_value < bonferroni_alpha

        print(f"  Mean OOS return/trade: {mean_ret*100:.3f}% | Win rate: {win_rate*100:.1f}% | p={p_value:.5f}"
              f"  -> {'PASS' if significant else 'fail'}")

        if significant:
            results.append({"symbol": symbol, "n_trades": n, "mean_return_pct": mean_ret,
                             "win_rate": win_rate, "p_value": p_value})

    print("\n" + "="*70)
    if not results:
        print("RESULT: No symbol produced a statistically significant, genuinely")
        print("out-of-sample edge under anchored walk-forward testing.")
        print()
        print("If pooled trade counts were consistently under ~30, the honest")
        print("conclusion is that daily-bar crypto swing trading, at the history")
        print("depth available on this exchange, may not provide enough independent")
        print("trades to ever validate an edge with confidence - regardless of which")
        print("indicators are used. That's a data ceiling, not a search failure.")
        print("="*70)
        return []

    results.sort(key=lambda r: r["p_value"])
    print(f"RESULT: {len(results)} symbol(s) passed:")
    for r in results:
        print(f"  {r['symbol']}: {r['n_trades']} OOS trades, mean={r['mean_return_pct']*100:.3f}%, "
              f"win_rate={r['win_rate']*100:.1f}%, p={r['p_value']:.6f}")
    print("Even a pass here still only reflects the AVAILABLE history and a fee/")
    print("slippage-free simulation. Paper-trade before risking real capital.")
    print("="*70)
    return results


if __name__ == "__main__":
    symbols = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "LINKUSDT", "AVAXUSDT"]
    run_honest_validation(symbols, interval="1d", days_back=1000, n_folds=5)
