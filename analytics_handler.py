import os

from datetime import datetime

import matplotlib.pyplot as plt

from matplotlib.dates import DateFormatter
from PIL import Image, ImageDraw, ImageFont

from api_handler import APICaller
from templates_handler import Constants
from log_handler import Logger, LogTemplates

logger = Logger(__name__)

LOCALE = {
    "en": {
        "Run": "Run",
        "Ride": "Ride",
        "distances": "Distance (km) forecast for {}",
        "times": "Time (h) forecast for {}",
        "elevations": "Elevation (m) forecast for {}",
    },
    "ru": {
        "Run": "Бег",
        "Ride": "Велосипед",
        "distances": "Прогноз расстояний (км) на {} год",
        "times": "Прогноз времени (ч) на {} год",
        "elevations": "Прогноз набора высоты (м) на {} год",
    },
}


class YearForecast:
    def __init__(self, telegram_id: int, lang: str):
        self.telegram_id = telegram_id
        self.lang = lang

        caller = APICaller(telegram_id)
        before = int(datetime.now().timestamp())
        after = int(datetime(datetime.now().year, 1, 1).timestamp())

        self.activities = caller.get_activities(after=after, before=before)
        self.stats_data = {
            "Ride": {"dates": [], "distances": [], "times": [], "elevations": []},
            "Run": {"dates": [], "distances": [], "times": [], "elevations": []},
        }

        self.prepare_exist_data()

        logger.debug(
            LogTemplates[__name__].RIDE_COUNT.format(
                self.telegram_id, len(self.stats_data["Ride"]["dates"])
            )
        )
        logger.debug(
            LogTemplates[__name__].RUN_COUNT.format(
                self.telegram_id, len(self.stats_data["Run"]["dates"])
            )
        )

        self.prepare_forecast_data()

    def prepare_exist_data(self):
        for activity in self.activities:
            activity_type = activity.get("type")
            try:
                self.stats_data[activity_type]["dates"].append(
                    datetime.strptime(
                        activity.get("start_date_local"), "%Y-%m-%dT%H:%M:%SZ"
                    ).date()
                )
                self.stats_data[activity_type]["distances"].append(
                    round(activity.get("distance") / 1000, 2)
                )
                self.stats_data[activity_type]["times"].append(
                    round(activity.get("moving_time") / 3600, 1)
                )
                self.stats_data[activity_type]["elevations"].append(
                    activity.get("total_elevation_gain")
                )
            except KeyError as error:
                # log error
                print(error)
                pass
        logger.debug(LogTemplates[__name__].READ_ACTIVITIES.format(self.telegram_id))

    def prepare_forecast_data(self):
        forecast_keys = ["distances", "times", "elevations"]

        for act_type in self.stats_data.values():
            if not act_type["dates"] or len(act_type["dates"]) == 1:
                continue

            last_date = act_type["dates"][-1]
            last_day = datetime(datetime.now().year, 12, 31).date()

            act_type["forecast_dates"] = [last_date, last_day]

            days_left = (last_day - last_date).days

            for key in forecast_keys:

                accumulated_values = [
                    round(sum(act_type[key][: i + 1]), 1)
                    for i in range(len(act_type[key]))
                ]

                act_type[f"accumulated_{key}"] = accumulated_values

                daily_increase = round(
                    (
                        (accumulated_values[-1] - accumulated_values[0])
                        / (act_type["dates"][-1] - act_type["dates"][0]).days
                    ),
                    3,
                )
                logger.debug(
                    LogTemplates[__name__].DAILY_INCREASE.format(daily_increase)
                )
                value_forecast = round(
                    accumulated_values[-1] + daily_increase * days_left, 1
                )

                act_type[f"forecast_{key}"] = [accumulated_values[-1], value_forecast]

    def create_forecast(self, stat_type: str) -> str:
        self.stat_type = stat_type

        run_data = self.stats_data["Run"]
        ride_data = self.stats_data["Ride"]

        if not run_data.get("forecast_dates") and not ride_data.get("forecast_dates"):
            print("HERE")
            return

        fig, ax = plt.subplots(figsize=(9.6, 7.2))
        fig.patch.set_facecolor("none")
        ax.set_facecolor("none")

        if len(run_data["dates"]) > 1:
            ax.plot(
                run_data["dates"],
                run_data[f"accumulated_{self.stat_type}"],
                label=LOCALE[self.lang]["Run"],
                linewidth=3,
                color="#555555",
            )
            ax.plot(
                run_data["forecast_dates"],
                run_data[f"forecast_{self.stat_type}"],
                linestyle="--",
                linewidth=3,
                color="#555555",
                label=None,
            )
            run_forecast_stat = round(run_data[f"forecast_{self.stat_type}"][-1])
            ax.annotate(
                f"{run_forecast_stat}",
                xy=(run_data["forecast_dates"][-1], run_forecast_stat),
                xytext=(10, 20),
                textcoords="offset points",
                fontsize=16,
                fontweight="bold",
                ha="right",
                va="center",
                color="#555555",
            )

        if len(ride_data["dates"]) > 1:
            ax.plot(
                ride_data["dates"],
                ride_data[f"accumulated_{self.stat_type}"],
                label=LOCALE[self.lang]["Ride"],
                linewidth=3,
                color="white",
            )
            ax.plot(
                ride_data["forecast_dates"],
                ride_data[f"forecast_{self.stat_type}"],
                linestyle="--",
                linewidth=3,
                color="white",
                label=None,
            )
            ride_forecast_stat = round(ride_data[f"forecast_{self.stat_type}"][-1])
            ax.annotate(
                f"{ride_forecast_stat}",
                xy=(ride_data["forecast_dates"][-1], ride_forecast_stat),
                xytext=(10, 20),
                textcoords="offset points",
                fontsize=16,
                fontweight="bold",
                ha="right",
                va="center",
                color="white",
            )

        ax.spines["right"].set_visible(False)
        ax.spines["top"].set_visible(False)

        ax.spines["bottom"].set_color("white")
        ax.spines["left"].set_color("white")
        ax.spines["bottom"].set_linewidth(2)
        ax.spines["left"].set_linewidth(2)

        date_format = DateFormatter("%Y-%m")
        ax.xaxis.set_major_formatter(date_format)

        ax.tick_params(axis="x", labelcolor="white", labelsize=14, colors="white")
        ax.tick_params(axis="y", labelcolor="white", labelsize=14, colors="white")

        ax.grid(which="both", color="grey", alpha=0.3, linestyle="--", linewidth=0.5)

        ax.legend(facecolor="none", frameon=False, fontsize=12, labelcolor="lightgrey")

        self.graph_filepath = os.path.join(
            Constants.IMAGE_PATH.value, f"{self.telegram_id}_{self.stat_type}_graph.png"
        )

        plt.savefig(self.graph_filepath)

        return self.add_images()

    def add_images(self):
        forecast_image = Image.open(
            os.path.join(Constants.FORECASTS_TEMPLATES.value, "forecast.png")
        )

        header_font = ImageFont.truetype(
            os.path.join(Constants.FONTS_DIR.value, "lsr.ttf"), 40
        )

        draw = ImageDraw.Draw(forecast_image)

        draw.text(
            (540, 90),
            LOCALE[self.lang][self.stat_type].format(str(datetime.now().year)),
            font=header_font,
            fill="white",
            anchor="mm",
        )

        graph_image = Image.open(self.graph_filepath).convert("RGBA")

        forecast_image.paste(graph_image, (60, 180, 1020, 900), mask=graph_image)

        forecast_filepath = os.path.join(
            Constants.IMAGE_PATH.value, f"{self.telegram_id}_{self.stat_type}.png"
        )

        forecast_image.save(forecast_filepath)

        try:
            os.remove(self.graph_filepath)
        except FileNotFoundError:
            pass

        return forecast_filepath
