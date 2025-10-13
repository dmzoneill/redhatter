# Architecture Overview

## System Architecture

```mermaid
graph TB
    subgraph "User Interfaces"
        CLI[CLI Tools<br/>vpn-connect, vpn-profile-manager]
        Chrome[Chrome Extension<br/>rh-otp]
        GNOME[GNOME Shell Extension<br/>rh-otp-gnome]
    end

    subgraph "FastAPI Service :8009"
        API[FastAPI App<br/>main.py]
        VPNRoutes[VPN Routes<br/>/vpn/*]
        EphemRoutes[Ephemeral Routes<br/>/ephemeral/*]
        LegacyRoutes[Legacy Routes<br/>/get_creds, etc]
    end

    subgraph "Services Layer"
        VPNSvc[VPN Service<br/>vpn.py]
        EphSvc[Ephemeral Service<br/>ephemeral.py]
        PassSvc[Password Store Service<br/>password_store.py]
    end

    subgraph "External Systems"
        NM[NetworkManager<br/>nmcli]
        Pass[Password Store<br/>pass + GPG]
        Bonfire[Bonfire CLI<br/>OpenShift]
        OC[oc/kubectl<br/>Kubernetes]
    end

    subgraph "Authentication"
        Token[Auth Token<br/>~/.cache/rhotp/auth_token]
        Native[Native Messaging Host<br/>native_host.py]
    end

    CLI --> API
    Chrome --> Native
    Native --> Token
    Chrome --> API
    GNOME --> API
    GNOME --> CLI

    API --> VPNRoutes
    API --> EphemRoutes
    API --> LegacyRoutes

    VPNRoutes --> VPNSvc
    EphemRoutes --> EphSvc
    LegacyRoutes --> PassSvc

    VPNSvc --> NM
    VPNSvc --> Pass
    EphSvc --> Bonfire
    EphSvc --> OC
    PassSvc --> Pass

    style API fill:#4CAF50
    style VPNSvc fill:#2196F3
    style EphSvc fill:#2196F3
    style PassSvc fill:#2196F3
```

## Component Overview

### 1. FastAPI Service (Port 8009)

**Core application** providing REST API for all operations:
- **VPN Management**: Connect, disconnect, profile management
- **Ephemeral Namespaces**: Bonfire integration for OpenShift environments
- **Credential Management**: HOTP token generation, password retrieval
- **Authentication**: Bearer token-based security

**Technology**:
- FastAPI (Python async web framework)
- Uvicorn (ASGI server)
- Modular routing (vpn, ephemeral, legacy)

---

### 2. VPN Management System

**Components**:
- **FastAPI Routes** (`api/routes/vpn.py`): REST endpoints
- **VPN Service** (`services/vpn.py`): Business logic
- **Profile Manager** (`vpn-profile-manager`): CLI tool
- **Connection Scripts** (`vpn-connect`, `vpn-connect-shuttle`): Bash wrappers

**Capabilities**:
- 21 global VPN endpoints (Red Hat infrastructure)
- Profile-based configuration (YAML)
- NetworkManager integration
- Default profile management

---

### 3. Password Store Integration

**Components**:
- **Password Store Service** (`services/password_store.py`)
- **GPG Integration**: Encrypted credential storage
- **HOTP Token Generation**: RFC 4226 compliant

**Secrets Structure**:
```
~/.password-store/redhat.com/
├── username
├── associate-password
├── hotp-secret
├── hotp-counter
└── nm-uuid
```

---

### 4. Chrome Extension

**Components**:
- **Manifest V3 Extension** (`rh-otp/`)
- **Native Messaging Host** (`rh-otp/native_host.py`)
- **Background Service Worker** (`background.js`)
- **Content Scripts** (`contentscript.js`)

**Capabilities**:
- Auto-login to Red Hat SSO
- One-click password retrieval
- Ephemeral environment integration
- Native token access (secure bridge)

---

### 5. GNOME Shell Extension

**Components**:
- **Extension Core** (`rh-otp-gnome/extension.js`)
- **Preferences UI** (`rh-otp-gnome/prefs.js`)
- **GSettings Schema**: Configuration storage

**Capabilities**:
- System tray integration
- VPN profile menu (21 endpoints)
- Real-time status monitoring
- Desktop notifications
- Password clipboard integration

---

### 6. Ephemeral Namespace Management

**Components**:
- **Ephemeral Service** (`services/ephemeral.py`)
- **Bonfire CLI Integration**: Namespace operations
- **OpenShift Integration**: `oc` and `kubectl` commands

**Capabilities**:
- Namespace listing and filtering
- Namespace extension (duration management)
- Password retrieval from Kubernetes secrets
- Route discovery
- Cache management

---

### 7. OpenShift Token Tool

**Component**: `rhtoken` (Selenium-based automation)

**Capabilities**:
- Auto-install ChromeDriver
- Automated browser login
- Token extraction from OAuth pages
- Support for 6 environments
- KUBECONFIG integration

---

## Data Flow

### VPN Connection Flow

```mermaid
sequenceDiagram
    participant User
    participant CLI as vpn-connect
    participant API as FastAPI :8009
    participant VPN as VPN Service
    participant Pass as Password Store
    participant NM as NetworkManager

    User->>CLI: ./vpn-connect
    CLI->>CLI: Wait for service (port 8009)
    CLI->>CLI: Read auth token
    CLI->>API: GET /vpn/default (Bearer token)
    API->>VPN: get_default_vpn_uuid()
    VPN->>Pass: get_from_store("nm-uuid")
    Pass-->>VPN: UUID
    VPN-->>API: UUID + profile info
    API-->>CLI: {"uuid": "abc-123", "profile_name": "..."}
    CLI->>API: GET /get_creds
    API->>Pass: get_associate_credentials()
    Pass->>Pass: Generate HOTP token
    Pass-->>API: username, password+OTP
    API-->>CLI: "username,password123456"
    CLI->>CLI: Create /tmp/vpnpw
    CLI->>NM: sudo nmcli con up uuid <UUID>
    NM-->>CLI: Connection active
    CLI->>User: Connected!
```

---

### Chrome Extension Authentication Flow

```mermaid
sequenceDiagram
    participant Page as Red Hat SSO Page
    participant CS as Content Script
    participant BG as Background Worker
    participant NH as Native Host
    participant API as FastAPI :8009
    participant Pass as Password Store

    Page->>CS: Load (auth.redhat.com)
    CS->>CS: Detect login form
    CS->>BG: Request credentials
    BG->>NH: Native message: get_token
    NH->>NH: Read ~/.cache/rhotp/auth_token
    NH-->>BG: {"success": true, "token": "..."}
    BG->>API: GET /get_creds (Bearer token)
    API->>Pass: get_associate_credentials()
    Pass->>Pass: Generate HOTP token
    Pass-->>API: username, password+OTP
    API-->>BG: "username,password123456"
    BG-->>CS: {username: "...", password: "..."}
    CS->>Page: Fill form fields
    CS->>Page: Submit form
    Page-->>CS: Login success
```

---

### Ephemeral Namespace Extension

```mermaid
sequenceDiagram
    participant User
    participant Ext as Chrome Extension
    participant API as FastAPI :8009
    participant Eph as Ephemeral Service
    participant Bonfire as bonfire CLI
    participant K8s as Kubernetes

    User->>Ext: Click "Extend Namespace"
    Ext->>API: POST /ephemeral/namespace/extend
    API->>Eph: extend_namespace(duration="72h")
    Eph->>Bonfire: bonfire namespace extend <ns> -d 72h
    Bonfire->>K8s: Update reservation
    K8s-->>Bonfire: Success
    Bonfire-->>Eph: Success
    Eph->>Bonfire: bonfire namespace list
    Bonfire-->>Eph: Updated namespace info
    Eph-->>API: {success: true, new_expiration: "..."}
    API-->>Ext: Extension confirmed
    Ext->>User: "Namespace extended to ..."
```

---

## Security Architecture

### Authentication Layers

```mermaid
graph LR
    subgraph "Token Generation"
        Startup[Service Startup]
        Gen[Generate Random Token]
        Cache[~/.cache/rhotp/auth_token]
    end

    subgraph "Client Access"
        Chrome[Chrome Extension]
        GNOME[GNOME Extension]
        CLI[CLI Scripts]
    end

    subgraph "API Security"
        Bearer[Bearer Token Verification]
        Routes[Protected Routes]
    end

    Startup --> Gen
    Gen --> Cache
    Cache -.-> Chrome
    Cache -.-> GNOME
    Cache -.-> CLI

    Chrome --> Bearer
    GNOME --> Bearer
    CLI --> Bearer
    Bearer --> Routes

    style Cache fill:#FF9800
    style Bearer fill:#4CAF50
```

### Password Store Encryption

```mermaid
graph TB
    subgraph "Password Store"
        GPG[GPG Encryption]
        Store[~/.password-store/redhat.com/]
        Username[username.gpg]
        Password[associate-password.gpg]
        HOTP[hotp-secret.gpg]
        Counter[hotp-counter.gpg]
    end

    subgraph "Service Access"
        PassSvc[Password Store Service]
        GnuPG[python-gnupg]
    end

    Store --> Username
    Store --> Password
    Store --> HOTP
    Store --> Counter

    PassSvc --> GnuPG
    GnuPG --> GPG
    GPG -.Decrypt.-> Username
    GPG -.Decrypt.-> Password
    GPG -.Decrypt.-> HOTP
    GPG -.Update.-> Counter

    style GPG fill:#F44336
    style GnuPG fill:#2196F3
```

---

## Deployment Architecture

### Development Mode

```mermaid
graph LR
    subgraph "Development"
        Dev[Developer Machine]
        Uvicorn[uvicorn --reload<br/>Port 8009]
        Chrome[Chrome Extension<br/>Dev Mode]
        GNOME[GNOME Extension<br/>Symlink]
    end

    Dev --> Uvicorn
    Dev --> Chrome
    Dev --> GNOME

    Uvicorn -.Auto-reload.-> Uvicorn
    Chrome -.Hot reload.-> Chrome
```

### Production Mode

```mermaid
graph TB
    subgraph "System Services"
        Systemd[systemd User Service<br/>rhotp.service]
        FastAPI[FastAPI :8009<br/>Auto-start on login]
    end

    subgraph "Installed Components"
        Chrome[Chrome Extension<br/>Installed from CRX]
        GNOME[GNOME Extension<br/>Installed to extensions/]
        Scripts[Scripts in ~/bin/<br/>or /usr/local/bin/]
    end

    subgraph "Background Services"
        NM[NetworkManager]
        Pass[GPG Agent]
    end

    Systemd --> FastAPI
    FastAPI --> NM
    FastAPI --> Pass

    Chrome --> FastAPI
    GNOME --> FastAPI
    Scripts --> FastAPI

    style Systemd fill:#4CAF50
    style FastAPI fill:#2196F3
```

---

## Technology Stack

### Backend

| Component | Technology | Version |
|-----------|-----------|---------|
| Framework | FastAPI | Latest |
| Server | Uvicorn | Latest |
| Language | Python 3 | 3.8+ |
| Async | asyncio | Built-in |

### Frontend

| Component | Technology | Version |
|-----------|-----------|---------|
| Chrome Extension | Manifest V3 | Latest |
| GNOME Extension | GJS (JavaScript) | GNOME 3.36-49+ |
| CLI Tools | Bash, Python 3 | Latest |

### Services

| Service | Purpose | Protocol |
|---------|---------|----------|
| NetworkManager | VPN connections | D-Bus/nmcli |
| Password Store | Credential storage | GPG encryption |
| Bonfire | Ephemeral namespaces | CLI subprocess |
| OpenShift | Kubernetes access | oc/kubectl |

### Security

| Component | Technology | Purpose |
|-----------|-----------|---------|
| Authentication | Bearer Tokens | API security |
| Encryption | GPG | Password storage |
| Native Messaging | Chrome Protocol | Token bridge |
| HOTP | RFC 4226 | OTP generation |

---

## File Structure

```
rh-otp-auto-connect/
├── src/
│   ├── main.py                      # FastAPI application
│   ├── api/
│   │   ├── routes/
│   │   │   ├── vpn.py              # VPN endpoints (17 routes)
│   │   │   ├── ephemeral.py        # Ephemeral namespace endpoints
│   │   │   └── legacy.py           # Backward compatibility
│   │   ├── models/                  # Pydantic models
│   │   └── dependencies/
│   │       ├── auth.py             # Bearer token verification
│   │       └── common.py           # Shared utilities
│   ├── services/
│   │   ├── vpn.py                  # VPN business logic
│   │   ├── ephemeral.py            # Bonfire integration
│   │   └── password_store.py       # GPG credential access
│   ├── vpn-profiles/
│   │   ├── profiles.yaml           # 21 VPN endpoints config
│   │   ├── templates/              # Jinja2 templates
│   │   └── certs/                  # Red Hat CA bundle
│   ├── vpn-connect                 # VPN connection script
│   ├── vpn-connect-shuttle         # Alternative VPN (SSH tunnel)
│   ├── vpn-profile-manager         # VPN CLI management tool
│   ├── rhtoken                     # OpenShift token automation
│   ├── rh-otp/                     # Chrome extension
│   │   ├── manifest.json           # Manifest V3
│   │   ├── background.js           # Service worker
│   │   ├── contentscript.js        # Auto-login
│   │   ├── popup.html/js           # Extension UI
│   │   └── native_host.py          # Native messaging
│   └── rh-otp-gnome/               # GNOME Shell extension
│       ├── extension.js            # Main logic
│       ├── prefs.js                # Settings UI
│       └── schemas/                # GSettings schema
├── docs/                            # Documentation
│   ├── ARCHITECTURE.md             # This file
│   ├── API.md                      # API reference
│   ├── USER_GUIDE.md               # User documentation
│   ├── DEVELOPER_GUIDE.md          # Developer docs
│   └── drawings/                   # Diagrams
├── plans/                           # Design documents
├── tests/                           # Test suite
├── Makefile                         # Build automation
└── pyproject.toml                  # Python config
```

---

## API Endpoints Summary

### VPN Management (17 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/vpn/profiles` | List all 21 VPN profiles |
| GET | `/vpn/profiles/{id}` | Get specific profile |
| GET | `/vpn/default` | Get default VPN UUID |
| POST | `/vpn/default` | Set default VPN |
| POST | `/vpn/connect/default` | Connect to default VPN |
| POST | `/vpn/connect/{id}` | Connect to specific profile |
| POST | `/vpn/disconnect` | Disconnect active VPN |
| GET | `/vpn/status` | Get connection status |

### Ephemeral Namespaces (4 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/ephemeral/namespace/details` | Get namespace info |
| GET | `/ephemeral/namespace/status` | Check namespace exists |
| POST | `/ephemeral/namespace/extend` | Extend reservation |
| POST | `/ephemeral/namespace/clear-cache` | Refresh data |

### Legacy/Credentials (2 endpoints)

| Method | Endpoint | Purpose |
|--------|----------|---------|
| GET | `/get_creds` | Get username + password + OTP |
| GET | `/get_associate_email` | Get user email |

---

## Integration Points

### External Services

```mermaid
graph LR
    subgraph "RH OTP System"
        API[FastAPI Service]
    end

    subgraph "Red Hat Infrastructure"
        SSO1[auth.redhat.com]
        SSO2[sso.redhat.com]
        VPN[21 Global VPN Endpoints]
        OS[OpenShift Clusters]
    end

    subgraph "Local Services"
        NM[NetworkManager]
        Pass[Password Store]
        GPG[GPG Agent]
    end

    API --> SSO1
    API --> SSO2
    API --> VPN
    API --> OS
    API --> NM
    API --> Pass
    Pass --> GPG

    style API fill:#4CAF50
```

---

## Performance Characteristics

### Response Times

| Operation | Typical Time | Notes |
|-----------|-------------|-------|
| Get credentials | ~100ms | Includes HOTP generation |
| List VPN profiles | ~50ms | Cached YAML parsing |
| VPN connect | ~3-5s | NetworkManager negotiation |
| Namespace extend | ~2-3s | Bonfire CLI execution |
| Token generation (rhtoken) | ~15-30s | Browser automation |

### Caching Strategy

```mermaid
graph TB
    subgraph "VPN Profile Cache"
        File[profiles.yaml]
        Mtime[File mtime check]
        Cache[In-memory cache]
        Load[Parse YAML]
    end

    Request[API Request] --> Mtime
    Mtime -->|Unchanged| Cache
    Mtime -->|Changed| Load
    Load --> File
    Load --> Cache
    Cache --> Response[API Response]

    style Cache fill:#4CAF50
```

---

## Future Architecture

### Planned Enhancements

```mermaid
graph TB
    subgraph "Current"
        Current[FastAPI Service<br/>VPN + Ephemeral]
    end

    subgraph "Phase 1: Namespace Lifecycle"
        Reserve[namespace/reserve]
        Release[namespace/release]
        Describe[namespace/describe]
    end

    subgraph "Phase 2: Deployment"
        Deploy[deploy/<apps>]
        Status[deploy/status]
        Wait[deploy/wait]
    end

    subgraph "Phase 3: Monitoring"
        Resources[resources/*]
        Health[health]
        Pods[pods/*]
    end

    Current --> Reserve
    Current --> Release
    Current --> Describe

    Reserve --> Deploy
    Release --> Deploy
    Describe --> Deploy

    Deploy --> Status
    Status --> Resources
    Wait --> Health
```

See `plans/bonfire_feature_proposal.md` for detailed roadmap.

---

## Related Documentation

- **[API Reference](API.md)** - Detailed endpoint documentation
- **[User Guide](USER_GUIDE.md)** - End-user documentation
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Development setup and guidelines
- **[Diagrams](drawings/)** - Additional workflow diagrams
- **[Plans](../plans/)** - Feature proposals and design documents
