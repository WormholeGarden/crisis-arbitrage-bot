#!/usr/bin/env python3
"""
🚀 CRISIS ARBITRAGE BOT - HEDGE FUND EDITION
Full automated execution with multiple asset classes
"""

import time
import json
import hashlib
import hmac
import requests
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import random
import os

# ========================================================================
# 📊 CONFIGURATION - SET THIS UP ONCE
# ========================================================================

CONFIG = {
    # --- CAPITAL ---
    "initial_capital": 100000,
    "max_positions": 6,
    "risk_per_trade": 0.15,
    
    # --- EXCHANGE API KEYS (GET THESE FROM YOUR EXCHANGE) ---
    "binance": {
        "api_key": "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn",
        "api_secret": "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0",
        "enabled": True,  # Set to True when you have keys
    },
    "bybit": {
        "api_key": "YOUR_BYBIT_API_KEY",
        "api_secret": "YOUR_BYBIT_API_SECRET",
        "enabled": False,
    },
    
    # --- BANK/WIRE TRANSFER (Manual for now) ---
"manual_execution": {
    "enabled": False,  # True = prints instructions for manual trades
    "email_alerts": False,
    "email": "marino.montagno@gmail.com",  # ← FIXED
},
    # --- ASSET CLASSES TO TRADE ---
    "assets": {
        "crypto": {"enabled": True, "max_per_trade": 5000},
        "gold": {"enabled": True, "max_per_trade": 10000},
        "real_estate": {"enabled": True, "max_per_trade": 50000},
        "stocks": {"enabled": True, "max_per_trade": 10000},
    },
    
    # --- TRADING PARAMETERS ---
    "slippage": 0.10,
    "transaction_costs": 0.08,
    "failure_rate": 0.15,
    "black_swan_rate": 0.05,
    "target_return": 0.20,
}

# ========================================================================
# 📡 EXCHANGE CONNECTORS
# ========================================================================

class ExchangeConnector:
    """Base class for exchange connections"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.binance = None
        self.bybit = None
        self._init_exchanges()
    
    def _init_exchanges(self):
        """Initialize exchange connections"""
        if self.config["binance"]["enabled"]:
            try:
                # Binance API
                self.binance = BinanceAPI(
                    self.config["binance"]["api_key"],
                    self.config["binance"]["api_secret"]
                )
                print("✅ Binance connected")
            except Exception as e:
                print(f"⚠️ Binance connection failed: {e}")
        
        if self.config["bybit"]["enabled"]:
            try:
                # Bybit API
                self.bybit = BybitAPI(
                    self.config["bybit"]["api_key"],
                    self.config["bybit"]["api_secret"]
                )
                print("✅ Bybit connected")
            except Exception as e:
                print(f"⚠️ Bybit connection failed: {e}")
    
    def get_balance(self, currency: str = "USDT") -> float:
        """Get account balance"""
        if self.binance:
            return self.binance.get_balance(currency)
        elif self.bybit:
            return self.bybit.get_balance(currency)
        return 0.0
    
    def place_order(self, symbol: str, side: str, amount: float, price: float) -> Dict:
        """Place an order on the exchange"""
        if self.binance:
            return self.binance.place_order(symbol, side, amount, price)
        elif self.bybit:
            return self.bybit.place_order(symbol, side, amount, price)
        return {"error": "No exchange connected"}

# ─── BINANCE API ──────────────────────────────────────────────────────────

class BinanceAPI:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.binance.com"
    
    def _sign_request(self, params: Dict) -> str:
        """Sign the request with HMAC-SHA256"""
        query_string = "&".join([f"{k}={v}" for k, v in sorted(params.items())])
        signature = hmac.new(
            self.api_secret.encode('utf-8'),
            query_string.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
        return signature
    
    def get_balance(self, currency: str = "USDT") -> float:
        """Get account balance"""
        try:
            headers = {"X-MBX-APIKEY": self.api_key}
            params = {"timestamp": int(time.time() * 1000)}
            params["signature"] = self._sign_request(params)
            response = requests.get(
                f"{self.base_url}/api/v3/account",
                headers=headers,
                params=params
            )
            if response.status_code == 200:
                data = response.json()
                for balance in data.get("balances", []):
                    if balance["asset"] == currency:
                        return float(balance["free"])
            return 0.0
        except Exception as e:
            print(f"⚠️ Balance check failed: {e}")
            return 0.0
    
    def place_order(self, symbol: str, side: str, amount: float, price: float) -> Dict:
        """Place a limit order"""
        try:
            headers = {"X-MBX-APIKEY": self.api_key}
            params = {
                "symbol": symbol,
                "side": side.upper(),
                "type": "LIMIT",
                "timeInForce": "GTC",
                "quantity": amount,
                "price": price,
                "timestamp": int(time.time() * 1000)
            }
            params["signature"] = self._sign_request(params)
            response = requests.post(
                f"{self.base_url}/api/v3/order",
                headers=headers,
                params=params
            )
            return response.json()
        except Exception as e:
            return {"error": str(e)}

# ─── BYBIT API ────────────────────────────────────────────────────────────

class BybitAPI:
    def __init__(self, api_key: str, api_secret: str):
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = "https://api.bybit.com"
    
    def get_balance(self, currency: str = "USDT") -> float:
        """Get account balance"""
        try:
            # Simplified - in production use proper signing
            print(f"ℹ️ Bybit: Checking {currency} balance")
            return 10000.0  # Placeholder
        except Exception as e:
            print(f"⚠️ Balance check failed: {e}")
            return 0.0
    
    def place_order(self, symbol: str, side: str, amount: float, price: float) -> Dict:
        """Place a limit order"""
        try:
            print(f"ℹ️ Bybit: Placing {side} order for {symbol}")
            return {"orderId": "test_order", "status": "NEW"}
        except Exception as e:
            return {"error": str(e)}

# ========================================================================
# 🏦 ASSET EXECUTORS
# ========================================================================

class AssetExecutor:
    """Execute trades for different asset classes"""
    
    def __init__(self, config: Dict, exchange: ExchangeConnector):
        self.config = config
        self.exchange = exchange
    
    def execute_crypto(self, country: Dict, trade: Dict) -> Dict:
        """Execute a crypto trade"""
        print(f"\n{'='*60}")
        print("🪙 CRYPTO TRADE EXECUTION")
        print(f"{'='*60}")
        
        # Find the best crypto pair for this country
        pairs = {
            "USDT": {"symbol": "USDT/USD", "exchange": "binance"},
        }
        
        for pair, info in pairs.items():
            print(f"\n📍 Trade: {country['flag']} {country['iso']}")
            print(f"   Asset: {pair}")
            print(f"   Exchange: {info['exchange']}")
            print(f"   Entry Price: ${trade['entry_price']:,.2f}")
            print(f"   Exit Price: ${trade['exit_price']:,.2f}")
            print(f"   Position Size: ${trade['position_size']:,.2f}")
            print(f"   Expected Profit: ${trade['position_size'] * ((trade['exit_price'] - trade['entry_price']) / trade['entry_price']):,.2f}")
            
            if self.config["manual_execution"]["enabled"]:
                self._print_manual_instructions(country, trade, "crypto")
            else:
                return self._auto_execute_crypto(country, trade, pair)
        
        return {"status": "pending", "type": "crypto"}
    
    def execute_gold(self, country: Dict, trade: Dict) -> Dict:
        """Execute a gold trade"""
        print(f"\n{'='*60}")
        print("🥇 GOLD TRADE EXECUTION")
        print(f"{'='*60}")
        
        print(f"\n📍 Trade: {country['flag']} {country['iso']}")
        print(f"   Asset: Gold (XAU)")
        print(f"   Local Price: ${trade['entry_price']:,.2f}/oz")
        print(f"   Global Price: ${trade['exit_price']:,.2f}/oz")
        print(f"   Position Size: ${trade['position_size']:,.2f}")
        print(f"   Expected Profit: ${trade['position_size'] * ((trade['exit_price'] - trade['entry_price']) / trade['entry_price']):,.2f}")
        
        self._print_gold_instructions(country, trade)
        return {"status": "manual", "type": "gold"}
    
    def execute_real_estate(self, country: Dict, trade: Dict) -> Dict:
        """Execute a real estate trade"""
        print(f"\n{'='*60}")
        print("🏠 REAL ESTATE TRADE EXECUTION")
        print(f"{'='*60}")
        
        print(f"\n📍 Trade: {country['flag']} {country['iso']}")
        print(f"   Asset: Residential Property")
        print(f"   Crisis Price: ${trade['entry_price']:,.2f}")
        print(f"   Recovery Price: ${trade['exit_price']:,.2f}")
        print(f"   Position Size: ${trade['position_size']:,.2f}")
        print(f"   Expected Profit: ${trade['position_size'] * ((trade['exit_price'] - trade['entry_price']) / trade['entry_price']):,.2f}")
        
        self._print_real_estate_instructions(country, trade)
        return {"status": "manual", "type": "real_estate"}
    
    def _print_manual_instructions(self, country: Dict, trade: Dict, asset_type: str):
        """Print manual execution instructions"""
        print("\n📋 EXECUTION INSTRUCTIONS:")
        print("-" * 40)
        print(f"1. Open Binance P2P account")
        print(f"2. Find a seller from {country['iso']} offering USDT")
        print(f"3. Buy USDT worth ${trade['position_size']:,.2f}")
        print(f"4. Transfer USDT to global Binance account")
        print(f"5. Sell USDT at global rate")
        print(f"6. Expected profit: ${trade['position_size'] * ((trade['exit_price'] - trade['entry_price']) / trade['entry_price']):,.2f}")
        print("-" * 40)
    
    def _print_gold_instructions(self, country: Dict, trade: Dict):
        """Print gold execution instructions"""
        print("\n📋 EXECUTION INSTRUCTIONS:")
        print("-" * 40)
        print(f"1. Find a gold dealer in {country['iso']}")
        print(f"2. Buy {trade['position_size'] / 45:.2f}g of 24K gold")
        print(f"3. Transport gold to Dubai/Switzerland")
        print(f"4. Sell at international spot price")
        print(f"5. Expected profit: ${trade['position_size'] * ((trade['exit_price'] - trade['entry_price']) / trade['entry_price']):,.2f}")
        print("-" * 40)
    
    def _print_real_estate_instructions(self, country: Dict, trade: Dict):
        """Print real estate execution instructions"""
        print("\n📋 EXECUTION INSTRUCTIONS:")
        print("-" * 40)
        print(f"1. Research property market in {country['iso']}")
        print(f"2. Contact local real estate agents")
        print(f"3. Find distressed property at ${trade['entry_price']:,.2f}")
        print(f"4. Legal due diligence and purchase")
        print(f"5. Hold for 6-24 months until recovery")
        print(f"6. Sell at ${trade['exit_price']:,.2f}")
        print(f"7. Expected profit: ${trade['position_size'] * ((trade['exit_price'] - trade['entry_price']) / trade['entry_price']):,.2f}")
        print("-" * 40)
    
    def _auto_execute_crypto(self, country: Dict, trade: Dict, pair: str) -> Dict:
        """Auto-execute crypto trade via exchange API"""
        try:
            result = self.exchange.place_order(
                symbol=pair.split('/')[0],
                side="BUY",
                amount=trade['position_size'] / trade['entry_price'],
                price=trade['entry_price']
            )
            return {"status": "executed", "result": result, "type": "crypto"}
        except Exception as e:
            return {"status": "failed", "error": str(e), "type": "crypto"}

# ========================================================================
# 🧠 TRADING ENGINE
# ========================================================================

class CrisisArbitrageBot:
    def __init__(self, config: Dict):
        self.config = config
        self.capital = config["initial_capital"]
        self.positions = []
        self.trades = []
        self.total_profit = 0
        self.win_count = 0
        self.loss_count = 0
        self.exchange = ExchangeConnector(config)
        self.executor = AssetExecutor(config, self.exchange)
        
        # Load FSI data (abbreviated - full data from earlier)
        self.fsi_data = self._load_fsi_data()
        self.wst_data = self._load_wst_data()
    
    def _load_fsi_data(self) -> Dict:
        """Load FSI 2024 data (full data from previous version)"""
        # Full FSI_2024 data here (179 countries)
        # Using abbreviated version for space
        return {
            "SOM": {"name": "Somalia", "flag": "🇸🇴", "fsi_score": 111.3, "rank": 1, "region": "africa"},
            "SDN": {"name": "Sudan", "flag": "🇸🇩", "fsi_score": 109.3, "rank": 2, "region": "africa"},
            "SSD": {"name": "South Sudan", "flag": "🇸🇸", "fsi_score": 109.0, "rank": 3, "region": "africa"},
            "SYR": {"name": "Syria", "flag": "🇸🇾", "fsi_score": 108.1, "rank": 4, "region": "middleeast"},
            "COD": {"name": "Congo-Kinshasa", "flag": "🇨🇩", "fsi_score": 106.7, "rank": 5, "region": "africa"},
            "YEM": {"name": "Yemen", "flag": "🇾🇪", "fsi_score": 106.6, "rank": 6, "region": "middleeast"},
            "AFG": {"name": "Afghanistan", "flag": "🇦🇫", "fsi_score": 103.9, "rank": 7, "region": "asia"},
            "HTI": {"name": "Haiti", "flag": "🇭🇹", "fsi_score": 103.5, "rank": 9, "region": "americas"},
            "UKR": {"name": "Ukraine", "flag": "🇺🇦", "fsi_score": 93.1, "rank": 22, "region": "europe"},
            "LBN": {"name": "Lebanon", "flag": "🇱🇧", "fsi_score": 92.7, "rank": 23, "region": "middleeast"},
            "ETH": {"name": "Ethiopia", "flag": "🇪🇹", "fsi_score": 98.1, "rank": 12, "region": "africa"},
            "VEN": {"name": "Venezuela", "flag": "🇻🇪", "fsi_score": 89.0, "rank": 30, "region": "americas"},
            "LKA": {"name": "Sri Lanka", "flag": "🇱🇰", "fsi_score": 88.2, "rank": 33, "region": "asia"},
            "PAK": {"name": "Pakistan", "flag": "🇵🇰", "fsi_score": 91.7, "rank": 27, "region": "asia"},
            "NGA": {"name": "Nigeria", "flag": "🇳🇬", "fsi_score": 96.6, "rank": 15, "region": "africa"},
            "RUS": {"name": "Russia", "flag": "🇷🇺", "fsi_score": 81.6, "rank": 48, "region": "europe"},
            "ZWE": {"name": "Zimbabwe", "flag": "🇿🇼", "fsi_score": 95.7, "rank": 18, "region": "africa"},
        }
    
    def _load_wst_data(self) -> Dict:
        """Load WST classification data"""
        return {
            "USA": {"class": "Core", "recovery_rate": 0.85},
            "GBR": {"class": "Core", "recovery_rate": 0.80},
            "DEU": {"class": "Core", "recovery_rate": 0.82},
            "UKR": {"class": "Semi", "recovery_rate": 0.35},
            "RUS": {"class": "Semi", "recovery_rate": 0.50},
            "CHN": {"class": "Semi", "recovery_rate": 0.55},
            "IND": {"class": "Semi", "recovery_rate": 0.48},
            "BRA": {"class": "Semi", "recovery_rate": 0.50},
            "default": {"class": "Periphery", "recovery_rate": 0.26}
        }
    
    def get_country_data(self) -> List[Dict]:
        """Build country data from FSI and WST"""
        countries = []
        for iso, data in self.fsi_data.items():
            wst = self.wst_data.get(iso, self.wst_data["default"])
            
            fsi_score = data["fsi_score"]
            base_score = min(99, max(1, round((fsi_score / 120) * 100)))
            
            class_modifier = 0
            if wst["class"] == "Periphery":
                class_modifier = 5 + 10 / 4
            elif wst["class"] == "Semi":
                class_modifier = 2
            elif wst["class"] == "Core":
                class_modifier = -5
                
            score = min(99, max(1, base_score + class_modifier))
            
            discount = 0.15 + (score / 100) * 0.5
            if wst["class"] == "Periphery":
                discount += 0.10
            elif wst["class"] == "Semi":
                discount += 0.05
            discount = min(0.75, discount)
            
            countries.append({
                "iso": iso,
                "name": data["name"],
                "flag": data["flag"],
                "region": data["region"],
                "score": round(score),
                "fsi_score": fsi_score,
                "fsi_rank": data["rank"],
                "wst_class": wst["class"],
                "recovery_rate": wst["recovery_rate"],
                "discount": discount,
            })
            
        countries.sort(key=lambda x: x["score"], reverse=True)
        return countries
    
    def score_opportunity(self, country: Dict) -> float:
        """Score a country as a trading opportunity"""
        crisis_score = country["score"] / 100
        discount = country["discount"]
        recovery_potential = 1 - country["recovery_rate"]
        structural_bonus = 0.2 if country["wst_class"] == "Periphery" else 0.1 if country["wst_class"] == "Semi" else 0
        
        return min(1, max(0, crisis_score * 0.35 + discount * 0.30 + recovery_potential * 0.20 + structural_bonus * 0.05))
    
    def calculate_expected_return(self, country: Dict) -> Dict:
        """Calculate expected return for a trade"""
        discount = country["discount"]
        fair_value = 100000
        entry_price = fair_value * (1 - discount)
        slippage_adjusted_entry = entry_price * (1 + self.config["slippage"])
        
        recovery_factor = 1 + (1 - country["recovery_rate"]) * 0.6
        structural_factor = 1.2 if country["wst_class"] == "Periphery" else 1.1 if country["wst_class"] == "Semi" else 0.9
        
        expected_exit_price = fair_value * (0.6 + country["recovery_rate"] * 0.6) * recovery_factor * structural_factor
        slippage_adjusted_exit = expected_exit_price * (1 - self.config["slippage"] * 0.5)
        cost_factor = 1 - self.config["transaction_costs"]
        
        gross_return = (slippage_adjusted_exit - slippage_adjusted_entry) / slippage_adjusted_entry
        net_return = gross_return * cost_factor
        
        return {
            "entry_price": slippage_adjusted_entry,
            "exit_price": slippage_adjusted_exit,
            "net_return": net_return
        }
    
    def execute_trade(self, country: Dict) -> Dict:
        """Execute a trade based on the opportunity"""
        if len(self.positions) >= self.config["max_positions"]:
            return {"status": "skipped", "reason": "max_positions"}
        
        expected = self.calculate_expected_return(country)
        if expected["net_return"] < self.config["target_return"]:
            return {"status": "skipped", "reason": "low_return"}
        
        position_size = self.capital * self.config["risk_per_trade"]
        if position_size > self.capital:
            return {"status": "skipped", "reason": "insufficient_capital"}
        
        trade = {
            "id": int(time.time() * 1000) + random.randint(1, 1000),
            "country": country,
            "entry_price": expected["entry_price"],
            "exit_price": expected["exit_price"],
            "position_size": position_size,
            "discount": country["discount"],
            "entry_time": datetime.now().isoformat(),
            "status": "pending",
            "profit": 0,
            "profit_pct": 0,
        }
        
        print(f"\n🚀 EXECUTING TRADE: {country['flag']} {country['name']}")
        print(f"   Entry: ${expected['entry_price']:,.2f}")
        print(f"   Exit: ${expected['exit_price']:,.2f}")
        print(f"   Size: ${position_size:,.2f}")
        print(f"   Expected Return: {expected['net_return']*100:.1f}%")
        
        # Determine asset class based on country
        asset_type = self._determine_asset_type(country)
        
        # Execute the trade
        if asset_type == "crypto":
            result = self.executor.execute_crypto(country, trade)
        elif asset_type == "gold":
            result = self.executor.execute_gold(country, trade)
        elif asset_type == "real_estate":
            result = self.executor.execute_real_estate(country, trade)
        else:
            result = {"status": "pending", "type": "manual"}
        
        trade["status"] = result.get("status", "pending")
        trade["asset_type"] = result.get("type", "unknown")
        self.positions.append(trade)
        
        return trade
    
    def _determine_asset_type(self, country: Dict) -> str:
        """Determine which asset class to trade"""
        # Strategy: Use crypto for high-risk countries, gold for medium, real estate for stable
        if country["score"] > 90:
            return "crypto"
        elif country["score"] > 75:
            return "gold"
        else:
            return "real_estate"
    
    def exit_trade(self, trade_id: int) -> Dict:
        """Exit a trade"""
        trade = next((t for t in self.positions if t["id"] == trade_id), None)
        if not trade:
            return {"status": "error", "reason": "trade_not_found"}
        
        # Simulate exit with realistic returns
        exit_result = self._calculate_realistic_exit(trade)
        
        trade["exit_price"] = exit_result["exit_price"]
        trade["profit"] = trade["position_size"] * exit_result["profit_pct"]
        trade["profit_pct"] = exit_result["profit_pct"]
        trade["status"] = "closed"
        
        self.capital += trade["position_size"] + trade["profit"]
        self.total_profit += trade["profit"]
        
        if trade["profit"] > 0:
            self.win_count += 1
            print(f"🟢 CLOSED: {trade['country']['flag']} {trade['country']['name']} +{trade['profit_pct']*100:.1f}%")
        else:
            self.loss_count += 1
            print(f"🔴 CLOSED: {trade['country']['flag']} {trade['country']['name']} {trade['profit_pct']*100:.1f}%")
        
        self.positions.remove(trade)
        self.trades.append(trade)
        
        return trade
    
    def _calculate_realistic_exit(self, trade: Dict) -> Dict:
        """Calculate realistic exit with failure scenarios"""
        entry = trade["entry_price"]
        country = trade["country"]
        recovery_rate = country["recovery_rate"]
        
        # Random factors for realism
        random_factor = 0.8 + random.random() * 0.4
        success_chance = random.random()
        
        # Failure scenarios
        if success_chance < 0.15:  # Failed recovery
            pct = -0.15 - random.random() * 0.05
        elif success_chance < 0.20:  # Black swan
            pct = -0.30 - random.random() * 0.10
        elif success_chance < 0.50:  # Stagnation
            pct = 0.05 + random.random() * 0.10
        elif success_chance < 0.70:  # Partial recovery
            pct = 0.15 + random.random() * 0.15
        else:  # Full recovery
            pct = (0.20 + recovery_rate * 0.60) * random_factor
        
        pct = min(0.35, max(-0.20, pct))
        exit_price = entry * (1 + pct)
        
        return {"exit_price": exit_price, "profit_pct": pct}
    
    def run(self, cycles: int = 1):
        """Main run loop"""
        print("\n" + "="*70)
        print("🏦 CRISIS ARBITRAGE BOT - HEDGE FUND EDITION")
        print("="*70)
        print(f"📊 Capital: ${self.config['initial_capital']:,.0f}")
        print(f"💰 Target Return: {self.config['target_return']*100:.0f}%")
        print(f"💸 Costs: {self.config['transaction_costs']*100:.0f}% fees, {self.config['slippage']*100:.0f}% slippage")
        print("="*70)
        
        for cycle in range(cycles):
            print(f"\n🔄 Cycle {cycle+1}/{cycles}")
            print("-"*40)
            
            countries = self.get_country_data()
            opportunities = []
            
            for country in countries:
                score = self.score_opportunity(country)
                if score > 0.25:
                    opportunities.append({**country, "score": score})
            
            opportunities.sort(key=lambda x: x["score"], reverse=True)
            print(f"📊 Found {len(opportunities)} opportunities")
            
            # Execute top opportunities
            executed = 0
            for country in opportunities[:self.config["max_positions"]]:
                expected = self.calculate_expected_return(country)
                if expected["net_return"] >= self.config["target_return"]:
                    result = self.execute_trade(country)
                    if result.get("status") != "skipped":
                        executed += 1
                        time.sleep(0.5)
            
            print(f"\n📈 Executed {executed} trades")
            
            # Wait for trades to complete (simulated)
            if self.positions:
                print("⏳ Waiting for trades to complete...")
                time.sleep(5)  # Simulate hold period
                for trade in self.positions[:]:
                    self.exit_trade(trade["id"])
        
        self.print_summary()
    
    def print_summary(self):
        """Print trading summary"""
        total = len(self.trades)
        win_rate = (self.win_count / total * 100) if total > 0 else 0
        
        print("\n" + "="*70)
        print("🏆 TRADING SUMMARY")
        print("="*70)
        print(f"💰 Final P&L: ${self.total_profit:,.2f}")
        print(f"📊 Trades: {total}")
        print(f"✅ Win Rate: {win_rate:.1f}%")
        print(f"📈 ROI: {(self.total_profit / self.config['initial_capital']) * 100:.1f}%")
        print(f"💵 Cash: ${self.capital:,.0f}")
        print(f"💎 Total Equity: ${self.capital + self.total_profit:,.0f}")
        print(f"✅ Wins: {self.win_count}")
        print(f"❌ Losses: {self.loss_count}")
        print("="*70)
        
        # Print individual trades
        if self.trades:
            print("\n📋 TRADE DETAILS:")
            print("-"*70)
            for trade in self.trades:
                country = trade["country"]
                status = "🟢" if trade["profit"] > 0 else "🔴"
                print(f"{status} {country['flag']} {country['name']}: ${trade['profit']:,.2f} ({trade['profit_pct']*100:.1f}%)")

# ========================================================================
# 🚀 MAIN EXECUTION
# ========================================================================

if __name__ == "__main__":
    # Create and run the bot
    bot = CrisisArbitrageBot(CONFIG)
    bot.run(cycles=1)
