# class broadcast:
#     def __init__(self,websocket) -> None:
#         pass
#     async def broadcast_to_user(websocket, msg, type, sender="system"):
#         payload = {"type": type, "sender":sender, "text": msg}
#         message = json.dumps(payload)
#         try:
#             await websocket.send(message)
#         except websockets.exceptions.ConnectionClosed:
#             pass
import json
import websockets

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

