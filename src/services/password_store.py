"""Password store service for managing GPG-encrypted credentials."""

import logging
import os
import subprocess

import gnupg
import pyotp

logger = logging.getLogger(__name__)

# Errors gnupg / file IO / decoding can raise.
_GPG_ERRORS = (OSError, ValueError, TypeError, RuntimeError)


class PasswordStoreService:
    """Service for interacting with the password store."""

    def __init__(self):
        self.gpg = gnupg.GPG()
        self.pass_store_path = os.path.expanduser("~/.password-store")

    def _decrypt_file(self, path, the_item, label):
        """Decrypt a .gpg file with gnupg; return the text, False on decrypt failure, None on error."""
        try:
            with open(path, "rb") as f:
                decrypted_data = self.gpg.decrypt_file(f)
        except _GPG_ERRORS as e:
            logger.error("Error retrieving password %s: %s", label, e)
            return None
        if not decrypted_data.ok:
            logger.error("Error decrypting %s %s: %s", the_item, label, decrypted_data.status)
            return False
        try:
            text = decrypted_data.data.decode("utf-8")
        except _GPG_ERRORS as e:
            logger.error("Error retrieving password %s: %s", label, e)
            return None
        logger.debug("Password for %s retrieved %s.", the_item, label)
        return text

    @staticmethod
    def _pass_show(the_item):
        """Run `pass show`; return the CompletedProcess, or None if it could not be run."""
        try:
            return subprocess.run(
                ["pass", "show", f"redhat.com/{the_item}"],
                capture_output=True,
                text=True,
                check=False,
            )
        except (OSError, subprocess.SubprocessError) as e:
            logger.error("Error running pass show: %s", e)
            return None

    def get_from_store(self, the_item):
        """
        Retrieve password from password store using gnupg, fall back to pass.

        Args:
            the_item: Item path relative to redhat.com/ (e.g., "username", "nm-uuid")

        Returns:
            Decrypted content as string, or False on error
        """
        secret_file_path = os.path.join(self.pass_store_path, "redhat.com/" + the_item + ".gpg")

        if not os.path.exists(secret_file_path):
            logger.error("Error: %s does not exist.", secret_file_path)
            return False

        # Try retrieving the password using gnupg first
        value = self._decrypt_file(secret_file_path, the_item, "with gnupg")
        if value is not None:
            return value

        # If gnupg decryption fails, attempt to use pass show which will prompt if necessary
        logger.debug("Attempting to retrieve %s using pass show...", the_item)
        result = self._pass_show(the_item)
        if result is not None:
            if result.returncode != 0:
                logger.error("Error retrieving password with pass show: %s", result.stderr)
                return False
            logger.debug("Password for %s successfully retrieved using pass show.", the_item)
            return result.stdout.strip()

        # As a final fallback, attempt gnupg again after prompting the user if necessary
        logger.debug("Fallback: Attempting gnupg decryption again after potential passphrase prompt.")
        value = self._decrypt_file(secret_file_path, the_item, "after fallback with gnupg")
        return False if value is None else value

    def get_recipient_key_id(self):
        """Retrieve the recipient key ID from the .gpg-id file in the password store."""
        gpg_id_file = os.path.join(self.pass_store_path, ".gpg-id")
        if not os.path.exists(gpg_id_file):
            logger.error("Error: .gpg-id file not found.")
            return None

        with open(gpg_id_file, encoding="utf-8") as f:
            recipient_key_id = f.read().strip()

        if not recipient_key_id:
            logger.error("Error: .gpg-id file is empty.")
            return None

        return recipient_key_id

    def _encrypt_to_file(self, path, new_value, recipient_key_id, label):
        """Encrypt and write; return True/False on gnupg result, None on error."""
        try:
            encrypted_data = self.gpg.encrypt(new_value, recipient_key_id)
            if not encrypted_data.ok:
                logger.error("Error encrypting the data %s: %s", label, encrypted_data.status)
                return False
            with open(path, "wb") as f:
                f.write(encrypted_data.data)
        except _GPG_ERRORS as e:
            logger.error("Error encrypting the password %s: %s", label, e)
            return None
        return True

    def update_store(self, the_item, new_value):
        """
        Update the password in the password store.

        Args:
            the_item: Item path relative to redhat.com/ (e.g., "username", "nm-uuid")
            new_value: New value to store

        Returns:
            True if successful, False otherwise
        """
        secret_file_path = os.path.join(self.pass_store_path, "redhat.com/" + the_item + ".gpg")
        recipient_key_id = self.get_recipient_key_id()

        if not recipient_key_id:
            logger.error("Error: Unable to retrieve recipient key ID.")
            return False

        # Try to encrypt the password using gnupg first
        ok = self._encrypt_to_file(secret_file_path, new_value, recipient_key_id, "with gnupg")
        if ok is not None:
            if ok:
                logger.info("Successfully updated %s.", the_item)
            return ok

        # If gnupg encryption fails, attempt to use pass show to prompt for the passphrase
        logger.debug("Attempting to retrieve encryption passphrase interactively using pass show...")
        result = self._pass_show(the_item)
        if result is not None:
            if result.returncode != 0:
                logger.error("Error retrieving passphrase using pass show: %s", result.stderr)
                return False
            ok = self._encrypt_to_file(secret_file_path, new_value, recipient_key_id, "after pass show")
            if ok:
                logger.info("Successfully updated %s after pass show.", the_item)
            if ok is not None:
                return ok

        # As a final fallback, attempt to encrypt using gnupg after potential passphrase prompt
        logger.debug("Fallback: Attempting gnupg encryption again after potential passphrase prompt.")
        ok = self._encrypt_to_file(secret_file_path, new_value, recipient_key_id, "with gnupg after fallback")
        if ok:
            logger.info("Successfully updated %s after fallback.", the_item)
        return bool(ok)

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

        logger.debug("Generated HOTP token (counter: %s)", counter)
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
            logger.error("Failed to generate OTP: %s", e)
            return None, None


# Global instance
password_store = PasswordStoreService()
