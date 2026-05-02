from dataclasses import dataclass
import os

from dotenv import load_dotenv


load_dotenv()


@dataclass(frozen=True)
class Settings:
    BILIBILI_SESSDATA: str
    BILIBILI_BUVID3: str
    BILIBILI_BUVID4: str
    BILIBILI_BILI_JCT: str
    BILIBILI_DEDE_USER_ID: str
    BILIBILI_DEDE_USER_ID_CKMD5: str
    X_COOKIE_STRING: str
    DB_PATH: str
    BILIBILI_UIDS: list[str]
    X_USERNAMES: list[str]

    @classmethod
    def from_env(cls) -> "Settings":
        return cls(
            BILIBILI_SESSDATA=_required_env("BILIBILI_SESSDATA"),
            BILIBILI_BUVID3=_required_env("BILIBILI_BUVID3"),
            BILIBILI_BUVID4=_required_env("BILIBILI_BUVID4"),
            BILIBILI_BILI_JCT=_required_env("BILIBILI_BILI_JCT"),
            BILIBILI_DEDE_USER_ID=_required_env("BILIBILI_DEDE_USER_ID"),
            BILIBILI_DEDE_USER_ID_CKMD5=_required_env("BILIBILI_DEDE_USER_ID_CKMD5"),
            X_COOKIE_STRING=_required_env("X_COOKIE_STRING"),
            DB_PATH=os.getenv("DB_PATH", "data/posts.db"),
            BILIBILI_UIDS=_parse_csv(os.getenv("BILIBILI_UIDS", "")),
            X_USERNAMES=_parse_usernames(os.getenv("X_USERNAMES", "")),
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
