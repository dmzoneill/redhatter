"""Password store service for managing GPG-encrypted credentials."""

import logging
import os
import subprocess

import gnupg
import pyotp

logger = logging.getLogger(__name__)


class PasswordStoreService:
    """Service for interacting with the password store."""

    def __init__(self):
        self.gpg = gnupg.GPG()
        self.pass_store_path = os.path.expanduser("~/.password-store")

    def get_from_store(self, the_item):
        """
        Retrieve password from password store using gnupg, fall back to pass.

        Args:
            the_item: Item path relative to redhat.com/ (e.g., "username", "nm-uuid")

        Returns:
            Decrypted content as string, or False on error
        """
        secret_file_path = os.path.join(
            self.pass_store_path, "redhat.com/" + the_item + ".gpg"
        )

        if not os.path.exists(secret_file_path):
            logger.error(f"Error: {secret_file_path} does not exist.")
            return False

        # Try retrieving the password using gnupg first
        try:
            with open(secret_file_path, "rb") as f:
                decrypted_data = self.gpg.decrypt_file(f)
                if decrypted_data.ok:
                    logger.debug(
                        f"Password for {the_item} retrieved using gnupg (cached)."
                    )
                    return decrypted_data.data.decode("utf-8")
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
                ["pass", "show", f"redhat.com/{the_item}"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                logger.debug(
                    f"Password for {the_item} successfully retrieved using pass show."
                )
                return result.stdout.strip()
            else:
                logger.error(
                    f"Error retrieving password with pass show: {result.stderr}"
                )
                return False
        except Exception as e:
            logger.error(f"Error retrieving password using pass show: {e}")

        # As a final fallback, attempt gnupg again after prompting the user if necessary
        logger.debug(
            "Fallback: Attempting gnupg decryption again after potential passphrase prompt."
        )
        try:
            with open(secret_file_path, "rb") as f:
                decrypted_data = self.gpg.decrypt_file(f)
                if decrypted_data.ok:
                    logger.debug(
                        f"Password for {the_item} successfully retrieved after fallback."
                    )
                    return decrypted_data.data.decode("utf-8")
                else:
                    logger.error(
                        f"Error decrypting {the_item} after fallback with gnupg: {decrypted_data.status}"
                    )
                    return False
        except Exception as e:
            logger.error(f"Error retrieving password after fallback with gnupg: {e}")
            return False

    def get_recipient_key_id(self):
        """Retrieve the recipient key ID from the .gpg-id file in the password store."""
        gpg_id_file = os.path.join(self.pass_store_path, ".gpg-id")
        if not os.path.exists(gpg_id_file):
            logger.error("Error: .gpg-id file not found.")
            return None

        with open(gpg_id_file, "r") as f:
            recipient_key_id = f.read().strip()

        if not recipient_key_id:
            logger.error("Error: .gpg-id file is empty.")
            return None

        return recipient_key_id

    def update_store(self, the_item, new_value):
        """
        Update the password in the password store.

        Args:
            the_item: Item path relative to redhat.com/ (e.g., "username", "nm-uuid")
            new_value: New value to store

        Returns:
            True if successful, False otherwise
        """
        secret_file_path = os.path.join(
            self.pass_store_path, "redhat.com/" + the_item + ".gpg"
        )
        recipient_key_id = self.get_recipient_key_id()

        if not recipient_key_id:
            logger.error("Error: Unable to retrieve recipient key ID.")
            return False

        # Try to encrypt the password using gnupg first
        try:
            encrypted_data = self.gpg.encrypt(new_value, recipient_key_id)
            if encrypted_data.ok:
                with open(secret_file_path, "wb") as f:
                    f.write(encrypted_data.data)
                logger.info(f"Successfully updated {the_item}.")
                return True
            else:
                logger.error(
                    f"Error encrypting the data with gnupg: {encrypted_data.status}"
                )
                return False
        except Exception as e:
            logger.error(f"Error encrypting the password with gnupg: {e}")

        # If gnupg encryption fails, attempt to use pass show to prompt for the passphrase
        logger.debug(
            "Attempting to retrieve encryption passphrase interactively using pass show..."
        )
        try:
            result = subprocess.run(
                ["pass", "show", f"redhat.com/{the_item}"],
                capture_output=True,
                text=True,
            )

            if result.returncode == 0:
                encrypted_data = self.gpg.encrypt(new_value, recipient_key_id)
                if encrypted_data.ok:
                    with open(secret_file_path, "wb") as f:
                        f.write(encrypted_data.data)
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
            encrypted_data = self.gpg.encrypt(new_value, recipient_key_id)
            if encrypted_data.ok:
                with open(secret_file_path, "wb") as f:
                    f.write(encrypted_data.data)
                logger.info(f"Successfully updated {the_item} after fallback.")
                return True
            else:
                logger.error(
                    f"Error encrypting the data with gnupg after fallback: {encrypted_data.status}"
                )
                return False
        except Exception as e:
            logger.error(
                f"Error encrypting the password with gnupg after fallback: {e}"
            )
            return False

    def generate_hotp_token(self):
        """
        Generate HOTP token and increment the counter.

        Returns:
            6-digit HOTP token as string

        Raises:
            ValueError: If counter or secret not found
        """
        counter = self.get_from_store("hotp-counter")
        hotp_secret = self.get_from_store("hotp-secret")

        if not counter or counter is False:
            raise ValueError("HOTP counter not found in password store.")

        if not hotp_secret or hotp_secret is False:
            raise ValueError("HOTP secret not found in password store.")

        counter = int(counter.strip())
        hotp_secret = hotp_secret.strip()

        # Generate token
        hotp = pyotp.HOTP(hotp_secret)
        token = hotp.at(counter)

        # Increment and save counter
        counter += 1
        self.update_store("hotp-counter", str(counter))

        logger.debug(f"Generated HOTP token (counter: {counter})")
        return token

    def get_username(self):
        """Get the Red Hat username from password store."""
        username = self.get_from_store("username")
        return username.strip() if username else None

    def get_associate_password(self):
        """Get the associate password (without OTP) from password store."""
        password = self.get_from_store("associate-password")
        return password.strip() if password else None

    def get_associate_credentials(self):
        """
        Get full associate credentials (username + password + OTP).

        Returns:
            Tuple of (username, password_with_otp) or (None, None) on error
        """
        username = self.get_username()
        password = self.get_associate_password()

        if not username or not password:
            logger.error("Failed to retrieve username or password from store")
            return None, None

        try:
            otp_token = self.generate_hotp_token()
            full_password = f"{password}{otp_token}"
            return username, full_password
        except ValueError as e:
            logger.error(f"Failed to generate OTP: {e}")
            return None, None


# Global instance
password_store = PasswordStoreService()
