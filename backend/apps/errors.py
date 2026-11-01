from rest_framework.views import exception_handler


def _message(value):
    if isinstance(value, list):
        return str(value[0]) if value else "Request could not be processed."
    if isinstance(value, dict):
        return "Request could not be processed."
    return str(value)


def api_exception_handler(exc, context):
    """Consistent error body: detail, code, and field errors when present."""
    response = exception_handler(exc, context)
    if response is None:
        return None
    data = response.data
    code = getattr(exc, "default_code", "error")
    errors = None
    if isinstance(data, dict) and set(data.keys()) == {"detail"}:
        detail = _message(data["detail"])
        item_code = getattr(exc, "get_codes", None)
        if item_code:
            raw = exc.get_codes()
            if isinstance(raw, str):
                code = raw
    elif isinstance(data, dict):
        detail = "Request could not be processed."
        errors = data
        code = "invalid"
    else:
        detail = _message(data)
    if isinstance(code, (dict, list)):
        code = "invalid"
    response.data = {"detail": detail, "code": str(code), "errors": errors}
    return response
