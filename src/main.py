import json
from collections import defaultdict
from loguru import logger
import typing as t
from pathlib import Path
from fastapi.staticfiles import StaticFiles
from fastapi import FastAPI, WebSocket, Request, BackgroundTasks
from fastapi.templating import Jinja2Templates
from starlette.websockets import WebSocketDisconnect
from starlette.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

BASE_DIR = Path(__file__).resolve().parent
logger.info(f"BASE_DIR: {BASE_DIR}")

app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))


def https_url_for(request: Request, name: str, **path_params: t.Any) -> str:
    http_url = request.url_for(name, **path_params)
    return http_url.replace("http", "https", 1)


templates.env.globals["https_url_for"] = https_url_for


class Notifier:
    """
        Manages chat room sessions and members along with message routing
    """

    def __init__(self):
        self.connections: dict = defaultdict(dict)
        self.generator = self.get_notification_generator()

    async def get_notification_generator(self):
        while True:
            message = yield
            msg = message["message"]
            room_name = message["room_name"]
            await self._notify(msg, room_name)

    def get_members(self, room_name):
        try:
            return self.connections[room_name]
        except Exception:
            return None

    async def push(self, msg: str, room_name: str = None):
        message_body = {"message": msg, "room_name": room_name}
        await self.generator.asend(message_body)

    async def connect(self, websocket: WebSocket, room_name: str):
        await websocket.accept()
        if self.connections[room_name] == {} or len(self.connections[room_name]) == 0:
            self.connections[room_name] = []
        self.connections[room_name].append(websocket)
        logger.info(f"CONNECTIONS : {self.connections[room_name]}")

    def remove(self, websocket: WebSocket, room_name: str):
        self.connections[room_name].remove(websocket)
        logger.info(
            f"CONNECTION REMOVED\nREMAINING CONNECTIONS : {self.connections[room_name]}"
        )

    async def _notify(self, message: str, room_name: str):
        living_connections = []
        while len(self.connections[room_name]) > 0:
            websocket = self.connections[room_name].pop()
            await websocket.send_text(message)
            living_connections.append(websocket)
        self.connections[room_name] = living_connections


notifier = Notifier()


@app.get("/")
async def hello_world(request: Request):
    return "Go to /{room}/{username}/ to join a chat room. Connect to WebSocket at /ws/{room}"


# controller routes
@app.get("/{room_name}/{user_name}")
async def get(request: Request, room_name, user_name):
    return templates.TemplateResponse(
        "chat_room.html",
        {"request": request, "room_name": room_name, "user_name": user_name},
    )


@app.websocket("/ws/{room_name}")
async def websocket_endpoint(
        websocket: WebSocket, room_name, background_tasks: BackgroundTasks
):
    await notifier.connect(websocket, room_name)
    try:
        while True:
            data = await websocket.receive_text()
            d = json.loads(data)
            d["room_name"] = room_name

            room_members = (
                notifier.get_members(room_name)
                if notifier.get_members(room_name) is not None
                else []
            )
            if websocket not in room_members:
                logger.warning("SENDER NOT IN ROOM MEMBERS: RECONNECTING")
                await notifier.connect(websocket, room_name)

            await notifier._notify(f"{data}", room_name)
    except WebSocketDisconnect:
        notifier.remove(websocket, room_name)
