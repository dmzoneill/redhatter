from fastapi import FastAPI
from pprint import pprint
import subprocess
import json
import base64
from subprocess import Popen, PIPE

app = FastAPI()

cache = {}


def pexec(cmd):
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = proc.communicate()
    exitcode = proc.returncode

    if exitcode != 0:
        pprint(err)

    return out


def set_namespace(namespace):
    pexec("oc project " + namespace)


def ephemeral_login(username, headless):
    namespace = get_namespace_name(username, headless)
    password = get_namespace_password(namespace)
    return password


def get_namespace_password(namespace):
    global cache

    if "eph-password" in cache:
        return cache["eph-password"]

    set_namespace(namespace)
    secret = pexec("kubectl get secret \"env-" + namespace +
                   "-keycloak\" -o json").decode("UTF-8").strip()
    password = json.loads(secret)
    password = password['data']['defaultPassword']
    password = base64.b64decode(password).decode("utf-8")
    cache["eph-password"] = password
    return cache["eph-password"]


def get_namespace(username, headless=""):
    global cache

    if 'namespace' in cache:
        return cache["namespace"]

    server = pexec(
        "oc project | awk -F'\"' '{print $4}'").decode("UTF-8").strip()
    if server != "https://api.c-rh-c-eph.8p0c.p1.openshiftapps.com:6443":
        subprocess.call("/usr/bin/rhtoken e " + headless, shell=True)
    namespace = pexec("bonfire namespace list | grep " +
                      username).decode("UTF-8").strip()
    cache["namespace"] = namespace.split()
    pprint(cache["namespace"])
    return cache["namespace"]


def extend_namespace(namespace, headless):
    global cache
    pexec("bonfire namespace extend " + namespace + " -d 72h")
    cache = {}
    return get_namespace(namespace, headless)


def get_namespace_name(username, headless):
    return get_namespace(username, headless)[0]


def get_namespace_expires(username, headless):
    return get_namespace(username, headless)[6]


def get_namespace_route(namespace):
    global cache

    if "eph-route" in cache:
        return cache["eph-route"]

    set_namespace(namespace)
    server = pexec(
        "kubectl get route 2>/dev/null | tail -n 1 | awk '{print $2}'").decode("UTF-8").strip()
    cache["eph-route"] = server
    return cache["eph-route"]


@app.get("/")
def top_level():
    return "Nothing to see here"


@app.get("/get_creds")
def get_creds(context: str = "associate", headless: bool = False):
    with open('key', 'r') as kfile:
        with open('username', 'r') as ufile:
            key = kfile.read()
            if context == "associate":
                token = subprocess.run(['./getpw'], stdout=subprocess.PIPE)
                token = token.stdout.decode("utf-8")
                return ufile.read().strip() + "," + key.strip() + token.strip()
            elif context == "jdoeEphemeral":
                headlessstr = "--headless" if headless else ""
                return "jdoe," + ephemeral_login(ufile.read().strip(), headlessstr)
            else:
                print("Context not defined:")


@app.get("/get_namespace_details")
def get_namespace_details(headless: bool = False):
    with open('username', 'r') as ufile:
        headlessstr = "--headless" if headless else ""
        namespace = get_namespace_name(ufile.read().strip(), headlessstr)
        result = namespace + "," + get_namespace_route(
            namespace) + "," + get_namespace_expires(ufile.read().strip(), headlessstr)
        return result


@app.get("/clear_cache")
def get_clear_cache(headless: bool = False):
    global cache
    cache = {}
    with open('username', 'r') as ufile:
        headlessstr = "--headless" if headless else ""
        namespace = get_namespace_name(ufile.read().strip(), headlessstr)
        return get_namespace(namespace, headless)


@app.get("/extend_namespace")
def get_extend_namespace(headless: bool = False):
    with open('username', 'r') as ufile:
        headlessstr = "--headless" if headless else ""
        namespace = get_namespace_name(ufile.read().strip(), headlessstr)
        return extend_namespace(namespace, headless)
