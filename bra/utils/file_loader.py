import json

def load_input():
    with open("input.json") as f:
        return json.load(f)

def load_schema():
    with open("response_schema.txt") as f:
        return f.read().strip()