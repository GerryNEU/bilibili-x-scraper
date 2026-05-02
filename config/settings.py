from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    BILIBILI_SESSDATA: str
    BILIBILI_BUVID3: str
    X_USERNAME: str
    X_PASSWORD: str
    DB_PATH: str
    BILIBILI_UIDS: list[str]
    X_USERNAMES: list[str]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            BILIBILI_SESSDATA=_required_env("BILIBILI_SESSDATA"),
            BILIBILI_BUVID3=_required_env("BILIBILI_BUVID3"),
            X_USERNAME=_required_env("X_USERNAME"),
            X_PASSWORD=_required_env("X_PASSWORD"),
            DB_PATH=os.getenv("DB_PATH", "data/posts.db"),
            BILIBILI_UIDS=_parse_csv(_required_env("BILIBILI_UIDS")),
            X_USERNAMES=_parse_usernames(_required_env("X_USERNAMES")),
        )


def _required_env(name: str) -> str:
    value = os.getenv(name)
    if value is None or value.strip() == "":
        raise ValueError(f"Missing required environment variable: {name}")
    return value


def _parse_csv(value: str) -> list[str]:
    return [item.strip() for item in value.split(",") if item.strip()]


def _parse_usernames(value: str) -> list[str]:
    return [username for username in (item.lstrip("@") for item in _parse_csv(value)) if username]


settings = Settings.from_env()
