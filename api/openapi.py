import re
from typing import Dict, Iterable

from aiohttp import web
from aiohttp.abc import Request
from aiohttp.hdrs import METH_ANY, METH_ALL, METH_PATCH, METH_DELETE, METH_POST, METH_PUT, METH_GET
from apispec.ext.marshmallow import MarshmallowPlugin
from apispec import APISpec as APISpec
from apispec.yaml_utils import load_operations_from_docstring

from api import schemas as schemas_module
from api.utils import issubclass_py37


async def generate_openapi_spec(app: web.Application) -> None:
    accepted_methods = {METH_GET, METH_PUT, METH_POST, METH_DELETE, METH_PATCH}
    paths = {}
    schemas = []
    options = {
        "info": {
            "description": "[Cookie Authentication](https://swagger.io/docs/specification/authentication/cookie-authentication/) "
                           "[OAuth2 Implicit Grant and SPA](https://auth0.com/blog/oauth2-implicit-grant-and-spa/)"
        },
        "securitySchemes": {
            "cookieAuth": {
                 "type": "apiKey",
                "in": "cookie",
                "name": app["settings"]["session"]["cookie"]["cookie_name"]
            }
        }
    }

    spec = APISpec(
        title=app["settings"]["name"],
        version=app["settings"]["version"],
        openapi_version="3.0.2",
        plugins=[MarshmallowPlugin()],
        **options
    )

    routes = [route for route in app.router.routes() if route.name != app["settings"]["openapi"]["route"]["name"]]

    for route in routes:
        operations: Dict = {}

        if issubclass_py37(route.handler, web.View) and route.method == METH_ANY:
            for attr in dir(route.handler):
                attr_uc = attr.upper()

                if attr_uc in METH_ALL and attr_uc in accepted_methods:
                    docstring_source = getattr(route.handler, attr)
                    operations = load_operations_from_docstring(docstring_source.__doc__)
        else:
            docstring_source = route.handler
            operations = load_operations_from_docstring(docstring_source.__doc__)

        if operations:
            info = route.get_info()
            path = info.get('path') or info.get('formatter')

            for schema in lookup("schema", operations):
                if schema not in schemas:
                    schemas.append(schema)

            if path not in paths.keys():
                paths[path] = {}

            paths[path].update(operations)

    for schema in schemas:
        schema_class = getattr(schemas_module, schema)
        if callable(schema_class):
            schema_name = re.match(r"([^/]+?)(?:Schema)*$", schema).group(1)
            spec.components.schema(schema_name, schema=schema_class)

    for path, operations in paths.items():
        spec.path(path=path, operations=operations)

    app["openapi"] = spec


async def get_openapi_handler(request: Request) -> web.Response:
    return web.json_response(request.app["openapi"].to_dict())


def clean(text: str) -> str:
    return text.replace("#/components/schemas/", "")


def lookup(key: str, data: Dict) -> Iterable[str]:
    if isinstance(data, dict):
        for k, v in data.items():
            if k == key:
                if isinstance(v, str):
                    yield clean(v)
                elif isinstance(v, dict) and "items" in v:
                    yield clean(v["items"])
            if isinstance(v, (dict, list)):
                yield from lookup(key, v)
    elif isinstance(data, list):
        for e in data:
            yield from lookup(key, e)
