"""
Hostinger API Client for VPS Management.
Provides methods to interact with all VPS-related endpoints.
"""

import requests
import logging
from typing import Optional, Dict, List
from datetime import datetime, timedelta, timezone
from dataclasses import dataclass

from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .app.constants import (
    API_BACKOFF_FACTOR,
    API_BASE_URL,
    API_MAX_RETRIES,
    API_RETRY_STATUSES,
    API_TIMEOUT_SECONDS,
    METRIC_AVERAGING_HOURS,
)

logger = logging.getLogger(__name__)


@dataclass
class VirtualMachine:
    """Represents a VPS instance."""
    id: int
    hostname: str
    state: str
    plan: Optional[str]
    cpus: int
    memory: int  # MB
    disk: int  # MB
    bandwidth: int  # MB
    ipv4: List[Dict]
    ipv6: Optional[List[Dict]]
    firewall_group_id: Optional[int]
    template: Optional[Dict]
    created_at: str
    actions_lock: str
    ns1: Optional[str] = None
    ns2: Optional[str] = None
    subscription_id: Optional[str] = None
    data_center_id: Optional[int] = None


@dataclass
class FirewallRule:
    """Represents a firewall rule."""
    id: int
    protocol: str
    port: str
    source: str
    source_detail: Optional[str]


@dataclass
class Firewall:
    """Represents a firewall configuration."""
    id: int
    name: str
    is_synced: bool
    rules: List[FirewallRule]


@dataclass
class Action:
    """Represents a VPS action/event."""
    id: int
    name: str
    state: str
    created_at: str
    updated_at: Optional[str]


@dataclass
class Backup:
    """Represents a VPS backup."""
    id: int
    location: str
    created_at: str


@dataclass
class Metrics:
    """Represents VPS metrics data."""
    cpu: List[Dict]
    memory: List[Dict]
    disk: List[Dict]
    network: List[Dict]
    uptime: List[Dict]


@dataclass
class PublicKey:
    """Represents an SSH public key."""
    id: int
    name: str
    key: str


@dataclass
class MalwareScanMetrics:
    """Represents Monarx malware scanner metrics."""
    records: int
    malicious: int
    compromised: int
    scanned_files: int
    scan_started_at: Optional[str]
    scan_ended_at: Optional[str]


@dataclass
class Subscription:
    """Represents a billing subscription."""
    id: str
    name: str
    status: str  # active, paused, cancelled, not_renewing, transferred, in_trial, future
    billing_period: int
    billing_period_unit: str
    currency_code: str
    total_price: int  # in cents
    renewal_price: int  # in cents
    is_auto_renewed: bool
    created_at: str
    expires_at: Optional[str]
    next_billing_at: Optional[str]


@dataclass
class DataCenter:
    """Represents a VPS data center."""
    id: int
    name: Optional[str]
    location: Optional[str]  # Country code (e.g., "us")
    city: Optional[str]
    continent: Optional[str]


class HostingerAPIError(Exception):
    """Custom exception for API errors."""
    def __init__(self, message: str, status_code: int = None, correlation_id: str = None):
        self.message = message
        self.status_code = status_code
        self.correlation_id = correlation_id
        super().__init__(self.message)


class HostingerAPIClient:
    """Client for interacting with the Hostinger API."""
    
    def __init__(self, api_token: str):
        self.api_token = api_token
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_token}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        })

        # Retry transient failures (5xx, 429) with exponential backoff and
        # respect Retry-After. POST/PUT/DELETE included on the assumption
        # that VPS actions are server-idempotent (start when already started
        # is a no-op).
        retry = Retry(
            total=API_MAX_RETRIES,
            backoff_factor=API_BACKOFF_FACTOR,
            status_forcelist=API_RETRY_STATUSES,
            allowed_methods=frozenset(["GET", "HEAD", "OPTIONS", "POST", "PUT", "DELETE"]),
            respect_retry_after_header=True,
            raise_on_status=False,
        )
        adapter = HTTPAdapter(max_retries=retry)
        self.session.mount("https://", adapter)
        self.session.mount("http://", adapter)

        # Lazy caches for endpoints whose contents change rarely. Populated
        # by the list-fetch methods; consulted by *_by_id helpers to avoid
        # N+1 round-trips.
        self._data_centers_index: Optional[Dict[int, "DataCenter"]] = None
        self._subscriptions_index: Optional[Dict[str, "Subscription"]] = None

    def _request(self, method: str, endpoint: str, data: Dict = None, params: Dict = None) -> Dict:
        """Make an API request."""
        url = f"{API_BASE_URL}{endpoint}"
        try:
            response = self.session.request(
                method, url, json=data, params=params, timeout=API_TIMEOUT_SECONDS
            )
            
            if response.status_code == 401:
                raise HostingerAPIError("Unauthorized - Invalid API token", 401)
            elif response.status_code == 429:
                raise HostingerAPIError("Rate limit exceeded", 429)
            elif response.status_code >= 400:
                error_data = response.json() if response.text else {}
                raise HostingerAPIError(
                    error_data.get("message", f"API error: {response.status_code}"),
                    response.status_code,
                    error_data.get("correlation_id")
                )
            
            return response.json() if response.text else {}
        except requests.exceptions.RequestException as e:
            logger.error(f"Request failed: {e}")
            raise HostingerAPIError(f"Network error: {str(e)}")
    
    def _get(self, endpoint: str, params: Dict = None) -> Dict:
        return self._request("GET", endpoint, params=params)
    
    def _post(self, endpoint: str, data: Dict = None) -> Dict:
        return self._request("POST", endpoint, data=data)
    
    def _put(self, endpoint: str, data: Dict = None) -> Dict:
        return self._request("PUT", endpoint, data=data)
    
    def _delete(self, endpoint: str, data: Dict = None) -> Dict:
        return self._request("DELETE", endpoint, data=data)
    
    # Virtual Machine endpoints
    def get_virtual_machines(self) -> List[VirtualMachine]:
        """Get all virtual machines."""
        response = self._get("/api/vps/v1/virtual-machines")
        return [self._parse_vm(vm) for vm in response]
    
    def get_virtual_machine(self, vm_id: int) -> VirtualMachine:
        """Get details of a specific virtual machine."""
        response = self._get(f"/api/vps/v1/virtual-machines/{vm_id}")
        return self._parse_vm(response)
    
    def _parse_vm(self, data: Dict) -> VirtualMachine:
        """Parse VM data into VirtualMachine object."""
        return VirtualMachine(
            id=data.get("id"),
            hostname=data.get("hostname", ""),
            state=data.get("state", "unknown"),
            plan=data.get("plan"),
            cpus=data.get("cpus", 0),
            memory=data.get("memory", 0),
            disk=data.get("disk", 0),
            bandwidth=data.get("bandwidth", 0),
            ipv4=data.get("ipv4", []),
            ipv6=data.get("ipv6"),
            firewall_group_id=data.get("firewall_group_id"),
            template=data.get("template"),
            created_at=data.get("created_at", ""),
            actions_lock=data.get("actions_lock", "unlocked"),
            ns1=data.get("ns1"),
            ns2=data.get("ns2"),
            subscription_id=data.get("subscription_id"),
            data_center_id=data.get("data_center_id")
        )

    # VM Control endpoints
    def start_vm(self, vm_id: int) -> Action:
        """Start a virtual machine."""
        response = self._post(f"/api/vps/v1/virtual-machines/{vm_id}/start")
        return self._parse_action(response)

    def stop_vm(self, vm_id: int) -> Action:
        """Stop a virtual machine."""
        response = self._post(f"/api/vps/v1/virtual-machines/{vm_id}/stop")
        return self._parse_action(response)

    def restart_vm(self, vm_id: int) -> Action:
        """Restart a virtual machine."""
        response = self._post(f"/api/vps/v1/virtual-machines/{vm_id}/restart")
        return self._parse_action(response)

    # Metrics endpoint
    def get_metrics(self, vm_id: int, date_from: datetime = None, date_to: datetime = None) -> Dict:
        """Get metrics for a virtual machine."""
        if date_from is None:
            date_from = datetime.now(timezone.utc) - timedelta(hours=METRIC_AVERAGING_HOURS)
        if date_to is None:
            date_to = datetime.now(timezone.utc)

        params = {
            "date_from": date_from.strftime("%Y-%m-%dT%H:%M:%SZ"),
            "date_to": date_to.strftime("%Y-%m-%dT%H:%M:%SZ")
        }
        return self._get(f"/api/vps/v1/virtual-machines/{vm_id}/metrics", params=params)

    # Actions/Logs endpoints
    def get_actions(self, vm_id: int, page: int = 1) -> List[Action]:
        """Get actions history for a virtual machine."""
        response = self._get(f"/api/vps/v1/virtual-machines/{vm_id}/actions", params={"page": page})
        data = response.get("data", response) if isinstance(response, dict) else response
        return [self._parse_action(a) for a in data]

    def get_action(self, vm_id: int, action_id: int) -> Action:
        """Get details of a specific action."""
        response = self._get(f"/api/vps/v1/virtual-machines/{vm_id}/actions/{action_id}")
        return self._parse_action(response)

    def _parse_action(self, data: Dict) -> Action:
        """Parse action data into Action object."""
        return Action(
            id=data.get("id"),
            name=data.get("name", ""),
            state=data.get("state", ""),
            created_at=data.get("created_at", ""),
            updated_at=data.get("updated_at")
        )

    # Firewall endpoints
    def get_firewalls(self, page: int = 1) -> List[Firewall]:
        """Get all firewalls."""
        response = self._get("/api/vps/v1/firewall", params={"page": page})
        data = response.get("data", response) if isinstance(response, dict) else response
        return [self._parse_firewall(f) for f in data]

    def get_firewall(self, firewall_id: int) -> Firewall:
        """Get details of a specific firewall."""
        response = self._get(f"/api/vps/v1/firewall/{firewall_id}")
        return self._parse_firewall(response)

    def create_firewall(self, name: str) -> Firewall:
        """Create a new firewall."""
        response = self._post("/api/vps/v1/firewall", data={"name": name})
        return self._parse_firewall(response)

    def delete_firewall(self, firewall_id: int) -> bool:
        """Delete a firewall."""
        self._delete(f"/api/vps/v1/firewall/{firewall_id}")
        return True

    def create_firewall_rule(self, firewall_id: int, protocol: str, port: str,
                             source: str, source_detail: str = None) -> FirewallRule:
        """Create a new firewall rule."""
        # source_detail is required by API - use "any" as default if not provided
        data = {
            "protocol": protocol,
            "port": port,
            "source": source,
            "source_detail": source_detail if source_detail else "any"
        }
        response = self._post(f"/api/vps/v1/firewall/{firewall_id}/rules", data=data)
        return self._parse_firewall_rule(response)

    def update_firewall_rule(self, firewall_id: int, rule_id: int, protocol: str,
                             port: str, source: str, source_detail: str = None) -> FirewallRule:
        """Update a firewall rule."""
        # source_detail is required by API - use "any" as default if not provided
        data = {
            "protocol": protocol,
            "port": port,
            "source": source,
            "source_detail": source_detail if source_detail else "any"
        }
        logger.info(f"Updating firewall rule: firewall_id={firewall_id}, rule_id={rule_id}, data={data}")
        response = self._put(f"/api/vps/v1/firewall/{firewall_id}/rules/{rule_id}", data=data)
        return self._parse_firewall_rule(response)

    def delete_firewall_rule(self, firewall_id: int, rule_id: int) -> bool:
        """Delete a firewall rule."""
        self._delete(f"/api/vps/v1/firewall/{firewall_id}/rules/{rule_id}")
        return True

    def activate_firewall(self, firewall_id: int, vm_id: int) -> Action:
        """Activate a firewall for a VM."""
        response = self._post(f"/api/vps/v1/firewall/{firewall_id}/activate/{vm_id}")
        return self._parse_action(response)

    def deactivate_firewall(self, firewall_id: int, vm_id: int) -> Action:
        """Deactivate a firewall for a VM."""
        response = self._post(f"/api/vps/v1/firewall/{firewall_id}/deactivate/{vm_id}")
        return self._parse_action(response)

    def sync_firewall(self, firewall_id: int, vm_id: int) -> Action:
        """Sync firewall rules to a VM."""
        logger.info(f"Syncing firewall: firewall_id={firewall_id}, vm_id={vm_id}")
        response = self._post(f"/api/vps/v1/firewall/{firewall_id}/sync/{vm_id}")
        logger.info(f"Sync firewall response: {response}")
        return self._parse_action(response)

    def _parse_firewall(self, data: Dict) -> Firewall:
        """Parse firewall data into Firewall object."""
        rules = [self._parse_firewall_rule(r) for r in data.get("rules", [])]
        return Firewall(
            id=data.get("id"),
            name=data.get("name", ""),
            is_synced=data.get("is_synced", False),
            rules=rules
        )

    def _parse_firewall_rule(self, data: Dict) -> FirewallRule:
        """Parse firewall rule data into FirewallRule object."""
        return FirewallRule(
            id=data.get("id"),
            protocol=data.get("protocol", ""),
            port=data.get("port", ""),
            source=data.get("source", ""),
            source_detail=data.get("source_detail")
        )

    # Backup endpoints
    def get_backups(self, vm_id: int, page: int = 1) -> List[Backup]:
        """Get backups for a virtual machine."""
        response = self._get(f"/api/vps/v1/virtual-machines/{vm_id}/backups", params={"page": page})
        data = response.get("data", response) if isinstance(response, dict) else response
        return [self._parse_backup(b) for b in data]

    def restore_backup(self, vm_id: int, backup_id: int) -> Action:
        """Restore a backup."""
        response = self._post(f"/api/vps/v1/virtual-machines/{vm_id}/backups/{backup_id}/restore")
        return self._parse_action(response)

    def _parse_backup(self, data: Dict) -> Backup:
        """Parse backup data into Backup object."""
        return Backup(
            id=data.get("id"),
            location=data.get("location", ""),
            created_at=data.get("created_at", "")
        )

    # Snapshot endpoints
    def get_snapshot(self, vm_id: int) -> Optional[Dict]:
        """Get snapshot for a virtual machine."""
        try:
            return self._get(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot")
        except HostingerAPIError:
            return None

    def create_snapshot(self, vm_id: int) -> Action:
        """Create a snapshot."""
        response = self._post(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot")
        return self._parse_action(response)

    def restore_snapshot(self, vm_id: int) -> Action:
        """Restore from snapshot."""
        response = self._post(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot/restore")
        return self._parse_action(response)

    def delete_snapshot(self, vm_id: int) -> Action:
        """Delete a snapshot."""
        response = self._delete(f"/api/vps/v1/virtual-machines/{vm_id}/snapshot")
        return self._parse_action(response)

    # SSH Public Key endpoints
    def get_public_keys(self, page: int = 1) -> List[PublicKey]:
        """Get all SSH public keys associated with the account."""
        response = self._get("/api/vps/v1/public-keys", params={"page": page})
        logger.info(f"Get public keys response: {response}")
        data = response.get("data", response) if isinstance(response, dict) else response
        keys = [self._parse_public_key(k) for k in data]
        logger.info(f"Parsed {len(keys)} public keys")
        return keys

    def create_public_key(self, name: str, key: str) -> PublicKey:
        """Create a new SSH public key."""
        data = {"name": name, "key": key}
        logger.info(f"Creating public key: name={name}, key={key[:50]}...")
        response = self._post("/api/vps/v1/public-keys", data=data)
        logger.info(f"Create public key response: {response}")
        return self._parse_public_key(response)

    def delete_public_key(self, key_id: int) -> None:
        """Delete an SSH public key."""
        self._delete(f"/api/vps/v1/public-keys/{key_id}")

    def _parse_public_key(self, data: Dict) -> PublicKey:
        """Parse public key data into PublicKey object."""
        return PublicKey(
            id=data.get("id"),
            name=data.get("name", ""),
            key=data.get("key", "")
        )

    # Malware Scanner (Monarx) endpoints
    def get_malware_metrics(self, vm_id: int) -> Optional[MalwareScanMetrics]:
        """Get malware scan metrics for a virtual machine."""
        try:
            response = self._get(f"/api/vps/v1/virtual-machines/{vm_id}/monarx")
            logger.info(f"Get malware metrics response: {response}")
            return self._parse_malware_metrics(response)
        except HostingerAPIError as e:
            logger.warning(f"Failed to get malware metrics: {e.message}")
            return None

    def install_monarx(self, vm_id: int) -> Action:
        """Install Monarx malware scanner on a virtual machine."""
        response = self._post(f"/api/vps/v1/virtual-machines/{vm_id}/monarx")
        logger.info(f"Install Monarx response: {response}")
        return self._parse_action(response)

    def uninstall_monarx(self, vm_id: int) -> Action:
        """Uninstall Monarx malware scanner from a virtual machine."""
        response = self._delete(f"/api/vps/v1/virtual-machines/{vm_id}/monarx")
        logger.info(f"Uninstall Monarx response: {response}")
        return self._parse_action(response)

    def _parse_malware_metrics(self, data: Dict) -> MalwareScanMetrics:
        """Parse malware metrics data into MalwareScanMetrics object."""
        return MalwareScanMetrics(
            records=data.get("records", 0),
            malicious=data.get("malicious", 0),
            compromised=data.get("compromised", 0),
            scanned_files=data.get("scanned_files", 0),
            scan_started_at=data.get("scan_started_at"),
            scan_ended_at=data.get("scan_ended_at")
        )

    # Billing: Subscriptions
    def get_subscriptions(self) -> List[Subscription]:
        """Get all subscriptions for the account."""
        response = self._get("/api/billing/v1/subscriptions")
        logger.info(f"Get subscriptions response: {response}")
        subscriptions = [self._parse_subscription(s) for s in response]
        logger.info(f"Parsed {len(subscriptions)} subscriptions")
        self._subscriptions_index = {s.id: s for s in subscriptions}
        return subscriptions

    def get_subscription_by_id(self, subscription_id: str) -> Optional[Subscription]:
        """Get a specific subscription by ID, populating the cache on first use."""
        if self._subscriptions_index is None:
            self.get_subscriptions()
        return (self._subscriptions_index or {}).get(subscription_id)

    def _parse_subscription(self, data: Dict) -> Subscription:
        """Parse subscription data into Subscription object."""
        return Subscription(
            id=data.get("id", ""),
            name=data.get("name", ""),
            status=data.get("status", ""),
            billing_period=data.get("billing_period", 0),
            billing_period_unit=data.get("billing_period_unit", ""),
            currency_code=data.get("currency_code", ""),
            total_price=data.get("total_price", 0),
            renewal_price=data.get("renewal_price", 0),
            is_auto_renewed=data.get("is_auto_renewed", False),
            created_at=data.get("created_at", ""),
            expires_at=data.get("expires_at"),
            next_billing_at=data.get("next_billing_at")
        )

    # Data Centers
    def get_data_centers(self) -> List[DataCenter]:
        """Get all available data centers."""
        response = self._get("/api/vps/v1/data-centers")
        logger.info(f"Get data centers response: {response}")
        data_centers = [self._parse_data_center(dc) for dc in response]
        logger.info(f"Parsed {len(data_centers)} data centers")
        self._data_centers_index = {dc.id: dc for dc in data_centers}
        return data_centers

    def get_data_center_by_id(self, data_center_id: int) -> Optional[DataCenter]:
        """Get a specific data center by ID, populating the cache on first use."""
        if self._data_centers_index is None:
            self.get_data_centers()
        return (self._data_centers_index or {}).get(data_center_id)

    def _parse_data_center(self, data: Dict) -> DataCenter:
        """Parse data center data into DataCenter object."""
        return DataCenter(
            id=data.get("id", 0),
            name=data.get("name"),
            location=data.get("location"),
            city=data.get("city"),
            continent=data.get("continent")
        )

    # Test connection
    def test_connection(self) -> bool:
        """Test if the API connection is working."""
        try:
            self.get_virtual_machines()
            return True
        except HostingerAPIError:
            return False

