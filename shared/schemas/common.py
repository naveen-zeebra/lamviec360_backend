from typing import Generic, TypeVar, Optional, List, Any
from pydantic import BaseModel, Field

DataT = TypeVar("DataT")

class BaseResponse(BaseModel):
    success: bool = True
    message: str = "Operation completed successfully"

class APIResponse(BaseResponse, Generic[DataT]):
    data: Optional[DataT] = None

class PaginationMeta(BaseModel):
    page: int = Field(default=1, ge=1)
    page_size: int = Field(default=10, ge=1, le=100)
    total_items: int = Field(default=0, ge=0)
    total_pages: int = Field(default=0, ge=0)
    has_next: bool = False
    has_prev: bool = False

class PaginatedResponse(BaseResponse, Generic[DataT]):
    data: List[DataT] = []
    pagination: PaginationMeta
