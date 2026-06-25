import asyncio

# Keep track of all connected client writers
connected_clients = set()

async def handle_client(reader, writer):
    """Handles an individual user connection."""
    connected_clients.add(writer)
    addr = writer.get_extra_info('peername')
    print(f"New connection from {addr}")

    try:
        while True:
            # Wait efficiently for this specific client to send text
            data = await reader.readline()
            if not data:
                break # Client disconnected
            
            message = f"{addr}: {data.decode()}"
            
            # Broadcast the message to all other connected users concurrently
            # if a client has a slow connection, it won't block the loop
            for client in connected_clients:
                if client != writer:
                    client.write(message.encode())
                    await client.drain() # Yield control while sending data

    except asyncio.CancelledError:
        pass
    finally:
        # Clean up on disconnect
        connected_clients.remove(writer)
        writer.close()
        await writer.wait_closed()

async def main():
    # Start a TCP socket server listening on port 8888
    server = await asyncio.start_server(handle_client, '127.0.0.1', 8888)
    print("Chat server running on port 8888...")
    async with server:
        await server.serve_forever()

# Run the event loop
asyncio.run(main())

import asyncio
import websockets

# Keep track of all actively connected WebSocket clients
connected_clients = set()

async def chat_handler(websocket):
    """Handles the lifecycle of a single WebSocket connection."""
    # Register the new client
    connected_clients.add(websocket)
    print(f"Client connected. Total clients: {len(connected_clients)}")
    
    try:
        # Loop stays alive as long as the client remains connected
        async for message in websocket:
            print(f"Received: {message}")
            
            # Broadcast the incoming message to every OTHER connected client
            if connected_clients:
                # Create a list of send tasks to run them concurrently
                broadcast_tasks = [
                    client.send(f"Anonymous: {message}") 
                    for client in connected_clients 
                    if client != websocket
                ]
                if broadcast_tasks:
                    await asyncio.gather(*broadcast_tasks)
                    
    except websockets.exceptions.ConnectionClosedOK:
        print("Client disconnected cleanly.")
    except websockets.exceptions.ConnectionClosedError:
        print("Client disconnected unexpectedly.")
    finally:
        # Always clean up the set when a user leaves
        connected_clients.remove(websocket)
        print(f"Client removed. Total clients: {len(connected_clients)}")

async def main():
    # Start the WebSocket server on localhost port 8765
    async with websockets.serve(chat_handler, "localhost", 8765):
        print("WebSocket server running on ws://localhost:8765")
        await asyncio.Future()  # Keeps the server running forever

if __name__ == "__main__":
    asyncio.run(main())
