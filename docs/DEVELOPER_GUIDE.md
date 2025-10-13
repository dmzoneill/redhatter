# Developer Guide

## Table of Contents

1. [Development Setup](#development-setup)
2. [Project Structure](#project-structure)
3. [Development Workflow](#development-workflow)
4. [Testing](#testing)
5. [Code Quality](#code-quality)
6. [Contributing](#contributing)
7. [Release Process](#release-process)

---

## Development Setup

### Prerequisites

- **Operating System**: Linux (Fedora/RHEL recommended)
- **Python**: 3.13 or higher
- **Git**: For version control
- **GPG**: Configured with a key
- **Development tools**: make, gcc, python3-devel

### Clone Repository

```bash
cd ~/src
git clone https://github.com/yourusername/rh-otp-auto-connect.git
cd rh-otp-auto-connect/src
```

### Install Development Dependencies

```bash
# Install Pipenv
pip install --user pipenv

# Install all dependencies (including dev dependencies)
pipenv install --dev

# Or using make
make install-deps
```

### Setup Pre-commit Hooks

```bash
# Install pre-commit hooks
pipenv run pre-commit install

# Run hooks manually
pipenv run pre-commit run --all-files
```

### Development Environment

```bash
# Activate Pipenv shell
pipenv shell

# Or run commands with pipenv run
pipenv run uvicorn main:app --reload
```

---

## Project Structure

```
rh-otp-auto-connect/
├── src/                           # Main source directory
│   ├── main.py                    # FastAPI application entry point
│   ├── api/                       # API layer
│   │   ├── routes/               # Route handlers
│   │   │   ├── vpn.py           # VPN endpoints (17 routes)
│   │   │   ├── ephemeral.py     # Ephemeral namespace endpoints
│   │   │   └── legacy.py        # Backward compatibility endpoints
│   │   ├── models/               # Pydantic models
│   │   │   ├── vpn.py           # VPN request/response models
│   │   │   └── ephemeral.py     # Ephemeral models
│   │   └── dependencies/         # Shared dependencies
│   │       ├── auth.py          # Bearer token verification
│   │       └── common.py        # Common utilities
│   ├── services/                 # Business logic layer
│   │   ├── vpn.py               # VPN operations
│   │   ├── ephemeral.py         # Bonfire integration
│   │   └── password_store.py    # GPG/pass integration
│   ├── vpn-profiles/             # VPN configuration
│   │   ├── profiles.yaml        # Profile definitions
│   │   ├── templates/           # Jinja2 templates
│   │   └── certs/               # CA certificates
│   ├── vpn-connect              # VPN connection scripts
│   ├── vpn-connect-shuttle
│   ├── vpn-profile-manager      # VPN command-line tool
│   ├── rhtoken                  # OpenShift token automation
│   ├── rh-otp/                  # Chrome extension
│   └── rh-otp-gnome/            # GNOME Shell extension
├── docs/                         # Documentation
│   ├── ARCHITECTURE.md
│   ├── API.md
│   ├── USER_GUIDE.md
│   ├── DEVELOPER_GUIDE.md       # This file
│   └── drawings/                # Mermaid diagrams
├── plans/                        # Design documents
├── tests/                        # Test suite
├── Makefile                      # Build automation
├── Pipfile                       # Python dependencies
├── Pipfile.lock                 # Locked dependencies
├── pyproject.toml               # Python project config
└── README.md                    # Project overview
```

---

## Development Workflow

### Running in Development Mode

#### FastAPI Service

```bash
# Start with auto-reload (recommended for development)
make dev

# Or manually
pipenv run uvicorn main:app --reload --port 8009

# View logs
tail -f ~/.local/state/rhotp/rhotp.log
```

**Auto-reload features**:
- Watches Python files for changes
- Automatically restarts server
- Preserves authentication token

#### Chrome Extension

```bash
# Load extension in developer mode
# 1. Open chrome://extensions/
# 2. Enable "Developer mode"
# 3. Click "Load unpacked"
# 4. Select src/rh-otp/ directory

# After code changes, click "Reload" on extension card
# Or use make target (requires chrome-cli)
make extension-reload
```

#### GNOME Extension

```bash
# Install extension in development mode (symlink)
make install-gnome

# After code changes
make gnome-reload

# Watch logs in real-time
make gnome-logs

# Or auto-reload on file changes
make gnome-watch
```

---

### Making Changes

#### 1. Create Feature Branch

```bash
git checkout -b feature/my-new-feature
```

#### 2. Make Changes

Follow the project's coding standards (see [Code Quality](#code-quality)).

#### 3. Test Changes

```bash
# Run tests
make test

# Run specific test file
pipenv run pytest tests/test_vpn.py -v

# Run with coverage
pipenv run pytest --cov=services tests/
```

#### 4. Code Quality Checks

```bash
# Run all linters
make lint

# Auto-format code
make format

# Type checking
make type-check
```

#### 5. Commit Changes

```bash
git add .
git commit -m "feat: add new VPN profile management feature"
```

**Commit message format** (Conventional Commits):
- `feat:` New feature
- `fix:` bugfix
- `docs:` Documentation changes
- `refactor:` Code refactoring
- `test:` Adding tests
- `chore:` Build/tooling changes

#### 6. Push and Create PR

```bash
git push origin feature/my-new-feature
```

Then create a Pull Request on GitHub.

---

## Testing

### Running Tests

```bash
# Run all tests
make test

# Run with verbose output
pipenv run pytest -v

# Run specific test file
pipenv run pytest tests/test_main.py

# Run specific test function
pipenv run pytest tests/test_main.py::test_root_endpoint

# Run with coverage report
pipenv run pytest --cov=api --cov=services tests/
```

### Writing Tests

#### Unit Tests

```python
# tests/test_vpn_service.py
import pytest
from services.vpn import load_vpn_profiles, find_profile_by_id

def test_load_vpn_profiles():
    """Test VPN profile loading."""
    config = load_vpn_profiles()

    assert 'profiles' in config
    assert len(config['profiles']) > 0
    assert config['profiles'][0]['id'] == 'IAD2'

def test_find_profile_by_id():
    """Test profile lookup by ID."""
    config = load_vpn_profiles()
    profiles = config['profiles']

    profile = find_profile_by_id(profiles, 'BRQ2')

    assert profile is not None
    assert profile['id'] == 'BRQ2'
    assert profile['name'] == 'Brno (BRQ2)'

def test_find_profile_by_id_case_insensitive():
    """Test case-insensitive profile lookup."""
    config = load_vpn_profiles()
    profiles = config['profiles']

    profile = find_profile_by_id(profiles, 'brq2')  # lowercase

    assert profile is not None
    assert profile['id'] == 'BRQ2'
```

#### Integration Tests

```python
# tests/test_api_vpn.py
import pytest
from fastapi.testclient import TestClient
from main import app

@pytest.fixture
def client():
    """Create test client."""
    return TestClient(app)

@pytest.fixture
def auth_token():
    """Get authentication token."""
    from pathlib import Path
    token_file = Path.home() / ".cache/rhotp/auth_token"
    return token_file.read_text().strip()

def test_list_vpn_profiles(client, auth_token):
    """Test VPN profile listing endpoint."""
    response = client.get(
        "/vpn/profiles",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    profiles = response.json()
    assert isinstance(profiles, list)
    assert len(profiles) > 0
    assert profiles[0]['id'] == 'IAD2'

def test_get_vpn_profile(client, auth_token):
    """Test getting specific VPN profile."""
    response = client.get(
        "/vpn/profiles/BRQ2",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 200
    profile = response.json()
    assert profile['id'] == 'BRQ2'
    assert profile['name'] == 'Brno (BRQ2)'

def test_get_vpn_profile_not_found(client, auth_token):
    """Test 404 for non-existent profile."""
    response = client.get(
        "/vpn/profiles/INVALID",
        headers={"Authorization": f"Bearer {auth_token}"}
    )

    assert response.status_code == 404
    assert 'not found' in response.json()['detail'].lower()

def test_unauthorized_request(client):
    """Test request without authentication."""
    response = client.get("/vpn/profiles")

    assert response.status_code == 401
```

#### Mocking External Dependencies

```python
# tests/test_password_store.py
import pytest
from unittest.mock import Mock, patch
from services.password_store import PasswordStoreService

@pytest.fixture
def mock_gpg():
    """Mock python-gnupg."""
    with patch('gnupg.GPG') as mock:
        yield mock

def test_get_from_store(mock_gpg):
    """Test password store retrieval with mocked GPG."""
    # Setup mock
    mock_gpg_instance = Mock()
    mock_gpg.return_value = mock_gpg_instance

    mock_decrypt_result = Mock()
    mock_decrypt_result.ok = True
    mock_decrypt_result.data = b"test_value"
    mock_gpg_instance.decrypt_file.return_value = mock_decrypt_result

    # Test
    service = PasswordStoreService()
    result = service.get_from_store("username")

    assert result == "test_value"
```

---

## Code Quality

### Code Style

**Python**: Follow PEP 8 with some project-specific conventions:

```python
# Good: Clear, descriptive names
def get_vpn_connection_status():
    """Get current VPN connection status using nmcli."""
    pass

# Bad: Unclear abbreviations
def get_vpn_stat():
    pass

# Good: Type hints
def find_profile_by_id(profiles: list, profile_id: str) -> Optional[dict]:
    pass

# Bad: No type hints
def find_profile_by_id(profiles, profile_id):
    pass

# Good: Docstrings
def connect_vpn(uuid: str) -> bool:
    """
    Connect to VPN using NetworkManager.

    Args:
        uuid: NetworkManager connection UUID

    Returns:
        True if successful, False otherwise

    Raises:
        HTTPException: If connection fails
    """
    pass
```

**JavaScript** (Chrome/GNOME extensions): ES6+ with consistent formatting

### Linting

```bash
# Run all linters
make lint

# Individual linters
pipenv run black --check .         # Code formatting
pipenv run flake8 .                # Style guide enforcement
pipenv run isort --check-only .    # Import sorting
pipenv run mypy src/               # Type checking
```

### Auto-formatting

```bash
# Format all Python code
make format

# This runs:
# - black: Code formatter
# - isort: Import organizer
```

### Type Checking

```bash
# Run mypy
make type-check

# Or directly
pipenv run mypy src/
```

**Type hints are required** for all new code:

```python
from typing import List, Optional, Dict

def load_vpn_profiles(use_cache: bool = True) -> Dict:
    pass

def find_profile_by_id(profiles: List[dict], profile_id: str) -> Optional[dict]:
    pass
```

---

## Contributing

### Getting Started

1. **Fork the repository** on GitHub
2. **Clone your fork**:
   ```bash
   git clone https://github.com/YOUR_USERNAME/rh-otp-auto-connect.git
   ```
3. **Add upstream remote**:
   ```bash
   git remote add upstream https://github.com/ORIGINAL/rh-otp-auto-connect.git
   ```
4. **Create feature branch**:
   ```bash
   git checkout -b feature/my-feature
   ```

### Development Guidelines

#### Adding a New API Endpoint

1. **Define Pydantic models** (if needed):
   ```python
   # src/api/models/vpn.py
   from pydantic import BaseModel

   class VPNConnectRequest(BaseModel):
       profile_id: str
       headless: bool = False
   ```

2. **Add service function**:
   ```python
   # src/services/vpn.py
   def connect_to_profile(profile_id: str) -> bool:
       """Connect to VPN profile."""
       # Implementation
       pass
   ```

3. **Add route handler**:
   ```python
   # src/api/routes/vpn.py
   @router.post("/connect")
   def connect_vpn(
       request: VPNConnectRequest,
       token: str = Depends(verify_token)
   ):
       """Connect to VPN profile."""
       success = vpn_service.connect_to_profile(request.profile_id)
       return {"success": success}
   ```

4. **Write tests**:
   ```python
   # tests/test_vpn_api.py
   def test_connect_vpn_endpoint(client, auth_token):
       response = client.post(
           "/vpn/connect",
           json={"profile_id": "IAD2"},
           headers={"Authorization": f"Bearer {auth_token}"}
       )
       assert response.status_code == 200
   ```

5. **Update documentation**:
   - Add to `docs/API.md`
   - Update sequence diagrams if needed

#### Adding a New VPN Profile

1. **Update profiles.yaml**:
   ```yaml
   # src/vpn-profiles/profiles.yaml
   profiles:
     - id: NEW_SITE
       name: "New Site (NEW)"
       remote: ovpn-newsite.redhat.com
       uuid: "generate-or-provide"
   ```

2. **Generate and install**:
   ```bash
   make vpn-profiles-generate
   make vpn-profiles-install
   ```

3. **Test**:
   ```bash
   ./vpn-profile-manager list  # Should show new profile
   ./vpn-profile-manager connect NEW_SITE
   ```

---

### Pull Request Process

1. **Ensure all tests pass**:
   ```bash
   make test
   make lint
   ```

2. **Update documentation** (if applicable)

3. **Commit with descriptive messages**:
   ```bash
   git commit -m "feat: add support for NEW_SITE VPN endpoint"
   ```

4. **Push to your fork**:
   ```bash
   git push origin feature/my-feature
   ```

5. **Create Pull Request** on GitHub with:
   - Clear description of changes
   - Link to related issues
   - Screenshots (if UI changes)
   - Test results

6. **Address review feedback**

7. **Squash commits if requested**:
   ```bash
   git rebase -i HEAD~3  # Interactive rebase last 3 commits
   ```

---

## Release Process

### Version Numbering

Follow [Semantic Versioning](https://semver.org/):
- **MAJOR**: Incompatible API changes
- **MINOR**: New features (backward compatible)
- **PATCH**: bugfixes (backward compatible)

### Creating a Release

1. **Update version** in `pyproject.toml`:
   ```toml
   [tool.poetry]
   version = "2.1.0"
   ```

2. **Update CHANGELOG.md**:
   ```markdown
   ## [2.1.0] - 2025-01-15

   ### Added
   - New bonfire namespace lifecycle endpoints
   - Support for namespace reservation/release

   ### Changed
   - Improved VPN profile caching performance

   ### Fixed
   - Fixed authentication token refresh issue
   ```

3. **Create git tag**:
   ```bash
   git tag -a v2.1.0 -m "Release version 2.1.0"
   git push origin v2.1.0
   ```

4. **Create GitHub Release**:
   - Go to GitHub → Releases → Draft new release
   - Select tag `v2.1.0`
   - Copy changelog content
   - Publish release

5. **Deploy** (if applicable):
   ```bash
   make deploy
   ```

---

## Debugging

### FastAPI Service

```bash
# Enable debug logging
export LOG_LEVEL=DEBUG
uvicorn main:app --reload --log-level debug

# View logs
journalctl --user -u rhotp -f

# Interactive debugging with pdb
import pdb; pdb.set_trace()
```

### Chrome Extension

```bash
# Open extension background page console
chrome://extensions/ → Extension → "background page" link

# View console logs
console.log("Debug message", variable);

# Inspect native messaging
chrome://extensions/ → Enable "Developer mode" → View service worker
```

### GNOME Extension

```bash
# Watch logs in real-time
journalctl -f | grep gnome-shell

# Enable debug logging in extension
log("Debug message: " + variable);

# Use Looking Glass (Alt+F2 → "lg")
# Access global variables and inspect state
```

---

## Architecture Decisions

### Why FastAPI?

- ✅ Async/await support
- ✅ Automatic OpenAPI documentation
- ✅ Type hints with Pydantic
- ✅ High performance
- ✅ Modern Python web framework

### Why Native Messaging for Chrome Extension?

- ✅ Chrome extension can't access filesystem directly
- ✅ Secure bridge to read auth token
- ✅ Follows Chrome security model
- ✅ Better than chrome.storage (no size limits)

### Why Password Store (pass)?

- ✅ GPG encryption
- ✅ Standard Unix tool
- ✅ Git-friendly
- ✅ No custom encryption code
- ✅ Well-tested and audited

### Why Not Database?

- ✅ Single-user system
- ✅ Minimal state (just auth token)
- ✅ Password store handles persistence
- ✅ Simpler deployment
- ✅ No migration complexity

---

## Performance Optimization

### VPN Profile Caching

```python
# Before: Parse YAML on every request
def load_vpn_profiles():
    with open("profiles.yaml") as f:
        return yaml.safe_load(f)

# After: Cache with mtime-based invalidation
_cache = None
_cache_mtime = None

def load_vpn_profiles():
    global _cache, _cache_mtime
    current_mtime = profiles_file.stat().st_mtime

    if _cache and current_mtime == _cache_mtime:
        return _cache  # ~10x faster

    with open(profiles_file) as f:
        _cache = yaml.safe_load(f)
    _cache_mtime = current_mtime
    return _cache
```

**Result**: ~50ms → ~5ms for repeated calls

---

## Security Considerations

### Authentication

- ✅ **Bearer tokens**: Cryptographically secure random generation
- ✅ **Localhost only**: No network exposure
- ✅ **File permissions**: 600 on token file
- ✅ **No token in logs**: Only first 8 chars logged

### Password Storage

- ✅ **GPG encryption**: Military-grade encryption
- ✅ **No plaintext**: Never stored unencrypted
- ✅ **Temp files**: Immediate deletion after use
- ✅ **HOTP counter**: Auto-increment, encrypted storage

### Code Security

```bash
# Run security audit
pipenv check

# Run bandit (security linter)
pipenv run bandit -r src/

# Check for known vulnerabilities
pipenv run safety check
```

---

## Related Documentation

- **[Architecture](ARCHITECTURE.md)** - System architecture overview
- **[API Reference](API.md)** - Complete API documentation
- **[User Guide](USER_GUIDE.md)** - end user documentation
- **[VPN Workflows](drawings/VPN_WORKFLOWS.md)** - VPN flow diagrams
- **[Authentication](drawings/AUTH_FLOWS.md)** - Authentication diagrams
