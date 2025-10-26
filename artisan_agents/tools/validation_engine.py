"""
VALIDATION_ENGINE.PY
Purpose:
    A comprehensive rule-driven validation engine that applies YAML-based
    business policies to intake data. This module provides a flexible framework
    for defining validation rules as composable objects, registering policy
    domains, and executing validation workflows with detailed error reporting.

Architecture:
    - ValidationRule ABC: Base class for all validation rules
    - Concrete Rule Classes: Specific rule implementations (min/max values,
      region checks, commission calculations, refund windows, etc.)
    - RuleFactory: Creates rule instances from policy dataclasses
    - ValidationEngine: Orchestrates validation across multiple domains
    - Detailed metrics and logging for observability

Author: Senior Python Engineer
Date: October 2025
"""

# ============================================================================
# SECTION: IMPORTS
# ============================================================================

import sys
import logging
from typing import Dict, Any, Optional, List, Tuple, Type, Union, Callable
from dataclasses import dataclass, field, asdict
from abc import ABC, abstractmethod
from datetime import datetime, timedelta
from enum import Enum
import json
from collections import defaultdict


# ============================================================================
# SECTION: LOGGING CONFIGURATION
# ============================================================================

# Module-level logger with detailed formatting
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

# Console handler
console_handler = logging.StreamHandler()
console_handler.setLevel(logging.INFO)
formatter = logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - [%(filename)s:%(lineno)d] - %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
console_handler.setFormatter(formatter)
logger.addHandler(console_handler)

# File handler
file_handler = logging.FileHandler('validation_engine.log')
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(formatter)
logger.addHandler(file_handler)


# ============================================================================
# SECTION: CUSTOM EXCEPTIONS
# ============================================================================

class ValidationEngineException(Exception):
    """Base exception for validation engine errors."""
    pass


class ValidationDomainNotRegisteredError(ValidationEngineException):
    """Raised when attempting to validate against unregistered domain."""

    def __init__(self, domain: str):
        self.domain = domain
        super().__init__(f"Validation domain not registered: {domain}")


class ValidationErrorAggregate(ValidationEngineException):
    """
    Raised when multiple validation errors occur.

    Attributes:
        errors: List of individual error messages
        domain: Domain where validation failed
        data: Data that failed validation
    """

    def __init__(self, domain: str, errors: List[str], data: Optional[Dict] = None):
        self.domain = domain
        self.errors = errors
        self.data = data
        error_summary = f"{len(errors)} validation error(s) in domain '{domain}'"
        super().__init__(error_summary)

    def get_error_report(self) -> str:
        """Generate formatted error report."""
        report = [f"Validation failed for domain: {self.domain}"]
        report.append(f"Total errors: {len(self.errors)}")
        report.append("\nErrors:")
        for idx, error in enumerate(self.errors, 1):
            report.append(f"  {idx}. {error}")
        return "\n".join(report)


class RuleInstantiationError(ValidationEngineException):
    """Raised when rule cannot be instantiated from policy."""

    def __init__(self, rule_class: str, reason: str):
        self.rule_class = rule_class
        self.reason = reason
        super().__init__(f"Failed to instantiate {rule_class}: {reason}")


# ============================================================================
# SECTION: DATA CLASSES FOR VALIDATION INPUT
# ============================================================================

@dataclass
class IntakeData:
    """
    General intake data structure for customer/business profiling.

    Attributes:
        customer_id: Unique customer identifier
        customer_type: Type of customer (business, startup, personal_brand)
        region: Geographic region code
        industry: Industry/vertical classification
        company_size: Number of employees or size category
        annual_revenue: Annual revenue in base currency
        timestamp: When this intake was created
        metadata: Additional flexible metadata
    """
    customer_id: str
    customer_type: str
    region: str
    industry: str
    company_size: Optional[str] = None
    annual_revenue: Optional[float] = None
    timestamp: Optional[datetime] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set timestamp if not provided."""
        if self.timestamp is None:
            self.timestamp = datetime.now()


@dataclass
class OrderData:
    """
    Order data structure for order validation.

    Attributes:
        order_id: Unique order identifier
        customer_id: Associated customer ID
        order_value: Total order value
        currency: ISO currency code
        region: Region where order is placed
        category: Product/service category
        order_date: Date order was placed
        requires_approval: Whether order requires manual approval
        commission_amount: Calculated commission (if applicable)
        metadata: Additional order metadata
    """
    order_id: str
    customer_id: str
    order_value: float
    currency: str
    region: str
    category: str
    order_date: Optional[datetime] = None
    requires_approval: bool = False
    commission_amount: Optional[float] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Set order date if not provided."""
        if self.order_date is None:
            self.order_date = datetime.now()


@dataclass
class RefundRequest:
    """
    Refund request data structure.

    Attributes:
        refund_id: Unique refund request identifier
        order_id: Original order ID
        customer_id: Customer requesting refund
        refund_amount: Amount to be refunded
        refund_type: full or partial
        reason: Reason for refund
        region: Region where refund is requested
        category: Product/service category
        order_date: Original order date
        request_date: When refund was requested
        days_since_order: Calculated days between order and refund request
        metadata: Additional refund metadata
    """
    refund_id: str
    order_id: str
    customer_id: str
    refund_amount: float
    refund_type: str  # 'full' or 'partial'
    reason: str
    region: str
    category: str
    order_date: datetime
    request_date: Optional[datetime] = None
    days_since_order: Optional[int] = None
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Calculate derived fields."""
        if self.request_date is None:
            self.request_date = datetime.now()

        if self.days_since_order is None and self.order_date:
            delta = self.request_date - self.order_date
            self.days_since_order = delta.days


# ============================================================================
# SECTION: VALIDATION RULE BASE CLASS
# ============================================================================

class ValidationRule(ABC):
    """
    Abstract base class for all validation rules.

    Each rule encapsulates a single validation check and returns a tuple
    of (is_valid, error_message). Rules should be stateless and thread-safe.
    """

    def __init__(self, rule_name: str):
        """
        Initialize validation rule.

        Args:
            rule_name: Human-readable name for this rule
        """
        self.rule_name = rule_name
        self.validation_count = 0
        self.failure_count = 0

    @abstractmethod
    def apply(self, data: Any) -> Tuple[bool, Optional[str]]:
        """
        Apply validation rule to data.

        Args:
            data: Data to validate (type depends on rule)

        Returns:
            Tuple of (is_valid, error_message)
            - is_valid: True if validation passes, False otherwise
            - error_message: None if valid, error description if invalid
        """
        pass

    def validate(self, data: Any) -> Tuple[bool, Optional[str]]:
        """
        Wrapper around apply() that tracks metrics.

        Args:
            data: Data to validate

        Returns:
            Tuple of (is_valid, error_message)
        """
        self.validation_count += 1
        is_valid, error = self.apply(data)

        if not is_valid:
            self.failure_count += 1
            logger.debug(f"Rule '{self.rule_name}' failed: {error}")
        else:
            logger.debug(f"Rule '{self.rule_name}' passed")

        return is_valid, error

    def get_metrics(self) -> Dict[str, int]:
        """
        Get validation metrics for this rule.

        Returns:
            Dictionary with validation and failure counts
        """
        return {
            'validation_count': self.validation_count,
            'failure_count': self.failure_count,
            'success_count': self.validation_count - self.failure_count
        }

    def __repr__(self) -> str:
        """String representation."""
        return f"{self.__class__.__name__}(rule_name='{self.rule_name}')"


# ============================================================================
# SECTION: CONCRETE RULE CLASSES - ORDER VALIDATION
# ============================================================================

class MinOrderValueRule(ValidationRule):
    """Validates that order value meets minimum threshold."""

    def __init__(self, min_value: float):
        """
        Initialize minimum order value rule.

        Args:
            min_value: Minimum allowed order value
        """
        super().__init__("MinOrderValue")
        self.min_value = min_value

    def apply(self, data: Union[OrderData, Dict]) -> Tuple[bool, Optional[str]]:
        """Check if order value meets minimum."""
        order_value = data.order_value if isinstance(data, OrderData) else data.get('order_value', 0)

        if order_value < self.min_value:
            return False, f"Order value {order_value} is below minimum {self.min_value}"

        return True, None


class MaxOrderValueRule(ValidationRule):
    """Validates that order value does not exceed maximum threshold."""

    def __init__(self, max_value: float):
        """
        Initialize maximum order value rule.

        Args:
            max_value: Maximum allowed order value
        """
        super().__init__("MaxOrderValue")
        self.max_value = max_value

    def apply(self, data: Union[OrderData, Dict]) -> Tuple[bool, Optional[str]]:
        """Check if order value is within maximum."""
        order_value = data.order_value if isinstance(data, OrderData) else data.get('order_value', 0)

        if order_value > self.max_value:
            return False, f"Order value {order_value} exceeds maximum {self.max_value}"

        return True, None


class RegionSupportedRule(ValidationRule):
    """Validates that order region is supported."""

    def __init__(self, supported_regions: List[str]):
        """
        Initialize region support rule.

        Args:
            supported_regions: List of valid region codes
        """
        super().__init__("RegionSupported")
        self.supported_regions = set(supported_regions)

    def apply(self, data: Union[OrderData, IntakeData, Dict]) -> Tuple[bool, Optional[str]]:
        """Check if region is supported."""
        if isinstance(data, (OrderData, IntakeData)):
            region = data.region
        else:
            region = data.get('region', '')

        if region not in self.supported_regions:
            return False, f"Region '{region}' is not supported. Valid regions: {sorted(self.supported_regions)}"

        return True, None


class HighValueThresholdRule(ValidationRule):
    """Flags orders above high-value threshold for review."""

    def __init__(self, threshold: float):
        """
        Initialize high-value threshold rule.

        Args:
            threshold: Value above which orders are flagged
        """
        super().__init__("HighValueThreshold")
        self.threshold = threshold

    def apply(self, data: Union[OrderData, Dict]) -> Tuple[bool, Optional[str]]:
        """Check if order exceeds high-value threshold."""
        order_value = data.order_value if isinstance(data, OrderData) else data.get('order_value', 0)

        if order_value > self.threshold:
            # This is a warning, not a failure
            return True, f"INFO: Order value {order_value} exceeds high-value threshold {self.threshold}"

        return True, None


class CurrencyMatchRule(ValidationRule):
    """Validates that order currency matches expected currency."""

    def __init__(self, expected_currency: str):
        """
        Initialize currency match rule.

        Args:
            expected_currency: Expected ISO currency code
        """
        super().__init__("CurrencyMatch")
        self.expected_currency = expected_currency

    def apply(self, data: Union[OrderData, Dict]) -> Tuple[bool, Optional[str]]:
        """Check if currency matches expected."""
        currency = data.currency if isinstance(data, OrderData) else data.get('currency', '')

        if currency != self.expected_currency:
            return False, f"Currency '{currency}' does not match expected '{self.expected_currency}'"

        return True, None


# ============================================================================
# SECTION: CONCRETE RULE CLASSES - COMMISSION VALIDATION
# ============================================================================

class CommissionCalculationRule(ValidationRule):
    """Calculates and validates commission based on tiered rates."""

    def __init__(self, tiers: List[Any], min_floor: float = 0.0, max_cap: Optional[float] = None):
        """
        Initialize commission calculation rule.

        Args:
            tiers: List of commission tier objects
            min_floor: Minimum commission amount
            max_cap: Maximum commission cap (None for unlimited)
        """
        super().__init__("CommissionCalculation")
        self.tiers = sorted(tiers, key=lambda t: t.min_value)
        self.min_floor = min_floor
        self.max_cap = max_cap

    def _calculate_commission(self, order_value: float) -> float:
        """
        Calculate commission for given order value.

        Args:
            order_value: Order value to calculate commission for

        Returns:
            Calculated commission amount
        """
        commission = 0.0

        # Find applicable tier
        for tier in self.tiers:
            if order_value >= tier.min_value:
                if tier.max_value is None or order_value <= tier.max_value:
                    # Calculate percentage-based commission
                    commission = (order_value * tier.rate_percent / 100.0) + tier.flat_fee
                    break

        # Apply floor and cap
        commission = max(commission, self.min_floor)
        if self.max_cap is not None:
            commission = min(commission, self.max_cap)

        return commission

    def apply(self, data: Union[OrderData, Dict]) -> Tuple[bool, Optional[str]]:
        """Calculate and validate commission."""
        order_value = data.order_value if isinstance(data, OrderData) else data.get('order_value', 0)

        calculated_commission = self._calculate_commission(order_value)

        # If data has existing commission, validate it
        existing_commission = None
        if isinstance(data, OrderData):
            existing_commission = data.commission_amount
        elif isinstance(data, dict):
            existing_commission = data.get('commission_amount')

        if existing_commission is not None:
            # Allow small floating-point differences
            if abs(existing_commission - calculated_commission) > 0.01:
                return False, f"Commission mismatch: expected {calculated_commission:.2f}, got {existing_commission:.2f}"

        return True, f"Calculated commission: {calculated_commission:.2f}"


class CommissionTierValidationRule(ValidationRule):
    """Validates that order falls into a valid commission tier."""

    def __init__(self, tiers: List[Any]):
        """
        Initialize tier validation rule.

        Args:
            tiers: List of commission tier objects
        """
        super().__init__("CommissionTierValidation")
        self.tiers = sorted(tiers, key=lambda t: t.min_value)

    def apply(self, data: Union[OrderData, Dict]) -> Tuple[bool, Optional[str]]:
        """Check if order value falls into valid tier."""
        order_value = data.order_value if isinstance(data, OrderData) else data.get('order_value', 0)

        for tier in self.tiers:
            if order_value >= tier.min_value:
                if tier.max_value is None or order_value <= tier.max_value:
                    return True, f"Order matches tier: {tier.tier_name}"

        return False, f"Order value {order_value} does not match any commission tier"


# ============================================================================
# SECTION: CONCRETE RULE CLASSES - REFUND VALIDATION
# ============================================================================

class RefundWindowRule(ValidationRule):
    """Validates that refund request is within allowed time window."""

    def __init__(self, window_days: int):
        """
        Initialize refund window rule.

        Args:
            window_days: Number of days within which refunds are allowed
        """
        super().__init__("RefundWindow")
        self.window_days = window_days

    def apply(self, data: Union[RefundRequest, Dict]) -> Tuple[bool, Optional[str]]:
        """Check if refund is within time window."""
        if isinstance(data, RefundRequest):
            days_since_order = data.days_since_order
        else:
            order_date = data.get('order_date')
            request_date = data.get('request_date', datetime.now())

            if isinstance(order_date, str):
                order_date = datetime.fromisoformat(order_date)
            if isinstance(request_date, str):
                request_date = datetime.fromisoformat(request_date)

            days_since_order = (request_date - order_date).days

        if days_since_order > self.window_days:
            return False, f"Refund requested {days_since_order} days after order, exceeds {self.window_days}-day window"

        return True, None


class PartialRefundAllowedRule(ValidationRule):
    """Validates whether partial refunds are permitted."""

    def __init__(self, partial_allowed: bool):
        """
        Initialize partial refund rule.

        Args:
            partial_allowed: Whether partial refunds are permitted
        """
        super().__init__("PartialRefundAllowed")
        self.partial_allowed = partial_allowed

    def apply(self, data: Union[RefundRequest, Dict]) -> Tuple[bool, Optional[str]]:
        """Check if partial refund is allowed."""
        refund_type = data.refund_type if isinstance(data, RefundRequest) else data.get('refund_type', '')

        if refund_type == 'partial' and not self.partial_allowed:
            return False, "Partial refunds are not allowed by policy"

        return True, None


class RestockingFeeRule(ValidationRule):
    """Calculates and validates restocking fee for refunds."""

    def __init__(self, fee_percent: float):
        """
        Initialize restocking fee rule.

        Args:
            fee_percent: Restocking fee as percentage of refund amount
        """
        super().__init__("RestockingFee")
        self.fee_percent = fee_percent

    def apply(self, data: Union[RefundRequest, Dict]) -> Tuple[bool, Optional[str]]:
        """Calculate restocking fee."""
        refund_amount = data.refund_amount if isinstance(data, RefundRequest) else data.get('refund_amount', 0)

        restocking_fee = refund_amount * (self.fee_percent / 100.0)
        net_refund = refund_amount - restocking_fee

        return True, f"Restocking fee: {restocking_fee:.2f}, Net refund: {net_refund:.2f}"


class RefundRegionEligibilityRule(ValidationRule):
    """Validates that refund region is eligible."""

    def __init__(self, eligible_regions: List[str]):
        """
        Initialize region eligibility rule.

        Args:
            eligible_regions: List of regions where refunds are allowed
        """
        super().__init__("RefundRegionEligibility")
        self.eligible_regions = set(eligible_regions)

    def apply(self, data: Union[RefundRequest, Dict]) -> Tuple[bool, Optional[str]]:
        """Check if region is eligible for refunds."""
        region = data.region if isinstance(data, RefundRequest) else data.get('region', '')

        if region not in self.eligible_regions:
            return False, f"Region '{region}' is not eligible for refunds"

        return True, None


class ExcludedCategoryRule(ValidationRule):
    """Validates that product category is not excluded from refunds."""

    def __init__(self, excluded_categories: List[str]):
        """
        Initialize excluded category rule.

        Args:
            excluded_categories: List of categories excluded from refunds
        """
        super().__init__("ExcludedCategory")
        self.excluded_categories = set(excluded_categories)

    def apply(self, data: Union[RefundRequest, Dict]) -> Tuple[bool, Optional[str]]:
        """Check if category is excluded."""
        category = data.category if isinstance(data, RefundRequest) else data.get('category', '')

        if category in self.excluded_categories:
            return False, f"Category '{category}' is excluded from refunds"

        return True, None


class AutoApprovalThresholdRule(ValidationRule):
    """Determines if refund requires manual approval based on amount."""

    def __init__(self, auto_approve_threshold: Optional[float], requires_approval: bool):
        """
        Initialize auto-approval rule.

        Args:
            auto_approve_threshold: Maximum amount for automatic approval
            requires_approval: Base policy for whether approval is required
        """
        super().__init__("AutoApprovalThreshold")
        self.auto_approve_threshold = auto_approve_threshold
        self.requires_approval = requires_approval

    def apply(self, data: Union[RefundRequest, Dict]) -> Tuple[bool, Optional[str]]:
        """Determine if manual approval is required."""
        refund_amount = data.refund_amount if isinstance(data, RefundRequest) else data.get('refund_amount', 0)

        if self.requires_approval:
            if self.auto_approve_threshold and refund_amount <= self.auto_approve_threshold:
                return True, f"Auto-approved: amount {refund_amount} within threshold {self.auto_approve_threshold}"
            else:
                return True, "Manual approval required"

        return True, "No approval required"


# ============================================================================
# SECTION: RULE FACTORY
# ============================================================================

class RuleFactory:
    """
    Factory for creating validation rule instances from policy dataclasses.

    This factory knows how to instantiate appropriate rule objects based on
    policy domain and configuration.
    """

    @staticmethod
    def create_order_limit_rules(policy: Any) -> List[ValidationRule]:
        """
        Create validation rules from OrderLimitsPolicy.

        Args:
            policy: OrderLimitsPolicy instance

        Returns:
            List of ValidationRule instances
        """
        rules = []

        try:
            # Minimum order value rule
            rules.append(MinOrderValueRule(policy.min_order_value))

            # Maximum order value rule
            rules.append(MaxOrderValueRule(policy.max_order_value))

            # Region support rule
            rules.append(RegionSupportedRule(policy.supported_regions))

            # High-value threshold rule
            rules.append(HighValueThresholdRule(policy.high_value_threshold))

            # Currency match rule
            rules.append(CurrencyMatchRule(policy.currency))

            logger.info(f"Created {len(rules)} order limit rules")

        except AttributeError as e:
            raise RuleInstantiationError("OrderLimitRules", f"Missing policy attribute: {e}")

        return rules

    @staticmethod
    def create_commission_rules(policy: Any) -> List[ValidationRule]:
        """
        Create validation rules from CommissionRatesPolicy.

        Args:
            policy: CommissionRatesPolicy instance

        Returns:
            List of ValidationRule instances
        """
        rules = []

        try:
            # Commission calculation rule
            rules.append(CommissionCalculationRule(
                tiers=policy.tiers,
                min_floor=policy.min_commission_floor,
                max_cap=policy.max_commission_cap
            ))

            # Tier validation rule
            rules.append(CommissionTierValidationRule(policy.tiers))

            logger.info(f"Created {len(rules)} commission rules")

        except AttributeError as e:
            raise RuleInstantiationError("CommissionRules", f"Missing policy attribute: {e}")

        return rules

    @staticmethod
    def create_refund_rules(policy: Any) -> List[ValidationRule]:
        """
        Create validation rules from RefundPolicy.

        Args:
            policy: RefundPolicy instance

        Returns:
            List of ValidationRule instances
        """
        rules = []

        try:
            # Refund window rule
            rules.append(RefundWindowRule(policy.refund_window_days))

            # Partial refund allowed rule
            rules.append(PartialRefundAllowedRule(policy.partial_refund_allowed))

            # Restocking fee rule
            rules.append(RestockingFeeRule(policy.restocking_fee_percent))

            # Region eligibility rule
            rules.append(RefundRegionEligibilityRule(policy.eligible_regions))

            # Excluded category rule
            if policy.excluded_categories:
                rules.append(ExcludedCategoryRule(policy.excluded_categories))

            # Auto-approval threshold rule
            rules.append(AutoApprovalThresholdRule(
                auto_approve_threshold=policy.auto_approve_threshold,
                requires_approval=policy.requires_approval
            ))

            logger.info(f"Created {len(rules)} refund rules")

        except AttributeError as e:
            raise RuleInstantiationError("RefundRules", f"Missing policy attribute: {e}")

        return rules

    @classmethod
    def create_rules_for_domain(cls, domain: str, policy: Any) -> List[ValidationRule]:
        """
        Create rules for specified domain.

        Args:
            domain: Policy domain name
            policy: Policy dataclass instance

        Returns:
            List of ValidationRule instances

        Raises:
            ValueError: If domain is unknown
        """
        factory_map = {
            'order_limits': cls.create_order_limit_rules,
            'commission_rates': cls.create_commission_rules,
            'refund_policy': cls.create_refund_rules,
        }

        if domain not in factory_map:
            raise ValueError(f"Unknown domain: {domain}")

        factory_func = factory_map[domain]
        rules = factory_func(policy)

        logger.debug(f"Created {len(rules)} rules for domain '{domain}'")
        return rules


# ============================================================================
# SECTION: VALIDATION ENGINE
# ============================================================================

class ValidationEngine:
    """
    Main validation engine coordinating rule application across domains.

    The engine maintains registered policy domains with their associated rules,
    executes validation workflows, aggregates errors, and tracks metrics.

    Attributes:
        domains: Dictionary mapping domain names to lists of rules
        metrics: Validation metrics by domain
    """

    def __init__(self):
        """Initialize validation engine."""
        self.domains: Dict[str, List[ValidationRule]] = {}
        self.metrics: Dict[str, Dict[str, Any]] = defaultdict(lambda: {
            'total_validations': 0,
            'total_failures': 0,
            'total_successes': 0
        })
        self.rule_cache: Dict[str, List[ValidationRule]] = {}

        logger.info("ValidationEngine initialized")

    def register_domain(self, domain: str, policy: Any) -> None:
        """
        Register a policy domain with the engine.

        Args:
            domain: Domain name (e.g., 'order_limits')
            policy: Policy dataclass instance

        Raises:
            RuleInstantiationError: If rule creation fails
        """
        logger.info(f"Registering domain: {domain}")

        # Create rules using factory
        rules = RuleFactory.create_rules_for_domain(domain, policy)

        # Store rules
        self.domains[domain] = rules
        self.rule_cache[domain] = rules

        logger.info(f"Domain '{domain}' registered with {len(rules)} rules")

    def unregister_domain(self, domain: str) -> None:
        """
        Unregister a policy domain.

        Args:
            domain: Domain name to unregister
        """
        if domain in self.domains:
            del self.domains[domain]
            if domain in self.rule_cache:
                del self.rule_cache[domain]
            logger.info(f"Domain '{domain}' unregistered")
        else:
            logger.warning(f"Attempted to unregister unknown domain: {domain}")

    def is_domain_registered(self, domain: str) -> bool:
        """
        Check if domain is registered.

        Args:
            domain: Domain name to check

        Returns:
            True if domain is registered, False otherwise
        """
        return domain in self.domains

    def list_registered_domains(self) -> List[str]:
        """
        List all registered domains.

        Returns:
            List of registered domain names
        """
        return list(self.domains.keys())

    def validate(self, domain: str, data: Union[Dict, Any],
                 raise_on_error: bool = False) -> List[str]:
        """
        Validate data against registered domain rules.

        Args:
            domain: Domain name to validate against
            data: Data to validate (dict or dataclass instance)
            raise_on_error: Whether to raise exception on validation failure

        Returns:
            List of error messages (empty if all validations pass)

        Raises:
            ValidationDomainNotRegisteredError: If domain not registered
            ValidationErrorAggregate: If raise_on_error=True and validation fails
        """
        # Check domain registration
        if domain not in self.domains:
            raise ValidationDomainNotRegisteredError(domain)

        logger.info(f"Validating data against domain: {domain}")

        # Get rules for domain
        rules = self.domains[domain]

        # Track metrics
        self.metrics[domain]['total_validations'] += 1

        # Apply each rule and collect errors
        errors = []
        info_messages = []

        for rule in rules:
            is_valid, message = rule.validate(data)

            if not is_valid:
                errors.append(f"[{rule.rule_name}] {message}")
            elif message and message.startswith("INFO:"):
                info_messages.append(f"[{rule.rule_name}] {message}")
            elif message:
                # Success message with details
                logger.debug(f"[{rule.rule_name}] {message}")

        # Update metrics
        if errors:
            self.metrics[domain]['total_failures'] += 1
            logger.warning(f"Validation failed for domain '{domain}': {len(errors)} error(s)")
        else:
            self.metrics[domain]['total_successes'] += 1
            logger.info(f"Validation passed for domain '{domain}'")

        # Log info messages
        for info in info_messages:
            logger.info(info)

        # Raise exception if requested and errors exist
        if raise_on_error and errors:
            data_dict = asdict(data) if hasattr(data, '__dataclass_fields__') else data
            raise ValidationErrorAggregate(domain, errors, data_dict)

        return errors

    def validate_batch(self, domain: str, data_list: List[Union[Dict, Any]],
                       continue_on_error: bool = True) -> Dict[str, Any]:
        """
        Validate multiple data items against domain rules.

        Args:
            domain: Domain name to validate against
            data_list: List of data items to validate
            continue_on_error: Whether to continue after first failure

        Returns:
            Dictionary with validation results:
            {
                'total': int,
                'passed': int,
                'failed': int,
                'errors': List[Dict]  # List of {index, errors} dicts
            }
        """
        results = {
            'total': len(data_list),
            'passed': 0,
            'failed': 0,
            'errors': []
        }

        for idx, data in enumerate(data_list):
            errors = self.validate(domain, data, raise_on_error=False)

            if errors:
                results['failed'] += 1
                results['errors'].append({
                    'index': idx,
                    'errors': errors
                })

                if not continue_on_error:
                    break
            else:
                results['passed'] += 1

        logger.info(f"Batch validation complete: {results['passed']}/{results['total']} passed")
        return results

    def get_domain_metrics(self, domain: str) -> Dict[str, Any]:
        """
        Get validation metrics for specific domain.

        Args:
            domain: Domain name

        Returns:
            Dictionary of metrics
        """
        return dict(self.metrics.get(domain, {}))

    def get_all_metrics(self) -> Dict[str, Dict[str, Any]]:
        """
        Get validation metrics for all domains.

        Returns:
            Dictionary mapping domain names to their metrics
        """
        return dict(self.metrics)

    def get_rule_metrics(self, domain: str) -> List[Dict[str, Any]]:
        """
        Get per-rule metrics for a domain.

        Args:
            domain: Domain name

        Returns:
            List of dictionaries with rule metrics
        """
        if domain not in self.domains:
            return []

        rule_metrics = []
        for rule in self.domains[domain]:
            metrics = rule.get_metrics()
            metrics['rule_name'] = rule.rule_name
            rule_metrics.append(metrics)

        return rule_metrics

    def reset_metrics(self, domain: Optional[str] = None) -> None:
        """
        Reset validation metrics.

        Args:
            domain: Specific domain to reset, or None to reset all
        """
        if domain:
            if domain in self.metrics:
                self.metrics[domain] = {
                    'total_validations': 0,
                    'total_failures': 0,
                    'total_successes': 0
                }

            if domain in self.domains:
                for rule in self.domains[domain]:
                    rule.validation_count = 0
                    rule.failure_count = 0
        else:
            self.metrics.clear()
            for rules in self.domains.values():
                for rule in rules:
                    rule.validation_count = 0
                    rule.failure_count = 0

        logger.info(f"Metrics reset for: {domain if domain else 'all domains'}")


# ============================================================================
# SECTION: METRICS INTEGRATION STUBS
# ============================================================================

class MetricsCollector:
    """
    Stub for metrics collection and export.

    In production, this would integrate with monitoring systems like
    Prometheus, DataDog, CloudWatch, etc.
    """

    def __init__(self):
        """Initialize metrics collector."""
        self.counters: Dict[str, int] = defaultdict(int)
        self.histograms: Dict[str, List[float]] = defaultdict(list)
        logger.info("MetricsCollector initialized (stub)")

    def increment_counter(self, metric_name: str, value: int = 1,
                          tags: Optional[Dict[str, str]] = None) -> None:
        """
        Increment a counter metric.

        Args:
            metric_name: Name of the metric
            value: Amount to increment
            tags: Optional tags/labels
        """
        key = f"{metric_name}:{json.dumps(tags or {}, sort_keys=True)}"
        self.counters[key] += value

    def record_histogram(self, metric_name: str, value: float,
                         tags: Optional[Dict[str, str]] = None) -> None:
        """
        Record a histogram value.

        Args:
            metric_name: Name of the metric
            value: Value to record
            tags: Optional tags/labels
        """
        key = f"{metric_name}:{json.dumps(tags or {}, sort_keys=True)}"
        self.histograms[key].append(value)

    def export_metrics(self) -> Dict[str, Any]:
        """
        Export collected metrics.

        Returns:
            Dictionary of all collected metrics
        """
        return {
            'counters': dict(self.counters),
            'histograms': {
                k: {
                    'count': len(v),
                    'min': min(v) if v else 0,
                    'max': max(v) if v else 0,
                    'avg': sum(v) / len(v) if v else 0
                }
                for k, v in self.histograms.items()
            }
        }


# Global metrics collector instance
metrics_collector = MetricsCollector()


# ============================================================================
# SECTION: CLI ENTRYPOINT
# ============================================================================

def main():
    """
    Command-line interface for validation engine.

    Usage:
        python validation_engine.py --demo
        python validation_engine.py --test-domain <domain>
    """
    import argparse

    parser = argparse.ArgumentParser(description="Validation Engine CLI")
    parser.add_argument('--demo', action='store_true', help="Run demonstration")
    parser.add_argument('--test-domain', help="Test specific domain")
    parser.add_argument('--metrics', action='store_true', help="Show metrics")

    args = parser.parse_args()

    if args.demo:
        run_demo()
    elif args.test_domain:
        test_domain(args.test_domain)
    elif args.metrics:
        show_metrics()
    else:
        parser.print_help()


def run_demo():
    """Run validation engine demonstration."""
    print("\n=== Validation Engine Demo ===\n")

    # Create sample order data
    order = OrderData(
        order_id="ORD-001",
        customer_id="CUST-123",
        order_value=1500.0,
        currency="USD",
        region="US",
        category="electronics"
    )

    print(f"Sample Order: {order.order_id}, Value: ${order.order_value}")
    print("\nValidation results would appear here...")


def test_domain(domain: str):
    """Test validation for specific domain."""
    print(f"\nTesting domain: {domain}")
    print("Domain testing functionality would be implemented here...")


def show_metrics():
    """Display validation metrics."""
    print("\n=== Validation Metrics ===")
    exported = metrics_collector.export_metrics()
    print(json.dumps(exported, indent=2))


if __name__ == "__main__":
    main()


# ============================================================================
# SECTION: UNIT TESTS
# ============================================================================

import pytest
from datetime import datetime, timedelta


class TestValidationRules:
    """Test suite for individual validation rules."""

    def test_min_order_value_rule_pass(self):
        """Test MinOrderValueRule with valid order."""
        rule = MinOrderValueRule(min_value=10.0)
        order = OrderData("ORD1", "CUST1", 50.0, "USD", "US", "books")

        is_valid, error = rule.apply(order)
        assert is_valid is True
        assert error is None

    def test_min_order_value_rule_fail(self):
        """Test MinOrderValueRule with invalid order."""
        rule = MinOrderValueRule(min_value=100.0)
        order = OrderData("ORD1", "CUST1", 50.0, "USD", "US", "books")

        is_valid, error = rule.apply(order)
        assert is_valid is False
        assert "below minimum" in error

    def test_max_order_value_rule_pass(self):
        """Test MaxOrderValueRule with valid order."""
        rule = MaxOrderValueRule(max_value=10000.0)
        order = OrderData("ORD1", "CUST1", 5000.0, "USD", "US", "books")

        is_valid, error = rule.apply(order)
        assert is_valid is True

    def test_max_order_value_rule_fail(self):
        """Test MaxOrderValueRule with excessive value."""
        rule = MaxOrderValueRule(max_value=1000.0)
        order = OrderData("ORD1", "CUST1", 5000.0, "USD", "US", "books")

        is_valid, error = rule.apply(order)
        assert is_valid is False
        assert "exceeds maximum" in error

    def test_region_supported_rule_pass(self):
        """Test RegionSupportedRule with valid region."""
        rule = RegionSupportedRule(supported_regions=['US', 'CA', 'GB'])
        order = OrderData("ORD1", "CUST1", 100.0, "USD", "US", "books")

        is_valid, error = rule.apply(order)
        assert is_valid is True

    def test_region_supported_rule_fail(self):
        """Test RegionSupportedRule with unsupported region."""
        rule = RegionSupportedRule(supported_regions=['US', 'CA'])
        order = OrderData("ORD1", "CUST1", 100.0, "USD", "FR", "books")

        is_valid, error = rule.apply(order)
        assert is_valid is False
        assert "not supported" in error

    def test_currency_match_rule_pass(self):
        """Test CurrencyMatchRule with correct currency."""
        rule = CurrencyMatchRule(expected_currency="USD")
        order = OrderData("ORD1", "CUST1", 100.0, "USD", "US", "books")

        is_valid, error = rule.apply(order)
        assert is_valid is True

    def test_currency_match_rule_fail(self):
        """Test CurrencyMatchRule with wrong currency."""
        rule = CurrencyMatchRule(expected_currency="USD")
        order = OrderData("ORD1", "CUST1", 100.0, "EUR", "US", "books")

        is_valid, error = rule.apply(order)
        assert is_valid is False
        assert "does not match" in error

    def test_refund_window_rule_pass(self):
        """Test RefundWindowRule within valid window."""
        rule = RefundWindowRule(window_days=30)

        order_date = datetime.now() - timedelta(days=15)
        refund = RefundRequest(
            refund_id="REF1",
            order_id="ORD1",
            customer_id="CUST1",
            refund_amount=50.0,
            refund_type="full",
            reason="defective",
            region="US",
            category="electronics",
            order_date=order_date
        )

        is_valid, error = rule.apply(refund)
        assert is_valid is True

    def test_refund_window_rule_fail(self):
        """Test RefundWindowRule outside valid window."""
        rule = RefundWindowRule(window_days=30)

        order_date = datetime.now() - timedelta(days=45)
        refund = RefundRequest(
            refund_id="REF1",
            order_id="ORD1",
            customer_id="CUST1",
            refund_amount=50.0,
            refund_type="full",
            reason="defective",
            region="US",
            category="electronics",
            order_date=order_date
        )

        is_valid, error = rule.apply(refund)
        assert is_valid is False
        assert "exceeds" in error

    def test_partial_refund_allowed_rule_pass(self):
        """Test PartialRefundAllowedRule when allowed."""
        rule = PartialRefundAllowedRule(partial_allowed=True)
        refund = RefundRequest(
            refund_id="REF1",
            order_id="ORD1",
            customer_id="CUST1",
            refund_amount=25.0,
            refund_type="partial",
            reason="damaged",
            region="US",
            category="books",
            order_date=datetime.now()
        )

        is_valid, error = rule.apply(refund)
        assert is_valid is True

    def test_partial_refund_allowed_rule_fail(self):
        """Test PartialRefundAllowedRule when not allowed."""
        rule = PartialRefundAllowedRule(partial_allowed=False)
        refund = RefundRequest(
            refund_id="REF1",
            order_id="ORD1",
            customer_id="CUST1",
            refund_amount=25.0,
            refund_type="partial",
            reason="damaged",
            region="US",
            category="books",
            order_date=datetime.now()
        )

        is_valid, error = rule.apply(refund)
        assert is_valid is False
        assert "not allowed" in error


class TestRuleFactory:
    """Test suite for RuleFactory."""

    def test_create_rules_unknown_domain(self):
        """Test rule creation for unknown domain."""
        with pytest.raises(ValueError, match="Unknown domain"):
            RuleFactory.create_rules_for_domain('unknown_domain', None)


class TestValidationEngine:
    """Test suite for ValidationEngine."""

    def test_engine_initialization(self):
        """Test ValidationEngine initialization."""
        engine = ValidationEngine()
        assert isinstance(engine.domains, dict)
        assert len(engine.domains) == 0

    def test_domain_registration_check(self):
        """Test checking domain registration."""
        engine = ValidationEngine()
        assert not engine.is_domain_registered('test_domain')

    def test_list_registered_domains(self):
        """Test listing registered domains."""
        engine = ValidationEngine()
        domains = engine.list_registered_domains()
        assert isinstance(domains, list)
        assert len(domains) == 0

    def test_validation_unregistered_domain(self):
        """Test validation against unregistered domain."""
        engine = ValidationEngine()

        with pytest.raises(ValidationDomainNotRegisteredError):
            engine.validate('nonexistent', {})

    def test_get_domain_metrics(self):
        """Test retrieving domain metrics."""
        engine = ValidationEngine()
        metrics = engine.get_domain_metrics('test_domain')
        assert isinstance(metrics, dict)

    def test_get_all_metrics(self):
        """Test retrieving all metrics."""
        engine = ValidationEngine()
        metrics = engine.get_all_metrics()
        assert isinstance(metrics, dict)

    def test_reset_metrics(self):
        """Test resetting metrics."""
        engine = ValidationEngine()
        engine.reset_metrics()
        # Should not raise any errors


class TestDataClasses:
    """Test suite for validation data classes."""

    def test_intake_data_creation(self):
        """Test IntakeData creation."""
        intake = IntakeData(
            customer_id="CUST1",
            customer_type="business",
            region="US",
            industry="technology"
        )
        assert intake.customer_id == "CUST1"
        assert intake.timestamp is not None

    def test_order_data_creation(self):
        """Test OrderData creation."""
        order = OrderData(
            order_id="ORD1",
            customer_id="CUST1",
            order_value=500.0,
            currency="USD",
            region="US",
            category="software"
        )
        assert order.order_id == "ORD1"
        assert order.order_date is not None

    def test_refund_request_creation(self):
        """Test RefundRequest creation with date calculation."""
        order_date = datetime.now() - timedelta(days=10)
        refund = RefundRequest(
            refund_id="REF1",
            order_id="ORD1",
            customer_id="CUST1",
            refund_amount=100.0,
            refund_type="full",
            reason="defective",
            region="US",
            category="electronics",
            order_date=order_date
        )

        assert refund.days_since_order == 10
        assert refund.request_date is not None


class TestExceptions:
    """Test suite for custom exceptions."""

    def test_validation_domain_not_registered_error(self):
        """Test ValidationDomainNotRegisteredError."""
        error = ValidationDomainNotRegisteredError("test_domain")
        assert error.domain == "test_domain"
        assert "not registered" in str(error)

    def test_validation_error_aggregate(self):
        """Test ValidationErrorAggregate."""
        errors = ["Error 1", "Error 2", "Error 3"]
        aggregate = ValidationErrorAggregate("test_domain", errors)

        assert aggregate.domain == "test_domain"
        assert len(aggregate.errors) == 3

        report = aggregate.get_error_report()
        assert "test_domain" in report
        assert "3" in report

    def test_rule_instantiation_error(self):
        """Test RuleInstantiationError."""
        error = RuleInstantiationError("TestRule", "missing parameter")
        assert error.rule_class == "TestRule"
        assert "missing parameter" in str(error)


class TestMetricsCollector:
    """Test suite for MetricsCollector."""

    def test_metrics_collector_init(self):
        """Test MetricsCollector initialization."""
        collector = MetricsCollector()
        assert isinstance(collector.counters, defaultdict)
        assert isinstance(collector.histograms, defaultdict)

    def test_increment_counter(self):
        """Test counter increment."""
        collector = MetricsCollector()
        collector.increment_counter("test_metric", value=5)

        exported = collector.export_metrics()
        assert len(exported['counters']) > 0

    def test_record_histogram(self):
        """Test histogram recording."""
        collector = MetricsCollector()
        collector.record_histogram("test_histogram", 10.5)
        collector.record_histogram("test_histogram", 20.5)

        exported = collector.export_metrics()
        assert len(exported['histograms']) > 0

    def test_export_metrics(self):
        """Test metrics export."""
        collector = MetricsCollector()
        collector.increment_counter("counter1", 1)
        collector.record_histogram("hist1", 5.0)

        exported = collector.export_metrics()
        assert 'counters' in exported
        assert 'histograms' in exported


class TestEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_rule_with_dict_input(self):
        """Test rules with dictionary input instead of dataclass."""
        rule = MinOrderValueRule(min_value=10.0)
        data = {'order_value': 50.0}

        is_valid, error = rule.apply(data)
        assert is_valid is True

    def test_rule_metrics_tracking(self):
        """Test that rule metrics are tracked correctly."""
        rule = MinOrderValueRule(min_value=10.0)
        order = OrderData("ORD1", "CUST1", 50.0, "USD", "US", "books")

        # Apply rule multiple times
        for _ in range(5):
            rule.validate(order)

        metrics = rule.get_metrics()
        assert metrics['validation_count'] == 5
        assert metrics['success_count'] == 5
        assert metrics['failure_count'] == 0

    def test_batch_validation_continue_on_error(self):
        """Test batch validation continuing after errors."""
        engine = ValidationEngine()
        # Would need registered domain for full test
        # This tests the structure

        assert hasattr(engine, 'validate_batch')
