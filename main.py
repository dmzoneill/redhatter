from fastapi import FastAPI
import subprocess

app = FastAPI()

@app.get("/")
def top_level():
    return "Nothing to see here"

@app.get("/get_creds")
def get_creds():
    with open('key','r') as f:
        with open('username', 'r') as u:
            key = f.read()
            token = subprocess.run(['./getpw'], stdout=subprocess.PIPE)
            token = token.stdout.decode("utf-8")
            return u.read().strip() + "," + key.strip() + token.strip()