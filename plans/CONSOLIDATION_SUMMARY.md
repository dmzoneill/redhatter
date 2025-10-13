# Script Consolidation Summary

## Quick Answer

**Total standalone scripts**: 1,264 lines
**Already consolidated**: 495 lines (VPN endpoints in FastAPI)
**Can consolidate**: ~100 lines (vpn-profile-manager refactor)
**Should stay standalone**: ~669 lines (setup tools, native messaging, personal scripts)

---

## Executive Summary

Your codebase has **excellent separation of concerns**:
- ✅ FastAPI handles all runtime VPN operations
- ✅ CLI scripts are either setup utilities or convenience wrappers
- ⚠️ One script (`vpn-profile-manager`) has 20% overlap with FastAPI

**Recommended action**: Refactor `vpn-profile-manager` runtime commands to call FastAPI endpoints

---

## Scripts Analyzed

| Script | Lines | Purpose | Status | Recommendation |
|--------|-------|---------|--------|----------------|
| **vpn-profile-manager** | 482 | VPN management CLI | ⚠️ 20% overlap | Refactor to API client |
| vpn-connect | 66 | VPN connection | ✅ Endpoints exist | Keep both |
| vpn-connect-shuttle | 37 | Personal SSH tunnel | Personal | Keep standalone |
| rhtoken | 243 | OpenShift token | Selenium/GUI | Keep standalone |
| native_host.py | 68 | Chrome bridge | Required | Must stay standalone |
| install_native_host.py | 195 | Setup utility | One-time | Keep standalone |
| scan-profiles.py | 173 | VPN scanner | One-time | Keep standalone |
| **Total** | **1,264** | - | - | **~100 lines to refactor** |

---

## Detailed Analysis

### ✅ vpn-profile-manager (CONSOLIDATION CANDIDATE)

**Overlap with FastAPI** (100 lines):
- `list` → `GET /vpn/profiles` ✅
- `connect <id>` → `POST /vpn/connect/{profile_id}` ✅
- `disconnect` → `POST /vpn/disconnect` ✅
- `status` → `GET /vpn/status` ✅

**Can't consolidate** (380 lines):
- `generate` - Jinja2 template rendering
- `install` - Requires sudo for /etc/NetworkManager/
- `clean` - Destructive sudo operations
- `clean-duplicates` - Maintenance utility

**Recommendation**: Refactor runtime commands to call FastAPI, keep setup commands standalone

**See**: `plans/vpn_profile_manager_consolidation.md`

---

### ✅ VPN Connection Scripts (ALREADY OPTIMAL)

**vpn-connect** (66 lines):
- FastAPI equivalent: `POST /vpn/connect/default` ✅
- Script is convenience wrapper
- Status: **Keep both** - Script calls API

**vpn-connect-shuttle** (37 lines):
- Personal infrastructure (hardcoded SSH keys, VPS)
- Status: **Keep standalone**

---

### ❌ Can't Consolidate (Architectural Reasons)

**native_host.py** (68 lines):
- Chrome native messaging protocol requirement
- Must be standalone executable
- Status: **Architecture requirement**

**rhtoken** (243 lines):
- Selenium + ChromeDriver + desktop GUI
- Too fragile/complex for FastAPI service
- Status: **Keep standalone** (could add wrapper endpoint)

---

### ❌ Setup Utilities (One-time Use)

**install_native_host.py** (195 lines):
- Installation/configuration utility
- Status: **Keep standalone**

**scan-profiles.py** (173 lines):
- One-time VPN profile scanner
- Status: **Keep standalone**

---

## Recommendations by Priority

### 🎯 Priority 1: Refactor vpn-profile-manager (RECOMMENDED)

**Effort**: 2-3 hours
**Savings**: ~100 lines of duplicate logic
**Value**: Architectural consistency

**Action**:
1. Refactor runtime commands (list/connect/disconnect/status) to call FastAPI
2. Keep setup commands (generate/install/clean) standalone
3. Result: Single source of truth for VPN operations

**Before**:
```python
def list_profiles(args):
    config = load_profiles()
    profiles = config['profiles']
    for profile in profiles:
        print(profile['name'])
```

**After**:
```python
def list_profiles(args):
    response = requests.get(f"{API_BASE}/vpn/profiles", headers=HEADERS)
    profiles = response.json()
    for profile in profiles:
        print(profile['name'])
```

---

### ⚠️ Priority 2: Add rhtoken wrapper endpoint (OPTIONAL)

**Effort**: 30 minutes
**Value**: API access without full consolidation

```python
@router.post("/utilities/rhtoken")
def execute_rhtoken(env: str, headless: bool = True):
    """Wrapper for rhtoken script."""
    result = subprocess.run(["./rhtoken", env], capture_output=True)
    return {"output": result.stdout}
```

**Trade-offs**:
- Pro: API access to rhtoken
- Con: Still depends on standalone script
- Con: Selenium still fragile

---

### ❌ Priority 3: Full rhtoken consolidation (NOT RECOMMENDED)

**Effort**: 8-12 hours
**Risk**: High (Selenium, ChromeDriver, GUI)
**Value**: Low (script works fine)

**Why not**:
- Desktop GUI dependency
- ChromeDriver version management
- Browser automation fragility
- Over-engineering for single user

---

## Implementation Plan

### Phase 1: vpn-profile-manager Refactor (2-3 hours)

1. **Update dependencies** (10 min):
   ```python
   # Add to vpn-profile-manager
   import requests

   API_BASE = "http://localhost:8009"

   def get_auth_token():
       return Path.home() / ".cache/rhotp/auth_token").read_text().strip()
   ```

2. **Refactor runtime commands** (90 min):
   - `list_profiles()` → Call `GET /vpn/profiles`
   - `connect_vpn()` → Call `POST /vpn/connect/{id}`
   - `disconnect_vpn()` → Call `POST /vpn/disconnect`
   - `vpn_status()` → Call `GET /vpn/status`

3. **Keep setup commands unchanged** (0 min):
   - `generate_profiles()` - As-is (Jinja2, file I/O)
   - `install_profiles()` - As-is (sudo operations)
   - `clean_profiles()` - As-is (destructive, sudo)
   - `clean_duplicates()` - As-is (maintenance)

4. **Test and verify** (30 min):
   ```bash
   # Test runtime commands
   ./vpn-profile-manager list
   ./vpn-profile-manager connect IAD2
   ./vpn-profile-manager status
   ./vpn-profile-manager disconnect

   # Test setup commands
   ./vpn-profile-manager generate
   sudo ./vpn-profile-manager install
   ```

5. **Update documentation** (20 min):
   - Update CLAUDE.md with new architecture
   - Note that runtime commands require FastAPI service

---

### Phase 2: Optional Enhancements (30 min)

Add rhtoken wrapper endpoint:

```python
# src/api/routes/utilities.py (NEW)

from fastapi import APIRouter, Depends
from api.dependencies.auth import verify_token

router = APIRouter(prefix="/utilities", tags=["utilities"])

@router.post("/rhtoken")
def execute_rhtoken(env: str, headless: bool = True, token: str = Depends(verify_token)):
    """Execute rhtoken script and return OpenShift token."""
    script_path = find_script_path("rhtoken")
    cmd = [str(script_path), env]
    if headless:
        cmd.append("--headless")

    result = subprocess.run(cmd, capture_output=True, text=True, timeout=120)

    if result.returncode != 0:
        raise HTTPException(status_code=500, detail=result.stderr)

    return {"success": True, "output": result.stdout, "environment": env}
```

---

## Expected Results

### After vpn-profile-manager Refactor

**Before**:
- Total scripts: 1,264 lines
- Duplicate logic: ~100 lines
- Architecture: Mixed (some scripts call API, some don't)

**After**:
- Total scripts: ~1,164 lines (100 lines removed)
- Duplicate logic: 0 lines
- Architecture: Clean (all runtime ops via API, setup tools standalone)

**Benefits**:
- ✅ Single source of truth (FastAPI)
- ✅ Consistent authentication
- ✅ Better error handling
- ✅ Easier integration (GNOME, Chrome, etc.)

**Trade-offs**:
- ⚠️ CLI tools require FastAPI service running
- ⚠️ Network dependency for VPN operations
- ⚠️ Slightly slower than direct operations

---

## Cost-Benefit Analysis

| Action | Effort | Savings | Architectural Value | Risk | Recommendation |
|--------|--------|---------|---------------------|------|----------------|
| vpn-profile-manager refactor | 2-3h | 100 LOC | High | Low | ✅ DO IT |
| rhtoken wrapper | 30m | 0 LOC | Medium | Low | ⚠️ Optional |
| rhtoken full consolidation | 8-12h | 243 LOC | Low | High | ❌ Skip |
| Status quo | 0h | 0 LOC | Current | None | ✅ Also fine |

---

## Final Recommendation

### 🎯 Recommended: Refactor vpn-profile-manager

**Why**:
1. Eliminates ~100 lines of duplicate logic
2. Establishes FastAPI as single source of truth
3. Low risk (2-3 hours, backward compatible)
4. High architectural value

**Why not**:
1. Adds network dependency to CLI tool
2. Requires FastAPI service running
3. Minimal LOC savings for effort

**Decision criteria**:
- **Do it** if you value architectural consistency and single source of truth
- **Skip it** if current hybrid approach works fine and LOC savings aren't worth 2-3 hours

### Alternative: Keep Status Quo

The current architecture is actually quite good:
- FastAPI has comprehensive VPN endpoints
- Scripts are either setup utilities or convenience wrappers
- Clear separation of concerns
- Everything works

**Both options are valid** - it's a trade-off between architectural purity vs. pragmatism.

---

## Related Documents

- **Detailed vpn-profile-manager analysis**: `plans/vpn_profile_manager_consolidation.md`
- **Full script inventory**: `plans/script_consolidation_proposal.md`
- **Bonfire features**: `plans/bonfire_feature_proposal.md`
