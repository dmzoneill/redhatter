import base64
import inspect
import json
import logging
import os
import subprocess
from pprint import pformat
from subprocess import PIPE, Popen

import gnupg
import pyotp
from fastapi import FastAPI

# Initialize FastAPI app
app = FastAPI()

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Global cache to store temporary data
cache = {}
debug_output = True


def debug(out):
    if debug_output:
        logger.debug(out)


def getpw():
    """Generate HOTP token and increment the counter."""
    counter = int(get_from_store("hotp-counter").strip())
    hotp_secret = get_from_store("hotp-secret").strip()

    if not counter:
        raise ValueError("HOTP counter not found.")

    if not hotp_secret:
        raise ValueError("HOTP secret not found.")

    totp = pyotp.HOTP(hotp_secret)
    token = totp.at(counter)

    # Increment the counter and update the store
    counter += 1
    update_store("hotp-counter", str(counter))

    return token


def pexec(cmd):
    """Execute command and return output."""
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
    """Retrieve a password from the password store using gnupg, fall back to pass show if needed."""
    gpg = gnupg.GPG()
    pass_store_path = os.path.expanduser("~/.password-store")
    secret_file_path = os.path.join(pass_store_path, "redhat.com/" + the_item + ".gpg")

    if not os.path.exists(secret_file_path):
        logger.error(f"Error: {secret_file_path} does not exist.")
        return False

    # Try retrieving the password using gnupg first
    try:
        # Check if GPG is already caching the key (e.g., recent successful decryption)
        # We use `gnupg` to attempt decryption first, as `pass` should not prompt within a short window
        with open(secret_file_path, "rb") as f:
            decrypted_data = gpg.decrypt_file(f)
            if decrypted_data.ok:
                logger.debug(
                    f"Password for {the_item} successfully retrieved using gnupg (cached)."
                )
                return decrypted_data.data.decode("utf-8")  # Return decrypted password
            else:
                logger.error(
                    f"Error decrypting {the_item} with gnupg: {decrypted_data.status}"
                )
                return False
    except Exception as e:
        logger.error(f"Error retrieving password with gnupg: {e}")

    # If gnupg decryption fails, attempt to use pass show which will prompt if necessary
    logger.debug(f"Attempting to retrieve {the_item} using pass show...")
    try:
        result = subprocess.run(
            ["pass", "show", the_item], capture_output=True, text=True
        )

        if result.returncode == 0:
            logger.debug(
                f"Password for {the_item} successfully retrieved using pass show."
            )
            return result.stdout.strip()  # Return the decrypted password
        else:
            logger.error(f"Error retrieving password with pass show: {result.stderr}")
            return False
    except Exception as e:
        logger.error(f"Error retrieving password using pass show: {e}")

    # As a final fallback, attempt gnupg again after prompting the user if necessary
    logger.debug(
        "Fallback: Attempting gnupg decryption again after potential passphrase prompt."
    )
    try:
        with open(secret_file_path, "rb") as f:
            decrypted_data = gpg.decrypt_file(f)
            if decrypted_data.ok:
                logger.debug(
                    f"Password for {the_item} successfully retrieved after fallback."
                )
                return decrypted_data.data.decode("utf-8")  # Return decrypted password
            else:
                logger.error(
                    f"Error decrypting {the_item} after fallback with gnupg: {decrypted_data.status}"
                )
                return False
    except Exception as e:
        logger.error(f"Error retrieving password after fallback with gnupg: {e}")
        return False


def get_recipient_key_id():
    """Retrieve the recipient key ID from the .gpg-id file in the password store."""
    gpg_id_file = os.path.expanduser("~/.password-store/.gpg-id")
    if not os.path.exists(gpg_id_file):
        logger.error("Error: .gpg-id file not found.")
        return None

    with open(gpg_id_file, "r") as f:
        recipient_key_id = f.read().strip()

    if not recipient_key_id:
        logger.error("Error: .gpg-id file is empty.")
        return None

    return recipient_key_id


def update_store(the_item, new_value):
    """Update the password in the password store with a similar caching/prompting behavior as get_from_store."""
    gpg = gnupg.GPG()
    pass_store_path = os.path.expanduser("~/.password-store")

    secret_file_path = os.path.join(pass_store_path, "redhat.com/" + the_item + ".gpg")
    recipient_key_id = get_recipient_key_id()

    if not recipient_key_id:
        logger.error("Error: Unable to retrieve recipient key ID.")
        return False

    # Try to encrypt the password using gnupg first
    try:
        # Check if the GPG key is already cached
        encrypted_data = gpg.encrypt(new_value, recipient_key_id)
        if encrypted_data.ok:
            # If successful, write to the file
            with open(secret_file_path, "wb") as f:
                f.write(
                    encrypted_data.data
                )  # Save encrypted password back into the store
            logger.info(f"Successfully updated {the_item}.")
            return True
        else:
            logger.error(
                f"Error encrypting the data with gnupg: {encrypted_data.status}"
            )
            return False
    except Exception as e:
        logger.error(f"Error encrypting the password with gnupg: {e}")

    # If gnupg encryption fails or the key isn't cached, attempt to use pass show to prompt for the passphrase
    logger.debug(
        "Attempting to retrieve encryption passphrase interactively using pass show..."
    )
    try:
        # Running pass show to get passphrase from the user
        result = subprocess.run(
            ["pass", "show", the_item], capture_output=True, text=True
        )

        if result.returncode == 0:
            # If the passphrase was entered successfully, attempt to encrypt again
            encrypted_data = gpg.encrypt(new_value, recipient_key_id)
            if encrypted_data.ok:
                with open(secret_file_path, "wb") as f:
                    f.write(
                        encrypted_data.data
                    )  # Save encrypted password back into the store
                logger.info(f"Successfully updated {the_item} after pass show.")
                return True
            else:
                logger.error(
                    f"Error encrypting the data after pass show: {encrypted_data.status}"
                )
                return False
        else:
            logger.error(
                f"Error retrieving passphrase using pass show: {result.stderr}"
            )
            return False
    except Exception as e:
        logger.error(f"Error prompting for passphrase with pass show: {e}")

    # As a final fallback, attempt to encrypt using gnupg after potential passphrase prompt
    logger.debug(
        "Fallback: Attempting gnupg encryption again after potential passphrase prompt."
    )
    try:
        encrypted_data = gpg.encrypt(new_value, recipient_key_id)
        if encrypted_data.ok:
            with open(secret_file_path, "wb") as f:
                f.write(
                    encrypted_data.data
                )  # Save encrypted password back into the store
            logger.info(f"Successfully updated {the_item} after fallback.")
            return True
        else:
            logger.error(
                f"Error encrypting the data with gnupg after fallback: {encrypted_data.status}"
            )
            return False
    except Exception as e:
        logger.error(f"Error encrypting the password with gnupg after fallback: {e}")
        return False


def set_namespace(namespace):
    """Set the current namespace for kubectl/oc."""
    debug(inspect.stack()[0][3])
    pexec(f"/usr/local/bin/oc project {namespace}")


def ephemeral_login(username, headless):
    """Login to ephemeral environment and return password."""
    debug(inspect.stack()[0][3])
    namespace = get_namespace_name(username, headless)
    password = get_namespace_password(namespace)
    return password


def get_namespace_password(namespace):
    """Retrieve password for the given namespace."""
    debug(inspect.stack()[0][3])
    global cache

    if "eph-password" in cache:
        return cache["eph-password"]

    set_namespace(namespace)
    sc = pexec(f'/usr/local/bin/kubectl get secret "env-{namespace}-keycloak" -o json')
    secret = sc[1] if sc[0] else "{}"
    password = json.loads(secret)
    password = password["data"]["defaultPassword"]
    password = base64.b64decode(password).decode("utf-8")
    cache["eph-password"] = password
    return cache["eph-password"]


def get_namespace(username, headless=True):
    """Get namespace for the given user."""
    debug(inspect.stack()[0][3])
    global cache

    if "namespace" in cache:
        debug(cache["namespace"])
        return cache["namespace"]

    server = pexec("/usr/local/bin/oc project | awk -F'\"' '{print $4}'")
    server = server[1] if server[0] else ""

    headlessstr = "--headless" if headless else ""

    if server != "https://api.c-rh-c-eph.8p0c.p1.openshiftapps.com:6443":
        subprocess.call(f"/usr/local/bin/rhtoken e {headlessstr}", shell=True)

    namespace = pexec(f"~/.local/bin/bonfire namespace list | grep {username}")
    namespace = namespace[1] if namespace[0] else ""
    cache["namespace"] = namespace.split()
    debug('cache["namespace"] = ' + pformat(cache["namespace"]))
    return cache["namespace"]


def extend_namespace(namespace, headless):
    """Extend namespace duration."""
    debug(inspect.stack()[0][3])
    global cache
    pexec(f"bonfire namespace extend {namespace} -d 72h")
    cache = {}
    return get_namespace(namespace, headless)


def get_namespace_name(username, headless):
    """Get the name of the namespace."""
    debug(inspect.stack()[0][3])
    res = get_namespace(username, headless)
    if type(res) == list and len(res) > 0:
        return res[0]
    else:
        return "No visible reservation"


def get_namespace_expires(username, headless):
    """Get the expiration date of the namespace."""
    debug(inspect.stack()[0][3])
    res = get_namespace(username, headless)
    if type(res) == list and len(res) > 5:
        return res[6]
    else:
        return "No expiration"


def get_namespace_route(namespace):
    """Get the route for the namespace."""
    debug(inspect.stack()[0][3])
    global cache

    if "eph-route" in cache:
        return cache["eph-route"]

    set_namespace(namespace)
    server = pexec(
        "/usr/local/bin/kubectl get route 2>/dev/null | tail -n 1 | awk '{print $2}'"
    )
    server = server[1] if server[0] else ""

    cache["eph-route"] = server
    return cache["eph-route"]


@app.get("/")
def top_level():
    """Top-level route to check if the service is running."""
    debug(inspect.stack()[0][3])
    return "Nothing to see here"


@app.get("/get_creds")
def get_creds(context: str = "associate", headless: bool = False):
    """Get credentials based on context."""
    debug(inspect.stack()[0][3])
    username = get_from_store("username").strip()

    if context == "associate":
        key = get_from_store("associate-password").strip()

        if key is False:
            return "Failed"

        token = getpw().strip()
        debug(f"token = {token}")
        return f"{username},{key}{token}".strip()
    elif context == "jdoeEphemeral":
        return f"jdoe,{ephemeral_login(username, headless)}"
    else:
        debug("Context not defined:")


@app.get("/get_associate_email")
def get_associate_email():
    """Get get_associate_email."""
    debug(inspect.stack()[0][3])
    username = get_from_store("username").strip() + "@redhat.com"
    return f"{username}".replace('"', "").strip()


@app.get("/get_namespace_details")
def get_namespace_details(headless: bool = False):
    """Get namespace details for a user."""
    debug(inspect.stack()[0][3])
    username = get_from_store("username")

    if username is False:
        return "Failed"

    namespace = get_namespace_name(username, headless)
    result = (
        namespace
        + ","
        + get_namespace_route(namespace)
        + ","
        + get_namespace_expires(username, headless)
    )
    return result


@app.get("/clear_cache")
def get_clear_cache(headless: bool = False):
    """Clear the cache."""
    debug(inspect.stack()[0][3])
    global cache
    cache = {}

    username = get_from_store("username")

    if username is False:
        return "Failed"

    namespace = get_namespace_name(username, headless)
    return get_namespace(namespace, headless)


@app.get("/extend_namespace")
def get_extend_namespace(headless: bool = False):
    """Extend the namespace."""
    debug(inspect.stack()[0][3])
    username = get_from_store("username")

    if username is False:
        return "Failed"

    namespace = get_namespace_name(username, headless)
    return extend_namespace(namespace, headless)
