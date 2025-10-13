# Bonfire Feature Enhancement Proposal

## Current State Analysis

### Existing Capabilities ✅
- Namespace listing (`get_namespace_list`)
- Namespace extension (`extend_namespace`)
- Password retrieval (`get_namespace_password`)
- Route discovery (`get_namespace_route`)
- Expiration tracking (`get_namespace_expires`)

### Missing Capabilities ❌

#### 1. **Namespace Lifecycle Management**
- `bonfire namespace reserve` - Reserve new ephemeral namespace
- `bonfire namespace release` - Release namespace when done
- `bonfire namespace describe` - Get detailed namespace info

#### 2. **Application Deployment**
- `bonfire deploy` - Deploy apps to namespace
- `bonfire process` - Process templates without deploying
- Deployment configuration management

#### 3. **Resource Monitoring**
- `bonfire namespace wait-on-resources` - Wait for rollout completion
- ClowdApp status monitoring
- Pod health checking
- Deployment readiness

## Proposed Features

### Feature 1: Full Namespace Lifecycle Management

**New API Endpoints:**
```
POST   /ephemeral/namespace/reserve    # Reserve new namespace
POST   /ephemeral/namespace/release    # Release namespace
GET    /ephemeral/namespace/describe   # Detailed namespace info
```

**Use Cases:**
- Chrome extension: One-click namespace reservation
- GNOME extension: Desktop notification when namespace ready
- CI/CD integration: Automated namespace provisioning
- Cleanup automation: Auto-release after testing

**Example Flow:**
```bash
# Reserve namespace for 24 hours
POST /ephemeral/namespace/reserve
{
  "duration": "24h",
  "pool": "default"
}

# Use namespace for development...

# Release when done
POST /ephemeral/namespace/release
```

### Feature 2: Application Deployment Management

**New API Endpoints:**
```
POST   /ephemeral/deploy               # Deploy apps to namespace
GET    /ephemeral/deploy/status        # Check deployment status
POST   /ephemeral/deploy/wait          # Wait for deployment ready
GET    /ephemeral/apps                 # List available apps
```

**Use Cases:**
- Deploy specific app versions for testing
- CI/CD pipeline integration (Jenkins/Konflux)
- Quick environment setup for debugging
- Multi-app deployment orchestration

**Example Flow:**
```bash
# Deploy apps to namespace
POST /ephemeral/deploy
{
  "apps": ["app1", "app2"],
  "namespace": "ephemeral-abc123",
  "image_tags": {
    "app1": "feature-branch-123"
  }
}

# Wait for deployment ready
POST /ephemeral/deploy/wait
{
  "namespace": "ephemeral-abc123",
  "timeout": "10m"
}

# Check status
GET /ephemeral/deploy/status?namespace=ephemeral-abc123
```

### Feature 3: Enhanced Monitoring Dashboard

**New API Endpoints:**
```
GET    /ephemeral/resources            # List all resources in namespace
GET    /ephemeral/pods                 # Pod status
GET    /ephemeral/clowdapps            # ClowdApp status
GET    /ephemeral/health               # Overall environment health
```

**Use Cases:**
- Real-time deployment monitoring
- Health check dashboard
- Troubleshooting failed deployments
- Resource utilization tracking

## Integration Points

### Chrome Extension
- Add "Reserve Namespace" button to popup
- Show deployment status in real-time
- One-click deploy common app configurations
- Visual health indicators

### GNOME Extension
- Desktop notifications for namespace events
- System tray deployment status
- Quick actions menu (reserve, deploy, release)
- Background monitoring with alerts

### CI/CD Pipelines (Jenkins/Konflux)
- REST API calls from pipeline steps
- Automated environment provisioning
- Test result integration
- Cleanup on pipeline completion

### Local Development
- CLI wrappers for common workflows
- Configuration file support
- Template management
- Environment presets

## Implementation Priority

### Phase 1: Namespace Lifecycle (HIGH PRIORITY)
**Impact**: Eliminates manual bonfire CLI usage
**Effort**: Low (similar to existing extend endpoint)
**Files**:
- `src/services/ephemeral.py` - Add reserve/release/describe functions
- `src/api/routes/ephemeral.py` - Add REST endpoints
- `src/api/models/ephemeral.py` - Add request/response models

### Phase 2: Application Deployment (MEDIUM PRIORITY)
**Impact**: Full environment automation
**Effort**: Medium (requires template processing)
**Files**:
- `src/services/deployment.py` (NEW) - Deployment logic
- `src/api/routes/deployment.py` (NEW) - Deployment endpoints
- `src/api/models/deployment.py` (NEW) - Deployment models

### Phase 3: Monitoring & Health Checks (LOW PRIORITY)
**Impact**: Operational visibility
**Effort**: Medium (requires kubectl/oc integration)
**Files**:
- `src/services/monitoring.py` (NEW) - Resource monitoring
- `src/api/routes/monitoring.py` (NEW) - Monitoring endpoints

## Example Implementation

### Phase 1: Reserve Namespace

**services/ephemeral.py:**
```python
def reserve_namespace(
    duration: str = "24h",
    pool: str = "default",
    timeout: int = 600
) -> Optional[dict]:
    """Reserve a new ephemeral namespace."""
    cmd = f"bonfire namespace reserve --duration {duration} --timeout {timeout}"
    if pool != "default":
        cmd += f" --pool {pool}"

    success, stdout, stderr = run_command(cmd)
    if not success:
        logger.error(f"Failed to reserve namespace: {stderr}")
        return None

    # Parse bonfire output
    namespace_name = stdout.strip()
    return {
        "namespace": namespace_name,
        "duration": duration,
        "pool": pool
    }

def release_namespace(namespace: str) -> bool:
    """Release an ephemeral namespace."""
    cmd = f"bonfire namespace release {namespace}"
    success, _, stderr = run_command(cmd)
    if not success:
        logger.error(f"Failed to release namespace: {stderr}")
    return success

def describe_namespace(namespace: str) -> Optional[dict]:
    """Get detailed namespace information."""
    cmd = f"bonfire namespace describe {namespace}"
    success, stdout, stderr = run_command(cmd)
    if not success:
        logger.error(f"Failed to describe namespace: {stderr}")
        return None

    # Parse JSON output from bonfire
    import json
    return json.loads(stdout)
```

**api/routes/ephemeral.py:**
```python
@router.post("/namespace/reserve")
def reserve_namespace_endpoint(
    duration: str = "24h",
    pool: str = "default",
    token: str = Depends(get_verify_token)
):
    """Reserve a new ephemeral namespace."""
    result = reserve_namespace_service(duration, pool)
    if not result:
        raise HTTPException(status_code=500, detail="Failed to reserve namespace")

    return {
        "success": True,
        "message": f"Reserved namespace {result['namespace']}",
        **result
    }

@router.post("/namespace/release")
def release_namespace_endpoint(
    namespace: str,
    token: str = Depends(get_verify_token)
):
    """Release an ephemeral namespace."""
    success = release_namespace_service(namespace)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to release namespace")

    return {
        "success": True,
        "message": f"Released namespace {namespace}"
    }
```

## Benefits

### Developer Experience
- ✅ No manual bonfire CLI commands
- ✅ One-click environment provisioning
- ✅ Automated cleanup
- ✅ Visual status indicators

### CI/CD Integration
- ✅ Programmatic environment management
- ✅ Pipeline automation
- ✅ Consistent workflows
- ✅ Error handling

### Team Productivity
- ✅ Faster iteration cycles
- ✅ Reduced context switching
- ✅ Self-service environments
- ✅ Resource optimization

## Recommendation

**Start with Phase 1 (Namespace Lifecycle)** as it:
- Provides immediate value
- Low implementation effort
- Builds on existing code patterns
- Enables future phases

Estimated implementation time: **2-3 hours** for Phase 1
