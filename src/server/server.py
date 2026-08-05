

# manager = ConnectionManager()

import asyncio
import json
import logging
import websockets
from .rooms import *
from .user import *

from .broadcast import *
from .auth import *

# Configure minimal console feedback
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")



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
                await broadcast_to_room(Room_Manager.rooms, room_name, payload, exclude_socket=websocket)
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