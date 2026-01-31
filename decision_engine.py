
"""Decision Engine - Explains WHY readings are abnormal."""

import argparse
from pathlib import Path
from typing import Optional

import pandas as pd
import numpy as np

from model import CAT_COLS, FEATURE_COLS, load_model
from preprocess import preprocess


def load_data(path: Path) -> pd.DataFrame:
	df = pd.read_csv(str(path), parse_dates=["timestamp"])
	return df.sort_values("timestamp")


def detect_pattern(row: pd.Series, grouped_stats: pd.DataFrame) -> tuple[str, float, str]:
	meter_id = row["meter_id"]
	stats = grouped_stats.loc[meter_id]
	is_anomaly = row.get("prediction", 1) == -1
	anomaly_score = row.get("anomaly_score", 0)
	
	if "voltage" in row and "current" in row:
		voltage_drop = row["voltage"] < 0.85 * stats["voltage_mean"]
		high_current = row["current"] > 1.3 * stats["current_mean"]
		if voltage_drop and high_current:
			risk = 0.9 if is_anomaly else 0.6
			explanation = f"Voltage drop ({row['voltage']:.1f}V < {stats['voltage_mean']:.1f}V) with high current ({row['current']:.1f}A > {stats['current_mean']:.1f}A)"
			return ("theft", risk, explanation)
	
	if "power" in row:
		z_score = (row["power"] - stats["power_mean"]) / max(stats["power_std"], 0.001)
		if abs(z_score) > 3.0:
			risk = 0.7 if is_anomaly else 0.4
			explanation = f"Power spike detected: {row['power']:.1f}kW (z-score: {z_score:.2f})"
			return ("fault", risk, explanation)
	
	if "power" in row and "rolling_avg_power" in row:
		power_ratio = row["power"] / max(row["rolling_avg_power"], 0.001)
		if power_ratio < 0.5:
			risk = 0.8 if is_anomaly else 0.5
			explanation = f"Consumption {power_ratio*100:.0f}% of rolling average ({row['power']:.1f}kW < {row['rolling_avg_power']:.1f}kW)"
			return ("theft", risk, explanation)
	
	if is_anomaly:
		risk = 0.5
		explanation = f"AI detected anomaly (score: {anomaly_score:.3f})"
		return ("anomaly", risk, explanation)
	
	return ("normal", 0.0, "Normal operation")


def check_transformer_overload(df: pd.DataFrame, threshold: float = 0.7) -> pd.DataFrame:
	if "transformer_id" not in df.columns:
		return df
	df_copy = df.copy()
	grouped = df_copy.groupby(["transformer_id", "timestamp"])
	high_load = df_copy["power"] > df_copy.groupby("meter_id")["power"].transform("mean") * 1.2
	overload_pct = grouped["meter_id"].transform(lambda x: high_load[x.index].mean())
	transformer_overload = overload_pct > threshold
	df_copy.loc[transformer_overload, "pattern"] = "transformer_overload"
	df_copy.loc[transformer_overload, "risk_score"] = 0.85
	df_copy.loc[transformer_overload, "explanation"] = ("Transformer overload: " + (overload_pct * 100).round(0).astype(str) + "% of meters at high load")
	return df_copy


def analyze_patterns(processed: pd.DataFrame, model=None) -> pd.DataFrame:
	df = processed.copy()
	if model is not None:
		X = df[FEATURE_COLS + CAT_COLS]
		df["prediction"] = model.predict(X)
		df["anomaly_score"] = model.decision_function(X)
	else:
		df["prediction"] = 1
		df["anomaly_score"] = 0.0
	grouped_stats = df.groupby("meter_id").agg({"voltage": ["mean", "std"], "current": ["mean", "std"], "power": ["mean", "std"]})
	grouped_stats.columns = ["_".join(col).strip() for col in grouped_stats.columns]
	patterns = df.apply(lambda row: detect_pattern(row, grouped_stats), axis=1)
	df["pattern"] = patterns.apply(lambda x: x[0])
	df["risk_score"] = patterns.apply(lambda x: x[1])
	df["explanation"] = patterns.apply(lambda x: x[2])
	df = check_transformer_overload(df)
	return df


def run_engine(data_path: Path, model_path: Optional[Path], output_path: Optional[Path]) -> pd.DataFrame:
	# Convert string paths to Path objects if needed
	if isinstance(data_path, str):
		data_path = Path(data_path)
	if isinstance(model_path, str):
		model_path = Path(model_path)
	if isinstance(output_path, str):
		output_path = Path(output_path)
	
	raw = load_data(data_path)
	processed = preprocess(raw)
	model = None
	if model_path is not None and model_path.exists():
		model = load_model(model_path)
		print(f"Loaded model from {model_path}")
	else:
		print("No model provided, using rule-based detection only")
	decisions = analyze_patterns(processed, model=model)
	decisions["alert"] = decisions["pattern"] != "normal"
	decisions = decisions.sort_values("risk_score", ascending=False)
	if output_path is not None:
		output_path.parent.mkdir(parents=True, exist_ok=True)
		decisions.to_csv(output_path, index=False)
		print(f"Saved decisions to {output_path}")
	return decisions


def parse_args() -> argparse.Namespace:
	parser = argparse.ArgumentParser(description="Run decision engine on smart-meter CSV")
	parser.add_argument("--data", type=str, default="data/live_data.csv", help="Input CSV of readings")
	parser.add_argument("--model", type=str, default="artifacts/anomaly_model.joblib", help="Trained model path (optional)")
	parser.add_argument("--output", type=str, default="artifacts/decisions.csv", help="Where to write decisions")
	return parser.parse_args()


def main() -> None:
	args = parse_args()
	data_path = Path(args.data)
	model_path = Path(args.model) if args.model else None
	output_path = Path(args.output) if args.output else None
	decisions = run_engine(data_path, model_path, output_path)
	alerts = decisions[decisions["alert"]]
	pattern_counts = decisions["pattern"].value_counts()
	print(f"\n{'='*60}")
	print(f"Decision Engine Summary")
	print(f"{'='*60}")
	print(f"Total rows processed: {len(decisions)}")
	print(f"Alerts generated: {len(alerts)} ({len(alerts)/len(decisions)*100:.1f}%)")
	print(f"\nPattern breakdown:")
	for pattern, count in pattern_counts.items():
		pct = count / len(decisions) * 100
		print(f"  {pattern:20s}: {count:5d} ({pct:5.1f}%)")
	if len(alerts) > 0:
		print(f"\nTop 5 highest risk alerts:")
		for idx, row in alerts.head(5).iterrows():
			print(f"  • {row['meter_id']} - {row['pattern']} (risk: {row['risk_score']:.2f})")
			print(f"    └─ {row['explanation']}")


if __name__ == "__main__":
	main()

