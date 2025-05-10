# app/core/features/feature_engineer.py

import pandas as pd
import numpy as np
import time
from functools import lru_cache
from typing import Dict, Any


@lru_cache(maxsize=128)
def get_ewm_weights(span, adjust, n):
    """Cache EWM weights for reuse across calculations."""
    alpha = 2 / (span + 1)
    if adjust:
        weights = np.power(1 - alpha, np.arange(n, 0, -1))
        weights /= weights.sum()
    else:
        weights = np.ones(n) * alpha * (1 - alpha) ** np.arange(n)
    return weights


def fast_ewm(series, span, adjust=False):
    """Faster exponential weighted moving average calculation."""
    values = series.values
    n = len(values)
    result = np.full_like(values, np.nan, dtype=np.float64)

    # Handle beginning of the series with NaN values
    nan_mask = np.isnan(values)
    first_valid = np.argmin(nan_mask) if np.any(~nan_mask) else n

    if first_valid < n:
        values_to_process = values[first_valid:]
        weights = get_ewm_weights(span, adjust, len(values_to_process))

        # Calculate the weighted average
        for i in range(first_valid, n):
            window = values[max(first_valid, i - len(weights) + 1) : i + 1]
            if len(window) > 0:
                w = weights[-len(window) :]
                # Fix for division by zero
                if np.sum(w) > 0:
                    result[i] = np.sum(window * w) / np.sum(w)
                else:
                    result[i] = np.nan

    return pd.Series(result, index=series.index)


def calculate_rsi(series, period=14):
    """Calculate RSI indicator with optimized numpy operations."""
    # Convert to numpy for faster operations
    prices = series.values
    deltas = np.diff(prices)
    seed = deltas[: period + 1]

    # Calculate gains and losses
    up = seed[seed >= 0].sum() / period
    down = -seed[seed < 0].sum() / period

    if down == 0:  # Handle division by zero
        return np.full_like(prices, 100.0)

    rs = up / down
    rsi = np.zeros_like(prices)
    rsi[: period + 1] = 100.0 - (100.0 / (1.0 + rs))

    # Calculate RSI for remaining prices
    for i in range(period + 1, len(prices)):
        delta = deltas[i - 1]

        if delta > 0:
            upval = delta
            downval = 0.0
        else:
            upval = 0.0
            downval = -delta

        up = (up * (period - 1) + upval) / period
        down = (down * (period - 1) + downval) / period

        rs = up / down if down != 0 else float("inf")
        rsi[i] = 100.0 - (100.0 / (1.0 + rs))

    return pd.Series(rsi, index=series.index)


def calculate_features(eod_df: pd.DataFrame) -> pd.DataFrame:
    """Calculate features with optimized operations."""
    start_time = time.time()

    # Sort data chronologically
    df = eod_df.copy().sort_values(["symbol_id", "date"]).reset_index(drop=True)

    # Basic features
    df["week_day"] = pd.to_datetime(df["date"]).dt.weekday

    # Vectorized calculations for price-based features
    high, low, close, open_price = df["high"].values, df["low"].values, df["close"].values, df["open"].values

    # Calculate HL range vectorized
    hl_range = (high - low) / np.where(close == 0, np.nan, close)
    df["hl_range"] = hl_range

    # Group operations by symbol
    for symbol_id, group in df.groupby("symbol_id"):
        idx = group.index

        # Calculate gap percentage
        df.loc[idx, "gap_pct"] = group["open"] / group["close"].shift(1) - 1

        # Body to range ratio
        body = np.abs(group["close"] - group["open"])
        df.loc[idx, "body_to_range_ratio"] = body / (group["high"] - group["low"]).replace(0, np.nan)

        # EMA and distance calculations
        ema5 = fast_ewm(group["close"], span=5, adjust=False)
        df.loc[idx, "distance_from_ema_5"] = group["close"] - ema5

        # 3-day return
        df.loc[idx, "return_3d"] = group["close"].pct_change(3)

        # Range compression using numpy operations
        hl_range_rolling = group["hl_range"].rolling(3).mean()
        df.loc[idx, "range_compression_ratio"] = group["hl_range"] / hl_range_rolling

        # ATR calculation
        df.loc[idx, "atr_5"] = group["hl_range"].rolling(5).mean()

        # Volume spike ratio
        vol_rolling = group["volume"].rolling(3).mean()
        df.loc[idx, "volume_spike_ratio"] = group["volume"] / vol_rolling

        # Bollinger band width for volatility squeeze
        rolling_mean = group["close"].rolling(20).mean()
        rolling_std = group["close"].rolling(20).std()
        bb_width = (rolling_mean + 2 * rolling_std - (rolling_mean - 2 * rolling_std)) / rolling_mean
        df.loc[idx, "volatility_squeeze"] = bb_width / bb_width.rolling(20).mean()

        # Trend zone strength
        up_move = group["high"].diff()
        down_move = group["low"].diff().abs()
        trend_strength = np.where(up_move > down_move, up_move, 0)
        df.loc[idx, "trend_zone_strength"] = pd.Series(trend_strength, index=idx).rolling(14).mean()

        # RSI calculation
        df.loc[idx, "rsi_14"] = calculate_rsi(group["close"], period=14)

        # EMA 50
        ema_50 = fast_ewm(group["close"], span=50, adjust=False)
        df.loc[idx, "ema_50"] = ema_50
        df.loc[idx, "close_ema50_gap_pct"] = (group["close"] - ema_50) / ema_50 * 100

        # Previous close and open gap - Fixed to handle missing values
        prev_close = group["close"].shift(1)
        df.loc[idx, "prev_close"] = prev_close

        # Calculate open_gap_pct safely
        mask = prev_close.notna() & (prev_close != 0)
        df.loc[idx, "open_gap_pct"] = 0  # Default value
        df.loc[idx[mask], "open_gap_pct"] = ((group["open"] - prev_close) / prev_close * 100)[mask]

        # MACD calculation
        ema_12 = fast_ewm(group["close"], span=12, adjust=False)
        ema_26 = fast_ewm(group["close"], span=26, adjust=False)
        df.loc[idx, "macd_line"] = ema_12 - ema_26
        df.loc[idx, "macd_signal"] = fast_ewm(df.loc[idx, "macd_line"], span=9, adjust=False)
        df.loc[idx, "macd_histogram"] = df.loc[idx, "macd_line"] - df.loc[idx, "macd_signal"]

        # True range calculation
        high_close = np.abs(group["high"] - group["close"].shift())
        low_close = np.abs(group["low"] - group["close"].shift())
        hl = group["high"] - group["low"]
        df.loc[idx, "true_range"] = np.maximum.reduce([hl, high_close, low_close])

        # ATR 14 and normalized ATR
        df.loc[idx, "atr_14"] = df.loc[idx, "true_range"].rolling(14).mean()
        df.loc[idx, "atr_14_normalized"] = df.loc[idx, "atr_14"] / group["close"]

    # Select and return the calculated features
    feature_columns = ["symbol_id", "date", "week_day", "volatility_squeeze", "trend_zone_strength", "range_compression_ratio", "volume_spike_ratio", "body_to_range_ratio", "distance_from_ema_5", "gap_pct", "return_3d", "atr_5", "hl_range", "rsi_14", "close_ema50_gap_pct", "open_gap_pct", "macd_histogram", "atr_14_normalized", "change_percent"]  # Using existing change_percent

    elapsed = time.time() - start_time
    print(f"Feature calculation completed in {elapsed:.2f} seconds for {len(df)} rows.")

    return df[feature_columns]


def calculate_features_for_symbol(eod_data: pd.DataFrame) -> pd.DataFrame:
    """
    Calculate features for a single symbol's EOD data.
    This is an optimized version for operation on a single symbol.
    """
    if eod_data.empty:
        return pd.DataFrame()

    # Ensure data is sorted by date
    df = eod_data.copy().sort_values("date").reset_index(drop=True)

    # Calculate features
    df["week_day"] = pd.to_datetime(df["date"]).dt.weekday
    df["hl_range"] = (df["high"] - df["low"]) / df["close"]

    # Gap percentage
    df["gap_pct"] = df["open"] / df["close"].shift(1) - 1

    # Body to range ratio
    body = np.abs(df["close"] - df["open"])
    df["body_to_range_ratio"] = body / (df["high"] - df["low"])

    # EMA calculations
    ema5 = fast_ewm(df["close"], span=5, adjust=False)
    df["distance_from_ema_5"] = df["close"] - ema5

    ema50 = fast_ewm(df["close"], span=50, adjust=False)
    df["ema_50"] = ema50
    df["close_ema50_gap_pct"] = (df["close"] - ema50) / ema50 * 100

    # RSI
    df["rsi_14"] = calculate_rsi(df["close"], period=14)

    # Returns
    df["return_3d"] = df["close"].pct_change(3)

    # Range compression
    df["range_compression_ratio"] = df["hl_range"] / df["hl_range"].rolling(3).mean()

    # ATR
    df["atr_5"] = df["hl_range"].rolling(5).mean()

    # Volume
    df["volume_spike_ratio"] = df["volume"] / df["volume"].rolling(3).mean()

    # Volatility squeeze
    rolling_mean = df["close"].rolling(20).mean()
    rolling_std = df["close"].rolling(20).std()
    bb_width = (rolling_mean + 2 * rolling_std - (rolling_mean - 2 * rolling_std)) / rolling_mean
    df["volatility_squeeze"] = bb_width / bb_width.rolling(20).mean()

    # Trend zone strength
    up_move = df["high"].diff()
    down_move = df["low"].diff().abs()
    trend_strength = np.where(up_move > down_move, up_move, 0)
    df["trend_zone_strength"] = pd.Series(trend_strength).rolling(14).mean()

    # MACD
    ema_12 = fast_ewm(df["close"], span=12, adjust=False)
    ema_26 = fast_ewm(df["close"], span=26, adjust=False)
    df["macd_line"] = ema_12 - ema_26
    df["macd_signal"] = fast_ewm(df["macd_line"], span=9, adjust=False)
    df["macd_histogram"] = df["macd_line"] - df["macd_signal"]

    # True range and ATR
    high_close = np.abs(df["high"] - df["close"].shift())
    low_close = np.abs(df["low"] - df["close"].shift())
    hl = df["high"] - df["low"]
    df["true_range"] = np.maximum.reduce([hl, high_close, low_close])
    df["atr_14"] = df["true_range"].rolling(14).mean()
    df["atr_14_normalized"] = df["atr_14"] / df["close"]

    # Previous close
    df["prev_close"] = df["close"].shift(1)

    # Open gap percentage
    mask = df["prev_close"].notna() & (df["prev_close"] != 0)
    df["open_gap_pct"] = 0
    df.loc[mask, "open_gap_pct"] = ((df["open"] - df["prev_close"]) / df["prev_close"] * 100)[mask]

    return df
