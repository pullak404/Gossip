from json_helper import *
from auth import *
from datetime import datetime, UTC
import asyncio

USER_FILE = "data/user.jsonl"

class User:
    def __init__(self,id, name, password_hash, time):
        self.id = id
        # self.username = username
        self.name = name
        self.password_hash = password_hash
        self.joined = time
        self.friends: set[str] = set()

    def check_password(self, password) -> bool:
        return verify_hash(password, self.password_hash)
    

class UserManager:
    # manager = RoomManager()
# await manager.initialize()
    def __init__(self):
        self.users: dict[str, User] = {} # in-memory # key:str is user_name and value:User is the class
                                                     # here use dict so to find a user we have O(1) lookup
                                                     # also to avoid duplicate user name
    async def initialize(self):
        await self.load_users()
    
    async def load_users(self):
        noof_rooms = no_of_lines(USER_FILE)
        for i in range(noof_rooms):
            user_data = find_data_line_id(USER_FILE,i+1)
            if user_data is None:
                return
            user = User(user_data["id"],user_data["name"],user_data["password_hash"],user_data["joined_at"])
            self.users[user_data["name"]] = user

    async def add_user(self):
       noof_users = no_of_lines(USER_FILE)     
       for i in range(noof_users):
           user = find_data_line_id(USER_FILE,i+1)
           if user is None:
               return
           if user["name"] not in self.users:
                new_user = User(user["id"],user["name"],user["password_hash"],user["joined_at"])
                self.users[user["name"]] = new_user  

    async def find_user(self,user_name):
        if user_name in self.users:
            return self.users[user_name].id
        return None
    
    async def insert_user(self,user_data): ## if have made this for json for now change it for db
        new_id = len(self.users) + 1
        new_user_data = {"id":new_id}
        new_user_data.update(user_data)
        write_jsonl(USER_FILE,new_user_data)
        await self.add_user()


    # keep this in a try-except block
    async def create_user(self, user_name, password): #when use db add "db" in parameters
        try:
            existing = await self.find_user(user_name)
            if existing:
                raise ValueError("User already exists")
            await self.insert_user({
                "name": user_name,
                "password_hash": password,  #hash_password(password), # use this after making the hash func
                "joined_at": datetime.now(UTC).isoformat()
                })
        except ValueError as e:
            print("Error: ",e)
    
    async def authenticate(self, username, password):
        user = self.users[username]
        if user and verify_hash(password, user.password_hash):
            return user
        return None
    

# async def main():
#     manager = UserManager()
#     await manager.initialize()
#     await manager.create_user("pullak","abcd")
#     # joined,available = manager.list_rooms_for("pullak")
#     # print(joined,available)
#     await manager.create_user("srinaya","abcd")
#     await manager.create_user("priansu","abcd")
#     # for i in manager.users:
#         # print(i)
#     # joined1,available1 = manager.list_rooms_for("srinaya")
#     # print(joined1,available1)
#     # await manager.create_user("tejash","abcd")
#     for i in manager.users:
#         print(i)
#     # joined2,available2 = manager.list_rooms_for("tejash")
#     # print(joined2,available2)

# if  __name__ == "__main__":
#     asyncio.run(main())