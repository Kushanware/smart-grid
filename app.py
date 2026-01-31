
import pandas as pd
import plotly.express as px
import streamlit as st


@st.cache_data(show_spinner=False)
def load_data(path: str) -> pd.DataFrame:
	"""Load and tidy the smart meter readings."""
	df = pd.read_csv(path)
	df["timestamp"] = pd.to_datetime(df["timestamp"])
	df = df.sort_values("timestamp")
	return df


def filter_data(df: pd.DataFrame, meters: list[str], date_range: tuple[pd.Timestamp, pd.Timestamp]) -> pd.DataFrame:
	start, end = date_range
	mask = (df["timestamp"] >= start) & (df["timestamp"] <= end)
	if meters:
		mask &= df["meter_id"].isin(meters)
	return df.loc[mask]


def kpi_columns(filtered: pd.DataFrame) -> None:
	total_kwh = filtered["kwh"].sum()
	avg_kwh = filtered.groupby("meter_id")["kwh"].mean().mean() if not filtered.empty else 0
	peak_row = filtered.loc[filtered["kwh"].idxmax()] if not filtered.empty else None

	col1, col2, col3 = st.columns(3)
	col1.metric("Total kWh", f"{total_kwh:,.1f}")
	col2.metric("Avg kWh per meter", f"{avg_kwh:,.2f}")
	if peak_row is not None:
		col3.metric("Peak reading", f"{peak_row['kwh']:.1f} kWh", help=f"{peak_row['meter_id']} @ {peak_row['timestamp']:%Y-%m-%d %H:%M}")
	else:
		col3.metric("Peak reading", "–")


def render_charts(filtered: pd.DataFrame) -> None:
	if filtered.empty:
		st.info("No data for the selected filters.")
		return

	line_fig = px.line(
		filtered,
		x="timestamp",
		y="kwh",
		color="meter_id",
		markers=True,
		title="Load over time (15 min)"
	)
	line_fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))

	meter_totals = filtered.groupby("meter_id")[["kwh"]].sum().reset_index()
	bar_fig = px.bar(
		meter_totals,
		x="meter_id",
		y="kwh",
		text_auto=".1f",
		title="Total consumption by meter"
	)
	bar_fig.update_layout(margin=dict(l=10, r=10, t=40, b=10))

	hourly = filtered.set_index("timestamp").groupby("meter_id").resample("1H")["kwh"].sum().reset_index()
	heatmap_fig = px.density_heatmap(
		hourly,
		x="timestamp",
		y="meter_id",
		z="kwh",
		color_continuous_scale="Viridis",
		title="Hourly load heatmap"
	)
	heatmap_fig.update_layout(margin=dict(l=10, r=10, t=40, b=30))

	st.plotly_chart(line_fig, use_container_width=True, theme="streamlit")
	st.plotly_chart(bar_fig, use_container_width=True, theme="streamlit")
	st.plotly_chart(heatmap_fig, use_container_width=True, theme="streamlit")


def main() -> None:
	st.set_page_config(page_title="Smart Grid Dashboard", layout="wide")
	st.title("Smart Grid Dashboard")
	st.caption("Monitor meter-level energy consumption at 15-minute granularity.")

	data = load_data("data/live_data.csv")

	st.sidebar.header("Filters")
	meters = sorted(data["meter_id"].unique())
	selected_meters = st.sidebar.multiselect("Meters", options=meters, default=meters)

	min_date, max_date = data["timestamp"].min(), data["timestamp"].max()
	start_date, end_date = st.sidebar.date_input(
		"Date range",
		value=(min_date.date(), max_date.date()),
		min_value=min_date.date(),
		max_value=max_date.date(),
	)

	filtered = filter_data(
		data,
		meters=selected_meters,
		date_range=(pd.to_datetime(start_date), pd.to_datetime(end_date) + pd.Timedelta(days=1) - pd.Timedelta(minutes=15)),
	)

	kpi_columns(filtered)
	st.divider()
	render_charts(filtered)

	st.divider()
	st.subheader("Raw data")
	st.dataframe(filtered, use_container_width=True, height=300)


if __name__ == "__main__":
	main()

