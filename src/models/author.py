from typing import Literal

from pydantic import BaseModel


class Author(BaseModel):
    author_id: str
    author_name: str
    platform: Literal["bilibili", "x"]
