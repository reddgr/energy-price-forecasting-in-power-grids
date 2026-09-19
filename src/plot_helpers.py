import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import numpy as np
import pandas as pd


def plot_station_time_series(
	data,
	metric_name,
	trend_line=None,
	moving_average_days=None,
	figsize=None,
):
	"""Plot the row-wise mean of station time series with optional overlays."""
	if not isinstance(metric_name, str) or not metric_name.strip():
		raise ValueError("metric_name must be a non-empty string.")
	if not isinstance(data.index, pd.DatetimeIndex):
		raise TypeError("data index must be a pandas DatetimeIndex.")
	if data.empty:
		raise ValueError("data must contain at least one row and one column.")
	if not all(pd.api.types.is_numeric_dtype(data[column]) for column in data.columns):
		raise TypeError("data must contain only numeric station columns.")
	if trend_line is not None and (
		not isinstance(trend_line, (int, np.integer)) or trend_line < 1
	):
		raise ValueError("trend_line must be None or a positive polynomial degree.")
	if moving_average_days is not None and (
		not isinstance(moving_average_days, (int, np.integer))
		or moving_average_days < 1
	):
		raise ValueError("moving_average_days must be None or a positive integer.")

	time_series = data.mean(axis=1).dropna()
	if time_series.empty:
		raise ValueError("data must contain at least one row with numeric values.")

	metric_name = metric_name.strip()
	fig, ax = plt.subplots(figsize=figsize)
	ax.plot(
		time_series.index,
		time_series,
		color="tab:blue",
		label=f"Average {metric_name}",
	)

	moving_average = None
	if moving_average_days is not None:
		moving_average = time_series.rolling(
			moving_average_days, center=True
		).mean()
		ax.plot(
			moving_average.index,
			moving_average,
			color="tab:orange",
			linewidth=2,
			label=f"{moving_average_days}-day m.a. of {metric_name}",
		)

	trend_values = None
	trend_coefficients = None
	if trend_line is not None:
		years_elapsed = (time_series.index - time_series.index.min()).days / 365.25
		trend_coefficients = np.polyfit(
			years_elapsed, time_series.to_numpy(), trend_line
		)
		trend_values = np.polyval(trend_coefficients, years_elapsed)
		ax.plot(
			time_series.index,
			trend_values,
			color="tab:red",
			linewidth=1,
			linestyle=':',
			label=f"{metric_name} poly. trend (d. {trend_line})",
		)

	ax.set_title(f"Avg. {metric_name} across stations")
	ax.set_xlabel("Date")
	ax.set_ylabel(f"Average {metric_name}")
	ax.grid(True, which="major", axis="both", linestyle="--", alpha=0.9)
	ax.xaxis.set_major_locator(mdates.YearLocator())
	ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y"))
	ax.tick_params(axis="x", labelrotation=45)
	ax.legend(loc="upper center", bbox_to_anchor=(0.5, -0.32), ncol=3)
	fig.tight_layout(rect=(0, 0.15, 1, 1))

	return {
		"figure": fig,
		"axes": ax,
		"time_series": time_series,
		"moving_average": moving_average,
		"trend_values": trend_values,
		"trend_coefficients": trend_coefficients,
	}
