import aiohttp_jinja2
from aiohttp import web


@aiohttp_jinja2.template('swagger.html')
async def get_swagger_ui_handler(request: web.Request) -> web.Response:
    pass
