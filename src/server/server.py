# class ConnectionManager:
#     def __init__(self):
#         # Maps room_name -> set of active WebSocket connections on THIS server instance
#         self.active_connections: dict[str, set[]] = {}

#     async def connect(self, websocket, room_name: str):
#         await websocket.accept()
#         if room_name not in self.active_connections:
#             self.active_connections[room_name] = set()
#         self.active_connections[room_name].add(websocket)

#     def disconnect(self, websocket: WebSocket, room_name: str):
#         if room_name in self.active_connections:
#             self.active_connections[room_name].discard(websocket)
#             if not self.active_connections[room_name]:
#                 del self.active_connections[room_name]

#     async def broadcast_to_local_room(self, room_name: str, message: str):
#         """Sends the message to all clients connected to this specific server instance."""
#         if room_name in self.active_connections:
#             # Create a snapshot list to avoid runtime size change errors during iteration
#             for connection in list(self.active_connections[room_name]):
#                 try:
#                     await connection.send_text(message)
#                 except Exception:
#                     # Clear broken connections immediately
#                     self.disconnect(connection, room_name)

# manager = ConnectionManager()

import asyncio
import json
import logging
import websockets
from .rooms import *
from .user import *


# Configure minimal console feedback
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")


async def broadcast_to_room(rooms, room_name, payload_dict, exclude_socket=None):
    """Iterates over active room sockets to publish structured JSON payloads."""
    if room_name in rooms:
        message = json.dumps(payload_dict)
        # Snapshot list to avoid mutating the set while iterating over it
        for connection in list(rooms[room_name].active_connections):
            if connection != exclude_socket:
                try:
                    await connection.send(message)
                except websockets.exceptions.ConnectionClosed:
                    rooms[room_name].active_connections.discard(connection)

async def broadcast_to_user(websocket, msg, type, sender="system"):
        payload = {"type": type, "sender":sender, "text": msg}
        message = json.dumps(payload)
        try:
            await websocket.send(message)
        except websockets.exceptions.ConnectionClosed:
            pass

async def login(websocket,manager):
    true = 1
    loginMsg = "Enter Login Or Signup"
    NameMsg = "Enter Chosen Display Handle Name: "
    pwdMsg = "Enter your password: "
    while true:
        await broadcast_to_user(websocket,loginMsg,"sys")
        LoginOrSignup = await websocket.recv()
        if LoginOrSignup.upper() == "LOGIN":
            await broadcast_to_user(websocket,NameMsg,"sys")
            user_name = await websocket.recv()
            await broadcast_to_user(websocket,pwdMsg,"sys")
            password = await websocket.recv()
            true = 0
        elif LoginOrSignup.upper() == "SIGNUP":
            await broadcast_to_user(websocket,NameMsg,"sys")
            user_name = await websocket.recv()
            await broadcast_to_user(websocket,pwdMsg,"sys")
            password = await websocket.recv()
            await manager.create_user(user_name,password)
            true = 0
        elif LoginOrSignup.lower() == "!exit":
            os._exit(1)
        else:
            await broadcast_to_user(websocket,"Enter again correctly or type !exit to quit","sys")
    return  user_name.strip(),password.strip()

async def authenticate_client(websocket, User_Manager):
    """Reads the handshake packet, validates it, and returns the authenticated
    user_name on success or None on failure (closing/logging as appropriate).
    """
    try:
        user_name , password = await login(websocket,User_Manager)
    except Exception as e:
        logging.error(f"Invalid client handshake. Dropping connection. Due to {e}")
        return None

    # Reject unknown users rather than crashing on KeyError
    if user_name not in User_Manager.users:
        logging.error(f"User {user_name} does not exist. Dropping connection.")
        await websocket.close(code=4004, reason="User does not exist")
        return None

    # TODO: verify `password` against the stored credential on users[user_name]
    # once the User model (in user.py) exposes a way to check it, e.g.:
    if not User_Manager.users[user_name].check_password(password):
        logging.error(f"Invalid password for {user_name}. Dropping connection.")
        await websocket.close(code=4001, reason="Invalid credentials")
        return None

    return user_name

async def send_room_list(websocket,user_name,Room_Manager):
    joined , available = Room_Manager.list_rooms_for(user_name)
    await broadcast_to_user(websocket,"Joined","sys")
    i=0
    for rooms in joined:
        i+=1
        await broadcast_to_user(websocket,f"{i}. {rooms}","sys")
    i=0
    await broadcast_to_user(websocket,"Available","sys")
    for rooms in available:
        i+=1
        await broadcast_to_user(websocket,f"{i}. {rooms}","sys")

async def prompt_room_selection(websocket, user_name, Room_Manager):
    await broadcast_to_user(websocket,"Enter Room to join: ","sys")
    room_name = await websocket.recv()
    await broadcast_to_user(websocket,"Enter password: ","sys")
    password = await websocket.recv()
    await Room_Manager.join(room_name,user_name,websocket,password)
    return room_name

async def notify_join(rooms,room_name, user_name):
    # Broadcast arrival status frame
    logging.info(f"User {user_name} joined target room: {room_name}")
    await broadcast_to_room(rooms, room_name, {"type": "sys", "text": f"[SYSTEM] {user_name} joined the room."})

async def notify_leave(rooms,room_name, user_name):
    logging.info(f"User {user_name} disconnected from room: {room_name}")
    await broadcast_to_room(rooms, room_name, {"type": "sys", "text": f"[SYSTEM] {user_name} left the room."})

# async def EnterRoom(Room_manager,User_name):
async def join_room_flow(websocket, Room_Manager, user_name, room_name):
    Room_Manager.rooms[room_name].active_connections.add(websocket)
    await notify_join(Room_Manager.rooms,room_name, user_name)
    # await send_active_count(websocket, room_name)

    try:
        async for message in websocket:
            if message in ("!exit", "!quit"):
                break
            if room_name == "friends":
                # await broadcast_to_friends(user, message)
                pass
            else:
                payload = {"type": "msg", "sender": user_name, "text": message}
                await broadcast_to_room(Room_Manager.rooms,room_name, user_name, payload)
    except websockets.exceptions.ConnectionClosed:
        logging.info("Connection closed")
    finally:
        Room_Manager.rooms[room_name].active_connections.discard(websocket)
        await notify_leave(Room_Manager.rooms,room_name, user_name)

async def handle_client(websocket, Room_Manager, User_Manager):
    """Lifecycle handler executed concurrently for every incoming client."""
    rooms = Room_Manager.rooms
    users = User_Manager.users

    user_name = await authenticate_client(websocket, User_Manager)
    if user_name is None:
        return
    else:
        logging.info(f"User {user_name} authentication succesfull")
    
    await send_room_list(websocket, user_name, Room_Manager)
    room_name = await prompt_room_selection(websocket, user_name, Room_Manager)
    if room_name is None:
        return
    await join_room_flow(websocket, Room_Manager, user_name, room_name)

async def main():
    # Global tracking registry: room_name -> Room (built inside main, since
    # top-level `await` isn't valid outside an async function)
    room_manager = RoomManager()
    await room_manager.initialize()


    user_manager = UserManager()
    await user_manager.initialize()

    async def handler(websocket):
        await handle_client(websocket, room_manager,user_manager)

    # Bind server to localhost port 8765
    async with websockets.serve(handler, "127.0.0.1", 8765):
        logging.info("WebSocket infrastructure deployed on ws://127.0.0.1:8765")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server down.")