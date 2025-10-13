.PHONY: help install install-deps install-chrome install-systemd start stop restart status logs \
        lint format test clean dev check health uninstall vpn-profiles-list vpn-profiles-scan \
        vpn-profiles-generate vpn-profiles-install vpn-profiles-clean vpn-profiles-clean-duplicates \
        vpn-profile-connect

# Default target
help: ## Show this help message
	@echo "RHOTP Auto-Connect Makefile"
	@echo "=========================="
	@echo ""
	@awk 'BEGIN {FS = ":.*?## "} /^[a-zA-Z_-]+:.*?## / {printf "\033[36m%-25s\033[0m %s\n", $$1, $$2}' $(MAKEFILE_LIST)

# Installation targets
install: install-deps install-chrome install-systemd ## Install everything (dependencies, Chrome extension, systemd service)
	@echo "✅ Installation complete!"

install-deps: ## Install Python dependencies via pipenv
	@echo "📦 Installing Python dependencies..."
	@which pipenv > /dev/null || (echo "❌ pipenv not found. Install with: pip install pipenv" && exit 1)
	pipenv install --dev
	@echo "✅ Dependencies installed"
	@echo "🔍 Verifying installation..."
	@pipenv run python -c "import fastapi, uvicorn; print('✅ Core dependencies verified')" || (echo "❌ Dependency verification failed" && exit 1)

install-chrome: ## Install Chrome native messaging host
	@echo "🌐 Installing Chrome native messaging host..."
	@python3 src/install_native_host.py --extension-id pnhnmlnjjbjhacgeadpnmmfdglepblbc
	@echo "✅ Chrome native messaging installed"

install-systemd: ## Install systemd user service
	@echo "⚙️  Installing systemd service..."
	@which pipenv > /dev/null || (echo "❌ pipenv not found. Run 'make install-deps' first" && exit 1)
	@mkdir -p ~/.config/systemd/user
	@cp systemd/rhotp.service ~/.config/systemd/user/
	@sed -i 's|%h/src/rh-otp-auto-connect|$(PWD)|g' ~/.config/systemd/user/rhotp.service
	@sed -i 's|%h/.local/bin/pipenv|$(shell which pipenv)|g' ~/.config/systemd/user/rhotp.service
	@sed -i 's|%h/.local/bin|$(shell dirname $(shell which pipenv))|g' ~/.config/systemd/user/rhotp.service
	@systemctl --user daemon-reload
	@systemctl --user enable rhotp
	@echo "✅ Systemd service installed and enabled"
	@echo "🔧 Service will use pipenv virtual environment at $(shell which pipenv)"

# Service management
start: ## Start the RHOTP service
	@echo "🚀 Starting RHOTP service..."
	@systemctl --user start rhotp
	@echo "✅ Service started"

stop: ## Stop the RHOTP service
	@echo "🛑 Stopping RHOTP service..."
	@systemctl --user stop rhotp
	@echo "✅ Service stopped"

restart: ## Restart the RHOTP service
	@echo "🔄 Restarting RHOTP service..."
	@systemctl --user restart rhotp
	@echo "✅ Service restarted"

status: ## Show service status
	@systemctl --user status rhotp

logs: ## Show service logs
	@journalctl --user -u rhotp -f

# Development targets
dev: ## Start development server with auto-reload
	@echo "🔧 Starting development server..."
	cd src && pipenv run uvicorn main:app --reload --port 8009

# Code quality
lint: ## Run linting checks (black, flake8, isort, mypy)
	@echo "🔍 Running lint checks..."
	@pipenv run black --check --diff .
	@pipenv run flake8 .
	@pipenv run isort --check-only --diff .
	@pipenv run mypy . || true
	@echo "✅ Lint checks complete"

format: ## Format code with black and isort
	@echo "🎨 Formatting code..."
	@pipenv run black .
	@pipenv run isort .
	@echo "✅ Code formatted"

test: ## Run tests
	@echo "🧪 Running tests..."
	@if [ -d "tests" ]; then \
		pipenv run pytest -v; \
	else \
		echo "ℹ️  No tests directory found. Creating basic test structure..."; \
		mkdir -p tests; \
		echo "# Add your tests here" > tests/__init__.py; \
		echo "def test_placeholder():" > tests/test_main.py; \
		echo "    assert True" >> tests/test_main.py; \
		echo "📝 Basic test structure created in tests/"; \
	fi

# Health checks
check: lint test ## Run all checks (lint + test)

health: ## Check if service is healthy
	@echo "🏥 Checking service health..."
	@if curl -s http://localhost:8009/ > /dev/null; then \
		echo "✅ Service is responding on port 8009"; \
	else \
		echo "❌ Service is not responding on port 8009"; \
		exit 1; \
	fi

check-venv: ## Check if service is using the correct Python environment
	@echo "🐍 Checking Python environment used by service..."
	@if systemctl --user is-active rhotp >/dev/null 2>&1; then \
		echo "✅ Service is running"; \
		if curl -s http://localhost:8009/ >/dev/null 2>&1; then \
			echo "✅ Service responding - likely using correct environment"; \
		else \
			echo "❌ Service not responding - may have dependency issues"; \
		fi; \
	else \
		echo "❌ Service is not running"; \
	fi
	@echo "📋 To check service logs: make logs"

# Utility targets
clean: ## Clean up cache files and temporary files
	@echo "🧹 Cleaning up..."
	@find . -type f -name "*.pyc" -delete
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@rm -f /tmp/vpnpw /tmp/vpnpw-shuttle
	@echo "✅ Cleanup complete"

uninstall: ## Uninstall systemd service and Chrome extension
	@echo "🗑️  Uninstalling RHOTP..."
	@systemctl --user stop rhotp 2>/dev/null || true
	@systemctl --user disable rhotp 2>/dev/null || true
	@rm -f ~/.config/systemd/user/rhotp.service
	@python3 src/install_native_host.py --uninstall
	@systemctl --user daemon-reload
	@echo "✅ Uninstall complete"

# VPN connection shortcuts
vpn-connect: ## Connect to VPN using vpn-connect script
	@echo "🔌 Connecting to VPN..."
	@./vpn-connect

vpn-connect-shuttle: ## Connect to VPN using shuttle
	@echo "🚀 Connecting to VPN via shuttle..."
	@./vpn-connect-shuttle

vpn-status: ## Show VPN connection status
	@echo "📊 VPN Connection Status:"
	@nmcli connection show --active | grep -i vpn || echo "❌ No active VPN connections"
	@echo ""
	@echo "🔗 Available VPN connections:"
	@nmcli connection show | grep vpn || echo "❌ No VPN connections configured"

vpn-disconnect: ## Disconnect VPN
	@echo "🔌 Disconnecting VPN..."
	@nmcli connection down vpn 2>/dev/null || nmcli connection down id "Red Hat VPN" 2>/dev/null || echo "⚠️  No VPN to disconnect"

# VPN Profile Management
vpn-profiles-list: ## List all configured VPN profiles
	@./vpn-profile-manager list

vpn-profiles-scan: ## Scan NetworkManager for Red Hat VPN profiles
	@echo "🔍 Scanning NetworkManager for Red Hat VPN profiles..."
	@cd vpn-profiles && python3 scan-profiles.py

vpn-profiles-generate: ## Generate .nmconnection files for all profiles
	@echo "📝 Generating VPN profile configurations..."
	@./vpn-profile-manager generate

vpn-profiles-install: ## Install all VPN profiles to NetworkManager
	@echo "📦 Installing VPN profiles to NetworkManager..."
	@./vpn-profile-manager install-all

vpn-profiles-clean: ## Remove all Red Hat VPN profiles from NetworkManager
	@echo "🗑️  Removing Red Hat VPN profiles..."
	@./vpn-profile-manager clean

vpn-profiles-clean-duplicates: ## Remove duplicate VPN profiles
	@echo "🧹 Removing duplicate VPN profiles..."
	@./vpn-profile-manager clean-duplicates -y

vpn-profile-connect: ## Connect to specific VPN profile (usage: make vpn-profile-connect PROFILE=IAD2)
	@if [ -z "$(PROFILE)" ]; then \
		echo "❌ Error: PROFILE not specified"; \
		echo "Usage: make vpn-profile-connect PROFILE=IAD2"; \
		./vpn-profile-manager list; \
		exit 1; \
	fi
	@./vpn-profile-manager connect $(PROFILE)

# Token management
token-info: ## Show token file information
	@echo "🔑 Token information:"
	@if [ -f ~/.cache/rhotp/auth_token ]; then \
		echo "Token file exists: ~/.cache/rhotp/auth_token"; \
		echo "File permissions: $$(ls -la ~/.cache/rhotp/auth_token | cut -d' ' -f1)"; \
		echo "File size: $$(wc -c < ~/.cache/rhotp/auth_token) bytes"; \
	else \
		echo "❌ Token file not found. Start the service to generate one."; \
	fi

# Requirements file generation (for non-pipenv users)
requirements: ## Generate requirements.txt from Pipfile
	@echo "📋 Generating requirements.txt..."
	@pipenv requirements > requirements.txt
	@pipenv requirements --dev > requirements-dev.txt
	@echo "✅ Generated requirements.txt and requirements-dev.txt"

# Chrome extension development
list-chrome-dirs: ## List Chrome configuration directories
	@python3 src/install_native_host.py --list

install-chrome-specific: ## Install for specific browsers (e.g., make install-chrome-specific BROWSERS="chrome chromium")
	@python3 src/install_native_host.py --extension-id pnhnmlnjjbjhacgeadpnmmfdglepblbc --browsers $(BROWSERS)

# Extension development
extension-reload: ## Reload Chrome extension (requires chrome-cli or similar)
	@echo "🔄 Reloading Chrome extension..."
	@if command -v chrome-cli >/dev/null 2>&1; then \
		chrome-cli reload -t "chrome-extension://pnhnmlnjjbjhacgeadpnmmfdglepblbc"; \
	else \
		echo "ℹ️  Install chrome-cli for automatic extension reloading"; \
		echo "   Or manually reload extension at chrome://extensions/"; \
	fi

# GNOME Extension targets
install-gnome: ## Install GNOME Shell extension (via symlink for development)
	@echo "🐧 Installing GNOME Shell extension..."
	@EXTENSION_UUID="rh-otp@redhat.com"; \
	EXTENSION_DIR="$$HOME/.local/share/gnome-shell/extensions/$$EXTENSION_UUID"; \
	SOURCE_DIR="$(PWD)/src/rh-otp-gnome"; \
	echo "📁 Checking extension directories..."; \
	mkdir -p "$$(dirname "$$EXTENSION_DIR")"; \
	if [ -L "$$EXTENSION_DIR" ]; then \
		echo "🔗 Removing existing symlink..."; \
		rm "$$EXTENSION_DIR"; \
	elif [ -d "$$EXTENSION_DIR" ]; then \
		echo "📂 Removing existing directory..."; \
		rm -rf "$$EXTENSION_DIR"; \
	fi; \
	echo "🔗 Creating symlink: $$EXTENSION_DIR -> $$SOURCE_DIR"; \
	ln -sf "$$SOURCE_DIR" "$$EXTENSION_DIR"; \
	echo "⚙️  Compiling GSettings schema..."; \
	if [ -d "$$SOURCE_DIR/schemas" ]; then \
		glib-compile-schemas "$$SOURCE_DIR/schemas/" || echo "⚠️  Schema compilation failed"; \
	fi; \
	echo "✅ GNOME extension installed successfully (symlinked)!"; \
	echo ""; \
	echo "💡 Development benefits:"; \
	echo "• Edit files in rh-otp-gnome/ directory"; \
	echo "• Changes reflect immediately after: make gnome-reload"; \
	echo "• No need to reinstall for updates"; \
	echo ""; \
	echo "📋 Next steps:"; \
	if [ "$$XDG_SESSION_TYPE" = "wayland" ]; then \
		echo "🌊 Wayland session detected:"; \
		echo "1. Log out and log back in (Wayland requirement)"; \
		echo "2. Enable extension: make gnome-enable"; \
		echo "3. For development: make gnome-reload (often works without logout)"; \
	else \
		echo "🖥️  X11 session detected:"; \
		echo "1. Restart GNOME Shell: Alt+F2, type 'r', press Enter"; \
		echo "   OR use: make gnome-restart-shell"; \
		echo "2. Enable extension: make gnome-enable"; \
	fi; \
	echo "4. Configure extension: make gnome-prefs"

gnome-enable: ## Enable GNOME Shell extension
	@echo "🔄 Enabling GNOME Shell extension..."
	@gnome-extensions enable rh-otp@redhat.com 2>/dev/null && \
		echo "✅ Extension enabled!" || \
		echo "⚠️  Could not enable automatically. Try manually or restart GNOME Shell first."

gnome-disable: ## Disable GNOME Shell extension
	@echo "🔄 Disabling GNOME Shell extension..."
	@gnome-extensions disable rh-otp@redhat.com 2>/dev/null && \
		echo "✅ Extension disabled!" || \
		echo "⚠️  Extension was not enabled or could not disable"

gnome-prefs: ## Open GNOME extension preferences
	@echo "⚙️  Opening GNOME extension preferences..."
	@gnome-extensions prefs rh-otp@redhat.com 2>/dev/null || \
		echo "⚠️  Could not open preferences. Extension may not be installed or enabled."

gnome-status: ## Show GNOME extension status
	@echo "📊 GNOME Extension Status:"
	@echo "Session type: $$(echo $$XDG_SESSION_TYPE | tr '[:lower:]' '[:upper:]')"
	@echo "Extension installed: $$([ -d "$$HOME/.local/share/gnome-shell/extensions/rh-otp@redhat.com" ] && echo "✅ Yes" || echo "❌ No")"
	@echo "Extension symlinked: $$([ -L "$$HOME/.local/share/gnome-shell/extensions/rh-otp@redhat.com" ] && echo "✅ Yes (development mode)" || echo "❌ No")"
	@echo "Extension enabled: $$(gnome-extensions list --enabled 2>/dev/null | grep -q rh-otp && echo "✅ Yes" || echo "❌ No")"
	@echo "GNOME Shell version: $$(gnome-shell --version 2>/dev/null || echo "Unknown")"

gnome-logs: ## Show GNOME extension logs
	@echo "📋 GNOME Extension Logs (press Ctrl+C to exit):"
	@journalctl -f /usr/bin/gnome-shell | grep -i --color=always rh-otp

uninstall-gnome: ## Uninstall GNOME Shell extension
	@echo "🗑️  Uninstalling GNOME Shell extension..."
	@gnome-extensions disable rh-otp@redhat.com 2>/dev/null || echo "Extension was not enabled"
	@EXTENSION_DIR="$$HOME/.local/share/gnome-shell/extensions/rh-otp@redhat.com"; \
	if [ -d "$$EXTENSION_DIR" ]; then \
		rm -rf "$$EXTENSION_DIR"; \
		echo "✅ Extension files removed"; \
	else \
		echo "⚠️  Extension directory not found"; \
	fi; \
	echo "💡 You may need to restart GNOME Shell to complete removal"

gnome-reload: ## Reload GNOME extension (disable and re-enable)
	@echo "🔄 Reloading GNOME extension..."
	@make gnome-disable >/dev/null 2>&1 || true
	@sleep 1
	@make gnome-enable

gnome-restart-shell: ## Restart GNOME Shell (X11 only, Wayland users need logout/login)
	@echo "🔄 Restarting GNOME Shell..."
	@if [ "$$XDG_SESSION_TYPE" = "wayland" ]; then \
		echo "❌ GNOME Shell restart not supported under Wayland"; \
		echo "💡 Wayland users must log out and log back in to restart GNOME Shell"; \
		echo "💡 For extension changes, try: make gnome-reload (often works without shell restart)"; \
	else \
		echo "🖥️  Restarting GNOME Shell (X11)..."; \
		busctl --user call org.gnome.Shell /org/gnome/Shell org.gnome.Shell Eval s 'Meta.restart("Restarting...")'; \
	fi

gnome-session-restart: ## Restart GNOME session (works on both X11 and Wayland)
	@echo "🔄 Restarting GNOME session..."
	@echo "⚠️  This will close all applications and restart your desktop session"
	@read -p "Continue? (y/N): " confirm; \
	if [ "$$confirm" = "y" ] || [ "$$confirm" = "Y" ]; then \
		gnome-session-quit --logout --force; \
	else \
		echo "❌ Session restart cancelled"; \
	fi

gnome-dev: ## Development mode: install, enable, and watch for changes
	@echo "🔧 Setting up GNOME extension development mode..."
	@make install-gnome
	@sleep 2
	@make gnome-enable
	@echo "✅ Development setup complete!"
	@echo ""
	@echo "🔄 Quick development workflow:"
	@echo "• Edit files in rh-otp-gnome/"
	@echo "• Test changes: make gnome-reload"
	@echo "• View logs: make gnome-logs"
	@echo "• Check status: make gnome-status"

gnome-watch: ## Watch extension files and auto-reload on changes (requires inotify-tools)
	@echo "👁️  Watching GNOME extension files for changes..."
	@echo "Press Ctrl+C to stop watching"
	@which inotifywait >/dev/null 2>&1 || (echo "❌ inotifywait not found. Install with: sudo dnf install inotify-tools" && exit 1)
	@while inotifywait -e modify,create,delete -r src/rh-otp-gnome/ >/dev/null 2>&1; do \
		echo "📝 File change detected, reloading extension..."; \
		make gnome-reload >/dev/null 2>&1; \
		echo "✅ Extension reloaded"; \
		sleep 1; \
	done

# Combined installation targets
install-all: install install-gnome ## Install everything (service, Chrome extension, GNOME extension)
	@echo "🎉 All components installed!"
	@echo ""
	@echo "📋 Quick start:"
	@echo "1. Start service: make start"
	@echo "2. Enable GNOME extension: make gnome-enable"
	@echo "3. Check status: make status && make gnome-status"

uninstall-all: uninstall uninstall-gnome ## Uninstall all components
	@echo "🗑️  All components uninstalled"