# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Recent Changes (2025-10-13)

### Project Restructuring
- **Moved all source code to `src/` directory** for better organization
- **Modularized codebase** into services, API routes, and models
- **Updated all paths** in Makefile, systemd units, and documentation

### Chrome Extension Native Messaging Fix
- **Added `nativeMessaging` permission** to manifest.json (src/rh-otp/manifest.json:10)
- **Fixed "Access to native messaging host is forbidden" error** by:
  - Installing native host with correct extension ID: `hpffdobkffegnaemnhninjeokmodeghh`
  - Updated all browser native messaging manifests
  - Verified native_host.py executable permissions
- **Native messaging flow**: popup.js → background.js → native_host.py → auth_token file

### Port Standardization
- **All services now run on port 8009** (previously mixed 8000/8009)
- Updated Chrome extension host_permissions to `http://localhost:8009/*`
- Consistent port usage across dev and production modes

## Quick Start Commands

### Using the Makefile (Recommended)
```bash
# Install all components and dependencies
make install

# Start the service (development mode with auto-reload)
make dev

# Start the service (production mode on port 8009)
make start

# Check service status and logs
make status
make logs

# Connect to VPN (standard mode)
make vpn-connect

# Connect to VPN (shuttle mode) 
make vpn-shuttle

# Check VPN status
make vpn-status

# VPN Profile Management (21 global endpoints)
make vpn-profiles-list                 # List all configured VPN profiles
make vpn-profiles-install              # Install all profiles to NetworkManager
make vpn-profile-connect PROFILE=IAD2  # Connect to specific profile
make vpn-profiles-clean-duplicates     # Remove duplicate profiles

# Run tests and code quality checks
make test
make lint

# Utility targets
make check-venv        # Check Python virtual environment used by service
make token-info        # Show authentication token file information
make requirements      # Generate requirements.txt from Pipfile
```

### Manual Service Commands
```bash
# Development (auto-reload on port 8009)
uvicorn main:app --reload --port 8009

# Production (port 8009)
uvicorn main:app --host 0.0.0.0 --port 8009

# Using Pipenv
pipenv run uvicorn main:app --host 0.0.0.0 --port 8009
```

### VPN Connection
```bash
# Standard VPN connection
./vpn-connect

# Shuttle VPN connection (SSH tunnel + sshuttle)
./vpn-connect-shuttle
```

## Architecture Overview

This is a comprehensive Red Hat VPN auto-connect system with five main components:

### 1. FastAPI Backend Service (main.py)
- **Port**: 8009 (both development and production)
- **Purpose**: Core authentication and credential management service
- **Security**: Bearer token authentication with auto-generated tokens
- **Key endpoints**:
  - `/` - Top-level endpoint to verify service is running
  - `/get_creds?context=associate&headless=false` - Returns username,password+otp
  - `/get_associate_email` - Returns user's email address
  - `/get_namespace_details` - Gets ephemeral environment details
  - `/extend_namespace` - Extends ephemeral namespace duration
  - `/clear_cache` - Invalidates in-memory cache
  - `/vpn/profiles` - Lists all configured VPN profiles (21 global endpoints)
  - `/vpn/profiles/{profile_id}` - Get specific VPN profile details
  - `/vpn/connect/{profile_id}` - Connect to specific VPN profile via NetworkManager
  - `/vpn/disconnect` - Disconnect active VPN connection
  - `/vpn/status` - Get current VPN connection status and profile information

### 2. Chrome Extension (rh-otp/)
- **Purpose**: Browser automation for Red Hat SSO login flows
- **Type**: Manifest V3 extension with native messaging support
- **Files**:
  - `manifest.json` - Extension configuration (V3)
  - `background.js` - Service worker for API communication
  - `contentscript.js` - Page injection for automatic login
  - `popup.html/js` - Extension UI with settings
  - `native_host.py` - Secure token bridge for Chrome
  - `com.redhat.rhotp.json` - Native messaging host manifest
- **Features**: 
  - Auto-fills credentials on Red Hat login pages
  - One-click password retrieval
  - Support for multiple SSO flows (auth.redhat.com, sso.redhat.com, ephemeral)
  - Settings management for automatic behavior

### 3. GNOME Shell Extension (rh-otp-gnome/)
- **Purpose**: Native desktop integration for GNOME environments
- **Files**:
  - `extension.js` - Main extension logic with system tray integration
  - `prefs.js` - Preferences UI for settings management
  - `metadata.json` - Extension metadata and compatibility
  - `schemas/` - GSettings schema for configuration storage
- **Features**:
  - System tray indicator with Red Hat branding
  - Password retrieval with clipboard integration
  - VPN connection management (standard and shuttle modes)
  - Real-time VPN status monitoring
  - Desktop notifications
  - Integrated preferences with GNOME Settings

### 4. VPN Connection Scripts
- **`vpn-connect`**: Standard NetworkManager-based VPN connection
- **`vpn-connect-shuttle`**: Alternative connection via SSH tunnel and sshuttle
- **Dependencies**: NetworkManager CLI, curl, pass, expect
- **Flow**: Wait for service → Fetch credentials → Connect via nmcli

### 5. Supporting Tools
- **`rhtoken`**: Selenium-based OpenShift token acquisition tool with auto-ChromeDriver management
- **`install_native_host.py`**: Chrome native messaging host installer with multi-browser support

## Installation & Setup

### System Dependencies (Fedora/RHEL)
```bash
sudo dnf install oathtool expect pass gpg python3-pip NetworkManager-cli curl
```

### Python Dependencies
```bash
# Using Pipenv (recommended)
pipenv install

# Or using pip directly
pip install fastapi uvicorn python-gnupg pyotp requests selenium beautifulsoup4 click
```

### Complete Installation
```bash
# Install everything (service, Chrome extension, GNOME extension)
make install

# Install specific components
make install-deps     # System and Python dependencies
make install-chrome   # Chrome extension and native host
make install-gnome    # GNOME Shell extension
```

## Password Store Integration

The system uses `pass` (Unix password manager) with GPG encryption:

### Required Secrets Structure
```
~/.password-store/redhat.com/
├── username          # Red Hat username
├── associate-password # Base password (without OTP)
├── hotp-secret       # HOTP secret for OTP generation
├── hotp-counter      # Current HOTP counter value
└── nm-uuid           # NetworkManager VPN connection UUID
```

### Password Store Functions
- `get_from_store(item)` - Retrieves encrypted values using gnupg/pass
- `update_store(item, value)` - Updates encrypted values (used for HOTP counter)
- **File permissions**: 600 for sensitive cached files
- **GPG agent integration**: Supports caching for seamless operation

## Security Architecture

### Authentication System
- **Bearer token authentication** for API security
- **Automatic token generation** and caching in `~/.cache/rhotp/auth_token`
- **Native messaging bridge** for secure Chrome extension communication
- **Restricted API access** - Chrome extension limited to localhost only

### OTP (One-Time Password) System
Uses HOTP (RFC 4226 compliant) algorithm:
- **Secret storage**: Encrypted in password store
- **Counter management**: Auto-incrementing with persistent storage
- **Code generation**: 6-digit codes via pyotp library
- **Integration**: Combined with base password for full authentication

### Encryption & Storage
- **GPG encryption** for all sensitive data
- **Temporary file cleanup** after use
- **Secure cache management** with proper file permissions
- **No secrets in logs** or error messages

## Ephemeral Environment Support

Integrates with Red Hat's bonfire/OpenShift ephemeral environments:
- **CLI tools**: Uses `oc` and `kubectl` for environment management
- **Namespace management**: Reservation and extension capabilities
- **Secret retrieval**: Fetches passwords from Kubernetes secrets
- **Mode support**: Both headless and interactive modes
- **Auto-detection**: Identifies ephemeral environment contexts

## Service Management

### Systemd User Service
```bash
# Install and enable service
make install-service

# Manual installation
cp systemd/rhotp.service ~/.config/systemd/user/
systemctl --user daemon-reload
systemctl --user enable rhotp
systemctl --user start rhotp

# Service management
systemctl --user status rhotp
systemctl --user restart rhotp
systemctl --user stop rhotp
```

### Service Configuration
- **Port**: 8009 (both development and production, expected by vpn-connect and extensions)
- **Health checks**: Use `/` endpoint or `make health` target to verify service is running
- **Logging**: Comprehensive logging to journald

## Development Workflow

### Code Quality & Testing
```bash
# Run all tests
make test

# Code formatting and linting
make lint          # Run all linters
make format        # Auto-format code with black
make type-check    # Run mypy type checking

# Security scanning
make security      # Run bandit and safety checks
```

### Development Mode
```bash
# Start development server with auto-reload
make dev

# Run specific tests
pipenv run pytest tests/test_main.py -v

# Manual testing
pipenv run python -m pytest --cov=main tests/
```

### Continuous Integration
- **GitHub Actions**: Automated testing on multiple Python versions
- **Security scanning**: bandit, safety, and dependency checks
- **Code quality**: Black, flake8, isort, mypy enforcement
- **Multi-platform testing**: Linux focus with cross-platform compatibility

## Browser Extension Details

### Supported Browsers
- Chrome, Chromium, Brave, Microsoft Edge, Chrome Beta
- **Manifest V3** compliance for future compatibility
- **Native messaging** for secure token communication

### Auto-Login Support
- **auth.redhat.com**: Main Red Hat authentication portal
- **sso.redhat.com**: Secondary SSO portal
- **Ephemeral environments**: Dynamic environment login forms
- **Form detection**: Automatic credential field identification

### Configuration Options
- **Automatic login**: Toggle for hands-free operation
- **API endpoint**: Configurable service URL
- **Headless mode**: Background operation without UI
- **Context switching**: Associate vs. ephemeral credentials

### Development Commands
```bash
# Install native messaging host for Chrome extension
make install-chrome

# List Chrome configuration directories for all browsers
make list-chrome-dirs

# Install for specific browsers only
make install-chrome-specific BROWSERS="chrome chromium"

# Reload extension (requires chrome-cli)
make extension-reload
```

## GNOME Extension Details

### Compatibility
- **GNOME Shell versions**: 3.36 through 49+ (wide compatibility)
- **Settings integration**: Native GNOME preferences support
- **Theme integration**: Follows system theme and styling

### Features
- **System tray integration**: Red Hat branded indicator with Red Hat icon
- **VPN profile management**:
  - Dynamic VPN profile submenu showing all 21 global VPN endpoints
  - Profiles organized by region (Americas, Europe, Asia-Pacific, Global)
  - One-click connection to any VPN endpoint via FastAPI
  - Real-time VPN connection status monitoring
- **VPN connection methods**:
  - VPN Profile submenu (new) - Select from 21 endpoints
  - Standard VPN connection (legacy) - Uses nm-uuid from pass store
  - Shuttle VPN connection - SSH tunnel + sshuttle
  - Disconnect VPN - Terminates active connection
- **Password operations**:
  - Retrieve Associate credentials (username + password + OTP)
  - Retrieve Ephemeral environment credentials
  - Automatic clipboard integration
- **Status monitoring**:
  - Real-time VPN status updates (connected/disconnected, profile name)
  - Service status indicator
  - Automatic VPN status refresh every 30 seconds
- **Notifications**: Desktop notifications for all operations
- **Auto-detection**: Automatic VPN script path detection
- **Settings integration**: Native GNOME preferences UI

### Development Workflow
```bash
# Install and enable extension (development mode with symlink)
make install-gnome
make gnome-enable

# Development commands
make gnome-reload      # Reload extension after changes
make gnome-logs        # Watch extension logs
make gnome-status      # Check extension status
make gnome-watch       # Auto-reload on file changes (requires inotify-tools)
make gnome-prefs       # Open preferences UI

# Utility commands
make gnome-disable     # Disable extension
make uninstall-gnome   # Uninstall extension
```

## VPN Profile Management

### Overview

The VPN profile management system provides centralized configuration and deployment of Red Hat OpenVPN profiles using NetworkManager. All profiles are defined in a single YAML file and can be managed via CLI or Makefile targets.

### Architecture

```
vpn-profiles/
├── profiles.yaml             # Single source of truth for all VPN endpoints
├── scan-profiles.py          # Scanner to extract existing NM profiles
├── templates/redhat-vpn.j2   # Jinja2 template for .nmconnection files
├── generated/                # Auto-generated configs (gitignored)
└── certs/ca-bundle.crt       # Red Hat CA certificates
```

### Quick Start

```bash
# List all configured VPN profiles (21 Red Hat locations)
make vpn-profiles-list
./vpn-profile-manager list

# Generate .nmconnection files from profiles.yaml
make vpn-profiles-generate

# Install all profiles to NetworkManager
make vpn-profiles-install

# Connect to specific profile
make vpn-profile-connect PROFILE=IAD2
./vpn-profile-manager connect IAD2

# Remove old/duplicate profiles
make vpn-profiles-clean-duplicates
```

### Workflow

#### 1. Scan Existing Profiles (One-time Setup)

Extract current NetworkManager configs into `profiles.yaml`:

```bash
make vpn-profiles-scan
```

This creates `vpn-profiles/profiles.yaml` with:
- All 21 discovered Red Hat VPN endpoints
- Extracted settings (remote, port, protocol, DNS, MTU, etc.)
- Default configurations that apply to all profiles

#### 2. Customize Configuration (Optional)

Edit `vpn-profiles/profiles.yaml` to:
- Add new VPN endpoints
- Modify DNS settings (`dns_search`)
- Adjust MTU or port settings
- Remove unwanted profiles

#### 3. Generate Profiles

Generate `.nmconnection` files from YAML:

```bash
# Generate all profiles
make vpn-profiles-generate

# Generate specific profile
./vpn-profile-manager generate IAD2
```

Features:
- Retrieves username from password store (`pass show redhat.com/username`)
- Applies default settings from `profiles.yaml`
- Renders Jinja2 template for each profile
- Outputs to `vpn-profiles/generated/`

#### 4. Install to NetworkManager

```bash
# Install all profiles
make vpn-profiles-install

# Install specific profile
./vpn-profile-manager install IAD2
```

This will:
- Copy files to `/etc/NetworkManager/system-connections/`
- Set permissions (600, root:root)
- Reload NetworkManager

#### 5. Connect to VPN

```bash
# Using Makefile
make vpn-profile-connect PROFILE=IAD2

# Using CLI tool
./vpn-profile-manager connect IAD2
./vpn-profile-manager disconnect
./vpn-profile-manager status

# Using existing vpn-connect script (uses nm-uuid from pass)
./vpn-connect
```

### VPN Profile Manager Commands

```bash
list              # List all configured VPN profiles
generate [id]     # Generate .nmconnection files for profiles
install [id]      # Install profile(s) to NetworkManager
install-all       # Install all profiles
connect <id>      # Connect to a specific VPN profile
disconnect        # Disconnect active VPN
status            # Show VPN connection status
clean             # Remove all Red Hat VPN profiles from NetworkManager
clean-duplicates  # Remove duplicate profiles (keeps first of each ID)
```

### Makefile Targets

```bash
make vpn-profiles-list              # List all configured profiles
make vpn-profiles-scan              # Scan NetworkManager for profiles
make vpn-profiles-generate          # Generate .nmconnection files
make vpn-profiles-install           # Install all profiles to NetworkManager
make vpn-profiles-clean             # Remove all Red Hat VPN profiles
make vpn-profiles-clean-duplicates  # Remove duplicate profiles
make vpn-profile-connect PROFILE=ID # Connect to specific profile
```

### profiles.yaml Structure

```yaml
default_settings:
  auth: SHA256
  ca: '{{project_dir}}/vpn-profiles/certs/ca-bundle.crt'
  cipher: AES-256-CBC
  data_ciphers: AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305:AES-256-CBC
  port: 443
  proto_tcp: true
  tunnel_mtu: 1360
  dns_search: '~.;redhat.com;'
  route_table: 75
  routing_rule: 'priority 16383 from 0.0.0.0/0 table 75'
  # ... other defaults

profiles:
  - id: IAD2
    name: "Ashburn (IAD2)"
    remote: ovpn-iad2.redhat.com
    # Inherits all default_settings unless overridden

  - id: AMS2
    name: "Amsterdam (AMS2)"
    remote: ovpn-ams2.redhat.com
    tunnel_mtu: 1300  # Override default
```

### Available VPN Endpoints

The system includes 21 Red Hat VPN endpoints across global locations:
- **Americas**: IAD2 (Ashburn), RDU2 (Raleigh), GRU2 (São Paulo)
- **Europe**: AMS2 (Amsterdam), BRQ2 (Brno), LCY (London), FAB (Farnborough)
- **Asia-Pacific**: NRT (Tokyo), PEK2 (Beijing), SIN2 (Singapore), SYD (Sydney), PNQ2 (Pune)
- **Middle East**: TLV2 (Tel Aviv)
- **Global**: GLOBAL (ovpn.redhat.com with multiple variants)
- **Specialized**: PEK2_ALT (Alternate Beijing), EGYPT_RDU2 (Egypt routing)

### Adding a New Profile

1. Edit `vpn-profiles/profiles.yaml`:

```yaml
profiles:
  - id: NEW_SITE
    name: "New Site Description"
    remote: ovpn-newsite.redhat.com
    # Optional overrides:
    port: 4443
    proto_tcp: false
    dns_search: "custom.domain;"
```

2. Generate and install:

```bash
make vpn-profiles-generate
make vpn-profiles-install
```

### Security & Best Practices

- **Generated files** (`.nmconnection`) are gitignored - contain username
- **profiles.yaml** is safe to commit - no credentials
- **Username** retrieved from password store at generation time
- **Password** provided by NetworkManager/vpn-connect at connection time
- **CA certificates** included in repository for convenience
- **DNS configuration**: Preserved from original profiles with `~.;redhat.com;` search domains
- **Routing**: Uses table 75 with priority 16383 for proper VPN routing

### Integration Points

- **Existing vpn-connect script**: Works with any profile by UUID from pass store
- **GNOME Extension**: VPN profile submenu for easy selection (✅ implemented)
  - Dynamically loads profiles from FastAPI `/vpn/profiles` endpoint
  - Organized by region (Americas, Europe, Asia-Pacific, Global)
  - One-click connection via FastAPI `/vpn/connect/{id}` endpoint
  - Real-time status via `/vpn/status` endpoint
- **FastAPI Backend**: VPN management endpoints (✅ implemented)
  - `GET /vpn/profiles` - List all 21 configured VPN profiles
  - `GET /vpn/profiles/{profile_id}` - Get specific profile details
  - `POST /vpn/connect/{profile_id}` - Connect to VPN using nmcli
  - `POST /vpn/disconnect` - Disconnect active VPN
  - `GET /vpn/status` - Get current VPN connection status
- **CLI Tool**: `vpn-profile-manager` for command-line profile management

### Troubleshooting

**Profile not connecting:**
```bash
# Check if installed
nmcli connection show | grep "Profile Name"

# Check UUID
./vpn-profile-manager list

# Try direct connection
nmcli connection up uuid "profile-uuid"

# View NetworkManager logs
journalctl -u NetworkManager -f
```

**Duplicate profiles:**
```bash
make vpn-profiles-clean-duplicates
```

**Username not found:**
```bash
pass show redhat.com/username
```

For detailed documentation, see `vpn-profiles/README.md`.

## Troubleshooting & Maintenance

### Common Issues
- **Service not running**: Check `make status` and `make logs`
- **Authentication failures**: Verify password store setup and GPG keys
- **VPN connection issues**: Check NetworkManager and nm-uuid configuration
- **Extension errors**: Check browser console and GNOME logs

### Log Locations
- **Service logs**: `journalctl --user -u rhotp -f`
- **Chrome extension**: Browser developer tools console
- **GNOME extension**: `journalctl -f | grep gnome-shell`

### Cache Management
```bash
# Clear service cache (requires authentication token)
token=$(cat ~/.cache/rhotp/auth_token)
curl -H "Authorization: Bearer $token" http://localhost:8009/clear_cache

# Clear authentication tokens
rm ~/.cache/rhotp/auth_token

# Reset HOTP counter (if needed)
pass edit redhat.com/hotp-counter
```

## File Structure

```
├── main.py                    # FastAPI service (main application)
├── Makefile                   # Comprehensive build and operation targets
├── Pipfile / Pipfile.lock     # Python dependency management
├── pyproject.toml             # Python project configuration
├── .github/workflows/         # CI/CD pipeline configuration
├── vpn-connect               # Standard VPN connection script
├── vpn-connect-shuttle       # SSH tunnel VPN connection script
├── vpn-profile-manager       # VPN profile management CLI tool
├── rhtoken                   # OpenShift token acquisition tool
├── install_native_host.py    # Chrome native host installer
├── vpn-profiles/             # VPN profile management system
│   ├── README.md             # VPN profile documentation
│   ├── profiles.yaml         # VPN profile definitions (source of truth)
│   ├── scan-profiles.py      # NetworkManager profile scanner
│   ├── templates/
│   │   └── redhat-vpn.j2     # Jinja2 template for .nmconnection files
│   ├── generated/            # Auto-generated configs (gitignored)
│   └── certs/
│       └── ca-bundle.crt     # Red Hat CA certificates
├── rh-otp/                   # Chrome extension
│   ├── manifest.json         # Extension configuration (V3)
│   ├── background.js         # Service worker
│   ├── contentscript.js      # Page automation
│   ├── popup.html/js         # Extension UI
│   ├── native_host.py        # Native messaging host
│   └── com.redhat.rhotp.json # Native host manifest
├── rh-otp-gnome/             # GNOME Shell extension
│   ├── extension.js          # Main extension logic
│   ├── prefs.js              # Preferences UI
│   ├── metadata.json         # Extension metadata
│   ├── rh.png                # Red Hat icon
│   └── schemas/              # GSettings configuration schema
│       ├── org.gnome.shell.extensions.rh-otp.gschema.xml
│       └── gschemas.compiled
├── systemd/                  # Service configuration
│   └── rhotp.service         # Systemd user service
├── tests/                    # Test suite
│   ├── test_main.py          # FastAPI service tests
│   └── __init__.py
└── README*.md                # Platform-specific setup guides
```

## Integration Points

### External Services
- **Red Hat SSO**: auth.redhat.com, sso.redhat.com authentication
- **OpenShift**: Ephemeral environment management via bonfire
- **NetworkManager**: VPN connection management
- **Password Store**: GPG-encrypted credential storage
- **GNOME Shell**: Desktop environment integration

### Cross-Component Communication
- **HTTP API**: Chrome/GNOME extensions ↔ FastAPI service
- **Native messaging**: Chrome extension ↔ Native host (secure token bridge)
- **D-Bus/GSettings**: GNOME extension preferences and configuration
- **File system**: Token and cache sharing between components

This project represents a production-ready, enterprise-grade solution for Red Hat infrastructure automation with comprehensive security, multi-platform integration, and professional development practices.