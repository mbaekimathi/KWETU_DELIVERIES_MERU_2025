/**
 * USB Thermal Printer Manager
 * Handles USB thermal printer connections using WebUSB API
 * Supports ESC/POS thermal printers (XPrinter, Epson, etc.)
 */

class USBPrinterManager {
    constructor() {
        this.connectedPrinters = new Map();
        this.connectionStatus = 'disconnected';
        this.reconnectAttempts = 0;
        this.maxReconnectAttempts = 3;
        this.reconnectDelay = 2000;
        
        // USB device filters for thermal printers
        this.deviceFilters = [
            // XPrinter USB IDs
            { vendorId: 0x04e8, productId: 0x0202 }, // Samsung (often used by XPrinter)
            { vendorId: 0x04e8 }, // Samsung vendor
            // Epson thermal printers
            { vendorId: 0x04b8 }, // Epson
            // Generic USB serial devices (common for thermal printers)
            { classCode: 0x07, subclassCode: 0x01 }, // USB CDC (Communication Device Class)
            { classCode: 0xff } // Vendor specific
        ];
        
        // Initialize from localStorage
        this.loadPersistedConnections();
        
        console.log('🔌 USB Printer Manager initialized');
    }

    // Check if WebUSB is supported
    isSupported() {
        return 'usb' in navigator && typeof navigator.usb.requestDevice === 'function';
    }

    // Load persisted connections from localStorage
    loadPersistedConnections() {
        try {
            const saved = localStorage.getItem('saved_usb_printers');
            if (saved) {
                const printers = JSON.parse(saved);
                console.log('📦 Loaded saved USB printers:', printers);
                // Note: USB devices need to be reconnected due to browser security
                // We'll store the device info for reference
                this.savedPrinters = printers;
            }
        } catch (e) {
            console.warn('Error loading USB printer connections:', e);
        }
    }

    // Save connections to localStorage
    savePersistedConnections() {
        try {
            const printers = Array.from(this.connectedPrinters.values()).map(p => ({
                id: p.id,
                name: p.name,
                vendorId: p.vendorId,
                productId: p.productId,
                serialNumber: p.serialNumber,
                type: 'usb'
            }));
            localStorage.setItem('saved_usb_printers', JSON.stringify(printers));
            console.log('💾 Saved USB printer connections:', printers);
        } catch (e) {
            console.warn('Error saving USB printer connections:', e);
        }
    }

    // Scan for USB thermal printers
    async scanForPrinters() {
        if (!this.isSupported()) {
            throw new Error('WebUSB is not supported in this browser. Please use Chrome, Edge, or Opera.');
        }

        try {
            // Request USB device with broader filters if initial request fails
            let device = null;
            try {
                // First try with specific filters
                device = await navigator.usb.requestDevice({
                    filters: this.deviceFilters
                });
            } catch (filterError) {
                // If filters fail, try without filters (user can select manually)
                console.warn('Filtered device request failed, trying without filters:', filterError);
                try {
                    device = await navigator.usb.requestDevice({
                        filters: [] // Empty filters = show all USB devices
                    });
                } catch (noFilterError) {
                    if (noFilterError.name === 'NotFoundError') {
                        throw new Error('No USB device selected. Please select your printer from the device list.');
                    } else if (noFilterError.name === 'SecurityError') {
                        throw new Error('USB permission denied. Please allow USB access in your browser.');
                    } else {
                        throw noFilterError;
                    }
                }
            }

            if (device) {
                return [{
                    id: this.generateDeviceId(device),
                    name: device.productName || `USB Printer (${device.manufacturerName || 'Unknown'})`,
                    device: device,
                    vendorId: device.vendorId,
                    productId: device.productId,
                    serialNumber: device.serialNumber,
                    type: 'usb',
                    status: 'available'
                }];
            }
            return [];
        } catch (error) {
            if (error.name === 'NotFoundError') {
                throw new Error('No USB device selected');
            } else if (error.name === 'SecurityError') {
                throw new Error('USB permission denied');
            } else {
                throw error;
            }
        }
    }

    // Generate unique device ID
    generateDeviceId(device) {
        return `usb_${device.vendorId}_${device.productId}_${device.serialNumber || 'unknown'}`;
    }

    // Connect to USB printer
    async connectToPrinter(device) {
        try {
            const deviceId = this.generateDeviceId(device);
            
            // Check if already connected
            if (this.connectedPrinters.has(deviceId)) {
                const existingPrinter = this.connectedPrinters.get(deviceId);
                // Check if device is still open
                try {
                    if (existingPrinter.device.opened) {
                        console.log('USB printer already connected:', deviceId);
                        return deviceId;
                    }
                } catch (e) {
                    // Device might be closed, remove from map and reconnect
                    this.connectedPrinters.delete(deviceId);
                }
            }

            // Check if device is already opened and handle it
            if (device.opened) {
                console.warn('Device is already opened, attempting to close and reopen...');
                try {
                    // Try to release any claimed interfaces first
                    if (device.configuration && device.configuration.interfaces) {
                        for (const iface of device.configuration.interfaces) {
                            try {
                                await device.releaseInterface(iface.interfaceNumber);
                            } catch (e) {
                                // Ignore release errors - interface might not be claimed
                            }
                        }
                    }
                    await device.close();
                    // Wait longer before reopening to allow OS to release the device
                    await new Promise(resolve => setTimeout(resolve, 500));
                } catch (e) {
                    console.warn('Could not close already-opened device:', e);
                    // Continue anyway - might still work
                }
            }

            // Open device with retry logic
            let openAttempts = 0;
            const maxOpenAttempts = 3;
            let lastError = null;
            
            while (openAttempts < maxOpenAttempts) {
                try {
                    await device.open();
                    console.log(`✅ Device opened successfully on attempt ${openAttempts + 1}`);
                    break; // Success, exit retry loop
                } catch (error) {
                    openAttempts++;
                    lastError = error;
                    
                    if (error.name === 'SecurityError' || error.message.includes('Access denied')) {
                        if (openAttempts < maxOpenAttempts) {
                            console.warn(`Access denied on attempt ${openAttempts}, waiting before retry...`);
                            // Wait progressively longer between retries
                            await new Promise(resolve => setTimeout(resolve, 1000 * openAttempts));
                            continue; // Retry
                        } else {
                            // All retries failed
                            throw new Error('USB device access denied after multiple attempts. Please:\n\n' +
                                          '1. Close any other applications using this printer\n' +
                                          '2. Disable the printer in Windows Device Manager temporarily\n' +
                                          '3. Unplug and replug the USB printer\n' +
                                          '4. Wait 5-10 seconds and try again\n' +
                                          '5. If using Windows, you may need to disable the printer driver');
                        }
                    } else if (error.name === 'NotFoundError') {
                        throw new Error('USB device not found. Please make sure the printer is connected and try again.');
                    } else {
                        // For other errors, don't retry
                        throw new Error(`Failed to open USB device: ${error.message}`);
                    }
                }
            }
            
            if (lastError && !device.opened) {
                throw lastError;
            }
            
            // Select configuration (most devices use configuration 1)
            try {
                // Get available configurations
                if (device.configurations && device.configurations.length > 0) {
                    await device.selectConfiguration(1);
                } else {
                    // Some devices auto-select configuration
                    console.log('Device has no selectable configurations, using default');
                }
            } catch (e) {
                console.warn('Could not select configuration, trying default:', e);
                // Try to continue without explicit configuration selection
            }

            // Wait for device to be ready and get configuration
            if (!device.configuration) {
                // Some devices need a moment after opening
                await new Promise(resolve => setTimeout(resolve, 200));
                if (!device.configuration) {
                    throw new Error('Device configuration not available. Please reconnect the device.');
                }
            }

            // Find and claim interface with retry logic
            // Thermal printers typically use interface 0 or 1
            let interfaceClaimed = false;
            let claimedInterfaceNumber = null;
            
            // Get interfaces from the active configuration
            const interfaces = device.configuration.interfaces || [];
            
            if (interfaces.length === 0) {
                throw new Error('No USB interfaces found on device. This device may not be compatible.');
            }
            
            // Try to claim interfaces with retry logic
            const maxClaimAttempts = 2;
            for (let attempt = 0; attempt < maxClaimAttempts && !interfaceClaimed; attempt++) {
                if (attempt > 0) {
                    console.log(`Retrying interface claim (attempt ${attempt + 1})...`);
                    await new Promise(resolve => setTimeout(resolve, 500));
                }
                
                for (let i = 0; i < interfaces.length; i++) {
                    try {
                        const iface = interfaces[i];
                        
                        // Check if interface is already claimed (might be from previous attempt)
                        try {
                            await device.releaseInterface(iface.interfaceNumber);
                            await new Promise(resolve => setTimeout(resolve, 100));
                        } catch (e) {
                            // Interface wasn't claimed, that's fine
                        }
                        
                        // Try to claim the interface
                        await device.claimInterface(iface.interfaceNumber);
                        interfaceClaimed = true;
                        claimedInterfaceNumber = iface.interfaceNumber;
                        console.log(`✅ Claimed interface ${iface.interfaceNumber} on attempt ${attempt + 1}`);
                        break;
                    } catch (e) {
                        const errorMsg = e.message || e.toString();
                        if (errorMsg.includes('Access denied') || errorMsg.includes('already claimed')) {
                            if (attempt === maxClaimAttempts - 1) {
                                // Last attempt failed
                                throw new Error(`Interface ${i} is already claimed by another application or driver. ` +
                                              `Please:\n1. Close any other programs using this printer\n` +
                                              `2. Disable the printer in Windows Device Manager\n` +
                                              `3. Unplug and replug the USB printer\n` +
                                              `4. Wait 5-10 seconds and try again`);
                            }
                            // Will retry on next attempt
                            console.warn(`Interface ${i} access denied, will retry...`);
                        } else {
                            console.warn(`Could not claim interface ${i}:`, errorMsg);
                        }
                    }
                }
            }

            if (!interfaceClaimed) {
                // Try to release any partially claimed interfaces before throwing
                try {
                    for (let i = 0; i < interfaces.length; i++) {
                        try {
                            await device.releaseInterface(interfaces[i].interfaceNumber);
                        } catch (e) {
                            // Ignore release errors
                        }
                    }
                } catch (e) {
                    // Ignore cleanup errors
                }
                throw new Error('Could not claim any USB interface after multiple attempts. ' +
                              'The device may be in use by another application or Windows printer driver. ' +
                              'Try disabling the printer in Device Manager or closing other applications.');
            }

            // Find bulk out endpoint (for sending data to printer)
            const endpoint = this.findBulkOutEndpoint(device);
            if (!endpoint) {
                throw new Error('Could not find bulk out endpoint');
            }

            // Store printer info
            const printer = {
                id: deviceId,
                name: device.productName || `USB Printer (${device.manufacturerName || 'Unknown'})`,
                device: device,
                vendorId: device.vendorId,
                productId: device.productId,
                serialNumber: device.serialNumber,
                endpoint: endpoint,
                interfaceNumber: claimedInterfaceNumber,
                type: 'usb',
                connected: true,
                connectedAt: new Date().toISOString()
            };

            this.connectedPrinters.set(deviceId, printer);
            this.connectionStatus = 'connected';
            this.savePersistedConnections();

            // Set up disconnect handler
            device.addEventListener('disconnect', () => {
                this.handleDisconnect(deviceId);
            });

            console.log('✅ USB printer connected:', printer.name);
            return deviceId;
        } catch (error) {
            console.error('USB connection error:', error);
            throw error;
        }
    }

    // Find bulk out endpoint
    findBulkOutEndpoint(device) {
        for (const iface of device.configuration.interfaces) {
            for (const alt of iface.alternates) {
                for (const endpoint of alt.endpoints) {
                    if (endpoint.direction === 'out' && endpoint.type === 'bulk') {
                        return endpoint;
                    }
                }
            }
        }
        return null;
    }

    // Handle device disconnect
    handleDisconnect(deviceId) {
        const printer = this.connectedPrinters.get(deviceId);
        if (printer) {
            console.log('🔌 USB printer disconnected:', printer.name);
            this.connectedPrinters.delete(deviceId);
            this.savePersistedConnections();
            
            if (this.connectedPrinters.size === 0) {
                this.connectionStatus = 'disconnected';
            }

            // Dispatch disconnect event
            document.dispatchEvent(new CustomEvent('usbPrinterDisconnected', {
                detail: { printerId: deviceId, printer: printer }
            }));
        }
    }

    // Disconnect printer
    async disconnectPrinter(printerId) {
        const printer = this.connectedPrinters.get(printerId);
        if (!printer) {
            throw new Error('Printer not found');
        }

        try {
            // Release interface
            await printer.device.releaseInterface(printer.interfaceNumber);
            // Close device
            await printer.device.close();
        } catch (e) {
            console.warn('Error during USB disconnect:', e);
        }

        this.connectedPrinters.delete(printerId);
        this.savePersistedConnections();

        if (this.connectedPrinters.size === 0) {
            this.connectionStatus = 'disconnected';
        }

        console.log('🔌 USB printer disconnected:', printer.name);
    }

    // Disconnect all printers
    async disconnectAll() {
        const printerIds = Array.from(this.connectedPrinters.keys());
        for (const printerId of printerIds) {
            try {
                await this.disconnectPrinter(printerId);
            } catch (e) {
                console.warn('Error disconnecting printer:', e);
            }
        }
    }

    // Print to USB printer
    async print(printerId, data) {
        const printer = this.connectedPrinters.get(printerId);
        if (!printer) {
            throw new Error('USB printer not connected');
        }

        try {
            // Convert data to Uint8Array if needed
            let printData;
            if (typeof data === 'string') {
                printData = new TextEncoder().encode(data);
            } else if (data instanceof ArrayBuffer) {
                printData = new Uint8Array(data);
            } else if (data instanceof Uint8Array) {
                printData = data;
            } else {
                throw new Error('Invalid data type for printing');
            }

            // Send data in chunks (USB has packet size limits)
            const chunkSize = printer.endpoint.packetSize || 64;
            for (let i = 0; i < printData.length; i += chunkSize) {
                const chunk = printData.slice(i, i + chunkSize);
                await printer.device.transferOut(printer.endpoint.endpointNumber, chunk);
            }

            console.log(`✅ Printed ${printData.length} bytes to USB printer: ${printer.name}`);
            return { success: true, printerId, bytesSent: printData.length };
        } catch (error) {
            console.error('USB print error:', error);
            // Handle disconnect errors
            if (error.message.includes('disconnect') || error.name === 'NotFoundError') {
                this.handleDisconnect(printerId);
            }
            throw error;
        }
    }

    // Print to all connected USB printers
    async printToAllPrinters(data) {
        const results = [];
        for (const [printerId, printer] of this.connectedPrinters) {
            try {
                const result = await this.print(printerId, data);
                results.push(result);
            } catch (error) {
                results.push({
                    success: false,
                    printerId,
                    error: error.message
                });
            }
        }
        return results;
    }

    // Get connected printers
    getConnectedPrinters() {
        return Array.from(this.connectedPrinters.values());
    }

    // Check if any printer is connected
    isConnected() {
        return this.connectedPrinters.size > 0;
    }

    // Get connection status
    getStatus() {
        return {
            connected: this.isConnected(),
            count: this.connectedPrinters.size,
            printers: this.getConnectedPrinters()
        };
    }
}

// Make it globally available
window.USBPrinterManager = USBPrinterManager;



