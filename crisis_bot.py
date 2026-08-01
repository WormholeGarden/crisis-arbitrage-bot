"""
PhD-Level Genetic Programming Trading Strategy Discovery System
⚠️  WARNING: Direct API key placement is INSECURE - Use only for testing
"""

import numpy as np
import pandas as pd
from datetime import datetime, timedelta
import ccxt
import os
import sys
import time
from typing import Dict, List, Tuple, Optional, Any
import random
import copy
import json
from dataclasses import dataclass, field
from concurrent.futures import ProcessPoolExecutor, as_completed
import warnings
warnings.filterwarnings('ignore')

# ============================================================================
# 🔑 DIRECT API KEY CONFIGURATION - PUT YOUR KEYS HERE
# ============================================================================

# ⚠️  WARNING: Never commit code with hardcoded API keys to GitHub
# ⚠️  Use this ONLY for local testing

API_KEY = "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn"
API_SECRET = "5ub1m7ESdtllFD8yVWFtkezO479C9J8p0WjNH4KS5J0bc0mcBHlRKaarYIrOIWT0"

# Exchange configuration
EXCHANGE_ID = 'binance'  # Options: binance, kraken, coinbase, bybit
SANDBOX_MODE = True  # Set to False for real trading
SYMBOL = 'BTC/USDT'
TIMEFRAME = '1h'

# ============================================================================
# GENETIC PROGRAMMING CONFIGURATION
# ============================================================================

GP_CONFIG = {
    'population_size': 500,
    'generations': 100,
    'tournament_size': 7,
    'crossover_rate': 0.85,
    'mutation_rate': 0.15,
    'elite_count': 10,
    'max_depth': 6,
    'initial_depth': 4,
    'parsimony_coefficient': 0.01,
}

TRADING_CONFIG = {
    'symbol': SYMBOL,
    'timeframe': TIMEFRAME,
    'lookback_days': 365,
    'train_ratio': 0.6,
    'val_ratio': 0.2,
    'test_ratio': 0.2,
    'commission': 0.001,
    'slippage': 0.0005,
    'min_trades': 50,
}

# ============================================================================
# DATA FETCHING & PREPROCESSING
# ============================================================================

class DataFetcher:
    """Fetches and preprocesses market data with proper handling"""
    
    def __init__(self, api_key: str, api_secret: str, exchange_id: str = 'binance', sandbox: bool = True):
        self.api_key = api_key
        self.api_secret = api_secret
        self.exchange_id = exchange_id
        self.sandbox = sandbox
        self.exchange = self._initialize_exchange()
        
    def _initialize_exchange(self):
        """Initialize exchange connection with direct API keys"""
        exchange_class = getattr(ccxt, self.exchange_id)
        exchange = exchange_class({
            'apiKey': self.api_key,
            'secret': self.api_secret,
            'enableRateLimit': True,
            'options': {'defaultType': 'spot'},
        })
        if self.sandbox:
            exchange.set_sandbox_mode(True)
            print(f"🔒 Running in SANDBOX mode - No real trades will be executed")
        else:
            print(f"⚠️  Running in LIVE mode - Real trades will be executed!")
        return exchange
    
    def fetch_data(self, symbol: str, timeframe: str, days: int) -> pd.DataFrame:
        """Fetch OHLCV data with proper pagination"""
        print(f"📊 Fetching {days} days of {symbol} data...")
        since = self.exchange.parse8601(
            (datetime.now() - timedelta(days=days)).isoformat()
        )
        all_ohlcv = []
        
        while True:
            try:
                ohlcv = self.exchange.fetch_ohlcv(
                    symbol, timeframe, since=since, limit=1000
                )
                if not ohlcv:
                    break
                all_ohlcv.extend(ohlcv)
                since = ohlcv[-1][0] + 1
                
                if len(ohlcv) < 1000:
                    break
            except Exception as e:
                print(f"⚠️  Error fetching data: {e}")
                break
        
        df = pd.DataFrame(all_ohlcv, columns=['timestamp', 'open', 'high', 'low', 'close', 'volume'])
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        print(f"✅ Fetched {len(df)} candles")
        return df
    
    def compute_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Compute comprehensive feature set for strategy evolution"""
        df = df.copy()
        
        # Price-based features
        df['returns'] = df['close'].pct_change()
        df['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Volatility features
        for period in [5, 10, 20, 50]:
            df[f'volatility_{period}'] = df['returns'].rolling(period).std() * np.sqrt(period)
            df[f'atr_{period}'] = self._compute_atr(df, period)
        
        # Momentum indicators
        for period in [5, 10, 20, 50, 100, 200]:
            df[f'sma_{period}'] = df['close'].rolling(period).mean()
            df[f'ema_{period}'] = df['close'].ewm(span=period, adjust=False).mean()
            df[f'rsi_{period}'] = self._compute_rsi(df, period)
        
        # Price ratios
        df['hl_ratio'] = (df['high'] - df['low']) / df['close']
        df['co_ratio'] = (df['close'] - df['open']) / df['open']
        
        # Volume features
        df['volume_sma_20'] = df['volume'].rolling(20).mean()
        df['volume_ratio'] = df['volume'] / df['volume_sma_20']
        
        # Bollinger Bands
        for period in [20, 50]:
            sma = df['close'].rolling(period).mean()
            std = df['close'].rolling(period).std()
            df[f'bb_upper_{period}'] = sma + 2 * std
            df[f'bb_lower_{period}'] = sma - 2 * std
            df[f'bb_position_{period}'] = (df['close'] - sma) / (2 * std)
        
        # MACD
        exp1 = df['close'].ewm(span=12, adjust=False).mean()
        exp2 = df['close'].ewm(span=26, adjust=False).mean()
        df['macd'] = exp1 - exp2
        df['macd_signal'] = df['macd'].ewm(span=9, adjust=False).mean()
        df['macd_hist'] = df['macd'] - df['macd_signal']
        
        # Clean NaN values
        df = df.replace([np.inf, -np.inf], np.nan)
        df = df.fillna(method='ffill').fillna(method='bfill')
        
        return df
    
    @staticmethod
    def _compute_atr(df: pd.DataFrame, period: int) -> pd.Series:
        """Average True Range"""
        high_low = df['high'] - df['low']
        high_close = np.abs(df['high'] - df['close'].shift())
        low_close = np.abs(df['low'] - df['close'].shift())
        tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
        return tr.rolling(period).mean()
    
    @staticmethod
    def _compute_rsi(df: pd.DataFrame, period: int) -> pd.Series:
        """Relative Strength Index"""
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
        rs = gain / loss
        return 100 - (100 / (1 + rs))

# ============================================================================
# GENETIC PROGRAMMING CORE
# ============================================================================

@dataclass
class StrategyNode:
    """Node in the strategy expression tree"""
    value: Any
    left: Optional['StrategyNode'] = None
    right: Optional['StrategyNode'] = None
    is_leaf: bool = True

class StrategyTree:
    """Genetic programming tree representing a trading strategy"""
    
    OPERATORS = {
        '+': lambda x, y: x + y,
        '-': lambda x, y: x - y,
        '*': lambda x, y: x * y,
        '/': lambda x, y: x / (y + 1e-8),
        'max': lambda x, y: np.maximum(x, y),
        'min': lambda x, y: np.minimum(x, y),
        'avg': lambda x, y: (x + y) / 2,
        'sqrt': lambda x, y: np.sqrt(np.abs(x) + 1e-8),
        'exp': lambda x, y: np.exp(np.clip(x, -10, 10)),
        'log': lambda x, y: np.log(np.abs(x) + 1e-8),
        'abs': lambda x, y: np.abs(x),
        'sign': lambda x, y: np.sign(x),
        'sigmoid': lambda x, y: 1 / (1 + np.exp(-np.clip(x, -10, 10))),
    }
    
    TERMINALS = [
        'close', 'open', 'high', 'low', 'volume',
        'returns', 'volatility_5', 'volatility_10', 'volatility_20',
        'rsi_5', 'rsi_10', 'rsi_20', 'rsi_50',
        'sma_5', 'sma_10', 'sma_20', 'sma_50', 'sma_100', 'sma_200',
        'ema_5', 'ema_10', 'ema_20', 'ema_50', 'ema_100', 'ema_200',
        'bb_position_20', 'bb_position_50',
        'atr_5', 'atr_10', 'atr_20', 'atr_50',
        'macd', 'macd_signal', 'macd_hist',
        'volume_ratio', 'hl_ratio', 'co_ratio',
    ]
    
    def __init__(self, max_depth: int = 6, initial_depth: int = 4):
        self.max_depth = max_depth
        self.initial_depth = initial_depth
        self.root = None
        self.fitness = -np.inf
        self.performance_metrics = {}
        self._terminal_prob = 0.4
        
    def grow(self, depth: int = 0):
        """Grow a random tree"""
        if depth >= self.initial_depth or (depth > 0 and random.random() < self._terminal_prob):
            return StrategyNode(random.choice(self.TERMINALS), is_leaf=True)
        
        operator = random.choice(list(self.OPERATORS.keys()))
        node = StrategyNode(operator, is_leaf=False)
        node.left = self.grow(depth + 1)
        node.right = self.grow(depth + 1)
        return node
    
    def evaluate(self, df: pd.DataFrame) -> np.ndarray:
        """Evaluate the tree on the given dataframe"""
        if self.root is None:
            return np.zeros(len(df))
        return self._evaluate_node(self.root, df)
    
    def _evaluate_node(self, node: StrategyNode, df: pd.DataFrame) -> np.ndarray:
        """Recursive evaluation of the expression tree"""
        if node.is_leaf:
            if node.value in df.columns:
                return df[node.value].values
            else:
                return np.full(len(df), float(node.value) if isinstance(node.value, (int, float)) else 0.0)
        
        left_val = self._evaluate_node(node.left, df)
        right_val = self._evaluate_node(node.right, df)
        
        if node.value in self.OPERATORS:
            return self.OPERATORS[node.value](left_val, right_val)
        else:
            return left_val
    
    def to_string(self, node: Optional[StrategyNode] = None, depth: int = 0) -> str:
        """Convert tree to human-readable string"""
        if node is None:
            node = self.root
        if node.is_leaf:
            return str(node.value)
        left_str = self.to_string(node.left, depth + 1)
        right_str = self.to_string(node.right, depth + 1)
        if node.value in ['sqrt', 'exp', 'log', 'abs', 'sign']:
            return f"{node.value}({left_str})"
        return f"({left_str} {node.value} {right_str})"
    
    def copy(self) -> 'StrategyTree':
        """Deep copy of the tree"""
        new_tree = StrategyTree(self.max_depth, self.initial_depth)
        new_tree.root = self._copy_node(self.root)
        return new_tree
    
    def _copy_node(self, node: Optional[StrategyNode]) -> Optional[StrategyNode]:
        if node is None:
            return None
        new_node = StrategyNode(node.value, is_leaf=node.is_leaf)
        new_node.left = self._copy_node(node.left)
        new_node.right = self._copy_node(node.right)
        return new_node
    
    def size(self, node: Optional[StrategyNode] = None) -> int:
        """Count nodes in tree"""
        if node is None:
            node = self.root
        if node is None or node.is_leaf:
            return 1
        return 1 + self.size(node.left) + self.size(node.right)

# ============================================================================
# BACKTESTING & FITNESS EVALUATION
# ============================================================================

class TradingSimulator:
    """Simulates trading with a strategy and computes performance metrics"""
    
    def __init__(self, config: Dict):
        self.config = config
        
    def backtest(self, df: pd.DataFrame, signals: np.ndarray) -> Dict:
        """Perform backtest with realistic constraints"""
        signals = np.clip(signals, -1, 1)
        positions = np.zeros(len(df))
        
        threshold = 0.1
        positions[signals > threshold] = 1
        positions[signals < -threshold] = -1
        
        returns = df['returns'].values
        strategy_returns = positions * returns * (1 - self.config['commission']) - self.config['slippage']
        strategy_returns = np.nan_to_num(strategy_returns, 0)
        
        total_return = np.prod(1 + strategy_returns) - 1
        annual_return = (1 + total_return) ** (252 / len(df)) - 1
        
        daily_std = np.std(strategy_returns) * np.sqrt(252)
        sharpe = (annual_return - 0.02) / daily_std if daily_std > 0 else 0
        
        cumulative = np.cumprod(1 + strategy_returns)
        running_max = np.maximum.accumulate(cumulative)
        drawdown = (cumulative - running_max) / running_max
        max_drawdown = np.min(drawdown)
        
        winning_trades = strategy_returns[strategy_returns > 0]
        losing_trades = strategy_returns[strategy_returns < 0]
        win_rate = len(winning_trades) / (len(winning_trades) + len(losing_trades)) if len(winning_trades) + len(losing_trades) > 0 else 0
        
        calmar = abs(annual_return / max_drawdown) if max_drawdown != 0 else 0
        
        downside_returns = strategy_returns[strategy_returns < 0]
        downside_std = np.std(downside_returns) * np.sqrt(252) if len(downside_returns) > 0 else 1
        sortino = (annual_return - 0.02) / downside_std if downside_std > 0 else 0
        
        avg_win = np.mean(winning_trades) if len(winning_trades) > 0 else 0
        avg_loss = np.mean(losing_trades) if len(losing_trades) > 0 else 0
        profit_factor = abs(np.sum(winning_trades) / np.sum(losing_trades)) if np.sum(losing_trades) != 0 else 0
        
        trade_count = np.sum(np.abs(np.diff(positions)) > 0.5)
        
        excess_returns = strategy_returns - returns
        tracking_error = np.std(excess_returns) * np.sqrt(252)
        information_ratio = annual_return / tracking_error if tracking_error > 0 else 0
        
        return {
            'total_return': total_return,
            'annual_return': annual_return,
            'sharpe_ratio': sharpe,
            'sortino_ratio': sortino,
            'calmar_ratio': calmar,
            'max_drawdown': max_drawdown,
            'win_rate': win_rate,
            'profit_factor': profit_factor,
            'avg_win': avg_win,
            'avg_loss': avg_loss,
            'trade_count': trade_count,
            'information_ratio': information_ratio,
            'returns': strategy_returns,
            'positions': positions,
            'cumulative_returns': cumulative,
            'drawdown': drawdown,
        }
    
    def compute_fitness(self, metrics: Dict) -> float:
        """Multi-objective fitness function"""
        if metrics['trade_count'] < self.config['min_trades']:
            return -np.inf
        
        score = 0
        score += 0.40 * metrics['sharpe_ratio']
        score += 0.20 * min(metrics['calmar_ratio'], 5)
        score += 0.15 * metrics['win_rate']
        score += 0.15 * min(metrics['profit_factor'], 3)
        
        if metrics['max_drawdown'] < -0.3:
            score += 0.10 * (metrics['max_drawdown'] + 0.3)
        
        score += 0.05 * min(metrics['information_ratio'], 2)
        
        return score

# ============================================================================
# GENETIC PROGRAMMING EVOLUTION ENGINE
# ============================================================================

class GPEngine:
    """Main genetic programming engine for strategy discovery"""
    
    def __init__(self, config: Dict, data: pd.DataFrame, fetcher: DataFetcher):
        self.config = config
        self.data = data
        self.fetcher = fetcher
        self.population = []
        self.best_individual = None
        self.generation = 0
        self.history = []
        self.simulator = TradingSimulator(TRADING_CONFIG)
        
    def initialize_population(self):
        """Create initial random population"""
        self.population = []
        for _ in range(self.config['population_size']):
            tree = StrategyTree(
                max_depth=self.config['max_depth'],
                initial_depth=self.config['initial_depth']
            )
            tree.root = tree.grow()
            self.population.append(tree)
    
    def evaluate_population(self, df: pd.DataFrame, use_cache: bool = True):
        """Evaluate all individuals in the population"""
        for individual in self.population:
            if not hasattr(individual, '_fitness_cache') or not use_cache:
                try:
                    signals = individual.evaluate(df)
                    metrics = self.simulator.backtest(df, signals)
                    fitness = self.simulator.compute_fitness(metrics)
                    
                    tree_size = individual.size()
                    fitness -= self.config['parsimony_coefficient'] * tree_size
                    
                    individual.fitness = fitness
                    individual.performance_metrics = metrics
                    individual._fitness_cache = (signals, metrics, fitness)
                    
                except Exception as e:
                    individual.fitness = -np.inf
    
    def select_parent(self) -> StrategyTree:
        """Tournament selection"""
        tournament = random.sample(self.population, self.config['tournament_size'])
        best = max(tournament, key=lambda x: x.fitness)
        return best.copy()
    
    def crossover(self, parent1: StrategyTree, parent2: StrategyTree) -> Tuple[StrategyTree, StrategyTree]:
        """Subtree crossover"""
        if random.random() > self.config['crossover_rate']:
            return parent1.copy(), parent2.copy()
        
        child1 = parent1.copy()
        child2 = parent2.copy()
        
        node1 = self._select_random_node(child1.root)
        node2 = self._select_random_node(child2.root)
        
        if node1 and node2:
            temp = node1.value
            node1.value = node2.value
            node2.value = temp
            temp_left = node1.left
            node1.left = node2.left
            node2.left = temp_left
            temp_right = node1.right
            node1.right = node2.right
            node2.right = temp_right
        
        return child1, child2
    
    def _select_random_node(self, node: StrategyNode) -> Optional[StrategyNode]:
        """Select a random node in the tree for crossover"""
        if node.is_leaf:
            return node
        if random.random() < 0.3:
            return node
        if node.left and random.random() < 0.5:
            return self._select_random_node(node.left)
        if node.right:
            return self._select_random_node(node.right)
        return node
    
    def mutate(self, tree: StrategyTree) -> StrategyTree:
        """Point mutation and subtree mutation"""
        if random.random() > self.config['mutation_rate']:
            return tree.copy()
        
        mutant = tree.copy()
        mutation_type = random.choice(['point', 'subtree', 'shrink'])
        
        if mutation_type == 'point':
            self._mutate_point(mutant.root)
        elif mutation_type == 'subtree':
            node = self._select_random_node(mutant.root)
            if node:
                new_subtree = StrategyTree(
                    max_depth=self.config['max_depth'],
                    initial_depth=3
                ).grow()
                node.value = new_subtree.value
                node.left = new_subtree.left
                node.right = new_subtree.right
                node.is_leaf = new_subtree.is_leaf
        else:
            node = self._select_random_node(mutant.root)
            if node and not node.is_leaf:
                node.value = random.choice(StrategyTree.TERMINALS)
                node.left = None
                node.right = None
                node.is_leaf = True
        
        if mutant.size() > 2 ** self.config['max_depth']:
            new_tree = StrategyTree(
                max_depth=self.config['max_depth'],
                initial_depth=3
            )
            new_tree.root = new_tree.grow()
            return new_tree
        
        return mutant
    
    def _mutate_point(self, node: StrategyNode):
        """Point mutation - change a node's value"""
        if node.is_leaf:
            if random.random() < 0.5:
                node.value = random.choice(StrategyTree.TERMINALS)
            else:
                node.value = random.uniform(-1, 1)
        else:
            if random.random() < 0.3:
                node.value = random.choice(list(StrategyTree.OPERATORS.keys()))
            else:
                if node.left:
                    self._mutate_point(node.left)
                if node.right:
                    self._mutate_point(node.right)
    
    def evolve(self, generations: int):
        """Main evolution loop"""
        print(f"\n🧬 Starting evolution for {generations} generations")
        print(f"📊 Population size: {self.config['population_size']}")
        print(f"📈 Data shape: {self.data.shape}")
        
        train_size = int(len(self.data) * TRADING_CONFIG['train_ratio'])
        val_size = int(len(self.data) * TRADING_CONFIG['val_ratio'])
        train_data = self.data.iloc[:train_size]
        val_data = self.data.iloc[train_size:train_size + val_size]
        test_data = self.data.iloc[train_size + val_size:]
        
        self.initialize_population()
        self.evaluate_population(train_data)
        best_fitness_history = []
        
        for gen in range(generations):
            self.generation = gen
            
            sorted_pop = sorted(self.population, key=lambda x: x.fitness, reverse=True)
            elite = sorted_pop[:self.config['elite_count']]
            
            new_population = []
            new_population.extend([e.copy() for e in elite])
            
            while len(new_population) < self.config['population_size']:
                parent1 = self.select_parent()
                parent2 = self.select_parent()
                
                child1, child2 = self.crossover(parent1, parent2)
                child1 = self.mutate(child1)
                child2 = self.mutate(child2)
                
                new_population.extend([child1, child2])
            
            self.population = new_population[:self.config['population_size']]
            self.evaluate_population(train_data)
            
            best = max(self.population, key=lambda x: x.fitness)
            best_fitness_history.append(best.fitness)
            
            val_signals = best.evaluate(val_data)
            val_metrics = self.simulator.backtest(val_data, val_signals)
            val_fitness = self.simulator.compute_fitness(val_metrics)
            
            if best.fitness > 0:
                print(f"🧬 Gen {gen}: Best Fitness = {best.fitness:.4f}, "
                      f"Val Fitness = {val_fitness:.4f}, "
                      f"Sharpe = {best.performance_metrics['sharpe_ratio']:.2f}, "
                      f"Size = {best.size()}")
            
            if self.best_individual is None or best.fitness > self.best_individual.fitness:
                self.best_individual = best.copy()
                self.best_individual._val_metrics = val_metrics
                self._save_checkpoint()
            
            if len(best_fitness_history) > 20:
                recent = best_fitness_history[-20:]
                if max(recent) - min(recent) < 0.001:
                    print(f"🛑 Early stopping at generation {gen} - no improvement")
                    break
        
        if self.best_individual:
            print("\n" + "="*70)
            print("🏆 BEST STRATEGY DISCOVERED")
            print("="*70)
            print(f"\n📝 Expression: {self.best_individual.to_string()}")
            print(f"\n📏 Tree Size: {self.best_individual.size()} nodes")
            print(f"\n📊 Final Fitness: {self.best_individual.fitness:.4f}")
            
            test_signals = self.best_individual.evaluate(test_data)
            test_metrics = self.simulator.backtest(test_data, test_signals)
            
            print("\n📈 Test Performance:")
            for key, value in test_metrics.items():
                if not isinstance(value, (np.ndarray, list)):
                    print(f"  {key}: {value:.4f}")
            
            return self.best_individual, test_metrics
        
        return None, None
    
    def _save_checkpoint(self):
        """Save best individual to file"""
        checkpoint = {
            'generation': self.generation,
            'fitness': self.best_individual.fitness,
            'expression': self.best_individual.to_string(),
            'performance': self.best_individual.performance_metrics,
        }
        with open('best_strategy_checkpoint.json', 'w') as f:
            json.dump(checkpoint, f, indent=2)

# ============================================================================
# ENSEMBLE & REGIME DETECTION
# ============================================================================

class EnsembleStrategy:
    """Combine multiple strategies with dynamic weighting"""
    
    def __init__(self):
        self.strategies = []
        self.weights = []
        
    def add_strategy(self, strategy: StrategyTree, weight: float = 1.0):
        self.strategies.append(strategy)
        self.weights.append(weight)
    
    def predict(self, df: pd.DataFrame) -> np.ndarray:
        """Weighted ensemble prediction"""
        predictions = []
        for strategy, weight in zip(self.strategies, self.weights):
            pred = strategy.evaluate(df)
            predictions.append(pred * weight)
        
        ensemble_pred = np.sum(predictions, axis=0) / np.sum(self.weights)
        return ensemble_pred

# ============================================================================
# 🚀 MAIN EXECUTION
# ============================================================================

if __name__ == "__main__":
    print("="*70)
    print("🧬 PHD-LEVEL GENETIC PROGRAMMING TRADING STRATEGY DISCOVERY")
    print("="*70)
    print("\n⚠️  IMPORTANT SECURITY WARNING:")
    print("   - You are using HARDCODED API keys")
    print("   - NEVER commit this code to GitHub")
    print("   - This is for LOCAL TESTING only")
    print("="*70)
    
    # Validate API keys
    if not API_KEY or not API_SECRET:
        print("\n❌ ERROR: API keys are empty!")
        print("Please set your API keys in the section marked")
        print("'DIRECT API KEY CONFIGURATION' at the top of the file.")
        sys.exit(1)
    
    if API_KEY == "dD9RfqKg3tDc6SXHV54jhJY5jym0NlK0gEiB5HwQcgCuILEaQ5uu63ZllsPby0Vn":
        print("\n⚠️  WARNING: You are using the EXAMPLE API keys!")
        print("   These are NOT real keys and will not work.")
        print("   Replace them with your actual API keys.")
        print("\n   Press Ctrl+C to cancel, or wait 5 seconds to continue...")
        time.sleep(5)
    
    # Clean up API keys
    API_KEY = API_KEY.strip()
    API_SECRET = API_SECRET.strip()
    
    print(f"\n🔑 API Key: {API_KEY[:8]}...{API_KEY[-8:]}")
    print(f"🔒 API Secret: {API_SECRET[:8]}...{API_SECRET[-8:]}")
    print(f"🏦 Exchange: {EXCHANGE_ID}")
    print(f"🔐 Sandbox Mode: {SANDBOX_MODE}")
    print(f"📊 Symbol: {SYMBOL}")
    print(f"⏱️  Timeframe: {TIMEFRAME}")
    
    try:
        # 1. Initialize data fetcher with DIRECT API KEYS
        print("\n" + "="*70)
        print("📡 INITIALIZING DATA FETCHER")
        print("="*70)
        
        fetcher = DataFetcher(
            api_key=API_KEY,
            api_secret=API_SECRET,
            exchange_id=EXCHANGE_ID,
            sandbox=SANDBOX_MODE
        )
        print(f"✅ Connected to {EXCHANGE_ID} (Sandbox: {SANDBOX_MODE})")
        
        # 2. Fetch data
        print("\n" + "="*70)
        print("📊 FETCHING MARKET DATA")
        print("="*70)
        
        df = fetcher.fetch_data(
            SYMBOL,
            TIMEFRAME,
            TRADING_CONFIG['lookback_days']
        )
        
        if len(df) < 100:
            print(f"❌ Not enough data: {len(df)} candles. Need at least 100.")
            print("Try reducing 'lookback_days' or using a different symbol.")
            sys.exit(1)
        
        # 3. Compute features
        print("\n" + "="*70)
        print("🧮 COMPUTING FEATURES")
        print("="*70)
        
        df = fetcher.compute_features(df)
        print(f"✅ Feature shape: {df.shape}")
        print(f"📊 Features: {list(df.columns)}")
        
        # 4. Initialize GP engine
        print("\n" + "="*70)
        print("🧬 INITIALIZING GENETIC PROGRAMMING ENGINE")
        print("="*70)
        
        engine = GPEngine(GP_CONFIG, df, fetcher)
        
        # 5. Run evolution
        print("\n" + "="*70)
        print("🚀 STARTING GENETIC PROGRAMMING EVOLUTION")
        print("="*70)
        print("⚠️  This may take several minutes to complete...")
        print("   Press Ctrl+C at any time to stop.\n")
        
        best_strategy, final_metrics = engine.evolve(GP_CONFIG['generations'])
        
        # 6. Results
        if best_strategy:
            print("\n" + "="*70)
            print("✅ STRATEGY DISCOVERY SUCCESSFUL!")
            print("="*70)
            
            # Create ensemble with top strategies
            print("\n" + "="*70)
            print("🤝 CREATING ENSEMBLE STRATEGY")
            print("="*70)
            
            ensemble = EnsembleStrategy()
            top_strategies = sorted(engine.population, key=lambda x: x.fitness, reverse=True)[:5]
            for i, strategy in enumerate(top_strategies):
                weight = 1.0 / (i + 1)
                ensemble.add_strategy(strategy, weight)
                print(f"✅ Added strategy {i+1} with weight {weight:.3f}")
            
            test_size = int(len(df) * TRADING_CONFIG['test_ratio'])
            test_data = df.iloc[-test_size:]
            ensemble_signals = ensemble.predict(test_data)
            ensemble_metrics = engine.simulator.backtest(test_data, ensemble_signals)
            
            print("\n📊 ENSEMBLE PERFORMANCE:")
            for key, value in ensemble_metrics.items():
                if not isinstance(value, (np.ndarray, list)):
                    print(f"  {key}: {value:.4f}")
            
            print("\n" + "="*70)
            print("🎉 STRATEGY DISCOVERY COMPLETE!")
            print("="*70)
            print("\n📝 Best strategy saved to 'best_strategy_checkpoint.json'")
            print("\n⚠️  REMEMBER:")
            print("   - Never use this strategy with real money without extensive testing")
            print("   - Past performance does not guarantee future results")
            print("   - Always use proper risk management")
            print("="*70)
            
        else:
            print("\n❌ No valid strategy found. Try adjusting parameters.")
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Evolution stopped by user.")
        print("Check 'best_strategy_checkpoint.json' for any saved results.")
        
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        print("\nTroubleshooting tips:")
        print("1. Check your API keys are correct")
        print("2. Verify the exchange supports your symbol")
        print("3. Try using SANDBOX_MODE = True")
        print("4. Check your internet connection")
        print("5. Try using synthetic data by setting SYNTHETIC_DATA = True")
