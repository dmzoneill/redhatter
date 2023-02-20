from fastapi import FastAPI
from pprint import pprint
import subprocess
import json
import base64
from subprocess import Popen, PIPE

app = FastAPI()


def pexec(cmd):
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = proc.communicate()
    exitcode = proc.returncode

    if exitcode != 0:
        pprint(err)

    return out

def ephemeral_login(username):
    namespace = get_namespace(username)
    password = get_namespace_password(namespace)
    return password

def get_namespace_password(namespace):
    secret = pexec("kubectl get secret \"env-" + namespace + "-keycloak\" -o json").decode("UTF-8").strip()
    password = json.loads(secret)
    password = password['data']['defaultPassword']
    password = base64.b64decode(password).decode("utf-8")
    return password
        
def get_namespace(username):
    subprocess.call("/usr/bin/rhtoken e", shell=True)
    namespace = pexec("bonfire namespace list | grep " + username + " | awk '{print $1}'").decode("UTF-8").strip()
    return namespace

@app.get("/")
def top_level():
    return "Nothing to see here"

@app.get("/get_creds")
def get_creds(context: str = "associate"):
    with open('key','r') as kfile:
        with open('username', 'r') as ufile:
            key = kfile.read()
            if context == "associate":
                token = subprocess.run(['./getpw'], stdout=subprocess.PIPE)
                token = token.stdout.decode("utf-8")
                return ufile.read().strip() + "," + key.strip() + token.strip()
            elif context == "jdoeEphemeral":
                return "jdoe," + ephemeral_login(ufile.read().strip())
            else:
                print("Context not defined:")
    
