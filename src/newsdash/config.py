import os
import yaml
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

CONFIG_PATH = Path(__file__).parent.parent.parent / "config" / "sources.yaml"


def load_config() -> dict:
    """Load and return the full sources.yaml config."""
    with open(CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)


def get_enabled_feeds(config: dict) -> list[dict]:
    return [f for f in config.get("feeds", []) if f.get("enabled", True)]


def get_topics(config: dict) -> list[dict]:
    return config.get("topics", [])


def get_pipeline_config(config: dict) -> dict:
    return config.get("pipeline", {})


def get_github_config(config: dict) -> dict:
    return config.get("github", {})


def get_digest_config(config: dict) -> dict:
    return config.get("digest", {})
