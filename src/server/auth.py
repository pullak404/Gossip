def verify_hash(password, password_hash) ->bool:
    if password == password_hash:
        return True
    return False

    