/**
 * WiFi Printer Manager
 * Handles WiFi thermal printer connections and printing
 */

class WiFiPrinterManager {
    constructor() {
        this.connectedPrinters = new Map();
        this.connectionStatus = 'disconnected';
        this.connectionTimeout = 5000; // 5 second timeout
        this.chunkDelay = 10; // Delay between data chunks
        
        // Performance metrics
        this.metrics = {
            connectionTimes: [],
            printTimes: [],
            errorCount: 0
        };
        
        // Load persisted connections
        this.loadPersistedConnections();
        
        // Clean up any duplicates that may have been created
        this.cleanupDuplicates();
    }

    // Load persisted connections from localStorage
    loadPersistedConnections() {
        try {
            const savedConnections = localStorage.getItem('wifi-printer-connections');
            if (savedConnections) {
                const connections = JSON.parse(savedConnections);
                console.log('Loading persisted WiFi printer connections:', connections);
                
                // CRITICAL: Always mark as disconnected when loading - they must be verified before use
                connections.forEach(connection => {
                    console.log(`  Loading printer: ${connection.name} (${connection.ip}:${connection.port}) - Status: disconnected (will verify on connect)`);
                    
                    this.connectedPrinters.set(connection.id, {
                        ...connection,
                        // Always start as disconnected - must verify connectivity before marking as connected
                        status: 'disconnected'
                    });
                });
                
                console.log(`Loaded ${connections.length} printer(s) - all marked as disconnected until verified`);
            }
        } catch (error) {
            console.error('Error loading persisted WiFi connections:', error);
        }
    }

    // Save connections to localStorage
    savePersistedConnections() {
        try {
            const connections = Array.from(this.connectedPrinters.values()).map(printer => ({
                id: printer.id,
                name: printer.name,
                ip: printer.ip,
                port: printer.port,
                status: printer.status,
                lastUsed: printer.lastUsed
            }));
            localStorage.setItem('wifi-printer-connections', JSON.stringify(connections));
        } catch (error) {
            console.error('Error saving WiFi connections:', error);
        }
    }

    // Add a new printer with deduplication
    addPrinter(name, ip, port = 9100) {
        // Check if printer already exists (by IP and port)
        const existingPrinter = this.findPrinterByAddress(ip, port);
        if (existingPrinter) {
            console.log(`Printer already exists at ${ip}:${port}, updating name to: ${name}`);
            existingPrinter.name = name;
            existingPrinter.lastUsed = new Date().toISOString();
            this.savePersistedConnections();
            return existingPrinter.id;
        }
        
        const printerId = `wifi_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
        const printer = {
            id: printerId,
            name: name,
            ip: ip,
            port: port,
            status: 'disconnected',
            lastUsed: new Date().toISOString()
        };
        
        this.connectedPrinters.set(printerId, printer);
        this.savePersistedConnections();
        
        console.log(`Added new printer: ${name} at ${ip}:${port}`);
        return printerId;
    }

    // Find printer by IP and port
    findPrinterByAddress(ip, port) {
        for (const [printerId, printer] of this.connectedPrinters) {
            if (printer.ip === ip && printer.port === port) {
                return printer;
            }
        }
        return null;
    }

    // Clean up duplicate printers
    cleanupDuplicates() {
        const seen = new Set();
        const toRemove = [];
        
        for (const [printerId, printer] of this.connectedPrinters) {
            const key = `${printer.ip}:${printer.port}`;
            if (seen.has(key)) {
                toRemove.push(printerId);
                console.log(`Removing duplicate printer: ${printer.name} at ${printer.ip}:${printer.port}`);
            } else {
                seen.add(key);
            }
        }
        
        // Remove duplicates
        toRemove.forEach(printerId => {
            this.connectedPrinters.delete(printerId);
        });
        
        if (toRemove.length > 0) {
            console.log(`Cleaned up ${toRemove.length} duplicate printers`);
            this.savePersistedConnections();
        }
    }
    
    // Clean up unreachable printers (those that have been disconnected for a long time)
    async cleanupUnreachablePrinters() {
        const unreachableThreshold = 5 * 60 * 1000; // 5 minutes
        const now = Date.now();
        const toRemove = [];
        
        for (const [printerId, printer] of this.connectedPrinters) {
            // Check if printer has been disconnected for too long
            if (printer.status === 'disconnected') {
                const lastUsed = printer.lastUsed ? new Date(printer.lastUsed).getTime() : 0;
                const timeSinceLastUsed = now - lastUsed;
                
                // If disconnected for more than threshold, verify one more time
                if (timeSinceLastUsed > unreachableThreshold) {
                    console.log(`Checking if printer ${printer.name} (${printer.ip}:${printer.port}) is still reachable...`);
                    const isReachable = await this.verifyPrinterConnectivity(printer.ip, printer.port);
                    
                    if (!isReachable) {
                        console.log(`Printer ${printer.name} (${printer.ip}:${printer.port}) is not reachable - marking for removal`);
                        toRemove.push(printerId);
                    } else {
                        // Printer is reachable, try to reconnect
                        try {
                            await this.connectPrinter(printerId);
                            console.log(`Reconnected to ${printer.name}`);
                        } catch (e) {
                            console.warn(`Failed to reconnect to ${printer.name}:`, e);
                        }
                    }
                }
            }
        }
        
        // Remove unreachable printers
        if (toRemove.length > 0) {
            toRemove.forEach(printerId => {
                this.connectedPrinters.delete(printerId);
                console.log(`Removed unreachable printer: ${printerId}`);
            });
            this.savePersistedConnections();
            console.log(`Cleaned up ${toRemove.length} unreachable printer(s)`);
        }
    }

    // Clear all disconnected printers
    clearDisconnectedPrinters() {
        const toRemove = [];
        
        for (const [printerId, printer] of this.connectedPrinters) {
            if (printer.status === 'disconnected') {
                toRemove.push(printerId);
            }
        }
        
        toRemove.forEach(printerId => {
            this.connectedPrinters.delete(printerId);
        });
        
        if (toRemove.length > 0) {
            console.log(`Cleared ${toRemove.length} disconnected printers`);
            this.savePersistedConnections();
        }
    }

    // Clean up all printers and start fresh
    resetAllPrinters() {
        this.connectedPrinters.clear();
        this.savePersistedConnections();
        console.log('Reset all WiFi printers');
    }

    // Connect to a printer - WITH CONNECTIVITY VERIFICATION
    async connectPrinter(printerId) {
        const printer = this.connectedPrinters.get(printerId);
        if (!printer) {
            throw new Error('Printer not found');
        }

        const startTime = Date.now();
        
        try {
            // CRITICAL: Verify printer is actually reachable before marking as connected
            console.log(`Verifying connectivity to ${printer.name} (${printer.ip}:${printer.port})...`);
            const isReachable = await this.verifyPrinterConnectivity(printer.ip, printer.port);
            
            if (!isReachable) {
                // Printer is not reachable - mark as disconnected
                printer.status = 'disconnected';
                this.savePersistedConnections();
                throw new Error(`Printer ${printer.name} (${printer.ip}:${printer.port}) is not reachable`);
            }
            
            // For WiFi thermal printers, we test the connection via backend
            // since we can't directly establish TCP connections from the browser
            // The actual printing will be handled by the backend
            
            return new Promise((resolve, reject) => {
                const timeout = setTimeout(() => {
                    reject(new Error('Connection timeout'));
                }, this.connectionTimeout);

                // Test connection by making a request to backend
                fetch('/api/test-wifi-printer', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                    },
                    body: JSON.stringify({
                        ip: printer.ip,
                        port: printer.port
                    })
                })
                .then(response => response.json())
                .then(data => {
                    clearTimeout(timeout);
                    
                    if (data.success) {
                        printer.status = 'connected';
                        printer.lastUsed = new Date().toISOString();
                        
                        const connectionTime = Date.now() - startTime;
                        this.metrics.connectionTimes.push(connectionTime);
                        
                        console.log(`✅ WiFi printer "${printer.name}" connected and verified in ${connectionTime}ms`);
                        this.notifyConnectionStatus('connected', printer);
                        this.savePersistedConnections();
                        
                        resolve(printer);
                    } else {
                        // Connection test failed - mark as disconnected
                        printer.status = 'disconnected';
                        this.savePersistedConnections();
                        reject(new Error(data.error || `Failed to connect to ${printer.name}`));
                    }
                })
                .catch(error => {
                    clearTimeout(timeout);
                    console.error(`❌ WiFi printer connection error:`, error);
                    // Mark as disconnected on error
                    printer.status = 'disconnected';
                    this.savePersistedConnections();
                    reject(new Error(`Failed to connect to ${printer.name}`));
                });
            });
            
        } catch (error) {
            this.metrics.errorCount++;
            // Ensure printer is marked as disconnected on any error
            printer.status = 'disconnected';
            this.savePersistedConnections();
            throw error;
        }
    }

    // Disconnect a printer
    disconnectPrinter(printerId) {
        try {
            if (!printerId) {
                console.warn('No printer ID provided for disconnection');
                return false;
            }
            
            const printer = this.connectedPrinters.get(printerId);
            if (printer) {
                printer.status = 'disconnected';
                printer.socket = null;
                this.notifyConnectionStatus('disconnected', printer);
                // Save connections after disconnecting
                this.savePersistedConnections();
                console.log(`Disconnected WiFi printer: ${printer.name}`);
                return true;
            } else {
                console.warn(`WiFi printer ${printerId} not found for disconnection`);
                return false;
            }
        } catch (error) {
            console.error(`Error disconnecting WiFi printer ${printerId}:`, error);
            // Don't throw - return false instead to allow other printers to disconnect
            return false;
        }
    }

    // Disconnect all printers
    disconnectAllPrinters() {
        try {
            if (!this.connectedPrinters || this.connectedPrinters.size === 0) {
                console.log('No WiFi printers to disconnect');
                return 0;
            }
            
            const printerCount = this.connectedPrinters.size;
            let successCount = 0;
            let failCount = 0;
            
            // Create a copy of the map entries to avoid modification during iteration
            const printersToDisconnect = Array.from(this.connectedPrinters.entries());
            
            for (const [printerId, printer] of printersToDisconnect) {
                try {
                    const success = this.disconnectPrinter(printerId);
                    if (success) {
                        successCount++;
                    } else {
                        failCount++;
                    }
                } catch (error) {
                    console.error(`Error disconnecting printer ${printerId}:`, error);
                    failCount++;
                }
            }
            
            // Save connections after disconnecting all
            try {
                this.savePersistedConnections();
            } catch (saveError) {
                console.warn('Error saving connections after disconnect:', saveError);
            }
            
            console.log(`Disconnected ${successCount} of ${printerCount} WiFi printer(s)`);
            if (failCount > 0) {
                console.warn(`${failCount} printer(s) failed to disconnect`);
            }
            
            return successCount;
        } catch (error) {
            console.error('Error disconnecting all WiFi printers:', error);
            // Don't throw - return 0 to indicate failure but don't break the caller
            return 0;
        }
    }

    // Get connected printers
    getConnectedPrinters() {
        const allPrinters = Array.from(this.connectedPrinters.values());
        const connectedPrinters = allPrinters.filter(printer => printer.status === 'connected');
        
        // Debug logging
        console.log(`WiFi Printer Manager - Total printers: ${allPrinters.length}, Connected: ${connectedPrinters.length}`);
        allPrinters.forEach(printer => {
            console.log(`  ${printer.name} (${printer.ip}:${printer.port}) - Status: ${printer.status}`);
        });
        
        return connectedPrinters;
    }

    // Check if any printers are connected
    isConnected() {
        return this.getConnectedPrinters().length > 0;
    }

    // Print to a specific printer
    async printToPrinter(printerId, content) {
        const printer = this.connectedPrinters.get(printerId);
        if (!printer || printer.status !== 'connected') {
            throw new Error('Printer not connected');
        }

        const startTime = Date.now();
        
        console.log(`Attempting to print to WiFi printer: ${printer.name} at ${printer.ip}:${printer.port}`);
        console.log('Print content preview:', content.substring(0, 100) + '...');
        
        try {
            // Check if this looks like a thermal printer port
            const thermalPorts = [9100, 9101, 9102, 515, 631];
            if (!thermalPorts.includes(printer.port)) {
                console.warn(`Warning: Port ${printer.port} is not a typical thermal printer port. This might not be a thermal printer.`);
            }
            
            // Send print job to backend
            const response = await fetch('/api/print-wifi', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                },
                body: JSON.stringify({
                    ip: printer.ip,
                    port: printer.port,
                    content: content,
                    printerName: printer.name
                })
            });

            if (!response.ok) {
                throw new Error(`HTTP ${response.status}: ${response.statusText}`);
            }

            const data = await response.json();
            console.log('Print API response:', data);
            
            if (!data.success) {
                throw new Error(data.error || 'Print failed');
            }

            const printTime = Date.now() - startTime;
            this.metrics.printTimes.push(printTime);
            
            console.log(`✅ WiFi print completed successfully in ${printTime}ms`);
            return true;
            
        } catch (error) {
            this.metrics.errorCount++;
            console.error('❌ WiFi print error:', error);
            
            // Provide more helpful error messages
            if (error.message.includes('Failed to print')) {
                throw new Error(`Printing failed: ${error.message}. This device might not be a thermal printer or may not support raw printing.`);
            } else {
                throw error;
            }
        }
    }

    // Print to all connected printers with improved error handling
    async printToAllPrinters(content) {
        const connectedPrinters = this.getConnectedPrinters();
        if (connectedPrinters.length === 0) {
            console.warn('No WiFi printers connected, attempting to reconnect...');
            await this.attemptReconnectAllPrinters();
            const retryPrinters = this.getConnectedPrinters();
            if (retryPrinters.length === 0) {
                throw new Error('No WiFi printers available after reconnection attempt');
            }
        }

        const printPromises = connectedPrinters.map(async (printer) => {
            try {
                // Check if printer is actually reachable before attempting to print
                if (printer.status !== 'connected') {
                    console.log(`Printer ${printer.name} is not connected, skipping...`);
                    return { printerId: printer.id, success: false, error: 'Printer not connected' };
                }
                
                const success = await this.printToPrinter(printer.id, content);
                return { printerId: printer.id, success };
            } catch (error) {
                console.error(`Print failed for printer ${printer.id}:`, error);
                // Mark printer as disconnected if connection fails
                if (error.message.includes('Connection refused') || error.message.includes('timeout')) {
                    printer.status = 'disconnected';
                    this.savePersistedConnections();
                }
                return { printerId: printer.id, success: false, error: error.message };
            }
        });

        return await Promise.all(printPromises);
    }

    // Attempt to reconnect all disconnected printers - WITH CONNECTIVITY VERIFICATION
    async attemptReconnectAllPrinters() {
        const disconnectedPrinters = Array.from(this.connectedPrinters.values())
            .filter(printer => printer.status === 'disconnected');
        
        if (disconnectedPrinters.length === 0) {
            console.log('No disconnected printers to reconnect');
            return;
        }

        console.log(`Attempting to reconnect ${disconnectedPrinters.length} disconnected printers...`);
        
        const reconnectPromises = disconnectedPrinters.map(async (printer) => {
            try {
                // CRITICAL: Verify printer is actually reachable before attempting reconnection
                console.log(`Verifying connectivity to ${printer.name} (${printer.ip}:${printer.port})...`);
                const isReachable = await this.verifyPrinterConnectivity(printer.ip, printer.port);
                
                if (!isReachable) {
                    console.warn(`❌ Printer ${printer.name} (${printer.ip}:${printer.port}) is not reachable - skipping reconnection`);
                    return;
                }
                
                // Only reconnect if printer is reachable
                await this.connectPrinter(printer.id);
                console.log(`✅ Successfully reconnected printer: ${printer.name}`);
            } catch (error) {
                console.log(`❌ Failed to reconnect printer ${printer.name}:`, error.message);
                // Mark as disconnected if reconnection fails
                printer.status = 'disconnected';
                this.savePersistedConnections();
            }
        });

        await Promise.all(reconnectPromises);
    }
    
    // Verify printer connectivity
    async verifyPrinterConnectivity(ip, port) {
        try {
            const response = await fetch('/api/test-wifi-printer', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ ip: ip, port: port })
            });
            
            if (response.ok) {
                const data = await response.json();
                return data.success === true;
            }
            return false;
        } catch (error) {
            console.warn(`Connectivity verification failed for ${ip}:${port}:`, error);
            return false;
        }
    }

    // Check printer connectivity
    async checkPrinterConnectivity(printerId) {
        const printer = this.connectedPrinters.get(printerId);
        if (!printer) return false;

        try {
            // Try a simple connectivity test
            const response = await fetch(`/api/test-wifi-printer`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    ip: printer.ip,
                    port: printer.port
                })
            });

            if (response.ok) {
                printer.status = 'connected';
                return true;
            } else {
                printer.status = 'disconnected';
                return false;
            }
        } catch (error) {
            printer.status = 'disconnected';
            return false;
        }
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

    // Get performance metrics
    getMetrics() {
        const avgConnectionTime = this.metrics.connectionTimes.length > 0 
            ? this.metrics.connectionTimes.reduce((a, b) => a + b, 0) / this.metrics.connectionTimes.length 
            : 0;
        
        const avgPrintTime = this.metrics.printTimes.length > 0 
            ? this.metrics.printTimes.reduce((a, b) => a + b, 0) / this.metrics.printTimes.length 
            : 0;

        return {
            avgConnectionTime: Math.round(avgConnectionTime),
            avgPrintTime: Math.round(avgPrintTime),
            totalConnections: this.metrics.connectionTimes.length,
            totalPrints: this.metrics.printTimes.length,
            errorCount: this.metrics.errorCount
        };
    }

    // Notify connection status changes
    notifyConnectionStatus(type, printer) {
        const event = new CustomEvent('wifiPrinterStatus', {
            detail: { type, printer, status: this.getConnectionStatus() }
        });
        document.dispatchEvent(event);
    }

    // Generate receipt content
    generateReceiptContent() {
        const now = new Date();
        const timestamp = now.toLocaleString();
        
        return `
=== RECEIPT ===
Date: ${timestamp}
Printer: WiFi Thermal Printer
Status: Connected Successfully

Receipt printed via WiFi
thermal printer connection.

Thank you!
============
`;
    }
}

// Export for use in other modules
if (typeof module !== 'undefined' && module.exports) {
    module.exports = WiFiPrinterManager;
} else {
    window.WiFiPrinterManager = WiFiPrinterManager;
}
