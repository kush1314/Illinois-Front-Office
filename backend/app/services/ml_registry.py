"""Single trained ML pipeline shared across the whole app.

Routes and chat service both import from here so they always
reference the same in-memory instance trained at startup.
"""
from __future__ import annotations

import pandas as pd

from app.services.ml import TransferSuccessPipeline

_pipeline: TransferSuccessPipeline = TransferSuccessPipeline()


def get_pipeline() -> TransferSuccessPipeline:
    return _pipeline


def train_pipeline(historical_df: pd.DataFrame) -> None:
    _pipeline.train(historical_df)


def ml_predict(player_df: pd.DataFrame) -> dict[str, object] | None:
    """Return ML predictions for a player row, or None if the model is not trained."""
    try:
        return _pipeline.predict_player(player_df)
    except Exception:
        return None
