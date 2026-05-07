def normalize_sort_order(order, default="desc"):
    """
    Return a safe SQL sort order.
    """
    if order == "asc":
        return "asc"

    if order == "desc":
        return "desc"

    return default


def apply_sort(query, sort, order, allowed_sorts, default_sort, default_order="desc", tie_breaker=None):
    """
    Apply whitelist-based sorting to a Peewee query.

    allowed_sorts must be a dict:
        {
            "id": Model.id,
            "name": Model.name,
        }

    This prevents passing raw user input into order_by().
    """
    sort_key = sort if sort in allowed_sorts else default_sort
    direction = normalize_sort_order(order, default_order)
    expression = allowed_sorts[sort_key]

    ordered_expression = expression.asc() if direction == "asc" else expression.desc()

    if tie_breaker is not None and sort_key != "id":
        return query.order_by(ordered_expression, tie_breaker.desc())

    return query.order_by(ordered_expression)
