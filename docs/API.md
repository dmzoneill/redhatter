# API Reference

## Base URL

```
http://localhost:8009
```

All API endpoints require authentication via Bearer token unless otherwise specified.

---

## Authentication

### Bearer Token

All requests must include an `Authorization` header with the bearer token:

```bash
Authorization: Bearer <token>
```

**Token location**: `~/.cache/rhotp/auth_token`

**Example**:
```bash
TOKEN=$(cat ~/.cache/rhotp/auth_token)
curl -H "Authorization: Bearer $TOKEN" http://localhost:8009/vpn/profiles
```

---

## API Endpoints

### Health & Status

#### GET `/`

Root endpoint to verify service is running.

**Authentication**: Optional

**Response**:
```json
{
  "status": "ok",
  "message": "RH-OTP Auto-Connect API is running",
  "version": "2.0.0"
}
```

**Example**:
```bash
curl http://localhost:8009/
```

---

#### GET `/ping`

Quick health check endpoint.

**Authentication**: Optional

**Response**:
```json
{
  "status": "ok"
}
```

---

## VPN Management

### List VPN Profiles

#### GET `/vpn/profiles`

List all configured VPN profiles (21 Red Hat global endpoints).

**Authentication**: Required

**Response**: `200 OK`
```json
[
  {
    "id": "IAD2",
    "name": "Ashburn (IAD2)",
    "remote": "ovpn-iad2.redhat.com",
    "uuid": "abc-123-def-456",
    "port": 443,
    "proto_tcp": true,
    "tunnel_mtu": 1360
  },
  {
    "id": "BRQ2",
    "name": "Brno (BRQ2)",
    "remote": "ovpn-brq2.redhat.com",
    "uuid": "xyz-789-uvw-012",
    "port": 443,
    "proto_tcp": true
  }
  // ... 19 more profiles
]
```

**Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/vpn/profiles
```

**Use cases**:
- Populate VPN profile menus in UI
- Discover available endpoints
- Get UUID for connections

---

### Get Specific VPN Profile

#### GET `/vpn/profiles/{profile_id}`

Get details for a specific VPN profile.

**Authentication**: Required

**Path Parameters**:
- `profile_id` (string, required): Profile ID (e.g., "IAD2", "BRQ2")

**Response**: `200 OK`
```json
{
  "id": "IAD2",
  "name": "Ashburn (IAD2)",
  "remote": "ovpn-iad2.redhat.com",
  "uuid": "abc-123-def-456",
  "port": 443,
  "proto_tcp": true,
  "tunnel_mtu": 1360,
  "dns_search": "~.;redhat.com;"
}
```

**Errors**:
- `404 Not Found`: Profile does not exist

**Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/vpn/profiles/IAD2
```

---

### Get Default VPN

#### GET `/vpn/default`

Get the default VPN profile information from password store.

**Authentication**: Required

**Response**: `200 OK`
```json
{
  "uuid": "abc-123-def-456",
  "profile_id": "IAD2",
  "profile_name": "Ashburn (IAD2)",
  "source": "password_store"
}
```

**Notes**:
- If `nm-uuid` not found in password store, automatically initializes to GLOBAL profile
- Source indicates if value was initialized: `"password_store (initialized)"`

**Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/vpn/default
```

---

### Set Default VPN

#### POST `/vpn/default`

Set the default VPN profile by profile ID or UUID.

**Authentication**: Required

**Request Body**:
```json
{
  "profile_id": "BRQ2"  // Optional: Profile ID (preferred)
  // OR
  "uuid": "xyz-789-uvw-012"  // Optional: Direct UUID
}
```

**Note**: Must provide either `profile_id` OR `uuid` (profile_id takes precedence).

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Default VPN set to Brno (BRQ2)",
  "uuid": "xyz-789-uvw-012",
  "profile_name": "Brno (BRQ2)"
}
```

**Errors**:
- `400 Bad Request`: Neither profile_id nor uuid provided
- `404 Not Found`: Profile not found
- `500 Internal Server Error`: Failed to update password store

**Example**:
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"profile_id": "BRQ2"}' \
  http://localhost:8009/vpn/default
```

---

### Connect to Default VPN

#### POST `/vpn/connect/default`

Connect to the default VPN using the `vpn-connect` script.

**Authentication**: Required

**Request Body**: None

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Connected to default VPN",
  "method": "default"
}
```

**Errors**:
- `404 Not Found`: vpn-connect script not found
- `500 Internal Server Error`: Connection failed
- `504 Gateway Timeout`: Connection timeout (60s)

**Example**:
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/vpn/connect/default
```

**Notes**:
- Uses UUID from password store (`nm-uuid`)
- Executes `vpn-connect` script which calls `nmcli`
- Requires sudo permissions for nmcli
- Timeout: 60 seconds

---

### Connect to Specific VPN Profile

#### POST `/vpn/connect/{profile_id}`

Connect to a specific VPN profile by ID.

**Authentication**: Required

**Path Parameters**:
- `profile_id` (string, required): Profile ID (e.g., "IAD2", "BRQ2")

**Request Body**: None

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Connected to Ashburn (IAD2)",
  "profile_id": "IAD2",
  "profile_name": "Ashburn (IAD2)",
  "uuid": "abc-123-def-456"
}
```

**Errors**:
- `404 Not Found`: Profile or vpn-connect script not found
- `400 Bad Request`: Profile doesn't have UUID configured
- `500 Internal Server Error`: Connection failed
- `504 Gateway Timeout`: Connection timeout (60s)

**Example**:
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/vpn/connect/iad2
```

**Notes**:
- Case-insensitive profile ID matching
- Executes `vpn-connect --uuid <UUID>`
- Does NOT update default VPN in password store

---

### Connect via Shuttle Method

#### POST `/vpn/connect/shuttle`

Connect to VPN using the alternative shuttle method (SSH tunnel + sshuttle).

**Authentication**: Required

**Request Body**: None

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Connected to VPN (shuttle)",
  "method": "shuttle"
}
```

**Errors**:
- `404 Not Found`: vpn-connect-shuttle script not found
- `500 Internal Server Error`: Connection failed
- `504 Gateway Timeout`: Connection timeout (60s)

**Example**:
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/vpn/connect/shuttle
```

**Notes**:
- Personal infrastructure (hardcoded SSH keys, VPS)
- Not recommended for general use
- Requires SSH access to personal VPS

---

### Disconnect VPN

#### POST `/vpn/disconnect`

Disconnect active VPN connection.

**Authentication**: Required

**Request Body**: None

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Disconnected from Ashburn (IAD2)",
  "was_connected": true
}
```

**If no active VPN**:
```json
{
  "success": true,
  "message": "No active VPN connection",
  "was_connected": false
}
```

**Errors**:
- `500 Internal Server Error`: Disconnection failed

**Example**:
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/vpn/disconnect
```

---

### Get VPN Status

#### GET `/vpn/status`

Get current VPN connection status.

**Authentication**: Required

**Response**: `200 OK` (Connected)
```json
{
  "connected": true,
  "profile_name": "Ashburn (IAD2)",
  "profile_id": "IAD2",
  "connection_details": {
    "connected": true,
    "profile_name": "Ashburn (IAD2)",
    "connection_uuid": "abc-123-def-456"
  }
}
```

**Response**: `200 OK` (Not Connected)
```json
{
  "connected": false,
  "profile_name": null,
  "profile_id": null,
  "connection_details": {
    "connected": false
  }
}
```

**Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/vpn/status
```

**Use cases**:
- Monitor VPN connection state
- Display status in UI
- Verify connection before operations

---

## Ephemeral Namespace Management

### Get Namespace Details

#### GET `/ephemeral/namespace/details`

Get details about the user's ephemeral namespace.

**Authentication**: Required

**Query Parameters**:
- `headless` (boolean, optional, default: false): Use headless mode for authentication
- `include_password` (boolean, optional, default: false): Include namespace password in response

**Response**: `200 OK`
```json
{
  "name": "ephemeral-abc123",
  "route": "https://my-app.apps.crc-eph.example.com",
  "expires": "2025-01-15T10:30:00Z",
  "password": "k8s_secret_password"  // Only if include_password=true
}
```

**Errors**:
- `404 Not Found`: No visible namespace reservation found
- `500 Internal Server Error`: Failed to retrieve details

**Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8009/ephemeral/namespace/details?include_password=true"
```

---

### Get Namespace Status

#### GET `/ephemeral/namespace/status`

Check if a namespace exists and get its current state.

**Authentication**: Required

**Query Parameters**:
- `headless` (boolean, optional, default: false): Use headless mode

**Response**: `200 OK` (Namespace exists)
```json
{
  "exists": true,
  "name": "ephemeral-abc123",
  "expires": "2025-01-15T10:30:00Z",
  "details": {
    "full_info": ["ephemeral-abc123", "...", "2025-01-15T10:30:00Z"]
  }
}
```

**Response**: `200 OK` (No namespace)
```json
{
  "exists": false,
  "name": null,
  "expires": null,
  "details": null
}
```

**Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/ephemeral/namespace/status
```

---

### Extend Namespace Duration

#### POST `/ephemeral/namespace/extend`

Extend the duration of the user's ephemeral namespace reservation.

**Authentication**: Required

**Query Parameters**:
- `headless` (boolean, optional, default: false): Use headless mode

**Request Body** (optional):
```json
{
  "duration": "72h"  // Optional, default: "72h"
}
```

**Supported durations**: Any bonfire-compatible duration string (e.g., "24h", "48h", "72h", "1w")

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Namespace ephemeral-abc123 extended by 72h",
  "namespace": "ephemeral-abc123",
  "duration": "72h",
  "new_expiration": "2025-01-18T10:30:00Z",
  "details": ["ephemeral-abc123", "...", "2025-01-18T10:30:00Z"]
}
```

**Errors**:
- `404 Not Found`: No visible namespace reservation found
- `500 Internal Server Error`: Failed to extend namespace

**Example**:
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"duration": "48h"}' \
  http://localhost:8009/ephemeral/namespace/extend
```

---

### Clear Namespace Cache

#### POST `/ephemeral/namespace/clear-cache`

Clear cached namespace data and fetch fresh information.

**Authentication**: Required

**Query Parameters**:
- `headless` (boolean, optional, default: false): Use headless mode

**Request Body**: None

**Response**: `200 OK`
```json
{
  "success": true,
  "message": "Cache cleared and namespace info refreshed",
  "namespace_info": ["ephemeral-abc123", "...", "2025-01-15T10:30:00Z"]
}
```

**Errors**:
- `404 Not Found`: No visible namespace reservation found
- `500 Internal Server Error`: Failed to refresh data

**Example**:
```bash
curl -X POST \
  -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/ephemeral/namespace/clear-cache
```

**Use cases**:
- Force refresh after external changes
- Verify latest namespace state
- Debug stale data issues

---

## Legacy/Credential Endpoints

### Get Credentials

#### GET `/get_creds`

Get user credentials with OTP token.

**Authentication**: Required

**Query Parameters**:
- `context` (string, optional, default: "associate"): Credential context
  - `"associate"`: Corporate credentials with HOTP token
  - `"ephemeral"`: Ephemeral namespace credentials
- `headless` (boolean, optional, default: false): Use headless mode (for ephemeral)

**Response**: `200 OK`
```
"username,password123456"
```

**Context: Associate**:
- Returns: `"username,password+OTP"`
- Generates HOTP token using pyotp
- Auto-increments HOTP counter in password store
- Password + 6-digit OTP combined

**Context: Ephemeral**:
- Returns: `"username,k8s_password"`
- Fetches password from Kubernetes secret
- No OTP generation

**Example (Associate)**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8009/get_creds?context=associate&headless=false"
```

**Example (Ephemeral)**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  "http://localhost:8009/get_creds?context=ephemeral&headless=true"
```

**Notes**:
- Plain text response (not JSON)
- Comma-separated format
- OTP is single-use (counter increments)

---

### Get Associate Email

#### GET `/get_associate_email`

Get user's Red Hat email address.

**Authentication**: Required

**Query Parameters**: None

**Response**: `200 OK`
```
"username@redhat.com"
```

**Example**:
```bash
curl -H "Authorization: Bearer $TOKEN" \
  http://localhost:8009/get_associate_email
```

**Notes**:
- Plain text response (not JSON)
- Derives email from username in password store

---

## Error Responses

All endpoints may return the following error responses:

### 401 Unauthorized

Invalid or missing authentication token.

```json
{
  "detail": "Invalid authentication token"
}
```

**Causes**:
- Missing `Authorization` header
- Invalid token format (not "Bearer <token>")
- Token doesn't match server token

**Resolution**:
- Check service is running: `systemctl --user status rhotp`
- Verify token file exists: `ls ~/.cache/rhotp/auth_token`
- Restart service: `systemctl --user restart rhotp`

---

### 404 Not Found

Resource not found.

```json
{
  "detail": "Profile 'INVALID' not found"
}
```

**Causes**:
- Profile ID doesn't exist
- Namespace not found
- Script file not found

**Resolution**:
- List available profiles: `GET /vpn/profiles`
- Check namespace exists: `GET /ephemeral/namespace/status`

---

### 500 Internal Server Error

Server-side error during processing.

```json
{
  "detail": "Failed to connect: Connection timeout"
}
```

**Causes**:
- NetworkManager errors
- Password store errors
- Subprocess failures
- Bonfire CLI errors

**Resolution**:
- Check logs: `journalctl --user -u rhotp -f`
- Verify dependencies (nmcli, pass, bonfire)
- Check password store: `pass show redhat.com/username`

---

### 504 Gateway Timeout

Operation exceeded timeout limit.

```json
{
  "detail": "Connection timeout"
}
```

**Causes**:
- VPN connection taking >60s
- NetworkManager unresponsive

**Resolution**:
- Check NetworkManager: `systemctl status NetworkManager`
- Try manual connection: `nmcli connection up uuid <UUID>`

---

## Rate Limiting

**Current implementation**: No rate limiting

**Future**: May implement per-client rate limiting for security.

---

## CORS

**Current implementation**: Disabled (localhost-only service)

**Allowed origins**:
- Chrome extension (via native messaging, not CORS)
- Localhost clients only

---

## Versioning

**Current version**: 2.0.0 (FastAPI consolidation)

**Version strategy**:
- No API versioning implemented
- Backward compatibility maintained
- Legacy endpoints preserved (`/get_creds`, `/get_associate_email`)

**Future**: May implement `/v2/` prefix for breaking changes.

---

## Response Format

### Success Responses

Most endpoints return JSON with consistent structure:

```json
{
  "success": true,
  "message": "Operation successful",
  "data": { ... }
}
```

**Legacy endpoints** (`/get_creds`, `/get_associate_email`) return plain text for backward compatibility.

---

### Error Responses

FastAPI standard error format:

```json
{
  "detail": "Error message describing the issue"
}
```

**HTTP status codes**:
- `200 OK`: Success
- `400 Bad Request`: Invalid request parameters
- `401 Unauthorized`: Authentication failure
- `404 Not Found`: Resource not found
- `500 Internal Server Error`: Server-side error
- `504 Gateway Timeout`: Operation timeout

---

## OpenAPI Documentation

**Interactive API docs**: http://localhost:8009/docs

**Swagger UI features**:
- Try endpoints directly in browser
- View request/response schemas
- See authentication requirements
- Download OpenAPI spec

**Alternative docs**: http://localhost:8009/redoc

---

## Client Examples

### Python

```python
import requests

TOKEN = open(os.path.expanduser("~/.cache/rhotp/auth_token")).read().strip()
BASE_URL = "http://localhost:8009"
HEADERS = {"Authorization": f"Bearer {TOKEN}"}

# List VPN profiles
response = requests.get(f"{BASE_URL}/vpn/profiles", headers=HEADERS)
profiles = response.json()

# Connect to specific profile
response = requests.post(
    f"{BASE_URL}/vpn/connect/iad2",
    headers=HEADERS
)
result = response.json()
print(result["message"])

# Get VPN status
response = requests.get(f"{BASE_URL}/vpn/status", headers=HEADERS)
status = response.json()
if status["connected"]:
    print(f"Connected to {status['profile_name']}")
```

---

### Bash/cURL

```bash
#!/bin/bash

TOKEN=$(cat ~/.cache/rhotp/auth_token)
BASE_URL="http://localhost:8009"

# List VPN profiles
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/vpn/profiles" | jq .

# Connect to VPN
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/vpn/connect/brq2" | jq .

# Get status
curl -s -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/vpn/status" | jq .

# Disconnect
curl -s -X POST \
  -H "Authorization: Bearer $TOKEN" \
  "$BASE_URL/vpn/disconnect" | jq .
```

---

### JavaScript (Chrome Extension)

```javascript
// Get auth token via native messaging
const token = await getAuthToken();  // Native messaging bridge

// List VPN profiles
const response = await fetch('http://localhost:8009/vpn/profiles', {
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const profiles = await response.json();

// Connect to VPN
const connectResponse = await fetch('http://localhost:8009/vpn/connect/iad2', {
  method: 'POST',
  headers: {
    'Authorization': `Bearer ${token}`
  }
});
const result = await connectResponse.json();
console.log(result.message);
```

---

## Related Documentation

- **[Architecture](ARCHITECTURE.md)** - System architecture
- **[VPN Workflows](drawings/VPN_WORKFLOWS.md)** - VPN flow diagrams
- **[Authentication](drawings/AUTH_FLOWS.md)** - Auth flow diagrams
- **[User Guide](USER_GUIDE.md)** - End-user documentation
- **[Developer Guide](DEVELOPER_GUIDE.md)** - Development setup
