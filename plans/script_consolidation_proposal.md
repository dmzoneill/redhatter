# Script Consolidation into FastAPI Proposal

## Executive Summary

**Current State**: 782 lines of standalone scripts executing outside FastAPI
**Consolidation Potential**: ~500 lines could move into FastAPI endpoints
**Recommendation**: **PARTIAL CONSOLIDATION** - Some scripts should stay standalone

---

## Current Standalone Scripts Inventory

### 1. VPN Profile Manager (482 lines) - Python CLI Tool

#### `vpn-profile-manager` (482 lines)
**Purpose**: Comprehensive VPN profile management CLI tool
**Key operations**:
- List all VPN profiles from profiles.yaml
- Generate .nmconnection files from Jinja2 templates
- Install profiles to NetworkManager (requires sudo)
- Connect/disconnect VPN (via nmcli)
- Status checking
- Cleanup utilities (remove all/duplicates)

**Overlap with FastAPI**: ~100 lines (20%)
- `list` → `GET /vpn/profiles` ✅ Already in FastAPI
- `connect <id>` → `POST /vpn/connect/{profile_id}` ✅ Already in FastAPI
- `disconnect` → `POST /vpn/disconnect` ✅ Already in FastAPI
- `status` → `GET /vpn/status` ✅ Already in FastAPI

**Can't consolidate** (~380 lines):
- `generate` - Jinja2 template rendering, file I/O
- `install` - Requires sudo for /etc/NetworkManager/
- `clean` - Destructive operation, requires sudo
- `clean-duplicates` - Maintenance utility, requires sudo

**Dependencies**: `gnupg`, `yaml`, `jinja2`, `nmcli`, `sudo`

**See detailed analysis**: `plans/vpn_profile_manager_consolidation.md`

---

### 2. VPN Connection Scripts (103 lines total)

#### `vpn-connect` (66 lines) - Bash
**Purpose**: Connect to VPN via NetworkManager using FastAPI credentials
**Key operations**:
- Wait for FastAPI service (port 8009)
- Read auth token from `~/.cache/rhotp/auth_token`
- Fetch default VPN UUID from `/vpn/default` endpoint
- Get credentials from `/get_creds` endpoint
- Execute `nmcli con up` with sudo

**Dependencies**: `nc`, `curl`, `nmcli`, `sudo`

#### `vpn-connect-shuttle` (37 lines) - Bash
**Purpose**: Alternative VPN via SSH tunnel + sshuttle (personal infrastructure)
**Key operations**:
- Wait for FastAPI service
- Fetch credentials from `/get_creds`
- SSH to personal VPS (fio.ie)
- Setup sshuttle tunnel via VPS
- **HIGHLY PERSONALIZED** (hardcoded SSH keys, host, port 2222)

**Dependencies**: `ssh`, `scp`, `sshuttle`, custom SSH key

---

### 2. OpenShift Token Tool (243 lines) - Python

#### `rhtoken` (243 lines) - Selenium automation
**Purpose**: Acquire OpenShift OAuth tokens via automated browser login
**Key operations**:
- Auto-install/update ChromeDriver based on Chrome version
- Launch Selenium Chrome browser (headless or GUI)
- Navigate to OpenShift OAuth token pages (6 different environments)
- Auto-fill credentials via `/get_creds` endpoint
- Extract `oc login` command from page
- Execute kubectl/oc login command
- Handle KUBECONFIG environment variable

**Dependencies**: `selenium`, `requests`, Chrome browser, ChromeDriver

**Environments supported**:
- `e` - Ephemeral CRC
- `p`, `s` - Production stages
- `ap`, `cp` - AppSRE environments
- `k` - Stone production

---

### 3. Chrome Extension Bridge (263 lines total)

#### `rh-otp/native_host.py` (68 lines) - Native messaging host
**Purpose**: Secure bridge for Chrome extension to access auth token
**Key operations**:
- Read native messaging protocol (binary stdin/stdout)
- Fetch token from `~/.cache/rhotp/auth_token`
- Respond to Chrome extension requests

**Why it exists**: Chrome extensions can't access filesystem directly

#### `install_native_host.py` (195 lines) - Installer
**Purpose**: Configure native messaging manifest for multiple browsers
**Key operations**:
- Detect Chrome/Chromium/Brave/Edge installations
- Create manifest files in `~/.config/{browser}/NativeMessagingHosts/`
- Configure extension ID
- Uninstall/list capabilities

**Browsers supported**: Chrome, Chromium, Brave, Edge, Chrome Beta

---

### 4. VPN Profile Scanner (173 lines) - Python

#### `vpn-profiles/scan-profiles.py` (173 lines)
**Purpose**: Extract VPN profiles from NetworkManager → YAML config
**Key operations**:
- Scan `/etc/NetworkManager/system-connections/` with sudo
- Parse `.nmconnection` files (INI format)
- Extract 21 Red Hat VPN endpoints
- Generate `profiles.yaml` with all settings
- **ONE-TIME SETUP UTILITY** (not used during normal operations)

**Dependencies**: `sudo`, NetworkManager, `pyyaml`

---

## Consolidation Analysis

### ✅ RECOMMENDED FOR CONSOLIDATION

#### 1. **VPN Connection Logic** → FastAPI Endpoints
**Target**: `vpn-connect` (66 lines)

**Current Flow**:
```bash
vpn-connect → Wait for service → Fetch UUID → Fetch creds → nmcli
```

**Proposed FastAPI Endpoint**:
```python
POST /vpn/connect/default
{
  "use_default": true,
  "headless": false
}

Response:
{
  "success": true,
  "connection_uuid": "abc-123",
  "profile_name": "Ashburn (IAD2)",
  "status": "connected"
}
```

**Implementation**:
```python
# Already exists in api/routes/vpn.py:209-279!
@router.post("/vpn/connect/default")
def connect_vpn_default(headless: bool = False, token: str = Depends(verify_token)):
    """Connect to default VPN profile using nmcli."""
    # Fetch UUID from password store
    # Get credentials
    # Execute nmcli via subprocess
    # Return connection status
```

**Status**: ✅ **ALREADY IMPLEMENTED** (lines 209-279 in vpn.py)

**Good**:
- ✅ Centralized VPN logic in FastAPI
- ✅ Consistent auth via bearer tokens
- ✅ Better error handling and logging
- ✅ Can be called from GNOME extension, Chrome, CLI

**Bad**:
- ⚠️ Requires `sudo` for `nmcli` (authentication complexity)
- ⚠️ Script is simpler for end users (single command)

**Ugly**:
- 💀 Password handling via temp files (`/tmp/vpnpw`)
- 💀 Sudo password caching required

**Recommendation**:
- ✅ **KEEP BOTH** - Endpoint exists, script is convenience wrapper
- Script becomes: `curl -H "Bearer $token" -X POST localhost:8009/vpn/connect/default`

---

#### 2. **OpenShift Token Acquisition** → WebSocket-based Endpoint
**Target**: `rhtoken` (243 lines)

**Current Flow**:
```bash
rhtoken e → Download ChromeDriver → Launch browser → Login → Extract token → oc login
```

**Proposed Consolidation**:
```python
POST /openshift/token
{
  "environment": "e",  # ephemeral
  "headless": true,
  "kubeconfig_path": "/path/to/kubeconfig"
}

WebSocket: ws://localhost:8009/openshift/token/stream
{
  "status": "downloading_driver",
  "progress": 25
}
→
{
  "status": "complete",
  "token": "sha256~...",
  "command": "oc login --token=..."
}
```

**Implementation Points**:
```python
# New file: src/api/routes/openshift.py
# New service: src/services/openshift_auth.py

from selenium import webdriver
from fastapi import WebSocket

@router.post("/openshift/token")
async def get_openshift_token(env: str, headless: bool = True):
    """Acquire OpenShift OAuth token via Selenium."""
    # Use existing rhtoken logic
    # Return token + oc login command

@router.websocket("/openshift/token/stream")
async def token_stream(websocket: WebSocket, env: str):
    """Stream progress updates during token acquisition."""
    # Real-time updates during ChromeDriver download
    # Browser automation progress
```

**Good**:
- ✅ Unified API for all authentication workflows
- ✅ Real-time progress via WebSocket
- ✅ No standalone script dependency
- ✅ GNOME/Chrome extensions can use it

**Bad**:
- ⚠️ Selenium dependency in FastAPI service (heavyweight)
- ⚠️ ChromeDriver auto-download increases service complexity
- ⚠️ Browser automation can fail (fragile)

**Ugly**:
- 💀 Desktop GUI browser launch from background service (X11/Wayland)
- 💀 Xvfb required for headless
- 💀 ChromeDriver versioning hell in production
- 💀 6 hardcoded OAuth URLs may change

**Recommendation**:
- ⚠️ **KEEP STANDALONE** - Too complex, fragile, desktop-dependent
- Alternative: Create simple wrapper endpoint that calls script
```python
@router.post("/openshift/token")
def trigger_rhtoken(env: str):
    """Execute rhtoken script and return result."""
    result = subprocess.run(["./rhtoken", env, "--headless"], capture_output=True)
    return {"output": result.stdout}
```

---

### ❌ NOT RECOMMENDED FOR CONSOLIDATION

#### 3. **Native Messaging Host** → MUST STAY STANDALONE

**Why**: Chrome native messaging protocol **requires** standalone executable
- Chrome security model mandates separate process
- Cannot be HTTP endpoint
- Binary stdin/stdout protocol (not HTTP)
- Must be launched by Chrome, not user

**Recommendation**: ✅ **KEEP AS-IS** - Architectural requirement

---

#### 4. **Native Host Installer** → CLI Tool (Stay Standalone)

**Why**: Installation/configuration utility (not runtime operation)
- Only runs during setup
- Modifies system config files
- No benefit from FastAPI integration
- Users expect `python install_native_host.py`

**Recommendation**: ✅ **KEEP AS-IS** - One-time setup utility

---

#### 5. **VPN Profile Scanner** → CLI Tool (Stay Standalone)

**Why**: One-time setup utility, requires sudo
- Scans `/etc/NetworkManager/` (requires sudo)
- Generates initial `profiles.yaml` config
- Run once during setup, not during operations
- No runtime value from FastAPI endpoint

**Recommendation**: ✅ **KEEP AS-IS** - One-time setup utility

---

#### 6. **vpn-connect-shuttle** → Personal Infrastructure (Stay Standalone)

**Why**: Highly personalized, not generalizable
- Hardcoded personal SSH key (`~/.ssh/dmzoneill-2024`)
- Hardcoded personal VPS (`fio.ie`, port 2222)
- Hardcoded username (`daoneill`)
- sshuttle dependency (not standard VPN)
- Supervisor control on remote host

**Recommendation**: ✅ **KEEP AS-IS** - Personal workflow, not project feature

---

## Summary Table

| Script | LOC | Consolidation | Recommendation | Effort |
|--------|-----|---------------|----------------|--------|
| `vpn-profile-manager` | 482 | ⚠️ 20% overlap | Refactor to API client | 2-3h |
| `vpn-connect` | 66 | ✅ Already done | Keep both (endpoint + script) | 0h (done) |
| `vpn-connect-shuttle` | 37 | ❌ Personal | Keep standalone | N/A |
| `rhtoken` | 243 | ⚠️ Possible | Keep standalone (fragile) | 8-12h |
| `native_host.py` | 68 | ❌ Required | Must stay standalone | N/A |
| `install_native_host.py` | 195 | ❌ Setup tool | Keep standalone | N/A |
| `scan-profiles.py` | 173 | ❌ Setup tool | Keep standalone | N/A |
| **Total** | **1,264** | **~166** | **100 lines via refactor** | **2-3h** |

---

## Detailed Recommendations

### ✅ Option 1: Status Quo (RECOMMENDED)
**Keep all scripts as-is, use existing FastAPI endpoints**

**Rationale**:
- VPN connection endpoints already exist in FastAPI ✅
- Standalone scripts are convenient CLI wrappers
- Native messaging host is architectural requirement
- Setup tools are one-time utilities
- Personal scripts (shuttle) are custom workflows

**Benefits**:
- Zero migration effort
- No breaking changes
- Scripts remain simple for end users
- FastAPI endpoints available for programmatic access

**Users get best of both worlds**:
- CLI: `./vpn-connect` (simple)
- API: `POST /vpn/connect/default` (programmatic)
- GNOME: Click button → calls API
- Chrome: Auto-connect → calls API

---

### ⚠️ Option 2: Consolidate rhtoken (NOT RECOMMENDED)
**Move Selenium automation into FastAPI service**

**Effort**: 8-12 hours
**Risk**: High (Selenium, ChromeDriver, desktop GUI)
**Value**: Low (script works fine)

**Why not**:
1. **Selenium in background service** = Desktop GUI dependency
2. **ChromeDriver auto-install** = Version management hell
3. **Browser automation** = Fragile, breaks on website changes
4. **X11/Wayland display** = Service can't run truly headless
5. **Only 1 user** = Not worth engineering effort

**If you must**: Create wrapper endpoint that calls script
```python
@router.post("/openshift/token")
def get_openshift_token(env: str, headless: bool = True):
    """Wrapper for rhtoken script."""
    cmd = ["./rhtoken", env]
    if headless:
        cmd.append("--headless")
    result = subprocess.run(cmd, capture_output=True, text=True)
    return {"output": result.stdout, "success": result.returncode == 0}
```

**Effort**: 30 minutes (wrapper endpoint)
**Value**: API access to rhtoken without full consolidation

---

### 🎯 Option 3: Hybrid Approach (BEST BALANCE)

**Consolidate**: None (everything is fine as-is)

**Enhance**: Add convenience wrapper endpoints

```python
# New file: src/api/routes/utilities.py

@router.post("/utilities/rhtoken")
def execute_rhtoken(env: str, headless: bool = True):
    """Execute rhtoken script via API."""
    # Wrapper for existing script

@router.post("/utilities/vpn-connect")
def execute_vpn_connect(uuid: Optional[str] = None):
    """Execute vpn-connect script via API."""
    # Wrapper for existing script (though endpoint already exists)
```

**Benefits**:
- ✅ Zero refactoring risk
- ✅ Scripts remain independent (can be used directly)
- ✅ API available for integrations
- ✅ Minimal code changes
- ✅ Backward compatible

**Effort**: 1-2 hours

---

## The Good, Bad, and Ugly of Consolidation

### 😊 The Good

**Unified API Surface**:
- All operations accessible via REST endpoints
- Consistent authentication (bearer tokens)
- Better logging and error handling
- Easier integration with GNOME/Chrome extensions

**Centralized Logic**:
- Single source of truth
- Easier to maintain
- Better testing capabilities
- Improved observability

### 😐 The Bad

**Added Complexity**:
- FastAPI service becomes heavier
- More dependencies (Selenium, ChromeDriver)
- Longer startup time
- More potential failure points

**Deployment Challenges**:
- Desktop GUI dependencies (Selenium)
- Sudo requirements (nmcli)
- Binary dependencies (ChromeDriver)
- Platform-specific code (X11/Wayland)

### 💀 The Ugly

**Security Concerns**:
- Sudo access from web service
- Password temp files
- Browser automation security risks
- ChromeDriver auto-download risks

**Desktop GUI from Service**:
- Selenium requires display (X11/Wayland)
- Can't run truly headless
- Xvfb workaround is hacky
- Chrome profile conflicts

**Maintenance Burden**:
- ChromeDriver version management
- OAuth URL changes (6 environments)
- NetworkManager API changes
- Browser automation fragility

---

## Final Recommendation

### ✅ **DO NOTHING** (Status Quo)

**Rationale**:
1. **VPN endpoints already exist** in FastAPI (495 lines in vpn.py)
2. **Scripts are convenience wrappers** for CLI users
3. **Native messaging is architectural requirement**
4. **Setup tools are one-time utilities**
5. **Selenium consolidation is high-risk, low-value**

**The current architecture is actually optimal**:
```
┌─────────────────────────────────────────────────┐
│ FastAPI Service (Port 8009)                     │
│  ├─ /vpn/connect/default    ← GNOME/Chrome call │
│  ├─ /get_creds              ← All clients call  │
│  └─ /ephemeral/*            ← All clients call  │
└─────────────────────────────────────────────────┘
           ↑                           ↑
           │                           │
    ┌──────┴───────┐           ┌──────┴──────────┐
    │ vpn-connect  │           │ Chrome Extension│
    │ (CLI wrapper)│           │ (calls API)     │
    └──────────────┘           └─────────────────┘
           ↑
           │
    ┌──────┴───────┐
    │ GNOME Ext    │
    │ (calls both) │
    └──────────────┘
```

**Everyone is happy**:
- CLI users: `./vpn-connect` (simple)
- API users: `POST /vpn/connect/default`
- GNOME: Calls API directly
- Chrome: Calls API directly

---

## If You REALLY Want Consolidation...

### Minimal-Risk Enhancement (1-2 hours)

Add wrapper endpoints for CLI tools:

```python
# src/api/routes/utilities.py (NEW)

@router.post("/utilities/rhtoken", tags=["utilities"])
def execute_rhtoken(
    env: str,
    headless: bool = True,
    token: str = Depends(verify_token)
):
    """Execute rhtoken script and return OpenShift token."""
    script_path = find_script_path("rhtoken")
    cmd = [str(script_path), env]
    if headless:
        cmd.append("--headless")

    result = subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        timeout=120
    )

    if result.returncode != 0:
        raise HTTPException(
            status_code=500,
            detail=f"rhtoken failed: {result.stderr}"
        )

    return {
        "success": True,
        "output": result.stdout,
        "environment": env
    }
```

**Benefits**:
- API access to rhtoken without refactoring
- Scripts remain independent
- Zero risk
- Minimal effort

**Usage**:
```bash
# Via API
curl -H "Authorization: Bearer $token" \
  -X POST "http://localhost:8009/utilities/rhtoken?env=e&headless=true"

# Via script (still works)
./rhtoken e --headless
```

---

---

## VPN Profile Manager - Special Case

The `vpn-profile-manager` script (482 lines) deserves special attention:

**Current overlap**: ~100 lines (20%) duplicates FastAPI functionality
- `list` command = `GET /vpn/profiles`
- `connect` command = `POST /vpn/connect/{id}`
- `disconnect` command = `POST /vpn/disconnect`
- `status` command = `GET /vpn/status`

**Recommendation**: **Refactor to hybrid CLI/API client**
- Runtime commands → Call FastAPI endpoints (eliminate duplication)
- Setup commands → Keep standalone (require sudo, file I/O)

**See detailed analysis**: `plans/vpn_profile_manager_consolidation.md`

**Effort**: 2-3 hours
**Value**: Architectural consistency (single source of truth)
**Savings**: ~100 lines of duplicate logic

---

## Conclusion

**Answer to "How much can we consolidate?"**:

Technically: **~400 lines** (rhtoken + vpn-profile-manager runtime commands)
Practically: **~100 lines recommended** (vpn-profile-manager refactor only)

**The architecture you have is actually very good**:
- FastAPI provides API endpoints ✅
- Scripts provide CLI convenience ✅
- No duplication (scripts call API) ✅
- Separation of concerns ✅

**Don't fix what isn't broken.**

The only script that *could* be consolidated (rhtoken) is the one that *shouldn't* be - it's fragile, desktop-dependent, and works fine standalone.

### 🎯 Recommended Action: **NONE**

Your consolidation work is complete. The codebase is clean, well-organized, and follows best practices. Focus on new features (bonfire lifecycle management) instead of unnecessary refactoring.
