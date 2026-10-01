"""Technical indicators and quantitative finance metrics.

Implements pure-Python mathematical algorithms for trading indicators
and risk-adjusted return calculations without heavy C-dependencies.
"""

from __future__ import annotations

import math
from typing import Sequence


def calculate_sma(prices: Sequence[float], period: int) -> list[float | None]:
    """Calculate Simple Moving Average (SMA)."""
    if period <= 0:
        raise ValueError("Period must be greater than 0")

    result: list[float | None] = [None] * len(prices)
    if len(prices) < period:
        return result

    window_sum = sum(prices[:period])
    result[period - 1] = window_sum / period

    for i in range(period, len(prices)):
        window_sum += prices[i] - prices[i - period]
        result[i] = window_sum / period

    return result


def calculate_ema(prices: Sequence[float], period: int) -> list[float | None]:
    """Calculate Exponential Moving Average (EMA)."""
    if period <= 0:
        raise ValueError("Period must be greater than 0")

    result: list[float | None] = [None] * len(prices)
    if len(prices) < period:
        return result

    # Seed EMA with initial SMA
    initial_sma = sum(prices[:period]) / period
    result[period - 1] = initial_sma

    multiplier = 2.0 / (period + 1)
    prev_ema = initial_sma

    for i in range(period, len(prices)):
        curr_ema = (prices[i] - prev_ema) * multiplier + prev_ema
        result[i] = curr_ema
        prev_ema = curr_ema

    return result


def calculate_rsi(prices: Sequence[float], period: int = 14) -> list[float | None]:
    """Calculate Relative Strength Index (RSI) using Wilder's Smoothing."""
    if period <= 0:
        raise ValueError("Period must be greater than 0")

    result: list[float | None] = [None] * len(prices)
    if len(prices) <= period:
        return result

    gains: list[float] = []
    losses: list[float] = []

    for i in range(1, len(prices)):
        change = prices[i] - prices[i - 1]
        gains.append(max(change, 0.0))
        losses.append(max(-change, 0.0))

    if len(gains) < period:
        return result

    # Initial average gain & loss
    avg_gain = sum(gains[:period]) / period
    avg_loss = sum(losses[:period]) / period

    if avg_loss == 0.0:
        result[period] = 100.0
    else:
        rs = avg_gain / avg_loss
        result[period] = 100.0 - (100.0 / (1.0 + rs))

    for i in range(period, len(gains)):
        avg_gain = (avg_gain * (period - 1) + gains[i]) / period
        avg_loss = (avg_loss * (period - 1) + losses[i]) / period

        if avg_loss == 0.0:
            result[i + 1] = 100.0
        else:
            rs = avg_gain / avg_loss
            result[i + 1] = 100.0 - (100.0 / (1.0 + rs))

    return result


def calculate_bollinger_bands(
    prices: Sequence[float],
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Calculate Bollinger Bands (Upper, Middle, Lower)."""
    sma = calculate_sma(prices, period)
    upper: list[float | None] = [None] * len(prices)
    lower: list[float | None] = [None] * len(prices)

    for i in range(period - 1, len(prices)):
        window = prices[i - period + 1 : i + 1]
        mean = sma[i]
        if mean is None:
            continue
        variance = sum((p - mean) ** 2 for p in window) / period
        std_dev = math.sqrt(variance)
        upper[i] = mean + (num_std * std_dev)
        lower[i] = mean - (num_std * std_dev)

    return upper, sma, lower


def calculate_atr(
    highs: Sequence[float],
    lows: Sequence[float],
    closes: Sequence[float],
    period: int = 14,
) -> list[float | None]:
    """Calculate Average True Range (ATR)."""
    if len(highs) != len(lows) or len(highs) != len(closes):
        raise ValueError("High, Low, and Close sequences must have equal length")

    result: list[float | None] = [None] * len(highs)
    if len(highs) < period:
        return result

    tr_list: list[float] = [highs[0] - lows[0]]
    for i in range(1, len(highs)):
        h = highs[i]
        l = lows[i]
        prev_c = closes[i - 1]
        tr = max(h - l, abs(h - prev_c), abs(l - prev_c))
        tr_list.append(tr)

    first_atr = sum(tr_list[:period]) / period
    result[period - 1] = first_atr
    prev_atr = first_atr

    for i in range(period, len(tr_list)):
        curr_atr = (prev_atr * (period - 1) + tr_list[i]) / period
        result[i] = curr_atr
        prev_atr = curr_atr

    return result


def calculate_sharpe_ratio(
    returns: Sequence[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252 * 24,  # Hourly crypto default
) -> float:
    """Calculate Annualized Sharpe Ratio."""
    if not returns or len(returns) < 2:
        return 0.0

    excess_returns = [r - (risk_free_rate / periods_per_year) for r in returns]
    mean_excess = sum(excess_returns) / len(excess_returns)
    variance = sum((r - mean_excess) ** 2 for r in excess_returns) / (len(excess_returns) - 1)
    std_dev = math.sqrt(variance)

    if std_dev == 0.0:
        return 0.0

    return (mean_excess / std_dev) * math.sqrt(periods_per_year)


def calculate_sortino_ratio(
    returns: Sequence[float],
    risk_free_rate: float = 0.0,
    periods_per_year: int = 252 * 24,
) -> float:
    """Calculate Annualized Sortino Ratio (downside risk adjusted)."""
    if not returns or len(returns) < 2:
        return 0.0

    rf_period = risk_free_rate / periods_per_year
    excess_returns = [r - rf_period for r in returns]
    mean_excess = sum(excess_returns) / len(excess_returns)

    downside_diffs = [min(0.0, r) ** 2 for r in excess_returns]
    downside_variance = sum(downside_diffs) / len(downside_diffs)
    downside_dev = math.sqrt(downside_variance)

    if downside_dev == 0.0:
        return 0.0

    return (mean_excess / downside_dev) * math.sqrt(periods_per_year)


def calculate_max_drawdown(equity_curve: Sequence[float]) -> tuple[float, float]:
    """Calculate Maximum Drawdown in absolute currency and percentage.

    Returns:
        (max_drawdown_amount, max_drawdown_percentage)
    """
    if not equity_curve:
        return 0.0, 0.0

    peak = equity_curve[0]
    max_dd = 0.0
    max_dd_pct = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        dd = peak - value
        dd_pct = (dd / peak) * 100.0 if peak > 0 else 0.0

        if dd > max_dd:
            max_dd = dd
        if dd_pct > max_dd_pct:
            max_dd_pct = dd_pct

    return round(max_dd, 2), round(max_dd_pct, 2)
