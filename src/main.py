import inspect
import logging
import os
import subprocess

import gnupg
import pyotp
from fastapi import FastAPI

# Import auth dependencies
from api.dependencies.auth import get_or_create_auth_token

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import routers (must be after logging config)
from api.routes import ephemeral, vpn

# Initialize FastAPI app
app = FastAPI(
    title="RH-OTP Auto-Connect API",
    description="Red Hat OTP Auto-Connect Service with VPN and Ephemeral Namespace Management",
    version="1.0.0"
)

# Include routers
app.include_router(vpn.router)
app.include_router(ephemeral.router)

debug_output = True


# Initialize auth token on startup
@app.on_event("startup")
async def startup_event():
    """Initialize authentication token and other startup tasks."""
    token = get_or_create_auth_token()
    logger.info("RH-OTP Auto-Connect Service started")
    logger.info(f"Authentication token initialized: {token[:8]}...")


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
        # Ephemeral login is now handled by /ephemeral/namespace/details endpoint
        # This is kept for backwards compatibility but should migrate to new API
        from services.ephemeral import get_namespace_name, get_namespace_password
        namespace = get_namespace_name(username, headless)
        password = get_namespace_password(namespace)
        return f"jdoe,{password}"
    else:
        debug("Context not defined:")


@app.get("/get_associate_email")
def get_associate_email():
    """Get get_associate_email."""
    debug(inspect.stack()[0][3])
    username = get_from_store("username").strip() + "@redhat.com"
    return f"{username}".replace('"', "").strip()
