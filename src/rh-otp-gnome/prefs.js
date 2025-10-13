import { ExtensionPreferences } from 'resource:///org/gnome/shell/extensions/prefs.js';
import { gettext as _ } from 'resource:///org/gnome/shell/extensions/extension.js';

import GObject from 'gi://GObject';
import Gtk from 'gi://Gtk';
import Gio from 'gi://Gio';
import GLib from 'gi://GLib';
import Soup from 'gi://Soup';
import Adw from 'gi://Adw';

export default class RHOTPPreferences extends ExtensionPreferences {
    fillPreferencesWindow(window) {
        const settings = this.getSettings();
    
    // Create main container
    const widget = new Gtk.Box({
        orientation: Gtk.Orientation.VERTICAL,
        spacing: 20,
        margin_top: 20,
        margin_bottom: 20,
        margin_start: 20,
        margin_end: 20
    });
    
    // Title
    const titleLabel = new Gtk.Label({
        label: '<b>Red Hat OTP Auto-Connect Settings</b>',
        use_markup: true,
        halign: Gtk.Align.START
    });
    widget.append(titleLabel);
    
    // API URL setting
    const urlBox = new Gtk.Box({
        orientation: Gtk.Orientation.HORIZONTAL,
        spacing: 10
    });
    
    const urlLabel = new Gtk.Label({
        label: 'API URL:',
        width_chars: 15,
        halign: Gtk.Align.START
    });
    
    const urlEntry = new Gtk.Entry({
        text: settings.get_string('api-url'),
        hexpand: true
    });
    
    urlEntry.connect('changed', () => {
        settings.set_string('api-url', urlEntry.get_text());
    });
    
    urlBox.append(urlLabel);
    urlBox.append(urlEntry);
    widget.append(urlBox);
    
    // Headless mode setting
    const headlessBox = new Gtk.Box({
        orientation: Gtk.Orientation.HORIZONTAL,
        spacing: 10
    });
    
    const headlessLabel = new Gtk.Label({
        label: 'Use headless mode:',
        width_chars: 15,
        halign: Gtk.Align.START
    });
    
    const headlessSwitch = new Gtk.Switch({
        active: settings.get_boolean('headless'),
        halign: Gtk.Align.END,
        hexpand: true
    });
    
    headlessSwitch.connect('notify::active', () => {
        settings.set_boolean('headless', headlessSwitch.get_active());
    });
    
    headlessBox.append(headlessLabel);
    headlessBox.append(headlessSwitch);
    widget.append(headlessBox);
    
    // Auto-notifications setting
    const notifBox = new Gtk.Box({
        orientation: Gtk.Orientation.HORIZONTAL,
        spacing: 10
    });
    
    const notifLabel = new Gtk.Label({
        label: 'Show notifications:',
        width_chars: 15,
        halign: Gtk.Align.START
    });
    
    const notifSwitch = new Gtk.Switch({
        active: settings.get_boolean('auto-notifications'),
        halign: Gtk.Align.END,
        hexpand: true
    });
    
    notifSwitch.connect('notify::active', () => {
        settings.set_boolean('auto-notifications', notifSwitch.get_active());
    });
    
    notifBox.append(notifLabel);
    notifBox.append(notifSwitch);
    widget.append(notifBox);
    
    // Default context setting
    const contextBox = new Gtk.Box({
        orientation: Gtk.Orientation.HORIZONTAL,
        spacing: 10
    });
    
    const contextLabel = new Gtk.Label({
        label: 'Default context:',
        width_chars: 15,
        halign: Gtk.Align.START
    });
    
    const contextCombo = new Gtk.ComboBoxText();
    contextCombo.append_text('associate');
    contextCombo.append_text('jdoeEphemeral');
    contextCombo.set_active_id(settings.get_string('default-context'));
    
    contextCombo.connect('changed', () => {
        settings.set_string('default-context', contextCombo.get_active_text());
    });
    
    contextBox.append(contextLabel);
    contextBox.append(contextCombo);
    widget.append(contextBox);
    
    // Show context menu setting
    const menuBox = new Gtk.Box({
        orientation: Gtk.Orientation.HORIZONTAL,
        spacing: 10
    });
    
    const menuLabel = new Gtk.Label({
        label: 'Show context menu:',
        width_chars: 15,
        halign: Gtk.Align.START
    });
    
    const menuSwitch = new Gtk.Switch({
        active: settings.get_boolean('show-context-menu'),
        halign: Gtk.Align.END,
        hexpand: true
    });
    
    menuSwitch.connect('notify::active', () => {
        settings.set_boolean('show-context-menu', menuSwitch.get_active());
    });
    
    menuBox.append(menuLabel);
    menuBox.append(menuSwitch);
    widget.append(menuBox);
    
    // VPN Settings Section
    const vpnTitleLabel = new Gtk.Label({
        label: '<b>VPN Settings</b>',
        use_markup: true,
        halign: Gtk.Align.START,
        margin_top: 20
    });
    widget.append(vpnTitleLabel);
    
    // VPN Script Path
    const vpnScriptBox = new Gtk.Box({
        orientation: Gtk.Orientation.HORIZONTAL,
        spacing: 10
    });
    
    const vpnScriptLabel = new Gtk.Label({
        label: 'VPN script path:',
        width_chars: 15,
        halign: Gtk.Align.START
    });
    
    const vpnScriptEntry = new Gtk.Entry({
        text: settings.get_string('vpn-script-path'),
        hexpand: true,
        placeholder_text: '/path/to/vpn-connect'
    });
    
    vpnScriptEntry.connect('changed', () => {
        settings.set_string('vpn-script-path', vpnScriptEntry.get_text());
    });
    
    const vpnScriptButton = new Gtk.Button({
        label: 'Browse...'
    });
    
    vpnScriptButton.connect('clicked', () => {
        _browseForFile(vpnScriptEntry, 'Select VPN Connect Script');
    });
    
    vpnScriptBox.append(vpnScriptLabel);
    vpnScriptBox.append(vpnScriptEntry);
    vpnScriptBox.append(vpnScriptButton);
    widget.append(vpnScriptBox);
    
    // VPN Shuttle Path
    const vpnShuttleBox = new Gtk.Box({
        orientation: Gtk.Orientation.HORIZONTAL,
        spacing: 10
    });
    
    const vpnShuttleLabel = new Gtk.Label({
        label: 'VPN shuttle path:',
        width_chars: 15,
        halign: Gtk.Align.START
    });
    
    const vpnShuttleEntry = new Gtk.Entry({
        text: settings.get_string('vpn-shuttle-path'),
        hexpand: true,
        placeholder_text: '/path/to/vpn-connect-shuttle'
    });
    
    vpnShuttleEntry.connect('changed', () => {
        settings.set_string('vpn-shuttle-path', vpnShuttleEntry.get_text());
    });
    
    const vpnShuttleButton = new Gtk.Button({
        label: 'Browse...'
    });
    
    vpnShuttleButton.connect('clicked', () => {
        _browseForFile(vpnShuttleEntry, 'Select VPN Shuttle Script');
    });
    
    vpnShuttleBox.append(vpnShuttleLabel);
    vpnShuttleBox.append(vpnShuttleEntry);
    vpnShuttleBox.append(vpnShuttleButton);
    widget.append(vpnShuttleBox);
    
    // Auto-check VPN status
    const vpnStatusBox = new Gtk.Box({
        orientation: Gtk.Orientation.HORIZONTAL,
        spacing: 10
    });
    
    const vpnStatusLabel = new Gtk.Label({
        label: 'Auto-check VPN:',
        width_chars: 15,
        halign: Gtk.Align.START
    });
    
    const vpnStatusSwitch = new Gtk.Switch({
        active: settings.get_boolean('auto-check-vpn-status'),
        halign: Gtk.Align.END,
        hexpand: true
    });
    
    vpnStatusSwitch.connect('notify::active', () => {
        settings.set_boolean('auto-check-vpn-status', vpnStatusSwitch.get_active());
    });
    
    vpnStatusBox.append(vpnStatusLabel);
    vpnStatusBox.append(vpnStatusSwitch);
    widget.append(vpnStatusBox);
    
    // Service status
    const statusBox = new Gtk.Box({
        orientation: Gtk.Orientation.VERTICAL,
        spacing: 10,
        margin_top: 20
    });
    
    const statusLabel = new Gtk.Label({
        label: '<b>Service Status</b>',
        use_markup: true,
        halign: Gtk.Align.START
    });
    
    const statusText = new Gtk.Label({
        label: 'Checking service status...',
        halign: Gtk.Align.START
    });
    
        // Check service status
        this._checkServiceStatus(statusText, settings.get_string('api-url'));
        
        statusBox.append(statusLabel);
        statusBox.append(statusText);
        widget.append(statusBox);
        
        // Create page and add to window
        const page = new Adw.PreferencesPage({
            title: _('General'),
            icon_name: 'system-run-symbolic',
        });
        page.add(widget);
        window.add(page);
    }

    _browseForFile(entry, title) {
        const dialog = new Gtk.FileChooserDialog({
            title: title,
            action: Gtk.FileChooserAction.OPEN,
            transient_for: entry.get_root()
        });
        
        dialog.add_button('Cancel', Gtk.ResponseType.CANCEL);
        dialog.add_button('Open', Gtk.ResponseType.ACCEPT);
        
        dialog.connect('response', (dialog, response) => {
            if (response === Gtk.ResponseType.ACCEPT) {
                const file = dialog.get_file();
                if (file) {
                    entry.set_text(file.get_path());
                }
            }
            dialog.destroy();
        });
        
        dialog.show();
    }

    _checkServiceStatus(statusLabel, apiUrl) {
        try {
            const session = new Soup.Session();
            const message = Soup.Message.new('GET', `${apiUrl}/health`);
            
            session.send_async(message, GLib.PRIORITY_DEFAULT, null, (session, result) => {
                try {
                    session.send_finish(result);
                    if (message.status_code === 200) {
                        statusLabel.set_text('✅ RHOTP service is running');
                    } else if (message.status_code === 401) {
                        statusLabel.set_text('🔒 RHOTP service running (authentication required)');
                    } else {
                        statusLabel.set_text(`❌ Service error: HTTP ${message.status_code}`);
                    }
                } catch (e) {
                    statusLabel.set_text('❌ RHOTP service is not running');
                }
            });
        } catch (e) {
            statusLabel.set_text('❌ Could not check service status');
        }
    }
}