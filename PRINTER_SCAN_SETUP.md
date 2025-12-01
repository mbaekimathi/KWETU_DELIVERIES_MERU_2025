# WiFi Printer Scanner Setup for cPanel

## Overview
This guide explains how to set up the local printer scanning agent for cPanel hosting environments.

## Local Agent Script
The `scan_printers_agent.py` script can scan your local network for WiFi thermal printers and save results that the web application can read.

## Setup Instructions

### 1. Upload the Agent Script
Upload `scan_printers_agent.py` to your cPanel hosting:
- Via cPanel File Manager: Upload to your public_html or project directory
- Via FTP: Upload to your project root directory
- Via SSH: Copy the file to your server

### 2. Make the Script Executable
Via SSH or cPanel Terminal:
```bash
chmod +x scan_printers_agent.py
```

### 3. Test the Script Manually
```bash
python3 scan_printers_agent.py 192.168.1
```
Replace `192.168.1` with your network range (e.g., `192.168.0`, `10.0.0`)

### 4. Set Up Cron Job (Recommended)
In cPanel, go to **Cron Jobs** and add:

**Every 5 minutes:**
```
*/5 * * * * /usr/bin/python3 /home/username/public_html/scan_printers_agent.py 192.168.1 >> /tmp/printer_scan.log 2>&1
```

**Every 10 minutes:**
```
*/10 * * * * /usr/bin/python3 /home/username/public_html/scan_printers_agent.py 192.168.1 >> /tmp/printer_scan.log 2>&1
```

**Replace:**
- `/home/username/public_html/` with your actual path
- `192.168.1` with your network range

### 5. Verify Results
Check if results are being saved:
```bash
cat /tmp/printer_scan_results.json
```

## Network Range Detection

The script can auto-detect your network range, or you can specify it:

```bash
# Auto-detect
python3 scan_printers_agent.py

# Specify range
python3 scan_printers_agent.py 192.168.1
python3 scan_printers_agent.py 10.0.0
python3 scan_printers_agent.py 172.16.0
```

## How It Works

1. **Agent Script** (`scan_printers_agent.py`):
   - Scans your local network for thermal printers
   - Tests common printer ports (9100, 9101, 9102, 515, 631)
   - Saves results to `/tmp/printer_scan_results.json`
   - Can be run manually or via cron job

2. **Web Application**:
   - Automatically detects cPanel environment
   - Checks for recent agent scan results (within 5 minutes)
   - Falls back to direct API scanning if agent results not available
   - Can trigger agent scan via `/api/trigger-agent-scan` endpoint

## Troubleshooting

### Agent Script Not Found
- Ensure the script is in the correct directory
- Check file permissions (should be executable)
- Verify Python 3 path: `which python3`

### No Printers Found
- Verify your network range is correct
- Check if printers are on the same network
- Ensure printers are powered on and connected
- Try manual printer setup as fallback

### Permission Errors
- Ensure script has read/write permissions to `/tmp/`
- Check if your hosting allows cron jobs
- Verify Python 3 is available on your server

### Results Not Updating
- Check cron job is running: `crontab -l`
- Verify cron job output: `tail -f /tmp/printer_scan.log`
- Ensure results file is being created: `ls -la /tmp/printer_scan_results.json`

## Manual Printer Setup
If automatic scanning doesn't work, you can manually add printers:
1. Go to Printer Setup in the application
2. Select "WiFi Printer"
3. Enter printer IP address and port (usually 9100)
4. Click "Connect"

## Support
For issues or questions, check:
- Application logs
- Cron job logs: `/tmp/printer_scan.log`
- Agent results: `/tmp/printer_scan_results.json`












