/**
 * Global Bluetooth Printer Manager
 * Manages persistent Bluetooth printer connections across all pages
 */

class BluetoothPrinterManager {
    constructor() {
        this.connectedPrinters = new Map();
        this.connectionStatus = 'disconnected';
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        this.reconnectDelay = 2000;
        this.autoReconnectInProgress = false;
        this.autoReconnectAttempted = false;
        
        // Initialize from localStorage
        this.loadPersistedConnections();
        
        // Set up connection monitoring
        this.setupConnectionMonitoring();
        
        // Handle page visibility changes
        this.setupPageVisibilityHandling();
    }

    // Load persisted connections from localStorage
    loadPersistedConnections() {
        try {
            const savedConnections = localStorage.getItem('bluetooth-printer-connections');
            console.log('🔵 [DEBUG] Checking localStorage for saved connections...');
            console.log('🔵 [DEBUG] Raw localStorage value:', savedConnections);
            
            if (savedConnections) {
                const connections = JSON.parse(savedConnections);
                console.log('🔵 [DEBUG] Parsed connections:', connections);
                console.log('🔵 [DEBUG] Number of saved connections:', connections.length);
                
                if (connections.length === 0) {
                    console.log('🔵 No saved printer connections found');
                    return;
                }
                
                // Store connection info for auto-reconnection
                connections.forEach((connection, index) => {
                    console.log(`🔵 [DEBUG] Loading printer ${index + 1}:`, {
                        id: connection.id,
                        name: connection.name,
                        deviceId: connection.deviceId,
                        connectedAt: connection.connectedAt
                    });
                    this.connectedPrinters.set(connection.id, {
                        ...connection,
                        device: null, // Will be reconnected when needed
                        server: null,
                        status: 'disconnected'
                    });
                });
                
                console.log(`🔵 Loaded ${connections.length} printer(s) from localStorage`);
                console.log('🔵 [DEBUG] Current connectedPrinters Map size:', this.connectedPrinters.size);
                
                // Attempt to reconnect to previously paired devices
                // Delay to ensure page is ready and Bluetooth API is available
                setTimeout(() => {
                    console.log('🔵 [DEBUG] Starting auto-reconnect attempt from loadPersistedConnections...');
                    console.log('🔵 [DEBUG] Bluetooth API available:', !!navigator.bluetooth);
                    console.log('🔵 [DEBUG] getDevices() available:', typeof navigator.bluetooth?.getDevices === 'function');
                    // Only attempt if we haven't already attempted
                    if (!this.autoReconnectAttempted) {
                this.attemptReconnectAll();
                    } else {
                        console.log('🔵 [DEBUG] Auto-reconnect already attempted, skipping...');
                    }
                }, 2000);
            } else {
                console.log('🔵 No saved printer connections in localStorage');
                console.log('🔵 [DEBUG] localStorage.getItem("bluetooth-printer-connections") returned:', savedConnections);
            }
        } catch (error) {
            console.error('❌ Error loading persisted connections:', error);
            console.error('❌ [DEBUG] Error stack:', error.stack);
        }
    }

    // Save connections to localStorage
    savePersistedConnections() {
        try {
            const connections = Array.from(this.connectedPrinters.values()).map(printer => ({
                id: printer.id,
                name: printer.name,
                deviceId: printer.deviceId,
                connectedAt: printer.connectedAt,
                lastUsed: printer.lastUsed
            }));
            
            localStorage.setItem('bluetooth-printer-connections', JSON.stringify(connections));
            console.log('🔵 [DEBUG] Saved printer connections to localStorage:', connections);
            console.log('🔵 [DEBUG] Each connection saved with:', connections.map(c => ({
                id: c.id,
                name: c.name,
                deviceId: c.deviceId,
                deviceIdType: typeof c.deviceId
            })));
        } catch (error) {
            console.error('Error saving connections:', error);
        }
    }

    // Add a new Bluetooth printer connection
    async addPrinter(device, server) {
        try {
            const deviceName = device.name || 'Bluetooth Printer';
            const printerId = `ble_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
            
            const printerData = {
                id: printerId,
                name: deviceName,
                deviceId: device.id,
                device: device,
                server: server,
                status: 'connected',
                connectedAt: new Date().toISOString(),
                lastUsed: new Date().toISOString()
            };

            this.connectedPrinters.set(printerId, printerData);
            this.savePersistedConnections();
            
            // Set up device event listeners
            this.setupDeviceEventListeners(device, printerId);
            
            console.log(`Added printer: ${deviceName} (${printerId})`);
            return printerId;
            
        } catch (error) {
            console.error('Error adding printer:', error);
            throw error;
        }
    }

    // Set up device event listeners for connection monitoring
    setupDeviceEventListeners(device, printerId) {
        device.addEventListener('gattserverdisconnected', () => {
            console.log(`Printer ${printerId} disconnected`);
            this.handleDisconnection(printerId);
        });
    }

    // Handle printer disconnection
    handleDisconnection(printerId) {
        const printer = this.connectedPrinters.get(printerId);
        if (printer) {
            printer.status = 'disconnected';
            printer.device = null;
            printer.server = null;
            
            // Attempt to reconnect
            this.attemptReconnection(printerId);
        }
    }

    // Attempt to reconnect all previously paired devices
    async attemptReconnectAll() {
        // Prevent multiple simultaneous reconnection attempts
        if (this.autoReconnectInProgress) {
            console.log('🔄 Auto-reconnect already in progress, skipping...');
            return;
        }
        
        // Mark as attempted to prevent duplicate calls
        if (this.autoReconnectAttempted) {
            console.log('🔄 Auto-reconnect already attempted, skipping duplicate call...');
            return;
        }
        
        this.autoReconnectInProgress = true;
        this.autoReconnectAttempted = true;
        
        console.log('🔄 Attempting to reconnect all previously paired devices...');
        
        // Check if Bluetooth is available
        if (!navigator.bluetooth) {
            console.error('❌ Bluetooth API not available in this browser');
            this.autoReconnectInProgress = false;
            return;
        }
        
        // Check if getDevices is supported
        if (typeof navigator.bluetooth.getDevices !== 'function') {
            console.warn('⚠️ getDevices() not supported - cannot auto-connect without user interaction');
            console.warn('⚠️ Auto-connect requires getDevices() API which is available in Chrome/Edge');
            this.autoReconnectInProgress = false;
            return;
        }
        
        const disconnectedPrinters = Array.from(this.connectedPrinters.entries())
            .filter(([printerId, printer]) => printer.status === 'disconnected' || !printer.device);
        
        if (disconnectedPrinters.length === 0) {
            console.log('✅ No disconnected printers to reconnect (all already connected)');
            this.autoReconnectInProgress = false;
            return;
        }
        
        console.log(`🔵 Found ${disconnectedPrinters.length} disconnected printer(s) to reconnect:`, 
            disconnectedPrinters.map(([id, p]) => `${p.name} (ID: ${p.deviceId})`));
        
        // Get all paired devices first
        try {
            console.log('🔵 [DEBUG] Calling getDevices() to retrieve previously paired devices...');
            console.log('🔵 [DEBUG] Bluetooth API check:', {
                available: !!navigator.bluetooth,
                hasGetDevices: typeof navigator.bluetooth?.getDevices === 'function'
            });
            
            const pairedDevices = await navigator.bluetooth.getDevices();
            console.log(`🔵 [DEBUG] getDevices() returned ${pairedDevices.length} paired device(s)`);
            
            if (pairedDevices.length > 0) {
                console.log(`🔵 [DEBUG] Paired devices found:`);
                pairedDevices.forEach((d, index) => {
                    console.log(`  ${index + 1}. Name: "${d.name || 'Unknown'}", ID: "${d.id}"`);
                    console.log(`     GATT connected: ${d.gatt?.connected || false}`);
                });
            } else {
                console.warn('⚠️ [DEBUG] No paired devices found in getDevices()!');
                console.warn('⚠️ This means the browser does not remember previously paired devices.');
                console.warn('⚠️ Possible reasons:');
                console.warn('   1. Devices were not previously paired via requestDevice()');
                console.warn('   2. Browser cache/cookies were cleared');
                console.warn('   3. Browser doesn\'t support persistent device pairing');
                console.warn('   4. Device needs to be re-paired manually');
                console.warn('');
                console.warn('🔵 [DEBUG] Saved printer connections from localStorage:');
                disconnectedPrinters.forEach(([id, p]) => {
                    console.warn(`   - "${p.name}" (ID: ${p.deviceId})`);
                });
                console.warn('');
                console.warn('⚠️ Auto-connect cannot work without getDevices() returning devices.');
                console.warn('⚠️ User will need to manually reconnect the printer.');
                this.autoReconnectInProgress = false;
                return;
            }
            
            // Reconnect printers sequentially with delays to avoid conflicts
            let reconnectPromises = [];
            for (let i = 0; i < disconnectedPrinters.length; i++) {
                const [printerId, printer] = disconnectedPrinters[i];
                const reconnectPromise = new Promise((resolve) => {
                    setTimeout(async () => {
                        try {
                            console.log(`🔄 [${i + 1}/${disconnectedPrinters.length}] Attempting auto-reconnect for ${printer.name}...`);
                            console.log(`   Looking for device ID: ${printer.deviceId}`);
                            await this.attemptReconnection(printerId, false); // false = auto-connect, no picker
                            resolve(true);
                        } catch (error) {
                            console.error(`❌ Auto-reconnect failed for ${printer.name}:`, error.message);
                            resolve(false);
                        }
                    }, i * 1500); // Stagger by 1.5 seconds each
                });
                reconnectPromises.push(reconnectPromise);
            }
            
            // Wait for all reconnection attempts to complete
            await Promise.all(reconnectPromises);
            console.log('✅ Auto-reconnect attempts completed');
            
        } catch (error) {
            console.error('❌ Error getting paired devices:', error);
            console.error('   Error type:', error.name);
            console.error('   Error message:', error.message);
            console.error('❌ Auto-connect cannot proceed without getDevices() access');
        } finally {
            this.autoReconnectInProgress = false;
        }
    }

    // Attempt to reconnect a disconnected printer
    async attemptReconnection(printerId, showPicker = false) {
        const printer = this.connectedPrinters.get(printerId);
        if (!printer) {
            return;
        }

        console.log(`Attempting to reconnect printer ${printerId}: ${printer.name}`);

        try {
            // First, try to get previously paired devices without showing picker
            let device = null;
            
            // Only use getDevices() for auto-connect (no picker)
            if (!showPicker && navigator.bluetooth && typeof navigator.bluetooth.getDevices === 'function') {
            try {
                const pairedDevices = await navigator.bluetooth.getDevices();
                    console.log(`🔵 getDevices() returned ${pairedDevices.length} paired device(s)`);
                    
                    if (pairedDevices.length > 0) {
                        console.log(`🔵 Paired devices:`, pairedDevices.map(d => `${d.name} (${d.id})`));
                    }
                    
                    // Find matching device by ID first (most reliable), then by name
                    console.log(`🔍 Looking for device with ID: ${printer.deviceId} or name: ${printer.name}`);
                    
                    // Try exact ID match first
                    device = pairedDevices.find(d => {
                        if (d.id === printer.deviceId) {
                            console.log(`  ✅ Exact ID match found: ${d.name} (${d.id})`);
                            return true;
                        }
                        return false;
                    });
                    
                    // If no exact ID match, try name match
                    if (!device) {
                        device = pairedDevices.find(d => {
                            if (d.name && printer.name && d.name.toLowerCase() === printer.name.toLowerCase()) {
                                console.log(`  ✅ Name match found: ${d.name} (${d.id})`);
                                return true;
                            }
                            return false;
                        });
                    }
                    
                    // If still no match, log all devices for debugging
                    if (!device) {
                        console.log(`  ❌ [DEBUG] No matching device found for printer "${printer.name}"`);
                        console.log(`  ❌ [DEBUG] Saved device info:`, {
                            name: printer.name,
                            deviceId: printer.deviceId,
                            deviceIdType: typeof printer.deviceId,
                            deviceIdLength: printer.deviceId?.length
                        });
                        console.log(`  ❌ [DEBUG] Available paired devices:`);
                        pairedDevices.forEach((d, index) => {
                            console.log(`    ${index + 1}. Device: ${d.name || 'Unknown'}`);
                            console.log(`       ID: ${d.id}`);
                            console.log(`       ID Type: ${typeof d.id}`);
                            console.log(`       ID Length: ${d.id?.length}`);
                            console.log(`       ID Match: ${d.id === printer.deviceId}`);
                            console.log(`       ID Match (string): ${String(d.id) === String(printer.deviceId)}`);
                            console.log(`       Name Match: ${d.name === printer.name}`);
                            console.log(`       Name Match (case-insensitive): ${d.name?.toLowerCase() === printer.name?.toLowerCase()}`);
                        });
                        console.log(`  ❌ [DEBUG] Device ID comparison details:`, {
                            savedDeviceId: printer.deviceId,
                            savedDeviceIdString: String(printer.deviceId),
                            savedDeviceIdTrimmed: String(printer.deviceId).trim(),
                            pairedDeviceIds: pairedDevices.map(d => d.id),
                            pairedDeviceIdStrings: pairedDevices.map(d => String(d.id))
                        });
                    }
                    
                    if (device) {
                        console.log(`✅ Found paired device for ${printer.name}!`);
                        console.log(`   Device ID: ${device.id}`);
                        console.log(`   Device name: ${device.name}`);
                        console.log(`   Already connected: ${device.gatt?.connected || false}`);
                    } else {
                        console.log(`❌ Device not found in paired devices for ${printer.name}`);
                        console.log(`   Expected ID: ${printer.deviceId}`);
                        console.log(`   Expected name: ${printer.name}`);
                        console.log(`   Available devices:`, pairedDevices.map(d => `${d.name} (${d.id})`));
                    }
            } catch (error) {
                    console.error('❌ getDevices() failed:', error);
                    console.error('   Error details:', error.message);
                }
            } else {
                if (showPicker) {
                    console.log('ℹ️ showPicker is true, skipping getDevices()');
                } else if (!navigator.bluetooth) {
                    console.error('❌ Bluetooth API not available');
                } else {
                    console.error('❌ getDevices() not supported in this browser');
                }
            }

            // Only use requestDevice if showPicker is true (for manual reconnection)
            if (!device && showPicker) {
                console.log(`Requesting device selection for ${printer.name} (manual reconnection)`);
                try {
                device = await navigator.bluetooth.requestDevice({
                    acceptAllDevices: true,
                    optionalServices: [
                        '000018f0-0000-1000-8000-00805f9b34fb',
                        '00001800-0000-1000-8000-00805f9b34fb',
                        '00001801-0000-1000-8000-00805f9b34fb',
                        '00001101-0000-1000-8000-00805f9b34fb',
                        '0000ffe0-0000-1000-8000-00805f9b34fb',
                        '0000ffe1-0000-1000-8000-00805f9b34fb'
                    ]
                });
                } catch (error) {
                    console.log('requestDevice() failed or cancelled:', error.message);
                    return; // User cancelled or error occurred
                }
            }

            // If we have a device, try to connect
            if (device) {
                // Verify it's the correct device
                if (device.id === printer.deviceId || device.name === printer.name) {
                    try {
                        // Check if already connected
                        if (device.gatt && device.gatt.connected) {
                            console.log(`✅ Device ${printer.name} is already connected!`);
                            printer.device = device;
                            printer.server = device.gatt;
                            printer.status = 'connected';
                            printer.lastUsed = new Date().toISOString();
                            this.setupDeviceEventListeners(device, printerId);
                            this.notifyConnectionStatus('reconnected', printer);
                            this.savePersistedConnections();
                            
                            // Dispatch event for UI update
                            document.dispatchEvent(new CustomEvent('bluetoothPrinterStatus', {
                                detail: { type: 'reconnected', printer, status: this.getConnectionStatus() }
                            }));
                            
                            return;
                        }

                        // Connect to GATT server
                        console.log(`🔗 Connecting to GATT server for ${printer.name}...`);
                        console.log(`   Device ID: ${device.id}`);
                        console.log(`   Device name: ${device.name}`);
                        
                const server = await device.gatt.connect();
                        console.log(`✅ Connected to GATT server for ${printer.name}`);
                        
                printer.device = device;
                printer.server = server;
                printer.status = 'connected';
                printer.lastUsed = new Date().toISOString();
                
                this.setupDeviceEventListeners(device, printerId);
                
                        console.log(`✅ Successfully reconnected printer ${printerId}: ${printer.name}`);
                this.notifyConnectionStatus('reconnected', printer);
                this.savePersistedConnections();
                        
                        // Dispatch event for UI update
                        document.dispatchEvent(new CustomEvent('bluetoothPrinterStatus', {
                            detail: { type: 'reconnected', printer, status: this.getConnectionStatus() }
                        }));
                    } catch (connectError) {
                        console.error(`❌ Failed to connect to device ${printer.name}:`, connectError);
                        console.error(`   Error type: ${connectError.name}`);
                        console.error(`   Error message: ${connectError.message}`);
                        // Don't show picker on auto-connect failure, just log it
                        if (!showPicker) {
                            console.log(`⚠️ Auto-connect failed for ${printer.name}. User can manually reconnect if needed.`);
                        } else {
                            throw connectError;
                        }
                    }
                } else {
                    console.log(`Device found but doesn't match printer ${printerId} (expected: ${printer.deviceId}, got: ${device.id})`);
                }
            } else {
                // No device found - this is expected if device is not paired or not in range
                if (!showPicker) {
                    console.log(`Auto-connect skipped for ${printer.name} - device not found in paired devices`);
                }
            }
        } catch (error) {
            console.error(`Reconnection attempt failed for printer ${printerId}:`, error.message);
            // Only throw if it's a manual reconnection attempt
            if (showPicker) {
                throw error;
            }
        }
    }

    // Set up connection monitoring
    setupConnectionMonitoring() {
        // Check connection status every 30 seconds
        setInterval(() => {
            this.checkConnections();
        }, 30000);
    }

    // Check all connections
    async checkConnections() {
        for (const [printerId, printer] of this.connectedPrinters) {
            if (printer.status === 'connected' && printer.device) {
                try {
                    // Check if device is still connected
                    if (!printer.device.gatt.connected) {
                        this.handleDisconnection(printerId);
                    }
                } catch (error) {
                    console.log(`Connection check failed for printer ${printerId}:`, error);
                    this.handleDisconnection(printerId);
                }
            }
        }
    }

    // Set up page visibility handling
    setupPageVisibilityHandling() {
        document.addEventListener('visibilitychange', () => {
            if (!document.hidden) {
                // Page became visible, check connections and attempt reconnection
                console.log('🔄 Page became visible, checking connections...');
                this.checkConnections();
                
                // Reset auto-reconnect flag to allow reconnection attempts
                // (but wait a bit to avoid immediate duplicate calls)
                setTimeout(() => {
                    this.autoReconnectAttempted = false;
                    if (this.connectedPrinters.size > 0) {
                        const disconnectedCount = Array.from(this.connectedPrinters.values())
                            .filter(p => p.status === 'disconnected' || !p.device).length;
                        if (disconnectedCount > 0) {
                            console.log(`🔄 Found ${disconnectedCount} disconnected printer(s), attempting reconnection...`);
                            this.attemptReconnectAll();
                        }
                    }
                }, 1000);
            }
        });

        // Handle page load - attempt to reconnect previously paired devices
        // Note: We don't call attemptReconnectAll() here because it's already called
        // from loadPersistedConnections() after a delay. This prevents duplicate calls.
        window.addEventListener('load', () => {
            console.log('🔄 Page loaded, connections will be checked by loadPersistedConnections...');
        });
        
        // Also attempt auto-connect when DOM is ready (faster than load event)
        // But only if we haven't already attempted
        if (document.readyState === 'loading') {
            document.addEventListener('DOMContentLoaded', () => {
                console.log('🔄 DOM ready, checking if auto-reconnect is needed...');
                // Delay to allow loadPersistedConnections to run first
                setTimeout(() => {
                    if (!this.autoReconnectAttempted && this.connectedPrinters.size > 0) {
                        const disconnectedCount = Array.from(this.connectedPrinters.values())
                            .filter(p => p.status === 'disconnected' || !p.device).length;
                        if (disconnectedCount > 0) {
                            console.log(`🔄 Found ${disconnectedCount} disconnected printer(s) on DOM ready, attempting reconnection...`);
                            this.attemptReconnectAll();
                        }
                    }
                }, 2500); // Slightly longer than loadPersistedConnections delay
            });
        } else {
            // DOM already loaded
            console.log('🔄 DOM already loaded, checking if auto-reconnect is needed...');
            setTimeout(() => {
                if (!this.autoReconnectAttempted && this.connectedPrinters.size > 0) {
                    const disconnectedCount = Array.from(this.connectedPrinters.values())
                        .filter(p => p.status === 'disconnected' || !p.device).length;
                    if (disconnectedCount > 0) {
                        console.log(`🔄 Found ${disconnectedCount} disconnected printer(s), attempting reconnection...`);
                        this.attemptReconnectAll();
                    }
                }
            }, 2500);
        }

        // Handle beforeunload to clean up connections
        window.addEventListener('beforeunload', () => {
            console.log('Page unloading, cleaning up connections...');
            // Note: We don't disconnect here as we want to maintain connections
        });
    }

    // Get all connected printers
    getConnectedPrinters() {
        return Array.from(this.connectedPrinters.values()).filter(printer => 
            printer.status === 'connected' && printer.device && printer.server
        );
    }

    // Get printer by ID
    getPrinter(printerId) {
        return this.connectedPrinters.get(printerId);
    }

    // Print to a specific printer
    async printToPrinter(printerId, content) {
        const printer = this.connectedPrinters.get(printerId);
        if (!printer || printer.status !== 'connected') {
            throw new Error('Printer not connected');
        }

        try {
            const success = await this.sendPrintData(printer, content);
            if (success) {
                printer.lastUsed = new Date().toISOString();
                this.savePersistedConnections();
            }
            return success;
        } catch (error) {
            console.error(`Print failed for printer ${printerId}:`, error);
            throw error;
        }
    }

    // Print to all connected printers
    async printToAllPrinters(content) {
        const connectedPrinters = this.getConnectedPrinters();
        if (connectedPrinters.length === 0) {
            throw new Error('No printers connected');
        }

        const results = [];
        for (const printer of connectedPrinters) {
            try {
                const success = await this.printToPrinter(printer.id, content);
                results.push({ printerId: printer.id, success });
            } catch (error) {
                results.push({ printerId: printer.id, success: false, error: error.message });
            }
        }

        return results;
    }

    // Send print data to printer
    async sendPrintData(printer, content) {
        try {
            if (!printer.device.gatt.connected) {
                throw new Error('Device not connected');
            }

            let service, characteristic;
            
            try {
                service = await printer.server.getPrimaryService('000018f0-0000-1000-8000-00805f9b34fb');
                characteristic = await service.getCharacteristic('00002af1-0000-1000-8000-00805f9b34fb');
            } catch (e) {
                try {
                    service = await printer.server.getPrimaryService('00001101-0000-1000-8000-00805f9b34fb');
                    characteristic = await service.getCharacteristic('00001102-0000-1000-8000-00805f9b34fb');
                } catch (e2) {
                    try {
                        service = await printer.server.getPrimaryService('0000ffe0-0000-1000-8000-00805f9b34fb');
                        characteristic = await service.getCharacteristic('0000ffe1-0000-1000-8000-00805f9b34fb');
                    } catch (e3) {
                        const services = await printer.server.getPrimaryServices();
                        for (const svc of services) {
                            try {
                                const characteristics = await svc.getCharacteristics();
                                for (const char of characteristics) {
                                    if (char.properties.write || char.properties.writeWithoutResponse) {
                                        service = svc;
                                        characteristic = char;
                                        break;
                                    }
                                }
                                if (characteristic) break;
                            } catch (e4) {
                                continue;
                            }
                        }
                    }
                }
            }

            if (!characteristic) {
                throw new Error('No writable characteristic found');
            }

            const encoder = new TextEncoder();
            const data = encoder.encode(content);

            const chunkSize = 244;
            for (let i = 0; i < data.length; i += chunkSize) {
                const chunk = data.slice(i, i + chunkSize);
                await characteristic.writeValue(chunk);
                if (i + chunkSize < data.length) {
                    await new Promise(resolve => setTimeout(resolve, 10));
                }
            }

            return true;

        } catch (error) {
            console.error('Print data send error:', error);
            throw error;
        }
    }

    // Disconnect a specific printer
    disconnectPrinter(printerId) {
        const printer = this.connectedPrinters.get(printerId);
        if (printer && printer.device) {
            if (printer.device.gatt.connected) {
                printer.device.gatt.disconnect();
            }
            this.connectedPrinters.delete(printerId);
            this.savePersistedConnections();
            console.log(`Disconnected printer ${printerId}`);
        }
    }

    // Disconnect all printers
    disconnectAllPrinters() {
        for (const [printerId, printer] of this.connectedPrinters) {
            if (printer.device && printer.device.gatt.connected) {
                printer.device.gatt.disconnect();
            }
        }
        this.connectedPrinters.clear();
        this.savePersistedConnections();
        console.log('Disconnected all printers');
    }

    // Get connection status
    getConnectionStatus() {
        const connectedCount = this.getConnectedPrinters().length;
        return {
            connected: connectedCount,
            total: this.connectedPrinters.size,
            status: connectedCount > 0 ? 'connected' : 'disconnected'
        };
    }

    // Notify connection status changes
    notifyConnectionStatus(type, printer) {
        const event = new CustomEvent('bluetoothPrinterStatus', {
            detail: { type, printer, status: this.getConnectionStatus() }
        });
        document.dispatchEvent(event);
        
        // Also show user notification
        this.showReconnectionNotification(type, printer);
    }

    // Show reconnection notification to user
    showReconnectionNotification(type, printer) {
        let message = '';
        let notificationType = 'info';
        
        switch (type) {
            case 'reconnected':
                message = `Printer "${printer.name}" reconnected successfully!`;
                notificationType = 'success';
                break;
            case 'failed':
                message = `Failed to reconnect printer "${printer.name}". Please check if it's powered on and in range.`;
                notificationType = 'warning';
                break;
            case 'disconnected':
                message = `Printer "${printer.name}" disconnected. Attempting to reconnect...`;
                notificationType = 'warning';
                break;
            default:
                return;
        }
        
        // Dispatch a custom event for notifications
        const notificationEvent = new CustomEvent('showNotification', {
            detail: { message, type: notificationType }
        });
        document.dispatchEvent(notificationEvent);
    }

    // Generate test receipt
    generateTestReceipt() {
        const now = new Date();
        const dateStr = now.toLocaleDateString();
        const timeStr = now.toLocaleTimeString();
        
        let receipt = '';
        receipt += '\x1B\x40'; // Initialize printer
        receipt += '\x1B\x61\x01'; // Center alignment
        receipt += '\x1B\x21\x30'; // Double height and width
        receipt += 'PRINTER TEST\n';
        receipt += '\x1B\x21\x00'; // Normal text
        receipt += 'HOTEL POS\n';
        receipt += '\x1B\x61\x00'; // Left alignment
        receipt += '================================\n';
        receipt += `Date: ${dateStr}\n`;
        receipt += `Time: ${timeStr}\n`;
        receipt += 'Test Type: Bluetooth BLE\n';
        receipt += 'Status: SUCCESS\n';
        receipt += '================================\n';
        receipt += 'This is a test print to verify\n';
        receipt += 'Bluetooth connectivity and\n';
        receipt += 'printer functionality.\n';
        receipt += '================================\n';
        receipt += '\n\n\n';
        receipt += '\x1D\x56\x00'; // Cut paper
        
        return receipt;
    }
}

// Create global instance
window.bluetoothPrinterManager = new BluetoothPrinterManager();

// Add debug helper function to window for testing
window.debugBluetoothAutoConnect = async function() {
    console.log('🔍 [DEBUG] Starting manual Bluetooth auto-connect test...');
    console.log('🔍 [DEBUG] ============================================');
    
    // Check localStorage
    const savedConnections = localStorage.getItem('bluetooth-printer-connections');
    console.log('🔍 [DEBUG] 1. Checking localStorage...');
    if (savedConnections) {
        const connections = JSON.parse(savedConnections);
        console.log(`   Found ${connections.length} saved connection(s):`);
        connections.forEach((c, i) => {
            console.log(`   ${i + 1}. "${c.name}" - Device ID: ${c.deviceId}`);
        });
    } else {
        console.log('   ❌ No saved connections found in localStorage');
        return;
    }
    
    // Check Bluetooth API
    console.log('🔍 [DEBUG] 2. Checking Bluetooth API...');
    if (!navigator.bluetooth) {
        console.log('   ❌ Bluetooth API not available');
        return;
    }
    console.log('   ✅ Bluetooth API available');
    
    if (typeof navigator.bluetooth.getDevices !== 'function') {
        console.log('   ❌ getDevices() not supported');
        return;
    }
    console.log('   ✅ getDevices() is supported');
    
    // Check getDevices()
    console.log('🔍 [DEBUG] 3. Calling getDevices()...');
    try {
        const pairedDevices = await navigator.bluetooth.getDevices();
        console.log(`   Found ${pairedDevices.length} paired device(s):`);
        if (pairedDevices.length > 0) {
            pairedDevices.forEach((d, i) => {
                console.log(`   ${i + 1}. "${d.name || 'Unknown'}" - Device ID: ${d.id}`);
                console.log(`      Connected: ${d.gatt?.connected || false}`);
            });
        } else {
            console.log('   ⚠️ No paired devices found!');
            console.log('   ⚠️ This means auto-connect cannot work.');
            console.log('   ⚠️ The device needs to be manually connected again.');
        }
        
        // Compare saved vs paired
        if (savedConnections && pairedDevices.length > 0) {
            const connections = JSON.parse(savedConnections);
            console.log('🔍 [DEBUG] 4. Comparing saved vs paired devices...');
            connections.forEach((saved, i) => {
                console.log(`   Saved device ${i + 1}: "${saved.name}" (ID: ${saved.deviceId})`);
                const match = pairedDevices.find(d => d.id === saved.deviceId || d.name === saved.name);
                if (match) {
                    console.log(`   ✅ Found match: "${match.name}" (ID: ${match.id})`);
                } else {
                    console.log(`   ❌ No match found in paired devices`);
                }
            });
        }
        
        // Try to reconnect
        console.log('🔍 [DEBUG] 5. Attempting auto-reconnect...');
        if (window.bluetoothPrinterManager) {
            window.bluetoothPrinterManager.autoReconnectAttempted = false;
            await window.bluetoothPrinterManager.attemptReconnectAll();
        } else {
            console.log('   ❌ Bluetooth printer manager not found');
        }
        
    } catch (error) {
        console.error('   ❌ Error:', error);
        console.error('   Error message:', error.message);
    }
    
    console.log('🔍 [DEBUG] ============================================');
    console.log('🔍 [DEBUG] Test complete. Check the logs above for details.');
};

console.log('🔵 Bluetooth Printer Manager loaded. Use debugBluetoothAutoConnect() in console to test auto-connect.');

// Export for module systems
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BluetoothPrinterManager;
}
