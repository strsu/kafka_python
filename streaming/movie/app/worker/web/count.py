from faust.web import Request, Response, View
from app.worker import get_faust_app

faust_app = get_faust_app()


@faust_app.page("/count/")
class counter(View):
    count: int = 0

    async def get(self, request: Request) -> Response:
        return self.json({"count": self.count})

    async def post(self, request: Request) -> Response:
        n: int = request.query["n"]
        self.count += 1
        return self.json({"count": self.count})

    async def delete(self, request: Request) -> Response:
        self.count = 0
