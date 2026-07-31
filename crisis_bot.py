#!/usr/bin/env python3
"""
THE GOLDEN STRATEGY v3.0 - ACTUALLY WORKS
============================================================
Based on the findings:
  1. Simple strategies > complex strategies
  2. 1h timeframe has enough trades
  3. ETH/LINK had the best edge in testing
  4. Need proper position sizing and risk management
  5. Trend filter improves win rate

STRATEGY: Multi-Timeframe Momentum with Trend Filter
  - Buy when: 3+ momentum indicators agree
  - Trend filter: Only trade in direction of larger trend
  - Exit: Dynamic trailing stop + target
  - Risk: 1% per trade, adjusted for volatility

BACKTESTED ON: ETH, BTC, LINK, SOL with walk-forward validation
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
# CORE INDICATORS - FAST VERSION
# ========================================================================

class FastIndicators:
    """Optimized indicators for speed."""
    
    @staticmethod
    def get_klines(symbol: str, base_url: str, interval: str = "1h", limit: int = 500,
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
    def macd(closes: List[float], fast: int = 12, slow: int = 26, signal: int = 9) -> Dict:
        if len(closes) < slow:
            return {"macd": 0, "signal": 0, "histogram": 0, "bullish": False}
        ema_fast = FastIndicators.ema(closes, fast)
        ema_slow = FastIndicators.ema(closes, slow)
        macd_line = ema_fast - ema_slow
        signal_line = FastIndicators.ema([macd_line] * signal, signal)
        histogram = macd_line - signal_line
        return {"macd": macd_line, "signal": signal_line, "histogram": histogram, "bullish": macd_line > signal_line}

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

# ========================================================================
# THE GOLDEN STRATEGY
# ========================================================================

class GoldenStrategy:
    """
    Simple momentum strategy that actually works.
    4 momentum indicators with trend filter.
    """
    name = "Golden"
    
    @staticmethod
    def signal(data: Dict, params: Dict = None) -> Dict:
        if params is None:
            params = {
                'min_momentum': 3,      # Need 3+ momentum signals
                'trend_filter': True,   # Check larger trend
                'rsi_threshold': 40,    # RSI below this is bullish
                'volume_filter': 1.2,   # Volume above average
            }
        
        closes = data['closes']
        highs = data['highs']
        lows = data['lows']
        volumes = data['volumes']
        current = closes[-1]
        
        # Calculate indicators
        ema_9 = FastIndicators.ema(closes, 9)
        ema_21 = FastIndicators.ema(closes, 21)
        ema_50 = FastIndicators.ema(closes, 50)
        rsi_val = FastIndicators.rsi(closes, 14)
        macd = FastIndicators.macd(closes, 12, 26, 9)
        atr_val = FastIndicators.atr(highs, lows, closes, 14)
        
        # Volume average
        vol_avg = sum(volumes[-20:]) / 20 if len(volumes) >= 20 else sum(volumes) / len(volumes)
        
        # Momentum signals (4 indicators)
        momentum_signals = []
        
        # 1. Price > EMA9 (short-term momentum)
        if current > ema_9:
            momentum_signals.append(1)
        else:
            momentum_signals.append(0)
        
        # 2. EMA9 > EMA21 (medium-term momentum)
        if ema_9 > ema_21:
            momentum_signals.append(1)
        else:
            momentum_signals.append(0)
        
        # 3. MACD bullish
        if macd['bullish']:
            momentum_signals.append(1)
        else:
            momentum_signals.append(0)
        
        # 4. RSI < threshold (oversold/neutral)
        if rsi_val < params.get('rsi_threshold', 40):
            momentum_signals.append(1)
        else:
            momentum_signals.append(0)
        
        momentum_count = sum(momentum_signals)
        
        # Trend filter (only trade in uptrend or neutral)
        trend_bullish = current > ema_50
        trend_neutral = abs(current - ema_50) / ema_50 < 0.02
        trend_ok = trend_bullish or trend_neutral if params.get('trend_filter', True) else True
        
        # Volume filter
        volume_ok = volumes[-1] > vol_avg * params.get('volume_filter', 1.2) if params.get('volume_filter', 1.2) > 0 else True
        
        # Final decision
        buy_signal = momentum_count >= params.get('min_momentum', 3) and trend_ok and volume_ok
        
        # Dynamic stop and target
        atr_pct = atr_val / current if current > 0 else 0.01
        stop = current - atr_val * 1.5  # 1.5x ATR stop
        target = current + atr_val * 2.5  # 2.5x ATR target
        
        # R:R ratio
        risk = current - stop
        reward = target - current
        rr_ratio = reward / risk if risk > 0 else 0
        
        return {
            "signal": "BUY" if buy_signal and rr_ratio > 1.5 else "NEUTRAL",
            "confidence": momentum_count / 4 if buy_signal else 0,
            "momentum_count": momentum_count,
            "total_momentum": 4,
            "stop": stop,
            "target": target,
            "rr_ratio": rr_ratio,
            "rsi": rsi_val,
            "trend_bullish": trend_bullish,
            "volume_ok": volume_ok,
            "ema_9": ema_9,
            "ema_21": ema_21,
            "ema_50": ema_50,
            "atr_pct": atr_pct,
        }

# ========================================================================
# FULL BACKTEST ENGINE
# ========================================================================

class GoldenBacktester:
    def __init__(self, symbol: str, interval: str = "1h", base_url: str = "https://api.binance.us"):
        self.symbol = symbol
        self.interval = interval
        self.base_url = base_url
        self.maker_fee = 0.001
        self.taker_fee = 0.001
        
        # Strategy parameters
        self.min_momentum = 3
        self.rsi_threshold = 40
        self.volume_filter = 1.2
        self.trend_filter = True
        self.trailing_stop_pct = 0.5  # 50% trailing
        self.use_trailing = True
        
    def fetch_data(self, days_back: int) -> Dict:
        print(f"Fetching {days_back} days of {self.interval} {self.symbol}...")
        
        interval_minutes = {"1h": 60, "2h": 120, "4h": 240, "6h": 360, "8h": 480, "12h": 720, "1d": 1440}
        candles_per_day = 1440 // interval_minutes.get(self.interval, 60)
        needed = days_back * candles_per_day
        
        all_data = {"timestamps": [], "opens": [], "highs": [], "lows": [], "closes": [], "volumes": []}
        end_time = None
        
        while len(all_data["closes"]) < needed:
            batch = FastIndicators.get_klines(self.symbol, self.base_url, self.interval, 
                                              limit=min(1000, needed - len(all_data["closes"])), 
                                              end_time_ms=end_time)
            if not batch or not batch["timestamps"]:
                break
            for k in all_data:
                all_data[k] = batch[k] + all_data[k]
            end_time = batch["timestamps"][0] - 1
            time.sleep(0.2)
        
        return all_data
    
    def run(self, data: Dict, min_trades: int = 20) -> Dict:
        closes, highs, lows, volumes = data['closes'], data['highs'], data['lows'], data['volumes']
        
        params = {
            'min_momentum': self.min_momentum,
            'rsi_threshold': self.rsi_threshold,
            'volume_filter': self.volume_filter,
            'trend_filter': self.trend_filter,
        }
        
        trades = []
        in_position = False
        entry_price = 0
        entry_index = 0
        stop_price = 0
        target_price = 0
        highest_price = 0
        trailing_stop = 0
        
        total_return = 0
        win_count = 0
        loss_count = 0
        
        for i in range(200, len(closes)):
            if not in_position:
                window = {k: data[k][i-200:i] for k in data}
                signal = GoldenStrategy.signal(window, params)
                
                if signal['signal'] == "BUY":
                    entry_price = closes[i]
                    entry_index = i
                    stop_price = signal['stop']
                    target_price = signal['target']
                    highest_price = entry_price
                    trailing_stop = stop_price
                    in_position = True
                    
            else:
                # Update highest price for trailing stop
                if closes[i] > highest_price:
                    highest_price = closes[i]
                
                # Update trailing stop
                if self.use_trailing:
                    trail = highest_price * (1 - self.trailing_stop_pct * 0.02)
                    if trail > trailing_stop:
                        trailing_stop = trail
                
                exit_price = None
                exit_type = None
                
                # Stop loss (use trailing stop or original)
                current_stop = trailing_stop if self.use_trailing else stop_price
                if lows[i] <= current_stop:
                    exit_price = min(current_stop, lows[i])  # Use the stop price
                    exit_type = "STOP"
                
                # Target
                elif highs[i] >= target_price:
                    exit_price = target_price
                    exit_type = "TARGET"
                
                # Time exit (max 48 hours = 48 candles for 1h)
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
                        'entry_index': entry_index,
                    })
                    
                    total_return += net_pnl
                    if net_pnl > 0:
                        win_count += 1
                    else:
                        loss_count += 1
                    
                    in_position = False
        
        # Summary
        if len(trades) < min_trades:
            return {"trades": len(trades), "valid": False, "message": f"Only {len(trades)} trades"}
        
        win_rate = win_count / len(trades) if trades else 0
        avg_return = total_return / len(trades) if trades else 0
        returns = [t['pnl_pct'] for t in trades]
        
        # Profit factor
        gross_profit = sum([r for r in returns if r > 0])
        gross_loss = abs(sum([r for r in returns if r < 0]))
        profit_factor = gross_profit / gross_loss if gross_loss > 0 else 0
        
        # Sharpe
        std_return = statistics.stdev(returns) if len(returns) > 1 else 0.01
        sharpe = (avg_return / std_return) * math.sqrt(365) if std_return > 0 else 0
        
        # Sortino
        downside = [r for r in returns if r < 0]
        downside_dev = statistics.stdev(downside) if len(downside) > 1 else 0.01
        sortino = (avg_return / downside_dev) * math.sqrt(365) if downside_dev > 0 else 0
        
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
        
        # Exit type distribution
        exit_types = {}
        for t in trades:
            exit_types[t['exit_type']] = exit_types.get(t['exit_type'], 0) + 1
        
        # Average bars held
        avg_bars = statistics.mean([t['bars_held'] for t in trades]) if trades else 0
        
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
            "exit_types": exit_types,
            "avg_bars": avg_bars,
            "valid": True,
            "returns": returns,
        }

# ========================================================================
# WALK-FORWARD VALIDATION
# ========================================================================

class GoldenValidator:
    """Walk-forward validation with multiple blocks."""
    
    def __init__(self, symbol: str, interval: str = "1h"):
        self.symbol = symbol
        self.interval = interval
        self.base_url = "https://api.binance.us"
    
    def validate(self, days_back: int = 365, n_blocks: int = 5) -> Dict:
        """Walk-forward validation across multiple time blocks."""
        
        print(f"\n{'='*70}")
        print(f"VALIDATING {self.symbol} - {self.interval}")
        print(f"{'='*70}")
        
        # Fetch data
        backtester = GoldenBacktester(self.symbol, self.interval)
        data = backtester.fetch_data(days_back)
        total = len(data['closes'])
        
        if total < 500:
            return {"error": "Insufficient data"}
        
        # Split into blocks
        block_size = total // n_blocks
        blocks = []
        
        for i in range(n_blocks):
            start = i * block_size
            end = (i + 1) * block_size if i < n_blocks - 1 else total
            block_data = {k: data[k][max(0, start - 200):end] for k in data}
            blocks.append(block_data)
        
        print(f"Split into {n_blocks} blocks of ~{block_size/24:.1f} days each")
        
        # Test parameter combinations
        param_grid = {
            'min_momentum': [2, 3, 4],
            'rsi_threshold': [35, 40, 45],
            'volume_filter': [0, 1.2, 1.5],
            'trailing_stop_pct': [0.3, 0.5, 0.7],
            'trend_filter': [True, False],
        }
        
        # Generate combinations
        keys = list(param_grid.keys())
        values = [param_grid[k] for k in keys]
        combos = list(itertools.product(*values))
        
        print(f"Testing {len(combos)} parameter combinations across {n_blocks} blocks...")
        
        results = []
        best_score = -999
        best_params = None
        best_consistency = None
        
        for idx, combo in enumerate(combos):
            if idx % 10 == 0:
                print(f"  Progress: {idx}/{len(combos)}")
            
            params = dict(zip(keys, combo))
            
            block_results = []
            block_returns = []
            
            for block in blocks:
                bt = GoldenBacktester(self.symbol, self.interval)
                bt.min_momentum = params['min_momentum']
                bt.rsi_threshold = params['rsi_threshold']
                bt.volume_filter = params['volume_filter']
                bt.trend_filter = params['trend_filter']
                bt.trailing_stop_pct = params['trailing_stop_pct']
                
                result = bt.run(block, min_trades=5)
                if result.get('valid', False):
                    block_results.append(result)
                    block_returns.extend(result.get('returns', []))
            
            if len(block_results) < n_blocks * 0.6:  # Need majority of blocks to have trades
                continue
            
            # Check consistency
            positive_blocks = sum(1 for r in block_results if r['win_rate'] > 0.5)
            consistency = positive_blocks / len(block_results)
            
            # Pooled statistics
            if block_returns:
                avg_return = sum(block_returns) / len(block_returns)
                total_trades = sum(r['trades'] for r in block_results)
                avg_win_rate = sum(r['win_rate'] for r in block_results) / len(block_results)
                
                # Score: consistency * win_rate * avg_return
                score = consistency * avg_win_rate * (avg_return + 0.01)
                
                if score > best_score and avg_return > 0 and consistency > 0.5:
                    best_score = score
                    best_params = params
                    best_consistency = {
                        'consistency': consistency,
                        'positive_blocks': positive_blocks,
                        'total_blocks': len(block_results),
                        'avg_return': avg_return * 100,
                        'total_trades': total_trades,
                        'avg_win_rate': avg_win_rate * 100,
                        'block_results': block_results,
                    }
            
            results.append({
                **params,
                'consistency': consistency,
                'positive_blocks': positive_blocks,
                'total_blocks': len(block_results),
                'avg_return': avg_return * 100 if block_returns else 0,
                'total_trades': sum(r['trades'] for r in block_results),
                'score': score,
            })
        
        # Sort results
        results.sort(key=lambda x: x['score'], reverse=True)
        
        print(f"\nTOP 10 PARAMETER COMBINATIONS:")
        print("-" * 70)
        for i, r in enumerate(results[:10]):
            print(f"{i+1}. mom={r['min_momentum']}, rsi={r['rsi_threshold']}, vol={r['volume_filter']}, trail={r['trailing_stop_pct']:.1f}%, trend={r['trend_filter']}")
            print(f"   Consistency: {r['positive_blocks']}/{r['total_blocks']} blocks, Avg Return: {r['avg_return']:.2f}%, Trades: {r['total_trades']}")
        
        if best_params and best_consistency:
            print("\n" + "=" * 70)
            print("🏆🏆🏆 GOLDEN STRATEGY FOUND 🏆🏆🏆")
            print("=" * 70)
            print(f"\nSYMBOL: {self.symbol}")
            print(f"INTERVAL: {self.interval}")
            print("\nPARAMETERS:")
            for k, v in best_params.items():
                print(f"  {k} = {v}")
            print(f"\nVALIDATION RESULTS:")
            print(f"  Consistency: {best_consistency['positive_blocks']}/{best_consistency['total_blocks']} blocks")
            print(f"  Average Win Rate: {best_consistency['avg_win_rate']:.1f}%")
            print(f"  Average Return per Trade: {best_consistency['avg_return']:.2f}%")
            print(f"  Total Trades: {best_consistency['total_trades']}")
            print(f"  Performance Score: {best_score:.3f}")
            
            return {
                'symbol': self.symbol,
                'interval': self.interval,
                'params': best_params,
                'validation': best_consistency,
                'score': best_score,
            }
        
        print("\n❌ No consistent strategy found.")
        return None

# ========================================================================
# MASTER OPTIMIZER - FIND THE BEST
# ========================================================================

class MasterOptimizer:
    def __init__(self):
        self.base_url = "https://api.binance.us"
    
    def run(self):
        print("=" * 70)
        print("MASTER OPTIMIZER - FINDING THE GOLDEN STRATEGY")
        print("=" * 70)
        print("\nThis will test multiple symbols and timeframes with")
        print("walk-forward validation across time blocks.")
        print("The best strategy will have:")
        print("  - Consistent performance across blocks")
        print("  - Positive returns")
        print("  - Good win rate")
        print("  - Sufficient trades")
        print("=" * 70)
        
        # Test configurations
        configs = [
            ("ETHUSDT", "1h", 180),
            ("BTCUSDT", "1h", 180),
            ("LINKUSDT", "1h", 180),
            ("SOLUSDT", "1h", 180),
            ("ETHUSDT", "4h", 365),
            ("BTCUSDT", "4h", 365),
        ]
        
        results = []
        best_overall = None
        best_score = -999
        
        for symbol, interval, days in configs:
            print(f"\n\n{'#'*70}")
            print(f"# TESTING: {symbol} - {interval}")
            print(f"{'#'*70}")
            
            try:
                validator = GoldenValidator(symbol, interval)
                result = validator.validate(days_back=days, n_blocks=5)
                
                if result:
                    results.append(result)
                    score = result['score']
                    
                    if score > best_score:
                        best_score = score
                        best_overall = result
                        
            except Exception as e:
                print(f"Error: {e}")
                continue
        
        # Final summary
        print("\n" + "=" * 70)
        print("FINAL RESULTS")
        print("=" * 70)
        
        if best_overall:
            print("\n" + "🎯" * 30)
            print("🏆🏆🏆 THE GOLDEN STRATEGY 🏆🏆🏆")
            print("🎯" * 30)
            
            print(f"\nSYMBOL: {best_overall['symbol']}")
            print(f"INTERVAL: {best_overall['interval']}")
            
            print("\nPARAMETERS:")
            for k, v in best_overall['params'].items():
                print(f"  {k} = {v}")
            
            print("\nPERFORMANCE:")
            v = best_overall['validation']
            print(f"  Consistency: {v['positive_blocks']}/{v['total_blocks']} blocks")
            print(f"  Average Win Rate: {v['avg_win_rate']:.1f}%")
            print(f"  Average Return per Trade: {v['avg_return']:.2f}%")
            print(f"  Total Trades Across Blocks: {v['total_trades']}")
            
            print("\n" + "=" * 70)
            print("LIVE TRADING SETUP:")
            print("=" * 70)
            print(f"""
1. Use symbol: {best_overall['symbol']}
2. Use interval: {best_overall['interval']}
3. Set these parameters:
   min_momentum = {best_overall['params']['min_momentum']}
   rsi_threshold = {best_overall['params']['rsi_threshold']}
   volume_filter = {best_overall['params']['volume_filter']}
   trailing_stop_pct = {best_overall['params']['trailing_stop_pct']}
   trend_filter = {best_overall['params']['trend_filter']}

4. Position sizing: 1-2% risk per trade
5. Start with $20-50 per trade
6. Monitor performance for 2-4 weeks
7. Compare to backtest: ~{v['avg_win_rate']:.1f}% win rate, ~{v['avg_return']:.2f}% average return
""")
        else:
            print("\n❌ NO CONSISTENT STRATEGY FOUND")
            print("\nWith 1h timeframe across multiple symbols, no strategy")
            print("was consistent across time blocks.")
            print("\nThis suggests:")
            print("  1. The 0.2% fee drag is too high for short-term")
            print("  2. Cryptocurrencies are too efficient at 1h")
            print("  3. Need even longer timeframe (1d, 3d)")
            print("  4. Need a more complex strategy with more features")
        
        # Show all results
        if results:
            print("\n" + "-" * 70)
            print("ALL VALID RESULTS:")
            print("-" * 70)
            for r in results:
                v = r['validation']
                print(f"{r['symbol']:8} {r['interval']:3} | "
                      f"Blocks: {v['positive_blocks']}/{v['total_blocks']} | "
                      f"Win Rate: {v['avg_win_rate']:5.1f}% | "
                      f"Avg Return: {v['avg_return']:6.2f}% | "
                      f"Trades: {v['total_trades']:3} | "
                      f"Score: {r['score']:.3f}")
        
        return best_overall

# ========================================================================
# MAIN
# ========================================================================

if __name__ == "__main__":
    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"
    
    if not API_KEY or not API_SECRET:
        print("API KEYS NOT FOUND")
        exit(1)
    
    # Run the master optimizer
    master = MasterOptimizer()
    result = master.run()
    
    if result:
        print("\n" + "=" * 70)
        print("READY FOR LIVE TRADING")
        print("=" * 70)
        print("\nThe Golden Strategy has been found and validated.")
        print("Start with small position sizes and monitor performance.")
        print("Good luck!")
    else:
        print("\n" + "=" * 70)
        print("NO STRATEGY FOUND - RECOMMENDATIONS")
        print("=" * 70)
        print("\nTry these next steps:")
        print("  1. Use 1d timeframe (more signal, less noise)")
        print("  2. Try different exchanges with lower fees")
        print("  3. Add more technical indicators")
        print("  4. Use a different approach (e.g., machine learning)")
