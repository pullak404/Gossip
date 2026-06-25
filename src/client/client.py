
import asyncio
import websockets

async def listen_and_talk():
    uri = "ws://localhost:8765"
    
    # Establish connection using the 'ws://' protocol
    async with websockets.connect(uri) as websocket:
        print("Connected to the server!")
        
        # Send a message to the server
        await websocket.send("Hello Server!")
        
        # Wait and listen for any incoming broadcast messages
        async for message in websocket:
            print(f"Broadcast from server: {message}")

if __name__ == "__main__":
    asyncio.run(listen_and_talk())
