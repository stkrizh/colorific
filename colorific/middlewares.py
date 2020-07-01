from aiohttp import web

from .settings import config


@web.middleware
async def cors_middleware(request, handler):
    cors_headers = {
        "Access-Control-Allow-Origin": config.colorific.cors_allow_origin,
        "Access-Control-Allow-Methods": "PUT, OPTIONS",
        "Access-Control-Allow-Headers": "*",
        "Access-Control-Max-Age": "86400",
    }
    try:
        response = await handler(request)
        response.headers.update(cors_headers)
        return response
    except web.HTTPException as ex:
        ex.headers.update(cors_headers)
        raise
