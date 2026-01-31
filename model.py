
"""Training and inference helpers for smart-meter anomaly detection.

Uses Isolation Forest to detect anomalies without labeled theft data.
Learns normal usage patterns and identifies rare/different points.
"""

import argparse
from pathlib import Path
from typing import Iterable, Optional

import joblib
import pandas as pd
from sklearn.compose import ColumnTransformer
from sklearn.ensemble import IsolationForest
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder, StandardScaler

from preprocess import preprocess


FEATURE_COLS = [
	"kwh_denoised",
	"power",
	"rolling_avg_power",
	"deviation_from_normal",
	"voltage",
	"current",
	"energy_kwh",
]
CAT_COLS = ["meter_id"]


def load_data(path: Path) -> pd.DataFrame:
	df = pd.read_csv(path, parse_dates=["timestamp"])
	return df


def build_dataset(df: pd.DataFrame) -> pd.DataFrame:
	"""Prepare features for unsupervised anomaly detection."""
	processed = preprocess(df)
	X = processed[FEATURE_COLS + CAT_COLS].dropna()
	return X


def make_pipeline() -> Pipeline:
	numeric_features = FEATURE_COLS
	categorical_features = CAT_COLS

	numeric_transformer = Pipeline(
		steps=[
			("scaler", StandardScaler()),
		]
	)

	categorical_transformer = Pipeline(
		steps=[
			("onehot", OneHotEncoder(handle_unknown="ignore")),
		]
	)

	preprocessor = ColumnTransformer(
		transformers=[
			("num", numeric_transformer, numeric_features),
			("cat", categorical_transformer, categorical_features),
		]
	)

	# Isolation Forest: learns normal patterns, finds rare/different points
	# contamination: expected proportion of anomalies (5% default)
	# n_estimators: number of isolation trees
	clf = IsolationForest(
		n_estimators=100,
		contamination=0.05,
		max_samples='auto',
		n_jobs=-1,
		random_state=42,
	)

	return Pipeline(
		steps=[
			("preprocessor", preprocessor),
			("model", clf),
		]
	)


def train_model(df: pd.DataFrame):
	"""Train Isolation Forest on normal usage patterns (unsupervised)."""
	X = build_dataset(df)
	
	pipe = make_pipeline()
	pipe.fit(X)
	
	# Get predictions and scores for summary
	predictions = pipe.predict(X)
	scores = pipe.decision_function(X)
	
	n_normal = (predictions == 1).sum()
	n_anomaly = (predictions == -1).sum()
	
	summary = f"""
Training complete:
- Total samples: {len(X)}
- Normal (1): {n_normal} ({n_normal/len(X)*100:.1f}%)
- Anomaly (-1): {n_anomaly} ({n_anomaly/len(X)*100:.1f}%)
- Anomaly score range: [{scores.min():.3f}, {scores.max():.3f}]
"""
	
	return pipe, summary


def save_model(model: Pipeline, path: Path) -> None:
	path.parent.mkdir(parents=True, exist_ok=True)
	joblib.dump(model, path)


def load_model(path: Path) -> Pipeline:
	return joblib.load(path)


def predict(model: Pipeline, rows: Iterable[dict]) -> pd.DataFrame:
	"""Predict anomalies and compute anomaly scores.
	
	Returns:
		DataFrame with:
		- prediction: 1 (Normal) or -1 (Anomaly)
		- anomaly_score: How strange/rare the reading is (lower = more anomalous)
	"""
	df = pd.DataFrame(rows)
	processed = preprocess(df)
	X = processed[FEATURE_COLS + CAT_COLS]
	
	# Predict: 1 = Normal, -1 = Anomaly
	predictions = model.predict(X)
	
	# Anomaly score: negative values indicate anomalies
	# Lower score = more anomalous
	scores = model.decision_function(X)
	
	processed["prediction"] = predictions
	processed["anomaly_score"] = scores
	
	return processed


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Train Isolation Forest for anomaly detection")
	parser.add_argument("--data", type=str, default="data/live_data.csv", help="CSV with meter readings")
	parser.add_argument("--model-out", type=str, default="artifacts/anomaly_model.joblib", help="Where to store trained model")
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	data_path = Path(args.data)
	model_out = Path(args.model_out)

	df = load_data(data_path)
	model, summary = train_model(df)
	save_model(model, model_out)
	print("Model saved to", model_out)
	print(summary)


if __name__ == "__main__":
	main()

