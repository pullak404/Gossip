import json,os

def read_json(file_name):
    try:
        with open(file_name, "r") as file: # retrives from file # file closes automatically on block exit
            data = file.read()
    except FileNotFoundError as e:
        print("Error:", e)
        return None
    return data

def write_jsonl(file_name,data):
    try:
        with open(file_name, "a") as file: # retrives from file
            file.write(json.dumps(data) + "\n")
    except FileNotFoundError as e:
        print("Error:", e)

def add_jsonl(file_name, room_name,key, value):
    rooms = []
    found = False
    with open(file_name, "r") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            room = json.loads(line)
            if room["name"] == room_name:
                room[key].append(value)
                found = True
            rooms.append(room)

    if not found:
        raise ValueError(f"Room '{room_name}' not found")

    tmp_path = file_name + ".tmp"
    with open(tmp_path, "w") as f:
        for room in rooms:
            f.write(json.dumps(room) + "\n")
    os.replace(tmp_path, file_name)  # atomic on POSIX

def find_data_line(file,room_name):
    data = read_json(file)
    if data is None:
        return None
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        room_data = json.loads(line)
        if room_data["name"] == room_name:
            return room_data
    return None

# we can replace everywhere to find_data_line_id(find_room(room_name)) no need os find_data_line

def find_data_line_id(file,id):
    data = read_json(file)
    if data is None:
        return None
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        room_data = json.loads(line)
        if room_data["id"] == id:
            return room_data
    return None


def no_of_lines(file)-> int:
    data = read_json(file)
    if data is None:
        return 0
    ans = 0
    for line in data.splitlines():
        line = line.strip()
        if not line:
            continue
        ans+=1
    return ans