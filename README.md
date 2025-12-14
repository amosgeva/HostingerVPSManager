# Hostinger VPS Manager

A modern desktop application for managing your Hostinger VPS infrastructure. Built with Python and PyQt6, this tool provides a user-friendly interface to monitor and control your virtual private servers.

![Python](https://img.shields.io/badge/Python-3.10+-blue.svg)
![PyQt6](https://img.shields.io/badge/PyQt6-6.6+-green.svg)
![License](https://img.shields.io/badge/License-MIT-yellow.svg)

## Features

### Server Management
- **Multi-Account Support**: Manage multiple Hostinger accounts from a single interface
- **Server Overview**: View all your VPS instances with real-time status
- **Power Controls**: Start, stop, restart, and force restart servers
- **Server Information**: View detailed server specs (CPU, RAM, Disk, Bandwidth)

### Monitoring
- **Real-time Metrics**: CPU usage, RAM usage, and disk utilization with visual charts
- **Uptime Tracking**: Monitor server uptime
- **Auto-refresh**: Configurable automatic data refresh (10-300 seconds)

### Security
- **Firewall Management**: View, add, edit, and delete firewall rules
- **SSH Key Management**: Manage SSH keys for secure server access
- **Malware Scanner (Monarx)**: Monitor malware scan status and metrics
- **Secure Credential Storage**: API tokens stored securely using Windows Credential Manager

### Additional Features
- **System Tray Integration**: Minimize to tray, notifications for status changes
- **Data Export**: Export logs and metrics to CSV format
- **Subscription Info**: View billing and subscription details
- **Data Center Info**: See server location (city, country)
- **Action Logs**: Track all server actions with timestamps

## Installation

### Prerequisites
- Python 3.10 or higher
- Windows 10/11 (for Windows Credential Manager support)

### From Source
```bash
# Clone the repository
git clone https://github.com/yourusername/hostinger-vps-manager.git
cd hostinger-vps-manager

# Install dependencies
pip install -r requirements.txt

# Run the application
python run.py
```

### Build Executable
```bash
# Build standalone executable
pyinstaller HostingerVPSManager.spec --clean
```
The executable will be created at `dist/HostingerVPSManager.exe`

## Configuration

### API Token Setup
1. Log in to your [Hostinger Dashboard](https://hpanel.hostinger.com/)
2. Navigate to Account Settings → API Tokens
3. Generate a new API token with VPS permissions
4. In the app, click "Manage Accounts" → "Add Account"
5. Enter a name and paste your API token

### Settings
Access settings via the ⚙ Settings button:
- **Auto-refresh interval**: How often to refresh data (default: 30s)
- **Minimize to tray on close**: Keep app running in system tray
- **Start minimized**: Launch app minimized to tray
- **Enable notifications**: Show alerts for server status changes

## Project Structure
```
Hostinger.API/
├── assets/                 # Application icons
│   ├── hostinger.ico
│   └── hostinger.png
├── src/                    # Source code
│   ├── __init__.py
│   ├── api_client.py       # Hostinger API client
│   ├── credentials.py      # Secure credential storage
│   ├── main.py             # Application entry point
│   ├── main_window.py      # Main GUI window
│   └── styles.py           # UI styles and constants
├── .gitignore
├── HostingerVPSManager.spec  # PyInstaller spec file
├── README.md
├── requirements.txt
└── run.py                  # Run script
```

## Security

- **No hardcoded credentials**: All API tokens are stored using Windows Credential Manager
- **Secure transmission**: All API calls use HTTPS
- **Local storage only**: No data is sent to third-party services

## API Reference

This application uses the [Hostinger API](https://developers.hostinger.com/). Supported endpoints:
- VPS Virtual Machines
- VPS Firewall
- VPS SSH Keys (Public Keys)
- VPS Malware Scanner (Monarx)
- VPS Data Centers
- Billing Subscriptions

## Requirements

See `requirements.txt`:
- PyQt6 >= 6.6.0
- requests >= 2.31.0
- keyring >= 24.3.0
- pywin32 >= 306
- matplotlib >= 3.8.0
- psutil >= 5.9.0

## Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- [Hostinger](https://www.hostinger.com/) for their VPS API
- [PyQt6](https://www.riverbankcomputing.com/software/pyqt/) for the GUI framework
- [Keyring](https://github.com/jaraco/keyring) for secure credential storage

