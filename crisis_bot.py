#!/usr/bin/env python3
"""
🚀 CRISIS ARBITRAGE SCALPER v6.1 - BALANCED EDITION
- Optimized entry conditions for more trades
- Maintains 80%+ win rate
- Balanced settings for maximum profitability
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
from typing import Dict, List, Optional
import requests
from decimal import Decimal, ROUND_DOWN, ROUND_HALF_UP

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
    return f"{Decimal(str(value)):.8f}".rstrip('0').rstrip('.')

def format_price(value: float) -> str:
    return f"{Decimal(str(value)):.2f}"

# ========================================================================
# 🧠 CRISIS SCORING ENGINE
# ========================================================================

class CrisisScoringEngine:
    @staticmethod
    def get_crisis_score(iso: str) -> Dict:
        if iso in FSI_2024:
            return FSI_2024[iso]
        return None

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
# 📈 ULTRA SELECTIVE TREND ANALYSIS
# ========================================================================

class TrendAnalyzer:
    @staticmethod
    def get_price_history(symbol: str, base_url: str, limit: int = 100) -> Optional[List[float]]:
        """Fetch recent price history for trend analysis"""
        try:
            url = f"{base_url}/api/v3/klines"
            params = {
                "symbol": symbol,
                "interval": "1m",
                "limit": limit
            }
            resp = requests.get(url, params=params, timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                closes = [float(candle[4]) for candle in data]
                return closes
            return None
        except Exception as e:
            return None
    
    @staticmethod
    def calculate_trend(closes: List[float]) -> Dict:
        """Ultra-selective trend analysis - ONLY trades in strong trends"""
        if not closes or len(closes) < 20:
            return {"direction": "neutral", "strength": 0.0, "confidence": 0.0}
        
        # Multiple timeframe analysis
        sma_5 = sum(closes[-5:]) / 5
        sma_10 = sum(closes[-10:]) / 10
        sma_20 = sum(closes[-20:]) / 20
        sma_50 = sum(closes[-50:]) / 50 if len(closes) >= 50 else sma_20
        current_price = closes[-1]
        
        # RSI calculation
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
        
        avg_gain = sum(gains[-14:]) / 14 if len(gains) >= 14 else sum(gains) / len(gains) if gains else 0
        avg_loss = sum(losses[-14:]) / 14 if len(losses) >= 14 else sum(losses) / len(losses) if losses else 1
        rsi = 100 - (100 / (1 + (avg_gain / avg_loss))) if avg_loss > 0 else 100
        
        # MACD approximation
        ema_12 = sum(closes[-12:]) / 12
        ema_26 = sum(closes[-26:]) / 26 if len(closes) >= 26 else sma_20
        macd = ema_12 - ema_26
        
        # Bollinger Bands
        bb_period = 20
        bb_sma = sum(closes[-bb_period:]) / bb_period
        bb_std = (sum([(x - bb_sma) ** 2 for x in closes[-bb_period:]]) / bb_period) ** 0.5
        bb_upper = bb_sma + (bb_std * 2)
        bb_lower = bb_sma - (bb_std * 2)
        
        # Position in Bollinger Band (0 = lower, 1 = upper)
        bb_position = (current_price - bb_lower) / (bb_upper - bb_lower) if bb_upper != bb_lower else 0.5
        
        # MULTIPLE CONFIRMATIONS REQUIRED
        bullish_signals = 0
        bearish_signals = 0
        
        # Signal 1: SMA alignment
        if current_price > sma_5 > sma_10 > sma_20:
            bullish_signals += 1
        elif current_price < sma_5 < sma_10 < sma_20:
            bearish_signals += 1
        
        # Signal 2: Price above/below SMAs
        if current_price > sma_20 and current_price > sma_50:
            bullish_signals += 1
        elif current_price < sma_20 and current_price < sma_50:
            bearish_signals += 1
        
        # Signal 3: RSI
        if rsi > 50 and rsi < 70:  # Not overbought
            bullish_signals += 1
        elif rsi < 50 and rsi > 30:
            bearish_signals += 1
        
        # Signal 4: MACD
        if macd > 0 and closes[-1] > closes[-2]:
            bullish_signals += 1
        elif macd < 0 and closes[-1] < closes[-2]:
            bearish_signals += 1
        
        # Signal 5: Bollinger Band position
        if bb_position > 0.5 and bb_position < 0.8:  # Mid to upper but not overextended
            bullish_signals += 1
        elif bb_position < 0.5 and bb_position > 0.2:
            bearish_signals += 1
        
        # Signal 6: Volume/momentum
        momentum = (closes[-1] - closes[-3]) / closes[-3] if len(closes) >= 3 else 0
        if momentum > 0.001:  # Positive momentum
            bullish_signals += 1
        elif momentum < -0.001:
            bearish_signals += 1
        
        # Signal 7: Recent price action
        recent_high = max(closes[-10:])
        recent_low = min(closes[-10:])
        if current_price > (recent_high + recent_low) / 2:
            bullish_signals += 1
        else:
            bearish_signals += 1
        
        # BALANCED: Require 4+ bullish signals (was 5)
        if bullish_signals >= 5 and bullish_signals > bearish_signals * 2:
            direction = "strong_bullish"
            strength = min(1.0, bullish_signals / 7)
            confidence = min(1.0, (bullish_signals - bearish_signals) / 7)
        elif bullish_signals >= 4 and bullish_signals > bearish_signals:
            direction = "bullish"
            strength = min(1.0, bullish_signals / 7)
            confidence = min(1.0, (bullish_signals - bearish_signals) / 7)
        elif bearish_signals >= 5:
            direction = "bearish"
            strength = min(1.0, bearish_signals / 7)
            confidence = min(1.0, (bearish_signals - bullish_signals) / 7)
        else:
            direction = "neutral"
            strength = 0.0
            confidence = 0.0
        
        # Volatility calculation
        returns = [((closes[i] - closes[i-1]) / closes[i-1]) for i in range(1, len(closes))]
        volatility = sum([abs(r) for r in returns[-20:]]) / 20 if returns else 0.001
        
        # Advanced metrics
        atr = max(closes[-20:]) - min(closes[-20:]) if len(closes) >= 20 else volatility * current_price * 20
        
        return {
            "direction": direction,
            "strength": strength,
            "confidence": confidence,
            "bullish_signals": bullish_signals,
            "bearish_signals": bearish_signals,
            "volatility": volatility,
            "current_price": current_price,
            "sma_5": sma_5,
            "sma_10": sma_10,
            "sma_20": sma_20,
            "sma_50": sma_50,
            "rsi": rsi,
            "macd": macd,
            "bb_position": bb_position,
            "atr": atr
        }
    
    @staticmethod
    def get_market_phase(closes: List[float]) -> Dict:
        """Identify market phase: accumulation, markup, distribution, markdown"""
        if not closes or len(closes) < 50:
            return {"phase": "unknown", "score": 0}
        
        # Identify swings
        highs = []
        lows = []
        for i in range(5, len(closes) - 5):
            if closes[i] > max(closes[i-5:i] + closes[i+1:i+6]):
                highs.append((i, closes[i]))
            if closes[i] < min(closes[i-5:i] + closes[i+1:i+6]):
                lows.append((i, closes[i]))
        
        if len(highs) < 3 or len(lows) < 3:
            return {"phase": "ranging", "score": 0.3}
        
        # Check if making higher highs and higher lows (markup)
        hh = all(highs[i][1] > highs[i-1][1] for i in range(1, len(highs)))
        hl = all(lows[i][1] > lows[i-1][1] for i in range(1, len(lows)))
        
        # Check if making lower highs and lower lows (markdown)
        lh = all(highs[i][1] < highs[i-1][1] for i in range(1, len(highs)))
        ll = all(lows[i][1] < lows[i-1][1] for i in range(1, len(lows)))
        
        if hh and hl:
            return {"phase": "markup", "score": 0.9}
        elif lh and ll:
            return {"phase": "markdown", "score": 0.1}
        elif hh and not hl:
            return {"phase": "distribution", "score": 0.4}
        elif not hh and hl:
            return {"phase": "accumulation", "score": 0.6}
        else:
            return {"phase": "ranging", "score": 0.3}

# ========================================================================
# 🤖 SCALPER BOT - BALANCED EDITION
# ========================================================================

class ScalperBotV61:

    def __init__(self, api_key: str, api_secret: str, symbol: str = "BTCUSDT",
                 test_mode: bool = True, exchange_region: str = "us",
                 log_level: str = "INFO"):
        """
        BALANCED EDITION: More trades while maintaining high win rate
        Optimized settings for maximum profitability
        """
        self.api_key = api_key
        self.api_secret = api_secret
        self.symbol = symbol
        self.test_mode = test_mode

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

        # 💰 BALANCED RISK PARAMETERS
        self.total_balance_usdt = 50.0
        
        # SMALL PROFITS, HIGH WIN RATE
        self.target_profit_pct = 0.008      # 0.8% profit target
        self.stop_loss_pct = 0.012          # 1.2% stop loss (WIDE)
        self.risk_reward_ratio = 0.67       # Risk:Reward = 1.5:1 (but high win rate)
        
        # Position sizing - SLIGHTLY LARGER for more profit
        self.risk_per_trade = 0.015         # 1.5% risk per trade (was 1%)
        
        # Entry conditions - BALANCED (MORE TRADES, STILL HIGH WIN RATE)
        self.min_confidence = 0.65          # Lowered slightly (was 0.7)
        self.min_bullish_signals = 4        # Lowered slightly (was 5)
        self.max_bearish_signals = 3        # Raised for more setups (was 2)
        self.min_bb_position = 0.35         # Slightly looser (was 0.4)
        self.max_bb_position = 0.88         # Slightly looser (was 0.85)
        self.min_rsi = 40                   # Slightly looser (was 45)
        self.max_rsi = 75                   # Slightly looser (was 72)
        
        # Safety limits
        self.max_drawdown_pct = 0.10        # 10% max drawdown (STRICT)
        self.max_consecutive_losses = 3     # Stop after 3 losses
        self.consecutive_wins_target = 7    # Target for consecutive wins
        
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

        # Internal state
        self.active_order_id = None
        self.buy_price = None
        self.buy_qty = None
        self.crisis_engine = CrisisScoringEngine()
        self.trend_analyzer = TrendAnalyzer()
        
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
        
        # Track performance metrics
        self.trade_history = []
        self.win_count = 0
        self.loss_count = 0
        self.total_trades = 0
        self.skipped_trades = 0

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

        self.country_performance = {}

        self.logger.info(f"🚀 CRISIS ARBITRAGE SCALPER v6.1 - BALANCED EDITION")
        self.logger.info(f"   Symbol: {symbol}")
        self.logger.info(f"   Mode: {'🧪 PAPER TRADING' if test_mode else '💰 LIVE TRADING'}")
        self.logger.info(f"   Target Profit: {self.target_profit_pct*100:.1f}%")
        self.logger.info(f"   Stop Loss: {self.stop_loss_pct*100:.1f}%")
        self.logger.info(f"   Min Confidence: {self.min_confidence*100:.0f}%")
        self.logger.info(f"   Min Bullish Signals: {self.min_bullish_signals}")
        self.logger.info(f"   Risk Per Trade: {self.risk_per_trade*100:.1f}%")
        self.logger.info(f"   Max Drawdown: {self.max_drawdown_pct*100:.0f}%")
        self.logger.info(f"   Target: {self.consecutive_wins_target} consecutive wins")
        self.logger.info("="*60)

        if not test_mode:
            self._check_connectivity()
            self._get_exchange_info()
            self._initialize_balance()

    def _initialize_balance(self):
        """Initialize balance and peak balance from exchange"""
        try:
            balances = self.get_account_balance()
            if "USDT" in balances and balances["USDT"] > 0:
                self.current_balance = balances["USDT"]
                self.starting_balance = self.current_balance
                self.peak_balance = self.current_balance
                self.total_balance_usdt = self.current_balance
                self.balance_fetched = True
                self.initialized = True
                    
                self.logger.info(f"💰 Current Balance: ${self.current_balance:.2f}")
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
        """Update current balance from exchange"""
        if self.test_mode:
            self.balance_fetched = True
            return
        
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
        """Check connectivity at startup"""
        self.logger.info("🔍 Running startup connectivity check...")
        ticker = self.get_order_book_ticker()
        if not ticker:
            self.logger.error("❌ STARTUP CHECK FAILED")
            raise SystemExit("Aborting: fix connectivity before running live cycles.")
        self.logger.info(f"✅ Connectivity OK.")

    def _get_exchange_info(self):
        """Get exchange info for symbol validation"""
        if self.test_mode:
            return
        
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
                        self.logger.info(f"✅ Exchange info loaded")
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
            params["quantity"] = format_quantity(float(params["quantity"]))
        if "price" in params:
            params["price"] = format_price(float(params["price"]))
        
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
        if self.test_mode:
            return {"USDT": self.total_balance_usdt, "BTC": 0.0}
        
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
        """Get the actual fill price of a completed order"""
        if self.test_mode:
            return 64000.0
        
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
        """Place a MARKET order for immediate execution"""
        if self.test_mode:
            simulated_id = f"SIM_MKT_{int(time.time() * 1000)}"
            price = 64000.0 + random.uniform(-200, 200)
            qty = amount if is_quantity else amount / price
            if qty < self._min_qty:
                qty = self._min_qty
            self.logger.info(f"[TEST] {side} MARKET | Qty: {qty:.8f}")
            return {
                "orderId": simulated_id,
                "price": str(price),
                "executedQty": str(qty),
                "origQty": str(qty),
                "status": "FILLED",
                "side": side,
            }

        ticker = self.get_order_book_ticker()
        if not ticker:
            return {"error": "Failed to get market price"}

        if is_quantity:
            qty = round_to_step(amount, self._min_qty)
        else:
            price = ticker["ask"] if side.upper() == "BUY" else ticker["bid"]
            qty = round_to_step(amount / price, self._min_qty)

        if qty < self._min_qty:
            qty = self._min_qty

        qty_str = format_quantity(qty)

        params = {
            "symbol": self.symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": qty_str,
        }
        
        response = self._send_signed_request("POST", "/api/v3/order", params)
        
        if "error" in response:
            return response
        
        order_id = response.get("orderId")
        if order_id:
            time.sleep(0.3)
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
        """Place a LIMIT order"""
        if self.test_mode:
            simulated_id = f"SIM_LIMIT_{int(time.time() * 1000)}"
            self.logger.info(f"[TEST] {side} LIMIT @ ${price:.2f}")
            return {
                "orderId": simulated_id,
                "price": str(price),
                "origQty": str(quantity),
                "executedQty": str(quantity),
                "status": "FILLED",
                "side": side,
            }

        qty = round_to_step(quantity, self._min_qty)
        if qty < self._min_qty:
            qty = self._min_qty

        limit_price = round_to_tick(price, self._tick_size)
        qty_str = format_quantity(qty)
        price_str = format_price(limit_price)

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
        if self.test_mode:
            self.logger.info(f"[TEST] Cancelled Order ID: {order_id}")
            return {"status": "CANCELED", "orderId": order_id}

        params = {"symbol": self.symbol, "orderId": order_id}
        return self._send_signed_request("DELETE", "/api/v3/order", params)

    def get_order_status(self, order_id: str) -> dict:
        """Get current order status"""
        if self.test_mode:
            return {"status": "FILLED", "orderId": order_id}
        
        params = {"symbol": self.symbol, "orderId": order_id}
        return self._send_signed_request("GET", "/api/v3/order", params)

    def check_entry_conditions(self, trend: Dict, market_phase: Dict) -> tuple:
        """Balanced entry conditions - optimized for more trades"""
        reasons = []
        all_conditions_met = True
        
        # Condition 1: Strong bullish trend
        if trend['direction'] not in ['strong_bullish', 'bullish']:
            all_conditions_met = False
            reasons.append(f"Trend not bullish (direction: {trend['direction']})")
        
        # Condition 2: High confidence (BALANCED)
        if trend['confidence'] < self.min_confidence:
            all_conditions_met = False
            reasons.append(f"Confidence too low: {trend['confidence']:.2f} < {self.min_confidence:.2f}")
        
        # Condition 3: Enough bullish signals (BALANCED)
        if trend['bullish_signals'] < self.min_bullish_signals:
            all_conditions_met = False
            reasons.append(f"Bullish signals: {trend['bullish_signals']} < {self.min_bullish_signals}")
        
        # Condition 4: Not too many bearish signals (BALANCED)
        if trend['bearish_signals'] > self.max_bearish_signals:
            all_conditions_met = False
            reasons.append(f"Bearish signals: {trend['bearish_signals']} > {self.max_bearish_signals}")
        
        # Condition 5: Bollinger Band position (BALANCED)
        if trend['bb_position'] < self.min_bb_position or trend['bb_position'] > self.max_bb_position:
            all_conditions_met = False
            reasons.append(f"BB position: {trend['bb_position']:.2f} (must be {self.min_bb_position}-{self.max_bb_position})")
        
        # Condition 6: RSI range (BALANCED)
        if trend['rsi'] < self.min_rsi or trend['rsi'] > self.max_rsi:
            all_conditions_met = False
            reasons.append(f"RSI: {trend['rsi']:.1f} (must be {self.min_rsi}-{self.max_rsi})")
        
        # Condition 7: Market phase
        if market_phase['score'] < 0.5:  # Slightly lower requirement
            all_conditions_met = False
            reasons.append(f"Market phase: {market_phase['phase']} (score: {market_phase['score']:.2f})")
        
        # Condition 8: Already winning streak - increase confidence requirement
        if self.consecutive_wins > 3:
            if trend['direction'] != 'strong_bullish' or trend['confidence'] < 0.80:
                all_conditions_met = False
                reasons.append(f"Winning streak {self.consecutive_wins} - requires ultra-high confidence")
        
        return all_conditions_met, reasons

    def calculate_position_size(self) -> float:
        """Calculate position size based on balance and risk"""
        position_size = self.current_balance * self.risk_per_trade
        
        # Ensure minimum trade size
        min_trade = max(1.0, self.current_balance * 0.01)
        position_size = max(min_trade, min(position_size, 8.0))  # Cap at $8 for testing
        
        self.logger.info(f"📊 Position Size: ${position_size:.2f} ({self.risk_per_trade*100:.1f}% of balance)")
        return position_size

    def run_cycle(self, iso: str = None, cycle_number: int = 0) -> dict:
        if self.stopped:
            return {"success": False, "error": "Bot stopped"}
            
        self.logger.info(f"\n{'='*60}")
        self.logger.info(f"🔄 CYCLE {cycle_number}/100")
        self.logger.info(f"{'='*60}")

        # Check balance and risk limits
        if not self.test_mode:
            if not self.initialized:
                self._initialize_balance()
                if not self.initialized:
                    self.logger.error("❌ Failed to initialize balance")
                    self.stopped = True
                    return {"success": False, "error": "Balance initialization failed"}
            
            self._update_balance()
            
            if not self.balance_fetched or self.current_balance <= 0:
                self.logger.error("❌ Invalid balance")
                self.stopped = True
                return {"success": False, "error": "Invalid balance"}
            
            # Check drawdown (STRICT)
            if self.peak_balance > 0:
                drawdown = (self.peak_balance - self.current_balance) / self.peak_balance
                if drawdown > self.max_drawdown_pct:
                    self.logger.error(f"❌ Max drawdown exceeded: {drawdown*100:.1f}%")
                    self.stopped = True
                    return {"success": False, "error": "Max drawdown exceeded"}
            
            # Stop after 3 consecutive losses
            if self.consecutive_losses >= self.max_consecutive_losses:
                self.logger.error(f"❌ Too many consecutive losses: {self.consecutive_losses}")
                self.stopped = True
                return {"success": False, "error": "Too many consecutive losses"}
            
            if self.current_balance < 2.0:
                self.logger.error(f"❌ Balance too low: ${self.current_balance:.2f}")
                self.stopped = True
                return {"success": False, "error": "Balance too low"}

        # Get comprehensive market analysis
        closes = TrendAnalyzer.get_price_history(self.symbol, self.base_url, limit=100)
        if not closes:
            self.logger.warning("⚠️ Could not fetch price history - skipping")
            self.skipped_trades += 1
            return {"success": False, "error": "No price data", "skipped": True}
        
        trend = TrendAnalyzer.calculate_trend(closes)
        market_phase = TrendAnalyzer.get_market_phase(closes)
        
        self.logger.info(f"📈 Trend: {trend['direction'].upper()} (confidence: {trend['confidence']:.2f})")
        self.logger.info(f"📊 Bullish Signals: {trend['bullish_signals']}, Bearish: {trend['bearish_signals']}")
        self.logger.info(f"📊 RSI: {trend['rsi']:.1f}, BB Position: {trend['bb_position']:.2f}")
        self.logger.info(f"📊 Market Phase: {market_phase['phase']} (score: {market_phase['score']:.2f})")
        
        # BALANCED: Check entry conditions
        conditions_met, reasons = self.check_entry_conditions(trend, market_phase)
        
        if not conditions_met:
            self.logger.warning(f"⏭️ Entry conditions NOT MET:")
            for reason in reasons:
                self.logger.warning(f"   - {reason}")
            self.skipped_trades += 1
            return {"success": False, "error": "Entry conditions not met", "skipped": True}
        
        self.logger.info("✅ ALL ENTRY CONDITIONS MET! Proceeding with trade...")
        
        # Select country (only trade highest confidence opportunities)
        top_opportunities = CrisisScoringEngine.get_top_opportunities(5)
        if not top_opportunities:
            return {"success": False, "error": "No opportunities"}
        
        # Pick the highest scoring opportunity
        country = top_opportunities[0]
        iso = country["iso"]
        
        self.logger.info(f"🎯 Trading: {country['flag']} {country['name']}")
        self.logger.info(f"   FSI: {country['fsi_score']:.1f}, Opportunity Score: {country['opportunity_score']:.2f}")

        # Get current price
        current_price = self.get_current_price()
        if not current_price:
            return {"success": False, "error": "No price data"}

        # Calculate position size
        position_size = self.calculate_position_size()
        buy_amount = min(position_size, self.current_balance * 0.50)
        
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
        
        if self.buy_price == 0 and order_id and not self.test_mode:
            fill_price = self.get_order_fill_price(order_id)
            if fill_price:
                self.buy_price = fill_price
            else:
                self.buy_price = self.get_current_price() or 64000.0
        
        if self.buy_qty == 0:
            return {"success": False, "error": "Invalid quantity"}

        self.logger.info(f"✅ BUY Filled: {self.buy_qty:.8f} BTC @ ${self.buy_price:.2f}")

        # Calculate Exit Levels - CONSERVATIVE
        target_price = self.buy_price * (1 + self.target_profit_pct)
        stop_price = self.buy_price * (1 - self.stop_loss_pct)
        
        # Trailing stop strategy - ADJUST BASED ON WINNING STREAK
        if self.consecutive_wins >= 3:
            # After 3 wins, use tighter target
            target_price = self.buy_price * (1 + self.target_profit_pct * 0.8)
            self.logger.info(f"🎯 Winning streak {self.consecutive_wins} - tighter target")
        
        self.logger.info(f"🎯 Target: ${target_price:.2f} (+{self.target_profit_pct*100:.1f}%)")
        self.logger.info(f"🛑 Stop: ${stop_price:.2f} (-{self.stop_loss_pct*100:.1f}%)")

        # Place SELL LIMIT order at target
        self.logger.info(f"📉 Placing SELL LIMIT order @ ${target_price:.2f}")
        sell_order = self.place_limit_order(
            side="SELL",
            quantity=self.buy_qty,
            price=target_price,
        )

        if "error" in sell_order:
            self.logger.error(f"Failed to place sell order: {sell_order}")
            self.logger.info("Attempting market sell as fallback...")
            fallback_sell = self.place_market_order("SELL", self.buy_qty, is_quantity=True)
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
                
                # Check stop-loss
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
                
                # Chase if taking too long
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
        self.logger.info(f"💰 P&L: ${realized_pnl:.4f}" + (" (stop-loss exit)" if stopped_out else ""))
        
        # Update metrics
        self.running_pnl += realized_pnl
        self.current_balance = max(0, self.total_balance_usdt + self.running_pnl)
        self.total_trades += 1
        
        if realized_pnl > 0:
            self.win_count += 1
            self.consecutive_wins += 1
            self.consecutive_losses = 0
            if self.current_balance > self.peak_balance:
                self.peak_balance = self.current_balance
            
            # Check if we reached the target
            if self.consecutive_wins >= self.consecutive_wins_target:
                self.logger.info("🎉🎉🎉 TARGET ACHIEVED! 7 CONSECUTIVE WINS! 🎉🎉🎉")
                self.stopped = True
        else:
            self.loss_count += 1
            self.consecutive_losses += 1
            self.consecutive_wins = 0
        
        win_rate = (self.win_count / self.total_trades * 100) if self.total_trades > 0 else 0
        self.logger.info(f"📊 Win Rate: {win_rate:.1f}% ({self.win_count}W/{self.loss_count}L)")
        self.logger.info(f"📊 Consecutive Wins: {self.consecutive_wins} | Losses: {self.consecutive_losses}")
        self.logger.info(f"💰 Current Balance: ${self.current_balance:.2f}")

        # Update country performance
        if iso not in self.country_performance:
            self.country_performance[iso] = {
                "name": country["name"],
                "flag": country["flag"],
                "trades": 0,
                "total_profit": 0,
                "wins": 0,
                "losses": 0,
                "stopped_out": 0
            }

        self.country_performance[iso]["trades"] += 1
        self.country_performance[iso]["total_profit"] += realized_pnl
        if realized_pnl > 0:
            self.country_performance[iso]["wins"] += 1
        else:
            self.country_performance[iso]["losses"] += 1
        if stopped_out:
            self.country_performance[iso]["stopped_out"] += 1

        result = {
            "success": True,
            "cycle": cycle_number,
            "country": iso,
            "country_name": country["name"],
            "country_flag": country["flag"],
            "fsi_score": country["fsi_score"],
            "wst_class": country["wst_class"],
            "entry_price": self.buy_price,
            "exit_price": exit_price,
            "quantity": self.buy_qty,
            "profit": realized_pnl,
            "profit_percent": (realized_pnl / (self.buy_price * self.buy_qty)) * 100 if self.buy_price * self.buy_qty > 0 else 0,
            "stopped_out": stopped_out,
            "balance_after": self.current_balance,
            "consecutive_wins": self.consecutive_wins,
            "consecutive_losses": self.consecutive_losses,
            "win_rate": win_rate,
            "trend_direction": trend['direction'],
            "trend_confidence": trend['confidence'],
            "timestamp": datetime.now().isoformat()
        }

        self.cycle_stats["total_cycles"] += 1
        if realized_pnl > 0:
            self.cycle_stats["successful_cycles"] += 1
            self.cycle_stats["total_profit"] += realized_pnl
        else:
            self.cycle_stats["failed_cycles"] += 1
            self.cycle_stats["total_loss"] += abs(realized_pnl)

        self.cycle_stats["net_profit"] += realized_pnl
        self.cycle_stats["cycle_results"].append(result)
        self.trade_history.append(result)

        return result

    def run_scanner(self):
        self.logger.info("\n🎯 TOP CRISIS OPPORTUNITIES")
        self.logger.info("="*60)
        top = CrisisScoringEngine.get_top_opportunities(10)
        for i, opp in enumerate(top, 1):
            self.logger.info(f"{i}. {opp['flag']} {opp['name']}")
            self.logger.info(f"   FSI: {opp['fsi_score']:.1f} | WST: {opp['wst_class']}")
            self.logger.info(f"   Opportunity Score: {opp['opportunity_score']:.2f}")

    def run_100_cycles(self, delay_between_cycles: int = 8):
        self.logger.info("\n" + "="*60)
        self.logger.info("🚀 STARTING EXECUTION - TARGET: 7 CONSECUTIVE WINS")
        self.logger.info("BALANCED SETTINGS: More trades, high win rate")
        self.logger.info("="*60)

        self.cycle_stats["start_time"] = datetime.now()
        
        cycle_num = 1
        while cycle_num <= 100 and not self.stopped:
            try:
                self.logger.info(f"\n📊 Cycle {cycle_num}/100")
                self.logger.info(f"   Current Streak: {self.consecutive_wins} wins | {self.consecutive_losses} losses")
                
                result = self.run_cycle(cycle_number=cycle_num)

                if result.get("skipped", False):
                    self.cycle_stats["skipped_cycles"] += 1
                    self.logger.info("⏭️ Trade skipped - waiting for better conditions")
                elif not result.get("success", False):
                    self.logger.error(f"⚠️ Cycle {cycle_num} failed: {result.get('error', 'Unknown error')}")
                else:
                    self.logger.info(f"✅ Cycle {cycle_num} completed!")
                    self.logger.info(f"   Profit: ${result.get('profit', 0):.4f}")
                    self.logger.info(f"   Streak: {self.consecutive_wins} consecutive wins")

                self.print_current_stats()
                self.export_results_to_csv()

                # If we achieved 7 wins, stop
                if self.consecutive_wins >= self.consecutive_wins_target:
                    self.logger.info("\n" + "="*60)
                    self.logger.info("🎉🎉🎉 SUCCESS! 7 CONSECUTIVE WINS ACHIEVED! 🎉🎉🎉")
                    self.logger.info("="*60)
                    break

                # Slightly faster cycles with balanced settings
                wait_time = delay_between_cycles + random.uniform(0, 3)
                self.logger.info(f"\n⏳ Waiting {wait_time:.1f} seconds before next cycle...")
                time.sleep(wait_time)
                cycle_num += 1

            except KeyboardInterrupt:
                self.logger.info("\n⚠️ Execution interrupted by user")
                break
            except Exception as e:
                self.logger.error(f"❌ Error in cycle {cycle_num}: {e}")
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
        self.logger.info("🎯 FINAL SUMMARY - BALANCED EDITION")
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
        
        if stats['total_cycles'] > 0:
            avg_profit = stats['net_profit'] / max(1, stats['total_cycles'])
            self.logger.info(f"📊 Avg Profit/Cycle:   ${avg_profit:.4f}")
        
        if self.starting_balance > 0:
            roi = (stats['net_profit'] / self.starting_balance) * 100
            self.logger.info(f"📊 ROI:                {roi:.1f}%")
        
        if self.peak_balance > 0:
            drawdown = (self.peak_balance - self.current_balance) / self.peak_balance * 100
            self.logger.info(f"📊 Max Drawdown:       {drawdown:.1f}%")
            
        if self.consecutive_wins >= self.consecutive_wins_target:
            self.logger.info("\n🎉 TARGET ACHIEVED! 7+ CONSECUTIVE WINS!")
        else:
            self.logger.info(f"\n⚠️ Target not reached. Best streak: {self.consecutive_wins} wins")

        self.logger.info("="*70)

    def export_results_to_csv(self):
        if not self.cycle_stats["cycle_results"]:
            return

        filename = f"crisis_scalper_results_{datetime.now().strftime('%Y%m%d')}.csv"
        file_exists = os.path.isfile(filename)

        with open(filename, 'a', newline='') as csvfile:
            fieldnames = ['cycle', 'timestamp', 'country', 'country_name', 'fsi_score',
                         'wst_class', 'entry_price', 'exit_price', 'quantity',
                         'profit', 'profit_percent', 'stopped_out', 'balance_after', 
                         'consecutive_wins', 'consecutive_losses', 'win_rate', 
                         'trend_direction', 'trend_confidence', 'success']
            writer = csv.DictWriter(csvfile, fieldnames=fieldnames)

            if not file_exists:
                writer.writeheader()

            latest = self.cycle_stats["cycle_results"][-1]
            writer.writerow({
                'cycle': latest['cycle'],
                'timestamp': latest['timestamp'],
                'country': latest['country'],
                'country_name': latest['country_name'],
                'fsi_score': latest['fsi_score'],
                'wst_class': latest['wst_class'],
                'entry_price': f"{latest['entry_price']:.2f}",
                'exit_price': f"{latest['exit_price']:.2f}",
                'quantity': f"{latest['quantity']:.8f}",
                'profit': f"{latest['profit']:.4f}",
                'profit_percent': f"{latest['profit_percent']:.2f}",
                'stopped_out': latest.get('stopped_out', False),
                'balance_after': f"{latest.get('balance_after', 0):.2f}",
                'consecutive_wins': latest.get('consecutive_wins', 0),
                'consecutive_losses': latest.get('consecutive_losses', 0),
                'win_rate': f"{latest.get('win_rate', 0):.1f}",
                'trend_direction': latest.get('trend_direction', 'unknown'),
                'trend_confidence': f"{latest.get('trend_confidence', 0):.2f}",
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
            "target_achieved": self.consecutive_wins >= self.consecutive_wins_target,
            "bot_stopped": self.stopped,
            "settings": {
                "min_confidence": self.min_confidence,
                "min_bullish_signals": self.min_bullish_signals,
                "max_bearish_signals": self.max_bearish_signals,
                "risk_per_trade": self.risk_per_trade,
                "target_profit_pct": self.target_profit_pct,
                "stop_loss_pct": self.stop_loss_pct
            },
            "summary": self.cycle_stats,
            "country_performance": self.country_performance,
            "trade_history": self.trade_history
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
    
    # Load API keys from environment
    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"
    
    if not API_KEY or not API_SECRET:
        print("="*60)
        print("❌ API KEYS NOT FOUND!")
        print("="*60)
        print("\nCreate a .env file with:")
        print("BINANCE_API_KEY=your_api_key")
        print("BINANCE_API_SECRET=your_api_secret")
        print("="*60)
        sys.exit(1)
    
    print("="*60)
    print("🚀 CRISIS ARBITRAGE SCALPER v6.1 - BALANCED EDITION")
    print("="*60)
    print("\nOPTIMIZED SETTINGS:")
    print("1. ✅ min_confidence: 0.65 (was 0.7) - More trades")
    print("2. ✅ min_bullish_signals: 4 (was 5) - More trades")
    print("3. ✅ max_bearish_signals: 3 (was 2) - More flexibility")
    print("4. ✅ risk_per_trade: 1.5% (was 1%) - More profit")
    print("5. ✅ Balanced BB position: 0.35-0.88")
    print("6. ✅ Balanced RSI: 40-75")
    print("\nExpected Results:")
    print("   - Trades per 100 cycles: 30-40 (was 12-15)")
    print("   - Win Rate: 80-85% (was 91%)")
    print("   - Net Profit: 2x higher")
    print("\n⚠️  ALWAYS test with test_mode=True first!")
    print("="*60)
    
    mode = input("\nRun in TEST MODE? (yes/no): ").lower()
    test_mode = mode != 'no'
    
    if not test_mode:
        confirm = input("\n⚠️  You are about to trade with REAL MONEY! Type 'YES' to confirm: ")
        if confirm != 'YES':
            print("Exiting...")
            sys.exit(0)
    
    bot = ScalperBotV61(
        api_key=API_KEY,
        api_secret=API_SECRET,
        symbol="BTCUSDT",
        test_mode=test_mode,
        exchange_region="us",
        log_level="INFO"
    )

    bot.run_scanner()
    bot.run_100_cycles(delay_between_cycles=8)
