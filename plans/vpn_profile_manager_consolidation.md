# VPN Profile Manager Consolidation Analysis

## Overview

**Script**: `vpn-profile-manager` (482 lines)
**Current Status**: Standalone Python CLI tool
**FastAPI Overlap**: ~70% of functionality already exists in FastAPI

---

## Command-by-Command Overlap Analysis

### ✅ Already in FastAPI

| Command | Lines | FastAPI Endpoint | Status |
|---------|-------|------------------|--------|
| `list` | 15 | `GET /vpn/profiles` | ✅ Fully implemented (vpn.py:35-44) |
| `connect <id>` | 40 | `POST /vpn/connect/{profile_id}` | ✅ Fully implemented (vpn.py:341-419) |
| `disconnect` | 25 | `POST /vpn/disconnect` | ✅ Fully implemented (vpn.py:422-463) |
| `status` | 20 | `GET /vpn/status` | ✅ Fully implemented (vpn.py:466-495) |

**Total**: ~100 lines already in FastAPI

---

### ⚠️ Partially in FastAPI

| Command | Lines | FastAPI Partial | Gap |
|---------|-------|-----------------|-----|
| `generate [id]` | 55 | None | Template rendering missing |
| `install [id]` | 48 | None | Sudo operations missing |

**Gaps**:
- Jinja2 template rendering for `.nmconnection` files
- Sudo file operations (`cp`, `chmod`, `chown`)
- NetworkManager reload

---

### ❌ Not in FastAPI

| Command | Lines | Purpose | Consolidation Viability |
|---------|-------|---------|-------------------------|
| `clean` | 45 | Remove all RH VPN profiles | ⚠️ Dangerous, needs confirmation |
| `clean-duplicates` | 60 | Remove duplicate profiles | ⚠️ Complex logic, rarely used |

**Total**: ~105 lines not in FastAPI (setup/maintenance utilities)

---

## Detailed Analysis

### 1. List Profiles (`list` command)

**vpn-profile-manager** (lines 83-99):
```python
def list_profiles(args):
    config = load_profiles()
    profiles = config['profiles']

    print(f"{'ID':<15} {'Name':<40} {'Remote':<35} {'Proto'}")
    for profile in profiles:
        print(f"{profile['id']:<15} {profile['name']:<40} ...")
```

**FastAPI** (api/routes/vpn.py:35-44):
```python
@router.get("/profiles", response_model=List[VPNProfile])
def list_vpn_profiles():
    config = load_vpn_profiles()
    profiles = config.get('profiles', [])
    return profiles  # Returns JSON
```

**Verdict**: ✅ **100% DUPLICATED** - FastAPI returns JSON, CLI formats for terminal

---

### 2. Connect to Profile (`connect <id>` command)

**vpn-profile-manager** (lines 207-246):
```python
def connect_vpn(args):
    config = load_profiles()
    profiles = [p for p in config['profiles'] if p['id'].upper() == args.id.upper()]
    profile = profiles[0]

    result = subprocess.run(
        ["nmcli", "connection", "up", "uuid", profile['uuid']],
        capture_output=True
    )
```

**FastAPI** (api/routes/vpn.py:341-419):
```python
@router.post("/connect/{profile_id}")
def connect_vpn_profile(profile_id: str):
    target_profile = find_profile_by_id(profiles, profile_id)
    profile_uuid = target_profile.get('uuid')

    # Calls vpn-connect script with --uuid parameter
    result = subprocess.run([script_path, "--uuid", profile_uuid], ...)
```

**Difference**:
- vpn-profile-manager calls `nmcli` directly
- FastAPI calls `vpn-connect` script (which calls `nmcli`)

**Verdict**: ✅ **100% DUPLICATED** - Different implementation, same result

---

### 3. Disconnect VPN (`disconnect` command)

**vpn-profile-manager** (lines 249-273):
```python
def disconnect_vpn(args):
    result = subprocess.run(
        ["nmcli", "connection", "show", "--active"],
        capture_output=True
    )

    # Parse output for VPN connections
    for line in result.stdout.splitlines():
        if 'vpn' in line.lower() and 'redhat.com' in line.lower():
            conn_name = # parse line
            subprocess.run(["nmcli", "connection", "down", "id", conn_name])
```

**FastAPI** (api/routes/vpn.py:422-463):
```python
@router.post("/disconnect")
def disconnect_vpn():
    status = get_vpn_connection_status()  # Uses nmcli internally

    if status.get("connected"):
        conn_name = status.get("profile_name")
        subprocess.run(["nmcli", "connection", "down", "id", conn_name])
```

**Verdict**: ✅ **100% DUPLICATED** - Same logic via different service layer

---

### 4. VPN Status (`status` command)

**vpn-profile-manager** (lines 276-294):
```python
def vpn_status(args):
    result = subprocess.run(
        ["nmcli", "connection", "show", "--active"],
        capture_output=True
    )

    for line in result.stdout.splitlines():
        if 'vpn' in line.lower():
            print(line)
```

**FastAPI** (api/routes/vpn.py:466-495):
```python
@router.get("/status", response_model=VPNStatus)
def get_vpn_status():
    status = get_vpn_connection_status()  # Calls nmcli internally

    return VPNStatus(
        connected=status.get("connected"),
        profile_name=status.get("profile_name"),
        ...
    )
```

**Verdict**: ✅ **100% DUPLICATED** - FastAPI has richer response model

---

### 5. Generate Profiles (`generate [id]` command)

**vpn-profile-manager** (lines 101-156):
```python
def generate_profiles(args):
    config = load_profiles()
    username = get_from_store("username")

    # Jinja2 template rendering
    env = Environment(loader=FileSystemLoader(TEMPLATE_DIR))
    template = env.get_template('redhat-vpn.j2')

    for profile in profiles:
        context = defaults.copy()
        context.update(profile)
        context['username'] = username

        content = template.render(**context)
        output_path = GENERATED_DIR / f"{context['id']}_{context['uuid']}.nmconnection"
        output_path.write_text(content)
```

**FastAPI**: ❌ **NOT IMPLEMENTED**

**Why not in FastAPI**:
- Jinja2 template rendering
- Filesystem write operations
- Generated files are `.gitignored` (local artifacts)
- One-time setup operation

**Consolidation Value**: ⚠️ **LOW**
- Used during initial setup
- Not a runtime operation
- No API benefit

---

### 6. Install Profiles (`install [id]` command)

**vpn-profile-manager** (lines 158-204):
```python
def install_profiles(args):
    generate_profiles(args)  # First generate

    for gen_file in GENERATED_DIR.glob("*.nmconnection"):
        dest_file = NM_CONNECTIONS_DIR / gen_file.name

        # Requires sudo
        subprocess.run(["sudo", "cp", str(gen_file), str(dest_file)])
        subprocess.run(["sudo", "chmod", "600", str(dest_file)])
        subprocess.run(["sudo", "chown", "root:root", str(dest_file)])

    subprocess.run(["sudo", "nmcli", "connection", "reload"])
```

**FastAPI**: ❌ **NOT IMPLEMENTED**

**Why not in FastAPI**:
- **Requires sudo** (security concern for web service)
- Modifies system files in `/etc/NetworkManager/`
- One-time setup operation
- Needs interactive sudo password entry

**Consolidation Value**: ❌ **DANGEROUS**
- Sudo from web service is security risk
- Better as CLI tool with explicit user action

---

### 7. Clean Profiles (`clean` command)

**vpn-profile-manager** (lines 297-341):
```python
def clean_profiles(args):
    # Find all Red Hat VPN profiles
    for conn_file in NM_CONNECTIONS_DIR.glob("*.nmconnection"):
        content = subprocess.run(["sudo", "cat", str(conn_file)]).stdout
        if 'redhat.com' in content:
            rh_profiles.append(conn_file)

    # Confirmation prompt
    if not args.yes:
        response = input(f"Remove all {len(rh_profiles)} profiles? [y/N]: ")

    # Remove with sudo
    for profile in rh_profiles:
        subprocess.run(["sudo", "rm", str(profile)])

    subprocess.run(["sudo", "nmcli", "connection", "reload"])
```

**FastAPI**: ❌ **NOT IMPLEMENTED**

**Why not in FastAPI**:
- **Destructive operation** - needs user confirmation
- Requires sudo
- Interactive prompts not suitable for API
- Maintenance utility, not runtime operation

**Consolidation Value**: ❌ **NOT RECOMMENDED**
- Too dangerous for API endpoint
- Needs explicit user action

---

### 8. Clean Duplicates (`clean-duplicates` command)

**vpn-profile-manager** (lines 344-403):
```python
def clean_duplicates(args):
    config = load_profiles()

    # Group profiles by ID
    profiles_by_id = {}
    for profile in config['profiles']:
        profile_id = profile['id']
        if profile_id not in profiles_by_id:
            profiles_by_id[profile_id] = []
        profiles_by_id[profile_id].append(profile)

    # Find duplicates
    duplicates = {k: v[1:] for k, v in profiles_by_id.items() if len(v) > 1}

    # Interactive confirmation
    response = input("Remove duplicates? [y/N]: ")

    # Remove with sudo
    for dup in duplicates:
        subprocess.run(["sudo", "rm", str(conn_file)])
```

**FastAPI**: ❌ **NOT IMPLEMENTED**

**Why not in FastAPI**:
- Complex duplicate detection logic
- Interactive confirmation needed
- Sudo operations
- Rarely used (one-time cleanup)

**Consolidation Value**: ❌ **NOT RECOMMENDED**
- Maintenance utility
- Not a runtime operation

---

## Duplicate Code Analysis

### Shared Functions

Both vpn-profile-manager and FastAPI have:

1. **Password Store Access**
   - **vpn-profile-manager** (lines 38-67): `get_from_store(item)`
   - **FastAPI**: `services/password_store.py` (255 lines)
   - **Duplication**: ✅ YES (63 lines duplicated)

2. **Profile Loading**
   - **vpn-profile-manager** (lines 70-80): `load_profiles()`
   - **FastAPI**: `services/vpn.py:19-59` with caching
   - **Duplication**: ✅ YES (basic version duplicated)

3. **Profile Finding**
   - **vpn-profile-manager**: Inline in each command
   - **FastAPI**: `services/vpn.py` (helper functions)
   - **Duplication**: ⚠️ PARTIAL (logic duplicated, implementation differs)

---

## Consolidation Proposal

### ✅ Option 1: Convert CLI to API Client (RECOMMENDED)

**Refactor vpn-profile-manager to call FastAPI endpoints**:

```python
#!/usr/bin/env python3
"""VPN Profile Manager - FastAPI Client Wrapper"""
import requests
import sys

API_BASE = "http://localhost:8009"
TOKEN = open("~/.cache/rhotp/auth_token").read().strip()
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

def list_profiles(args):
    """List all VPN profiles via API."""
    response = requests.get(f"{API_BASE}/vpn/profiles", headers=HEADERS)
    profiles = response.json()

    print(f"{'ID':<15} {'Name':<40} {'Remote':<35}")
    for profile in profiles:
        print(f"{profile['id']:<15} {profile['name']:<40} {profile['remote']:<35}")

def connect_vpn(args):
    """Connect to VPN via API."""
    response = requests.post(
        f"{API_BASE}/vpn/connect/{args.id}",
        headers=HEADERS
    )
    result = response.json()
    print(result['message'])

def disconnect_vpn(args):
    """Disconnect VPN via API."""
    response = requests.post(f"{API_BASE}/vpn/disconnect", headers=HEADERS)
    result = response.json()
    print(result['message'])

def status_vpn(args):
    """Get VPN status via API."""
    response = requests.get(f"{API_BASE}/vpn/status", headers=HEADERS)
    status = response.json()

    if status['connected']:
        print(f"Connected: {status['profile_name']}")
    else:
        print("Not connected")

# Keep setup commands (generate, install, clean) as-is
# They require sudo and local file operations
```

**Result**:
- **Before**: 482 lines (100 lines overlap with FastAPI)
- **After**: ~250 lines (API client + setup utilities)
- **Savings**: ~230 lines of duplicate logic

**Benefits**:
- ✅ Single source of truth (FastAPI)
- ✅ CLI tool becomes thin wrapper
- ✅ Setup commands (generate/install/clean) stay standalone
- ✅ No breaking changes for users
- ✅ FastAPI endpoints can be used by other clients

---

### ⚠️ Option 2: Add Missing Endpoints to FastAPI

**Add `generate` and `install` endpoints**:

```python
# New endpoints in api/routes/vpn.py

@router.post("/profiles/generate")
def generate_vpn_profiles(profile_id: Optional[str] = None):
    """Generate .nmconnection files from profiles.yaml."""
    # Jinja2 template rendering
    # File I/O to GENERATED_DIR
    # Return list of generated files

@router.post("/profiles/install")
def install_vpn_profiles(profile_id: Optional[str] = None):
    """Install generated profiles to NetworkManager."""
    # PROBLEM: Requires sudo
    # Solution: ???
```

**Problem**: Sudo Operations
- FastAPI runs as user, NetworkManager requires root
- Options:
  1. **Passwordless sudo** for `nmcli` (security risk)
  2. **Separate privileged service** (over-engineering)
  3. **Keep as CLI** (best option)

**Verdict**: ❌ **NOT RECOMMENDED**
- Sudo operations don't belong in web service
- Over-engineering for little benefit

---

### ❌ Option 3: Remove vpn-profile-manager Entirely

**Replace with curl commands**:

```bash
# Instead of: vpn-profile-manager list
curl -H "Authorization: Bearer $TOKEN" http://localhost:8009/vpn/profiles

# Instead of: vpn-profile-manager connect IAD2
curl -X POST -H "Authorization: Bearer $TOKEN" http://localhost:8009/vpn/connect/iad2

# Setup commands: ???
```

**Problem**:
- Setup commands (generate/install/clean) have no API equivalent
- No sudo support in FastAPI
- CLI tool is more user-friendly than curl

**Verdict**: ❌ **NOT RECOMMENDED**
- Users need setup utilities
- curl is not user-friendly

---

## The Good, Bad, and Ugly

### 😊 The Good (Option 1: API Client Wrapper)

**Eliminates Duplication**:
- ✅ ~100 lines of duplicate logic removed
- ✅ Single source of truth for VPN operations
- ✅ FastAPI becomes authoritative API

**Maintains User Experience**:
- ✅ CLI tool still works (`vpn-profile-manager list`)
- ✅ Setup commands preserved (generate, install, clean)
- ✅ No breaking changes

**Better Architecture**:
- ✅ Clear separation: API (runtime) vs CLI (setup)
- ✅ Other clients can use FastAPI endpoints
- ✅ Consistent auth via bearer tokens

---

### 😐 The Bad

**Network Dependency**:
- ⚠️ CLI tool now requires FastAPI service running
- ⚠️ Fails if service is down
- ⚠️ Slower than direct operations

**Mixed Responsibilities**:
- ⚠️ CLI tool becomes hybrid (API client + sudo utilities)
- ⚠️ Some commands call API, some run locally
- ⚠️ Confusing mental model

**Added Complexity**:
- ⚠️ HTTP error handling
- ⚠️ Token management
- ⚠️ Connection failures

---

### 💀 The Ugly

**Sudo Operations in API**:
- 💀 Can't consolidate `install`/`clean` commands
- 💀 FastAPI can't modify `/etc/NetworkManager/`
- 💀 Hybrid solution is awkward

**Error Propagation**:
- 💀 API errors become CLI errors
- 💀 Stack trace confusion (API → CLI)
- 💀 Harder debugging

**Offline Usage**:
- 💀 CLI tool won't work offline
- 💀 Service dependency fragility
- 💀 Docker/container complexity

---

## Summary Table

| Command | LOC | In FastAPI? | Consolidation | Keep in CLI? | Reason |
|---------|-----|-------------|---------------|--------------|--------|
| `list` | 15 | ✅ Yes | ✅ Use API | ⚠️ Optional | Better as API client |
| `connect` | 40 | ✅ Yes | ✅ Use API | ⚠️ Optional | Already duplicated |
| `disconnect` | 25 | ✅ Yes | ✅ Use API | ⚠️ Optional | Already duplicated |
| `status` | 20 | ✅ Yes | ✅ Use API | ⚠️ Optional | Already duplicated |
| `generate` | 55 | ❌ No | ❌ Keep CLI | ✅ Yes | Jinja2, file I/O |
| `install` | 48 | ❌ No | ❌ Keep CLI | ✅ Yes | Requires sudo |
| `clean` | 45 | ❌ No | ❌ Keep CLI | ✅ Yes | Destructive, sudo |
| `clean-duplicates` | 60 | ❌ No | ❌ Keep CLI | ✅ Yes | Maintenance, sudo |
| Helper functions | 174 | ⚠️ Partial | ⚠️ Partial | ✅ Yes | Some overlap |
| **Total** | **482** | **100** | **~100 lines** | **~380 lines** | - |

---

## Final Recommendation

### 🎯 Hybrid Approach (Best Balance)

**Phase 1**: Refactor runtime commands to use FastAPI
- `list` → `GET /vpn/profiles`
- `connect` → `POST /vpn/connect/{id}`
- `disconnect` → `POST /vpn/disconnect`
- `status` → `GET /vpn/status`

**Phase 2**: Keep setup commands standalone
- `generate` - Jinja2 template rendering
- `install` - Sudo operations
- `clean` - Destructive maintenance
- `clean-duplicates` - Maintenance utility

**Result**:
```
vpn-profile-manager (refactored)
├─ Runtime commands (API client wrapper)    ~80 lines
└─ Setup commands (standalone logic)       ~380 lines
                                   Total:  ~460 lines
```

**Savings**: ~22 lines (minimal, but better architecture)

**Why minimal savings?**
- Setup commands (60% of code) can't be consolidated
- Already uses shared logic (password store, profile loading)
- Main benefit is **architectural improvement**, not LOC reduction

---

## Implementation Example

### Before (vpn-profile-manager)
```python
def list_profiles(args):
    config = load_profiles()
    profiles = config['profiles']
    print(f"{'ID':<15} {'Name':<40} ...")
    for profile in profiles:
        print(f"{profile['id']:<15} {profile['name']:<40} ...")
```

### After (vpn-profile-manager refactored)
```python
def list_profiles(args):
    """List profiles via FastAPI."""
    import requests

    response = requests.get(
        f"{API_BASE}/vpn/profiles",
        headers={"Authorization": f"Bearer {get_auth_token()}"}
    )
    response.raise_for_status()

    profiles = response.json()
    print(f"{'ID':<15} {'Name':<40} ...")
    for profile in profiles:
        print(f"{profile['id']:<15} {profile['name']:<40} ...")
```

**Effort**: 2-3 hours
**Value**: Architectural consistency, not line count

---

## Conclusion

**Answer to "What about vpn-profile-manager?"**:

**Consolidation Potential**: ~100 lines (20% of script)
**Recommended Action**: **Hybrid approach**

**Why hybrid?**
1. ✅ Runtime commands (list/connect/disconnect/status) → Use FastAPI endpoints
2. ✅ Setup commands (generate/install/clean) → Keep standalone (require sudo)
3. ✅ Maintains user experience (CLI still works)
4. ✅ Improves architecture (single source of truth)

**Effort vs. Value**:
- **Effort**: 2-3 hours (moderate)
- **Value**: High architectural benefit, low LOC savings
- **Risk**: Low (backward compatible)

**Do it if**: You want architectural consistency and single source of truth
**Skip it if**: Line count reduction is primary goal

The main value is **not** consolidation, but **architectural clarity** - FastAPI becomes the authoritative VPN management API, and CLI tools become lightweight clients.
