#!/usr/bin/env python3
"""
Scan NetworkManager system-connections for Red Hat VPN profiles
and generate profiles.yaml configuration file.
"""

import configparser
import os
import re
import sys
from pathlib import Path

import yaml

NM_CONNECTIONS_DIR = "/etc/NetworkManager/system-connections"


def scan_redhat_vpn_profiles():
    """Scan NetworkManager connections for Red Hat VPN profiles."""
    profiles = []

    if not os.path.exists(NM_CONNECTIONS_DIR):
        print(f"Error: {NM_CONNECTIONS_DIR} not found")
        sys.exit(1)

    # Get all .nmconnection files
    connection_files = list(Path(NM_CONNECTIONS_DIR).glob("*.nmconnection"))

    for conn_file in connection_files:
        try:
            # Read the connection file
            config = configparser.ConfigParser()

            # Read with sudo to handle permissions
            content = os.popen(f'sudo cat "{conn_file}"').read()
            config.read_string(content)

            # Check if it's an OpenVPN connection
            if not config.has_section("vpn"):
                continue

            vpn_section = config["vpn"]

            # Check if it's a Red Hat VPN (contains redhat.com in remote)
            if "remote" not in vpn_section:
                continue

            remote = vpn_section.get("remote", "")
            if "redhat.com" not in remote:
                continue

            # Extract profile information
            conn_section = config["connection"]
            ipv4_section = config["ipv4"] if config.has_section("ipv4") else {}

            # Parse the remote to extract location code
            # Format: ovpn-ams2.redhat.com or ovpn.redhat.com
            remote_match = re.match(r"ovpn(?:-([a-z0-9-]+))?\.redhat\.com", remote)
            if remote_match:
                location_code = remote_match.group(1)
                if location_code:
                    profile_id = location_code.upper().replace("-", "_")
                else:
                    profile_id = "GLOBAL"
            else:
                # Fallback: use connection ID
                profile_id = conn_section.get("id", "").replace(" ", "_").upper()

            # Build profile dictionary
            profile = {
                "id": profile_id,
                "name": conn_section.get("id", profile_id),
                "remote": remote,
                "uuid": conn_section.get("uuid", ""),
            }

            # Add optional fields if they differ from defaults
            if "port" in vpn_section and vpn_section.get("port") != "443":
                profile["port"] = int(vpn_section.get("port"))

            if "proto-tcp" in vpn_section:
                profile["proto_tcp"] = vpn_section.get("proto-tcp") == "yes"

            if "tunnel-mtu" in vpn_section and vpn_section.get("tunnel-mtu") != "1360":
                profile["tunnel_mtu"] = int(vpn_section.get("tunnel-mtu"))

            # Extract DNS settings
            if "dns-search" in ipv4_section:
                dns_search = ipv4_section.get("dns-search")
                if dns_search and dns_search != "~.;redhat.com;":
                    profile["dns_search"] = dns_search

            if "route-table" in ipv4_section:
                route_table = ipv4_section.get("route-table")
                if route_table and route_table != "75":
                    profile["route_table"] = int(route_table)

            profiles.append(profile)
            print(f"Found: {profile['id']} - {profile['name']}")

        except Exception as e:
            print(f"Error processing {conn_file}: {e}", file=sys.stderr)
            continue

    return profiles


def generate_profiles_yaml(profiles):
    """Generate profiles.yaml configuration file."""

    # Sort profiles by ID
    profiles.sort(key=lambda x: x["id"])

    # Default settings that apply to all profiles
    default_settings = {
        "auth": "SHA256",
        "ca": "{{project_dir}}/vpn-profiles/certs/ca-bundle.crt",
        "cipher": "AES-256-CBC",
        "connection_type": "password",
        "data_ciphers": "AES-256-GCM:AES-128-GCM:CHACHA20-POLY1305:AES-256-CBC",
        "password_flags": 2,
        "port": 443,
        "proto_tcp": True,
        "remote_cert_tls": "server",
        "reneg_seconds": 0,
        "tunnel_mtu": 1360,
        "verify_x509_name": "name:ovpn.redhat.com",
        "dns_search": "~.;redhat.com;",
        "dns_priority": -1,
        "never_default": True,
        "route_table": 75,
        "routing_rule": "priority 16383 from 0.0.0.0/0 table 75",
    }

    config = {"default_settings": default_settings, "profiles": profiles}

    return yaml.dump(config, default_flow_style=False, sort_keys=False, indent=2)


def main():
    """Main function."""
    print("Scanning NetworkManager connections for Red Hat VPN profiles...")
    print()

    profiles = scan_redhat_vpn_profiles()

    print()
    print(f"Found {len(profiles)} Red Hat VPN profiles")
    print()

    if not profiles:
        print("No profiles found. Exiting.")
        sys.exit(0)

    # Generate YAML
    yaml_content = generate_profiles_yaml(profiles)

    # Write to file
    output_file = Path(__file__).parent / "profiles.yaml"
    output_file.write_text(yaml_content)

    print(f"Generated: {output_file}")
    print()
    print("Next steps:")
    print("1. Review and edit profiles.yaml")
    print("2. Run: ./vpn-profile-manager list")
    print("3. Run: ./vpn-profile-manager install-all")


if __name__ == "__main__":
    main()
