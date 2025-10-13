#!/usr/bin/env python3
"""
Native messaging host for Chrome extension to securely access authentication token.
This allows Chrome extension to read auth token without filesystem access.
"""

import json
import struct
import sys
from pathlib import Path


def send_message(message):
    """Send a message to the Chrome extension."""
    encoded_message = json.dumps(message).encode("utf-8")
    sys.stdout.buffer.write(struct.pack("I", len(encoded_message)))
    sys.stdout.buffer.write(encoded_message)
    sys.stdout.buffer.flush()


def read_message():
    """Read a message from the Chrome extension."""
    raw_length = sys.stdin.buffer.read(4)
    if not raw_length:
        return None
    message_length = struct.unpack("I", raw_length)[0]
    raw_message = sys.stdin.buffer.read(message_length)
    return json.loads(raw_message.decode("utf-8"))


def get_auth_token():
    """Read the authentication token from the cache file."""
    token_file = Path.home() / ".cache" / "rhotp" / "auth_token"

    if not token_file.exists():
        return None

    try:
        token = token_file.read_text().strip()
        return token if token else None
    except Exception:
        return None


def main():
    """Main native messaging host loop."""
    while True:
        try:
            message = read_message()
            if not message:
                break

            if message.get("action") == "get_token":
                token = get_auth_token()
                if token:
                    send_message({"success": True, "token": token})
                else:
                    send_message({"success": False, "error": "Token not found"})
            else:
                send_message({"success": False, "error": "Unknown action"})

        except Exception as e:
            send_message({"success": False, "error": str(e)})
            break


if __name__ == "__main__":
    main()
