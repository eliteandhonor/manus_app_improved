# Automated Login Manager

A secure application for managing website credentials and automating logins using browser automation.

## Features

- **Secure Credential Storage**: All credentials are encrypted using strong Fernet symmetric encryption with PBKDF2 key derivation
- **Enhanced Security**: Secure file permissions, memory clearing, and protection against timing attacks
- **Modular Browser Automation**: Flexible strategy pattern for different login methods (Form, Google, System Browser)
- **Asynchronous Support**: Full async/await pattern support for improved performance and responsiveness
- **Browser Automation**: Uses Playwright to automate logins across multiple browsers (Chrome, Firefox, Edge)
- **Bonus Site Tracking**: Mark sites that offer free credit or trial bonuses
- **CAPTCHA & 2FA Detection**: Automatically detects and pauses for user intervention when needed
- **Dual Interface**: Both GUI (Tkinter) and CLI interfaces available
- **Cross-Platform**: Works on Windows, macOS, and Linux
- **Comprehensive Testing**: Extensive test suite with pytest for reliability and maintainability

## Installation

### Prerequisites

- Python 3.8 or higher
- Pip package manager

### Setup

1. Clone or download this repository
2. Install required dependencies:

```bash
pip install -r requirements.txt
```

3. Install browser drivers:

```bash
playwright install
```

## Usage

### GUI Version

To start the application with the graphical user interface:

```bash
python main.py
```

On first run, you'll be prompted to create a master password. This password encrypts all your stored credentials.

### CLI Version

The CLI version provides the same functionality for headless environments or automation:

#### Initialize the application:

```bash
python cli.py init
```

Or non-interactively:

```bash
python cli.py init --password "your_master_password" --no-confirm
```

#### Add website credentials:

```bash
python cli.py add example.com username --password "website_password" --has-bonus
```

#### List stored credentials:

```bash
python cli.py list
```

Or only sites with bonuses:

```bash
python cli.py list --bonus-only
```

#### Remove website credentials:

```bash
python cli.py remove example.com
```

#### Automate logins:

```bash
python cli.py login
```

Or for specific sites:

```bash
python cli.py login example.com another-site.com
```

Or only sites with bonuses:

```bash
python cli.py login --bonus-only
```

#### Change master password:

```bash
python cli.py change-password
```

## Security Considerations

- All credentials are encrypted using Fernet symmetric encryption with PBKDF2HMAC key derivation (600,000 iterations)
- 32-byte cryptographically secure random salt for key derivation
- Secure file permissions (0600 for credential files, 0700 for data directories)
- The master password is never stored, only used to derive encryption keys
- Sensitive data is cleared from memory when no longer needed
- Atomic file operations to prevent corruption during writes
- Credentials are stored locally and never transmitted externally
- Browser automation is visible by default to maintain transparency

## Handling Google Logins

The application now provides special handling for Google OAuth logins:

1. Automatically detects Google login buttons on websites
2. Offers two login methods:
   - **Playwright Automation**: Attempts to automate the Google login process
   - **System Browser**: Opens your default browser for manual login when automation is detected as a bot

To specify the Google login method:

```bash
python cli.py login example.com --google-method playwright
```

Or:

```bash
python cli.py login example.com --google-method system_browser
```

## Handling CAPTCHAs and Two-Factor Authentication

When the application detects a CAPTCHA or two-factor authentication:

1. The automation will pause
2. You'll be notified to complete the verification manually
3. After completion, the automation will continue

## Asynchronous API Usage

For developers integrating with the application, an asynchronous API is available:

```python
import asyncio
from src.utils.config_manager import ConfigManager
from src.core.app_core import AppCore

async def main():
    # Initialize components
    config = ConfigManager()
    app = AppCore(config)
    await app.initialize_async("master_password")
    
    # Login to a website
    result = await app.login_to_website_async("https://example.com")
    print(f"Login result: {result}")
    
    # Clean up
    await app.close_async()

# Run the async function
asyncio.run(main())
```

## Testing

The application includes a comprehensive test suite using pytest:

```bash
# Run all tests
pytest

# Run specific test modules
pytest tests/test_credential_manager.py

# Run with coverage report
pytest --cov=src
```

## Troubleshooting

### Browser Automation Issues

- Ensure browser drivers are installed: `playwright install`
- Try a different browser with `--browser firefox` or `--browser webkit`
- Update Playwright: `pip install --upgrade playwright`
- For Google login issues, try the system browser method: `--google-method system_browser`

### Login Detection Problems

- Some websites use complex login forms that may not be detected automatically
- Try updating the site's entry with more specific notes about the login form
- Check logs for detailed information about the login process

### GUI Not Working

- Ensure tkinter is installed for your Python version
- On Linux: `sudo apt-get install python3-tk`
- Use the CLI version as an alternative

## Configuration

The application supports various configuration options:

```bash
# Set browser type
python cli.py config set browser firefox

# Enable headless mode
python cli.py config set headless true

# Set log level
python cli.py config set log_level DEBUG

# View all configuration
python cli.py config list
```

Environment variables can also be used for configuration:

- `AUTO_LOGIN_CONFIG_DIR`: Directory for configuration files
- `AUTO_LOGIN_BROWSER`: Browser to use (chromium, firefox, webkit)
- `AUTO_LOGIN_HEADLESS`: Run in headless mode (true/false)
- `AUTO_LOGIN_LOG_LEVEL`: Logging level (DEBUG, INFO, WARNING, ERROR)

## Maintenance

Websites may change their login forms over time. If a login stops working:

1. Remove the website entry
2. Add it again with updated credentials
3. Test the login manually

## License

This project is licensed for personal use only.

## Disclaimer

This tool is intended for personal use to manage your own accounts. Always respect website terms of service and never use for unauthorized access.
