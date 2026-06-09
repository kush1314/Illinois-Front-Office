import pandas as pd
from sklearn.metrics.pairwise import cosine_similarity
from sklearn.preprocessing import StandardScaler


SIMILARITY_FEATURES = [
    "height_inches",
    "usage_rate",
    "true_shooting",
    "three_pt_pct",
    "ft_pct",
    "assist_rate",
    "turnover_rate",
    "offensive_rebound_rate",
    "defensive_rebound_rate",
    "block_rate",
    "steal_rate",
    "minutes",
]


def find_similar_players(players: pd.DataFrame, player_name: str, limit: int = 5) -> pd.DataFrame:
    feature_frame = players[SIMILARITY_FEATURES].fillna(players[SIMILARITY_FEATURES].median())
    scaled = StandardScaler().fit_transform(feature_frame)
    idx = players.index[players["player_name"] == player_name][0]
    scores = cosine_similarity([scaled[idx]], scaled)[0]
    result = players.copy()
    result["similarity"] = scores
    return (
        result[result["player_name"] != player_name]
        .sort_values("similarity", ascending=False)
        .head(limit)
        [["player_name", "school", "position", "transfer_success_score", "similarity"]]
    )
