# import socket
# import threading
import asyncio
import sys
import json
import websockets
import os

from src.server.user import UserManager


# ANSI Escape color codes for visual tracking inside terminal windows
COLOR_SYS = "\033[93m"  # Yellow system notifications
COLOR_MSG = "\033[94m"  # Blue remote messages
COLOR_ERR = "\033[91m"  # Red connection errors
COLOR_RST = "\033[0m"   # Reset code to default terminal state

USER = "YOU"

async def receive_loop(websocket):
    """Inbound stream execution layer routing updates to display instantly."""
    async for raw_payload in websocket:
        payload = json.loads(raw_payload)
        
        # Clear current input line placeholder, print message, restore user prompt character
        print("\r\033[K", end="") 
        msg_type = payload.get("type")
        if msg_type == "sys":
            print(f"{COLOR_SYS}{payload.get('text', '')}{COLOR_RST}")
        elif msg_type == "msg":
            print(f"{COLOR_MSG}[{payload.get('sender', '?')}]{COLOR_RST}: {payload.get('text', '')}")
        else:
            print(f"{COLOR_ERR}⚠ Received unrecognized payload from server: {payload}{COLOR_RST}")

        print(f"[{COLOR_MSG}{USER}{COLOR_RST}] ", end="", flush=True)

async def send_loop(websocket):
    """Intercepts local standard keyboard streams without blocking the thread pool."""
    loop = asyncio.get_running_loop()
    while True:
        # Execute sys.stdin block off the main asynchronous thread loop
        user_input = await loop.run_in_executor(None, sys.stdin.readline)
        sanitized = user_input.strip()
        
        if sanitized.lower() == "!exit":
            print("\nExiting interface application stack.")
            # Hard exit the program when user manually requests escape.
            # os._exit is used (not sys.exit) because this runs inside one of
            # several concurrent asyncio tasks under asyncio.gather — sys.exit
            # would only raise SystemExit in this task, which can get delayed
            # or swallowed instead of actually terminating the process.
            os._exit(0)
            
        if sanitized:
            await websocket.send(sanitized)
        print(f"[{COLOR_MSG}{USER}{COLOR_RST}] ", end="", flush=True)

async def manage_connection():
    """Supervisor loop that connects, executes chat tasks, and retries on failure."""
    server_uri = "ws://127.0.0.1:8765"
    
    # Backoff configurations
    base_delay = 1.0      # Start with a 1-second delay
    max_delay = 32.0      # Cap the max wait ceiling at 32 seconds
    factor = 2.0          # Exponential backoff factor (double the time each failure)
    current_delay = base_delay

    while True:
        try:
            print(f"\r\033[KConnecting to backend gateway {server_uri}...", flush=True)
            
            async with websockets.connect(server_uri) as websocket:
                # Reset exponential backoff penalty tracker on a successful handshake connection
                current_delay = base_delay
                
                # Deliver Initial Configuration Handshake Frame instantly upon connection
                
                # handshake_payload = {"user_name": user_name,"password": password}
                # await websocket.send(json.dumps(handshake_payload))
                ##Rather than this send device ipv4 address and location

                
                print(f"Connected! Type messages below. Type 'exit' to escape.\n> ", end="", flush=True)
                
                # Run parallel tasks together concurrently until connection breaks
                # loop.create_task or asyncio.gather allows exceptions to bubble up here
                await asyncio.gather(
                    receive_loop(websocket),
                    send_loop(websocket)
                )

        except websockets.exceptions.ConnectionClosed as e:
            # Codes the server sends when it deliberately rejects the handshake
            # (bad user, bad credentials, etc). Retrying won't help here, so stop.
            NON_RECOVERABLE_CODES = {4004, 4001}

            if e.code in NON_RECOVERABLE_CODES:
                print(f"\r\033[K{COLOR_ERR}Connection rejected by server ({e.code}: {e.reason}).{COLOR_RST}")
                print(f"{COLOR_ERR}Not retrying — check your username/password and restart the client.{COLOR_RST}")
                os._exit(1)

            print(f"\r\033[K{COLOR_ERR}❌ Network error / Connection lost ({type(e).__name__}).{COLOR_RST}")
            print(f"{COLOR_SYS}🔄 Retrying in {current_delay} seconds... (Type 'exit' to abort){COLOR_RST}\n> ", end="", flush=True)

            # Non-blocking pause for the duration of current backoff penalty
            await asyncio.sleep(current_delay)

            # Progress backoff scaling calculation (e.g., 1s -> 2s -> 4s -> 8s -> 16s -> 32s)
            current_delay = min(current_delay * factor, max_delay)

        except (OSError, ConnectionRefusedError) as e:
            print(f"\r\033[K{COLOR_ERR}❌ Network error / Connection lost ({type(e).__name__}).{COLOR_RST}")
            print(f"{COLOR_SYS}🔄 Retrying in {current_delay} seconds... (Type 'exit' to abort){COLOR_RST}\n> ", end="", flush=True)

            # Non-blocking pause for the duration of current backoff penalty
            await asyncio.sleep(current_delay)

            # Progress backoff scaling calculation (e.g., 1s -> 2s -> 4s -> 8s -> 16s -> 32s)
            current_delay = min(current_delay * factor, max_delay)
            
        except Exception as dynamic_error:
            # Handle unexpected edge case loops explicitly to protect app workflow execution stability
            print(f"\nCritical Unhandled Pipeline Error: {dynamic_error}")
            break

async def start_client():

    await manage_connection()

if __name__ == "__main__":
    help_msg = """
            Welcome\n
            this is a chat app\n
            If already a member enter login or if a new member enter signup\n
            then enter a room to start gossiping!!!\n
            Type !help for help and !exit to quit the application\n\n"""
    print(help_msg)
    try:
        asyncio.run(start_client())
    except KeyboardInterrupt:
        print("\nExiting interface application stack.")