# Thermal Printer Scanner Agent Setup Guide

## Overview

The Thermal Printer Scanner Agent is a Python script that automatically discovers thermal printers on your local network. It's designed to work with cPanel and shared hosting environments where the web application cannot directly scan the network.

## Features

- ✅ **Real Network Scanning**: Scans your network for actual thermal printers (no dummy data)
- ✅ **Multiple Discovery Methods**: Uses network range scanning and ARP table scanning
- ✅ **ESC/POS Verification**: Tests printers to verify they're actual thermal printers
- ✅ **cPanel Compatible**: Works in restricted hosting environments
- ✅ **API Integration**: Automatically reports discovered printers to your web app
- ✅ **Database Storage**: Can save discovered printers to a database/file

## Installation

### 1. Upload the Agent Script

Upload `scan_printers_agent.py` to your cPanel hosting directory (same directory as your Flask app):

```bash
# Via cPanel File Manager or FTP
/path/to/your/web/app/scan_printers_agent.py
```

### 2. Make it Executable

In cPanel Terminal or via SSH:

```bash
chmod +x scan_printers_agent.py
```

### 3. Install Python Dependencies

The agent requires Python 3 and the `requests` library:

```bash
pip3 install requests
```

Or add to your requirements.txt (already included):
```
requests==2.31.0
```

## Usage

### Manual Scan

Run the agent manually to scan for printers:

```bash
python3 scan_printers_agent.py 192.168.1
```

Replace `192.168.1` with your network range (e.g., `192.168.0`, `10.0.0`).

### With API Integration

To automatically send discovered printers to your web app:

```bash
python3 scan_printers_agent.py 192.168.1 --api-url https://yourdomain.com/api/agent/printer-found
```

### With Database Storage

To save printers to a local database file:

```bash
python3 scan_printers_agent.py 192.168.1 --save-db
```

### Custom IP Range

Scan a specific IP range instead of the full subnet:

```bash
python3 scan_printers_agent.py 192.168.1 --scan-range 1-100
```

## Setting Up as Cron Job (cPanel)

### Option 1: Via cPanel Cron Jobs

1. Log into cPanel
2. Go to **Cron Jobs**
3. Add a new cron job:
   - **Minute**: `*/5` (every 5 minutes)
   - **Hour**: `*`
   - **Day**: `*`
   - **Month**: `*`
   - **Weekday**: `*`
   - **Command**: 
     ```bash
     /usr/bin/python3 /home/username/path/to/scan_printers_agent.py 192.168.1 --save-db >> /home/username/printer_scan.log 2>&1
     ```

### Option 2: Via SSH

Edit crontab:

```bash
crontab -e
```

Add line:

```bash
*/5 * * * * /usr/bin/python3 /path/to/scan_printers_agent.py 192.168.1 --save-db >> /tmp/printer_scan.log 2>&1
```

## API Endpoints

The web application provides these endpoints for the agent:

### 1. Report Discovered Printer

**POST** `/api/agent/printer-found`

```json
{
  "ip": "192.168.1.100",
  "port": 9100,
  "name": "Thermal Printer at 192.168.1.100:9100",
  "model": "ESC/POS Thermal Printer",
  "type": "thermal"
}
```

### 2. Get Scan Results

**GET** `/api/agent/scan-results`

Returns the latest scan results from the agent.

### 3. Trigger Scan

**POST** `/api/agent/trigger-scan`

```json
{
  "network_range": "192.168.1"
}
```

Triggers a new scan via the agent.

## How It Works

1. **Network Scanning**: The agent scans your network range (e.g., 192.168.1.1-254) for devices with thermal printer ports open (9100, 9101, 9102, 515, 631).

2. **Printer Verification**: For each open port, it sends ESC/POS commands to verify it's actually a thermal printer.

3. **Results Storage**: Discovered printers are saved to:
   - `printer_scan_results.json` (in the app directory)
   - `/tmp/printer_scan_results.json` (fallback)
   - Database file (if `--save-db` is used)

4. **API Integration**: If `--api-url` is provided, each discovered printer is sent to your web app.

5. **Web App Access**: The web app reads the scan results and displays them in the printer setup interface.

## Troubleshooting

### No Printers Found

1. **Check Network Range**: Make sure you're using the correct network range (e.g., `192.168.1` not `192.168.1.1`)

2. **Check Printer Power**: Ensure printers are powered on and connected to the network

3. **Check Firewall**: Make sure firewall allows connections to printer ports (9100, 9101, 9102)

4. **Check Network**: Verify printers are on the same network as the server

### Permission Errors

If you get permission errors:

```bash
# Make sure script is executable
chmod +x scan_printers_agent.py

# Check Python path
which python3

# Try running with full path
/usr/bin/python3 scan_printers_agent.py 192.168.1
```

### Agent Not Accessible from Web App

1. Check that `scan_printers_agent.py` is in the same directory as `app.py`
2. Verify file permissions (should be readable and executable)
3. Check cron job logs: `/tmp/printer_scan.log` or `/home/username/printer_scan.log`

## Network Range Detection

The agent can auto-detect your network range, but you can also specify it:

- `192.168.1` - Common home/office network
- `192.168.0` - Alternative home network
- `10.0.0` - Corporate network
- `172.16.0` - Alternative corporate network

## Security Notes

- The agent only scans your local network
- It doesn't modify any printer settings
- It only reads network information
- Results are stored locally on your server
- API endpoints should be protected with authentication in production

## Support

For issues or questions:
1. Check the scan log file
2. Verify network connectivity
3. Test printer connection manually
4. Review cron job execution logs

