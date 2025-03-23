import re

def username(username):
    pattern = r'^[a-zA-Z0-9-_]{3,20}$'
    return re.match(pattern, username)

def password(password):
    pattern = r'^(?=.*[A-Z])(?=.*[a-z])(?=.*\d)(?=.*[\W_]).{8,20}$'
    return re.match(pattern, password)