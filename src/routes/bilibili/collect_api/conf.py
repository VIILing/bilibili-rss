from typing import TypeVar, Generic
from pydantic import BaseModel, Field

UNIVERSAL_UA = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/131.0.0.0 Safari/537.36 Edg/131.0.0.0"
DM_APPEND = ''


T = TypeVar('T')


class FetchResult(Generic[T], BaseModel):
    ok: bool
    data: T | None = Field(None)
    msg: str = Field('')
