class ConnectionManager:
    def __init__(self):
        # Maps room_name -> set of active WebSocket connections on THIS server instance
        self.active_connections: dict[str, set[]] = {}

    async def connect(self, websocket, room_name: str):
        await websocket.accept()
        if room_name not in self.active_connections:
            self.active_connections[room_name] = set()
        self.active_connections[room_name].add(websocket)

    def disconnect(self, websocket, room_name: str):
        if room_name in self.active_connections:
            self.active_connections[room_name].discard(websocket)
            if not self.active_connections[room_name]:
                del self.active_connections[room_name]

    async def broadcast_to_local_room(self, room_name: str, message: str):
        """Sends the message to all clients connected to this specific server instance."""
        if room_name in self.active_connections:
            # Create a snapshot list to avoid runtime size change errors during iteration
            for connection in list(self.active_connections[room_name]):
                try:
                    await connection.send_text(message)
                except Exception:
                    # Clear broken connections immediately
                    self.disconnect(connection, room_name)

