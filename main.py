# from oath_toolkit import HOTP
import inspect
from fastapi import FastAPI
from pprint import pprint, pformat
import subprocess
import json
import base64
from subprocess import Popen, PIPE

app = FastAPI()

cache = {}
debug_output = False


def debug(out):
    if debug_output:
        print(out)


def pexec(cmd):
    debug(inspect.stack()[0][3])
    debug(cmd)
    proc = Popen(cmd, stdout=PIPE, stderr=PIPE, shell=True)
    out, err = proc.communicate()
    exitcode = proc.returncode
    debug("Out = " + out.decode("UTF-8").strip())
    debug("Err = " + err.decode("UTF-8").strip())

    if exitcode != 0:
        debug(pformat(err.decode("UTF-8").strip()))

    return [True if exitcode == 0 else False, out.decode("UTF-8").strip()]


def get_from_store(the_item):
    debug(inspect.stack()[0][3])
    pw = pexec("pass show redhat.com/" + the_item)
    if pw[0]:
        return pw[1]
    else:
        return False


def get_from_file(the_file):
    debug(inspect.stack()[0][3])
    try:
        kfile = open(the_file, "r")
        return kfile.read().strip()
    except:
        return False


def set_namespace(namespace):
    debug(inspect.stack()[0][3])
    pexec("oc project " + namespace)


def ephemeral_login(username, headless):
    debug(inspect.stack()[0][3])
    namespace = get_namespace_name(username, headless)
    password = get_namespace_password(namespace)
    return password


def get_namespace_password(namespace):
    debug(inspect.stack()[0][3])
    global cache

    if "eph-password" in cache:
        return cache["eph-password"]

    set_namespace(namespace)

    sc = pexec('kubectl get secret "env-' + namespace + '-keycloak" -o json')
    secret = sc[1] if sc[0] else ""
    password = json.loads(secret)
    password = password["data"]["defaultPassword"]
    password = base64.b64decode(password).decode("utf-8")
    cache["eph-password"] = password
    return cache["eph-password"]


def get_namespace(username, headless=""):
    debug(inspect.stack()[0][3])
    global cache

    if "namespace" in cache:
        debug(cache["namespace"])
        return cache["namespace"]

    server = pexec("oc project | awk -F'\"' '{print $4}'")
    server = server[1] if server[0] else ""

    if server != "https://api.c-rh-c-eph.8p0c.p1.openshiftapps.com:6443":
        subprocess.call("/usr/bin/rhtoken e " + headless, shell=True)

    namespace = pexec("bonfire namespace list | grep " + username)
    debug("namespace[0] = " + str(namespace[0]))
    debug("namespace[1] = " + namespace[1])
    debug("namespace[1].split = " + pformat(namespace[1].split()))
    namespace = namespace[1] if namespace[0] else ""
    debug("namespace = " + namespace)

    cache["namespace"] = namespace.split()
    debug("cache[\"namespace\"] = " + pformat(cache["namespace"]))
    pprint(cache["namespace"])
    return cache["namespace"]


def extend_namespace(namespace, headless):
    debug(inspect.stack()[0][3])
    global cache
    pexec("bonfire namespace extend " + namespace + " -d 72h")
    cache = {}
    return get_namespace(namespace, headless)


def get_namespace_name(username, headless):
    debug(inspect.stack()[0][3])
    return get_namespace(username, headless)[0]


def get_namespace_expires(username, headless):
    debug(inspect.stack()[0][3])
    return get_namespace(username, headless)[6]


def get_namespace_route(namespace):
    debug(inspect.stack()[0][3])
    global cache

    if "eph-route" in cache:
        return cache["eph-route"]

    set_namespace(namespace)

    server = pexec(
        "kubectl get route 2>/dev/null | tail -n 1 | awk '{print $2}'")
    server = server[1] if server[0] else ""

    cache["eph-route"] = server
    return cache["eph-route"]


@app.get("/")
def top_level():
    debug(inspect.stack()[0][3])
    return "Nothing to see here"


@app.get("/get_creds")
def get_creds(context: str = "associate", headless: bool = False):
    debug(inspect.stack()[0][3])
    headlessstr = "--headless" if headless else ""
    username = get_from_file("username")

    if context == "associate":
        key = get_from_store("associate-password")
        key = key.strip() if key is not False else get_from_file("associate-password")

        if key is False:
            return "Failed"

        token = pexec("./getpw")
        debug("token = " + pformat(token))
        token = token[1] if token[0] else ""
        debug("token = " + token)
        return username + "," + key + token
    elif context == "jdoeEphemeral":
        return "jdoe," + ephemeral_login(username, headlessstr)
    else:
        debug("Context not defined:")


@app.get("/get_namespace_details")
def get_namespace_details(headless: bool = False):
    debug(inspect.stack()[0][3])
    username = get_from_file("username")

    if username is False:
        return "Failed"

    headlessstr = "--headless" if headless else ""
    namespace = get_namespace_name(username, headlessstr)
    result = (
        namespace
        + ","
        + get_namespace_route(namespace)
        + ","
        + get_namespace_expires(username, headlessstr)
    )
    return result


@app.get("/clear_cache")
def get_clear_cache(headless: bool = False):
    debug(inspect.stack()[0][3])
    global cache
    cache = {}

    username = get_from_file("username")

    if username is False:
        return "Failed"

    headlessstr = "--headless" if headless else ""
    namespace = get_namespace_name(username, headlessstr)
    return get_namespace(namespace, headless)


@app.get("/extend_namespace")
def get_extend_namespace(headless: bool = False):
    debug(inspect.stack()[0][3])
    username = get_from_file("username")

    if username is False:
        return "Failed"

    headlessstr = "--headless" if headless else ""
    namespace = get_namespace_name(username, headlessstr)
    return extend_namespace(namespace, headless)
