"""Reusable API pagination contracts."""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from pydantic import BaseModel, Field


class PaginationParams(BaseModel):
    """Validated offset pagination parameters."""

    limit: int = Field(default=50, ge=1, le=1000)
    offset: int = Field(default=0, ge=0)


Pagination = Annotated[PaginationParams, Depends()]
