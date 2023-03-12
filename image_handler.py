import requests
import os

from datetime import timedelta, datetime
from enum import Enum

from PIL import Image, ImageDraw, ImageFont
from polyline import decode

import matplotlib.pyplot as plt

from api_handler import APICaller
from templates_handler import Constants
from log_handler import Logger, LogTemplates

logger = Logger(__name__)


class ImageProperties(Enum):
    NAME_FONT = ImageFont.truetype(
        os.path.join(Constants.FONTS_DIR.value, "lsr.ttf"), 50
    )
    DATE_FONT = ImageFont.truetype(
        os.path.join(Constants.FONTS_DIR.value, "lsb.ttf"), 30
    )
    STATS_FONT = ImageFont.truetype(
        os.path.join(Constants.FONTS_DIR.value, "lsr.ttf"), 70
    )
    FONT_COLOR = (255, 255, 255)


LOCALE = {
    "en": {
        "distance": " km",
        "speed": " km/h",
        "elevation": " m",
    },
    "ru": {
        "distance": " км",
        "speed": " км/ч",
        "elevation": " м",
    },
}


class Stories:
    """Class for creating Instagram stories image from Strava activities.
    Args:
        telegram_id (int): user's telegram id
        activity_id (int): the id of the activity to be processed
        lang (str): user's language code
    """

    def __init__(self, telegram_id: int, activity_id: int, lang: str):
        self.telegram_id = telegram_id
        self.activity_id = activity_id
        self.lang = lang
        self.image_filepath = None
        self.route_filepath = None

        caller = APICaller(telegram_id)
        self.raw_data = caller.raw_data(get_activity=activity_id)

        self.create_images()
        self.prepare_stats()
        self.select_template()
        self.add_stats()

    def create_images(self):
        """Downloads activity image and route polyline and saves them to the files."""
        image_url = None
        try:
            image_url = self.raw_data["photos"]["primary"]["urls"]["600"]
        except Exception:
            logger.error(
                LogTemplates[__name__].CANT_GET_IMAGE_URL.format(self.activity_id)
            )
            pass
        if image_url:
            self.image_filepath = os.path.join(
                Constants.IMAGE_PATH.value, f"{self.activity_id}_photo.png"
            )
            with open(self.image_filepath, "wb") as f:
                f.write(requests.get(image_url).content)
            logger.debug(LogTemplates[__name__].SAVED_IMAGE.format(self.image_filepath))

        try:
            polyline = self.raw_data["map"]["polyline"]
        except KeyError:
            logger.error(
                LogTemplates[__name__].CANT_GET_POLYLINE.format(self.activity_id)
            )
            pass
        if polyline:
            points = decode(polyline)
            latitudes = [point[0] for point in points]
            longitudes = [point[1] for point in points]
            fig, ax = plt.subplots()
            ax.plot(longitudes, latitudes, color="white", linewidth=2)
            fig.patch.set_alpha(0.0)
            ax.set_axis_off()
            self.route_filepath = os.path.join(
                Constants.IMAGE_PATH.value, f"{self.activity_id}_route.png"
            )
            plt.savefig(self.route_filepath, transparent=True)
            logger.debug(LogTemplates[__name__].SAVED_ROUTE.format(self.route_filepath))

    def prepare_stats(self):
        """Extracts and prepares activity stats for the image."""
        self.name = self.raw_data.get("name")
        date = datetime.strptime(
            self.raw_data.get("start_date_local"), "%Y-%m-%dT%H:%M:%SZ"
        )
        self.date = datetime.strftime(date, "%Y-%m-%d %H:%m")
        self.distance = str(round(self.raw_data.get("distance") / 1000, 2))
        self.time = str(timedelta(seconds=self.raw_data.get("moving_time")))
        self.elevation = str(round(self.raw_data.get("total_elevation_gain")))

        self.type = self.raw_data.get("type")
        if self.type == "Run":
            pace = datetime.strptime(
                (
                    str(
                        timedelta(
                            seconds=(round(1000 / self.raw_data.get("average_speed")))
                        )
                    )
                ),
                "%H:%M:%S",
            )
            self.speed = datetime.strftime(pace, "%M:%S")
            logger.debug(
                LogTemplates[__name__].PACE_CALCULATED.format(self.activity_id)
            )
        else:
            self.speed = str(round((self.raw_data.get("average_speed") * 3.6), 2))
            logger.debug(
                LogTemplates[__name__].SPEED_CALCULATED.format(self.activity_id)
            )

        self.heartrate = str(round(self.raw_data.get("average_heartrate")))
        self.achievements = str(self.raw_data.get("achievement_count"))

        self.distance += LOCALE[self.lang]["distance"]
        if self.type != "Run":
            self.speed += LOCALE[self.lang]["speed"]
        self.elevation += LOCALE[self.lang]["elevation"]
        logger.debug(LogTemplates[__name__].STATS_PREPARED.format(self.activity_id))

    def select_template(self):
        """Selects template for the image depending on the activity type and optional fields."""
        if self.heartrate and self.achievements:
            self.template = os.path.join(
                Constants.STORIES_TEMPLATES.value, "stories_hr_ac.png"
            )
        elif self.heartrate:
            self.template = os.path.join(
                Constants.STORIES_TEMPLATES.value, "stories_hr.png"
            )
        elif self.achievements:
            self.template = os.path.join(
                Constants.STORIES_TEMPLATES.value, "stories_ac.png"
            )
        else:
            self.template = os.path.join(
                Constants.STORIES_TEMPLATES.value, "stories.png"
            )
        logger.debug(LogTemplates[__name__].TEMPLATE_SELECTED.format(self.template))

    def add_stats(self):
        """Adds stats to the template."""
        self.story_image = Image.open(self.template)
        draw = ImageDraw.Draw(self.story_image)

        draw.text(
            (540, 40),
            self.name,
            font=ImageProperties.NAME_FONT.value,
            fill=ImageProperties.FONT_COLOR.value,
            anchor="mm",
        )
        draw.text(
            (540, 110),
            self.date,
            font=ImageProperties.DATE_FONT.value,
            fill=ImageProperties.FONT_COLOR.value,
            anchor="mm",
        )
        draw.text(
            (166, 245),
            self.distance,
            font=ImageProperties.STATS_FONT.value,
            fill=ImageProperties.FONT_COLOR.value,
            anchor="lt",
        )
        draw.text(
            (166, 425),
            self.time,
            font=ImageProperties.STATS_FONT.value,
            fill=ImageProperties.FONT_COLOR.value,
            anchor="lt",
        )
        draw.text(
            (924, 245),
            self.speed,
            font=ImageProperties.STATS_FONT.value,
            fill=ImageProperties.FONT_COLOR.value,
            anchor="rt",
        )
        draw.text(
            (924, 425),
            self.elevation,
            font=ImageProperties.STATS_FONT.value,
            fill=ImageProperties.FONT_COLOR.value,
            anchor="rt",
        )
        if self.heartrate:
            draw.text(
                (166, 1425),
                self.heartrate,
                font=ImageProperties.STATS_FONT.value,
                fill=ImageProperties.FONT_COLOR.value,
                anchor="lt",
            )
            logger.debug(LogTemplates[__name__].HEARTRATE_ADDED.format(self.heartrate))
        if self.achievements:
            draw.text(
                (924, 1425),
                self.achievements,
                font=ImageProperties.STATS_FONT.value,
                fill=ImageProperties.FONT_COLOR.value,
                anchor="rt",
            )
            logger.debug(
                LogTemplates[__name__].ACHIEVEMENTS_ADDED.format(self.achievements)
            )
        logger.debug(LogTemplates[__name__].STATS_ADDED.format(self.activity_id))

    def create_story(self) -> str:
        """Prepares and inserts activity image and route map into the template.

        Returns:
            str: returns the path to the created story image
        """
        if not self.image_filepath or not self.route_filepath:
            return

        try:
            image = Image.open(self.image_filepath)
            self.story_image.paste(image, (156, 672, 924, 1248))
        except Exception as error:
            logger.error(LogTemplates[__name__].CANT_ADD_IMAGE.format(error))

        route = Image.open(self.route_filepath).convert("RGBA")
        width, height = route.size
        scale = round(min((768 / width), (310 / height)), 2)
        logger.debug(LogTemplates[__name__].CALCULATED_SCALE.format(scale))

        width = int(width * scale)
        height = int(height * scale)
        route = route.resize((width, height))
        logger.debug(LogTemplates[__name__].RESIZED_ROUTE.format(width, height))

        x_offset = int((768 - width) / 2)
        y_offset = int((310 - height) / 2)

        self.story_image.paste(
            route,
            (
                156 + x_offset,
                1510 + y_offset,
                156 + x_offset + width,
                1510 + y_offset + height,
            ),
            mask=route,
        )

        story_filepath = os.path.join(
            Constants.IMAGE_PATH.value, f"{self.activity_id}_story.png"
        )

        self.story_image.save(story_filepath)
        logger.info(LogTemplates[__name__].STORY_CREATED.format(story_filepath))

        try:
            os.remove(self.image_filepath)
            os.remove(self.route_filepath)
        except FileNotFoundError as error:
            logger.error(LogTemplates[__name__].CANT_REMOVE_FILES.format(error))
            pass

        return story_filepath
