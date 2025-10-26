"""
POLICY_LOADER.PY
Purpose:
    A production-ready YAML-based policy loader with hot-reloading capabilities.
    This module provides thread-safe loading, caching, and automatic reloading
    of business policy files organized by domain (e.g., order_limits,
    commission_rates, refunds).

Architecture:
    - PolicyLoader: Main class for loading and managing policy files
    - FileWatcher: Monitors policy directory for changes and triggers reloads
    - Domain-specific dataclasses: Type-safe representations of policies
    - Thread-safe caching: Ensures consistent reads under concurrent access
    - Validation: Schema validation for YAML structure and required fields

Author: Senior Python Engineer
Date: October 2025
"""

# ============================================================================
# SECTION: IMPORTS
# ============================================================================

import os
import sys
import threading
import time
import logging
from pathlib import Path
from typing import Dict, Any, Optional, Type, Union, List
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from datetime import datetime
import yaml

# File system monitoring
try:
    from watchdog.observers import Observer
    from watchdog.events import FileSystemEventHandler, FileModifiedEvent
    WATCHDOG_AVAILABLE = True
except ImportError:
    WATCHDOG_AVAILABLE = False
    print("Warning: watchdog not available. Hot-reload disabled.")


# ============================================================================
# SECTION: LOGGING CONFIGURATION
# ============================================================================

# Module-level logger with detailed formatting
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Console handler with custom format
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler for persistent logs
file_handler = logging.FileHandler('policy_loader.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# ============================================================================
# SECTION: CUSTOM EXCEPTIONS
# ============================================================================

class PolicyLoaderException(Exception):
    """Base exception for all policy loader errors."""
    pass


class PolicyNotFoundError(PolicyLoaderException):
    """Raised when a policy file cannot be found."""

    def __init__(self, domain: str, path: Path):
        self.domain = domain
        self.path = path
        super().__init__(f"Policy not found for domain '{domain}' at path: {path}")


class PolicyParseError(PolicyLoaderException):
    """Raised when YAML parsing fails."""

    def __init__(self, domain: str, path: Path, original_error: Exception):
        self.domain = domain
        self.path = path
        self.original_error = original_error
        super().__init__(
            f"Failed to parse policy '{domain}' from {path}: {str(original_error)}"
        )


class PolicyValidationError(PolicyLoaderException):
    """Raised when policy schema validation fails."""

    def __init__(self, domain: str, errors: List[str]):
        self.domain = domain
        self.errors = errors
        error_msg = "; ".join(errors)
        super().__init__(
            f"Policy validation failed for domain '{domain}': {error_msg}"
        )


# ============================================================================
# SECTION: POLICY DATA CLASSES
# ============================================================================

@dataclass
class OrderLimitsPolicy:
    """
    Represents order limit policies including value thresholds and regional rules.

    Attributes:
        min_order_value: Minimum allowed order value in base currency
        max_order_value: Maximum allowed order value in base currency
        supported_regions: List of region codes where orders are accepted
        high_value_threshold: Value above which orders require additional review
        currency: ISO currency code
        effective_date: Date from which this policy applies
        version: Policy version identifier
        notes: Optional implementation notes
    """
    min_order_value: float
    max_order_value: float
    supported_regions: List[str]
    high_value_threshold: float
    currency: str = "USD"
    effective_date: Optional[str] = None
    version: str = "1.0"
    notes: Optional[str] = None

    def __post_init__(self):
        """Validate field constraints after initialization."""
        if self.min_order_value < 0:
            raise ValueError("min_order_value cannot be negative")
        if self.max_order_value <= self.min_order_value:
            raise ValueError("max_order_value must be greater than min_order_value")
        if self.high_value_threshold < self.min_order_value:
            raise ValueError("high_value_threshold must be >= min_order_value")
        if not self.supported_regions:
            raise ValueError("supported_regions cannot be empty")


@dataclass
class CommissionRate:
    """
    Individual commission rate configuration.

    Attributes:
        tier_name: Name of the commission tier
        min_value: Minimum order value for this tier
        max_value: Maximum order value for this tier (None for unlimited)
        rate_percent: Commission percentage for this tier
        flat_fee: Optional flat fee component
    """
    tier_name: str
    min_value: float
    max_value: Optional[float]
    rate_percent: float
    flat_fee: float = 0.0

    def __post_init__(self):
        """Validate rate constraints."""
        if self.rate_percent < 0 or self.rate_percent > 100:
            raise ValueError("rate_percent must be between 0 and 100")
        if self.flat_fee < 0:
            raise ValueError("flat_fee cannot be negative")


@dataclass
class CommissionRatesPolicy:
    """
    Complete commission rates policy with multiple tiers.

    Attributes:
        tiers: List of CommissionRate objects defining tier structure
        max_commission_cap: Optional absolute maximum commission amount
        min_commission_floor: Minimum commission charged regardless of tier
        calculation_method: Method for calculating commission (percentage, tiered, etc.)
        currency: ISO currency code
        version: Policy version identifier
        effective_date: Date from which this policy applies
    """
    tiers: List[CommissionRate]
    max_commission_cap: Optional[float] = None
    min_commission_floor: float = 0.0
    calculation_method: str = "tiered"
    currency: str = "USD"
    version: str = "1.0"
    effective_date: Optional[str] = None

    def __post_init__(self):
        """Validate commission policy structure."""
        if not self.tiers:
            raise ValueError("At least one commission tier is required")
        if self.min_commission_floor < 0:
            raise ValueError("min_commission_floor cannot be negative")
        # Validate tier ordering
        sorted_tiers = sorted(self.tiers, key=lambda t: t.min_value)
        for i in range(len(sorted_tiers) - 1):
            if sorted_tiers[i].max_value and sorted_tiers[i + 1].min_value < sorted_tiers[i].max_value:
                raise ValueError("Commission tiers have overlapping ranges")


@dataclass
class RefundPolicy:
    """
    Refund policy rules including time windows and conditions.

    Attributes:
        refund_window_days: Number of days within which refunds are allowed
        partial_refund_allowed: Whether partial refunds are permitted
        restocking_fee_percent: Percentage charged as restocking fee
        eligible_regions: Regions where refund policy applies
        excluded_categories: Product categories excluded from refunds
        requires_approval: Whether refunds require manual approval
        auto_approve_threshold: Maximum value for automatic approval
        currency: ISO currency code
        version: Policy version identifier
    """
    refund_window_days: int
    partial_refund_allowed: bool
    restocking_fee_percent: float
    eligible_regions: List[str]
    excluded_categories: List[str] = field(default_factory=list)
    requires_approval: bool = False
    auto_approve_threshold: Optional[float] = None
    currency: str = "USD"
    version: str = "1.0"
    effective_date: Optional[str] = None

    def __post_init__(self):
        """Validate refund policy constraints."""
        if self.refund_window_days < 0:
            raise ValueError("refund_window_days cannot be negative")
        if self.restocking_fee_percent < 0 or self.restocking_fee_percent > 100:
            raise ValueError("restocking_fee_percent must be between 0 and 100")
        if not self.eligible_regions:
            raise ValueError("eligible_regions cannot be empty")


# ============================================================================
# SECTION: YAML SCHEMA DEFINITIONS
# ============================================================================

class YAMLSchemaValidator:
    """
    Validates YAML data against expected schemas for each policy domain.
    Uses type checking and required field validation.
    """

    @staticmethod
    def validate_order_limits(data: Dict[str, Any]) -> List[str]:
        """
        Validate order limits policy schema.

        Args:
            data: Parsed YAML data dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        required_fields = [
            'min_order_value', 'max_order_value',
            'supported_regions', 'high_value_threshold'
        ]

        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Type validations
        if 'min_order_value' in data and not isinstance(data['min_order_value'], (int, float)):
            errors.append("min_order_value must be numeric")

        if 'max_order_value' in data and not isinstance(data['max_order_value'], (int, float)):
            errors.append("max_order_value must be numeric")

        if 'supported_regions' in data and not isinstance(data['supported_regions'], list):
            errors.append("supported_regions must be a list")

        if 'high_value_threshold' in data and not isinstance(data['high_value_threshold'], (int, float)):
            errors.append("high_value_threshold must be numeric")

        return errors

    @staticmethod
    def validate_commission_rates(data: Dict[str, Any]) -> List[str]:
        """
        Validate commission rates policy schema.

        Args:
            data: Parsed YAML data dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        if 'tiers' not in data:
            errors.append("Missing required field: tiers")
            return errors

        if not isinstance(data['tiers'], list):
            errors.append("tiers must be a list")
            return errors

        if not data['tiers']:
            errors.append("tiers list cannot be empty")

        for idx, tier in enumerate(data['tiers']):
            if not isinstance(tier, dict):
                errors.append(f"Tier {idx} must be a dictionary")
                continue

            required_tier_fields = ['tier_name', 'min_value', 'rate_percent']
            for field in required_tier_fields:
                if field not in tier:
                    errors.append(f"Tier {idx} missing required field: {field}")

        return errors

    @staticmethod
    def validate_refund_policy(data: Dict[str, Any]) -> List[str]:
        """
        Validate refund policy schema.

        Args:
            data: Parsed YAML data dictionary

        Returns:
            List of validation error messages (empty if valid)
        """
        errors = []

        required_fields = [
            'refund_window_days', 'partial_refund_allowed',
            'restocking_fee_percent', 'eligible_regions'
        ]

        for field in required_fields:
            if field not in data:
                errors.append(f"Missing required field: {field}")

        # Type validations
        if 'refund_window_days' in data and not isinstance(data['refund_window_days'], int):
            errors.append("refund_window_days must be an integer")

        if 'partial_refund_allowed' in data and not isinstance(data['partial_refund_allowed'], bool):
            errors.append("partial_refund_allowed must be a boolean")

        if 'restocking_fee_percent' in data and not isinstance(data['restocking_fee_percent'], (int, float)):
            errors.append("restocking_fee_percent must be numeric")

        if 'eligible_regions' in data and not isinstance(data['eligible_regions'], list):
            errors.append("eligible_regions must be a list")

        return errors


# ============================================================================
# SECTION: POLICY LOADER CLASS
# ============================================================================

class PolicyLoader:
    """
    Thread-safe policy loader with caching and hot-reload support.

    This class manages loading YAML policy files from a designated directory,
    parsing them into typed dataclass instances, and maintaining a thread-safe
    cache for fast access. Supports automatic reloading when files change.

    Attributes:
        base_dir: Base directory containing policy YAML files
        cache: Thread-safe cache mapping domain names to policy instances
        cache_lock: Threading lock for cache access
        domain_map: Mapping of domain names to dataclass types
        validator: YAML schema validator instance
    """

    # Map domain names to their corresponding dataclass types
    DOMAIN_MAP: Dict[str, Type] = {
        'order_limits': OrderLimitsPolicy,
        'commission_rates': CommissionRatesPolicy,
        'refund_policy': RefundPolicy,
    }

    # Map domain names to validator methods
    VALIDATOR_MAP: Dict[str, callable] = {
        'order_limits': YAMLSchemaValidator.validate_order_limits,
        'commission_rates': YAMLSchemaValidator.validate_commission_rates,
        'refund_policy': YAMLSchemaValidator.validate_refund_policy,
    }

    def __init__(self, base_dir: Union[str, Path]):
        """
        Initialize PolicyLoader with base directory.

        Args:
            base_dir: Directory containing policy YAML files

        Raises:
            FileNotFoundError: If base directory does not exist
        """
        self.base_dir = Path(base_dir)

        if not self.base_dir.exists():
            raise FileNotFoundError(f"Policy directory not found: {base_dir}")

        if not self.base_dir.is_dir():
            raise NotADirectoryError(f"Path is not a directory: {base_dir}")

        self.cache: Dict[str, Any] = {}
        self.cache_lock = threading.RLock()
        self.validator = YAMLSchemaValidator()

        logger.info(f"PolicyLoader initialized with base directory: {self.base_dir}")

    def _get_policy_path(self, domain: str) -> Path:
        """
        Construct file path for a policy domain.

        Args:
            domain: Policy domain name

        Returns:
            Path object for the policy YAML file
        """
        return self.base_dir / f"{domain}.yaml"

    def _read_yaml_file(self, path: Path) -> Dict[str, Any]:
        """
        Read and parse YAML file with error handling.

        Args:
            path: Path to YAML file

        Returns:
            Parsed YAML data as dictionary

        Raises:
            PolicyParseError: If YAML parsing fails
        """
        try:
            with open(path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f)

            if data is None:
                raise ValueError("YAML file is empty")

            if not isinstance(data, dict):
                raise ValueError("YAML root must be a dictionary")

            logger.debug(f"Successfully parsed YAML from: {path}")
            return data

        except yaml.YAMLError as e:
            logger.error(f"YAML parsing error in {path}: {e}")
            raise PolicyParseError(path.stem, path, e)
        except Exception as e:
            logger.error(f"Error reading file {path}: {e}")
            raise PolicyParseError(path.stem, path, e)

    def _validate_policy_data(self, domain: str, data: Dict[str, Any]) -> None:
        """
        Validate policy data against schema.

        Args:
            domain: Policy domain name
            data: Parsed policy data

        Raises:
            PolicyValidationError: If validation fails
        """
        if domain not in self.VALIDATOR_MAP:
            logger.warning(f"No validator defined for domain: {domain}")
            return

        validator_func = self.VALIDATOR_MAP[domain]
        errors = validator_func(data)

        if errors:
            logger.error(f"Validation errors for {domain}: {errors}")
            raise PolicyValidationError(domain, errors)

        logger.debug(f"Schema validation passed for domain: {domain}")

    def _parse_commission_rates(self, data: Dict[str, Any]) -> CommissionRatesPolicy:
        """
        Parse commission rates data into policy object.

        Args:
            data: Raw policy data dictionary

        Returns:
            CommissionRatesPolicy instance
        """
        # Parse individual tiers
        tier_objects = []
        for tier_data in data['tiers']:
            tier = CommissionRate(
                tier_name=tier_data['tier_name'],
                min_value=float(tier_data['min_value']),
                max_value=float(tier_data['max_value']) if tier_data.get('max_value') is not None else None,
                rate_percent=float(tier_data['rate_percent']),
                flat_fee=float(tier_data.get('flat_fee', 0.0))
            )
            tier_objects.append(tier)

        # Build policy object
        policy = CommissionRatesPolicy(
            tiers=tier_objects,
            max_commission_cap=float(data['max_commission_cap']) if data.get('max_commission_cap') else None,
            min_commission_floor=float(data.get('min_commission_floor', 0.0)),
            calculation_method=data.get('calculation_method', 'tiered'),
            currency=data.get('currency', 'USD'),
            version=data.get('version', '1.0'),
            effective_date=data.get('effective_date')
        )

        return policy

    def _instantiate_policy(self, domain: str, data: Dict[str, Any]) -> Any:
        """
        Create typed policy instance from raw data.

        Args:
            domain: Policy domain name
            data: Validated policy data

        Returns:
            Policy dataclass instance

        Raises:
            ValueError: If domain is unknown or instantiation fails
        """
        if domain not in self.DOMAIN_MAP:
            raise ValueError(f"Unknown policy domain: {domain}")

        policy_class = self.DOMAIN_MAP[domain]

        try:
            # Special handling for commission rates (nested structure)
            if domain == 'commission_rates':
                policy = self._parse_commission_rates(data)
            else:
                # Direct instantiation for other policies
                policy = policy_class(**data)

            logger.debug(f"Successfully instantiated {policy_class.__name__}")
            return policy

        except TypeError as e:
            logger.error(f"Failed to instantiate {policy_class.__name__}: {e}")
            raise ValueError(f"Policy data does not match {policy_class.__name__} schema: {e}")

    def load_policy(self, domain: str, use_cache: bool = True) -> Any:
        """
        Load policy for specified domain.

        Args:
            domain: Policy domain name (e.g., 'order_limits')
            use_cache: Whether to use cached policy if available

        Returns:
            Policy dataclass instance for the domain

        Raises:
            PolicyNotFoundError: If policy file doesn't exist
            PolicyParseError: If YAML parsing fails
            PolicyValidationError: If schema validation fails
        """
        # Check cache first if enabled
        if use_cache:
            with self.cache_lock:
                if domain in self.cache:
                    logger.debug(f"Returning cached policy for domain: {domain}")
                    return self.cache[domain]

        logger.info(f"Loading policy for domain: {domain}")

        # Construct file path
        policy_path = self._get_policy_path(domain)

        if not policy_path.exists():
            logger.error(f"Policy file not found: {policy_path}")
            raise PolicyNotFoundError(domain, policy_path)

        # Read and parse YAML
        data = self._read_yaml_file(policy_path)

        # Validate schema
        self._validate_policy_data(domain, data)

        # Instantiate policy object
        policy = self._instantiate_policy(domain, data)

        # Update cache
        with self.cache_lock:
            self.cache[domain] = policy
            logger.info(f"Policy cached for domain: {domain}")

        return policy

    def reload_policy(self, domain: str) -> Any:
        """
        Force reload of policy from disk, bypassing cache.

        Args:
            domain: Policy domain name

        Returns:
            Freshly loaded policy instance
        """
        logger.info(f"Reloading policy for domain: {domain}")

        # Clear from cache
        with self.cache_lock:
            if domain in self.cache:
                del self.cache[domain]
                logger.debug(f"Cleared cache for domain: {domain}")

        # Load fresh copy
        return self.load_policy(domain, use_cache=False)

    def get_cached_policy(self, domain: str) -> Optional[Any]:
        """
        Get policy from cache without loading from disk.

        Args:
            domain: Policy domain name

        Returns:
            Cached policy instance or None if not cached
        """
        with self.cache_lock:
            return self.cache.get(domain)

    def clear_cache(self, domain: Optional[str] = None) -> None:
        """
        Clear policy cache.

        Args:
            domain: Specific domain to clear, or None to clear all
        """
        with self.cache_lock:
            if domain:
                if domain in self.cache:
                    del self.cache[domain]
                    logger.info(f"Cleared cache for domain: {domain}")
            else:
                self.cache.clear()
                logger.info("Cleared all policy cache")

    def list_available_policies(self) -> List[str]:
        """
        List all available policy domains in base directory.

        Returns:
            List of domain names with corresponding YAML files
        """
        policies = []
        for yaml_file in self.base_dir.glob("*.yaml"):
            domain = yaml_file.stem
            policies.append(domain)

        logger.debug(f"Found {len(policies)} policy files")
        return sorted(policies)

    def preload_all_policies(self) -> Dict[str, Any]:
        """
        Load all known policies into cache.

        Returns:
            Dictionary mapping domain names to policy instances
        """
        logger.info("Preloading all policies")
        loaded = {}

        for domain in self.DOMAIN_MAP.keys():
            try:
                policy = self.load_policy(domain)
                loaded[domain] = policy
                logger.info(f"Preloaded policy: {domain}")
            except Exception as e:
                logger.error(f"Failed to preload {domain}: {e}")

        return loaded


# ============================================================================
# SECTION: FILE WATCHER CLASS
# ============================================================================

if WATCHDOG_AVAILABLE:

    class PolicyFileEventHandler(FileSystemEventHandler):
        """
        Handles file system events for policy files.

        Monitors YAML files in the policy directory and triggers reloads
        when modifications are detected.
        """

        def __init__(self, policy_loader: PolicyLoader):
            """
            Initialize event handler with policy loader instance.

            Args:
                policy_loader: PolicyLoader instance to reload policies
            """
            super().__init__()
            self.policy_loader = policy_loader
            self.last_reload_times: Dict[str, float] = {}
            self.debounce_seconds = 1.0  # Prevent rapid successive reloads
            logger.info("PolicyFileEventHandler initialized")

        def on_modified(self, event):
            """
            Handle file modification events.

            Args:
                event: FileSystemEvent from watchdog
            """
            if event.is_directory:
                return

            if not event.src_path.endswith('.yaml'):
                return

            # Extract domain name from file path
            file_path = Path(event.src_path)
            domain = file_path.stem

            # Debounce: check if we recently reloaded this domain
            current_time = time.time()
            last_reload = self.last_reload_times.get(domain, 0)

            if current_time - last_reload < self.debounce_seconds:
                logger.debug(f"Debouncing reload for {domain}")
                return

            # Reload policy
            logger.info(f"File modified detected: {file_path.name}, reloading {domain}")

            try:
                self.policy_loader.reload_policy(domain)
                self.last_reload_times[domain] = current_time
                logger.info(f"Successfully reloaded policy: {domain}")
            except Exception as e:
                logger.error(f"Failed to reload policy {domain}: {e}", exc_info=True)


    class FileWatcher:
        """
        Watches policy directory for changes and triggers reloads.

        Uses watchdog library to monitor file system events and automatically
        reload policies when YAML files are modified.
        """

        def __init__(self, policy_loader: PolicyLoader):
            """
            Initialize file watcher.

            Args:
                policy_loader: PolicyLoader instance to manage
            """
            self.policy_loader = policy_loader
            self.observer = Observer()
            self.event_handler = PolicyFileEventHandler(policy_loader)
            self.is_running = False
            logger.info("FileWatcher initialized")

        def start(self) -> None:
            """
            Start watching policy directory.

            Raises:
                RuntimeError: If watcher is already running
            """
            if self.is_running:
                raise RuntimeError("FileWatcher is already running")

            watch_path = str(self.policy_loader.base_dir)
            self.observer.schedule(
                self.event_handler,
                watch_path,
                recursive=False
            )
            self.observer.start()
            self.is_running = True

            logger.info(f"FileWatcher started, monitoring: {watch_path}")

        def stop(self) -> None:
            """Stop watching policy directory."""
            if not self.is_running:
                logger.warning("FileWatcher is not running")
                return

            self.observer.stop()
            self.observer.join(timeout=5.0)
            self.is_running = False

            logger.info("FileWatcher stopped")

        def __enter__(self):
            """Context manager entry."""
            self.start()
            return self

        def __exit__(self, exc_type, exc_val, exc_tb):
            """Context manager exit."""
            self.stop()
            return False

else:
    # Stub implementation when watchdog is not available
    class FileWatcher:
        """Stub FileWatcher when watchdog is not available."""

        def __init__(self, policy_loader: PolicyLoader):
            logger.warning("FileWatcher disabled: watchdog library not available")
            self.policy_loader = policy_loader

        def start(self):
            raise RuntimeError("FileWatcher requires watchdog library")

        def stop(self):
            pass


# ============================================================================
# SECTION: HELPER UTILITIES
# ============================================================================

def create_sample_policies(base_dir: Union[str, Path]) -> None:
    """
    Create sample policy YAML files for testing.

    Args:
        base_dir: Directory to create sample files in
    """
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    # Sample order limits policy
    order_limits_yaml = """
min_order_value: 10.0
max_order_value: 10000.0
supported_regions:
  - US
  - CA
  - GB
  - AU
high_value_threshold: 5000.0
currency: USD
version: "1.0"
effective_date: "2025-01-01"
notes: "Standard order limits for all regions"
"""

    with open(base_path / "order_limits.yaml", 'w') as f:
        f.write(order_limits_yaml)

    # Sample commission rates policy
    commission_rates_yaml = """
tiers:
  - tier_name: "Bronze"
    min_value: 0.0
    max_value: 1000.0
    rate_percent: 5.0
    flat_fee: 0.0
  - tier_name: "Silver"
    min_value: 1000.0
    max_value: 5000.0
    rate_percent: 3.5
    flat_fee: 10.0
  - tier_name: "Gold"
    min_value: 5000.0
    max_value: null
    rate_percent: 2.0
    flat_fee: 25.0
max_commission_cap: 500.0
min_commission_floor: 1.0
calculation_method: "tiered"
currency: "USD"
version: "1.0"
effective_date: "2025-01-01"
"""

    with open(base_path / "commission_rates.yaml", 'w') as f:
        f.write(commission_rates_yaml)

    # Sample refund policy
    refund_policy_yaml = """
refund_window_days: 30
partial_refund_allowed: true
restocking_fee_percent: 10.0
eligible_regions:
  - US
  - CA
  - GB
excluded_categories:
  - digital
  - perishable
requires_approval: false
auto_approve_threshold: 500.0
currency: "USD"
version: "1.0"
effective_date: "2025-01-01"
"""

    with open(base_path / "refund_policy.yaml", 'w') as f:
        f.write(refund_policy_yaml)

    logger.info(f"Created sample policy files in: {base_path}")


def policy_to_dict(policy: Any) -> Dict[str, Any]:
    """
    Convert policy dataclass to dictionary.

    Args:
        policy: Policy dataclass instance

    Returns:
        Dictionary representation of policy
    """
    return asdict(policy)


# ============================================================================
# SECTION: CLI ENTRYPOINT
# ============================================================================

def main():
    """
    Command-line interface for policy loader.

    Usage:
        python policy_loader.py <base_dir> <domain>
        python policy_loader.py <base_dir> --watch
        python policy_loader.py <base_dir> --create-samples
    """
    import argparse

    parser = argparse.ArgumentParser(description="Policy Loader CLI")
    parser.add_argument('base_dir', help="Base directory containing policy files")
    parser.add_argument('domain', nargs='?', help="Policy domain to load")
    parser.add_argument('--watch', action='store_true', help="Watch for file changes")
    parser.add_argument('--create-samples', action='store_true', help="Create sample policy files")
    parser.add_argument('--list', action='store_true', help="List available policies")

    args = parser.parse_args()

    # Create samples if requested
    if args.create_samples:
        create_sample_policies(args.base_dir)
        print(f"Sample policies created in: {args.base_dir}")
        return

    # Initialize loader
    try:
        loader = PolicyLoader(args.base_dir)
    except Exception as e:
        print(f"Error initializing loader: {e}")
        sys.exit(1)

    # List policies if requested
    if args.list:
        policies = loader.list_available_policies()
        print(f"Available policies in {args.base_dir}:")
        for policy in policies:
            print(f"  - {policy}")
        return

    # Load specific domain
    if args.domain:
        try:
            policy = loader.load_policy(args.domain)
            print(f"\nLoaded policy for domain: {args.domain}")
            print("\nPolicy data:")
            import json
            print(json.dumps(policy_to_dict(policy), indent=2, default=str))
        except Exception as e:
            print(f"Error loading policy: {e}")
            sys.exit(1)

    # Watch mode
    if args.watch:
        if not WATCHDOG_AVAILABLE:
            print("Error: watchdog library not available")
            sys.exit(1)

        print(f"Watching {args.base_dir} for changes... (Press Ctrl+C to stop)")

        watcher = FileWatcher(loader)
        watcher.start()

        try:
            while True:
                time.sleep(1)
        except KeyboardInterrupt:
            print("\nStopping watcher...")
            watcher.stop()


if __name__ == "__main__":
    main()


# ============================================================================
# SECTION: UNIT TESTS
# ============================================================================

import pytest
import tempfile
import shutil
from threading import Thread
from concurrent.futures import ThreadPoolExecutor, as_completed


class TestPolicyDataClasses:
    """Test suite for policy dataclasses."""

    def test_order_limits_valid(self):
        """Test valid OrderLimitsPolicy creation."""
        policy = OrderLimitsPolicy(
            min_order_value=10.0,
            max_order_value=1000.0,
            supported_regions=['US', 'CA'],
            high_value_threshold=500.0
        )
        assert policy.min_order_value == 10.0
        assert policy.max_order_value == 1000.0
        assert len(policy.supported_regions) == 2

    def test_order_limits_invalid_range(self):
        """Test OrderLimitsPolicy with invalid value range."""
        with pytest.raises(ValueError, match="max_order_value must be greater"):
            OrderLimitsPolicy(
                min_order_value=1000.0,
                max_order_value=100.0,
                supported_regions=['US'],
                high_value_threshold=500.0
            )

    def test_order_limits_negative_min(self):
        """Test OrderLimitsPolicy with negative minimum."""
        with pytest.raises(ValueError, match="cannot be negative"):
            OrderLimitsPolicy(
                min_order_value=-10.0,
                max_order_value=1000.0,
                supported_regions=['US'],
                high_value_threshold=500.0
            )

    def test_order_limits_empty_regions(self):
        """Test OrderLimitsPolicy with empty regions list."""
        with pytest.raises(ValueError, match="cannot be empty"):
            OrderLimitsPolicy(
                min_order_value=10.0,
                max_order_value=1000.0,
                supported_regions=[],
                high_value_threshold=500.0
            )

    def test_commission_rate_valid(self):
        """Test valid CommissionRate creation."""
        rate = CommissionRate(
            tier_name="Bronze",
            min_value=0.0,
            max_value=1000.0,
            rate_percent=5.0
        )
        assert rate.tier_name == "Bronze"
        assert rate.rate_percent == 5.0

    def test_commission_rate_invalid_percent(self):
        """Test CommissionRate with invalid percentage."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            CommissionRate(
                tier_name="Invalid",
                min_value=0.0,
                max_value=1000.0,
                rate_percent=150.0
            )

    def test_commission_rates_policy_valid(self):
        """Test valid CommissionRatesPolicy creation."""
        tiers = [
            CommissionRate("Bronze", 0.0, 1000.0, 5.0),
            CommissionRate("Silver", 1000.0, None, 3.0)
        ]
        policy = CommissionRatesPolicy(tiers=tiers)
        assert len(policy.tiers) == 2

    def test_commission_rates_policy_empty_tiers(self):
        """Test CommissionRatesPolicy with no tiers."""
        with pytest.raises(ValueError, match="At least one commission tier"):
            CommissionRatesPolicy(tiers=[])

    def test_refund_policy_valid(self):
        """Test valid RefundPolicy creation."""
        policy = RefundPolicy(
            refund_window_days=30,
            partial_refund_allowed=True,
            restocking_fee_percent=10.0,
            eligible_regions=['US', 'CA']
        )
        assert policy.refund_window_days == 30
        assert policy.partial_refund_allowed is True

    def test_refund_policy_negative_window(self):
        """Test RefundPolicy with negative window."""
        with pytest.raises(ValueError, match="cannot be negative"):
            RefundPolicy(
                refund_window_days=-5,
                partial_refund_allowed=True,
                restocking_fee_percent=10.0,
                eligible_regions=['US']
            )

    def test_refund_policy_invalid_fee(self):
        """Test RefundPolicy with invalid restocking fee."""
        with pytest.raises(ValueError, match="between 0 and 100"):
            RefundPolicy(
                refund_window_days=30,
                partial_refund_allowed=True,
                restocking_fee_percent=150.0,
                eligible_regions=['US']
            )


class TestYAMLSchemaValidator:
    """Test suite for YAML schema validation."""

    def test_validate_order_limits_valid(self):
        """Test validation of valid order limits data."""
        data = {
            'min_order_value': 10.0,
            'max_order_value': 1000.0,
            'supported_regions': ['US', 'CA'],
            'high_value_threshold': 500.0
        }
        errors = YAMLSchemaValidator.validate_order_limits(data)
        assert len(errors) == 0

    def test_validate_order_limits_missing_field(self):
        """Test validation with missing required field."""
        data = {
            'min_order_value': 10.0,
            'max_order_value': 1000.0
        }
        errors = YAMLSchemaValidator.validate_order_limits(data)
        assert len(errors) > 0
        assert any('supported_regions' in err for err in errors)

    def test_validate_order_limits_wrong_type(self):
        """Test validation with wrong field type."""
        data = {
            'min_order_value': "invalid",
            'max_order_value': 1000.0,
            'supported_regions': ['US'],
            'high_value_threshold': 500.0
        }
        errors = YAMLSchemaValidator.validate_order_limits(data)
        assert len(errors) > 0

    def test_validate_commission_rates_valid(self):
        """Test validation of valid commission rates data."""
        data = {
            'tiers': [
                {
                    'tier_name': 'Bronze',
                    'min_value': 0.0,
                    'rate_percent': 5.0
                }
            ]
        }
        errors = YAMLSchemaValidator.validate_commission_rates(data)
        assert len(errors) == 0

    def test_validate_commission_rates_missing_tiers(self):
        """Test validation with missing tiers field."""
        data = {}
        errors = YAMLSchemaValidator.validate_commission_rates(data)
        assert len(errors) > 0
        assert any('tiers' in err for err in errors)

    def test_validate_refund_policy_valid(self):
        """Test validation of valid refund policy data."""
        data = {
            'refund_window_days': 30,
            'partial_refund_allowed': True,
            'restocking_fee_percent': 10.0,
            'eligible_regions': ['US']
        }
        errors = YAMLSchemaValidator.validate_refund_policy(data)
        assert len(errors) == 0


class TestPolicyLoader:
    """Test suite for PolicyLoader class."""

    @pytest.fixture
    def temp_policy_dir(self):
        """Create temporary directory with sample policies."""
        temp_dir = tempfile.mkdtemp()
        create_sample_policies(temp_dir)
        yield temp_dir
        shutil.rmtree(temp_dir)

    def test_init_valid_directory(self, temp_policy_dir):
        """Test initialization with valid directory."""
        loader = PolicyLoader(temp_policy_dir)
        assert loader.base_dir.exists()
        assert isinstance(loader.cache, dict)

    def test_init_invalid_directory(self):
        """Test initialization with non-existent directory."""
        with pytest.raises(FileNotFoundError):
            PolicyLoader("/nonexistent/path")

    def test_load_order_limits(self, temp_policy_dir):
        """Test loading order limits policy."""
        loader = PolicyLoader(temp_policy_dir)
        policy = loader.load_policy('order_limits')
        assert isinstance(policy, OrderLimitsPolicy)
        assert policy.min_order_value == 10.0

    def test_load_commission_rates(self, temp_policy_dir):
        """Test loading commission rates policy."""
        loader = PolicyLoader(temp_policy_dir)
        policy = loader.load_policy('commission_rates')
        assert isinstance(policy, CommissionRatesPolicy)
        assert len(policy.tiers) == 3

    def test_load_refund_policy(self, temp_policy_dir):
        """Test loading refund policy."""
        loader = PolicyLoader(temp_policy_dir)
        policy = loader.load_policy('refund_policy')
        assert isinstance(policy, RefundPolicy)
        assert policy.refund_window_days == 30

    def test_load_nonexistent_domain(self, temp_policy_dir):
        """Test loading non-existent domain."""
        loader = PolicyLoader(temp_policy_dir)
        with pytest.raises(PolicyNotFoundError):
            loader.load_policy('nonexistent')

    def test_caching_behavior(self, temp_policy_dir):
        """Test that policies are properly cached."""
        loader = PolicyLoader(temp_policy_dir)

        # First load
        policy1 = loader.load_policy('order_limits')

        # Second load should return cached instance
        policy2 = loader.load_policy('order_limits')

        assert policy1 is policy2

    def test_reload_policy(self, temp_policy_dir):
        """Test reloading policy from disk."""
        loader = PolicyLoader(temp_policy_dir)

        # Initial load
        policy1 = loader.load_policy('order_limits')

        # Reload
        policy2 = loader.reload_policy('order_limits')

        # Should be different instances
        assert policy1 is not policy2

    def test_clear_cache_specific(self, temp_policy_dir):
        """Test clearing specific domain from cache."""
        loader = PolicyLoader(temp_policy_dir)

        loader.load_policy('order_limits')
        loader.load_policy('refund_policy')

        loader.clear_cache('order_limits')

        assert loader.get_cached_policy('order_limits') is None
        assert loader.get_cached_policy('refund_policy') is not None

    def test_clear_cache_all(self, temp_policy_dir):
        """Test clearing entire cache."""
        loader = PolicyLoader(temp_policy_dir)

        loader.load_policy('order_limits')
        loader.load_policy('refund_policy')

        loader.clear_cache()

        assert loader.get_cached_policy('order_limits') is None
        assert loader.get_cached_policy('refund_policy') is None

    def test_list_available_policies(self, temp_policy_dir):
        """Test listing available policy files."""
        loader = PolicyLoader(temp_policy_dir)
        policies = loader.list_available_policies()

        assert 'order_limits' in policies
        assert 'commission_rates' in policies
        assert 'refund_policy' in policies

    def test_preload_all_policies(self, temp_policy_dir):
        """Test preloading all policies."""
        loader = PolicyLoader(temp_policy_dir)
        loaded = loader.preload_all_policies()

        assert 'order_limits' in loaded
        assert 'commission_rates' in loaded
        assert 'refund_policy' in loaded

    def test_thread_safety(self, temp_policy_dir):
        """Test thread-safe concurrent access to cache."""
        loader = PolicyLoader(temp_policy_dir)
        errors = []

        def load_policy():
            try:
                policy = loader.load_policy('order_limits')
                assert isinstance(policy, OrderLimitsPolicy)
            except Exception as e:
                errors.append(e)

        threads = [Thread(target=load_policy) for _ in range(10)]

        for t in threads:
            t.start()

        for t in threads:
            t.join()

        assert len(errors) == 0

    def test_malformed_yaml(self, temp_policy_dir):
        """Test handling of malformed YAML."""
        # Create malformed YAML file
        malformed_path = Path(temp_policy_dir) / "malformed.yaml"
        with open(malformed_path, 'w') as f:
            f.write("invalid: yaml: content: [")

        loader = PolicyLoader(temp_policy_dir)

        with pytest.raises(PolicyParseError):
            loader._read_yaml_file(malformed_path)


class TestFileWatcher:
    """Test suite for FileWatcher class."""

    @pytest.fixture
    def temp_policy_dir(self):
        """Create temporary directory with sample policies."""
        temp_dir = tempfile.mkdtemp()
        create_sample_policies(temp_dir)
        yield temp_dir
        shutil.rmtree(temp_dir)

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_file_watcher_start_stop(self, temp_policy_dir):
        """Test starting and stopping file watcher."""
        loader = PolicyLoader(temp_policy_dir)
        watcher = FileWatcher(loader)

        watcher.start()
        assert watcher.is_running

        watcher.stop()
        assert not watcher.is_running

    @pytest.mark.skipif(not WATCHDOG_AVAILABLE, reason="watchdog not available")
    def test_file_watcher_context_manager(self, temp_policy_dir):
        """Test file watcher as context manager."""
        loader = PolicyLoader(temp_policy_dir)

        with FileWatcher(loader) as watcher:
            assert watcher.is_running

        assert not watcher.is_running


# Additional edge case tests
class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_empty_yaml_file(self):
        """Test handling of empty YAML file."""
        temp_dir = tempfile.mkdtemp()
        empty_file = Path(temp_dir) / "empty.yaml"
        empty_file.touch()

        loader = PolicyLoader(temp_dir)

        with pytest.raises(PolicyParseError):
            loader._read_yaml_file(empty_file)

        shutil.rmtree(temp_dir)

    def test_concurrent_cache_access(self):
        """Test concurrent cache read/write operations."""
        temp_dir = tempfile.mkdtemp()
        create_sample_policies(temp_dir)
        loader = PolicyLoader(temp_dir)

        def worker(domain):
            return loader.load_policy(domain)

        with ThreadPoolExecutor(max_workers=5) as executor:
            futures = [
                executor.submit(worker, 'order_limits')
                for _ in range(20)
            ]

            results = [f.result() for f in as_completed(futures)]

            # All results should be valid OrderLimitsPolicy instances
            assert all(isinstance(r, OrderLimitsPolicy) for r in results)

        shutil.rmtree(temp_dir)
