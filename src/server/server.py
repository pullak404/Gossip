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
from rooms import *
from user import *


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

async def broadcast_to_user(payload_dict, websocket):
        message = json.dumps(payload_dict)
        try:
            await websocket.send(message)
        except websockets.exceptions.ConnectionClosed:
            pass
async def create_room(user_name,RoomManager,websocket):
    pass
async def join_room(user_name,RoomManager,websocket):
    pass
async def authenticate_client(websocket, users):
    """Reads the handshake packet, validates it, and returns the authenticated
    user_name on success or None on failure (closing/logging as appropriate).
    """
    try:
        init_message = await websocket.recv()
        handshake = json.loads(init_message)
        user_name = handshake["user_name"]
        password = handshake["password"]
    except Exception as e:
        logging.error(f"Invalid client handshake. Dropping connection. Due to {e}")
        return None

    # Reject unknown users rather than crashing on KeyError
    if user_name not in users:
        logging.error(f"User {user_name} does not exist. Dropping connection.")
        await websocket.close(code=4004, reason="User does not exist")
        return None

    # TODO: verify `password` against the stored credential on users[user_name]
    # once the User model (in user.py) exposes a way to check it, e.g.:
    if not users[user_name].check_password(password):
        logging.error(f"Invalid password for {user_name}. Dropping connection.")
        await websocket.close(code=4001, reason="Invalid credentials")
        return None

    return user_name


async def handle_client(websocket, RoomManager, UserManager):
    """Lifecycle handler executed concurrently for every incoming client."""
    rooms = RoomManager.rooms
    users = UserManager.users

    user_name = await authenticate_client(websocket, users)
    if user_name is None:
        return

    try:
        async for raw_message in websocket:
            if raw_message == "!create room":
                await create_room(user_name,RoomManager,websocket)
            else:
                if raw_message == "!join room":
                    room_name = await join_room(user_name,RoomManager,UserManager)
                 # Add client socket to room roster
                rooms[room_name].active_connections.add(websocket)
                logging.info(f"User {user_name} joined target room: {room_name}")

                # Broadcast arrival status frame
                await broadcast_to_room(rooms, room_name, {"type": "sys", "text": f"📢 System: {user_name} joined the room."})
                # Relay standard message payload out to all other clients in the same room
                await broadcast_to_room(rooms,room_name,{"type": "msg", "sender": user_name, "text": raw_message},exclude_socket=websocket)
    except websockets.exceptions.ConnectionClosed:
        logging.info("Connection closed")
    finally:
        # Graceful connection breakdown
        if room_name in rooms:
            rooms[room_name].active_connections.discard(websocket)
        logging.info(f"User {user_name} disconnected from room: {room_name}")
        await broadcast_to_room(rooms, room_name, {"type": "sys", "text": f"🛑 System: {user_name} left the room."})


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