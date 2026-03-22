#!/usr/bin/env bash
# sophia-edge-node installer for Raspberry Pi 4 / 5
# Creates /opt/sophia-edge-node/, installs dependencies, sets up systemd services.
set -euo pipefail

INSTALL_DIR="/opt/sophia-edge-node"
STATE_DIR="$HOME/.sophia-edge"

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

info()  { echo -e "\033[1;32m[+]\033[0m $*"; }
warn()  { echo -e "\033[1;33m[!]\033[0m $*"; }
error() { echo -e "\033[1;31m[-]\033[0m $*"; exit 1; }

require_root() {
    if [[ $EUID -ne 0 ]]; then
        error "Run this script as root (sudo ./install.sh)"
    fi
}

# ---------------------------------------------------------------------------
# Hardware detection
# ---------------------------------------------------------------------------

detect_hardware() {
    local hw
    hw=$(grep -i 'Hardware' /proc/cpuinfo 2>/dev/null | head -1 | cut -d: -f2 | tr -d ' ' || true)
    case "$hw" in
        *BCM2712*) info "Detected Raspberry Pi 5 (BCM2712)"; return 0 ;;
        *BCM2711*) info "Detected Raspberry Pi 4 (BCM2711)"; return 0 ;;
        *BCM*)     info "Detected Broadcom SoC ($hw) -- should work"; return 0 ;;
    esac

    local arch
    arch=$(uname -m)
    if [[ "$arch" == "aarch64" || "$arch" == "armv7l" ]]; then
        warn "Not a Raspberry Pi but ARM detected ($arch). Proceeding anyway."
        return 0
    fi

    error "Unsupported architecture: $arch. This installer targets Raspberry Pi 4/5."
}

# ---------------------------------------------------------------------------
# Dependencies
# ---------------------------------------------------------------------------

install_deps() {
    info "Installing system packages..."
    apt-get update -qq
    apt-get install -y -qq python3 python3-pip python3-venv > /dev/null

    # Check Python version (need 3.9+)
    local pyver
    pyver=$(python3 -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')
    local major minor
    major=$(echo "$pyver" | cut -d. -f1)
    minor=$(echo "$pyver" | cut -d. -f2)
    if (( major < 3 || (major == 3 && minor < 9) )); then
        error "Python 3.9+ required (found $pyver)"
    fi
    info "Python $pyver OK"
}

setup_venv() {
    info "Setting up Python virtual environment..."
    python3 -m venv "$INSTALL_DIR/venv"
    "$INSTALL_DIR/venv/bin/pip" install --quiet --upgrade pip
    "$INSTALL_DIR/venv/bin/pip" install --quiet aiohttp requests
    info "Python dependencies installed"
}

# ---------------------------------------------------------------------------
# File installation
# ---------------------------------------------------------------------------

install_files() {
    info "Installing sophia-edge-node to $INSTALL_DIR ..."
    mkdir -p "$INSTALL_DIR"

    local script_dir
    script_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

    cp "$script_dir/rustchain_miner.py" "$INSTALL_DIR/"
    cp "$script_dir/achievement_bridge.py" "$INSTALL_DIR/"
    cp "$script_dir/config.json" "$INSTALL_DIR/"

    chmod +x "$INSTALL_DIR/rustchain_miner.py"
    chmod +x "$INSTALL_DIR/achievement_bridge.py"

    # State directory (user-writable)
    mkdir -p "$STATE_DIR"
    info "Files installed"
}

# ---------------------------------------------------------------------------
# Configuration prompts
# ---------------------------------------------------------------------------

configure() {
    local config="$INSTALL_DIR/config.json"
    local wallet ra_user ra_key node_id

    echo ""
    info "=== Configuration ==="
    echo ""

    # Node ID
    local default_node_id="sophia-edge-$(hostname -s)"
    read -rp "Node ID [$default_node_id]: " node_id
    node_id="${node_id:-$default_node_id}"

    # Wallet
    read -rp "RTC Wallet ID (leave blank to use node ID): " wallet
    wallet="${wallet:-$node_id}"

    # RetroAchievements
    echo ""
    info "RetroAchievements integration (optional)"
    info "Sign up at https://retroachievements.org if you don't have an account."
    echo ""
    read -rp "RetroAchievements username (blank to skip): " ra_user
    ra_key=""
    if [[ -n "$ra_user" ]]; then
        read -rp "RetroAchievements API key: " ra_key
    fi

    # Write config using python to avoid jq dependency
    python3 - "$config" "$node_id" "$ra_user" "$ra_key" <<'PYEOF'
import json, sys
config_path, node_id, ra_user, ra_key = sys.argv[1], sys.argv[2], sys.argv[3], sys.argv[4]
with open(config_path) as f:
    cfg = json.load(f)
cfg["node_id"] = node_id
cfg["achievements"]["retroachievements"]["username"] = ra_user
cfg["achievements"]["retroachievements"]["api_key"] = ra_key
if not ra_user:
    cfg["achievements"]["enabled"] = False
with open(config_path, "w") as f:
    json.dump(cfg, f, indent=2)
PYEOF

    # Write wallet to environment file for systemd
    cat > "$INSTALL_DIR/env" <<EOF
SOPHIA_WALLET=$wallet
SOPHIA_CONFIG=$INSTALL_DIR/config.json
RA_USERNAME=$ra_user
RA_API_KEY=$ra_key
EOF
    chmod 600 "$INSTALL_DIR/env"

    info "Configuration saved"
}

# ---------------------------------------------------------------------------
# Systemd services
# ---------------------------------------------------------------------------

install_services() {
    info "Installing systemd services..."

    # Miner service
    cat > /etc/systemd/system/sophia-miner.service <<EOF
[Unit]
Description=Sophia Edge Node - RustChain Miner
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=$INSTALL_DIR/env
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/rustchain_miner.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    # Achievement bridge service
    cat > /etc/systemd/system/sophia-achievements.service <<EOF
[Unit]
Description=Sophia Edge Node - RetroAchievements Bridge
After=network-online.target
Wants=network-online.target

[Service]
Type=simple
EnvironmentFile=$INSTALL_DIR/env
ExecStart=$INSTALL_DIR/venv/bin/python3 $INSTALL_DIR/achievement_bridge.py
Restart=always
RestartSec=30
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

    systemctl daemon-reload
    systemctl enable sophia-miner.service

    # Only enable achievements if configured
    if python3 -c "import json; c=json.load(open('$INSTALL_DIR/config.json')); exit(0 if c.get('achievements',{}).get('enabled') else 1)" 2>/dev/null; then
        systemctl enable sophia-achievements.service
        info "Achievement bridge enabled"
    else
        info "Achievement bridge disabled (no RetroAchievements credentials)"
    fi

    info "Systemd services installed"
}

# ---------------------------------------------------------------------------
# Start services
# ---------------------------------------------------------------------------

start_services() {
    echo ""
    read -rp "Start services now? [Y/n]: " start_now
    start_now="${start_now:-Y}"

    if [[ "$start_now" =~ ^[Yy] ]]; then
        systemctl start sophia-miner.service
        info "Miner started"

        if systemctl is-enabled sophia-achievements.service &>/dev/null; then
            systemctl start sophia-achievements.service
            info "Achievement bridge started"
        fi
    else
        info "Services installed but not started. Use:"
        info "  sudo systemctl start sophia-miner"
        info "  sudo systemctl start sophia-achievements"
    fi
}

# ---------------------------------------------------------------------------
# Summary
# ---------------------------------------------------------------------------

show_summary() {
    echo ""
    info "=== Installation Complete ==="
    echo ""
    echo "  Install dir:  $INSTALL_DIR"
    echo "  State dir:    $STATE_DIR"
    echo "  Config:       $INSTALL_DIR/config.json"
    echo ""
    echo "  Manage services:"
    echo "    sudo systemctl status sophia-miner"
    echo "    sudo systemctl status sophia-achievements"
    echo "    sudo journalctl -u sophia-miner -f"
    echo "    sudo journalctl -u sophia-achievements -f"
    echo ""
    echo "  RustChain:    https://rustchain.org"
    echo "  BoTTube:      https://bottube.ai"
    echo ""
}

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

main() {
    echo ""
    echo "  ╔═══════════════════════════════════════╗"
    echo "  ║  Sophia Edge Node Installer           ║"
    echo "  ║  Mine RTC + Earn Retro Game Rewards   ║"
    echo "  ╚═══════════════════════════════════════╝"
    echo ""

    require_root
    detect_hardware
    install_deps
    install_files
    setup_venv
    configure
    install_services
    start_services
    show_summary
}

main "$@"
