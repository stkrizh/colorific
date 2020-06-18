from aiohttp.web import View, json_response


class IndexView(View):
    async def get(self):
        return json_response({"status": "OK"})
