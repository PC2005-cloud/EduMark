from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    code: int
    message: str
    data: T | None = None

    @staticmethod
    def success(data: T | None = None) -> "Result[T]":
        return Result(code=1, message="success", data=data)

    @staticmethod
    def error(message: str) -> "Result[T]":
        return Result(code=-1, message=message, data=None)


class SortDirection(str, Enum):
    ASC = "asc"
    DESC = "desc"


class SortField(BaseModel):
    field: str = Field(..., min_length=1)
    direction: SortDirection = SortDirection.ASC


class PageDTO(BaseModel):
    page_num: int = Field(1, ge=1)
    page_size: int = Field(10, ge=1, le=100)
    sort_fields: list[SortField] | None = None
    query: dict | None = None

    @property
    def offset(self) -> int:
        return (self.page_num - 1) * self.page_size


class PageVO(BaseModel, Generic[T]):
    total: int
    rows: list[T]
