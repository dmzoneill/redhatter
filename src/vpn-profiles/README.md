# VPN Profile Management

This directory contains the VPN profile management system for Red Hat OpenVPN connections.

## Directory Structure

```
vpn-profiles/
├── README.md                 # This file
├── profiles.yaml             # Profile definitions (source of truth)
├── scan-profiles.py          # Scanner to extract profiles from NetworkManager
├── templates/
│   └── redhat-vpn.j2        # Jinja2 template for .nmconnection files
├── generated/                # Generated .nmconnection files (gitignored)
│   └── *.nmconnection
└── certs/
    └── ca-bundle.crt         # Red Hat CA certificates
```

## Quick Start

### List all configured VPN profiles

```bash
make vpn-profiles-list
# or
./vpn-profile-manager list
```

### Generate all profile configurations

```bash
make vpn-profiles-generate
# or
./vpn-profile-manager generate
```

### Install all profiles to NetworkManager

```bash
make vpn-profiles-install
# or
./vpn-profile-manager install-all
```

### Connect to a specific profile

```bash
make vpn-profile-connect PROFILE=IAD2
# or
./vpn-profile-manager connect IAD2
```

## Workflow

### 1. Initial Setup (One-time)

Scan existing NetworkManager configs to create `profiles.yaml`:

```bash
make vpn-profiles-scan
# or
cd vpn-profiles && python3 scan-profiles.py
```

This will:
- Scan `/etc/NetworkManager/system-connections/` for Red Hat VPN profiles
- Extract profile information (name, remote, port, protocol, etc.)
- Generate `profiles.yaml` with all discovered profiles

### 2. Customize profiles.yaml (Optional)

Edit `profiles.yaml` to:
- Add new VPN endpoints
- Modify DNS settings
- Adjust MTU or other parameters
- Remove unwanted profiles

### 3. Generate .nmconnection files

```bash
make vpn-profiles-generate
```

This will:
- Read username from password store (`pass show redhat.com/username`)
- Apply default settings from `profiles.yaml`
- Render Jinja2 template for each profile
- Save to `vpn-profiles/generated/`

### 4. Install profiles to NetworkManager

```bash
make vpn-profiles-install
```

This will:
- Copy `.nmconnection` files to `/etc/NetworkManager/system-connections/`
- Set proper permissions (600, root:root)
- Reload NetworkManager

### 5. Connect to VPN

```bash
# Using Makefile
make vpn-profile-connect PROFILE=IAD2

# Using vpn-profile-manager directly
./vpn-profile-manager connect IAD2

# Using nmcli directly
nmcli connection up "Ashburn (IAD2)"
```

## Management Commands

### vpn-profile-manager CLI

The `vpn-profile-manager` script provides comprehensive VPN profile management:

```bash
# List all profiles
./vpn-profile-manager list

# Generate specific profile
./vpn-profile-manager generate IAD2

# Generate all profiles
./vpn-profile-manager generate

# Install specific profile
./vpn-profile-manager install IAD2

# Install all profiles
./vpn-profile-manager install-all

# Connect to VPN
./vpn-profile-manager connect IAD2

# Disconnect VPN
./vpn-profile-manager disconnect

# Show VPN status
./vpn-profile-manager status

# Clean all Red Hat VPN profiles from NetworkManager
./vpn-profile-manager clean

# Remove duplicate profiles (keeps first of each ID)
./vpn-profile-manager clean-duplicates
```

### Make targets

```bash
make vpn-profiles-list              # List all configured profiles
make vpn-profiles-scan              # Scan NetworkManager for profiles
make vpn-profiles-generate          # Generate .nmconnection files
make vpn-profiles-install           # Install all profiles to NetworkManager
make vpn-profiles-clean             # Remove all Red Hat VPN profiles
make vpn-profiles-clean-duplicates  # Remove duplicate profiles
make vpn-profile-connect PROFILE=ID # Connect to specific profile
```

## Configuration

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
  # ... other defaults

profiles:
  - id: IAD2
    name: "Ashburn (IAD2)"
    remote: ovpn-iad2.redhat.com
    # Inherits all default_settings unless overridden

  - id: AMS2
    name: "Amsterdam (AMS2)"
    remote: ovpn-ams2.redhat.com
    # Can override defaults
    tunnel_mtu: 1300
```

### Adding a New Profile

1. Edit `profiles.yaml`:

```yaml
profiles:
  - id: NEW_SITE
    name: "New Site Description"
    remote: ovpn-newsite.redhat.com
    # Optional overrides:
    # port: 4443
    # proto_tcp: false
    # tunnel_mtu: 1400
    # dns_search: "custom.domain;"
```

2. Generate and install:

```bash
make vpn-profiles-generate
make vpn-profiles-install
```

## Troubleshooting

### Profile not connecting

1. Check if profile is installed:
```bash
nmcli connection show | grep "Profile Name"
```

2. Check profile UUID:
```bash
./vpn-profile-manager list
```

3. Try connecting with nmcli directly:
```bash
nmcli connection up uuid "profile-uuid-here"
```

4. Check NetworkManager logs:
```bash
journalctl -u NetworkManager -f
```

### Duplicate profiles

Remove duplicates (keeps first occurrence of each ID):
```bash
make vpn-profiles-clean-duplicates
```

### Username not found

Ensure username is in password store:
```bash
pass show redhat.com/username
```

### CA certificate issues

The CA bundle is copied from system to `vpn-profiles/certs/ca-bundle.crt`.
If issues occur, re-copy:
```bash
sudo cp /etc/pki/tls/certs/ca-bundle.crt vpn-profiles/certs/
```

## Security Notes

- **Generated files** (`.nmconnection`) are gitignored - they contain your username
- **profiles.yaml** is tracked in git - safe to commit (no credentials)
- **Username** is retrieved from password store at generation time
- **Password** is provided by NetworkManager/vpn-connect scripts at connection time
- **CA certificates** are included in the repository for convenience

## Integration

### With existing vpn-connect script

The existing `vpn-connect` script works with any installed profile by UUID from password store:

```bash
# Store your preferred VPN UUID
pass edit redhat.com/nm-uuid
# Then run
./vpn-connect
```

### With GNOME Extension

The GNOME extension will be updated to show a submenu of all available profiles for easy selection.

### With FastAPI backend

Future FastAPI endpoints will provide:
- `/vpn/profiles` - List available profiles
- `/vpn/connect/{profile_id}` - Connect to specific profile
- `/vpn/status` - Get VPN status
- `/vpn/disconnect` - Disconnect VPN

## Files

- **scan-profiles.py**: Python script to scan existing NetworkManager configs
- **profiles.yaml**: YAML configuration with all VPN profiles
- **templates/redhat-vpn.j2**: Jinja2 template for NetworkManager connection files
- **certs/ca-bundle.crt**: Red Hat CA certificates bundle
- **generated/**: Auto-generated .nmconnection files (gitignored)

## Notes

- All 21 discovered Red Hat VPN endpoints are included in `profiles.yaml`
- Profiles are generated with consistent settings from defaults
- DNS configuration is preserved from original profiles
- Routing table (75) and routing rules are configured for proper VPN routing
- IPv4 and IPv6 configurations are included
