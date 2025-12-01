#!/usr/bin/env python3
"""
Enhanced Local Network Thermal Printer Scanner Agent
For use with cPanel and shared hosting environments

This script scans for thermal printers on the local network and can:
- Run as a cron job for automatic discovery
- Be called via API from the web application
- Store results in a database or JSON file for the web app to read
- Auto-connect to discovered printers

Usage:
    python3 scan_printers_agent.py [network_range] [--api-url URL] [--save-db]
    
    Examples:
    python3 scan_printers_agent.py 192.168.1
    python3 scan_printers_agent.py 192.168.1 --api-url https://yourdomain.com/api/agent/printer-found
    python3 scan_printers_agent.py 192.168.1 --save-db
    
    Cron job (scan every 5 minutes):
    */5 * * * * /usr/bin/python3 /path/to/scan_printers_agent.py 192.168.1 >> /tmp/printer_scan.log 2>&1
"""

import socket
import sys
import json
import time
import os
import argparse
import requests
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

# Common thermal printer ports (prioritize thermal printer ports)
THERMAL_PORTS = [9100, 9101, 9102, 515, 631]  # Removed 80, 443 as they're not thermal printer ports

def test_printer_port(ip, port, timeout=1.0):
    """Test if a specific IP:port is a thermal printer with enhanced detection"""
    sock = None
    test_sock = None
    try:
        # First, test if port is open
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(timeout)
        result = sock.connect_ex((ip, port))
        
        if result == 0:
            # Port is open, now test if it's a thermal printer
            try:
                test_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                test_sock.settimeout(0.5)
                test_sock.connect((ip, port))
                
                # Send ESC/POS initialization command (standard for thermal printers)
                test_sock.send(b'\x1B\x40')  # ESC @ - Initialize printer
                time.sleep(0.1)
                
                # Try to get printer model/status (optional, some printers don't respond)
                try:
                    test_sock.send(b'\x1D\x49\x01')  # GS I 1 - Get printer ID
                    time.sleep(0.1)
                except:
                    pass
                
                # If we got here, it's likely a thermal printer
                # Try to get more info via HTTP if port 80 is available
                printer_name = f'Thermal Printer at {ip}:{port}'
                printer_model = 'ESC/POS Thermal Printer'
                
                # Try to get printer name via HTTP (some printers have web interfaces)
                if port == 9100:  # Standard thermal printer port
                    try:
                        http_sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                        http_sock.settimeout(0.3)
                        if http_sock.connect_ex((ip, 80)) == 0:
                            http_sock.close()
                            # Could potentially fetch printer name from HTTP, but skip for now
                    except:
                        pass
                
                return {
                    'ip': ip,
                    'port': port,
                    'name': printer_name,
                    'model': printer_model,
                    'type': 'thermal',
                    'status': 'available',
                    'discovery_method': 'Network Scan',
                    'timestamp': datetime.now().isoformat(),
                    'verified': True  # Port responded to ESC/POS commands
                }
            except Exception as e:
                # Port is open but might not be a thermal printer
                # Only return if it's a known thermal printer port
                if port in [9100, 9101, 9102]:
                    return {
                        'ip': ip,
                        'port': port,
                        'name': f'Printer at {ip}:{port}',
                        'model': 'Unknown Thermal Printer',
                        'type': 'thermal',
                        'status': 'available',
                        'discovery_method': 'Network Scan',
                        'timestamp': datetime.now().isoformat(),
                        'verified': False  # Port open but didn't respond to ESC/POS
                    }
        sock.close()
    except Exception as e:
        pass
    finally:
        try:
            if sock:
                sock.close()
        except:
            pass
        try:
            if test_sock:
                test_sock.close()
        except:
            pass
    return None

def scan_network_range(network_base, start=1, end=254, max_workers=20):
    """Scan a network range for thermal printers"""
    discovered_printers = []
    
    print(f"Scanning {network_base}.{start}-{end} for thermal printers...")
    print(f"Testing ports: {', '.join(map(str, THERMAL_PORTS))}")
    
    def scan_ip(ip_num):
        ip = f"{network_base}.{ip_num}"
        printers_found = []
        
        for port in THERMAL_PORTS:
            result = test_printer_port(ip, port)
            if result:
                printers_found.append(result)
                print(f"[FOUND] {result['name']} - {result['ip']}:{result['port']}")
        
        return printers_found
    
    # Use threading for faster scanning
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        futures = [executor.submit(scan_ip, i) for i in range(start, end + 1)]
        
        for future in as_completed(futures, timeout=60):
            try:
                results = future.result(timeout=2)
                if results:
                    discovered_printers.extend(results)
            except Exception as e:
                continue
    
    return discovered_printers

def scan_arp_table(network_base):
    """Scan ARP table for active devices and test for printers"""
    discovered_printers = []
    
    try:
        import subprocess
        import re
        
        print("Scanning ARP table for active devices...")
        result = subprocess.run(['arp', '-a'], capture_output=True, text=True, timeout=10)
        
        if result.returncode == 0:
            # Extract IPs from ARP table
            ips = set(re.findall(r'(\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})', result.stdout))
            
            # Filter to our network
            network_prefix = '.'.join(network_base.split('.')[:3])
            network_ips = [ip for ip in ips if ip.startswith(network_prefix)]
            
            print(f"Found {len(network_ips)} active devices in ARP table")
            
            # Test each IP for printer ports
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                for ip in network_ips:
                    for port in THERMAL_PORTS:
                        futures.append(executor.submit(test_printer_port, ip, port))
                
                for future in as_completed(futures, timeout=30):
                    try:
                        result = future.result(timeout=1)
                        if result:
                            discovered_printers.append(result)
                            print(f"[FOUND] {result['name']} - {result['ip']}:{result['port']}")
                    except:
                        continue
    except Exception as e:
        print(f"[WARNING] ARP scan failed: {e}")
    
    return discovered_printers

def send_to_api(api_url, printer_data):
    """Send discovered printer to web app API"""
    try:
        response = requests.post(
            api_url,
            json=printer_data,
            headers={'Content-Type': 'application/json'},
            timeout=5
        )
        if response.status_code == 200:
            print(f"[API] Successfully sent printer {printer_data['ip']} to web app")
            return True
        else:
            print(f"[API] Failed to send printer: HTTP {response.status_code}")
            return False
    except Exception as e:
        print(f"[API] Error sending to API: {e}")
        return False

def save_to_database(printer_data):
    """Save printer to database (if database connection available)"""
    # This would connect to your database and save the printer
    # For now, we'll save to a JSON file that the web app can read
    db_file = os.path.join(os.path.dirname(__file__), 'discovered_printers.json')
    try:
        # Load existing printers
        if os.path.exists(db_file):
            with open(db_file, 'r') as f:
                printers = json.load(f)
        else:
            printers = []
        
        # Check if printer already exists
        existing = next((p for p in printers if p['ip'] == printer_data['ip'] and p['port'] == printer_data['port']), None)
        if existing:
            # Update existing
            existing.update(printer_data)
            existing['last_seen'] = datetime.now().isoformat()
        else:
            # Add new
            printer_data['first_seen'] = datetime.now().isoformat()
            printer_data['last_seen'] = datetime.now().isoformat()
            printers.append(printer_data)
        
        # Save back to file
        with open(db_file, 'w') as f:
            json.dump(printers, f, indent=2)
        
        print(f"[DB] Saved printer {printer_data['ip']} to database")
        return True
    except Exception as e:
        print(f"[DB] Error saving to database: {e}")
        return False

def main():
    """Main scanning function with enhanced features"""
    parser = argparse.ArgumentParser(description='Thermal Printer Scanner Agent')
    parser.add_argument('network_range', nargs='?', help='Network range (e.g., 192.168.1)')
    parser.add_argument('--api-url', help='API URL to send discovered printers to')
    parser.add_argument('--save-db', action='store_true', help='Save printers to database/file')
    parser.add_argument('--scan-range', default='1-254', help='IP range to scan (e.g., 1-100)')
    
    args = parser.parse_args()
    
    # Get network range
    if args.network_range:
        network_range = args.network_range
    else:
        # Try to auto-detect
        try:
            hostname = socket.gethostname()
            local_ip = socket.gethostbyname(hostname)
            if local_ip.startswith('192.168.') or local_ip.startswith('10.') or local_ip.startswith('172.'):
                network_range = '.'.join(local_ip.split('.')[:-1])
            else:
                network_range = '192.168.1'
        except:
            network_range = '192.168.1'
    
    # Parse scan range
    if '-' in args.scan_range:
        start, end = map(int, args.scan_range.split('-'))
    else:
        start, end = 1, 254
    
    print(f"=== Enhanced Thermal Printer Scanner Agent ===")
    print(f"Network Range: {network_range}")
    print(f"IP Range: {network_range}.{start}-{end}")
    print(f"Start Time: {datetime.now().isoformat()}")
    if args.api_url:
        print(f"API URL: {args.api_url}")
    if args.save_db:
        print(f"Database Save: Enabled")
    print("=" * 60)
    
    all_printers = []
    
    # Method 1: Network Range Scan
    print("\n[Method 1] Scanning network range for thermal printers...")
    network_printers = scan_network_range(network_range, start=start, end=end)
    all_printers.extend(network_printers)
    
    # Method 2: ARP Table Scan (faster, only active devices)
    print("\n[Method 2] Scanning ARP table for active devices...")
    arp_printers = scan_arp_table(network_range)
    # Remove duplicates
    existing_ips = {(p['ip'], p['port']) for p in all_printers}
    for printer in arp_printers:
        if (printer['ip'], printer['port']) not in existing_ips:
            all_printers.append(printer)
    
    # Filter to only verified thermal printers
    verified_printers = [p for p in all_printers if p.get('verified', False) or p.get('type') == 'thermal']
    
    # Output results
    print("\n" + "=" * 60)
    print(f"Scan Complete: {datetime.now().isoformat()}")
    print(f"Total Devices Found: {len(all_printers)}")
    print(f"Verified Thermal Printers: {len(verified_printers)}")
    print("=" * 60)
    
    # Send to API if provided
    if args.api_url and verified_printers:
        print(f"\n[Sending] Sending {len(verified_printers)} printers to API...")
        for printer in verified_printers:
            send_to_api(args.api_url, printer)
    
    # Save to database if requested
    if args.save_db and verified_printers:
        print(f"\n[Saving] Saving {len(verified_printers)} printers to database...")
        for printer in verified_printers:
            save_to_database(printer)
    
    # Output as JSON for API consumption
    output = {
        'success': True,
        'printers': verified_printers,  # Only return verified thermal printers
        'all_devices': all_printers,  # Include all devices for reference
        'count': len(verified_printers),
        'network_range': network_range,
        'scan_time': datetime.now().isoformat(),
        'scan_methods': ['network_range', 'arp_table']
    }
    
    # Save to file for API to read (in web app directory or /tmp)
    output_file = os.path.join(os.path.dirname(__file__), 'printer_scan_results.json')
    try:
        with open(output_file, 'w') as f:
            json.dump(output, f, indent=2)
        print(f"\n[File] Results saved to: {output_file}")
    except Exception as e:
        # Try /tmp as fallback
        output_file = '/tmp/printer_scan_results.json'
        try:
            with open(output_file, 'w') as f:
                json.dump(output, f, indent=2)
            print(f"\n[File] Results saved to: {output_file}")
        except Exception as e2:
            print(f"\n[WARNING] Could not save results to file: {e2}")
    
    # Print summary
    if verified_printers:
        print("\n[Summary] Verified Thermal Printers Found:")
        for printer in verified_printers:
            print(f"  ✓ {printer['name']} - {printer['ip']}:{printer['port']} ({printer.get('model', 'Unknown')})")
    else:
        print("\n[Summary] No verified thermal printers found. Check:")
        print("  - Printers are powered on and connected to network")
        print("  - Network range is correct")
        print("  - Firewall allows connections to printer ports")
    
    # Also print JSON to stdout (for cron job logging)
    print("\n" + json.dumps(output, indent=2))
    
    return output

if __name__ == '__main__':
    try:
        main()
    except KeyboardInterrupt:
        print("\n\nScan interrupted by user")
        sys.exit(1)
    except Exception as e:
        print(f"\n[ERROR] Scan failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)












