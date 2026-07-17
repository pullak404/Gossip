

# class ConnectionManager:
#     def __init__(self):
#         # Maps room_id -> set of active WebSocket connections on THIS server instance
#         self.active_connections: dict[str, set[]] = {}

#     async def connect(self, websocket, room_id: str):
#         await websocket.accept()
#         if room_id not in self.active_connections:
#             self.active_connections[room_id] = set()
#         self.active_connections[room_id].add(websocket)

#     def disconnect(self, websocket: WebSocket, room_id: str):
#         if room_id in self.active_connections:
#             self.active_connections[room_id].discard(websocket)
#             if not self.active_connections[room_id]:
#                 del self.active_connections[room_id]

#     async def broadcast_to_local_room(self, room_id: str, message: str):
#         """Sends the message to all clients connected to this specific server instance."""
#         if room_id in self.active_connections:
#             # Create a snapshot list to avoid runtime size change errors during iteration
#             for connection in list(self.active_connections[room_id]):
#                 try:
#                     await connection.send_text(message)
#                 except Exception:
#                     # Clear broken connections immediately
#                     self.disconnect(connection, room_id)

# manager = ConnectionManager()


import asyncio
import json
import logging

import websockets

# Configure minimal console feedback
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(message)s")

# Global tracking registry: room_id -> set(WebSocketServerProtocol)
ROOMS = {}


async def broadcast_to_room(room_id, payload_dict, exclude_socket=None):
    """Iterates over active room sockets to publish structured JSON payloads."""
    if room_id in ROOMS:
        message = json.dumps(payload_dict)
        # Snapshot list to avoid mutating the set while iterating over it
        for connection in list(ROOMS[room_id]):
            if connection != exclude_socket:
                try:
                    await connection.send(message)
                except websockets.exceptions.ConnectionClosed:
                    ROOMS[room_id].discard(connection)


async def handle_client(websocket):
    """Lifecycle handler executed concurrently for every incoming client."""
    # The client must send a connection handshake packet containing metadata
    try:
        init_message = await websocket.recv()
        handshake = json.loads(init_message)
        room_id = handshake["room_id"]
        user_name = handshake["user_name"]
    except Exception:
        logging.error("Invalid client handshake. Dropping connection.")
        return

    # Add client socket to room roster
    if room_id not in ROOMS:
        ROOMS[room_id] = set()
    ROOMS[room_id].add(websocket)
    logging.info(f"User {user_name} joined target room: {room_id}")

    # Broadcast arrival status frame
    await broadcast_to_room(room_id, {"type": "sys", "text": f"📢 System: {user_name} joined the room."})

    try:
        async for raw_message in websocket:
            # Relay standard message payload out to all other clients in the same room
            await broadcast_to_room(
                room_id,
                {"type": "msg", "sender": user_name, "text": raw_message},
                exclude_socket=websocket,
            )
    except websockets.exceptions.ConnectionClosed:
        print("connecntion closed")
    finally:
        # Graceful connection breakdown
        if room_id in ROOMS:
            ROOMS[room_id].discard(websocket)
            if not ROOMS[room_id]:
                del ROOMS[room_id]
        logging.info(f"User {user_name} disconnected from room: {room_id}")
        await broadcast_to_room(room_id, {"type": "sys", "text": f"🛑 System: {user_name} left the room."})


async def main():
    # Bind server to localhost port 8765
    async with websockets.serve(handle_client, "127.0.0.1", 8765):
        logging.info("WebSocket infrastructure deployed on ws://127.0.0.1:8765")
        await asyncio.Future()  # Run forever


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("Server down.")