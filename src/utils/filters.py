#/src/utils/filters.py

import json
from markupsafe import Markup

def prettyjson(value):
    try:
        if isinstance(value, str):
            value = json.loads(value)
        return Markup(json.dumps(value, indent=2, ensure_ascii=False))
    except Exception:
        return value

def register_filters(app):
    app.jinja_env.filters['prettyjson'] = prettyjson