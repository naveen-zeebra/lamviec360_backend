import math
from typing import Any, List, Optional, Dict

def success_response(data: Any = None, message: str = "Operation completed successfully") -> Dict[str, Any]:
    return {
        "success": True,
        "message": message,
        "data": data,
    }

def paginated_response(
    items: List[Any],
    total_items: int,
    page: int = 1,
    page_size: int = 10,
    message: str = "Data retrieved successfully",
) -> Dict[str, Any]:
    total_pages = math.ceil(total_items / page_size) if page_size > 0 else 0
    return {
        "success": True,
        "message": message,
        "data": items,
        "pagination": {
            "page": page,
            "page_size": page_size,
            "total_items": total_items,
            "total_pages": total_pages,
            "has_next": page < total_pages,
            "has_prev": page > 1,
        },
    }
