import { Extension } from 'resource:///org/gnome/shell/extensions/extension.js';
import * as Main from 'resource:///org/gnome/shell/ui/main.js';
import * as PanelMenu from 'resource:///org/gnome/shell/ui/panelMenu.js';
import * as PopupMenu from 'resource:///org/gnome/shell/ui/popupMenu.js';
import * as MessageTray from 'resource:///org/gnome/shell/ui/messageTray.js';

import { gettext as _ } from 'resource:///org/gnome/shell/extensions/extension.js';

import GObject from 'gi://GObject';
import St from 'gi://St';
import Clutter from 'gi://Clutter';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Soup from 'gi://Soup';

// Extension version for debugging code reloads
const EXTENSION_VERSION = '1.0.8';

/**
 * Execute a command asynchronously and return the output from `stdout` on
 * success or throw an error with output from `stderr` on failure.
 *
 * If given, @input will be passed to `stdin` and @cancellable can be used to
 * stop the process before it finishes.
 *
 * @param {string[]} argv - a list of string arguments
 * @param {string} [input] - Input to write to `stdin` or %null to ignore
 * @param {Gio.Cancellable} [cancellable] - optional cancellable object
 * @returns {Promise<string>} - The process output
 */
async function execCommunicate (argv, input = null, cancellable = null) {
  let cancelId = 0
  let flags = Gio.SubprocessFlags.STDOUT_PIPE |
                Gio.SubprocessFlags.STDERR_PIPE

  if (input !== null) { flags |= Gio.SubprocessFlags.STDIN_PIPE }

  const proc = new Gio.Subprocess({ argv, flags })
  proc.init(cancellable)

  if (cancellable instanceof Gio.Cancellable) { cancelId = cancellable.connect(() => proc.force_exit()) }

  try {
    const [stdout, stderr] = await proc.communicate_utf8_async(input, cancellable)

    const status = proc.get_exit_status()

    if (status !== 0) {
      throw new Gio.IOErrorEnum({
        code: Gio.IOErrorEnum.FAILED,
        message: stderr ? stderr.trim() : `Command '${argv}' failed with exit code ${status}`
      })
    }

    return stdout.trim()
  } finally {
    if (cancelId > 0) { cancellable.disconnect(cancelId) }
  }
}

// GNOME Shell extension for Red Hat OTP Auto-Connect
var RHOTPIndicator = GObject.registerClass(
class RHOTPIndicator extends PanelMenu.Button {
    _init(extension) {
        super._init(0.0, 'Red Hat OTP');

        this._extension = extension;

        // Create the Red Hat icon
        this._icon = new St.Icon({
            gicon: this._getRedHatIcon(),
            style_class: 'system-status-icon'
        });
        
        this.add_child(this._icon);
        
        // Load settings first
        this._loadSettings();
        
        // Create menu items
        this._createMenu();
    }
    
    _getRedHatIcon() {
        try {
            // Use the rh.png from the GNOME extension directory
            const iconPath = this._extension.path + '/rh.png';
            const iconFile = Gio.File.new_for_path(iconPath);

            if (iconFile.query_exists(null)) {
                return Gio.icon_new_for_string(iconPath);
            }

            // Fallback to try the Chrome extension directory
            const altIconPath = '/home/' + GLib.get_user_name() + '/src/rh-otp-auto-connect/src/rh-otp/rh.png';
            const altIconFile = Gio.File.new_for_path(altIconPath);

            if (altIconFile.query_exists(null)) {
                return Gio.icon_new_for_string(altIconPath);
            }
        } catch (e) {
            log('RH-OTP: Could not load custom icon, using fallback');
        }

        // Fallback to system icon
        return Gio.icon_new_for_string('security-high-symbolic');
    }
    
    _createMenu() {
        // Password section
        const passwordSection = new PopupMenu.PopupMenuSection();

        // Associate Password menu item with key icon
        this._associateItem = new PopupMenu.PopupImageMenuItem('Get Associate Password', 'dialog-password-symbolic');
        this._associateItem.connect('activate', () => {
            this._getPassword('associate');
        });
        passwordSection.addMenuItem(this._associateItem);

        // Ephemeral Password menu item with cloud/server icon
        this._ephemeralItem = new PopupMenu.PopupImageMenuItem('Get Ephemeral Password', 'network-server-symbolic');
        this._ephemeralItem.connect('activate', () => {
            this._getPassword('jdoeEphemeral');
        });
        passwordSection.addMenuItem(this._ephemeralItem);

        this.menu.addMenuItem(passwordSection);

        // Separator
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // VPN section
        const vpnSection = new PopupMenu.PopupMenuSection();

        // VPN Profile submenu - dynamically populated with globe icon
        this._vpnProfileSubmenu = new PopupMenu.PopupSubMenuMenuItem('Connect to VPN Profile', true);
        this._vpnProfileSubmenu.icon.icon_name = 'network-vpn-symbolic';
        vpnSection.addMenuItem(this._vpnProfileSubmenu);

        // Set Default VPN submenu - dynamically populated with star icon
        this._setDefaultSubmenu = new PopupMenu.PopupSubMenuMenuItem('Set Default VPN Profile', true);
        this._setDefaultSubmenu.icon.icon_name = 'starred-symbolic';
        vpnSection.addMenuItem(this._setDefaultSubmenu);

        // VPN Connect menu item (legacy - uses default profile from pass)
        this._vpnConnectItem = new PopupMenu.PopupImageMenuItem('Connect VPN (Standard)', 'network-wired-symbolic');
        this._vpnConnectItem.connect('activate', () => {
            this._connectVPN('standard');
        });
        vpnSection.addMenuItem(this._vpnConnectItem);

        // VPN Shuttle Connect menu item with rocket icon
        this._vpnShuttleItem = new PopupMenu.PopupImageMenuItem('Connect VPN (Shuttle)', 'network-wireless-symbolic');
        this._vpnShuttleItem.connect('activate', () => {
            this._connectVPN('shuttle');
        });
        vpnSection.addMenuItem(this._vpnShuttleItem);

        // VPN Disconnect menu item with disconnect icon
        this._vpnDisconnectItem = new PopupMenu.PopupImageMenuItem('Disconnect VPN', 'network-offline-symbolic');
        this._vpnDisconnectItem.connect('activate', () => {
            this._disconnectVPN();
        });
        vpnSection.addMenuItem(this._vpnDisconnectItem);

        this.menu.addMenuItem(vpnSection);

        // Separator
        this.menu.addMenuItem(new PopupMenu.PopupSeparatorMenuItem());

        // Settings menu item with gear icon
        this._settingsItem = new PopupMenu.PopupImageMenuItem('Settings', 'preferences-system-symbolic');
        this._settingsItem.connect('activate', () => {
            this._openSettings();
        });
        this.menu.addMenuItem(this._settingsItem);
        
        // Status item
        this._statusItem = new PopupMenu.PopupMenuItem('Status: Ready', { reactive: false });
        this.menu.addMenuItem(this._statusItem);
        
        // VPN Status item  
        this._vpnStatusItem = new PopupMenu.PopupMenuItem('VPN: Initializing...', { reactive: false });
        this.menu.addMenuItem(this._vpnStatusItem);
        
        // Track initialization state
        this._isInitializing = true;
        
        // Check VPN status when menu is opened
        this.menu.connect('open-state-changed', (menu, open) => {
            if (open) {
                // Only show checking status if not initializing
                if (this._vpnStatusItem && !this._isInitializing) {
                    this._vpnStatusItem.label.text = 'VPN: Checking...';
                }
                // Add a small delay to make the checking visible, then check actual status
                GLib.timeout_add(GLib.PRIORITY_DEFAULT, 100, () => {
                    this._checkVPNState().catch(error => {
                        console.log(`RH-OTP: Error checking VPN state: ${error.message}`);
                    });
                    return GLib.SOURCE_REMOVE;
                });
            }
        });
        
        // Get VPN UUID once on startup and initialize status
        this._initializeVPNStatus();

        // Fetch default VPN profile information
        this._fetchDefaultVPN();

        // Set up periodic VPN status checking every 30 seconds
        this._vpnCheckInterval = GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 30, () => {
            this._checkVPNState().catch(error => {
                console.log(`RH-OTP: Error in periodic VPN check: ${error.message}`);
            });
            return GLib.SOURCE_CONTINUE;
        });
    }
    
    _loadSettings() {
        // Default settings
        this._settings = {
            apiUrl: 'http://localhost:8009',
            headless: false,
            autoNotifications: true,
            vpnScriptPath: '',
            vpnShuttlePath: '',
            autoCheckVpnStatus: true
        };

        // Try to load from gsettings if schema exists
        try {
            this._gsettings = this._extension.getSettings();
            this._settings.apiUrl = this._gsettings.get_string('api-url') || this._settings.apiUrl;
            this._settings.headless = this._gsettings.get_boolean('headless') || this._settings.headless;
            this._settings.autoNotifications = this._gsettings.get_boolean('auto-notifications') || this._settings.autoNotifications;
            this._settings.vpnScriptPath = this._gsettings.get_string('vpn-script-path') || this._detectVpnScriptPath();
            this._settings.vpnShuttlePath = this._gsettings.get_string('vpn-shuttle-path') || this._detectVpnShuttlePath();
            this._settings.autoCheckVpnStatus = this._gsettings.get_boolean('auto-check-vpn-status') !== false;
        } catch (e) {
            log('RH-OTP: Using default settings (no schema found)');
            this._settings.vpnScriptPath = this._detectVpnScriptPath();
            this._settings.vpnShuttlePath = this._detectVpnShuttlePath();
        }
    }

    async _fetchDefaultVPN() {
        try {
            const token = await this._getAuthToken();
            if (!token) {
                console.log('RH-OTP: Cannot fetch default VPN - no auth token');
                // Even if we can't get the default, still load the profiles
                console.log('RH-OTP: Initializing VPN profiles menu (no default)...');
                this._loadVPNProfiles();
                return;
            }

            const url = `${this._settings.apiUrl}/vpn/default`;
            const defaultInfo = await this._makeAuthenticatedJsonRequest(url, token);

            this._defaultProfileId = defaultInfo.profile_id;
            this._defaultProfileUuid = defaultInfo.uuid;

            console.log(`RH-OTP: Default VPN set to ${defaultInfo.profile_name} (${defaultInfo.profile_id})`);

            // Now load the VPN profiles with the default info available
            console.log('RH-OTP: Initializing VPN profiles menu with default...');
            this._loadVPNProfiles();
        } catch (error) {
            console.log(`RH-OTP: Error fetching default VPN: ${error.message}`);
            this._defaultProfileId = null;
            this._defaultProfileUuid = null;
            // Still load the profiles even if default fetch failed
            console.log('RH-OTP: Initializing VPN profiles menu (error getting default)...');
            this._loadVPNProfiles();
        }
    }
    
    async _getPassword(context) {
        this._updateStatus('Fetching password...', true);
        
        try {
            // Get auth token first
            const token = await this._getAuthToken();
            if (!token) {
                throw new Error('Failed to get authentication token');
            }
            
            // Make API request
            const url = `${this._settings.apiUrl}/get_creds?context=${context}&headless=${this._settings.headless}`;
            const password = await this._makeAuthenticatedRequest(url, token);
            
            // Parse password from response
            const credentials = password.split(',');
            let passwordOnly = credentials.length > 1 ? credentials[1] : password;
            
            // Clean up the password - remove quotes, newlines, carriage returns, and whitespace from start and end
            passwordOnly = passwordOnly.trim();
            passwordOnly = passwordOnly.replace(/^["']+/, '').replace(/["'\n\r\s]+$/, '');
            
            // Copy to clipboard
            this._copyToClipboard(passwordOnly);
            
            // Show notification
            if (this._settings.autoNotifications) {
                this._showNotification('Password Copied', `${context} password copied to clipboard`);
            }
            
            this._updateStatus('Password copied to clipboard');
            
        } catch (error) {
            log(`RH-OTP Error: ${error.message}`);
            this._updateStatus('Error: ' + error.message);
            this._showNotification('RH-OTP Error', error.message);
        }
    }
    
    _getAuthToken() {
        return new Promise((resolve, reject) => {
            try {
                const tokenPath = GLib.build_filenamev([GLib.get_home_dir(), '.cache', 'rhotp', 'auth_token']);
                const tokenFile = Gio.File.new_for_path(tokenPath);
                
                if (!tokenFile.query_exists(null)) {
                    reject(new Error('Auth token file not found. Is RHOTP service running?'));
                    return;
                }
                
                tokenFile.load_contents_async(null, (file, result) => {
                    try {
                        const [success, contents] = file.load_contents_finish(result);
                        if (success) {
                            const token = new TextDecoder().decode(contents).trim();
                            resolve(token);
                        } else {
                            reject(new Error('Failed to read auth token'));
                        }
                    } catch (e) {
                        reject(e);
                    }
                });
            } catch (e) {
                reject(e);
            }
        });
    }
    
    _makeAuthenticatedRequest(url, token) {
        return new Promise((resolve, reject) => {
            const session = new Soup.Session();
            const message = Soup.Message.new('GET', url);

            // Add authorization header
            message.request_headers.append('Authorization', `Bearer ${token}`);

            session.send_async(message, GLib.PRIORITY_DEFAULT, null, (session, result) => {
                try {
                    const inputStream = session.send_finish(result);
                    const dataInputStream = new Gio.DataInputStream({
                        base_stream: inputStream
                    });

                    let response = '';
                    let line;
                    while ((line = dataInputStream.read_line(null)[0]) !== null) {
                        response += new TextDecoder().decode(line) + '\n';
                    }

                    if (message.status_code === 200) {
                        // Clean up response - remove quotes, newlines, and whitespace
                        response = response.trim();
                        response = response.replace(/^["']+/, '').replace(/["'\n\r\s]+$/, '');
                        resolve(response);
                    } else {
                        reject(new Error(`HTTP ${message.status_code}: ${response}`));
                    }
                } catch (e) {
                    reject(e);
                }
            });
        });
    }

    _makeAuthenticatedJsonRequest(url, token) {
        return new Promise((resolve, reject) => {
            const session = new Soup.Session();
            const message = Soup.Message.new('GET', url);

            // Add authorization header
            message.request_headers.append('Authorization', `Bearer ${token}`);

            session.send_async(message, GLib.PRIORITY_DEFAULT, null, (session, result) => {
                try {
                    const inputStream = session.send_finish(result);
                    const dataInputStream = new Gio.DataInputStream({
                        base_stream: inputStream
                    });

                    let response = '';
                    let line;
                    while ((line = dataInputStream.read_line(null)[0]) !== null) {
                        response += new TextDecoder().decode(line) + '\n';
                    }

                    if (message.status_code === 200) {
                        // Parse JSON response without cleaning
                        const jsonData = JSON.parse(response.trim());
                        resolve(jsonData);
                    } else {
                        reject(new Error(`HTTP ${message.status_code}: ${response}`));
                    }
                } catch (e) {
                    reject(e);
                }
            });
        });
    }

    _copyToClipboard(text) {
        const clipboard = St.Clipboard.get_default();
        clipboard.set_text(St.ClipboardType.CLIPBOARD, text);
        clipboard.set_text(St.ClipboardType.PRIMARY, text);
    }
    
    _updateStatus(message, isLoading = false) {
        if (this._statusItem) {
            this._statusItem.label.text = `Status: ${message}`;
        }
        
        // Update icon to show loading state
        if (isLoading) {
            this._icon.add_style_class_name('loading');
        } else {
            this._icon.remove_style_class_name('loading');
        }
        
        // Auto-clear status after 5 seconds
        if (!isLoading) {
            GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 5, () => {
                if (this._statusItem) {
                    this._statusItem.label.text = 'Status: Ready';
                }
                return GLib.SOURCE_REMOVE;
            });
        }
    }
    
    _showNotification(title, message) {
        const source = new MessageTray.Source({
            title: 'RH-OTP',
            iconName: 'security-high-symbolic'
        });
        Main.messageTray.add(source);
        
        const notification = new MessageTray.Notification({
            source: source,
            title: title,
            body: message,
            isTransient: true
        });
        source.addNotification(notification);
    }
    
    _openSettings() {
        try {
            // Try to open extension preferences
            this._extension.openPreferences();
        } catch (e) {
            this._showNotification('Settings', 'Extension preferences not available. Configure via gsettings.');
        }
    }
    
    _detectVpnScriptPath() {
        // Try to find vpn-connect script in common locations
        const possiblePaths = [
            GLib.build_filenamev([GLib.get_home_dir(), 'src', 'rh-otp-auto-connect', 'src', 'vpn-connect']),
            GLib.build_filenamev([GLib.get_home_dir(), 'src', 'rh-otp-auto-connect', 'vpn-connect']),
            GLib.build_filenamev([GLib.get_current_dir(), 'vpn-connect']),
            '/usr/local/bin/vpn-connect',
            '/usr/bin/vpn-connect'
        ];

        for (const path of possiblePaths) {
            const file = Gio.File.new_for_path(path);
            if (file.query_exists(null)) {
                return path;
            }
        }

        return '';
    }

    _detectVpnShuttlePath() {
        // Try to find vpn-connect-shuttle script in common locations
        const possiblePaths = [
            GLib.build_filenamev([GLib.get_home_dir(), 'src', 'rh-otp-auto-connect', 'src', 'vpn-connect-shuttle']),
            GLib.build_filenamev([GLib.get_home_dir(), 'src', 'rh-otp-auto-connect', 'vpn-connect-shuttle']),
            GLib.build_filenamev([GLib.get_current_dir(), 'vpn-connect-shuttle']),
            '/usr/local/bin/vpn-connect-shuttle',
            '/usr/bin/vpn-connect-shuttle'
        ];

        for (const path of possiblePaths) {
            const file = Gio.File.new_for_path(path);
            if (file.query_exists(null)) {
                return path;
            }
        }

        return '';
    }
    
    async _connectVPN(type) {
        this._updateStatus(`Connecting VPN (${type})...`, true);

        try {
            // Get auth token
            const token = await this._getAuthToken();
            if (!token) {
                throw new Error('Failed to get authentication token');
            }

            // Call FastAPI endpoint for legacy VPN connect
            const url = `${this._settings.apiUrl}/vpn/connect/${type}`;
            const session = new Soup.Session();
            const message = Soup.Message.new('POST', url);

            // Add authorization header
            message.request_headers.append('Authorization', `Bearer ${token}`);

            // Send request
            const response = await new Promise((resolve, reject) => {
                session.send_async(message, GLib.PRIORITY_DEFAULT, null, (session, result) => {
                    try {
                        const inputStream = session.send_finish(result);
                        const dataInputStream = new Gio.DataInputStream({
                            base_stream: inputStream
                        });

                        let responseText = '';
                        let line;
                        while ((line = dataInputStream.read_line(null)[0]) !== null) {
                            responseText += new TextDecoder().decode(line) + '\n';
                        }

                        if (message.status_code === 200) {
                            resolve(responseText);
                        } else {
                            reject(new Error(`HTTP ${message.status_code}: ${responseText}`));
                        }
                    } catch (e) {
                        reject(e);
                    }
                });
            });

            // Parse response
            const result = JSON.parse(response);

            if (result.success) {
                this._updateStatus(`VPN connected via ${type}`);
                if (this._settings.autoNotifications) {
                    this._showNotification('VPN Connected', `Successfully connected via ${type}`);
                }
            } else {
                throw new Error(result.message || 'VPN connection failed');
            }

            // Update VPN status after connection attempt
            GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
                this._updateVPNStatus().catch(error => {
                    console.log(`RH-OTP: Error updating VPN status: ${error.message}`);
                });
                return GLib.SOURCE_REMOVE;
            });

        } catch (error) {
            log(`RH-OTP VPN Error: ${error.message}`);
            this._updateStatus('VPN connection failed: ' + error.message);
            this._showNotification('VPN Connection Failed', error.message);
        }
    }
    
    async _disconnectVPN() {
        this._updateStatus('Disconnecting VPN...', true);

        try {
            // Get auth token
            const token = await this._getAuthToken();
            if (!token) {
                throw new Error('Failed to get authentication token');
            }

            // Call FastAPI endpoint to disconnect
            const url = `${this._settings.apiUrl}/vpn/disconnect`;
            const session = new Soup.Session();
            const message = Soup.Message.new('POST', url);

            // Add authorization header
            message.request_headers.append('Authorization', `Bearer ${token}`);

            // Send request
            const response = await new Promise((resolve, reject) => {
                session.send_async(message, GLib.PRIORITY_DEFAULT, null, (session, result) => {
                    try {
                        const inputStream = session.send_finish(result);
                        const dataInputStream = new Gio.DataInputStream({
                            base_stream: inputStream
                        });

                        let responseText = '';
                        let line;
                        while ((line = dataInputStream.read_line(null)[0]) !== null) {
                            responseText += new TextDecoder().decode(line) + '\n';
                        }

                        if (message.status_code === 200) {
                            resolve(responseText);
                        } else {
                            reject(new Error(`HTTP ${message.status_code}: ${responseText}`));
                        }
                    } catch (e) {
                        reject(e);
                    }
                });
            });

            // Parse response
            const result = JSON.parse(response);

            if (result.success) {
                this._updateStatus('VPN disconnected');
                if (this._settings.autoNotifications) {
                    this._showNotification('VPN Disconnected', result.message || 'VPN connection terminated');
                }
            } else {
                throw new Error(result.message || 'VPN disconnect failed');
            }

            // Update VPN status after disconnection attempt
            GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
                this._updateVPNStatus().catch(error => {
                    console.log(`RH-OTP: Error updating VPN status: ${error.message}`);
                });
                return GLib.SOURCE_REMOVE;
            });

        } catch (error) {
            log(`RH-OTP VPN Disconnect Error: ${error.message}`);
            this._updateStatus('VPN disconnect failed: ' + error.message);
            this._showNotification('VPN Disconnect Failed', error.message);
        }
    }
    
    async _initializeVPNStatus() {
        if (!this._settings.autoCheckVpnStatus) {
            console.log('RH-OTP: VPN status checking disabled');
            this._isInitializing = false;
            if (this._vpnStatusItem) {
                this._vpnStatusItem.label.text = 'VPN: Status checking disabled';
            }
            return;
        }

        console.log('RH-OTP: Initializing VPN status check via API...');
        this._isInitializing = false;

        // Do initial status check using API
        await this._checkVPNState();
    }
    
    async _checkVPNState() {
        if (!this._settings.autoCheckVpnStatus) {
            console.log('RH-OTP: VPN status checking disabled');
            return;
        }

        console.log('RH-OTP: Checking VPN state via API...');

        try {
            // Get auth token
            const token = await this._getAuthToken();
            if (!token) {
                console.log('RH-OTP: No auth token, cannot check VPN status');
                if (this._vpnStatusItem) {
                    this._vpnStatusItem.label.text = 'VPN: Auth error';
                }
                return;
            }

            // Query the FastAPI /vpn/status endpoint
            const url = `${this._settings.apiUrl}/vpn/status`;
            const statusData = await this._makeAuthenticatedJsonRequest(url, token);

            const isConnected = statusData.connected || false;
            const vpnName = statusData.profile_name || '';
            const vpnStatus = isConnected ? 'Connected' : 'Disconnected';

            console.log(`RH-OTP: VPN Status from API: ${vpnStatus}, Name: ${vpnName}`);

            // Update VPN status in menu
            if (this._vpnStatusItem) {
                const statusText = vpnName ?
                    `VPN: ${vpnStatus} (${vpnName})` :
                    `VPN: ${vpnStatus}`;
                this._vpnStatusItem.label.text = statusText;
                console.log(`RH-OTP: Updated status text to: ${statusText}`);
            }

            // Update menu item sensitivity based on status
            if (this._vpnConnectItem && this._vpnShuttleItem && this._vpnDisconnectItem) {
                this._vpnConnectItem.setSensitive(!isConnected);
                this._vpnShuttleItem.setSensitive(!isConnected);
                this._vpnDisconnectItem.setSensitive(isConnected);
                console.log(`RH-OTP: Updated menu item sensitivity, connected: ${isConnected}`);
            }

        } catch (error) {
            console.log(`RH-OTP VPN Status Error: ${error.message}`);
            if (this._vpnStatusItem) {
                this._vpnStatusItem.label.text = 'VPN: Status unknown';
            }
        }
    }
    
    // Legacy method for compatibility with connect/disconnect callbacks
    async _updateVPNStatus() {
        await this._checkVPNState();
    }
    
    async _runCommand(command) {
        try {
            // Parse command into arguments - handle shell commands properly
            const argv = GLib.shell_parse_argv(command)[1];
            const stdout = await execCommunicate(argv);

            return {
                success: true,
                stdout: stdout,
                stderr: '',
                returncode: 0
            };

        } catch (error) {
            return {
                success: false,
                stdout: '',
                stderr: error.message || 'Command failed',
                returncode: error.code || -1
            };
        }
    }

    async _loadVPNProfiles() {
        try {
            // Clear existing items in submenu
            this._vpnProfileSubmenu.menu.removeAll();

            // Add loading indicator
            const loadingItem = new PopupMenu.PopupMenuItem('Loading profiles...', { reactive: false });
            this._vpnProfileSubmenu.menu.addMenuItem(loadingItem);

            // Get auth token
            const token = await this._getAuthToken();
            if (!token) {
                this._vpnProfileSubmenu.menu.removeAll();
                const errorItem = new PopupMenu.PopupMenuItem('Error: No auth token', { reactive: false });
                this._vpnProfileSubmenu.menu.addMenuItem(errorItem);
                return;
            }

            // Fetch VPN profiles from API
            const url = `${this._settings.apiUrl}/vpn/profiles`;
            const response = await this._makeAuthenticatedJsonRequest(url, token);

            // Response is already parsed JSON
            const profiles = response;

            // DEBUG: Verify profiles are retrieved and print them
            console.log(`RH-OTP: Retrieved ${profiles.length} profiles from API`);
            console.log('RH-OTP: Profiles data:', JSON.stringify(profiles, null, 2));

            // Clear loading indicator
            this._vpnProfileSubmenu.menu.removeAll();

            if (!profiles || profiles.length === 0) {
                const noProfilesItem = new PopupMenu.PopupMenuItem('No profiles available', { reactive: false });
                this._vpnProfileSubmenu.menu.addMenuItem(noProfilesItem);
                return;
            }

            // Group profiles by region for better organization
            const regions = {
                'Americas': ['IAD2', 'RDU2', 'GRU2', 'EGYPT_RDU2'],
                'Europe': ['AMS2', 'BRQ', 'BRQ2', 'LCY', 'FAB', 'TLV', 'TLV2'],
                'Asia-Pacific': ['NRT', 'PEK2', 'PEK2_ALT', 'SIN2', 'SYD', 'PNQ2'],
                'Global': ['GLOBAL']
            };

            // Add profiles organized by region
            for (const [regionName, profileIds] of Object.entries(regions)) {
                const regionProfiles = profiles.filter(p => profileIds.includes(p.id));

                if (regionProfiles.length > 0) {
                    // Add region label
                    const regionLabel = new PopupMenu.PopupMenuItem(regionName, { reactive: false });
                    regionLabel.label.add_style_class_name('popup-subtitle-menu-item');
                    this._vpnProfileSubmenu.menu.addMenuItem(regionLabel);

                    // Add profiles in this region
                    for (const profile of regionProfiles) {
                        // Check if this is the default profile
                        console.log(`RH-OTP: Checking profile ${profile.id}, default is ${this._defaultProfileId}, isDefault: ${this._defaultProfileId && profile.id === this._defaultProfileId}`);
                        const isDefault = this._defaultProfileId && profile.id === this._defaultProfileId;
                        const defaultIndicator = isDefault ? '⭐ ' : '';

                        const profileItem = new PopupMenu.PopupMenuItem(`${defaultIndicator}${profile.name}`);

                        // Left click connects to VPN
                        profileItem.connect('activate', () => {
                            this._connectVPNProfile(profile);
                        });

                        this._vpnProfileSubmenu.menu.addMenuItem(profileItem);
                    }
                }
            }

            // Add any ungrouped profiles at the end
            const groupedIds = Object.values(regions).flat();
            const ungrouped = profiles.filter(p => !groupedIds.includes(p.id));
            if (ungrouped.length > 0) {
                const otherLabel = new PopupMenu.PopupMenuItem('Other', { reactive: false });
                otherLabel.label.add_style_class_name('popup-subtitle-menu-item');
                this._vpnProfileSubmenu.menu.addMenuItem(otherLabel);

                for (const profile of ungrouped) {
                    // Check if this is the default profile
                    const isDefault = this._defaultProfileId && profile.id === this._defaultProfileId;
                    const defaultIndicator = isDefault ? '⭐ ' : '';

                    const profileItem = new PopupMenu.PopupMenuItem(`${defaultIndicator}${profile.name}`);

                    // Left click connects to VPN
                    profileItem.connect('activate', () => {
                        this._connectVPNProfile(profile);
                    });

                    this._vpnProfileSubmenu.menu.addMenuItem(profileItem);
                }
            }

            // Populate the "Set Default VPN Profile" submenu
            this._setDefaultSubmenu.menu.removeAll();

            // Add all profiles to the Set Default submenu (sorted alphabetically)
            const sortedProfiles = [...profiles].sort((a, b) => a.name.localeCompare(b.name));
            for (const profile of sortedProfiles) {
                const isDefault = this._defaultProfileId && profile.id === this._defaultProfileId;
                const defaultIndicator = isDefault ? '⭐ ' : '  ';

                const setDefaultItem = new PopupMenu.PopupMenuItem(`${defaultIndicator}${profile.name}`);
                setDefaultItem.connect('activate', () => {
                    this._setDefaultVPNProfile(profile);
                });

                this._setDefaultSubmenu.menu.addMenuItem(setDefaultItem);
            }

        } catch (error) {
            console.log(`RH-OTP: Error loading VPN profiles: ${error.message}`);
            this._vpnProfileSubmenu.menu.removeAll();
            const errorItem = new PopupMenu.PopupMenuItem(`Error: ${error.message}`, { reactive: false });
            this._vpnProfileSubmenu.menu.addMenuItem(errorItem);
        }
    }

    async _connectVPNProfile(profile) {
        this._updateStatus(`Connecting to ${profile.name}...`, true);

        try {
            // Get auth token
            const token = await this._getAuthToken();
            if (!token) {
                throw new Error('Failed to get authentication token');
            }

            // Call the FastAPI endpoint to connect
            const url = `${this._settings.apiUrl}/vpn/connect/${profile.id}`;
            const session = new Soup.Session();
            const message = Soup.Message.new('POST', url);

            // Add authorization header
            message.request_headers.append('Authorization', `Bearer ${token}`);

            // Send request
            const response = await new Promise((resolve, reject) => {
                session.send_async(message, GLib.PRIORITY_DEFAULT, null, (session, result) => {
                    try {
                        const inputStream = session.send_finish(result);
                        const dataInputStream = new Gio.DataInputStream({
                            base_stream: inputStream
                        });

                        let responseText = '';
                        let line;
                        while ((line = dataInputStream.read_line(null)[0]) !== null) {
                            responseText += new TextDecoder().decode(line) + '\n';
                        }

                        if (message.status_code === 200) {
                            resolve(responseText);
                        } else {
                            reject(new Error(`HTTP ${message.status_code}: ${responseText}`));
                        }
                    } catch (e) {
                        reject(e);
                    }
                });
            });

            // Parse response
            const result = JSON.parse(response);

            if (result.success) {
                this._updateStatus(`Connected to ${profile.name}`);
                if (this._settings.autoNotifications) {
                    this._showNotification('VPN Connected', `Successfully connected to ${profile.name}`);
                }

                // Update VPN status after connection
                GLib.timeout_add_seconds(GLib.PRIORITY_DEFAULT, 2, () => {
                    this._checkVPNState().catch(error => {
                        console.log(`RH-OTP: Error updating VPN status: ${error.message}`);
                    });
                    return GLib.SOURCE_REMOVE;
                });
            } else {
                throw new Error(result.message || 'Connection failed');
            }

        } catch (error) {
            console.log(`RH-OTP: Error connecting to VPN profile: ${error.message}`);
            this._updateStatus(`Failed to connect to ${profile.name}`);
            this._showNotification('VPN Connection Failed', error.message);
        }
    }

    async _setDefaultVPNProfile(profile) {
        try {
            // Get auth token
            const token = await this._getAuthToken();
            if (!token) {
                throw new Error('Failed to get authentication token');
            }

            // Call the FastAPI endpoint to set default VPN
            const url = `${this._settings.apiUrl}/vpn/default`;
            const session = new Soup.Session();
            const message = Soup.Message.new('POST', url);

            // Add authorization header
            message.request_headers.append('Authorization', `Bearer ${token}`);

            // Add request body
            const requestBody = JSON.stringify({ profile_id: profile.id });
            message.set_request_body_from_bytes('application/json', new GLib.Bytes(requestBody));

            // Send request
            const response = await new Promise((resolve, reject) => {
                session.send_async(message, GLib.PRIORITY_DEFAULT, null, (session, result) => {
                    try {
                        const inputStream = session.send_finish(result);
                        const dataInputStream = new Gio.DataInputStream({
                            base_stream: inputStream
                        });

                        let responseText = '';
                        let line;
                        while ((line = dataInputStream.read_line(null)[0]) !== null) {
                            responseText += new TextDecoder().decode(line) + '\n';
                        }

                        if (message.status_code === 200) {
                            resolve(responseText);
                        } else {
                            reject(new Error(`HTTP ${message.status_code}: ${responseText}`));
                        }
                    } catch (e) {
                        reject(e);
                    }
                });
            });

            // Parse response
            const result = JSON.parse(response);

            if (result.success) {
                // Update local state
                this._defaultProfileId = profile.id;
                this._defaultProfileUuid = result.uuid;

                console.log(`RH-OTP: Default VPN set to ${profile.name}`);

                if (this._settings.autoNotifications) {
                    this._showNotification('Default VPN Updated', `${profile.name} is now the default VPN`);
                }

                // Refresh the profile menu to show updated default indicator
                this._loadVPNProfiles();
            } else {
                throw new Error(result.message || 'Failed to set default VPN');
            }

        } catch (error) {
            console.log(`RH-OTP: Error setting default VPN: ${error.message}`);
            this._showNotification('Set Default VPN Failed', error.message);
        }
    }


    destroy() {
        // Clean up interval
        if (this._vpnCheckInterval) {
            GLib.source_remove(this._vpnCheckInterval);
            this._vpnCheckInterval = null;
        }
        
        if (this._gsettings) {
            this._gsettings = null;
        }
        super.destroy();
    }
});

export default class RHOTPExtension extends Extension {
    enable() {
        log('RH-OTP: Enabling extension');
        this._indicator = new RHOTPIndicator(this);
        Main.panel.addToStatusArea('rh-otp-indicator', this._indicator);
    }
    
    disable() {
        log('RH-OTP: Disabling extension');
        if (this._indicator) {
            this._indicator.destroy();
            this._indicator = null;
        }
    }
}