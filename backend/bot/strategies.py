"""Algorithmic trading strategies with standardized signal generation."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Literal

from .indicators import calculate_bollinger_bands, calculate_ema, calculate_rsi, calculate_sma
from .market_data import Candle

Signal = Literal["BUY", "SELL", "HOLD"]


class BaseStrategy(ABC):
    """Abstract base class for all trading strategies."""

    name: str

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        self.params = params or {}

    @abstractmethod
    def evaluate(self, history: list[Candle]) -> tuple[Signal, str]:
        """Evaluate strategy across historical candles.

        Returns:
            (signal, reason_description)
        """
        pass

    @abstractmethod
    def get_description(self) -> str:
        """Return human-readable strategy description."""
        pass


class EMAMomentumStrategy(BaseStrategy):
    """EMA Crossover strategy with RSI momentum filter."""

    name = "ema_rsi"

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__(params)
        self.fast_period = int(self.params.get("fast_period", 9))
        self.slow_period = int(self.params.get("slow_period", 21))
        self.rsi_period = int(self.params.get("rsi_period", 14))
        self.rsi_overbought = float(self.params.get("rsi_overbought", 70.0))
        self.rsi_oversold = float(self.params.get("rsi_oversold", 30.0))

    def get_description(self) -> str:
        return (
            f"EMA({self.fast_period}/{self.slow_period}) crossover filtered by "
            f"RSI({self.rsi_period}, OB={self.rsi_overbought}, OS={self.rsi_oversold})"
        )

    def evaluate(self, history: list[Candle]) -> tuple[Signal, str]:
        min_required = max(self.slow_period + 2, self.rsi_period + 2)
        if len(history) < min_required:
            return "HOLD", f"Insufficient candles (need at least {min_required})"

        closes = [c.close for c in history]
        fast_ema = calculate_ema(closes, self.fast_period)
        slow_ema = calculate_ema(closes, self.slow_period)
        rsi = calculate_rsi(closes, self.rsi_period)

        curr_fast, prev_fast = fast_ema[-1], fast_ema[-2]
        curr_slow, prev_slow = slow_ema[-1], slow_ema[-2]
        curr_rsi = rsi[-1]

        if any(v is None for v in (curr_fast, prev_fast, curr_slow, prev_slow, curr_rsi)):
            return "HOLD", "Indicator warmup period incomplete"

        # Bullish Crossover: Fast crosses above Slow
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            if curr_rsi < self.rsi_overbought:
                return "BUY", f"Golden Cross (EMA {self.fast_period} > {self.slow_period}) with RSI={curr_rsi:.1f}"
            return "HOLD", f"Golden Cross blocked by overbought RSI ({curr_rsi:.1f} >= {self.rsi_overbought})"

        # Bearish Crossover: Fast crosses below Slow or Overbought reversal
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return "SELL", f"Death Cross (EMA {self.fast_period} < {self.slow_period}) with RSI={curr_rsi:.1f}"

        if curr_rsi >= self.rsi_overbought + 5.0:
            return "SELL", f"Extreme overbought take-profit trigger (RSI={curr_rsi:.1f})"

        return "HOLD", f"Trend neutral (Fast EMA={curr_fast:.2f}, Slow EMA={curr_slow:.2f}, RSI={curr_rsi:.1f})"


class BollingerReversionStrategy(BaseStrategy):
    """Mean reversion strategy utilizing Bollinger Bands and RSI."""

    name = "bollinger_reversion"

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__(params)
        self.period = int(self.params.get("period", 20))
        self.num_std = float(self.params.get("num_std", 2.0))
        self.rsi_period = int(self.params.get("rsi_period", 14))
        self.rsi_oversold = float(self.params.get("rsi_oversold", 35.0))
        self.rsi_overbought = float(self.params.get("rsi_overbought", 65.0))

    def get_description(self) -> str:
        return (
            f"Bollinger Bands({self.period}, {self.num_std}σ) mean reversion "
            f"with RSI({self.rsi_period})"
        )

    def evaluate(self, history: list[Candle]) -> tuple[Signal, str]:
        min_required = max(self.period + 2, self.rsi_period + 2)
        if len(history) < min_required:
            return "HOLD", f"Insufficient candles (need at least {min_required})"

        closes = [c.close for c in history]
        upper, middle, lower = calculate_bollinger_bands(closes, self.period, self.num_std)
        rsi = calculate_rsi(closes, self.rsi_period)

        curr_close = closes[-1]
        curr_upper = upper[-1]
        curr_lower = lower[-1]
        curr_rsi = rsi[-1]

        if any(v is None for v in (curr_upper, curr_lower, curr_rsi)):
            return "HOLD", "Indicator warmup period incomplete"

        # Buy when price touches or breaches lower band and RSI is oversold
        if curr_close <= curr_lower and curr_rsi <= self.rsi_oversold:
            return "BUY", f"Price ({curr_close:.2f}) touched lower band ({curr_lower:.2f}) with RSI={curr_rsi:.1f}"

        # Sell when price touches or breaches upper band
        if curr_close >= curr_upper or curr_rsi >= self.rsi_overbought:
            return "SELL", f"Price ({curr_close:.2f}) touched upper band ({curr_upper:.2f}) or RSI={curr_rsi:.1f}"

        return "HOLD", f"Inside bands (Lower={curr_lower:.2f}, Upper={curr_upper:.2f}, RSI={curr_rsi:.1f})"


class GridTradingStrategy(BaseStrategy):
    """Grid trading strategy capitalizing on oscillating market volatility."""

    name = "grid"

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__(params)
        self.grid_levels = int(self.params.get("grid_levels", 6))
        self.grid_step_pct = float(self.params.get("grid_step_pct", 0.8))  # 0.8% per step

    def get_description(self) -> str:
        return f"Grid Strategy with {self.grid_levels} levels and {self.grid_step_pct}% spacing"

    def evaluate(self, history: list[Candle]) -> tuple[Signal, str]:
        if len(history) < 20:
            return "HOLD", "Insufficient candles for baseline moving average"

        closes = [c.close for c in history]
        sma = calculate_sma(closes, 20)
        baseline = sma[-1]
        if baseline is None:
            return "HOLD", "Baseline moving average not ready"

        curr_close = closes[-1]
        diff_pct = ((curr_close - baseline) / baseline) * 100.0

        step = self.grid_step_pct
        if diff_pct <= -step:
            return "BUY", f"Price dipped {abs(diff_pct):.2f}% below mean ({baseline:.2f}) - Grid Buy"
        elif diff_pct >= step:
            return "SELL", f"Price rose {diff_pct:.2f}% above mean ({baseline:.2f}) - Grid Sell"

        return "HOLD", f"Price within grid boundary ({diff_pct:+.2f}% of mean)"


class DCAStrategy(BaseStrategy):
    """Dollar Cost Averaging on pullbacks with trailing take-profit."""

    name = "dca"

    def __init__(self, params: dict[str, Any] | None = None) -> None:
        super().__init__(params)
        self.dip_pct = float(self.params.get("dip_pct", 1.5))
        self.profit_target_pct = float(self.params.get("profit_target_pct", 2.5))

    def get_description(self) -> str:
        return f"DCA with {self.dip_pct}% dip entry and {self.profit_target_pct}% take-profit"

    def evaluate(self, history: list[Candle]) -> tuple[Signal, str]:
        if len(history) < 10:
            return "HOLD", "Insufficient candles"

        high_recent = max(c.high for c in history[-10:])
        curr_close = history[-1].close
        pullback = ((high_recent - curr_close) / high_recent) * 100.0

        if pullback >= self.dip_pct:
            return "BUY", f"Pullback of {pullback:.2f}% from 10-bar high ({high_recent:.2f})"

        return "HOLD", f"Pullback {pullback:.2f}% is below threshold {self.dip_pct}%"


STRATEGY_REGISTRY: dict[str, type[BaseStrategy]] = {
    "ema_rsi": EMAMomentumStrategy,
    "bollinger_reversion": BollingerReversionStrategy,
    "grid": GridTradingStrategy,
    "dca": DCAStrategy,
}


def get_strategy(name: str, params: dict[str, Any] | None = None) -> BaseStrategy:
    """Instantiate a strategy by name."""
    cls = STRATEGY_REGISTRY.get(name.lower())
    if not cls:
        available = ", ".join(STRATEGY_REGISTRY.keys())
        raise ValueError(f"Unknown strategy '{name}'. Available: {available}")
    return cls(params)
