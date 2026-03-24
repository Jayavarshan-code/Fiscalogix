import pandas as pd
import numpy as np
from pytorch_forecasting import TimeSeriesDataSet, TemporalFusionTransformer
from pytorch_forecasting.metrics import QuantileLoss
import lightning.pytorch as pl

def build_tft_dataset(df):
    """
    Enterprise Data Module for TFT.
    Normalizes time-series and identifies categorical/continuous covariates.
    """
    # 1. Ensure time index is integer
    df["time_idx"] = (df["timestamp"] - df["timestamp"].min()).dt.total_seconds() // 3600
    df["time_idx"] = df["time_idx"].astype(int)
    
    # 2. Define the Dataset structure
    max_prediction_length = 24 # 24 hours
    max_encoder_length = 72 # 3 days history
    
    dataset = TimeSeriesDataSet(
        df,
        time_idx="time_idx",
        target="demand",
        group_ids=["sku_id"],
        min_encoder_length=max_encoder_length // 2,
        max_encoder_length=max_encoder_length,
        min_prediction_length=1,
        max_prediction_length=max_prediction_length,
        # Categorical Covariates (e.g. Region, Category)
        static_categoricals=["region"],
        time_varying_known_categoricals=[],
        # Continuous Covariates (e.g. Market indices)
        time_varying_known_reals=["time_idx"],
        time_varying_unknown_reals=["demand"],
        add_relative_time_idx=True,
        add_target_scales=True,
        add_encoder_generation_indices=True,
    )
    
    return dataset

def create_tft_model(dataset):
    """
    Initializes a Temporal Fusion Transformer with Self-Attention.
    """
    tft = TemporalFusionTransformer.from_dataset(
        dataset,
        learning_rate=0.03,
        hidden_size=16,
        attention_head_size=4,
        dropout=0.1,
        hidden_continuous_size=8,
        output_size=7, # 7 quantiles for risk-adjusted forecasting
        loss=QuantileLoss(),
        log_interval=10,
        reduce_on_plateau_patience=4,
    )
    return tft
