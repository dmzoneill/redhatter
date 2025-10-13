# RedHat OTP Chrome Extension

Chrome extension for automatic Red Hat SSO login and credential management.

## Features

- **Automatic Login** - Auto-fill credentials on Red Hat SSO pages
- **Native Messaging** - Secure token communication with backend service
- **Multiple Contexts** - Support for Associate and Ephemeral environment credentials
- **Password Management** - One-click password retrieval and clipboard integration
- **Manifest V3** - Modern Chrome extension API compliance

## Installation

### 1. Install the Extension

```bash
# Quick install via Makefile
make install-chrome

# This will:
# - Install native messaging host
# - Configure for all Chrome-based browsers
# - Set proper permissions
```

### 2. Load Extension in Chrome

1. Open Chrome and navigate to `chrome://extensions/`
2. Enable **Developer mode** (toggle in top right)
3. Click **Load unpacked**
4. Select the `src/rh-otp/` directory
5. Copy the **Extension ID** (e.g., `hpffdobkffegnaemnhninjeokmodeghh`)

### 3. Configure Native Messaging Host

The native messaging host allows the extension to securely read authentication tokens.

```bash
# Install with your extension ID
python3 src/install_native_host.py --extension-id YOUR_EXTENSION_ID_HERE

# Or reinstall for all browsers
make install-chrome
```

### 4. Start the Backend Service

The extension requires the FastAPI backend service to be running:

```bash
# Development mode (auto-reload on port 8009)
make dev

# Or production mode
make start

# Verify service is running
curl http://localhost:8009/
```

## Usage

### Getting Credentials

1. **Pin the Extension** - Click the puzzle icon in Chrome toolbar, pin the Red Hat icon
2. **Navigate to Login** - Go to any Red Hat SSO page (auth.redhat.com, sso.redhat.com)
3. **Click Extension** - Click the Red Hat icon in the toolbar
4. **Select Context**:
   - **Associate** - Your Red Hat employee credentials with OTP
   - **Ephemeral** - Ephemeral environment credentials

The extension will:
- Fetch credentials from the backend (with auto-generated OTP)
- Auto-fill the login form
- Submit the form automatically (if configured)

### Clipboard Integration

Click the password display or clipboard icon to copy credentials to clipboard.

### Settings

Configure automatic login behavior:
- **Automatic Login (Ephemeral)** - Auto-submit on ephemeral environment login pages
- **Automatic Login (Stage)** - Auto-submit on staging environment pages
- **Automatic Login (Prod)** - Auto-submit on production pages
- **Headless Mode** - Use headless browser for token acquisition

## Supported Login Pages

- `auth.redhat.com/auth/realms/*` - Main Red Hat authentication
- `sso.redhat.com/auth/realms/*` - Secondary SSO portal
- `*.env-ephemeral.*.com/*` - Ephemeral environments

## Architecture

```
┌─────────────────┐      ┌──────────────────┐      ┌─────────────┐
│  Chrome/Popup   │─────▶│  Background.js   │─────▶│ Native Host │
│   (popup.js)    │      │ (service worker) │      │ (Python)    │
└─────────────────┘      └──────────────────┘      └─────────────┘
                                   │                       │
                                   ▼                       ▼
                         ┌──────────────────┐    ┌────────────────┐
                         │  FastAPI Service │    │  Auth Token    │
                         │  localhost:8009  │    │  ~/.cache/...  │
                         └──────────────────┘    └────────────────┘
```

### Components

1. **popup.js** - Extension UI and user interaction
2. **background.js** - Service worker, handles messages and API calls
3. **contentscript.js** - Page injection, auto-fills credentials
4. **native_host.py** - Native messaging host, reads auth token from cache
5. **manifest.json** - Extension configuration (Manifest V3)

### Security

- **Native Messaging** - Secure communication between extension and local system
- **Bearer Token Auth** - API requests authenticated with token from native host
- **Extension ID Validation** - Only authorized extension can use native host
- **HTTPS Only** - Credentials only sent over secure connections

## Troubleshooting

### "Access to native messaging host is forbidden"

This means the extension ID in the native messaging manifest doesn't match your extension:

```bash
# Get your extension ID from chrome://extensions/
# Then reinstall with correct ID:
python3 src/install_native_host.py --extension-id YOUR_ACTUAL_EXTENSION_ID
```

### Extension not auto-filling credentials

1. Check that the backend service is running: `curl http://localhost:8009/`
2. Check browser console for errors (F12 → Console)
3. Verify extension has `nativeMessaging` permission in manifest.json
4. Check that auth token exists: `cat ~/.cache/rhotp/auth_token`

### Native messaging errors

```bash
# Check native host manifest
cat ~/.config/google-chrome/NativeMessagingHosts/com.redhat.rhotp.json

# Verify native_host.py is executable
ls -la src/rh-otp/native_host.py

# Test native host manually
echo '{"action":"get_token"}' | python3 src/rh-otp/native_host.py
```

## Manual Installation

If automatic installation fails:

```bash
# 1. Make native host executable
chmod +x src/rh-otp/native_host.py

# 2. Create native messaging manifest
mkdir -p ~/.config/google-chrome/NativeMessagingHosts/

cat > ~/.config/google-chrome/NativeMessagingHosts/com.redhat.rhotp.json << EOF
{
  "name": "com.redhat.rhotp",
  "description": "Native messaging host for RHOTP Chrome extension",
  "path": "/full/path/to/src/rh-otp/native_host.py",
  "type": "stdio",
  "allowed_origins": [
    "chrome-extension://YOUR_EXTENSION_ID_HERE/"
  ]
}
EOF

# 3. Replace paths and extension ID
# Edit the file and update "path" and "allowed_origins"
```

## Development

### Reload Extension

After making changes:

```bash
# Option 1: Via Makefile (if chrome-cli installed)
make extension-reload

# Option 2: Manual
# Go to chrome://extensions/ and click reload button
```

### Debug Mode

1. Open extension popup
2. Right-click → Inspect
3. View console logs and network requests

### Testing Native Messaging

```bash
# Test auth token retrieval
python3 -c "
import json, sys, struct
from pathlib import Path

# Send request
msg = json.dumps({'action': 'get_token'})
sys.stdout.buffer.write(struct.pack('I', len(msg)))
sys.stdout.buffer.write(msg.encode())
sys.stdout.buffer.flush()

# Read response
length = struct.unpack('I', sys.stdin.buffer.read(4))[0]
response = json.loads(sys.stdin.buffer.read(length))
print(response)
" | python3 src/rh-otp/native_host.py
```

## Uninstall

```bash
# Remove native messaging host
python3 src/install_native_host.py --uninstall

# Remove extension from Chrome
# Go to chrome://extensions/ and click Remove
```

## Browser Support

- Google Chrome
- Chromium
- Brave Browser
- Microsoft Edge
- Chrome Beta/Unstable

All Chrome-based browsers are supported via the installation script.
