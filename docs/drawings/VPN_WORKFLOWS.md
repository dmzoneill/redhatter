# VPN Connection Workflows

## Overview

This document details all VPN connection workflows in the RH-OTP system.

---

## 1. Standard VPN Connection (via vpn-connect script)

```mermaid
sequenceDiagram
    actor User
    participant Script as vpn-connect
    participant API as FastAPI :8009
    participant VPN as VPN Service
    participant Pass as Pass Store
    participant NM as NetworkManager

    User->>Script: Execute ./vpn-connect

    Note over Script: Wait for service
    loop Every 2 seconds
        Script->>Script: nc -z localhost 8009
    end

    Note over Script: Read auth token
    Script->>Script: Read ~/.cache/rhotp/auth_token

    Note over Script: Get default VPN UUID
    Script->>API: GET /vpn/default<br/>Authorization: Bearer TOKEN
    API->>VPN: get_default_vpn_uuid()
    VPN->>Pass: pass show redhat.com/nm-uuid
    Pass-->>VPN: UUID string

    alt UUID not found
        VPN->>VPN: Initialize to GLOBAL profile
        VPN->>Pass: pass insert redhat.com/nm-uuid
    end

    VPN->>VPN: load_vpn_profiles()
    VPN->>VPN: find_profile_by_uuid(UUID)
    VPN-->>API: {uuid, profile_id, profile_name}
    API-->>Script: JSON response

    Script->>Script: Parse JSON, extract UUID

    Note over Script: Get credentials
    Script->>API: GET /get_creds?context=associate
    API->>Pass: get_associate_credentials()
    Pass->>Pass: Read hotp-counter
    Pass->>Pass: Generate HOTP token
    Pass->>Pass: Increment counter
    Pass->>Pass: Update hotp-counter
    Pass-->>API: username, password+OTP
    API-->>Script: "username,password123456"

    Script->>Script: Parse credentials
    Script->>Script: Extract password

    Note over Script: Create temp password file
    Script->>Script: echo "vpn.secrets.password:$pw" > /tmp/vpnpw
    Script->>Script: sudo chmod 600 /tmp/vpnpw

    Note over Script: Connect via NetworkManager
    Script->>NM: sudo nmcli con up uuid UUID<br/>passwd-file /tmp/vpnpw
    NM->>NM: Read password from file
    NM->>NM: Connect to VPN endpoint
    NM-->>Script: Connection activated

    Script->>Script: sudo rm /tmp/vpnpw
    Script-->>User: Connected!
```

---

## 2. VPN Connection with Specific Profile (via API)

```mermaid
sequenceDiagram
    actor User
    participant Client as Client<br/>(GNOME/Chrome)
    participant API as FastAPI :8009
    participant VPN as VPN Service
    participant Script as vpn-connect
    participant NM as NetworkManager

    User->>Client: Select VPN Profile "IAD2"
    Client->>API: POST /vpn/connect/iad2<br/>Authorization: Bearer TOKEN

    API->>VPN: load_vpn_profiles()
    VPN->>VPN: Read profiles.yaml (cached)
    VPN->>VPN: find_profile_by_id("IAD2")

    alt Profile not found
        VPN-->>API: HTTPException 404
        API-->>Client: {"detail": "Profile not found"}
        Client-->>User: Error: Profile not found
    end

    VPN->>VPN: Extract UUID from profile
    VPN-->>API: profile_uuid, profile_name

    API->>API: find_script_path("vpn-connect")

    alt Script not found
        API-->>Client: HTTPException 404
        Client-->>User: Error: Script not found
    end

    API->>Script: Execute: ./vpn-connect --uuid UUID
    Note over Script: Same flow as standard connection<br/>but uses provided UUID
    Script->>NM: nmcli con up uuid UUID
    NM-->>Script: Connection result
    Script-->>API: Exit code + output

    alt Connection successful
        API->>VPN: get_vpn_connection_status()
        VPN->>NM: nmcli connection show --active
        NM-->>VPN: Active connections
        VPN-->>API: Connection details
        API-->>Client: {success: true, profile_name: "Ashburn (IAD2)"}
        Client-->>User: ✓ Connected to Ashburn (IAD2)
    else Connection failed
        API-->>Client: HTTPException 500
        Client-->>User: ✗ Failed to connect
    end
```

---

## 3. VPN Connection via GNOME Extension

```mermaid
sequenceDiagram
    actor User
    participant Tray as System Tray
    participant Ext as GNOME Extension
    participant API as FastAPI :8009
    participant VPN as VPN Service

    User->>Tray: Click Red Hat icon
    Tray->>Ext: Show menu

    Note over Ext: Load VPN profiles
    Ext->>API: GET /vpn/profiles
    API->>VPN: load_vpn_profiles()
    VPN-->>API: 21 profiles
    API-->>Ext: JSON array

    Ext->>Ext: Build VPN submenu<br/>Organized by region
    Ext->>Tray: Display menu with profiles

    User->>Tray: Select "Americas → Ashburn (IAD2)"
    Tray->>Ext: Menu item clicked

    Ext->>Ext: Extract profile_id = "IAD2"
    Ext->>API: POST /vpn/connect/iad2

    Note over Ext: Show notification
    Ext->>User: Desktop notification:<br/>"Connecting to Ashburn (IAD2)..."

    API->>VPN: Connect to profile
    Note over API,VPN: Standard connection flow
    VPN-->>API: Connection result

    alt Success
        API-->>Ext: {success: true}
        Ext->>User: Desktop notification:<br/>"✓ Connected to Ashburn (IAD2)"
        Ext->>Ext: Update status indicator
    else Failure
        API-->>Ext: {success: false, detail: "..."}
        Ext->>User: Desktop notification:<br/>"✗ Failed: ..."
    end

    Note over Ext: Update status every 30s
    loop Status monitoring
        Ext->>API: GET /vpn/status
        API->>VPN: get_vpn_connection_status()
        VPN-->>API: {connected, profile_name}
        API-->>Ext: Status update
        Ext->>Ext: Update icon/tooltip
    end
```

---

## 4. VPN Disconnection

```mermaid
sequenceDiagram
    actor User
    participant Client as Client<br/>(Any)
    participant API as FastAPI :8009
    participant VPN as VPN Service
    participant NM as NetworkManager

    User->>Client: Request disconnect
    Client->>API: POST /vpn/disconnect<br/>Authorization: Bearer TOKEN

    API->>VPN: get_vpn_connection_status()
    VPN->>NM: nmcli connection show --active
    NM-->>VPN: Active connections list

    VPN->>VPN: Parse for VPN connections<br/>Filter by type='vpn'

    alt No active VPN
        VPN-->>API: {connected: false}
        API-->>Client: {success: true, was_connected: false}
        Client-->>User: No active VPN connection
    end

    VPN-->>API: {connected: true, profile_name: "..."}

    API->>NM: nmcli connection down id "profile_name"
    NM->>NM: Disconnect VPN
    NM-->>API: Disconnection result

    alt Success
        API-->>Client: {success: true, was_connected: true}
        Client-->>User: ✓ Disconnected from VPN
    else Failure
        API-->>Client: HTTPException 500
        Client-->>User: ✗ Failed to disconnect
    end
```

---

## 5. VPN Status Check

```mermaid
sequenceDiagram
    participant Client as Client<br/>(Any)
    participant API as FastAPI :8009
    participant VPN as VPN Service
    participant NM as NetworkManager

    Client->>API: GET /vpn/status
    API->>VPN: get_vpn_connection_status()

    VPN->>NM: nmcli connection show --active
    NM-->>VPN: Output (text)

    VPN->>VPN: Parse output line by line
    loop For each line
        VPN->>VPN: Split by whitespace
        VPN->>VPN: Check if type contains 'vpn'
        alt Is VPN connection
            VPN->>VPN: Extract name (first fields)
            VPN->>VPN: Extract UUID (3rd from end)
        end
    end

    alt VPN found
        VPN-->>API: {connected: true,<br/>profile_name: "...",<br/>connection_uuid: "..."}

        API->>VPN: load_vpn_profiles()
        VPN-->>API: profiles list

        API->>API: Match by name or UUID
        API->>API: Extract profile_id

        API-->>Client: {connected: true,<br/>profile_name: "Ashburn (IAD2)",<br/>profile_id: "IAD2",<br/>connection_details: {...}}
    else No VPN
        VPN-->>API: {connected: false}
        API-->>Client: {connected: false,<br/>profile_name: null,<br/>profile_id: null}
    end
```

---

## 6. VPN Profile Listing

```mermaid
sequenceDiagram
    participant Client as Client<br/>(Any)
    participant API as FastAPI :8009
    participant VPN as VPN Service
    participant FS as File System

    Client->>API: GET /vpn/profiles
    API->>VPN: load_vpn_profiles(use_cache=true)

    VPN->>VPN: Check if cache exists

    alt Cache exists
        VPN->>FS: stat profiles.yaml<br/>Get mtime
        FS-->>VPN: mtime timestamp

        VPN->>VPN: Compare with cached mtime

        alt File unchanged
            VPN->>VPN: Return cached data
            VPN-->>API: Cached profiles (fast!)
        else File changed
            VPN->>FS: Read profiles.yaml
            FS-->>VPN: YAML content
            VPN->>VPN: Parse YAML
            VPN->>VPN: Update cache + mtime
            VPN-->>API: Fresh profiles
        end
    else No cache
        VPN->>FS: Read profiles.yaml
        FS-->>VPN: YAML content
        VPN->>VPN: yaml.safe_load()
        VPN->>VPN: Store in cache
        VPN-->>API: Parsed profiles
    end

    API->>API: Extract profiles array
    API-->>Client: JSON: [{id, name, remote, ...}, ...]
```

---

## 7. Default VPN Management

```mermaid
sequenceDiagram
    actor User
    participant Client as vpn-profile-manager
    participant API as FastAPI :8009
    participant VPN as VPN Service
    participant Pass as Pass Store

    Note over User,Pass: GET Default VPN

    User->>Client: ./vpn-profile-manager list
    Client->>API: GET /vpn/default

    API->>VPN: get_default_vpn_uuid(password_store)
    VPN->>Pass: pass show redhat.com/nm-uuid

    alt nm-uuid exists
        Pass-->>VPN: UUID string
        VPN->>VPN: load_vpn_profiles()
        VPN->>VPN: find_profile_by_uuid(UUID)
        VPN-->>API: {uuid, profile_id, profile_name,<br/>source: "password_store"}
    else nm-uuid not found
        Pass-->>VPN: null
        VPN->>VPN: load_vpn_profiles()
        VPN->>VPN: get_global_profile()
        VPN->>Pass: pass insert redhat.com/nm-uuid <UUID>
        Pass-->>VPN: Success
        VPN-->>API: {uuid, profile_id, profile_name,<br/>source: "password_store (initialized)"}
    end

    API-->>Client: JSON response
    Client-->>User: Default: Ashburn (IAD2)

    Note over User,Pass: SET Default VPN

    User->>Client: Set default to BRQ2
    Client->>API: POST /vpn/default<br/>{profile_id: "BRQ2"}

    API->>VPN: load_vpn_profiles()
    VPN-->>API: profiles

    API->>API: find_profile_by_id("BRQ2")

    alt Profile found
        API->>API: Extract UUID
        API->>VPN: set_default_vpn_uuid(UUID)
        VPN->>Pass: pass insert redhat.com/nm-uuid <UUID>
        Pass-->>VPN: Success
        VPN-->>API: true
        API-->>Client: {success: true,<br/>message: "Default VPN set to Brno (BRQ2)"}
        Client-->>User: ✓ Default set to Brno (BRQ2)
    else Profile not found
        API-->>Client: HTTPException 404
        Client-->>User: ✗ Profile 'BRQ2' not found
    end
```

---

## 8. Shuttle VPN Connection (Alternative Method)

```mermaid
sequenceDiagram
    actor User
    participant Script as vpn-connect-shuttle
    participant API as FastAPI :8009
    participant VPS as Personal VPS<br/>(fio.ie:2222)
    participant Tunnel as sshuttle

    User->>Script: Execute ./vpn-connect-shuttle

    Note over Script: Wait for service
    loop Every 2 seconds
        Script->>Script: nc -z localhost 8009
    end

    Script->>Script: Read ~/.cache/rhotp/auth_token

    Script->>API: GET /get_creds?context=associate
    API-->>Script: "username,password123456"

    Script->>Script: Parse password
    Script->>Script: Create /tmp/vpnpw-shuttle

    Note over Script,VPS: Setup VPN on remote server

    Script->>VPS: ssh root@fio.ie -p 2222<br/>"supervisorctl stop openvpn"
    VPS->>VPS: Stop OpenVPN service
    VPS-->>Script: Success

    Script->>VPS: scp /tmp/vpnpw-shuttle<br/>root@fio.ie:/vpn/auth.txt
    VPS-->>Script: File transferred

    Script->>VPS: ssh root@fio.ie -p 2222<br/>"supervisorctl restart openvpn"
    VPS->>VPS: Start OpenVPN with new creds
    VPS-->>Script: Service restarted

    Script->>Script: rm /tmp/vpnpw-shuttle

    Note over Script,Tunnel: Setup SSH tunnel

    Script->>Tunnel: sudo sshuttle --dns<br/>-r root@fio.ie<br/>--ssh-cmd "ssh -p 2222"<br/>10.0.0.0/8

    Tunnel->>VPS: Establish SSH connection
    VPS-->>Tunnel: Connected

    Tunnel->>Tunnel: Create tunnel routes<br/>for 10.0.0.0/8
    Tunnel-->>Script: Tunnel active

    Script-->>User: Connected via shuttle!

    Note over Tunnel: Tunnel runs until CTRL+C

    User->>Tunnel: CTRL+C
    Tunnel->>Tunnel: Cleanup routes
    Tunnel->>VPS: Close SSH connection
    Tunnel-->>User: Disconnected
```

**Note**: This is a personal workflow using custom infrastructure (hardcoded SSH keys, VPS, etc.)

---

## 9. VPN Profile Installation (Setup)

```mermaid
sequenceDiagram
    actor Admin
    participant CLI as vpn-profile-manager
    participant FS as File System
    participant Jinja as Jinja2
    participant NM as NetworkManager

    Admin->>CLI: ./vpn-profile-manager generate IAD2

    CLI->>CLI: load_profiles() from YAML
    CLI->>CLI: get_from_store("username")
    CLI->>CLI: Filter profiles (if ID specified)

    loop For each profile
        CLI->>CLI: Merge default_settings + profile
        CLI->>CLI: Replace {{project_dir}} in paths
        CLI->>CLI: Generate UUID if missing

        CLI->>Jinja: template.render(**context)
        Jinja-->>CLI: .nmconnection file content

        CLI->>FS: Write to vpn-profiles/generated/
        FS-->>CLI: File written
    end

    CLI-->>Admin: Generated 1 profile(s)

    Admin->>CLI: ./vpn-profile-manager install IAD2

    CLI->>CLI: generate_profiles() first
    Note over CLI: Generation step from above

    CLI->>FS: List vpn-profiles/generated/*.nmconnection
    FS-->>CLI: [IAD2_*.nmconnection]

    loop For each generated file
        CLI->>NM: sudo cp file.nmconnection<br/>/etc/NetworkManager/system-connections/
        CLI->>NM: sudo chmod 600 file.nmconnection
        CLI->>NM: sudo chown root:root file.nmconnection
    end

    CLI->>NM: sudo nmcli connection reload
    NM->>NM: Reload all connections
    NM-->>CLI: Reloaded

    CLI-->>Admin: Installed 1 profile(s)!
```

---

## Key Workflow Characteristics

### Performance

| Workflow | Typical Duration | Blocking Operations |
|----------|------------------|---------------------|
| Standard VPN connect | 3-5 seconds | nmcli negotiation |
| API profile list | 50ms | YAML cache (mtime check) |
| Status check | 100ms | nmcli show --active |
| Disconnect | 1-2 seconds | nmcli down |
| Shuttle connect | 10-15 seconds | SSH + OpenVPN restart |

### Security

| Workflow | Security Measures |
|----------|------------------|
| All API calls | Bearer token authentication |
| Password temp files | chmod 600, immediate deletion |
| Password store | GPG encryption |
| HOTP tokens | Auto-increment counter, single-use |
| Sudo operations | Explicit user action required |

### Reliability

| Workflow | Failure Handling |
|----------|------------------|
| Service wait | Retries every 2s (vpn-connect) |
| Profile caching | File mtime-based invalidation |
| nmcli failures | Captured stderr, logged |
| Missing profiles | HTTPException with clear messages |

---

## Related Documentation

- **[Architecture Overview](../ARCHITECTURE.md)** - System architecture
- **[API Reference](../API.md)** - Endpoint documentation
- **[Authentication Flows](AUTH_FLOWS.md)** - Authentication diagrams
- **[User Guide](../USER_GUIDE.md)** - End-user instructions
