# Authentication Flows

## Overview

This document details all authentication and credential management flows in the RH-OTP system.

---

## 1. System Initialization & Token Generation

```mermaid
sequenceDiagram
    participant Systemd as systemd<br/>rhotp.service
    participant App as FastAPI App
    participant Auth as Auth Module
    participant FS as File System
    participant Crypto as secrets module

    Systemd->>App: Start service (uvicorn)
    App->>App: on_event("startup")

    App->>Auth: get_or_create_auth_token()

    Auth->>FS: Check ~/.cache/rhotp/auth_token exists

    alt Token file exists
        FS-->>Auth: File exists
        Auth->>FS: Read token
        FS-->>Auth: Token string
        Auth->>Auth: Validate format (64 chars hex)

        alt Valid token
            Auth-->>App: Existing token
        else Invalid token
            Auth->>Crypto: secrets.token_hex(32)
            Crypto-->>Auth: New random token
            Auth->>FS: Write to ~/.cache/rhotp/auth_token
            Auth->>FS: chmod 600
            Auth-->>App: New token
        end

    else Token file doesn't exist
        FS-->>Auth: Not found

        Auth->>FS: mkdir -p ~/.cache/rhotp
        Auth->>Crypto: secrets.token_hex(32)
        Crypto-->>Auth: Random 64-char hex string
        Auth->>FS: Write to ~/.cache/rhotp/auth_token
        Auth->>FS: chmod 600 (user read/write only)
        Auth-->>App: New token
    end

    App->>App: Log token (first 8 chars)
    App-->>Systemd: Service ready (port 8009)
```

---

## 2. Bearer Token Authentication (API Requests)

```mermaid
sequenceDiagram
    participant Client as Client<br/>(Chrome/GNOME/CLI)
    participant API as FastAPI Endpoint
    participant Auth as verify_token()<br/>Dependency
    participant FS as File System

    Client->>API: Request with header:<br/>Authorization: Bearer TOKEN

    API->>Auth: Dependency injection:<br/>verify_token(auth: str)

    Auth->>Auth: Parse "Bearer TOKEN" format

    alt Invalid format
        Auth-->>API: HTTPException 401<br/>"Invalid authorization header"
        API-->>Client: 401 Unauthorized
    end

    Auth->>Auth: Extract token from header

    Auth->>FS: Read ~/.cache/rhotp/auth_token
    FS-->>Auth: Expected token

    Auth->>Auth: Compare tokens<br/>(secrets.compare_digest)

    alt Tokens match
        Auth-->>API: Token validated
        API->>API: Execute endpoint logic
        API-->>Client: 200 OK + response data
    else Tokens don't match
        Auth-->>API: HTTPException 401<br/>"Invalid authentication token"
        API-->>Client: 401 Unauthorized
    end
```

---

## 3. Chrome Extension Token Access (Native Messaging)

```mermaid
sequenceDiagram
    participant Page as Web Page
    participant CS as Content Script
    participant BG as Background Worker
    participant NH as Native Host<br/>(Python)
    participant FS as File System

    Page->>CS: Page load (auth.redhat.com)
    CS->>BG: Request credentials

    Note over BG,NH: Native Messaging Protocol

    BG->>BG: Create message:<br/>{action: "get_token"}
    BG->>BG: Encode as binary<br/>(length + JSON)

    BG->>NH: chrome.runtime.sendNativeMessage()<br/>"com.redhat.rhotp"

    Note over NH: Chrome launches native host process

    NH->>NH: read_message() from stdin
    NH->>NH: Unpack binary message<br/>(struct.unpack)
    NH->>NH: Parse JSON

    NH->>NH: Check action == "get_token"

    NH->>FS: Read ~/.cache/rhotp/auth_token
    FS-->>NH: Token string

    alt Token exists
        NH->>NH: Create response:<br/>{success: true, token: "..."}
    else Token not found
        NH->>NH: Create response:<br/>{success: false, error: "Token not found"}
    end

    NH->>NH: Encode response as binary
    NH->>BG: Write to stdout (binary)

    BG->>BG: Parse response JSON
    BG-->>CS: {success: true, token: "..."}

    CS->>CS: Store token for API calls
    CS->>Page: Continue with credentials request
```

---

## 4. Password Store Access & HOTP Generation

```mermaid
sequenceDiagram
    participant API as FastAPI Endpoint
    participant PS as Password Store Service
    participant GPG as python-gnupg
    participant Pass as Pass CLI
    participant FS as ~/.password-store

    API->>PS: get_associate_credentials()

    Note over PS: Step 1: Get username

    PS->>PS: get_from_store("username")
    PS->>FS: Check ~/.password-store/redhat.com/username.gpg
    FS-->>PS: File exists

    PS->>GPG: gpg.decrypt_file(username.gpg)
    GPG->>GPG: Decrypt with user's GPG key

    alt GPG decryption succeeds
        GPG-->>PS: Decrypted username
    else GPG decryption fails
        GPG-->>PS: Decryption failed
        PS->>Pass: pass show redhat.com/username
        Pass-->>PS: Username from pass CLI
    end

    Note over PS: Step 2: Get password

    PS->>PS: get_from_store("associate-password")
    PS->>FS: Check ~/.password-store/redhat.com/associate-password.gpg
    FS-->>PS: File exists
    PS->>GPG: gpg.decrypt_file(associate-password.gpg)
    GPG-->>PS: Decrypted password

    Note over PS: Step 3: Generate HOTP token

    PS->>PS: generate_hotp_token()

    PS->>PS: get_from_store("hotp-counter")
    PS->>GPG: Decrypt hotp-counter.gpg
    GPG-->>PS: Counter value (e.g., "42")

    PS->>PS: get_from_store("hotp-secret")
    PS->>GPG: Decrypt hotp-secret.gpg
    GPG-->>PS: HOTP secret (base32)

    PS->>PS: hotp = pyotp.HOTP(secret)
    PS->>PS: token = hotp.at(counter)
    PS->>PS: Generate 6-digit code

    Note over PS: Step 4: Increment counter

    PS->>PS: counter += 1
    PS->>PS: update_store("hotp-counter", new_counter)

    PS->>Pass: pass insert redhat.com/hotp-counter
    Pass->>FS: Create temp file
    Pass->>GPG: Encrypt with user's GPG key
    GPG->>FS: Write hotp-counter.gpg
    FS-->>PS: Counter updated

    Note over PS: Step 5: Return credentials

    PS->>PS: Combine password + token
    PS-->>API: (username, password+OTP)

    API-->>API: Format as "username,passwordOTP"
```

---

## 5. Chrome Extension Auto-Login Flow

```mermaid
sequenceDiagram
    participant Page as auth.redhat.com
    participant CS as Content Script
    participant BG as Background Worker
    participant NH as Native Host
    participant API as FastAPI :8009
    participant PS as Password Store

    Note over Page,CS: Page Detection

    Page->>CS: Page load
    CS->>CS: Detect URL pattern:<br/>auth.redhat.com or<br/>sso.redhat.com

    CS->>CS: Find login form:<br/>getElementById("username")<br/>getElementById("password")

    alt Login form found
        CS->>CS: Check auto-login setting
    else No login form
        CS->>CS: Exit (nothing to do)
    end

    Note over CS,NH: Get Auth Token

    CS->>BG: Request credentials
    BG->>NH: Native message: get_token
    NH-->>BG: {success: true, token: "..."}
    BG->>BG: Store token

    Note over BG,PS: Get Credentials

    BG->>API: GET /get_creds?context=associate<br/>Authorization: Bearer TOKEN

    API->>PS: get_associate_credentials()
    PS->>PS: Generate HOTP token
    PS-->>API: username, password+OTP

    API-->>BG: "username,password123456"

    BG->>BG: Parse response
    BG-->>CS: {username: "...", password: "..."}

    Note over CS,Page: Auto-Fill

    CS->>Page: document.getElementById("username").value = username
    CS->>Page: document.getElementById("password").value = password

    CS->>CS: Check auto-submit setting

    alt Auto-submit enabled
        CS->>Page: document.getElementById("submit").click()
        Page->>Page: Submit form
        Page->>Page: Redirect to SSO
        Page-->>CS: Login success
    else Auto-submit disabled
        CS-->>CS: Wait for user to click submit
    end
```

---

## 6. Credential Context Switching (Associate vs Ephemeral)

```mermaid
graph TB
    subgraph "API Endpoint"
        Endpoint[GET /get_creds?context=X]
    end

    subgraph "Context Router"
        Router{context parameter}
    end

    subgraph "Associate Flow"
        AssocPass[Password Store]
        AssocHOTP[Generate HOTP]
        AssocCreds["username,password+OTP"]
    end

    subgraph "Ephemeral Flow"
        EphUser[Get username from pass]
        EphNS[Get namespace name]
        EphK8s[Get password from K8s secret]
        EphCreds["username,k8s_password"]
    end

    Endpoint --> Router

    Router -->|context=associate| AssocPass
    Router -->|context=ephemeral| EphUser

    AssocPass --> AssocHOTP
    AssocHOTP --> AssocCreds

    EphUser --> EphNS
    EphNS --> EphK8s
    EphK8s --> EphCreds

    AssocCreds --> Response[Return to client]
    EphCreds --> Response

    style Router fill:#FF9800
    style AssocCreds fill:#4CAF50
    style EphCreds fill:#2196F3
```

---

## 7. GNOME Extension Authentication

```mermaid
sequenceDiagram
    actor User
    participant Menu as System Tray Menu
    participant Ext as GNOME Extension
    participant FS as File System
    participant API as FastAPI :8009

    User->>Menu: Click "Get Associate Password"
    Menu->>Ext: Menu item activated

    Note over Ext: Read auth token

    Ext->>FS: GLib.file_get_contents()<br/>~/.cache/rhotp/auth_token
    FS-->>Ext: Token string

    alt Token not found
        Ext->>Ext: log("Token not found")
        Ext->>User: Notification: "Service not running"
    end

    Note over Ext: Call API

    Ext->>Ext: Build request:<br/>url = http://localhost:8009/get_creds<br/>headers = {Authorization: "Bearer " + token}

    Ext->>API: Soup.Session.send_async()<br/>GET /get_creds

    API->>API: Verify bearer token
    API->>API: Get credentials

    API-->>Ext: "username,password123456"

    Note over Ext: Process response

    Ext->>Ext: Parse "username,password"
    Ext->>Ext: Extract password

    Note over Ext: Copy to clipboard

    Ext->>Ext: St.Clipboard.set_text(password)

    Ext->>User: Desktop notification:<br/>"Password copied to clipboard"

    Note over User: User can now paste
```

---

## 8. CLI Script Authentication

```mermaid
sequenceDiagram
    participant CLI as CLI Script<br/>(vpn-connect, etc.)
    participant FS as File System
    participant API as FastAPI :8009

    CLI->>CLI: Start execution

    Note over CLI: Wait for service

    loop Every 2 seconds
        CLI->>CLI: nc -z localhost 8009
        alt Port open
            CLI->>CLI: Break loop
        else Port closed
            CLI->>CLI: echo "Waiting for service..."
            CLI->>CLI: sleep 2
        end
    end

    Note over CLI: Read auth token

    CLI->>FS: Check ~/.cache/rhotp/auth_token exists
    FS-->>CLI: File exists

    alt Token file not found
        CLI->>CLI: echo "Error: Token not found"
        CLI->>CLI: exit 1
    end

    CLI->>FS: token=$(cat "$token_file")
    FS-->>CLI: Token string

    CLI->>CLI: Validate token not empty

    alt Token is empty
        CLI->>CLI: echo "Error: Token is empty"
        CLI->>CLI: exit 1
    end

    Note over CLI: Make authenticated request

    CLI->>API: curl -H "Authorization: Bearer $token"<br/>http://localhost:8009/endpoint

    API->>API: Verify token
    API-->>CLI: Response data

    CLI->>CLI: Process response
    CLI->>CLI: Continue with operation
```

---

## 9. HOTP Token Generation Detail

```mermaid
sequenceDiagram
    participant Client as Client Request
    participant PS as Password Store
    participant HOTP as pyotp.HOTP
    participant Pass as Pass CLI

    Client->>PS: generate_hotp_token()

    Note over PS: Read current counter

    PS->>Pass: pass show redhat.com/hotp-counter
    Pass-->>PS: "42" (string)

    PS->>PS: counter = int("42")

    Note over PS: Read HOTP secret

    PS->>Pass: pass show redhat.com/hotp-secret
    Pass-->>PS: "BASE32ENCODEDSECRET"

    PS->>PS: secret = "BASE32ENCODEDSECRET".strip()

    Note over PS: Generate token

    PS->>HOTP: hotp = pyotp.HOTP(secret)
    HOTP-->>PS: HOTP instance

    PS->>HOTP: token = hotp.at(counter)
    HOTP->>HOTP: HMAC-SHA1(secret, counter)
    HOTP->>HOTP: Truncate to 6 digits
    HOTP-->>PS: "123456"

    Note over PS: Increment counter

    PS->>PS: counter = 43
    PS->>PS: update_store("hotp-counter", "43")

    PS->>Pass: echo "43" | pass insert -e redhat.com/hotp-counter
    Pass->>Pass: GPG encrypt
    Pass->>Pass: Write to .password-store/
    Pass-->>PS: Success

    PS-->>Client: "123456"
```

---

## 10. Multi-Client Authentication Architecture

```mermaid
graph TB
    subgraph "Token Storage"
        Token[~/.cache/rhotp/auth_token<br/>Generated on startup<br/>64-char hex string]
    end

    subgraph "Clients"
        Chrome[Chrome Extension]
        GNOME[GNOME Extension]
        CLI[CLI Scripts]
        VPM[vpn-profile-manager]
    end

    subgraph "Access Methods"
        Native[Native Messaging<br/>Chrome → Python bridge]
        File[Direct File Read<br/>GLib/bash]
    end

    subgraph "FastAPI Service"
        Auth[Bearer Token Verification]
        Endpoints[Protected Endpoints]
    end

    Token -.Read via native messaging.-> Native
    Token -.Direct file read.-> File

    Native --> Chrome
    File --> GNOME
    File --> CLI
    File --> VPM

    Chrome --> Auth
    GNOME --> Auth
    CLI --> Auth
    VPM --> Auth

    Auth --> Endpoints

    style Token fill:#FF9800
    style Auth fill:#4CAF50
    style Endpoints fill:#2196F3
```

---

## Security Characteristics

### Token Security

| Aspect | Implementation | Security Level |
|--------|---------------|----------------|
| **Generation** | `secrets.token_hex(32)` | Cryptographically secure random |
| **Storage** | `~/.cache/rhotp/auth_token` | User-only access (chmod 600) |
| **Transmission** | HTTP headers (localhost) | Local-only, no network exposure |
| **Validation** | `secrets.compare_digest()` | Timing-attack resistant |
| **Rotation** | On service restart | Automatic invalidation |

### Password Store Security

| Aspect | Implementation | Security Level |
|--------|---------------|----------------|
| **Encryption** | GPG with user's key | Military-grade encryption |
| **HOTP Secret** | Stored encrypted | Never transmitted in clear |
| **HOTP Counter** | Auto-increment, encrypted | Single-use tokens |
| **Temp Files** | `chmod 600`, immediate deletion | Minimal exposure window |
| **API Access** | Bearer token required | Authenticated access only |

### Attack Surface

```mermaid
graph LR
    subgraph "Protected"
        Pass[Password Store<br/>GPG Encrypted]
        Token[Auth Token<br/>600 permissions]
        API[FastAPI :8009<br/>localhost only]
    end

    subgraph "Potential Risks"
        Local[Local privilege escalation]
        Memory[Memory dump]
        Temp[Temp file interception]
    end

    Local -.Can access.-> Token
    Local -.Can access.-> API
    Memory -.May expose.-> Pass
    Temp -.Brief window.-> Pass

    style Pass fill:#4CAF50
    style Token fill:#4CAF50
    style API fill:#4CAF50
    style Local fill:#F44336
    style Memory fill:#FF9800
    style Temp fill:#FF9800
```

**Mitigations**:
- ✅ No network exposure (localhost only)
- ✅ User-only file permissions
- ✅ Encrypted credential storage
- ✅ Temporary files immediately deleted
- ✅ Single-use HOTP tokens
- ⚠️ Relies on OS user isolation
- ⚠️ Assumes trusted local environment

---

## Authentication State Machine

```mermaid
stateDiagram-v2
    [*] --> ServiceDown: System boot

    ServiceDown --> Starting: systemctl start rhotp
    Starting --> GeneratingToken: on_event("startup")

    GeneratingToken --> TokenExists: Check token file

    TokenExists --> ValidatingToken: File found
    TokenExists --> CreatingToken: File not found

    ValidatingToken --> TokenReady: Valid
    ValidatingToken --> CreatingToken: Invalid

    CreatingToken --> WritingToken: secrets.token_hex(32)
    WritingToken --> TokenReady: chmod 600, write

    TokenReady --> ServiceReady: Service listening on :8009

    ServiceReady --> AuthRequest: Client request

    AuthRequest --> ValidateBearer: Extract Bearer token
    ValidateBearer --> Authorized: Token matches
    ValidateBearer --> Unauthorized: Token mismatch

    Authorized --> ProcessRequest: Execute endpoint
    ProcessRequest --> ServiceReady: Return response

    Unauthorized --> ServiceReady: Return 401

    ServiceReady --> ServiceDown: Service stop
    ServiceDown --> [*]
```

---

## Related Documentation

- **[Architecture Overview](../ARCHITECTURE.md)** - System architecture
- **[VPN Workflows](VPN_WORKFLOWS.md)** - VPN connection flows
- **[API Reference](../API.md)** - Endpoint documentation
- **[User Guide](../USER_GUIDE.md)** - End-user instructions
