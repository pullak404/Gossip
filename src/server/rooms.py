from auth import verify_hash
from json_helper import *
from datetime import datetime, UTC
import asyncio

ROOM_FILE = "data/rooms.jsonl"

class Room:
    def __init__(self,id, name, owner, password_hash, time):
        self.id = id
        self.name = name
        self.password_hash = password_hash
        self.owner = owner
        self.created_at = time
        self.members: set[str] = {owner}
        self.active_connections: set = set() # keep in memory


    def check_password(self, password) -> bool:
        return verify_hash(password, self.password_hash)
    
class RoomManager:
    # manager = RoomManager()
# await manager.initialize()
    def __init__(self):
        self.rooms: dict[str, Room] = {} # in-memory # key:str is room_name and value:Room is the class
                                                     # here use dict so to find a room we have O(1) lookup
                                                     # also to avoid duplicate room name
    async def initialize(self):
        await self.load_rooms()
    
    async def load_rooms(self):
        noof_rooms = no_of_lines(ROOM_FILE)
        for i in range(noof_rooms):
            room_data = find_data_line_id(ROOM_FILE,i+1)
            if room_data is None:
                return
            room = Room(room_data["id"],room_data["name"],room_data["owner"],room_data["password_hash"],room_data["created_at"])
            for name in room_data["members"]:
                    room.members.add(name)
            self.rooms[room_data["name"]] = room

    async def add_rooms(self):
        noof_rooms = no_of_lines(ROOM_FILE)
        for i in range(noof_rooms):
            room = find_data_line_id(ROOM_FILE,i+1)
            if room is None:
                return
            if room["name"] not in self.rooms:
                new_room = Room(room["id"],room["name"],room["owner"],room["password_hash"],room["created_at"])
                self.rooms[room["name"]] = new_room
  

    async def find_room(self,room_name):
        if room_name in self.rooms:
            return self.rooms[room_name].id
        return None
    
    async def insert_room(self,room_data): ## if have made this for json for now change it for db
        new_id = len(self.rooms) + 1
        new_room_data = {"id":new_id}
        new_room_data.update(room_data)
        write_jsonl(ROOM_FILE,new_room_data)
        await self.add_rooms()


    # keep this in a try-except block
    async def create_room(self, room_name, password, owner): #when use db add "db" in parameters
        try:
            if room_name in ("friends",):          # reserved names guard
                raise ValueError("Room name is reserved")
            # existing = await db.rooms.find_one({"_id": room_name}) ## make this for database
            existing = await self.find_room(room_name)
            if existing:
                raise ValueError("Room already exists")
            await self.insert_room({
                "name": room_name,
                "password_hash": password,  #hash_password(password), # use this after making the hash func
                "owner": owner,  # when make a owner class or person class use owner.username
                "members": [owner],  # here also
                "created_at": datetime.now(UTC).isoformat()
                })
        except ValueError as e:
            print("Error: ",e)
            

    #returns rooms in which user has joined and the rooms available to join
    # so in total it will give all the rooms , after user as a class use user.username
    def list_rooms_for(self, username: str) -> tuple[list[str], list[str]]: 
        joined = [i for i in self.rooms if username in self.rooms[i].members]
        available = [i for i in self.rooms if i not in joined]
        return joined, available

    async def join(self, room_name, username: str, websocket, password=None):
        if room_name not in self.rooms:
            raise KeyError(f"Room '{room_name}' not found")
        room = self.rooms[room_name]
        room_data = find_data_line(ROOM_FILE,room_name)
        if room_data is None:
            return
        if username not in room_data["members"]:#room.members:
            if not room.check_password(password):
                raise PermissionError("Invalid room password")
            room.members.add(username)
            add_jsonl(ROOM_FILE,room_name,"members",username)
            # print("done") # write a pretty statement like joined this chatroom or something [NEW MEMBER] username joined CHATROOM_NAME
        # room.active_connections.add(websocket)
        return len(room.active_connections)



# async def main():
#     manager = RoomManager()
#     await manager.initialize()
#     await manager.create_room("eee","abcd","pullak")
#     await manager.create_room("vssut", "abcd", "pullak")
#     joined,available = manager.list_rooms_for("pullak")
#     print(joined,available)
#     await manager.join("eee","srinaya",None,"abcd")
#     await manager.join("vssut","srinaya",None,"abcd")
#     for i in manager.rooms:
#         print(manager.rooms[i].members)
#     joined1,available1 = manager.list_rooms_for("srinaya")
#     print(joined1,available1)
#     await manager.join("eee","tejash",None,"abcd")
#     for i in manager.rooms:
#         print(manager.rooms[i].members)
#     joined2,available2 = manager.list_rooms_for("tejash")
#     print(joined2,available2)

# if  __name__ == "__main__":
#     asyncio.run(main())