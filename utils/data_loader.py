from pathlib import Path

import joblib
import pandas as pd
import streamlit as st


BASE_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = BASE_DIR / "data"
MODELS_DIR = BASE_DIR / "models"

# CSV column names → names used throughout the app
_RENAME = {
    "ts_pct": "true_shooting",
    "off_rebound_rate": "offensive_rebound_rate",
    "def_rebound_rate": "defensive_rebound_rate",
    "previous_bpm": "prior_bpm",
    "public_transfer_rank": "public_rank",
    "class": "year",
}

# Feature names that the classifier was trained on (pre-rename CSV names)
_MODEL_FEATURES = [
    "previous_bpm", "ts_pct", "offensive_rating", "defensive_rating",
    "conf_upgrade", "usage_rate", "three_pt_pct", "ft_pct", "minutes",
    "assist_rate", "def_rebound_rate", "block_rate", "steal_rate", "turnover_rate",
]


def _apply_model(players: pd.DataFrame) -> pd.DataFrame:
    """Predict transfer success probability for each portal player using the
    trained GBM classifier (CV AUC = 0.896).  Stores the calibrated probability
    (0–100) in `ml_success_prob` so scoring.py can use it as the primary signal."""
    model_path = MODELS_DIR / "transfer_success_model.pkl"
    features_path = MODELS_DIR / "model_features.pkl"
    if not model_path.exists():
        return players
    try:
        model = joblib.load(model_path)
        features = joblib.load(features_path) if features_path.exists() else _MODEL_FEATURES
        x = players[features].fillna(players[features].median())
        probs = model.predict_proba(x)[:, 1]           # calibrated P(success)
        players = players.copy()
        players["ml_success_prob"] = (probs * 100).round(1)
    except Exception:
        players = players.copy()
        players["ml_success_prob"] = 50.0
    return players


@st.cache_data(show_spinner=False)
def load_players() -> pd.DataFrame:
    players = pd.read_csv(DATA_DIR / "players.csv")
    players = _apply_model(players)
    return players.rename(columns=_RENAME).sort_values("public_rank").reset_index(drop=True)


@st.cache_data(show_spinner=False)
def load_historical_transfers() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "historical_transfers.csv")


@st.cache_data(show_spinner=False)
def load_illinois_roster() -> pd.DataFrame:
    return pd.read_csv(DATA_DIR / "illinois_roster.csv")


@st.cache_data(show_spinner=False)
def load_model_metadata() -> dict:
    meta_path = MODELS_DIR / "model_metadata.pkl"
    if meta_path.exists():
        return joblib.load(meta_path)
    return {}
