"""Chore functions and classes for the sms-freiburg package."""

import json
import sys
from dataclasses import dataclass, fields
from datetime import datetime
from pathlib import Path
from pprint import pformat

import paho.mqtt.client as mqtt
import yaml
from loguru import logger

from .client import LoginError, SMSFreiburgClient


@dataclass(frozen=True)
class Common:
    mqtt_user: str
    mqtt_password: str
    mqtt_ip: str
    mqtt_port: int
    headless: bool


@dataclass(frozen=True)
class Profile:
    name: str
    user: str
    password: str
    topic: str


def setup_logger(verbose: int) -> None:
    levels = ["WARNING", "SUCCESS", "INFO", "DEBUG", "TRACE"]
    level = levels[min(verbose, len(levels) - 1)]
    logger.remove()
    format = (
        "<green>{time:HH:mm:ss}</green> | "
        "<level>{level: <8}</level> | "
        "<cyan>{function}</cyan>:<cyan>{line}</cyan> - "
        "<level>{message}</level>"
    )
    logger.add(sys.stderr, level=level, format=format)
    logger.debug(f"Logger set to {level} level.")


def load_config(conffile: Path, headless: bool = True, profile: str | None = None):
    logger.debug(f"Using {conffile}")
    data = yaml.safe_load(conffile.read_text()) or {}
    data["headless"] = headless

    profiles = data.get("profiles", [])

    selected = profiles
    if profile:
        selected = [item for item in profiles if item.get("name") == profile]

    if not selected:
        raise AttributeError(f"Unknown profile: {profile}")

    common = Common(**{field.name: data[field.name] for field in fields(Common)})

    parsed_profiles = [
        Profile(**{field.name: item[field.name] for field in fields(Profile)})
        for item in selected
    ]

    return common, parsed_profiles


def scrape_and_publish(settings: Common, profile: Profile) -> None:
    logger.success(f"Scraping data for profile: {profile.name}")

    c = SMSFreiburgClient(profile.user, profile.password)
    try:
        all_meals = c.get_data(settings.headless)
    except LoginError:
        sys.exit(1)

    result = {
        "updated": datetime.now().astimezone().isoformat(),
        "meals": [
            {
                "date": datetime.strptime(date, "%d.%m.%y").date().isoformat(),
                "ordered": quantity,
                "meal": meal.strip('"').strip(),
            }
            for date, (quantity, meal) in all_meals.items()
        ],
    }

    logger.success(f"Scraped result for profile {profile.name}:\n{pformat(result)}")

    logger.debug(f"Publishing result for profile {profile.name} to MQTT.")
    mqtt_client = mqtt.Client(mqtt.CallbackAPIVersion.VERSION2)
    mqtt_client.username_pw_set(settings.mqtt_user, settings.mqtt_password)
    mqtt_client.connect(settings.mqtt_ip, settings.mqtt_port, 60)

    info = mqtt_client.publish(
        profile.topic, json.dumps(result, ensure_ascii=False), retain=True, qos=0
    )
    logger.info(f"Published to MQTT using topic: {profile.topic}")

    if info.rc != mqtt.MQTT_ERR_SUCCESS:
        logger.error("Could not queue MQTT publish: {}", info.rc)
    else:
        try:
            info.wait_for_publish(timeout=15)
        except (ValueError, RuntimeError) as exc:
            logger.error("MQTT publish failed: {}", exc)
        else:
            if info.is_published():
                logger.success("MQTT message published (mid={})", info.mid)
            else:
                logger.warning("MQTT publish timed out (mid={})", info.mid)

    mqtt_client.disconnect()
