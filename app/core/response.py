from enum import Enum
from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Result(BaseModel, Generic[T]):
    code: int = Field(description="状态码，1=成功，-1=失败")
    message: str = Field(description="提示信息，成功时为 'success'，失败时为错误描述")
    data: T | None = Field(None, description="响应数据，成功时返回业务数据，失败时为 null")

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
    field: str = Field(..., min_length=1, description="排序字段名")
    direction: SortDirection = Field(SortDirection.ASC, description="排序方向，asc=升序，desc=降序")


class PageDTO(BaseModel):
    page_num: int = Field(1, ge=1, description="页码，从 1 开始")
    page_size: int = Field(10, ge=1, le=100, description="每页条数，范围 1~100")
    sort_fields: list[SortField] | None = Field(None, description="排序规则列表，可选")
    query: dict | None = Field(None, description="查询过滤条件，键值对形式，可选")

    @property
    def offset(self) -> int:
        return (self.page_num - 1) * self.page_size


class PageVO(BaseModel, Generic[T]):
    total: int = Field(description="总记录数")
    rows: list[T] = Field(description="当前页数据列表")
