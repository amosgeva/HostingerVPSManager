"""
Secure credential storage via the OS-native keyring.

The `keyring` library auto-selects the appropriate backend per platform:
Windows Credential Manager on Windows, Keychain on macOS, and Secret
Service / libsecret (KWallet/GNOME Keyring) on Linux. Linux users
without a running secret-service daemon can install
`keyrings.cryptfile` for an encrypted file fallback.

Supports multiple Hostinger accounts with named tokens.
"""

import contextlib
import json
import logging
from dataclasses import asdict, dataclass

import keyring

# Constants
SERVICE_NAME = "HostingerVPSManager"
ACCOUNTS_KEY = "accounts_list"
ACCOUNT_KEY_PREFIX = "account_"  # nosec B105

logger = logging.getLogger(__name__)
logger.info("Keyring backend: %s", keyring.get_keyring().__class__.__name__)


@dataclass
class Account:
    """Represents a Hostinger account."""

    name: str
    id: str  # Unique identifier for the account


class CredentialManager:
    """Manages secure storage of API credentials via the OS-native keyring."""

    def __init__(self):
        self.service_name = SERVICE_NAME

    def get_accounts(self) -> list[Account]:
        """Get list of all stored accounts."""
        try:
            accounts_json = keyring.get_password(self.service_name, ACCOUNTS_KEY)
            if accounts_json:
                accounts_data = json.loads(accounts_json)
                return [Account(**acc) for acc in accounts_data]
            return []
        except Exception as e:
            logger.error(f"Failed to get accounts: {e}")
            return []

    def _save_accounts(self, accounts: list[Account]) -> bool:
        """Save the accounts list."""
        try:
            accounts_data = [asdict(acc) for acc in accounts]
            keyring.set_password(self.service_name, ACCOUNTS_KEY, json.dumps(accounts_data))
            return True
        except Exception as e:
            logger.error(f"Failed to save accounts: {e}")
            return False

    def add_account(self, name: str, token: str) -> Account | None:
        """
        Add a new account with its API token.

        Args:
            name: Display name for the account
            token: The Hostinger API token

        Returns:
            The created Account, or None if failed
        """
        try:
            # Generate unique ID
            import uuid

            account_id = str(uuid.uuid4())[:8]

            # Store token
            keyring.set_password(self.service_name, f"{ACCOUNT_KEY_PREFIX}{account_id}", token)

            # Add to accounts list
            accounts = self.get_accounts()
            account = Account(name=name, id=account_id)
            accounts.append(account)
            self._save_accounts(accounts)

            logger.info(f"Account '{name}' added successfully")
            return account
        except Exception as e:
            logger.error(f"Failed to add account: {e}")
            return None

    def update_account(self, account_id: str, name: str = None, token: str = None) -> bool:
        """Update an existing account."""
        try:
            accounts = self.get_accounts()
            for acc in accounts:
                if acc.id == account_id:
                    if name:
                        acc.name = name
                    if token:
                        keyring.set_password(
                            self.service_name, f"{ACCOUNT_KEY_PREFIX}{account_id}", token
                        )
                    self._save_accounts(accounts)
                    return True
            return False
        except Exception as e:
            logger.error(f"Failed to update account: {e}")
            return False

    def delete_account(self, account_id: str) -> bool:
        """Delete an account and its token."""
        try:
            # Delete token; the user may have already removed it from the
            # OS credential store outside the app.
            with contextlib.suppress(keyring.errors.PasswordDeleteError):
                keyring.delete_password(self.service_name, f"{ACCOUNT_KEY_PREFIX}{account_id}")

            # Remove from accounts list
            accounts = self.get_accounts()
            accounts = [acc for acc in accounts if acc.id != account_id]
            self._save_accounts(accounts)

            logger.info(f"Account {account_id} deleted successfully")
            return True
        except Exception as e:
            logger.error(f"Failed to delete account: {e}")
            return False

    def get_token(self, account_id: str) -> str | None:
        """Get the API token for a specific account."""
        try:
            return keyring.get_password(self.service_name, f"{ACCOUNT_KEY_PREFIX}{account_id}")
        except Exception as e:
            logger.error(f"Failed to get token: {e}")
            return None

    def has_accounts(self) -> bool:
        """Check if any accounts are stored."""
        return len(self.get_accounts()) > 0

    # Legacy support - store/get single token
    def store_api_token(self, token: str) -> bool:
        """Legacy: Store a single API token (creates default account)."""
        account = self.add_account("Default Account", token)
        return account is not None

    def get_api_token(self) -> str | None:
        """Legacy: Get the first account's token."""
        accounts = self.get_accounts()
        if accounts:
            return self.get_token(accounts[0].id)
        return None

    def has_api_token(self) -> bool:
        """Legacy: Check if any token exists."""
        return self.has_accounts()


# Singleton instance
_credential_manager: CredentialManager | None = None


def get_credential_manager() -> CredentialManager:
    """Get the singleton CredentialManager instance."""
    global _credential_manager
    if _credential_manager is None:
        _credential_manager = CredentialManager()
    return _credential_manager
