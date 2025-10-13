# RedHat OTP VPN Auto Connect

A comprehensive automation tool for Red Hat employees to seamlessly connect to the company VPN and manage authentication for various internal services using one-time passwords (OTP).

## Overview

rh-otp-auto-connect is a multi-component system that provides:

- **Automated VPN Connection** - One-click VPN connection with automatic OTP generation
- **FastAPI Backend** - Secure credential management service with bearer token authentication
- **Chrome Extension** - Browser automation for Red Hat SSO and ephemeral environment logins
- **GNOME Integration** - Native desktop extension with system tray integration
- **VPN Profile Management** - Support for 21 global Red Hat VPN endpoints

The system automatically retrieves and enters OTP codes for VPN authentication and web-based logins, streamlining the authentication process across all Red Hat services.

## Components

1. **FastAPI Service** (`src/main.py`) - Core authentication and credential management API
2. **Chrome Extension** (`src/rh-otp/`) - Browser automation with native messaging support
3. **GNOME Extension** (`src/rh-otp-gnome/`) - Desktop system tray integration
4. **VPN Scripts** (`src/vpn-connect*`) - Automated VPN connection utilities
5. **Native Messaging Host** (`src/rh-otp/native_host.py`) - Secure token bridge for Chrome

## Prerequisites

- [kubectl](https://kubernetes.io/docs/tasks/tools/)
- [bonfire](https://pypi.org/project/crc-bonfire/)
- [oc](https://docs.openshift.com/container-platform/4.11/cli_reference/openshift_cli/getting-started-cli.html)
- [pass](https://www.passwordstore.org/) - GPG-encrypted password store
- Python 3.8+
- NetworkManager (for VPN connections)

## Quick Start

### Installation

```bash
# Install all components (service, Chrome extension, GNOME extension)
make install

# Or install specific components
make install-deps      # System and Python dependencies
make install-chrome    # Chrome extension and native messaging host
make install-gnome     # GNOME Shell extension
```

### Running the Service

```bash
# Development mode (auto-reload)
make dev

# Production mode
make start

# Check status
make status
make logs
```

### VPN Connection

```bash
# Connect to default VPN
make vpn-connect

# Connect to specific profile
make vpn-profile-connect PROFILE=IAD2

# List all VPN profiles (21 global endpoints)
make vpn-profiles-list
```

## Documentation

- [Linux Setup Guide](README.LINUX.md)
- [Chrome Extension Guide](README.CHROME.md)
- [Developer Documentation](CLAUDE.md)

## Architecture

The system uses a layered architecture:

- **API Layer** - FastAPI endpoints with bearer token authentication
- **Service Layer** - Business logic for credential management, VPN, and ephemeral environments
- **Storage Layer** - GPG-encrypted password store via `pass`
- **Integration Layer** - Chrome native messaging, GNOME D-Bus, NetworkManager

For detailed architecture documentation, see [CLAUDE.md](CLAUDE.md).

## Security

- All credentials stored encrypted via GPG in `pass`
- Bearer token authentication for API access
- Native messaging for secure Chrome extension communication
- No secrets in logs or error messages
- Token caching with proper file permissions (600)

## License

See [LICENSE.txt](LICENSE.txt)