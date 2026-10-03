from __future__ import annotations

import math
from typing import Annotated

from fastapi import Query
from pydantic import BaseModel

DEFAULT_PAGE_SIZE = 4

class PageParams:
    def __init__(self, page: int, page_size: int) -> None:
        self.page = page
        self.page_size = page_size

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


def page_params(
    page: Annotated[int, Query(ge=1)] = 1,
    page_size: Annotated[int, Query(ge=1, le=100)] = DEFAULT_PAGE_SIZE,
) -> PageParams:
    return PageParams(page=page, page_size=page_size)


class Page[ItemT](BaseModel):
    items: list[ItemT]
    page: int
    page_size: int
    total: int
    total_pages: int

    @classmethod
    def create(
        cls,
        items: list[ItemT],
        params: PageParams,
        total: int,
    ) -> Page[ItemT]:
        return cls(
            items=items,
            page=params.page,
            page_size=params.page_size,
            total=total,
            total_pages=math.ceil(total / params.page_size) if total else 0,
        )