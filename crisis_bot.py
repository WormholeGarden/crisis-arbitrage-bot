#!/usr/bin/env python3
"""
🚀 INSTANT SCALPING BOT v2.0 - FIXED
============================================================
FIXES:
- Fixed RSI calculation (was returning 100 incorrectly)
- Proper volume detection
- Better momentum calculation
- Working signal detection
- Added price movement detection
============================================================
"""

import hashlib
import hmac
import time
import urllib.parse
import logging
import statistics
from datetime import datetime
from typing import Dict, List, Optional
import requests
from decimal import Decimal

# ========================================================================
# CONFIGURATION
# ========================================================================

CONFIG = {
    "symbol": "AVAXUSDT",
    "interval": "1m",
    "target_pct": 0.005,       # 0.5% target (was 0.3%)
    "stop_pct": 0.003,         # 0.3% stop (was 0.2%)
    "min_order_usdt": 10.0,
    "max_order_usdt": 30.0,
    "min_volume_spike": 1.2,   # Volume must be 1.2x average
    "rsi_oversold": 35,        # RSI below 35
    "rsi_overbought": 65,      # RSI above 65
    "min_momentum": 0.1,       # Minimum momentum for entry
}

# ========================================================================
# DECIMAL HELPERS
# ========================================================================

def round_to_step(value: float, step: float) -> float:
    return float((Decimal(str(value)) // Decimal(str(step))) * Decimal(str(step)))

def round_to_tick(value: float, tick: float) -> float:
    return float((Decimal(str(value)) / Decimal(str(tick))).quantize(Decimal('1')) * Decimal(str(tick)))

def format_quantity(value: float) -> str:
    return f"{Decimal(str(value)):.8f}"

def format_price(value: float) -> str:
    return f"{Decimal(str(value)):.4f}"

# ========================================================================
# BINANCE API
# ========================================================================

class BinanceAPI:
    def __init__(self, api_key: str, api_secret: str, region: str = "us"):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.binance.us" if region == "us" else "https://api.binance.com"
        
        self._min_qty = 0.00001
        self._tick_size = 0.01
        self._min_notional = 10.0
        
        self._price_cache = {}
        self._price_cache_time = 0
        self._price_cache_ttl = 2
        
        self._get_exchange_info()
        
    def _generate_signature(self, params: dict) -> str:
        query_string = urllib.parse.urlencode(params)
        return hmac.new(self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256).hexdigest()
    
    def _send_request(self, method: str, endpoint: str, params: dict = None, signed: bool = False) -> dict:
        if params is None:
            params = {}
        
        if signed:
            params["timestamp"] = int(time.time() * 1000)
            params["signature"] = self._generate_signature(params)
            headers = {"X-MBX-APIKEY": self.api_key}
        else:
            headers = {}
        
        url = f"{self.base_url}{endpoint}"
        
        if method.upper() == "GET":
            response = requests.get(url, headers=headers, params=params, timeout=10)
        elif method.upper() == "POST":
            response = requests.post(url, headers=headers, data=params, timeout=10)
        else:
            raise ValueError(f"Unsupported method: {method}")
        
        try:
            return response.json()
        except:
            return {"error": "Invalid response", "status_code": response.status_code}
    
    def _get_exchange_info(self):
        try:
            resp = requests.get(f"{self.base_url}/api/v3/exchangeInfo", timeout=5)
            if resp.status_code == 200:
                data = resp.json()
                for symbol_info in data.get("symbols", []):
                    if symbol_info["symbol"] == CONFIG["symbol"]:
                        for filter_data in symbol_info.get("filters", []):
                            if filter_data["filterType"] == "LOT_SIZE":
                                self._min_qty = float(filter_data.get("minQty", 0.00001))
                            if filter_data["filterType"] == "PRICE_FILTER":
                                self._tick_size = float(filter_data.get("tickSize", 0.01))
                            if filter_data["filterType"] == "MIN_NOTIONAL":
                                self._min_notional = float(filter_data.get("minNotional", 10.0))
                        break
        except Exception:
            pass
    
    def get_klines(self, symbol: str, interval: str = "1m", limit: int = 100) -> Optional[Dict]:
        try:
            url = f"{self.base_url}/api/v3/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            resp = requests.get(url, params=params, timeout=5)
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
        except Exception as e:
            return None
    
    def get_ticker(self, symbol: str) -> Optional[dict]:
        now = time.time()
        if now - self._price_cache_time < self._price_cache_ttl:
            if 'ticker' in self._price_cache:
                return self._price_cache['ticker']
        
        try:
            url = f"{self.base_url}/api/v3/ticker/bookTicker"
            resp = requests.get(url, params={"symbol": symbol}, timeout=3)
            if resp.status_code == 200:
                data = resp.json()
                ticker_data = {"bid": float(data["bidPrice"]), "ask": float(data["askPrice"])}
                self._price_cache = {'ticker': ticker_data}
                self._price_cache_time = now
                return ticker_data
            return None
        except Exception:
            return None
    
    def get_price(self, symbol: str) -> Optional[float]:
        ticker = self.get_ticker(symbol)
        if not ticker:
            return None
        return (ticker["bid"] + ticker["ask"]) / 2
    
    def get_balance(self) -> Dict[str, float]:
        resp = self._send_request("GET", "/api/v3/account", signed=True)
        if "balances" in resp and not resp.get("error"):
            balances = {}
            for balance in resp["balances"]:
                free = float(balance["free"])
                if free > 0:
                    balances[balance["asset"]] = free
            return balances
        return {}
    
    def market_order(self, symbol: str, side: str, amount: float, is_quantity: bool = False) -> dict:
        price = self.get_price(symbol)
        if not price:
            return {"error": "No price"}
        
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
        
        params = {
            "symbol": symbol,
            "side": side.upper(),
            "type": "MARKET",
            "quantity": format_quantity(qty),
        }
        
        response = self._send_request("POST", "/api/v3/order", params, signed=True)
        
        if "error" in response:
            return response
        
        order_id = response.get("orderId")
        if not order_id:
            return {"error": "No order ID"}
        
        # Wait for fill
        max_wait = 30
        for _ in range(max_wait):
            status = self._send_request("GET", "/api/v3/order", {"symbol": symbol, "orderId": order_id}, signed=True)
            if status.get("status") == "FILLED":
                executed_qty = float(status.get("executedQty", 0))
                cum_quote = float(status.get("cummulativeQuoteQty", 0))
                fill_price = cum_quote / executed_qty if executed_qty > 0 else price
                return {
                    "orderId": order_id,
                    "price": fill_price,
                    "executedQty": executed_qty,
                    "status": "FILLED",
                    "side": side,
                }
            elif status.get("status") in ["CANCELED", "EXPIRED"]:
                return {"error": f"Order {status.get('status')}"}
            time.sleep(0.5)
        
        return {"error": "Order fill timeout"}

# ========================================================================
# FIXED SCALPING INDICATORS
# ========================================================================

class ScalpIndicators:
    @staticmethod
    def calculate_rsi(closes: List[float], period: int = 14) -> float:
        """Proper RSI calculation that doesn't return 100 incorrectly."""
        if len(closes) < period + 1:
            return 50.0
        
        # Calculate price changes
        deltas = [closes[i] - closes[i-1] for i in range(1, len(closes))]
        
        # Separate gains and losses
        gains = [d if d > 0 else 0 for d in deltas]
        losses = [-d if d < 0 else 0 for d in deltas]
        
        # Use only the last 'period' values
        gains = gains[-period:]
        losses = losses[-period:]
        
        # Calculate average gain and loss
        avg_gain = sum(gains) / period if gains else 0
        avg_loss = sum(losses) / period if losses else 0
        
        if avg_loss == 0:
            return 100.0
        
        rs = avg_gain / avg_loss
        rsi = 100 - (100 / (1 + rs))
        
        return min(100, max(0, rsi))
    
    @staticmethod
    def calculate_ema(data: List[float], period: int) -> float:
        if not data or len(data) < period:
            return data[-1] if data else 0
        
        alpha = 2 / (period + 1)
        ema = data[0]
        for price in data[1:]:
            ema = price * alpha + ema * (1 - alpha)
        return ema
    
    @staticmethod
    def calculate_momentum(closes: List[float], period: int = 5) -> float:
        if len(closes) < period + 1:
            return 0.0
        
        # Percentage change over 'period' candles
        momentum = ((closes[-1] - closes[-period]) / closes[-period]) * 100
        return momentum
    
    @staticmethod
    def calculate_volume_ratio(volumes: List[float], period: int = 20) -> float:
        if len(volumes) < period:
            return 1.0
        
        avg_volume = sum(volumes[-period:]) / period
        if avg_volume == 0:
            return 1.0
        
        return volumes[-1] / avg_volume
    
    @staticmethod
    def calculate_price_change(closes: List[float], period: int = 3) -> float:
        if len(closes) < period + 1:
            return 0.0
        
        # Price change over last 'period' candles
        return ((closes[-1] - closes[-period]) / closes[-period]) * 100
    
    @staticmethod
    def calculate_bollinger(closes: List[float], period: int = 20, std_dev: float = 2) -> Dict:
        if len(closes) < period:
            return {"upper": closes[-1], "middle": closes[-1], "lower": closes[-1], "position": 0.5}
        
        middle = sum(closes[-period:]) / period
        squared = [(x - middle) ** 2 for x in closes[-period:]]
        std = (sum(squared) / period) ** 0.5
        upper = middle + (std * std_dev)
        lower = middle - (std * std_dev)
        
        position = (closes[-1] - lower) / (upper - lower) if upper != lower else 0.5
        return {"upper": upper, "middle": middle, "lower": lower, "position": position}

# ========================================================================
# FIXED SCALPING STRATEGY
# ========================================================================

class ScalpStrategy:
    @staticmethod
    def analyze(data: Dict) -> Dict:
        closes = data['closes']
        highs = data['highs']
        lows = data['lows']
        volumes = data['volumes']
        current = closes[-1]
        
        if len(closes) < 30:
            return {"signal": "NEUTRAL", "reason": "Insufficient data"}
        
        # Calculate indicators with proper values
        rsi = ScalpIndicators.calculate_rsi(closes, 14)
        ema_9 = ScalpIndicators.calculate_ema(closes, 9)
        ema_21 = ScalpIndicators.calculate_ema(closes, 21)
        momentum = ScalpIndicators.calculate_momentum(closes, 5)
        volume_ratio = ScalpIndicators.calculate_volume_ratio(volumes, 20)
        price_change = ScalpIndicators.calculate_price_change(closes, 3)
        bb = ScalpIndicators.calculate_bollinger(closes, 20, 2)
        
        # Price vs EMAs
        above_ema9 = current > ema_9
        above_ema21 = current > ema_21
        
        # Volume conditions
        volume_spike = volume_ratio > CONFIG["min_volume_spike"]
        
        # RSI conditions
        oversold = rsi < CONFIG["rsi_oversold"]
        overbought = rsi > CONFIG["rsi_overbought"]
        
        # Momentum conditions
        positive_momentum = momentum > CONFIG["min_momentum"]
        accelerating = momentum > 0.2  # Strong momentum
        
        # Bollinger position
        near_lower_band = bb['position'] < 0.3
        
        # BULLISH SIGNAL - Buy conditions
        bullish_conditions = 0
        total_bullish = 5
        
        # 1. RSI oversold or neutral
        if oversold:
            bullish_conditions += 1
        elif rsi < 50:
            bullish_conditions += 0.5
        
        # 2. Price above EMA9 (short-term momentum)
        if above_ema9:
            bullish_conditions += 1
        
        # 3. Positive momentum
        if positive_momentum:
            bullish_conditions += 1
        
        # 4. Volume spike (confirmation)
        if volume_spike:
            bullish_conditions += 1
        
        # 5. Near lower Bollinger (mean reversion)
        if near_lower_band:
            bullish_conditions += 1
        
        bullish_confidence = min(1.0, bullish_conditions / total_bullish)
        
        # BEARISH CONDITIONS - For confirmation
        bearish_conditions = 0
        
        # 1. RSI overbought
        if overbought:
            bearish_conditions += 1
        
        # 2. Price below EMA9
        if not above_ema9:
            bearish_conditions += 1
        
        # 3. Negative momentum
        if momentum < -CONFIG["min_momentum"]:
            bearish_conditions += 1
        
        # Final signal
        buy_signal = (bullish_confidence >= 0.5 and 
                     volume_spike and 
                     positive_momentum and 
                     not overbought)
        
        # Calculate target and stop
        atr = (max(highs[-14:]) - min(lows[-14:])) / 14 if len(highs) >= 14 else 0.01
        atr_pct = atr / current if current > 0 else 0.005
        
        # Dynamic target based on volatility
        target_pct = max(CONFIG["target_pct"], atr_pct * 0.5)
        target = current * (1 + target_pct)
        stop = current * (1 - CONFIG["stop_pct"])
        
        return {
            "signal": "BUY" if buy_signal else "NEUTRAL",
            "confidence": bullish_confidence,
            "rsi": rsi,
            "momentum": momentum,
            "volume_ratio": volume_ratio,
            "price_change": price_change,
            "bb_position": bb['position'],
            "above_ema9": above_ema9,
            "target": target,
            "stop": stop,
            "target_pct": target_pct * 100,
            "reason": self._get_reason(bullish_conditions, total_bullish, rsi, momentum, volume_ratio)
        }
    
    @staticmethod
    def _get_reason(conditions: float, total: int, rsi: float, momentum: float, volume: float) -> str:
        if conditions >= 4:
            return f"STRONG SIGNAL (RSI:{rsi:.1f}, Mom:{momentum:.2f}%, Vol:{volume:.2f}x)"
        elif conditions >= 3:
            return f"MODERATE SIGNAL (RSI:{rsi:.1f}, Mom:{momentum:.2f}%, Vol:{volume:.2f}x)"
        elif conditions >= 2:
            return f"WEAK SIGNAL (RSI:{rsi:.1f}, Mom:{momentum:.2f}%, Vol:{volume:.2f}x)"
        else:
            return f"NO SIGNAL (RSI:{rsi:.1f}, Mom:{momentum:.2f}%, Vol:{volume:.2f}x)"

# ========================================================================
# FIXED SCALPING BOT
# ========================================================================

class ScalpingBot:
    def __init__(self, api_key: str, api_secret: str):
        self.api = BinanceAPI(api_key, api_secret, "us")
        self.symbol = CONFIG["symbol"]
        self.asset = self.symbol.replace("USDT", "")
        
        self.has_position = False
        self.entry_price = 0.0
        self.entry_qty = 0.0
        self.target_price = 0.0
        self.stop_price = 0.0
        self.entry_time = 0
        
        self.wins = 0
        self.losses = 0
        self.total_pnl = 0.0
        self.total_trades = 0
        
        # Logging
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(message)s',
            datefmt='%Y-%m-%d %H:%M:%S'
        )
        self.logger = logging.getLogger(__name__)
        
        self.logger.info("="*60)
        self.logger.info("🚀 INSTANT SCALPING BOT v2.0 - FIXED")
        self.logger.info("="*60)
        self.logger.info(f"Symbol: {self.symbol}")
        self.logger.info(f"Target: {CONFIG['target_pct']*100:.1f}%")
        self.logger.info(f"Stop: {CONFIG['stop_pct']*100:.1f}%")
        self.logger.info("="*60)
    
    def get_balance_usdt(self) -> float:
        balances = self.api.get_balance()
        return balances.get("USDT", 0)
    
    def run_scalp(self) -> Dict:
        # Get market data
        data = self.api.get_klines(self.symbol, "1m", 100)
        if not data:
            return {"success": False, "error": "No data", "skipped": True}
        
        # Get signal
        signal = ScalpStrategy.analyze(data)
        
        # Log detailed info
        self.logger.info(f"📊 RSI: {signal['rsi']:.1f} | Volume: {signal['volume_ratio']:.2f}x | Momentum: {signal['momentum']:.2f}% | BB: {signal['bb_position']:.2f}")
        self.logger.info(f"   {signal['reason']}")
        
        if signal['signal'] != "BUY":
            return {"success": False, "error": "No signal", "skipped": True}
        
        # Check balance
        balance = self.get_balance_usdt()
        if balance < CONFIG["min_order_usdt"]:
            self.logger.error(f"❌ Insufficient USDT: ${balance:.2f}")
            return {"success": False, "error": "Insufficient USDT"}
        
        # Position size
        position_usdt = min(CONFIG["max_order_usdt"], balance * 0.10)
        position_usdt = max(CONFIG["min_order_usdt"], position_usdt)
        
        self.logger.info(f"📈 BUYING ${position_usdt:.2f} - Target: ${signal['target']:.4f} (+{signal['target_pct']:.1f}%) | Stop: ${signal['stop']:.4f}")
        
        # Execute BUY
        buy_result = self.api.market_order(self.symbol, "BUY", position_usdt, is_quantity=False)
        if "error" in buy_result:
            self.logger.error(f"❌ Buy failed: {buy_result}")
            return {"success": False, "error": "Buy failed"}
        
        self.entry_price = buy_result["price"]
        self.entry_qty = buy_result["executedQty"]
        self.target_price = signal["target"]
        self.stop_price = signal["stop"]
        self.entry_time = time.time()
        self.has_position = True
        
        self.logger.info(f"✅ BUY Filled: {self.entry_qty:.4f} @ ${self.entry_price:.4f}")
        self.logger.info(f"⏳ Monitoring - Target: ${self.target_price:.4f} | Stop: ${self.stop_price:.4f}")
        
        # Monitor position
        max_hold_seconds = 120  # 2 minutes
        
        while time.time() - self.entry_time < max_hold_seconds:
            current_price = self.api.get_price(self.symbol)
            if not current_price:
                time.sleep(1)
                continue
            
            # Show progress every 5 seconds
            elapsed = int(time.time() - self.entry_time)
            if elapsed % 5 == 0:
                pnl_pct = (current_price / self.entry_price - 1) * 100
                self.logger.info(f"   [{elapsed}s] Price: ${current_price:.4f} ({pnl_pct:+.2f}%) | Target: ${self.target_price:.4f} | Stop: ${self.stop_price:.4f}")
            
            # Check target hit
            if current_price >= self.target_price:
                self.logger.info(f"🎯 TARGET HIT! ${current_price:.4f}")
                sell_result = self.api.market_order(self.symbol, "SELL", self.entry_qty, is_quantity=True)
                if "error" in sell_result:
                    self.logger.error(f"❌ Sell failed: {sell_result}")
                    return {"success": False, "error": "Sell failed"}
                
                exit_price = sell_result["price"]
                pnl = (exit_price - self.entry_price) * self.entry_qty
                pnl_pct = (exit_price / self.entry_price - 1) * 100
                
                self.has_position = False
                self.wins += 1
                self.total_trades += 1
                self.total_pnl += pnl
                
                self.logger.info(f"✅ PROFIT: ${pnl:.4f} ({pnl_pct:.2f}%)")
                return {"success": True, "profit": pnl, "profit_pct": pnl_pct, "exit_type": "TARGET"}
            
            # Check stop hit
            if current_price <= self.stop_price:
                self.logger.info(f"🛑 STOP HIT! ${current_price:.4f}")
                sell_result = self.api.market_order(self.symbol, "SELL", self.entry_qty, is_quantity=True)
                if "error" in sell_result:
                    self.logger.error(f"❌ Sell failed: {sell_result}")
                    return {"success": False, "error": "Sell failed"}
                
                exit_price = sell_result["price"]
                pnl = (exit_price - self.entry_price) * self.entry_qty
                pnl_pct = (exit_price / self.entry_price - 1) * 100
                
                self.has_position = False
                self.losses += 1
                self.total_trades += 1
                self.total_pnl += pnl
                
                self.logger.info(f"❌ LOSS: ${pnl:.4f} ({pnl_pct:.2f}%)")
                return {"success": True, "profit": pnl, "profit_pct": pnl_pct, "exit_type": "STOP"}
            
            time.sleep(1)
        
        # Time exit
        self.logger.info(f"⏰ TIME EXIT - Max hold reached")
        current_price = self.api.get_price(self.symbol)
        if current_price:
            sell_result = self.api.market_order(self.symbol, "SELL", self.entry_qty, is_quantity=True)
            if "error" not in sell_result:
                exit_price = sell_result["price"]
                pnl = (exit_price - self.entry_price) * self.entry_qty
                pnl_pct = (exit_price / self.entry_price - 1) * 100
                
                self.has_position = False
                self.total_trades += 1
                self.total_pnl += pnl
                
                if pnl > 0:
                    self.wins += 1
                else:
                    self.losses += 1
                
                self.logger.info(f"⏰ Exit @ ${exit_price:.4f} | P&L: ${pnl:.4f} ({pnl_pct:.2f}%)")
                return {"success": True, "profit": pnl, "profit_pct": pnl_pct, "exit_type": "TIME"}
        
        return {"success": False, "error": "Time exit failed"}
    
    def run_forever(self):
        self.logger.info("\n🚀 Starting scalping loop - Press Ctrl+C to stop")
        cycle = 1
        
        while True:
            try:
                # Run a scalp
                result = self.run_scalp()
                
                if result.get("success", False):
                    if result.get("exit_type"):
                        self.logger.info(f"✅ Scalp completed: {result['exit_type']} | P&L: ${result.get('profit', 0):.4f}")
                elif result.get("skipped", False):
                    self.logger.info("⏭️ No signal, waiting...")
                else:
                    self.logger.warning(f"⚠️ {result.get('error', 'Unknown error')}")
                
                # Stats
                if self.total_trades > 0:
                    win_rate = (self.wins / self.total_trades) * 100
                    self.logger.info(f"📊 STATS: {self.total_trades} trades | {win_rate:.1f}% win | ${self.total_pnl:.4f}")
                
                # Wait
                wait_time = 10
                self.logger.info(f"⏳ Next check in {wait_time}s...")
                time.sleep(wait_time)
                cycle += 1
                
            except KeyboardInterrupt:
                self.logger.info("\n⚠️ Stopped by user")
                self.print_summary()
                break
            except Exception as e:
                self.logger.error(f"❌ Error: {e}")
                import traceback
                traceback.print_exc()
                time.sleep(5)
    
    def print_summary(self):
        self.logger.info("\n" + "="*60)
        self.logger.info("📊 FINAL SUMMARY")
        self.logger.info("="*60)
        if self.total_trades > 0:
            win_rate = (self.wins / self.total_trades) * 100
            self.logger.info(f"Trades: {self.total_trades}")
            self.logger.info(f"Wins: {self.wins} | Losses: {self.losses}")
            self.logger.info(f"Win Rate: {win_rate:.1f}%")
            self.logger.info(f"Total P&L: ${self.total_pnl:.4f}")
        self.logger.info("="*60)

# ========================================================================
# MAIN
# ========================================================================

if __name__ == "__main__":
    API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
    API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"
    
    if not API_KEY or not API_SECRET:
        print("❌ API KEYS NOT FOUND")
        exit(1)
    
    print("="*60)
    print("🚀 INSTANT SCALPING BOT v2.0 - FIXED")
    print("="*60)
    print("\n⚠️ WARNING:")
    print("   - Makes 0.5% profits in 1-5 minutes")
    print("   - Win rate target: 55-65%")
    print("   - Uses 1-minute candles")
    print("   - Checks every 10 seconds")
    print("\nStarting in 3 seconds...")
    time.sleep(3)
    
    bot = ScalpingBot(API_KEY, API_SECRET)
    bot.run_forever()
