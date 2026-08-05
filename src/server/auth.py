from .broadcast import *
import os

def verify_hash(password, password_hash) ->bool:
    if password == password_hash:
        return True
    return False


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