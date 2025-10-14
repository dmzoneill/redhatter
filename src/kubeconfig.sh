#!/usr/bin/bash 

cat > "$HOME/.kube/config" <<EOF
apiVersion: v1
kind: Config
preferences: {}
clusters: []
users: []
contexts: []
current-context: ""
EOF

kube() {
    local cluster="$1"
    local namespace="$2"
    local config_name="${cluster}"

    # If namespace provided, include it in the config name for isolation
    if [[ -n "$namespace" ]]; then
        config_name="${cluster}-${namespace}"
    fi

    local path="$HOME/.kube/config.${config_name}"

    if [[ -z "$cluster" ]]; then
        echo "Usage: kube <cluster> [namespace]"
        echo "  cluster:   Cluster identifier (e|s|p|k, etc.)"
        echo "  namespace: Optional OpenShift project/namespace for isolation"
        echo ""
        echo "Examples:"
        echo "  kube e                    # Ephemeral cluster, default namespace"
        echo "  kube e my-project         # Ephemeral cluster, my-project namespace"
        echo "  kube s another-namespace  # Stage cluster, another-namespace"
        echo ""
        echo "Cleanup:"
        echo "  kube-clean <cluster>      # Remove all configs for a cluster"
        return 1
    fi

    export KUBECONFIG="$path"

    # Clean PS1 of any previous (kube:...) tags
    PS1="$(echo "$PS1" | sed -E 's/\(kube:[^)]+\) ?//g')"
    PS1="(kube:${config_name}) $PS1"

    # Pre-fill config if it doesn't exist or is invalid
    if [[ ! -s "$path" ]] || ! grep -q "apiVersion: v1" "$path"; then
        echo "Creating new kubeconfig at: $path"

        # If namespace specified, try to copy from base cluster config
        if [[ -n "$namespace" ]]; then
            local base_config="$HOME/.kube/config.${cluster}"

            # Check if base cluster config exists and is valid
            if [[ -s "$base_config" ]] && grep -q "apiVersion: v1" "$base_config"; then
                # Validate the base config before copying
                echo "Validating base cluster authentication..."
                # Check if config has a valid current-context (not empty or "")
                local base_context=$(KUBECONFIG="$base_config" kubectl config current-context 2>/dev/null)
                if [[ -n "$base_context" ]] && [[ "$base_context" != '""' ]]; then
                    echo "Copying authentication from existing cluster config..."
                    cp "$base_config" "$path"
                    chmod 600 "$path"

                    # Temporarily point KUBECONFIG to namespace config to set namespace
                    local saved_kubeconfig="$KUBECONFIG"
                    export KUBECONFIG="$path"
                    echo "Setting namespace to '${namespace}'..."
                    kubectl config set-context --current --namespace="$namespace" 2>/dev/null || {
                        echo "Warning: Could not set namespace. You may need to run: oc project ${namespace}"
                    }
                    # KUBECONFIG is already set to $path from line 40, so no need to restore
                else
                    echo "Error: Base cluster authentication is invalid or expired."
                    echo "Cleaning up stale configs and re-authenticating..."
                    kube-clean "$cluster"

                    # Re-authenticate - need to temporarily switch KUBECONFIG to base config
                    cat > "$base_config" <<EOF
apiVersion: v1
kind: Config
preferences: {}
clusters: []
users: []
contexts: []
current-context: ""
EOF
                    chmod 600 "$base_config"

                    # Temporarily point KUBECONFIG to base config for rhtoken
                    export KUBECONFIG="$base_config"
                    echo "Authenticating to cluster '${cluster}'..."
                    rhtoken "$cluster"

                    # Verify the base config was populated with a valid context
                    if [[ -s "$base_config" ]] && grep -q "current-context:" "$base_config" && \
                       [[ "$(grep "^current-context:" "$base_config" | awk '{print $2}')" != '""' ]] && \
                       [[ "$(grep "^current-context:" "$base_config" | awk '{print $2}')" != "" ]]; then
                        echo "Copying fresh authentication to namespace config..."
                        cp "$base_config" "$path"
                        chmod 600 "$path"

                        # Now point KUBECONFIG to the namespace-specific config and set namespace
                        export KUBECONFIG="$path"
                        echo "Setting namespace to '${namespace}'..."
                        kubectl config set-context --current --namespace="$namespace" 2>/dev/null || {
                            echo "Warning: Could not set namespace. You may need to run: oc project ${namespace}"
                        }
                    else
                        echo "Error: Authentication failed - base config not properly populated"
                        export KUBECONFIG="$path"
                        return 1
                    fi
                fi
            else
                echo "Base cluster config not found. Please run 'kube ${cluster}' first to authenticate."
                return 1
            fi
        else
            # No namespace specified - create new config and authenticate
            cat > "$path" <<EOF
apiVersion: v1
kind: Config
preferences: {}
clusters: []
users: []
contexts: []
current-context: ""
EOF
            chmod 600 "$path"

            # Get base cluster config from rhtoken
            echo "Authenticating to cluster '${cluster}'..."
            rhtoken "$cluster"
        fi
    else
        echo "Switched to existing kubeconfig: $path"

        # Validate existing config - just check if we have a valid context
        local current_ctx=$(kubectl config current-context 2>/dev/null)
        if [[ -z "$current_ctx" ]] || [[ "$current_ctx" == '""' ]]; then
            echo "Warning: Current session appears to be invalid or expired."
            echo "Run 'kube-clean ${cluster}' to remove stale configs and re-authenticate."
        fi
    fi

    echo "KUBECONFIG now set to: $KUBECONFIG"

    # Display current context and namespace
    if command -v kubectl &> /dev/null; then
        local current_ctx=$(kubectl config current-context 2>/dev/null)
        local current_ns=$(kubectl config view --minify --output 'jsonpath={..namespace}' 2>/dev/null)
        [[ -n "$current_ctx" ]] && echo "Context: $current_ctx"
        [[ -n "$current_ns" ]] && echo "Namespace: $current_ns" || echo "Namespace: default"
    fi
}

# Cleanup function to remove all configs for a cluster
kube-clean() {
    local cluster="$1"

    if [[ -z "$cluster" ]]; then
        echo "Usage: kube-clean <cluster>"
        echo "  Removes all kubeconfig files for the specified cluster"
        echo ""
        echo "Examples:"
        echo "  kube-clean e    # Remove all ephemeral cluster configs"
        echo "  kube-clean s    # Remove all stage cluster configs"
        return 1
    fi

    local configs_found=0
    local configs_removed=0

    echo "Searching for configs matching cluster '${cluster}'..."

    # Find and remove all matching configs
    while IFS= read -r -d '' config_file; do
        ((configs_found++))
        echo "  Removing: $(basename "$config_file")"
        rm -f "$config_file"
        ((configs_removed++))
    done < <(find "$HOME/.kube" -maxdepth 1 -type f -name "config.${cluster}*" -print0 2>/dev/null)

    if [[ $configs_found -eq 0 ]]; then
        echo "No configs found for cluster '${cluster}'"
    else
        echo "Removed ${configs_removed} config file(s) for cluster '${cluster}'"
        echo "Run 'kube ${cluster}' to re-authenticate"
    fi
}

