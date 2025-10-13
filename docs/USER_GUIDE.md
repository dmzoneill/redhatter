# User Guide

## Table of Contents

1. [Introduction](#introduction)
2. [Installation](#installation)
3. [Quick Start](#quick-start)
4. [VPN Management](#vpn-management)
5. [Chrome Extension](#chrome-extension)
6. [GNOME Extension](#gnome-extension)
7. [Ephemeral Namespaces](#ephemeral-namespaces)
8. [Troubleshooting](#troubleshooting)
9. [FAQ](#faq)

---

## Introduction

RH-OTP Auto-Connect is a comprehensive system for automating Red Hat infrastructure access:

- **VPN Management**: Connect to 21 global Red Hat VPN endpoints
- **Auto-Login**: Automatic SSO authentication in Chrome
- **Desktop Integration**: GNOME Shell extension with system tray
- **Ephemeral Namespaces**: Manage bonfire/OpenShift environments
- **Credential Management**: Secure GPG-encrypted password storage

### Prerequisites

- **Operating System**: Linux (Fedora/RHEL recommended)
- **Required**:
  - NetworkManager
  - GPG with configured key
  - Password store (`pass`)
  - Python 3.13+
- **Optional**:
  - Chrome/Chromium browser
  - GNOME Shell (for desktop extension)
  - bonfire CLI (for ephemeral namespaces)

---

## Installation

### Quick Install

```bash
# Clone repository
cd ~/src
git clone https://github.com/yourusername/rh-otp-auto-connect.git
cd rh-otp-auto-connect/src

# Install everything
make install
```

This installs:
- ✅ System and Python dependencies
- ✅ FastAPI service (systemd user service)
- ✅ Chrome extension and native host
- ✅ GNOME Shell extension (if GNOME detected)
- ✅ VPN profiles configuration

### Step-by-Step Installation

#### 1. Install Dependencies

```bash
# System packages (Fedora/RHEL)
sudo dnf install python3-pip NetworkManager-cli pass gpg

# Python dependencies
make install-deps
```

#### 2. Setup Password Store

```bash
# Initialize password store (if not already done)
pass init <your-gpg-key-id>

# Add required secrets
pass insert redhat.com/username
pass insert redhat.com/associate-password
pass insert redhat.com/hotp-secret
pass insert redhat.com/hotp-counter
```

**Required secrets**:
- `username`: Your Red Hat username (without @redhat.com)
- `associate-password`: Your Red Hat password (without OTP)
- `hotp-secret`: Your HOTP secret (base32 encoded)
- `hotp-counter`: Initial counter value (usually "0")

#### 3. Install FastAPI Service

```bash
# Install and start service
make install-service
systemctl --user enable rhotp
systemctl --user start rhotp

# Verify service is running
make status
```

#### 4. Setup VPN Profiles (Optional)

```bash
# Scan existing NetworkManager VPN profiles
make vpn-profiles-scan

# Install all 21 Red Hat VPN profiles
make vpn-profiles-install
```

#### 5. Install Chrome Extension (Optional)

```bash
# Install native messaging host
make install-chrome

# Load extension in Chrome
# 1. Open chrome://extensions/
# 2. Enable "Developer mode"
# 3. Click "Load unpacked"
# 4. Select src/rh-otp/ directory
# 5. Copy extension ID

# Configure native host with extension ID
python3 install_native_host.py --extension-id <YOUR_EXTENSION_ID>
```

#### 6. Install GNOME Extension (Optional)

```bash
# Install extension
make install-gnome

# Enable extension
make gnome-enable

# Open preferences
make gnome-prefs
```

---

## Quick Start

### 1. Start the Service

```bash
# If using systemd (recommended)
systemctl --user start rhotp

# Or manually
make start
```

Verify service is running:
```bash
curl http://localhost:8009/
# Should return: {"status": "ok", ...}
```

### 2. Connect to VPN

```bash
# Using default VPN
./vpn-connect

# Or using Makefile
make vpn-connect
```

### 3. Check VPN Status

```bash
# Using CLI
make vpn-status

# Or using API
TOKEN=$(cat ~/.cache/rhotp/auth_token)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8009/vpn/status
```

### 4. Disconnect VPN

```bash
make vpn-disconnect
```

---

## VPN Management

### Available VPN Endpoints

The system supports 21 Red Hat VPN endpoints across global locations:

**Americas**:
- IAD2 - Ashburn, Virginia
- RDU2 - Raleigh, North Carolina
- GRU2 - São Paulo, Brazil

**Europe**:
- AMS2 - Amsterdam, Netherlands
- BRQ2 - Brno, Czech Republic
- LCY - London, United Kingdom
- FAB - Farnborough, United Kingdom

**Asia-Pacific**:
- NRT - Tokyo, Japan
- PEK2 - Beijing, China
- SIN2 - Singapore
- SYD - Sydney, Australia
- PNQ2 - Pune, India

**Middle East**:
- TLV2 - Tel Aviv, Israel

**Global**:
- GLOBAL - ovpn.redhat.com (multiple variants)

**See all profiles**:
```bash
./vpn-profile-manager list
# Or
make vpn-profiles-list
```

---

### Connecting to VPN

#### Method 1: Default VPN (Quickest)

```bash
# Connect to default VPN (stored in password store)
./vpn-connect

# Or using Makefile
make vpn-connect
```

**How it works**:
1. Waits for FastAPI service (port 8009)
2. Fetches default VPN UUID from password store (`nm-uuid`)
3. Gets credentials with HOTP token
4. Connects via NetworkManager

#### Method 2: Specific Profile (CLI)

```bash
# Connect to specific profile by ID
./vpn-profile-manager connect IAD2

# Or using Makefile
make vpn-profile-connect PROFILE=BRQ2
```

#### Method 3: API Call

```bash
TOKEN=$(cat ~/.cache/rhotp/auth_token)

# Connect to specific profile
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/vpn/connect/iad2
```

#### Method 4: GNOME Extension

1. Click Red Hat icon in system tray
2. Navigate to **VPN Profiles** submenu
3. Select region → Select profile
4. Click to connect

---

### Setting Default VPN

```bash
# Set default VPN to Brno
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"profile_id": "BRQ2"}' \
  http://localhost:8009/vpn/default
```

Now `./vpn-connect` will use BRQ2 by default.

---

### VPN Status

```bash
# Check if connected
make vpn-status

# Or using API
curl -H "Authorization: Bearer $TOKEN" http://localhost:8009/vpn/status
```

**Output (Connected)**:
```json
{
  "connected": true,
  "profile_name": "Ashburn (IAD2)",
  "profile_id": "IAD2"
}
```

**Output (Not Connected)**:
```json
{
  "connected": false,
  "profile_name": null,
  "profile_id": null
}
```

---

### Disconnecting VPN

```bash
# Using Makefile
make vpn-disconnect

# Or using CLI
./vpn-profile-manager disconnect

# Or using API
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/vpn/disconnect
```

---

## Chrome Extension

### Features

- ✅ **Auto-Login**: Automatic form filling on Red Hat SSO pages
- ✅ **One-Click Password**: Copy password to clipboard
- ✅ **Ephemeral Integration**: Manage ephemeral environments
- ✅ **Context Switching**: Support for multiple credential contexts

### Usage

#### Auto-Login

1. Navigate to Red Hat SSO page (auth.redhat.com or sso.redhat.com)
2. Extension automatically detects login form
3. Fills username and password (with OTP)
4. Optionally auto-submits (configurable)

**Supported pages**:
- `auth.redhat.com` - Main Red Hat authentication
- `sso.redhat.com` - Secondary SSO portal
- Ephemeral environment login pages

#### Manual Password Retrieval

1. Click extension icon in toolbar
2. Click "Get Password"
3. Password copied to clipboard

#### Settings

Click extension icon → Settings (gear icon):

- **Auto-fill credentials**: Enable/disable automatic form filling
- **Auto-submit form**: Enable/disable automatic form submission
- **Headless mode**: Background operation without notifications

### Troubleshooting Chrome Extension

**Extension not working**:
```bash
# Check native host is installed
ls ~/.config/google-chrome/NativeMessagingHosts/com.redhat.rhotp.json

# Reinstall native host with correct extension ID
python3 install_native_host.py --extension-id <YOUR_EXTENSION_ID>

# Check service is running
systemctl --user status rhotp
```

**Error: "Access to native messaging host is forbidden"**:
- Extension ID in manifest doesn't match actual extension ID
- Solution: Reinstall native host with correct ID

**Error: "Native messaging host not found"**:
- Native host script not executable
- Solution: `chmod +x src/rh-otp/native_host.py`

---

## GNOME Extension

### Features

- ✅ **System Tray Integration**: Red Hat branded icon
- ✅ **VPN Profile Menu**: All 21 endpoints organized by region
- ✅ **Real-Time Status**: VPN connection monitoring
- ✅ **Password Operations**: Quick credential access
- ✅ **Desktop Notifications**: Operation feedback
- ✅ **Settings UI**: Native GNOME preferences

### Usage

#### System Tray Menu

Click Red Hat icon in system tray to access:

**VPN Management**:
- **VPN Profiles** submenu:
  - Americas → IAD2, RDU2, GRU2
  - Europe → AMS2, BRQ2, LCY, FAB
  - Asia-Pacific → NRT, PEK2, SIN2, SYD, PNQ2
  - Middle East → TLV2
  - Global → GLOBAL variants
- **Connect VPN (Standard)**: Connect to default VPN
- **Connect VPN (Shuttle)**: Alternative SSH tunnel method
- **Disconnect VPN**: Disconnect active connection
- **VPN Status**: Show current connection

**Credentials**:
- **Get Associate Password**: Copy password to clipboard
- **Get Ephemeral Password**: Copy ephemeral namespace password

**Ephemeral Namespaces**:
- **Extend Namespace**: Extend reservation duration

**System**:
- **Preferences**: Open settings UI

#### VPN Connection via Menu

1. Click Red Hat icon
2. Hover over **VPN Profiles**
3. Select region (e.g., "Europe")
4. Click profile (e.g., "Brno (BRQ2)")
5. Wait for desktop notification: "Connecting..."
6. Success notification: "✓ Connected to Brno (BRQ2)"

#### Status Indicator

The system tray icon shows VPN status:
- **Icon tooltip**: Shows connected profile or "Not connected"
- **Auto-refresh**: Updates every 30 seconds

#### Password Operations

**Get Associate Password**:
1. Click Red Hat icon
2. Click "Get Associate Password"
3. Password copied to clipboard
4. Desktop notification: "Password copied to clipboard"

**Get Ephemeral Password**:
1. Click Red Hat icon
2. Click "Get Ephemeral Password"
3. Namespace password copied to clipboard

#### Preferences

Access via menu → Preferences:

- **API URL**: FastAPI service URL (default: http://localhost:8009)
- **Auto-connect**: Enable/disable automatic operations
- **Notification settings**: Configure desktop notifications

### Troubleshooting GNOME Extension

**Extension not visible**:
```bash
# Check extension is installed
ls ~/.local/share/gnome-shell/extensions/rh-otp@local

# Enable extension
make gnome-enable

# Restart GNOME Shell
Alt+F2 → type "r" → Enter
```

**"Service not running" error**:
```bash
# Check FastAPI service
systemctl --user status rhotp

# Start service
systemctl --user start rhotp
```

**VPN profiles not showing**:
```bash
# Check profiles.yaml exists
ls src/vpn-profiles/profiles.yaml

# Regenerate profiles
make vpn-profiles-scan
```

**View extension logs**:
```bash
journalctl -f | grep gnome-shell
# Or
make gnome-logs
```

---

## Ephemeral Namespaces

### Overview

Manage bonfire/OpenShift ephemeral environments directly from the system.

### Prerequisites

```bash
# Install bonfire CLI
pip install --user crc-bonfire

# Verify installation
bonfire --version
```

### Operations

#### Get Namespace Details

```bash
TOKEN=$(cat ~/.cache/rhotp/auth_token)

curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8009/ephemeral/namespace/details?include_password=true"
```

**Response**:
```json
{
  "name": "ephemeral-abc123",
  "route": "https://my-app.apps.crc-eph.example.com",
  "expires": "2025-01-15T10:30:00Z",
  "password": "k8s_secret_password"
}
```

#### Check Namespace Status

```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/ephemeral/namespace/status
```

#### Extend Namespace Duration

```bash
# Extend by 72 hours (default)
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/ephemeral/namespace/extend

# Custom duration
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"duration": "48h"}' \
  http://localhost:8009/ephemeral/namespace/extend
```

#### Clear Cache

```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/ephemeral/namespace/clear-cache
```

---

## Troubleshooting

### Service Won't Start

**Check systemd status**:
```bash
systemctl --user status rhotp
```

**View logs**:
```bash
journalctl --user -u rhotp -f
```

**Common issues**:
- **Port 8009 already in use**: Another service using the port
  - Solution: `lsof -i :8009` to find process, then kill it
- **Missing dependencies**: Python packages not installed
  - Solution: `make install-deps`
- **Permission errors**: Token file permissions
  - Solution: `chmod 600 ~/.cache/rhotp/auth_token`

---

### VPN Connection Fails

**Check NetworkManager**:
```bash
systemctl status NetworkManager
```

**Verify profile exists**:
```bash
nmcli connection show | grep -i vpn
```

**Test manual connection**:
```bash
UUID=$(pass show redhat.com/nm-uuid)
sudo nmcli connection up uuid $UUID
```

**Common issues**:
- **"Connection activation failed"**: Incorrect credentials
  - Solution: Verify password store: `pass show redhat.com/associate-password`
- **"nm-uuid not found"**: Default VPN not set
  - Solution: Set default via API or initialize by calling `/vpn/default`
- **"Timeout"**: VPN endpoint unreachable
  - Solution: Try different profile

---

### Password Store Errors

**GPG decryption fails**:
```bash
# Test GPG decryption
pass show redhat.com/username

# Check GPG agent
gpg-connect-agent /bye
```

**HOTP counter out of sync**:
```bash
# Reset counter (use with caution!)
pass insert redhat.com/hotp-counter
# Enter: 0

# Then generate new token
TOKEN=$(cat ~/.cache/rhotp/auth_token)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8009/get_creds
```

---

### Chrome Extension Issues

**See [Chrome Extension Troubleshooting](#troubleshooting-chrome-extension)** section above.

---

### GNOME Extension Issues

**See [GNOME Extension Troubleshooting](#troubleshooting-gnome-extension)** section above.

---

## FAQ

### How do I get my HOTP secret?

1. Log into Red Hat SSO
2. Go to Account Settings → Two-Factor Authentication
3. Select "Time-based One-Time Password (TOTP)"
4. Save the displayed secret (base32 encoded string)
5. Store in password store: `pass insert redhat.com/hotp-secret`

### Can I use this with multiple Red Hat accounts?

Currently, the system supports a single account in the password store. For multiple accounts, you would need separate instances with different password store paths.

### Is my password secure?

Yes:
- ✅ Passwords encrypted with GPG
- ✅ HOTP secrets never transmitted unencrypted
- ✅ Temporary files immediately deleted
- ✅ Auth tokens are localhost-only
- ✅ No network exposure (localhost:8009)

### How do I update to the latest version?

```bash
cd ~/src/rh-otp-auto-connect
git pull origin main
make install  # Reinstall all components
systemctl --user restart rhotp
```

### Can I run this on macOS or Windows?

The system is designed for Linux. Some components (GNOME extension, NetworkManager) are Linux-specific. The FastAPI service and Chrome extension could potentially work on other platforms with modifications.

### How do I uninstall?

```bash
# Stop and disable service
systemctl --user stop rhotp
systemctl --user disable rhotp

# Remove systemd service
rm ~/.config/systemd/user/rhotp.service
systemctl --user daemon-reload

# Remove Chrome extension native host
make uninstall-chrome

# Remove GNOME extension
make uninstall-gnome

# Remove VPN profiles (optional)
make vpn-profiles-clean

# Remove project directory
cd ~ && rm -rf ~/src/rh-otp-auto-connect
```

### Where are logs stored?

```bash
# Service logs (systemd)
journalctl --user -u rhotp -f

# GNOME extension logs
journalctl -f | grep gnome-shell

# Chrome extension logs
Open chrome://extensions/ → Click extension → Background page → Console
```

### How do I report bugs?

Open an issue on GitHub with:
- Operating system and version
- Error messages from logs
- Steps to reproduce
- Expected vs. actual behavior

---

## Related Documentation

- **[Architecture](ARCHITECTURE.md)** - System architecture overview
- **[API Reference](API.md)** - Complete API documentation
- **[VPN Workflows](drawings/VPN_WORKFLOWS.md)** - VPN connection diagrams
- **[Authentication](drawings/AUTH_FLOWS.md)** - Authentication flow diagrams
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Development and contribution guide
