DEFAULT_PAGE_SIZE = 10

EMPTY_PAGINATED_RESPONSE = {
    "count": 0,
    "next": None,
    "previous": None,
    "results": [],
}

EMPTY_CURSOR_RESPONSE = {
    "next": None,
    "previous": None,
    "results": [],
}


def paginate(items: list, page: int = 1, per_page: int = DEFAULT_PAGE_SIZE) -> dict:
    total = len(items)
    start = (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]
    return {
        "count": total,
        "next": page + 1 if end < total else None,
        "previous": page - 1 if page > 1 else None,
        "results": page_items,
    }
