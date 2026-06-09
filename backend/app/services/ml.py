"""
Transfer Success ML Pipeline — RF + XGBoost + Neural Network ensemble.

Why NOT TensorFlow / PyTorch for this problem
─────────────────────────────────────────────
TensorFlow and PyTorch shine when you have:
  • Large datasets (100k+ rows) — we have ~2,000–4,000 labeled transfers
  • Raw input (images, text, audio) — our input is 16 numeric stat columns
  • Sequential patterns (LSTM) — we predict a single-season outcome

For structured tabular data at this scale, Random Forest + XGBoost beats
deep learning in virtually every published benchmark.  Adding sklearn's
MLPRegressor (a proper multi-layer perceptron / neural network) gives us
the neural-net component of the ensemble without TF overhead.

The ensemble (weighted average of three models) outperforms any single model:
  RF:   robust to outliers, interpretable feature importance
  XGB:  gradient-boosted trees, best single-model on tabular data
  MLP:  neural network, captures non-linear feature interactions

What the model learns
─────────────────────
INPUT (16 features per player):
  previous_bpm, previous_bpm_conf_adj, ts_pct, usage_rate,
  assist_rate, turnover_rate, off_rebound_rate, def_rebound_rate,
  steal_rate, block_rate, vorp, games, minutes,
  conf_strength_from, conf_strength_to, conf_upgrade

OUTPUT (regression):
  future_bpm — what Box Plus/Minus will this player produce at new school?

OUTPUT (classification):
  transfer_success — will their BPM at new school be ≥ 0? (binary)

The conference adjustment features teach the model that moving from
a weak to a strong conference suppresses BPM, and vice-versa.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier, RandomForestRegressor
from sklearn.inspection import permutation_importance
from sklearn.metrics import (
    accuracy_score, mean_absolute_error, mean_squared_error,
    r2_score, roc_auc_score,
)
from sklearn.model_selection import KFold, cross_val_score, train_test_split
from sklearn.neural_network import MLPClassifier, MLPRegressor
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler

# ── Feature set ──────────────────────────────────────────────────────────────
FEATURES = [
    "previous_bpm",
    "previous_bpm_conf_adj",
    "ts_pct",
    "usage_rate",
    "assist_rate",
    "turnover_rate",
    "off_rebound_rate",
    "def_rebound_rate",
    "steal_rate",
    "block_rate",
    "vorp",
    "games",
    "minutes",
    "conf_strength_from",
    "conf_strength_to",
    "conf_upgrade",
]

# Fallback feature set for data that lacks the new conf-strength columns
FEATURES_LEGACY = [
    "weight", "minutes", "usage_rate", "ts_pct", "three_pt_pct",
    "ft_pct", "assist_rate", "turnover_rate", "off_rebound_rate",
    "def_rebound_rate", "steal_rate", "block_rate",
    "defensive_rating", "offensive_rating", "previous_bpm",
]


def _active_features(df: pd.DataFrame) -> list[str]:
    """Return whichever feature set the DataFrame supports."""
    if all(f in df.columns for f in FEATURES):
        return FEATURES
    return [f for f in FEATURES_LEGACY if f in df.columns]


@dataclass
class TrainedModels:
    # Regressors: predict future_bpm (continuous)
    rf_reg:  RandomForestRegressor
    xgb_reg: object | None          # XGBRegressor or None if not installed
    mlp_reg: Pipeline               # StandardScaler → MLPRegressor

    # Classifiers: predict transfer_success (binary)
    rf_cls:  RandomForestClassifier
    mlp_cls: Pipeline               # StandardScaler → MLPClassifier

    feature_names:    list[str]
    feature_importance: dict[str, float]
    performance:      dict[str, object]
    trained_on_rows:  int = 0


class TransferSuccessPipeline:
    def __init__(self) -> None:
        self.models: TrainedModels | None = None

    # ── Training ─────────────────────────────────────────────────────────────

    def train(self, historical_df: pd.DataFrame) -> None:
        data = historical_df.dropna(
            subset=["future_bpm", "ts_pct", "usage_rate", "previous_bpm"]
        ).copy()

        feat_cols = _active_features(data)
        X = data[feat_cols].fillna(data[feat_cols].median())

        y_reg = data["future_bpm"].astype(float)

        # Classification target: success = BPM ≥ 0 at destination
        if "transfer_success" in data.columns:
            y_cls = data["transfer_success"].astype(int)
        else:
            y_cls = (data["future_bpm"] >= 0).astype(int)

        X_tr, X_te, yr_tr, yr_te, yc_tr, yc_te = train_test_split(
            X, y_reg, y_cls, test_size=0.2, random_state=42, stratify=y_cls
        )

        # ── Random Forest (regression) ────────────────────────────────────
        rf_reg = RandomForestRegressor(
            n_estimators=400, max_features="sqrt",
            min_samples_leaf=2, n_jobs=-1, random_state=42,
        )
        rf_reg.fit(X_tr, yr_tr)

        # ── XGBoost (regression) ──────────────────────────────────────────
        xgb_reg = None
        try:
            from xgboost import XGBRegressor
            xgb_reg = XGBRegressor(
                n_estimators=350, max_depth=4, learning_rate=0.04,
                subsample=0.85, colsample_bytree=0.85,
                objective="reg:squarederror", random_state=42,
                verbosity=0,
            )
            xgb_reg.fit(X_tr, yr_tr)
        except Exception:
            xgb_reg = None

        # ── MLP Neural Network (regression) ──────────────────────────────
        # Architecture: 3-layer MLP (64 → 32 → 16 neurons)
        # StandardScaler is required before MLP — packed into a Pipeline.
        mlp_reg = Pipeline([
            ("scaler", StandardScaler()),
            ("mlp", MLPRegressor(
                hidden_layer_sizes=(64, 32, 16),
                activation="relu",
                solver="adam",
                max_iter=1000,
                early_stopping=True,
                validation_fraction=0.15,
                random_state=42,
                learning_rate_init=0.001,
            )),
        ])
        mlp_reg.fit(X_tr, yr_tr)

        # ── Random Forest (classifier) ────────────────────────────────────
        rf_cls = RandomForestClassifier(
            n_estimators=300, max_features="sqrt",
            min_samples_leaf=2, n_jobs=-1, random_state=42,
        )
        rf_cls.fit(X_tr, yc_tr)

        # ── MLP Neural Network (classifier) ──────────────────────────────
        mlp_cls = Pipeline([
            ("scaler", StandardScaler()),
            ("mlp", MLPClassifier(
                hidden_layer_sizes=(64, 32),
                activation="relu",
                solver="adam",
                max_iter=1000,
                early_stopping=True,
                validation_fraction=0.15,
                random_state=42,
            )),
        ])
        mlp_cls.fit(X_tr, yc_tr)

        # ── Feature importance (permutation-based, model-agnostic) ───────
        perm = permutation_importance(rf_reg, X_te, yr_te, n_repeats=8, random_state=42, n_jobs=-1)
        ranking = np.argsort(perm.importances_mean)[::-1]
        importance = {feat_cols[i]: float(perm.importances_mean[i]) for i in ranking}

        # ── Holdout evaluation ────────────────────────────────────────────
        rf_pred  = rf_reg.predict(X_te)
        mlp_pred = mlp_reg.predict(X_te)
        xgb_pred = xgb_reg.predict(X_te) if xgb_reg is not None else rf_pred

        # Ensemble: weighted average (XGB best, RF second, MLP third)
        ens_pred = 0.45 * xgb_pred + 0.35 * rf_pred + 0.20 * mlp_pred

        rf_cls_prob  = rf_cls.predict_proba(X_te)[:, 1]
        mlp_cls_prob = mlp_cls.predict_proba(X_te)[:, 1]
        ens_cls_prob = 0.55 * rf_cls_prob + 0.45 * mlp_cls_prob

        cv = KFold(n_splits=5, shuffle=True, random_state=42)

        def _reg_metrics(y_true: np.ndarray, y_pred: np.ndarray) -> dict:
            return {
                "r2":   round(float(r2_score(y_true, y_pred)), 4),
                "rmse": round(float(np.sqrt(mean_squared_error(y_true, y_pred))), 4),
                "mae":  round(float(mean_absolute_error(y_true, y_pred)), 4),
            }

        performance: dict[str, object] = {
            "holdout": {
                "random_forest":   _reg_metrics(yr_te, rf_pred),
                "xgboost":         _reg_metrics(yr_te, xgb_pred),
                "neural_network":  _reg_metrics(yr_te, mlp_pred),
                "ensemble":        _reg_metrics(yr_te, ens_pred),
                "classifier": {
                    "roc_auc":  round(float(roc_auc_score(yc_te, ens_cls_prob)), 4),
                    "accuracy": round(float(accuracy_score(yc_te, ens_cls_prob >= 0.5)), 4),
                },
            },
            "cross_validation": {
                "random_forest_r2": {
                    "mean": round(float(cross_val_score(rf_reg, X, y_reg, cv=cv, scoring="r2").mean()), 4),
                    "std":  round(float(cross_val_score(rf_reg, X, y_reg, cv=cv, scoring="r2").std()), 4),
                },
            },
            "training_rows": len(data),
            "feature_count": len(feat_cols),
            "model_stack": ["RandomForest", "XGBoost", "NeuralNetwork(MLP-3layer)"],
        }

        print(
            f"[ML] Trained on {len(data)} rows | "
            f"Ensemble R²={performance['holdout']['ensemble']['r2']} "  # type: ignore[index]
            f"RMSE={performance['holdout']['ensemble']['rmse']}"         # type: ignore[index]
        )

        self.models = TrainedModels(
            rf_reg=rf_reg, xgb_reg=xgb_reg, mlp_reg=mlp_reg,
            rf_cls=rf_cls, mlp_cls=mlp_cls,
            feature_names=feat_cols,
            feature_importance=importance,
            performance=performance,
            trained_on_rows=len(data),
        )

    # ── Inference ─────────────────────────────────────────────────────────────

    def predict_player(self, player_df: pd.DataFrame) -> dict[str, object]:
        if self.models is None:
            raise RuntimeError("Models not trained. Call train() first.")

        feat_cols = self.models.feature_names
        # Fill missing features with median-like defaults
        X = player_df.reindex(columns=feat_cols)
        for col in feat_cols:
            if col not in player_df.columns or player_df[col].isna().all():
                X[col] = 0.0
        X = X.fillna(0.0)

        rf_bpm  = float(self.models.rf_reg.predict(X)[0])
        mlp_bpm = float(self.models.mlp_reg.predict(X)[0])
        xgb_bpm = (
            float(self.models.xgb_reg.predict(X)[0])
            if self.models.xgb_reg is not None else rf_bpm
        )
        # Weighted ensemble BPM
        ensemble_bpm = 0.45 * xgb_bpm + 0.35 * rf_bpm + 0.20 * mlp_bpm

        # Success probabilities (ensemble)
        rf_prob  = float(self.models.rf_cls.predict_proba(X)[0, 1])
        mlp_prob = float(self.models.mlp_cls.predict_proba(X)[0, 1])
        success_prob = 0.55 * rf_prob + 0.45 * mlp_prob

        impact = float(np.clip(50 + ensemble_bpm * 6 + success_prob * 10, 0, 99))

        top6 = list(self.models.feature_importance.items())[:6]
        explanation = [{"feature": k, "importance": round(v, 4)} for k, v in top6]

        return {
            "transfer_success_probability":   round(success_prob * 100, 2),
            "future_bpm_prediction":          round(ensemble_bpm, 2),
            "rf_bpm_prediction":              round(rf_bpm, 2),
            "xgboost_bpm_prediction":         round(xgb_bpm, 2),
            "neural_network_bpm_prediction":  round(mlp_bpm, 2),
            "future_impact_score_prediction": round(impact, 2),
            "feature_importance":             explanation,
        }

    def get_model_performance(self) -> dict[str, object]:
        if self.models is None:
            raise RuntimeError("Models not trained.")
        return self.models.performance

    def is_trained(self) -> bool:
        return self.models is not None
