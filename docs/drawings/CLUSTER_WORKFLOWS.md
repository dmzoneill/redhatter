# OpenShift Cluster Management Workflows

## Overview

This document details all OpenShift cluster management and token acquisition workflows in the RH-OTP system.

---

## 1. Get OC Login Command

```mermaid
sequenceDiagram
    participant Client as Client<br/>(GNOME/CLI)
    participant API as FastAPI :8009
    participant rhtoken as rhtoken script
    participant Browser as Chrome<br/>(Selenium)
    participant SSO as Red Hat SSO

    Client->>API: GET /token/oc-login?env=e&headless=true<br/>Authorization: Bearer TOKEN

    API->>API: Verify bearer token
    API->>API: Locate rhtoken script

    API->>rhtoken: Execute: rhtoken e --query --headless

    rhtoken->>rhtoken: Load rhtoken.json config
    rhtoken->>rhtoken: Auto-download ChromeDriver if needed

    rhtoken->>Browser: Launch Chrome (headless mode)
    Browser->>SSO: Navigate to OAuth URL

    SSO-->>Browser: Login form
    Browser->>SSO: Auto-fill credentials
    SSO-->>Browser: Request device code
    Browser->>SSO: Display token page

    rhtoken->>rhtoken: Extract token from page
    rhtoken->>rhtoken: Build oc login command

    rhtoken-->>API: stdout: "oc login https://... --token=sha256~..."

    API->>API: Parse output
    API->>API: Extract oc login command

    API-->>Client: {<br/>  "command": "oc login ...",<br/>  "environment": "e",<br/>  "environment_name": "Ephemeral"<br/>}
```

---

## 2. List All Clusters

```mermaid
sequenceDiagram
    participant Client as Client
    participant API as FastAPI :8009
    participant Manager as ClusterConfigManager
    participant FS as File System<br/>(rhtoken.json)

    Client->>API: GET /token/clusters<br/>Authorization: Bearer TOKEN

    API->>Manager: list_clusters()
    Manager->>FS: Read rhtoken.json

    FS-->>Manager: JSON content
    Manager->>Manager: Parse JSON
    Manager->>Manager: Extract "clusters" object

    Manager-->>API: Dict of cluster_id -> cluster_data

    API->>API: Transform to response models

    API-->>Client: [<br/>  {cluster_id: "e", name: "Ephemeral", ...},<br/>  {cluster_id: "p", name: "Production", ...}<br/>]
```

---

## 3. Search Clusters

```mermaid
sequenceDiagram
    participant Client as Client
    participant API as FastAPI :8009
    participant Manager as ClusterConfigManager
    participant FS as rhtoken.json

    Client->>API: GET /token/clusters/search?q=ephemeral

    API->>Manager: search_clusters("ephemeral")
    Manager->>FS: Read rhtoken.json
    FS-->>Manager: All clusters

    Manager->>Manager: query_lower = "ephemeral"

    loop For each cluster
        Manager->>Manager: Build searchable text:<br/>cluster_id + name + description + url
        Manager->>Manager: Convert to lowercase
        Manager->>Manager: Check if query in searchable text

        alt Match found
            Manager->>Manager: Add to results
        end
    end

    Manager-->>API: Matching clusters dict
    API-->>Client: Filtered cluster list
```

---

## 4. Add New Cluster

```mermaid
sequenceDiagram
    participant Client as Client
    participant API as FastAPI :8009
    participant Manager as ClusterConfigManager
    participant FS as rhtoken.json

    Client->>API: POST /token/clusters/dev<br/>{name: "Dev Cluster", url: "https://...", description: "..."}

    API->>Manager: add_cluster(cluster_id="dev", ...)

    Manager->>FS: Read rhtoken.json
    FS-->>Manager: Current config

    Manager->>Manager: Check if cluster_id exists

    alt Cluster already exists
        Manager-->>API: ValueError: "Cluster 'dev' already exists"
        API-->>Client: 400 Bad Request
    end

    Manager->>Manager: Create new cluster object
    Manager->>Manager: Add to clusters dict

    Manager->>FS: Write updated rhtoken.json
    Manager->>FS: Add trailing newline
    FS-->>Manager: Success

    Manager-->>API: New cluster data
    API-->>Client: 201 Created<br/>{cluster_id: "dev", name: "Dev Cluster", ...}
```

---

## 5. Update Cluster

```mermaid
sequenceDiagram
    participant Client as Client
    participant API as FastAPI :8009
    participant Manager as ClusterConfigManager
    participant FS as rhtoken.json

    Client->>API: PUT /token/clusters/dev<br/>{description: "Updated description"}

    API->>Manager: update_cluster(cluster_id="dev", description="...")

    Manager->>FS: Read rhtoken.json
    FS-->>Manager: Current config

    Manager->>Manager: Check if cluster_id exists

    alt Cluster not found
        Manager-->>API: ValueError: "Cluster 'dev' not found"
        API-->>Client: 404 Not Found
    end

    Manager->>Manager: Get existing cluster
    Manager->>Manager: Update only provided fields<br/>(name, url, description)

    Manager->>FS: Write updated rhtoken.json
    FS-->>Manager: Success

    Manager-->>API: Updated cluster data
    API-->>Client: 200 OK<br/>{cluster_id: "dev", ...}
```

---

## 6. Delete Cluster

```mermaid
sequenceDiagram
    participant Client as Client
    participant API as FastAPI :8009
    participant Manager as ClusterConfigManager
    participant FS as rhtoken.json

    Client->>API: DELETE /token/clusters/dev

    API->>Manager: delete_cluster(cluster_id="dev")

    Manager->>FS: Read rhtoken.json
    FS-->>Manager: Current config

    Manager->>Manager: Check if cluster_id exists

    alt Cluster not found
        Manager-->>API: ValueError: "Cluster 'dev' not found"
        API-->>Client: 404 Not Found
    end

    Manager->>Manager: Pop cluster from dict
    Manager->>Manager: Save deleted cluster for response

    Manager->>FS: Write updated rhtoken.json
    FS-->>Manager: Success

    Manager-->>API: Deleted cluster data
    API-->>Client: 200 OK<br/>{cluster_id: "dev", ...}
```

---

## 7. Open Cluster Terminal

```mermaid
sequenceDiagram
    actor User
    participant GNOME as GNOME Extension
    participant API as FastAPI :8009
    participant Script as kubeconfig.sh
    participant Terminal as gnome-terminal
    participant Kube as kube function

    User->>GNOME: Click "Cluster Terminal → Ephemeral"
    GNOME->>API: POST /token/clusters/e/open-terminal

    API->>API: Locate kubeconfig.sh script

    alt Script not found
        API-->>GNOME: 404 Not Found
        GNOME-->>User: Error notification
    end

    API->>Terminal: subprocess.Popen(<br/>  ["gnome-terminal", "--", "bash", "-c",<br/>   "source kubeconfig.sh && kube-clean e && kube e; bash"]<br/>)

    Note over API,Terminal: Process runs in background<br/>(start_new_session=True)

    API-->>GNOME: {success: "true", message: "Terminal opened"}
    GNOME-->>User: Success notification

    Note over Terminal: Terminal window opens

    Terminal->>Script: source kubeconfig.sh
    Script->>Script: Define kube() function
    Script->>Script: Define kube-clean() function

    Terminal->>Kube: kube-clean e
    Kube->>Kube: Remove ~/.kube/config-e

    Terminal->>Kube: kube e
    Kube->>Kube: Set KUBECONFIG=~/.kube/config-e
    Kube->>Kube: Run rhtoken e (interactive)

    Note over Kube: Browser opens for authentication

    Kube->>Kube: Execute oc login command
    Kube-->>Terminal: Logged in to cluster

    Terminal->>Terminal: Drop to bash shell<br/>(KUBECONFIG still set)

    User->>Terminal: Run oc/kubectl commands
```

---

## 8. Open Cluster Web Console

```mermaid
sequenceDiagram
    actor User
    participant GNOME as GNOME Extension
    participant API as FastAPI :8009
    participant Manager as ClusterConfigManager
    participant Browser as xdg-open

    User->>GNOME: Click "Cluster Web Console → Ephemeral"
    GNOME->>API: POST /token/clusters/e/open-web

    API->>Manager: get_cluster("e")
    Manager-->>API: {<br/>  url: "https://oauth-openshift.apps.../<br/>        oauth/token/request"<br/>}

    alt Cluster not found
        API-->>GNOME: 404 Not Found
        GNOME-->>User: Error notification
    end

    API->>API: transform_oauth_to_console_url(oauth_url)

    Note over API: Transform URL:<br/>FROM: https://oauth-openshift.apps.../oauth/token/request<br/>TO: https://console-openshift-console.apps.../

    API->>Browser: subprocess.Popen(<br/>  ["xdg-open", console_url]<br/>)

    Note over Browser: Process runs in background

    Browser->>Browser: Open default browser
    Browser->>Browser: Navigate to console URL

    API-->>GNOME: {<br/>  success: "true",<br/>  message: "Web console opened",<br/>  url: "https://console-..."<br/>}

    GNOME-->>User: Success notification

    Note over Browser: User logs in via browser
```

---

## 9. GNOME Extension Integration Flow

```mermaid
sequenceDiagram
    actor User
    participant Menu as System Tray Menu
    participant Ext as GNOME Extension
    participant API as FastAPI :8009

    User->>Menu: Click Red Hat icon
    Menu->>Ext: Show menu

    Note over Ext: Load clusters on startup

    Ext->>API: GET /token/clusters
    API-->>Ext: List of all clusters

    Ext->>Ext: Build "Cluster Terminal" submenu
    Ext->>Ext: Build "Cluster Web Console" submenu

    Ext->>Menu: Display menu with submenus

    User->>Menu: Select "Cluster Terminal → Ephemeral"
    Menu->>Ext: Menu item activated (cluster_id="e")

    Ext->>API: POST /token/clusters/e/open-terminal

    Ext->>User: Notification: "Opening terminal..."

    API-->>Ext: {success: "true"}

    Ext->>User: Notification: "Terminal opened for Ephemeral"

    Note over User: Terminal window appears<br/>with oc login in progress

    alt User selects Web Console instead
        User->>Menu: Select "Cluster Web Console → Production"
        Menu->>Ext: Menu item activated (cluster_id="p")

        Ext->>API: POST /token/clusters/p/open-web
        Ext->>User: Notification: "Opening web console..."

        API-->>Ext: {success: "true", url: "https://..."}

        Ext->>User: Notification: "Web console opened"

        Note over User: Browser opens to cluster console
    end
```

---

## 10. rhtoken Script Workflow (Full Authentication)

```mermaid
sequenceDiagram
    participant CLI as CLI/API
    participant rhtoken as rhtoken script
    participant Config as rhtoken.json
    participant WebDriver as ChromeDriver
    participant Browser as Chrome/Chromium
    participant SSO as Red Hat SSO
    participant API as rhotp API :8009

    CLI->>rhtoken: Execute: rhtoken e --headless

    rhtoken->>Config: Load cluster configuration
    Config-->>rhtoken: {<br/>  "e": {<br/>    "name": "Ephemeral",<br/>    "url": "https://oauth-..."<br/>  }<br/>}

    rhtoken->>rhtoken: Check ChromeDriver version

    alt ChromeDriver missing or outdated
        rhtoken->>rhtoken: Download correct ChromeDriver<br/>for installed Chrome version
        rhtoken->>rhtoken: Extract to ~/.local/bin/
    end

    rhtoken->>WebDriver: Start ChromeDriver
    rhtoken->>Browser: Launch Chrome in headless mode

    Browser->>SSO: Navigate to OAuth URL
    SSO-->>Browser: Display login form

    rhtoken->>API: GET /get_creds?context=associate
    API-->>rhtoken: "username,password+OTP"

    rhtoken->>rhtoken: Parse credentials

    rhtoken->>Browser: Fill username field
    rhtoken->>Browser: Fill password field
    rhtoken->>Browser: Click submit

    Browser->>SSO: Submit credentials
    SSO->>SSO: Validate credentials
    SSO-->>Browser: Redirect to token page

    rhtoken->>Browser: Wait for token element
    Browser-->>rhtoken: Token page loaded

    rhtoken->>rhtoken: Extract token from page:<br/>"sha256~..."

    rhtoken->>rhtoken: Build oc login command:<br/>"oc login https://... --token=sha256~..."

    alt --query flag used
        rhtoken-->>CLI: Print command (stdout)
        CLI->>CLI: Capture command for later use
    else No --query flag
        rhtoken->>rhtoken: Execute oc login command
        rhtoken->>rhtoken: oc login runs in shell
        rhtoken-->>CLI: Authentication complete
    end

    rhtoken->>Browser: Close browser
    rhtoken->>WebDriver: Stop ChromeDriver
```

---

## 11. Cluster Configuration File Structure

```mermaid
graph TB
    subgraph "rhtoken.json"
        Root[Root Object]
        Clusters[clusters: {}]

        Cluster_E[e: Ephemeral]
        Cluster_P[p: Production]
        Cluster_S[s: Stage]
        Cluster_AP[ap: App SRE Prod]
        Cluster_CP[cp: App SRE Stage]
        Cluster_K[k: Stone Prod]
    end

    subgraph "Cluster Object Structure"
        Name[name: string]
        Desc[description: string]
        URL[url: string<br/>OAuth token request URL]
    end

    Root --> Clusters
    Clusters --> Cluster_E
    Clusters --> Cluster_P
    Clusters --> Cluster_S
    Clusters --> Cluster_AP
    Clusters --> Cluster_CP
    Clusters --> Cluster_K

    Cluster_E --> Name
    Cluster_E --> Desc
    Cluster_E --> URL

    style Root fill:#4CAF50
    style Clusters fill:#2196F3
    style Name fill:#FF9800
    style Desc fill:#FF9800
    style URL fill:#FF9800
```

**Example rhtoken.json**:
```json
{
  "clusters": {
    "e": {
      "name": "Ephemeral",
      "description": "Ephemeral OpenShift environments",
      "url": "https://oauth-openshift.apps.crcs02ue1.urby.p1.openshiftapps.com/oauth/token/request"
    },
    "p": {
      "name": "Production",
      "description": "Production OpenShift cluster",
      "url": "https://oauth-openshift.apps.prod.example.com/oauth/token/request"
    }
  }
}
```

---

## 12. Kubeconfig Management Flow

```mermaid
sequenceDiagram
    participant User
    participant Shell as Bash Shell
    participant KubeScript as kubeconfig.sh
    participant Kube as kube function
    participant rhtoken as rhtoken script
    participant FS as ~/.kube/

    User->>Shell: source kubeconfig.sh
    Shell->>KubeScript: Execute script

    KubeScript->>Shell: Define kube() function
    KubeScript->>Shell: Define kube-clean() function
    KubeScript-->>Shell: Functions loaded

    User->>Shell: kube e
    Shell->>Kube: Execute kube("e")

    Kube->>Kube: Set CONFIG_FILE=~/.kube/config-e
    Kube->>Kube: export KUBECONFIG=$CONFIG_FILE

    Kube->>FS: Check if config-e exists

    alt Config exists
        Kube->>Kube: Config already present
        Kube-->>Shell: KUBECONFIG set
    else Config missing
        Kube->>rhtoken: Execute: rhtoken e

        Note over rhtoken: Full authentication flow<br/>(see diagram 10)

        rhtoken->>rhtoken: Get token from SSO
        rhtoken->>rhtoken: Run oc login command

        Note over rhtoken: oc login creates config file

        rhtoken->>FS: Write ~/.kube/config-e
        rhtoken-->>Kube: Authentication complete

        Kube-->>Shell: KUBECONFIG=~/.kube/config-e
    end

    Shell->>Shell: KUBECONFIG persists in shell

    User->>Shell: oc get pods
    Shell->>Shell: Use KUBECONFIG=~/.kube/config-e
    Shell-->>User: Pod list from cluster "e"

    Note over User,Shell: User can run oc/kubectl commands<br/>without re-authenticating
```

---

## Key Workflow Characteristics

### Performance

| Workflow | Typical Duration | Blocking Operations |
|----------|------------------|---------------------|
| List clusters | 10ms | File read (rhtoken.json) |
| Search clusters | 15ms | File read + filtering |
| Get oc login command | 15-30 seconds | Browser automation, SSO login |
| Open terminal | 500ms | gnome-terminal spawn |
| Open web console | 200ms | xdg-open spawn |
| CRUD operations | 20-50ms | File read/write (rhtoken.json) |

### Security

| Workflow | Security Measures |
|----------|------------------|
| All API calls | Bearer token authentication |
| rhtoken.json | User-only read/write (chmod 600 recommended) |
| Browser automation | Headless mode, auto-close after token retrieval |
| Terminal spawning | User context, no privilege escalation |
| Web console | Opens in user's default browser (sandboxed) |

### Reliability

| Workflow | Failure Handling |
|----------|------------------|
| ChromeDriver download | Auto-detection and installation |
| SSO authentication | Timeout after 60 seconds |
| Config file operations | Validation, error messages on parse failures |
| Process spawning | Background execution (non-blocking) |
| Missing clusters | 404 errors with clear messages |

---

## Environment Identifiers

| ID | Environment Name | Description |
|----|-----------------|-------------|
| `e` | Ephemeral | Temporary development/testing environments |
| `p` | Production | Production OpenShift cluster |
| `s` | Stage | Staging environment |
| `ap` | App SRE Production | Application SRE production cluster |
| `cp` | App SRE Stage | Application SRE staging cluster |
| `k` | Stone Production | Stone production cluster |

---

## Related Documentation

- **[API Reference](../API.md)** - Complete API endpoint documentation
- **[VPN Workflows](VPN_WORKFLOWS.md)** - VPN connection diagrams
- **[Authentication Flows](AUTH_FLOWS.md)** - Authentication diagrams
- **[Architecture Overview](../ARCHITECTURE.md)** - System architecture
- **[User Guide](../USER_GUIDE.md)** - End-user instructions
