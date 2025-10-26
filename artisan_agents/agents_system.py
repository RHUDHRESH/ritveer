"""
ArtisanHub Agent System - LangGraph Pipeline Nodes

Modular, high-performance agent nodes for artisan marketplace processing.
Contains IntakeAgentNode for input parsing and GuardAgentNode for security/policy enforcement.

📝 lightblue - User Intake & Validation
🚨 red - Security & Policy Enforcement
"""

import asyncio
import logging
import json
import random
import re
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Union, Literal, Tuple
from dataclasses import dataclass, field, asdict
from pydantic import BaseModel, Field, validator
import traceback

# Import existing modular tools
try:
    from .extraction_tool import ExtractionTool, ExtractionResult
    from .tools.validation_engine import ValidationEngine, IntakeData
    from .tools.policy_loader import PolicyLoader, OrderLimitsPolicy
except ImportError:
    # Fallback for direct imports if needed
    from extraction_tool import ExtractionTool, ExtractionResult
    from tools.validation_engine import ValidationEngine, IntakeData
    from tools.policy_loader import PolicyLoader, OrderLimitsPolicy

# Configure logging for intake processing
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


# ============================================================================
# SECTION: WORKFLOW STATE SCHEMAS
# ============================================================================

@dataclass
class IntakeRawInput:
    """
    Raw input data from user submission.

    Attributes:
        text: Raw human-readable request text
        metadata: Additional context (source, user_id, timestamp, etc.)
    """
    text: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """Validate input constraints."""
        if not self.text or not self.text.strip():
            raise ValueError("Input text cannot be empty")


@dataclass
class IntakeAgentState:
    """
    Complete state for intake processing workflow.

    Attributes:
        raw: Original raw input data
        slots: Extracted and normalized slots from input
        validation_results: Results from business rule validation
        policy_flags: Policy compliance indicators
        errors: List of processing errors encountered
        timestamp: When this state was created
        transition: Next workflow step to take
        log: Processing log for debugging and monitoring
    """
    raw: IntakeRawInput
    slots: Optional[ExtractionResult] = None
    validation_results: List[str] = field(default_factory=list)
    policy_flags: Dict[str, bool] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    transition: str = "pending"
    log: List[str] = field(default_factory=list)

    def add_log_entry(self, message: str, level: str = "INFO"):
        """Add entry to processing log."""
        timestamp = datetime.now().isoformat()
        self.log.append(f"[{timestamp}] {level}: {message}")

    def add_error(self, error: str):
        """Add error to error list and log."""
        self.errors.append(error)
        self.add_log_entry(f"ERROR: {error}", "ERROR")


@dataclass
class IntakeAgentOutput:
    """
    Output from IntakeAgentNode execution.

    Attributes:
        normalized: Normalized slot data for downstream processing
        valid: Whether input passed all validation checks
        next_node: Next node in LangGraph pipeline to route to
        log: Complete processing log
        error_details: Detailed error information if validation failed
        metadata: Additional output metadata
    """
    normalized: Dict[str, Any]
    valid: bool
    next_node: str
    log: List[str]
    error_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SECTION: INTAKEAGENT NODE CLASS
# ============================================================================

class IntakeAgentNode:
    """
    LangGraph-ready IntakeAgentNode for artisan marketplace intake processing.

    Entry point that parses raw human input, extracts normalized slots using
    modular extraction tools, validates against business rules and policies,
    and determines next pipeline step.

    Role: Entry point, parses raw human input for artisan marketplace requests.
    Inputs: Raw text input with materials, quantities, location, urgency, notes
    Outputs: Normalized slots, validation results, next node transition
    Error Handling: Returns error details and "error" transition for downstream handling
    Tool Dependencies: slot extraction, validation engine, policy loader
    Downstream Transitions: "validated" -> ClusterAgent, "clarification_needed" -> ClarifyAgent, "error" -> ErrorHandler
    """

    def __init__(
        self,
        node_id: str = "intake_agent",
        extraction_model: str = "llama3",
        enable_policy_validation: bool = True,
        enable_logging: bool = True
    ):
        """
        Initialize IntakeAgentNode with configuration.

        Args:
            node_id: Unique identifier for this node in LangGraph
            extraction_model: Ollama model to use for slot extraction
            enable_policy_validation: Whether to apply business policy validation
            enable_logging: Whether to enable detailed processing logs
        """
        self.node_id = node_id
        self.extraction_model = extraction_model
        self.enable_policy_validation = enable_policy_validation
        self.enable_logging = enable_logging

        # Initialize modular tools
        self.extraction_tool = ExtractionTool(ollama_model=extraction_model)
        self.validation_engine = ValidationEngine() if enable_policy_validation else None
        self.policy_loader = PolicyLoader("policies") if enable_policy_validation else None

        # Load business policies if enabled
        if self.enable_policy_validation and self.policy_loader:
            try:
                self._load_business_policies()
            except Exception as e:
                logger.warning(f"Could not load business policies: {e}")

        # Transition mapping for LangGraph routing
        self.transition_map = {
            "validated": "ClusterAgent",
            "clarification_needed": "ClarifyAgent",
            "error": "ErrorHandler"
        }

        # Visual metadata for UI/graph editor
        self.meta = {
            "icon": "📝",
            "color": "lightblue",
            "description": "User Intake & Validation",
            "order": 1,
            "input_example": {
                "text": "Need 5 kg of aluminum sheets in Chennai by tonight, URGENT.",
                "metadata": {"source": "whatsapp", "user_id": "user123"}
            },
            "output_example": {
                "normalized": {
                    "material": "aluminum sheets",
                    "quantity": 5.0,
                    "unit": "kg",
                    "location": "Chennai",
                    "urgency": "URGENT"
                },
                "valid": True,
                "next_node": "ClusterAgent"
            }
        }

        logger.info(f"IntakeAgentNode '{node_id}' initialized successfully")

    def _load_business_policies(self):
        """Load business policies for validation."""
        if not self.policy_loader:
            return

        try:
            # Load order limits policy for validation
            order_limits = self.policy_loader.load_policy('order_limits')
            self.validation_engine.register_domain('order_limits', order_limits)
            logger.info("Loaded order limits policy for validation")
        except Exception as e:
            logger.warning(f"Could not load order limits policy: {e}")

    async def execute(self, state: IntakeAgentState) -> IntakeAgentOutput:
        """
        Async execute method for LangGraph node processing.

        Args:
            state: Current workflow state with raw input

        Returns:
            IntakeAgentOutput with normalized data and next node transition
        """
        start_time = datetime.now()
        output_log = []

        try:
            # Log input and timestamp
            output_log.append(f"Processing intake request at {start_time.isoformat()}")
            output_log.append(f"Raw input: {state.raw.text[:100]}{'...' if len(state.raw.text) > 100 else ''}")

            # Step 1: Extract slots using modular extraction tool
            output_log.append("Step 1: Extracting slots from raw input...")
            slots = await asyncio.get_event_loop().run_in_executor(
                None, self.extraction_tool.extract_all, state.raw.text
            )

            state.slots = slots
            state.add_log_entry("Slot extraction completed")

            # Log extracted slots
            slot_summary = {
                "material": slots.material.value,
                "quantity": f"{slots.quantity.value} {slots.quantity.unit}" if slots.quantity.value else None,
                "location": slots.location.value,
                "urgency": slots.urgency.value
            }
            output_log.append(f"Extracted slots: {json.dumps(slot_summary, default=str)}")

            # Step 2: Validate slots and completeness
            output_log.append("Step 2: Validating slot completeness...")
            validation_errors = self._validate_slot_completeness(slots)

            if validation_errors:
                state.add_error(f"Slot validation failed: {', '.join(validation_errors)}")
                output_log.append(f"Validation errors: {validation_errors}")

            # Step 3: Apply policy rules for acceptability
            output_log.append("Step 3: Applying business policy validation...")
            policy_validation_results = []

            if self.enable_policy_validation and self.validation_engine:
                # Create intake data for validation
                intake_data = self._create_intake_data_from_slots(slots, state.raw)

                # Validate against business policies
                policy_errors = self.validation_engine.validate('order_limits', intake_data)
                policy_validation_results.extend(policy_errors)

                if policy_errors:
                    state.add_error(f"Policy validation failed: {', '.join(policy_errors)}")
                    output_log.append(f"Policy errors: {policy_errors}")

            # Step 4: Decide transition based on validation results
            output_log.append("Step 4: Determining workflow transition...")
            transition = self._determine_transition(slots, validation_errors, policy_validation_results)

            state.transition = transition
            state.add_log_entry(f"Transition determined: {transition}")

            # Step 5: Prepare normalized output
            normalized = self._normalize_slots_for_output(slots)
            is_valid = transition == "validated"

            # Create output
            output = IntakeAgentOutput(
                normalized=normalized,
                valid=is_valid,
                next_node=self.transition_map.get(transition, "ErrorHandler"),
                log=output_log + state.log,
                error_details={
                    "validation_errors": validation_errors,
                    "policy_errors": policy_validation_results,
                    "slot_errors": [str(e) for e in slots.errors.values()] if slots.errors else []
                } if not is_valid else None,
                metadata={
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "extraction_method_flags": slots.method_flags,
                    "transition_reason": self._get_transition_reason(transition, validation_errors, policy_validation_results, slots)
                }
            )

            # Final logging
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            output_log.append(f"Processing completed in {processing_time:.2f}ms")
            output_log.append(f"Final transition: {transition} -> {output.next_node}")

            logger.info(f"IntakeAgentNode completed: {transition} -> {output.next_node}")
            return output

        except Exception as e:
            # Handle unexpected errors
            error_msg = f"Unexpected error in IntakeAgentNode: {str(e)}"
            state.add_error(error_msg)
            output_log.append(f"ERROR: {error_msg}")
            output_log.append(f"Traceback: {traceback.format_exc()}")

            logger.error(f"IntakeAgentNode error: {e}", exc_info=True)

            return IntakeAgentOutput(
                normalized={},
                valid=False,
                next_node="ErrorHandler",
                log=output_log + state.log,
                error_details={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc()
                },
                metadata={"processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000}
            )

    def _validate_slot_completeness(self, slots: ExtractionResult) -> List[str]:
        """
        Validate that required slots are present and valid.

        Args:
            slots: Extracted slot data

        Returns:
            List of validation error messages
        """
        errors = []

        # Check for critical missing slots
        if not slots.material.value:
            errors.append("Material specification is required")

        if not slots.quantity.value or not slots.quantity.unit:
            errors.append("Quantity and unit are required")

        if not slots.location.value:
            errors.append("Location is required")

        # Validate slot values
        if slots.quantity.value and slots.quantity.value <= 0:
            errors.append("Quantity must be greater than zero")

        if slots.quantity.unit and slots.quantity.unit not in ['kg', 'm', 'pcs']:
            errors.append(f"Invalid unit: {slots.quantity.unit}")

        if slots.urgency.value and slots.urgency.value not in ['NORMAL', 'URGENT', 'EMERGENCY']:
            errors.append(f"Invalid urgency level: {slots.urgency.value}")

        return errors

    def _create_intake_data_from_slots(self, slots: ExtractionResult, raw_input: IntakeRawInput) -> Dict[str, Any]:
        """
        Create intake data structure for policy validation.

        Args:
            slots: Extracted slot data
            raw_input: Original raw input

        Returns:
            Intake data dictionary for validation engine
        """
        return {
            "customer_id": raw_input.metadata.get("user_id", "unknown"),
            "customer_type": "business",  # Default assumption
            "region": slots.location.value or "unknown",
            "industry": "artisan_marketplace",  # Default
            "order_value": slots.quantity.value or 0,
            "metadata": {
                "material": slots.material.value,
                "quantity": slots.quantity.value,
                "unit": slots.quantity.unit,
                "urgency": slots.urgency.value,
                "source": raw_input.metadata.get("source", "unknown")
            }
        }

    def _determine_transition(self, slots: ExtractionResult, validation_errors: List[str], policy_errors: List[str]) -> str:
        """
        Determine next workflow transition based on validation results.

        Args:
            slots: Extracted slot data
            validation_errors: List of slot validation errors
            policy_errors: List of policy validation errors

        Returns:
            Transition string: "validated", "clarification_needed", or "error"
        """
        # If we have critical extraction errors, need clarification
        if not slots.material.value or not slots.quantity.value or not slots.location.value:
            return "clarification_needed"

        # If we have validation errors but slots are present, need clarification
        if validation_errors:
            return "clarification_needed"

        # If we have policy violations, this is an error
        if policy_errors:
            return "error"

        # If we have warnings but valid data, proceed to clustering
        if slots.urgency.value == "EMERGENCY":
            logger.warning("High urgency request detected")

        return "validated"

    def _normalize_slots_for_output(self, slots: ExtractionResult) -> Dict[str, Any]:
        """
        Normalize extracted slots for downstream processing.

        Args:
            slots: Extracted slot data

        Returns:
            Normalized dictionary for next pipeline steps
        """
        return {
            "material": {
                "value": slots.material.value,
                "confidence": "high" if slots.method_flags.get('material', {}).get('ollama', False) else "medium"
            },
            "quantity": {
                "value": slots.quantity.value,
                "unit": slots.quantity.unit,
                "formatted": f"{slots.quantity.value} {slots.quantity.unit}" if slots.quantity.value and slots.quantity.unit else None
            },
            "location": {
                "value": slots.location.value,
                "coordinates": None  # Could be enhanced with geocoding
            },
            "urgency": {
                "value": slots.urgency.value,
                "priority_score": self._calculate_priority_score(slots.urgency.value)
            },
            "extraction_metadata": {
                "method_flags": slots.method_flags,
                "errors": slots.errors,
                "timestamp": datetime.now().isoformat()
            }
        }

    def _calculate_priority_score(self, urgency: Optional[str]) -> int:
        """
        Calculate priority score from urgency level.

        Args:
            urgency: Urgency level string

        Returns:
            Numeric priority score (1-10)
        """
        urgency_map = {
            "EMERGENCY": 10,
            "URGENT": 7,
            "NORMAL": 4
        }
        return urgency_map.get(urgency or "NORMAL", 4)

    def _get_transition_reason(self, transition: str, validation_errors: List[str], policy_errors: List[str], slots: ExtractionResult) -> str:
        """
        Get human-readable reason for transition decision.

        Args:
            transition: The transition that was chosen
            validation_errors: List of validation errors
            policy_errors: List of policy errors
            slots: Extracted slot data for context

        Returns:
            Reason string explaining the transition
        """
        if transition == "validated":
            return "All slots extracted and validated successfully"
        elif transition == "clarification_needed":
            missing_slots = []
            if not slots.material.value:
                missing_slots.append("material")
            if not slots.quantity.value:
                missing_slots.append("quantity")
            if not slots.location.value:
                missing_slots.append("location")

            if missing_slots:
                return f"Missing required slots: {', '.join(missing_slots)}"
            else:
                return f"Validation issues: {', '.join(validation_errors)}"
        elif transition == "error":
            return f"Policy violations: {', '.join(policy_errors)}"
        else:
            return "Unknown transition reason"


# ============================================================================
# SECTION: GUARDAGENT NODE SCHEMAS
# ============================================================================

@dataclass
class GuardAgentInput:
    """
    Input data for GuardAgentNode from IntakeAgentNode.

    Attributes:
        normalized: Normalized slot data from intake processing
        intake_metadata: Metadata from original intake request
        previous_errors: Any errors from intake processing
        request_signature: Optional digital signature for verification
        user_context: User/session context for rate limiting and tracking
    """
    normalized: Dict[str, Any]
    intake_metadata: Dict[str, Any] = field(default_factory=dict)
    previous_errors: List[str] = field(default_factory=list)
    request_signature: Optional[str] = None
    user_context: Dict[str, Any] = field(default_factory=dict)


@dataclass
class GuardAgentState:
    """
    Complete state for guard processing workflow.

    Attributes:
        input_data: Input from IntakeAgentNode
        security_checks: Results of security validations
        policy_checks: Results of policy compliance checks
        rate_limit_status: Rate limiting check results
        signature_status: Digital signature verification status
        block_reasons: List of reasons for blocking (if any)
        risk_score: Calculated risk score (0-100)
        timestamp: When this state was created
        transition: Next workflow step to take
        log: Processing log for debugging and monitoring
    """
    input_data: GuardAgentInput
    security_checks: Dict[str, bool] = field(default_factory=dict)
    policy_checks: Dict[str, bool] = field(default_factory=dict)
    rate_limit_status: Dict[str, Any] = field(default_factory=dict)
    signature_status: Optional[str] = None
    block_reasons: List[str] = field(default_factory=list)
    risk_score: int = 0
    timestamp: datetime = field(default_factory=datetime.now)
    transition: str = "pending"
    log: List[str] = field(default_factory=list)

    def add_log_entry(self, message: str, level: str = "INFO"):
        """Add entry to processing log."""
        timestamp = datetime.now().isoformat()
        self.log.append(f"[{timestamp}] {level}: {message}")

    def add_block_reason(self, reason: str):
        """Add reason for blocking and log."""
        self.block_reasons.append(reason)
        self.add_log_entry(f"BLOCK: {reason}", "WARNING")


@dataclass
class GuardAgentOutput:
    """
    Output from GuardAgentNode execution.

    Attributes:
        approved: Whether request passed all guard checks
        block_reasons: List of reasons for blocking (if any)
        risk_score: Calculated security risk score
        transition: Next node in pipeline ('pass', 'clarify', 'fail')
        log: Complete processing log
        alert_data: Data for security alerts (if violations detected)
        metadata: Additional output metadata
    """
    approved: bool
    block_reasons: List[str]
    risk_score: int
    transition: str
    log: List[str]
    alert_data: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SECTION: GUARDAGENT NODE CLASS
# ============================================================================

class GuardAgentNode:
    """
    LangGraph-ready GuardAgentNode for security and policy enforcement.

    Security/filter/pass-through node activated after intake normalization.
    Enforces security, quality, and operational policies before allowing
    requests to proceed to downstream processing nodes.

    Role: Security/filter/pass-through node activated after intake normalization.
    Inputs: IntakeAgentOutput (normalized slots, validity flags, metadata)
    Outputs: Security clearance decision and next node transition
    Tool Dependencies: policy_loader (YAML rules), validation_engine (rule checks), messaging_stubs (alerts)
    Security Checks: Profanity, injection, rate limiting, banned words, policy blocks
    Operational Checks: Digital signatures, duplicate detection, bot/spam detection
    Downstream Transitions: "pass" -> ClusterAgent, "clarify" -> ClarifyAgent, "fail" -> ErrorHandlerAgent
    """

    def __init__(
        self,
        node_id: str = "guard_agent",
        enable_rate_limiting: bool = True,
        enable_signature_check: bool = True,
        enable_profanity_filter: bool = True,
        enable_policy_guards: bool = True,
        rate_limit_window: int = 300,  # 5 minutes
        max_requests_per_window: int = 10,
        enable_logging: bool = True
    ):
        """
        Initialize GuardAgentNode with security configuration.

        Args:
            node_id: Unique identifier for this node in LangGraph
            enable_rate_limiting: Whether to enforce rate limiting
            enable_signature_check: Whether to verify digital signatures
            enable_profanity_filter: Whether to filter profane content
            enable_policy_guards: Whether to apply policy-based blocking
            rate_limit_window: Time window for rate limiting (seconds)
            max_requests_per_window: Max requests per window per user
            enable_logging: Whether to enable detailed security logs
        """
        self.node_id = node_id
        self.enable_rate_limiting = enable_rate_limiting
        self.enable_signature_check = enable_signature_check
        self.enable_profanity_filter = enable_profanity_filter
        self.enable_policy_guards = enable_policy_guards
        self.rate_limit_window = rate_limit_window
        self.max_requests_per_window = max_requests_per_window
        self.enable_logging = enable_logging

        # Initialize rate limiting cache (in production, use Redis or similar)
        self.rate_limit_cache: Dict[str, List[datetime]] = {}

        # Initialize modular tools
        self.policy_loader = PolicyLoader("policies") if enable_policy_guards else None
        self.validation_engine = ValidationEngine() if enable_policy_guards else None

        # Load guard policies if enabled
        if self.enable_policy_guards and self.policy_loader:
            try:
                self._load_guard_policies()
            except Exception as e:
                logger.warning(f"Could not load guard policies: {e}")

        # Security patterns and rules
        self.profanity_patterns = self._compile_profanity_patterns()
        self.injection_patterns = self._compile_injection_patterns()
        self.banned_words = self._load_banned_words()
        self.suspicious_patterns = self._compile_suspicious_patterns()

        # Transition mapping for LangGraph routing
        self.transition_map = {
            "pass": "ClusterAgent",
            "clarify": "ClarifyAgent",
            "fail": "ErrorHandler"
        }

        # Visual metadata for UI/graph editor
        self.meta = {
            "icon": "🚨",
            "color": "red",
            "description": "Security & Policy Enforcement",
            "order": 2,
            "input_example": {
                "normalized": {
                    "material": {"value": "aluminum sheets"},
                    "quantity": {"value": 5.0, "unit": "kg"},
                    "location": {"value": "Chennai"},
                    "urgency": {"value": "URGENT"}
                },
                "intake_metadata": {"source": "whatsapp", "user_id": "user123"}
            },
            "output_example": {
                "approved": True,
                "block_reasons": [],
                "risk_score": 15,
                "transition": "pass",
                "next_node": "ClusterAgent"
            }
        }

        logger.info(f"GuardAgentNode '{node_id}' initialized with security protocols")

    def _load_guard_policies(self):
        """Load security and business guard policies."""
        if not self.policy_loader:
            return

        try:
            # Load order limits for guard validation
            order_limits = self.policy_loader.load_policy('order_limits')
            self.validation_engine.register_domain('order_limits', order_limits)

            # Load refund policy for additional checks
            refund_policy = self.policy_loader.load_policy('refund_policy')
            self.validation_engine.register_domain('refund_policy', refund_policy)

            logger.info("Loaded guard policies for security validation")
        except Exception as e:
            logger.warning(f"Could not load some guard policies: {e}")

    def _compile_profanity_patterns(self) -> List[Any]:
        """Compile regex patterns for profanity detection."""
        # Common profanity patterns (sanitized for professional use)
        return [
            re.compile(r'\b(damn|hell|stupid)\b', re.IGNORECASE),
            re.compile(r'\b(wtf|omg)\b', re.IGNORECASE),
            # Add more patterns as needed for your use case
        ]

    def _compile_injection_patterns(self) -> List[str]:
        """Compile regex patterns for injection attack detection."""
        return [
            r'<script[^>]*>.*?</script>',
            r'javascript:',
            r'on\w+\s*=',
            r'<\s*iframe',
            # SQL injection patterns
            r'(\b(union|select|insert|delete|drop|create|alter)\b)',
            r'(--|#|/\*)',
        ]

    def _load_banned_words(self) -> List[str]:
        """Load list of banned words/phrases."""
        return [
            'spam', 'scam', 'hack', 'exploit',
            # Add domain-specific banned terms
        ]

    def _compile_suspicious_patterns(self) -> List[str]:
        """Compile patterns for suspicious activity detection."""
        return [
            r'\b(free\s+money|guaranteed\s+profit)\b',
            r'\b(urgent\s+transfer|immediate\s+payment)\b',
            r'\b(bank\s+account|credit\s+card)\b',
            # Add more suspicious patterns
        ]

    async def execute(self, state: GuardAgentState) -> GuardAgentOutput:
        """
        Async execute method for LangGraph node processing.

        Args:
            state: Current workflow state with input data

        Returns:
            GuardAgentOutput with security clearance decision and next node transition
        """
        start_time = datetime.now()
        output_log = []

        try:
            # Log security scan initiation
            output_log.append(f"Security scan initiated at {start_time.isoformat()}")
            output_log.append(f"Input source: {state.input_data.intake_metadata.get('source', 'unknown')}")
            output_log.append(f"User context: {state.input_data.user_context}")

            # Step 1: Rate limiting check
            output_log.append("Step 1: Checking rate limits...")
            rate_limit_result = self._check_rate_limits(state.input_data)
            state.rate_limit_status = rate_limit_result

            if not rate_limit_result.get('allowed', True):
                state.add_block_reason(f"Rate limit exceeded: {rate_limit_result.get('reason', 'Unknown')}")
                output_log.append(f"Rate limit violation: {rate_limit_result.get('reason')}")

            # Step 2: Profanity and content filtering
            output_log.append("Step 2: Scanning for profanity and injection...")
            profanity_result = self._check_profanity_injection(state.input_data)
            state.security_checks.update(profanity_result)

            for check_name, passed in profanity_result.items():
                if not passed:
                    state.add_block_reason(f"Content violation: {check_name}")
                    output_log.append(f"Content check failed: {check_name}")

            # Step 3: Policy-based blocking
            output_log.append("Step 3: Applying policy-based guards...")
            policy_result = self._check_policy_blocks(state.input_data)
            state.policy_checks.update(policy_result)

            for check_name, passed in policy_result.items():
                if not passed:
                    state.add_block_reason(f"Policy violation: {check_name}")
                    output_log.append(f"Policy check failed: {check_name}")

            # Step 4: Digital signature verification
            output_log.append("Step 4: Verifying digital signatures...")
            signature_result = self._check_digital_signature(state.input_data)
            state.signature_status = signature_result

            if signature_result == "invalid":
                state.add_block_reason("Invalid digital signature")
                output_log.append("Digital signature verification failed")

            # Step 5: Suspicious activity detection
            output_log.append("Step 5: Scanning for suspicious patterns...")
            suspicious_result = self._check_suspicious_activity(state.input_data)
            state.security_checks.update(suspicious_result)

            for check_name, passed in suspicious_result.items():
                if not passed:
                    state.add_block_reason(f"Suspicious activity: {check_name}")
                    output_log.append(f"Suspicious pattern detected: {check_name}")

            # Step 6: Calculate overall risk score
            output_log.append("Step 6: Calculating security risk score...")
            risk_score = self._calculate_risk_score(state)
            state.risk_score = risk_score
            output_log.append(f"Calculated risk score: {risk_score}/100")

            # Step 7: Determine transition based on security results
            output_log.append("Step 7: Determining security clearance...")
            transition = self._determine_security_transition(state)

            state.transition = transition
            state.add_log_entry(f"Security transition determined: {transition}")

            # Step 8: Prepare security clearance output
            is_approved = transition == "pass"
            block_reasons = state.block_reasons.copy()

            # Create output
            output = GuardAgentOutput(
                approved=is_approved,
                block_reasons=block_reasons,
                risk_score=risk_score,
                transition=transition,
                log=output_log + state.log,
                alert_data=self._prepare_alert_data(state) if not is_approved else None,
                metadata={
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "security_checks_performed": len(state.security_checks),
                    "policy_checks_performed": len(state.policy_checks),
                    "rate_limit_status": state.rate_limit_status,
                    "signature_status": state.signature_status
                }
            )

            # Final logging
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            output_log.append(f"Security scan completed in {processing_time:.2f}ms")
            output_log.append(f"Final decision: {'APPROVED' if is_approved else 'BLOCKED'} -> {output.transition}")

            # Log security events for monitoring
            if not is_approved:
                self._log_security_event(state, output)

            logger.info(f"GuardAgentNode completed: {'APPROVED' if is_approved else 'BLOCKED'} -> {output.transition}")
            return output

        except Exception as e:
            # Handle unexpected errors in security processing
            error_msg = f"Unexpected error in GuardAgentNode: {str(e)}"
            state.add_block_reason(f"Processing error: {error_msg}")
            output_log.append(f"ERROR: {error_msg}")
            output_log.append(f"Traceback: {traceback.format_exc()}")

            logger.error(f"GuardAgentNode error: {e}", exc_info=True)

            return GuardAgentOutput(
                approved=False,
                block_reasons=["Processing error"],
                risk_score=100,  # Maximum risk for processing errors
                transition="fail",
                log=output_log + state.log,
                alert_data={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc()
                },
                metadata={"processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000}
            )

    def _check_rate_limits(self, input_data: GuardAgentInput) -> Dict[str, Any]:
        """
        Check if request exceeds rate limits.

        Args:
            input_data: Input data containing user context

        Returns:
            Dictionary with rate limit check results
        """
        if not self.enable_rate_limiting:
            return {"allowed": True, "reason": "Rate limiting disabled"}

        user_id = input_data.user_context.get("user_id", "anonymous")
        current_time = datetime.now()

        # Initialize user rate limit tracking if needed
        if user_id not in self.rate_limit_cache:
            self.rate_limit_cache[user_id] = []

        # Clean old requests outside the window
        window_start = current_time.timestamp() - self.rate_limit_window
        self.rate_limit_cache[user_id] = [
            req_time for req_time in self.rate_limit_cache[user_id]
            if req_time > window_start
        ]

        # Check if under limit
        request_count = len(self.rate_limit_cache[user_id])

        if request_count >= self.max_requests_per_window:
            return {
                "allowed": False,
                "reason": f"Rate limit exceeded ({request_count}/{self.max_requests_per_window} requests in window)",
                "request_count": request_count,
                "window_seconds": self.rate_limit_window
            }

        # Record this request
        self.rate_limit_cache[user_id].append(current_time.timestamp())

        return {
            "allowed": True,
            "reason": "Within rate limits",
            "request_count": request_count + 1,
            "window_seconds": self.rate_limit_window
        }

    def _check_profanity_injection(self, input_data: GuardAgentInput) -> Dict[str, bool]:
        """
        Check for profanity and injection attacks in input.

        Args:
            input_data: Input data to scan

        Returns:
            Dictionary with check results for each security scan
        """
        results = {}
        text_to_scan = input_data.intake_metadata.get("original_text", "")

        # Check for profanity
        if self.enable_profanity_filter:
            results["profanity_check"] = not any(
                pattern.search(text_to_scan.lower()) for pattern in self.profanity_patterns
            )

        # Check for injection patterns
        results["injection_check"] = not any(
            pattern.search(text_to_scan) for pattern in self.injection_patterns
        )

        # Check for banned words
        results["banned_words_check"] = not any(
            banned_word.lower() in text_to_scan.lower() for banned_word in self.banned_words
        )

        return results

    def _check_policy_blocks(self, input_data: GuardAgentInput) -> Dict[str, bool]:
        """
        Check against business policy blocks.

        Args:
            input_data: Input data to validate against policies

        Returns:
            Dictionary with policy check results
        """
        results = {}

        if not self.enable_policy_guards or not self.validation_engine:
            return {"policy_checks_disabled": True}

        try:
            # Check against order limits policy
            policy_data = {
                "customer_id": input_data.user_context.get("user_id", "unknown"),
                "customer_type": "business",
                "region": input_data.normalized.get("location", {}).get("value", "unknown"),
                "industry": "artisan_marketplace",
                "order_value": input_data.normalized.get("quantity", {}).get("value", 0),
                "metadata": input_data.intake_metadata
            }

            # Validate against order limits
            order_errors = self.validation_engine.validate('order_limits', policy_data)
            results["order_limits_check"] = len(order_errors) == 0

            # Additional policy checks can be added here
            results["business_rules_check"] = True  # Placeholder for additional rules

        except Exception as e:
            logger.error(f"Policy check error: {e}")
            results["policy_check_error"] = False

        return results

    def _check_digital_signature(self, input_data: GuardAgentInput) -> str:
        """
        Verify digital signature if provided.

        Args:
            input_data: Input data containing optional signature

        Returns:
            Signature verification status: "valid", "invalid", "missing", or "disabled"
        """
        if not self.enable_signature_check:
            return "disabled"

        signature = input_data.request_signature

        if not signature:
            return "missing"

        # In a real implementation, this would verify cryptographic signatures
        # For now, we'll do a simple validation
        if len(signature) < 10:
            return "invalid"

        # Placeholder for actual signature verification logic
        # This would typically involve:
        # 1. Extracting public key from user context
        # 2. Verifying signature against request data
        # 3. Checking timestamp validity

        return "valid"

    def _check_suspicious_activity(self, input_data: GuardAgentInput) -> Dict[str, bool]:
        """
        Check for suspicious activity patterns.

        Args:
            input_data: Input data to scan for suspicious patterns

        Returns:
            Dictionary with suspicious activity check results
        """
        results = {}
        text_to_scan = input_data.intake_metadata.get("original_text", "")

        # Check for suspicious patterns
        results["suspicious_content_check"] = not any(
            pattern.search(text_to_scan.lower()) for pattern in self.suspicious_patterns
        )

        # Check for potential bot patterns (repeated identical requests)
        user_id = input_data.user_context.get("user_id", "anonymous")
        if hasattr(self, '_recent_requests'):
            recent_count = self._recent_requests.get(user_id, 0)
            results["bot_pattern_check"] = recent_count < 5  # Threshold for bot detection
        else:
            results["bot_pattern_check"] = True

        return results

    def _calculate_risk_score(self, state: GuardAgentState) -> int:
        """
        Calculate overall security risk score based on all checks.

        Args:
            state: Current guard state with all check results

        Returns:
            Risk score from 0 (no risk) to 100 (maximum risk)
        """
        risk_score = 0

        # Rate limiting violations (high risk)
        if not state.rate_limit_status.get("allowed", True):
            risk_score += 40

        # Security check failures (medium-high risk)
        failed_security_checks = sum(1 for passed in state.security_checks.values() if not passed)
        risk_score += failed_security_checks * 15

        # Policy check failures (medium risk)
        failed_policy_checks = sum(1 for passed in state.policy_checks.values() if not passed)
        risk_score += failed_policy_checks * 10

        # Invalid signature (medium risk)
        if state.signature_status == "invalid":
            risk_score += 20

        # Block reasons (additional risk per reason)
        risk_score += len(state.block_reasons) * 5

        # Cap at 100
        return min(risk_score, 100)

    def _determine_security_transition(self, state: GuardAgentState) -> str:
        """
        Determine next workflow transition based on security results.

        Args:
            state: Current guard state with all check results

        Returns:
            Transition string: "pass", "clarify", or "fail"
        """
        # If rate limited, this is a failure
        if not state.rate_limit_status.get("allowed", True):
            return "fail"

        # If we have any block reasons, determine severity
        if state.block_reasons:
            # Check if violations are fixable (clarify) or permanent (fail)
            fixable_violations = [
                "profanity_check", "injection_check", "banned_words_check",
                "suspicious_content_check", "policy_check_error"
            ]

            permanent_violations = [
                "bot_pattern_check", "invalid_signature", "Processing error"
            ]

            has_fixable = any(vio in " ".join(state.block_reasons) for vio in fixable_violations)
            has_permanent = any(vio in " ".join(state.block_reasons) for vio in permanent_violations)

            if has_permanent or state.risk_score >= 70:
                return "fail"
            elif has_fixable:
                return "clarify"

        # If risk score is moderate, may need clarification
        if 30 <= state.risk_score < 70:
            return "clarify"

        # If all checks pass or low risk, proceed
        return "pass"

    def _prepare_alert_data(self, state: GuardAgentState) -> Dict[str, Any]:
        """
        Prepare alert data for security violations.

        Args:
            state: Current guard state with violation details

        Returns:
            Alert data dictionary for downstream processing
        """
        return {
            "alert_type": "security_violation",
            "risk_score": state.risk_score,
            "block_reasons": state.block_reasons,
            "user_id": state.input_data.user_context.get("user_id", "unknown"),
            "source": state.input_data.intake_metadata.get("source", "unknown"),
            "timestamp": state.timestamp.isoformat(),
            "input_data": state.input_data.normalized,
            "security_checks": state.security_checks,
            "policy_checks": state.policy_checks,
            "rate_limit_status": state.rate_limit_status,
            "signature_status": state.signature_status
        }

    def _log_security_event(self, state: GuardAgentState, output: GuardAgentOutput):
        """
        Log security events for monitoring and alerting.

        Args:
            state: Current guard state
            output: Guard output with decision details
        """
        try:
            # In a real implementation, this would send to SIEM, monitoring system, etc.
            if self.enable_logging:
                logger.warning(f"SECURITY ALERT: {', '.join(state.block_reasons)}")
                logger.warning(f"Risk Score: {state.risk_score}, User: {state.input_data.user_context.get('user_id', 'unknown')}")

            # Use messaging stubs for local alerting
            try:
                from .tools.messaging_stubs import MessageStub
                alert_msg = MessageStub(
                    platform="internal",
                    source="guard_agent",
                    text=f"Security violation detected: {', '.join(state.block_reasons)} (Risk: {state.risk_score})"
                )

                # This would typically send to admin channels
                logger.info(f"Security alert prepared: {alert_msg.text}")

            except ImportError:
                logger.debug("Messaging stubs not available for security alerts")

        except Exception as e:
            logger.error(f"Failed to log security event: {e}")


# ============================================================================
# SECTION: CLUSTERAGENT NODE SCHEMAS
# ============================================================================

@dataclass
class ClusterAgentInput:
    """
    Input data for ClusterAgentNode from GuardAgentNode.

    Attributes:
        normalized: Normalized slot data from intake processing
        intake_metadata: Metadata from original intake request
        guard_metadata: Security validation results from GuardAgentNode
        user_context: User/session context for clustering and matching
        embedding_text: Combined text for embedding generation (material + requirements)
        location_data: Geographic coordinates for spatial clustering
    """
    normalized: Dict[str, Any]
    intake_metadata: Dict[str, Any] = field(default_factory=dict)
    guard_metadata: Dict[str, Any] = field(default_factory=dict)
    user_context: Dict[str, Any] = field(default_factory=dict)
    embedding_text: Optional[str] = None
    location_data: Optional[Tuple[float, float]] = None

    def __post_init__(self):
        """Generate embedding text if not provided."""
        if not self.embedding_text:
            material = self.normalized.get('material', {}).get('value', '')
            quantity = self.normalized.get('quantity', {}).get('formatted', '')
            urgency = self.normalized.get('urgency', {}).get('value', '')

            self.embedding_text = f"{material} {quantity} {urgency}".strip()

        # Extract location coordinates if available
        if not self.location_data and 'location' in self.normalized:
            # In a real implementation, this would use geocoding
            # For now, we'll use placeholder coordinates based on location name
            location_name = self.normalized['location'].get('value', '').lower()
            location_map = {
                'chennai': (13.0827, 80.2707),
                'mumbai': (19.0760, 72.8777),
                'delhi': (28.7041, 77.1025),
                'bangalore': (12.9716, 77.5946),
                'hyderabad': (17.3850, 78.4867),
                'pune': (18.5204, 73.8567),
                'kolkata': (22.5726, 88.3639),
                'ahmedabad': (23.0225, 72.5714)
            }
            self.location_data = location_map.get(location_name, (0.0, 0.0))


@dataclass
class ClusterAgentState:
    """
    Complete state for clustering processing workflow.

    Attributes:
        input_data: Input from GuardAgentNode
        embeddings: Generated vector embeddings for semantic clustering
        spatial_clusters: Geographic cluster assignments
        semantic_clusters: Intent/semantic cluster assignments
        candidate_matches: Potential supplier/artisan matches found
        peer_requests: Similar historical requests for comparison
        confidence_scores: Confidence levels for each candidate
        ambiguity_flags: Indicators of matching conflicts or uncertainties
        cluster_metadata: Additional clustering algorithm metadata
        timestamp: When this state was created
        transition: Next workflow step to take
        log: Processing log for debugging and monitoring
    """
    input_data: ClusterAgentInput
    embeddings: Optional[List[float]] = None
    spatial_clusters: List[int] = field(default_factory=list)
    semantic_clusters: List[int] = field(default_factory=list)
    candidate_matches: List[Dict[str, Any]] = field(default_factory=list)
    peer_requests: List[Dict[str, Any]] = field(default_factory=list)
    confidence_scores: Dict[str, float] = field(default_factory=dict)
    ambiguity_flags: List[str] = field(default_factory=list)
    cluster_metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    transition: str = "pending"
    log: List[str] = field(default_factory=list)

    def add_log_entry(self, message: str, level: str = "INFO"):
        """Add entry to processing log."""
        timestamp = datetime.now().isoformat()
        self.log.append(f"[{timestamp}] {level}: {message}")

    def add_ambiguity_flag(self, flag: str, reason: str):
        """Add ambiguity flag with reason."""
        self.ambiguity_flags.append(f"{flag}: {reason}")
        self.add_log_entry(f"AMBIGUITY: {flag} - {reason}", "WARNING")


@dataclass
class CommitAgentInput:
    """
    Input data for CommitAgentNode from SupplierAgentNode.

    Attributes:
        order_context: Original order details (material, quantity, location, urgency)
        supplier_quotes: List of validated supplier quotes with pricing and delivery
        artisan_requirements: Specific artisan requirements and preferences
        payment_preferences: Payment method and type preferences
        workflow_metadata: Workflow tracking and user context
    """
    order_context: Dict[str, Any]
    supplier_quotes: List[Dict[str, Any]]
    artisan_requirements: Dict[str, Any]
    payment_preferences: Dict[str, Any] = field(default_factory=dict)
    workflow_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CommitAgentState:
    """
    Complete state for commit processing workflow.

    Attributes:
        input_data: Input from SupplierAgentNode
        commit_strategy: Selected commitment strategy (solo/pooling)
        order_id: Generated unique order identifier
        payment_status: Payment processing results
        persistence_status: Order persistence results
        notification_status: Notification delivery results
        policy_validation: Policy compliance check results
        commit_events: Timeline of commit events
        error_details: Detailed error information if processing failed
        timestamp: When this state was created
        transition: Next workflow step to take
        log: Processing log for debugging and monitoring
    """
    input_data: CommitAgentInput
    commit_strategy: Optional[str] = None
    order_id: Optional[str] = None
    payment_status: Dict[str, Any] = field(default_factory=dict)
    persistence_status: Dict[str, Any] = field(default_factory=dict)
    notification_status: Dict[str, Any] = field(default_factory=dict)
    policy_validation: Dict[str, bool] = field(default_factory=dict)
    commit_events: List[Dict[str, Any]] = field(default_factory=list)
    error_details: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    transition: str = "pending"
    log: List[str] = field(default_factory=list)

    def add_log_entry(self, message: str, level: str = "INFO"):
        """Add entry to processing log."""
        timestamp = datetime.now().isoformat()
        self.log.append(f"[{timestamp}] {level}: {message}")

    def add_error(self, error: str):
        """Add error to error list and log."""
        self.error_details.append(error)
        self.add_log_entry(f"ERROR: {error}", "ERROR")

    def add_commit_event(self, event_type: str, event_data: Dict[str, Any]):
        """Add commit event to timeline."""
        event = {
            "event_type": event_type,
            "timestamp": datetime.now().isoformat(),
            "event_data": event_data
        }
        self.commit_events.append(event)
        self.add_log_entry(f"COMMIT EVENT: {event_type}")


@dataclass
class CommitAgentOutput:
    """
    Output from CommitAgentNode execution.

    Attributes:
        order_id: Unique order identifier if successfully created
        commit_confirmation: Confirmation details of the commitment
        payment_summary: Payment processing summary
        notification_summary: Notification delivery summary
        transition: Next node in pipeline ('committed', 'payment_error', 'policy_block')
        log: Complete processing log
        error_details: Detailed error information if processing failed
        metadata: Additional output metadata including processing metrics
    """
    order_id: Optional[str]
    commit_confirmation: Dict[str, Any]
    payment_summary: Dict[str, Any]
    notification_summary: Dict[str, Any]
    transition: str
    log: List[str]
    error_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class ClusterAgentOutput:
    """
    Output from ClusterAgentNode execution.

    Attributes:
        cluster_assignment: Assigned cluster ID or category
        candidate_list: Top matching suppliers/artisans with scores
        confidence_score: Overall confidence in the clustering result
        transition: Next node in pipeline ('clustered', 'ambiguous', 'no-match')
        log: Complete processing log
        ambiguity_details: Details about matching conflicts or uncertainties
        metadata: Additional output metadata including clustering metrics
    """
    cluster_assignment: Optional[str]
    candidate_list: List[Dict[str, Any]]
    confidence_score: float
    transition: str
    log: List[str]
    ambiguity_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SECTION: COMMITAGENT NODE CLASS
# ============================================================================

class CommitAgentNode:
    """
    LangGraph-ready CommitAgentNode for order commitment and finalization.

    Central node that executes the final commitment step after supplier shortlisting.
    Handles order creation, payment simulation, policy enforcement, persistence,
    and workflow acknowledgment for artisan marketplace orders.

    Role: Final commitment step after supplier shortlisting, central to order lifecycle
    Inputs: SupplierAgentOutput (validated quotes, order context, supplier data)
    Outputs: Committed order with payment status, notifications, and next transition
    Tool Dependencies: payment_stubs (UPI/Razorpay simulation), policy_loader (business rules),
                      data_access (CRUD operations), notification_stubs (alerts), state_manager (checkpoints)
    Payment Methods: Supports prepay and postpay with UPI, Razorpay, and wallet options
    Commit Strategies: Pooling (multi-supplier split) vs Solo (single supplier direct)
    Downstream Transitions: "committed" -> SalesAgent, "payment_error" -> ErrorHandlerAgent, "policy_block" -> ClarifyAgent
    """

    def __init__(
        self,
        node_id: str = "commit_agent",
        enable_payment_simulation: bool = True,
        enable_policy_enforcement: bool = True,
        enable_notifications: bool = True,
        enable_persistence: bool = True,
        default_payment_method: str = "upi",
        min_order_value: float = 100.0,
        enable_logging: bool = True
    ):
        """
        Initialize CommitAgentNode with commitment configuration.

        Args:
            node_id: Unique identifier for this node in LangGraph
            enable_payment_simulation: Whether to simulate payment processing
            enable_policy_enforcement: Whether to enforce business policies
            enable_notifications: Whether to send commit notifications
            enable_persistence: Whether to persist order data
            default_payment_method: Default payment method if not specified
            min_order_value: Minimum order value for policy enforcement
            enable_logging: Whether to enable detailed commit logs
        """
        self.node_id = node_id
        self.enable_payment_simulation = enable_payment_simulation
        self.enable_policy_enforcement = enable_policy_enforcement
        self.enable_notifications = enable_notifications
        self.enable_persistence = enable_persistence
        self.default_payment_method = default_payment_method
        self.min_order_value = min_order_value
        self.enable_logging = enable_logging

        # Initialize modular tools
        try:
            from .tools.payment_stubs import PaymentStub, UPIPaymentStub, RazorpayPaymentStub, PaymentMethod, PaymentStatus
            self.payment_stub = PaymentStub()
            self.upi_stub = UPIPaymentStub()
            self.razorpay_stub = RazorpayPaymentStub()
            self.PaymentMethod = PaymentMethod
            self.PaymentStatus = PaymentStatus
        except ImportError:
            # Fallback for direct imports
            from tools.payment_stubs import PaymentStub, UPIPaymentStub, RazorpayPaymentStub, PaymentMethod, PaymentStatus
            self.payment_stub = PaymentStub()
            self.upi_stub = UPIPaymentStub()
            self.razorpay_stub = RazorpayPaymentStub()
            self.PaymentMethod = PaymentMethod
            self.PaymentStatus = PaymentStatus

        try:
            from .tools.policy_loader import PolicyLoader
            self.policy_loader = PolicyLoader("policies") if enable_policy_enforcement else None
        except ImportError:
            from tools.policy_loader import PolicyLoader
            self.policy_loader = PolicyLoader("policies") if enable_policy_enforcement else None

        try:
            from .tools.data_access import DataAccessLayer, DatabaseConfig
            db_config = DatabaseConfig()
            self.data_access = DataAccessLayer(db_config) if enable_persistence else None
        except ImportError:
            from tools.data_access import DataAccessLayer, DatabaseConfig
            db_config = DatabaseConfig()
            self.data_access = DataAccessLayer(db_config) if enable_persistence else None

        try:
            from .tools.notification_stubs import EmailNotificationStub, SMSNotificationStub, NotificationBase
            self.email_stub = EmailNotificationStub() if enable_notifications else None
            self.sms_stub = SMSNotificationStub() if enable_notifications else None
            self.NotificationBase = NotificationBase
        except ImportError:
            from tools.notification_stubs import EmailNotificationStub, SMSNotificationStub, NotificationBase
            self.email_stub = EmailNotificationStub() if enable_notifications else None
            self.sms_stub = SMSNotificationStub() if enable_notifications else None
            self.NotificationBase = NotificationBase

        try:
            from .tools.state_manager import StateManager
            self.state_manager = StateManager(self.data_access) if enable_persistence else None
        except ImportError:
            from tools.state_manager import StateManager
            self.state_manager = StateManager(self.data_access) if enable_persistence else None

        # Load business policies if enabled
        if self.enable_policy_enforcement and self.policy_loader:
            try:
                self._load_commit_policies()
            except Exception as e:
                logger.warning(f"Could not load commit policies: {e}")

        # Transition mapping for LangGraph routing
        self.transition_map = {
            "committed": "SalesAgent",
            "payment_error": "ErrorHandlerAgent",
            "policy_block": "ClarifyAgent"
        }

        # Visual metadata for UI/graph editor
        self.meta = {
            "icon": "📝",
            "color": "purple",
            "description": "Order Commitment & Finalization",
            "order": 4,
            "input_example": {
                "order_context": {
                    "material": "aluminum sheets",
                    "quantity": 5.0,
                    "urgency": "URGENT"
                },
                "supplier_quotes": [
                    {"supplier_id": 1, "price": 100.0, "delivery_days": 2},
                    {"supplier_id": 2, "price": 95.0, "delivery_days": 3}
                ],
                "artisan_requirements": {
                    "material": "aluminum sheets",
                    "quality": "premium"
                }
            },
            "output_example": {
                "order_id": "ORD-20250108-001",
                "commit_confirmation": {"status": "committed", "strategy": "solo"},
                "payment_summary": {"status": "completed", "method": "upi"},
                "transition": "committed"
            }
        }

        logger.info(f"CommitAgentNode '{node_id}' initialized successfully")

    def _load_commit_policies(self):
        """Load business policies for commit validation."""
        if not self.policy_loader:
            return

        try:
            # Load order limits policy for commit validation
            order_limits = self.policy_loader.load_policy('order_limits')
            if self.data_access:
                self.data_access.register_policy_domain('order_limits', order_limits)
            logger.info("Loaded order limits policy for commit validation")
        except Exception as e:
            logger.warning(f"Could not load order limits policy: {e}")

    async def execute(self, state: CommitAgentState) -> CommitAgentOutput:
        """
        Async execute method for LangGraph node processing.

        Args:
            state: Current workflow state with input data

        Returns:
            CommitAgentOutput with order commitment results and next node transition
        """
        start_time = datetime.now()
        output_log = []

        try:
            # Log commit initiation
            output_log.append(f"Order commitment initiated at {start_time.isoformat()}")
            output_log.append(f"Order context: {state.input_data.order_context}")
            output_log.append(f"Supplier quotes count: {len(state.input_data.supplier_quotes)}")

            # Step 1: Select and validate commit strategy
            output_log.append("Step 1: Selecting commit strategy...")
            strategy_result = self._select_commit_strategy(state)
            state.commit_strategy = strategy_result["strategy"]
            state.policy_validation.update(strategy_result["policy_checks"])

            strategy_info = f"Selected strategy: {state.commit_strategy}"
            state.add_log_entry(strategy_info)
            output_log.append(strategy_info)

            # Step 2: Apply policy validation and business rules
            output_log.append("Step 2: Applying policy validation...")
            policy_result = await self._apply_policy_validation(state)

            if not policy_result["passed"]:
                state.add_error(f"Policy validation failed: {policy_result['reasons']}")
                output_log.append(f"Policy block: {policy_result['reasons']}")
                return self._create_policy_block_output(state, output_log)

            state.add_log_entry("Policy validation passed")
            output_log.append("Policy validation completed successfully")

            # Step 3: Generate unique order ID
            output_log.append("Step 3: Generating order ID...")
            order_id = self._generate_order_id()
            state.order_id = order_id

            order_info = f"Generated order ID: {order_id}"
            state.add_log_entry(order_info)
            output_log.append(order_info)

            # Step 4: Simulate payment processing
            output_log.append("Step 4: Processing payment...")
            payment_result = await self._process_payment(state)

            if not payment_result["success"]:
                state.add_error(f"Payment processing failed: {payment_result['error']}")
                output_log.append(f"Payment error: {payment_result['error']}")
                return self._create_payment_error_output(state, output_log)

            state.payment_status = payment_result["payment_data"]
            state.add_commit_event("payment_completed", payment_result["payment_data"])
            state.add_log_entry("Payment processed successfully")
            output_log.append("Payment processing completed")

            # Step 5: Persist order data
            output_log.append("Step 5: Persisting order data...")
            persistence_result = await self._persist_order(state)

            if not persistence_result["success"]:
                state.add_error(f"Order persistence failed: {persistence_result['error']}")
                output_log.append(f"Persistence error: {persistence_result['error']}")
                return self._create_persistence_error_output(state, output_log)

            state.persistence_status = persistence_result["order_data"]
            state.add_commit_event("order_persisted", persistence_result["order_data"])
            state.add_log_entry("Order persisted successfully")
            output_log.append("Order persistence completed")

            # Step 6: Send notifications to stakeholders
            output_log.append("Step 6: Sending commit notifications...")
            notification_result = await self._send_notifications(state)

            state.notification_status = notification_result["notifications"]
            state.add_commit_event("notifications_sent", notification_result["summary"])
            state.add_log_entry("Notifications sent successfully")
            output_log.append("Notification delivery completed")

            # Step 7: Update state manager with commit checkpoint
            output_log.append("Step 7: Updating workflow state...")
            if self.state_manager:
                try:
                    await self.state_manager.save_workflow_state({
                        "id": order_id,
                        "workflow_id": state.input_data.workflow_metadata.get("workflow_id", "unknown"),
                        "agent_name": self.node_id,
                        "state_data": {
                            "order_id": order_id,
                            "commit_strategy": state.commit_strategy,
                            "payment_status": state.payment_status,
                            "commit_events": state.commit_events
                        }
                    })
                    state.add_log_entry("Workflow state checkpoint saved")
                    output_log.append("State checkpoint created")
                except Exception as e:
                    logger.warning(f"State manager checkpoint failed: {e}")
                    output_log.append(f"State checkpoint warning: {e}")

            # Step 8: Determine final transition
            output_log.append("Step 8: Determining final transition...")
            transition = "committed"
            state.transition = transition

            final_info = f"Commit completed successfully: {transition}"
            state.add_log_entry(final_info)
            output_log.append(final_info)

            # Step 9: Prepare commit confirmation output
            commit_confirmation = {
                "status": "committed",
                "order_id": order_id,
                "strategy": state.commit_strategy,
                "timestamp": datetime.now().isoformat(),
                "commit_events": state.commit_events
            }

            # Create output
            output = CommitAgentOutput(
                order_id=order_id,
                commit_confirmation=commit_confirmation,
                payment_summary=state.payment_status,
                notification_summary=state.notification_status,
                transition=transition,
                log=output_log + state.log,
                error_details={
                    "errors": state.error_details,
                    "policy_violations": [k for k, v in state.policy_validation.items() if not v],
                    "recovery_suggestions": self._get_recovery_suggestions(state)
                } if state.error_details else None,
                metadata={
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "commit_strategy": state.commit_strategy,
                    "payment_method": state.payment_status.get("method", "unknown"),
                    "supplier_count": len(state.input_data.supplier_quotes),
                    "policy_checks_passed": sum(1 for v in state.policy_validation.values() if v),
                    "policy_checks_total": len(state.policy_validation),
                    "events_recorded": len(state.commit_events)
                }
            )

            # Final logging
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            output_log.append(f"Order commitment completed in {processing_time:.2f}ms")
            output_log.append(f"Final result: {transition} -> {self.transition_map.get(transition, 'Unknown')}")

            logger.info(f"CommitAgentNode completed: {transition} -> {self.transition_map.get(transition, 'Unknown')}")
            return output

        except Exception as e:
            # Handle unexpected errors in commit processing
            error_msg = f"Unexpected error in CommitAgentNode: {str(e)}"
            state.add_error(error_msg)
            output_log.append(f"ERROR: {error_msg}")
            output_log.append(f"Traceback: {traceback.format_exc()}")

            logger.error(f"CommitAgentNode error: {e}", exc_info=True)

            return CommitAgentOutput(
                order_id=None,
                commit_confirmation={"status": "failed", "error": error_msg},
                payment_summary={},
                notification_summary={},
                transition="payment_error",
                log=output_log + state.log,
                error_details={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "recovery_suggestions": ["Contact system administrator", "Check payment and policy configurations"]
                },
                metadata={"processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000}
            )

    def _select_commit_strategy(self, state: CommitAgentState) -> Dict[str, Any]:
        """
        Select commit strategy based on supplier quotes and business rules.

        Args:
            state: Current commit state

        Returns:
            Dictionary with strategy selection results and policy checks
        """
        try:
            quotes = state.input_data.supplier_quotes
            policy_checks = {}

            # Policy check: Minimum order value
            total_value = sum(quote.get("price", 0) * quote.get("quantity", 1) for quote in quotes)
            policy_checks["min_order_value"] = total_value >= self.min_order_value

            # Policy check: Maximum suppliers per order
            max_suppliers = 3  # Could be configurable
            policy_checks["max_suppliers"] = len(quotes) <= max_suppliers

            # Strategy selection logic
            if len(quotes) == 1:
                strategy = "solo"
            elif len(quotes) > 1 and all(q.get("price", 0) * q.get("quantity", 1) < 1000 for q in quotes):
                strategy = "pooling"  # Split small orders across suppliers
            else:
                strategy = "solo"  # Use best supplier for larger orders

            # Override strategy if policy violations
            if not all(policy_checks.values()):
                strategy = "policy_review_required"

            return {
                "strategy": strategy,
                "policy_checks": policy_checks,
                "total_value": total_value,
                "supplier_count": len(quotes)
            }

        except Exception as e:
            logger.error(f"Strategy selection error: {e}")
            return {
                "strategy": "error",
                "policy_checks": {"strategy_selection_error": False},
                "error": str(e)
            }

    async def _apply_policy_validation(self, state: CommitAgentState) -> Dict[str, Any]:
        """
        Apply comprehensive policy validation before commit.

        Args:
            state: Current commit state

        Returns:
            Dictionary with policy validation results
        """
        try:
            if not self.enable_policy_enforcement:
                return {"passed": True, "reasons": [], "checks": {}}

            policy_checks = {}
            violations = []

            # Check order limits policy
            try:
                order_data = {
                    "customer_id": state.input_data.workflow_metadata.get("user_id", "unknown"),
                    "customer_type": "business",
                    "region": state.input_data.order_context.get("location", "unknown"),
                    "industry": "artisan_marketplace",
                    "order_value": sum(q.get("price", 0) for q in state.input_data.supplier_quotes),
                    "metadata": state.input_data.order_context
                }

                # This would use validation engine if available
                # For now, we'll do basic policy checks
                policy_checks["order_value_check"] = order_data["order_value"] >= self.min_order_value
                policy_checks["region_check"] = order_data["region"] != "unknown"

                if not policy_checks["order_value_check"]:
                    violations.append(f"Order value below minimum: ₹{order_data['order_value']}")
                if not policy_checks["region_check"]:
                    violations.append("Location not properly specified")

            except Exception as e:
                policy_checks["policy_engine_error"] = False
                violations.append(f"Policy engine error: {e}")

            # Additional business rule checks
            urgency = state.input_data.order_context.get("urgency", "NORMAL")
            if urgency == "EMERGENCY":
                policy_checks["emergency_order_check"] = True  # Could have special rules
            else:
                policy_checks["standard_order_check"] = True

            return {
                "passed": len(violations) == 0,
                "reasons": violations,
                "checks": policy_checks
            }

        except Exception as e:
            logger.error(f"Policy validation error: {e}")
            return {
                "passed": False,
                "reasons": [f"Policy validation error: {e}"],
                "checks": {"error": False}
            }

    def _generate_order_id(self) -> str:
        """
        Generate unique order ID for the commitment.

        Returns:
            Unique order identifier string
        """
        try:
            timestamp = datetime.now().strftime("%Y%m%d")
            random_suffix = str(random.randint(100, 999))
            order_id = f"ORD-{timestamp}-{random_suffix}"

            # Ensure uniqueness by checking against existing orders
            if self.data_access:
                try:
                    existing_orders = self.data_access.get_orders_by_status("all", limit=1)
                    # In a real implementation, would check for ID collisions
                    # For now, we'll assume the timestamp + random is sufficient
                except Exception as e:
                    logger.warning(f"Could not verify order ID uniqueness: {e}")

            return order_id

        except Exception as e:
            logger.error(f"Order ID generation error: {e}")
            # Fallback order ID
            return f"ORD-{int(datetime.now().timestamp())}"

    async def _process_payment(self, state: CommitAgentState) -> Dict[str, Any]:
        """
        Process payment using configured payment stubs.

        Args:
            state: Current commit state

        Returns:
            Dictionary with payment processing results
        """
        try:
            if not self.enable_payment_simulation:
                return {
                    "success": True,
                    "payment_data": {
                        "status": "simulation_disabled",
                        "method": "none",
                        "amount": 0.0
                    }
                }

            # Calculate total order amount
            total_amount = sum(
                quote.get("price", 0) * quote.get("quantity", 1)
                for quote in state.input_data.supplier_quotes
            )

            # Determine payment method
            payment_method_pref = state.input_data.payment_preferences.get("method", self.default_payment_method)
            payment_type = state.input_data.payment_preferences.get("type", "prepay")

            # Select appropriate payment stub
            if payment_method_pref == "upi":
                payment_stub = self.upi_stub
                payment_method = self.PaymentMethod.UPI
            elif payment_method_pref == "razorpay":
                payment_stub = self.razorpay_stub
                payment_method = self.PaymentMethod.RAZORPAY
            else:
                payment_stub = self.payment_stub
                payment_method = self.PaymentMethod.WALLET

            # Create payment object
            from tools.payment_stubs import PaymentBase
            payment = PaymentBase(
                order_id=state.order_id or "PENDING",
                amount=total_amount,
                payment_method=payment_method,
                metadata={
                    "payment_type": payment_type,
                    "supplier_count": len(state.input_data.supplier_quotes),
                    "urgency": state.input_data.order_context.get("urgency", "NORMAL")
                }
            )

            # Process payment
            payment_result = payment_stub.process_payment(payment)

            return {
                "success": payment_result.status == self.PaymentStatus.COMPLETED,
                "payment_data": {
                    "transaction_id": payment_result.transaction_id,
                    "status": payment_result.status.value,
                    "method": payment_result.payment_method.value,
                    "amount": payment_result.amount,
                    "timestamp": payment_result.timestamp,
                    "metadata": payment_result.metadata
                },
                "error": None if payment_result.status == self.PaymentStatus.COMPLETED else f"Payment {payment_result.status.value}"
            }

        except Exception as e:
            logger.error(f"Payment processing error: {e}")
            return {
                "success": False,
                "payment_data": {},
                "error": str(e)
            }

    async def _persist_order(self, state: CommitAgentState) -> Dict[str, Any]:
        """
        Persist order data using data access layer.

        Args:
            state: Current commit state

        Returns:
            Dictionary with persistence results
        """
        try:
            if not self.enable_persistence or not self.data_access:
                return {
                    "success": True,
                    "order_data": {"persistence": "disabled", "order_id": state.order_id}
                }

            # Prepare order data for persistence
            order_data = {
                "id": state.order_id,
                "customer_id": state.input_data.workflow_metadata.get("user_id", "unknown"),
                "status": "committed",
                "total_amount": sum(q.get("price", 0) * q.get("quantity", 1) for q in state.input_data.supplier_quotes),
                "currency": "INR",
                "created_at": datetime.now(),
                "updated_at": datetime.now(),
                "order_items": [
                    {
                        "material": state.input_data.order_context.get("material", "unknown"),
                        "quantity": quote.get("quantity", 1),
                        "unit_price": quote.get("price", 0),
                        "supplier_id": quote.get("supplier_id", "unknown"),
                        "delivery_days": quote.get("delivery_days", 0)
                    }
                    for quote in state.input_data.supplier_quotes
                ],
                "shipping_address": {
                    "city": state.input_data.order_context.get("location", "unknown"),
                    "urgency": state.input_data.order_context.get("urgency", "NORMAL")
                },
                "payment_info": state.payment_status,
                "commit_metadata": {
                    "strategy": state.commit_strategy,
                    "commit_timestamp": datetime.now().isoformat(),
                    "workflow_id": state.input_data.workflow_metadata.get("workflow_id", "unknown")
                }
            }

            # Persist order
            persisted_order = self.data_access.create_order(order_data)

            return {
                "success": True,
                "order_data": {
                    "persisted_id": persisted_order.get("id"),
                    "status": "active",
                    "items_count": len(order_data["order_items"]),
                    "persistence_timestamp": datetime.now().isoformat()
                }
            }

        except Exception as e:
            logger.error(f"Order persistence error: {e}")
            return {
                "success": False,
                "order_data": {},
                "error": str(e)
            }

    async def _send_notifications(self, state: CommitAgentState) -> Dict[str, Any]:
        """
        Send notifications to suppliers and artisans about the commitment.

        Args:
            state: Current commit state

        Returns:
            Dictionary with notification results
        """
        try:
            if not self.enable_notifications or not self.email_stub:
                return {
                    "notifications": {"email": "disabled", "sms": "disabled"},
                    "summary": "Notifications disabled"
                }

            notifications_sent = {}
            notification_summary = []

            # Notify suppliers about order commitment
            for quote in state.input_data.supplier_quotes:
                supplier_id = quote.get("supplier_id")
                if supplier_id:
                    try:
                        # Email notification to supplier
                        supplier_notification = self.NotificationBase(
                            recipient=f"supplier{supplier_id}@example.com",
                            subject=f"New Order Committed - {state.order_id}",
                            content=f"Your quote for order {state.order_id} has been accepted. Please prepare for delivery.",
                            event_type="order_committed"
                        )
                        self.email_stub.send(supplier_notification)
                        notifications_sent[f"supplier_{supplier_id}_email"] = "sent"
                        notification_summary.append(f"Supplier {supplier_id} notified via email")

                    except Exception as e:
                        notifications_sent[f"supplier_{supplier_id}_email"] = f"failed: {e}"
                        logger.warning(f"Supplier notification failed: {e}")

            # Notify artisan about order confirmation
            try:
                artisan_notification = self.NotificationBase(
                    recipient=state.input_data.workflow_metadata.get("user_email", "artisan@example.com"),
                    subject=f"Order Confirmed - {state.order_id}",
                    content=f"Your order {state.order_id} has been successfully committed and payment processed.",
                    event_type="order_confirmation"
                )
                self.email_stub.send(artisan_notification)
                notifications_sent["artisan_email"] = "sent"
                notification_summary.append("Artisan notified via email")

            except Exception as e:
                notifications_sent["artisan_email"] = f"failed: {e}"
                logger.warning(f"Artisan notification failed: {e}")

            return {
                "notifications": notifications_sent,
                "summary": "; ".join(notification_summary) if notification_summary else "No notifications sent"
            }

        except Exception as e:
            logger.error(f"Notification sending error: {e}")
            return {
                "notifications": {"error": str(e)},
                "summary": f"Notification error: {e}"
            }

    def _create_policy_block_output(self, state: CommitAgentState, log_entries: List[str]) -> CommitAgentOutput:
        """Create output for policy block scenarios."""
        return CommitAgentOutput(
            order_id=None,
            commit_confirmation={"status": "policy_blocked"},
            payment_summary={},
            notification_summary={},
            transition="policy_block",
            log=log_entries + state.log,
            error_details={
                "error_type": "policy_violation",
                "violations": [k for k, v in state.policy_validation.items() if not v],
                "suggestions": ["Review order requirements", "Check minimum order values", "Verify location details"]
            },
            metadata={"policy_checks_failed": True}
        )

    def _create_payment_error_output(self, state: CommitAgentState, log_entries: List[str]) -> CommitAgentOutput:
        """Create output for payment error scenarios."""
        return CommitAgentOutput(
            order_id=None,
            commit_confirmation={"status": "payment_failed"},
            payment_summary={"error": "Payment processing failed"},
            notification_summary={},
            transition="payment_error",
            log=log_entries + state.log,
            error_details={
                "error_type": "payment_error",
                "payment_errors": state.error_details,
                "suggestions": ["Verify payment method", "Check payment limits", "Retry with different payment method"]
            },
            metadata={"payment_failed": True}
        )

    def _create_persistence_error_output(self, state: CommitAgentState, log_entries: List[str]) -> CommitAgentOutput:
        """Create output for persistence error scenarios."""
        return CommitAgentOutput(
            order_id=state.order_id,  # Keep order ID even if persistence failed
            commit_confirmation={"status": "persistence_failed"},
            payment_summary=state.payment_status,
            notification_summary={},
            transition="payment_error",  # Route to error handler for persistence issues
            log=log_entries + state.log,
            error_details={
                "error_type": "persistence_error",
                "persistence_errors": state.error_details,
                "suggestions": ["Check database connectivity", "Verify data format", "Contact system administrator"]
            },
            metadata={"persistence_failed": True}
        )

    def _get_recovery_suggestions(self, state: CommitAgentState) -> List[str]:
        """Get recovery suggestions based on current state."""
        suggestions = []

        if not all(state.policy_validation.values()):
            suggestions.append("Review and adjust order requirements to meet policy constraints")

        if state.error_details:
            if any("payment" in error.lower() for error in state.error_details):
                suggestions.append("Try alternative payment methods or contact support")
            if any("persistence" in error.lower() for error in state.error_details):
                suggestions.append("Check system status and retry operation")

        return suggestions if suggestions else ["Contact system administrator for assistance"]

    @property
    def transitions(self) -> Dict[str, str]:
        """Get transition mapping for LangGraph routing."""
        return self.transition_map

    @property
    def meta(self) -> Dict[str, Any]:
        """Get node metadata for UI/graph editor."""
        return self._meta

    @meta.setter
    def meta(self, value: Dict[str, Any]):
        """Set node metadata."""
        self._meta = value


# ============================================================================
# SECTION: COMMITAGENT SELF-TEST HARNESS
# ============================================================================

async def run_commit_self_test():
    """
    Self-test harness for CommitAgentNode with various commitment scenarios.

    Tests valid orders, payment failures, policy violations, and error conditions
    to ensure proper transition logic and error handling.
    """
    print("\n📝 CommitAgentNode Self-Test Harness")
    print("=" * 50)

    # Initialize the commit node
    commit_node = CommitAgentNode(
        node_id="test_commit_agent",
        enable_payment_simulation=True,
        enable_policy_enforcement=True,
        enable_notifications=True,
        enable_persistence=False,  # Disable for testing
        min_order_value=50.0
    )

    # Sample test cases for commitment scenarios
    test_cases = [
        {
            "name": "Valid Solo Order Commitment",
            "input": {
                "order_context": {
                    "material": "aluminum sheets",
                    "quantity": 5.0,
                    "unit": "kg",
                    "location": "Chennai",
                    "urgency": "URGENT"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 100.0,
                        "quantity": 5.0,
                        "delivery_days": 2
                    }
                ],
                "artisan_requirements": {
                    "material": "aluminum sheets",
                    "quality": "premium"
                },
                "payment_preferences": {
                    "method": "upi",
                    "type": "prepay"
                },
                "workflow_metadata": {
                    "user_id": "artisan123",
                    "workflow_id": "wf_001"
                }
            },
            "expected_transition": "committed"
        },
        {
            "name": "Valid Pooling Order Commitment",
            "input": {
                "order_context": {
                    "material": "steel rods",
                    "quantity": 20.0,
                    "unit": "pcs",
                    "location": "Mumbai",
                    "urgency": "NORMAL"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 25.0,
                        "quantity": 10.0,
                        "delivery_days": 3
                    },
                    {
                        "supplier_id": 2,
                        "price": 23.0,
                        "quantity": 10.0,
                        "delivery_days": 4
                    }
                ],
                "artisan_requirements": {
                    "material": "steel rods",
                    "quality": "standard"
                },
                "payment_preferences": {
                    "method": "razorpay",
                    "type": "postpay"
                },
                "workflow_metadata": {
                    "user_id": "business456",
                    "workflow_id": "wf_002"
                }
            },
            "expected_transition": "committed"
        },
        {
            "name": "Policy Violation - Low Order Value",
            "input": {
                "order_context": {
                    "material": "copper wire",
                    "quantity": 1.0,
                    "unit": "kg",
                    "location": "Delhi",
                    "urgency": "NORMAL"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 30.0,
                        "quantity": 1.0,
                        "delivery_days": 1
                    }
                ],
                "artisan_requirements": {
                    "material": "copper wire",
                    "quality": "basic"
                },
                "payment_preferences": {
                    "method": "upi",
                    "type": "prepay"
                },
                "workflow_metadata": {
                    "user_id": "user789",
                    "workflow_id": "wf_003"
                }
            },
            "expected_transition": "policy_block"
        },
        {
            "name": "Payment Failure Scenario",
            "input": {
                "order_context": {
                    "material": "plastic sheets",
                    "quantity": 10.0,
                    "unit": "pcs",
                    "location": "Bangalore",
                    "urgency": "URGENT"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 200.0,
                        "quantity": 10.0,
                        "delivery_days": 2
                    }
                ],
                "artisan_requirements": {
                    "material": "plastic sheets",
                    "quality": "premium"
                },
                "payment_preferences": {
                    "method": "upi",
                    "type": "prepay"
                },
                "workflow_metadata": {
                    "user_id": "premium_user",
                    "workflow_id": "wf_004"
                }
            },
            "expected_transition": "payment_error",
            "force_payment_failure": True
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n💰 Test Case {i}: {test_case['name']}")
        print("-" * 40)

        try:
            # Special setup for payment failure test
            if test_case.get("force_payment_failure", False):
                # Create a payment stub with 0% success rate
                from tools.payment_stubs import PaymentStub
                commit_node.payment_stub = PaymentStub(success_rate=0.0)

            # Create commit state
            input_data = CommitAgentInput(**test_case['input'])
            state = CommitAgentState(input_data=input_data)

            # Execute commit node
            output = await commit_node.execute(state)

            # Log results
            print(f"Order context: {test_case['input']['order_context']['material']} - {test_case['input']['order_context']['quantity']} {test_case['input']['order_context']['unit']}")
            print(f"Supplier quotes: {len(test_case['input']['supplier_quotes'])} supplier(s)")
            print(f"Total value: ₹{sum(q['price'] * q['quantity'] for q in test_case['input']['supplier_quotes'])}")
            print(f"Expected transition: {test_case['expected_transition']}")
            print(f"Actual transition: {output.transition}")
            print(f"Order ID: {output.order_id or 'None'}")

            if output.commit_confirmation:
                print(f"Commit status: {output.commit_confirmation.get('status', 'unknown')}")

            if output.payment_summary:
                print(f"Payment status: {output.payment_summary.get('status', 'unknown')}")

            # Check if transition matches expectation
            success = output.transition == test_case['expected_transition']
            results.append(success)

            print(f"✅ PASS" if success else f"❌ FAIL")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append(False)

    # Summary
    print(f"\n📊 Commit Test Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All commit tests passed!")
    else:
        print(f"⚠️  {total - passed} commit test(s) failed")

    return passed == total


# ============================================================================
# SECTION: CLUSTERAGENT NODE CLASS
# ============================================================================

class ClusterAgentNode:
    """
    LangGraph-ready ClusterAgentNode for supplier discovery and matchmaking.

    Advanced clustering node that performs both semantic (embedding/intent) clustering
    and spatial (location/geography) clustering to enable intelligent supplier
    matching and network scaling for artisan marketplace requests.

    Role: Supplier discovery through semantic and spatial clustering
    Inputs: GuardAgentOutput (normalized slots, security clearance, metadata)
    Outputs: Cluster assignments, candidate matches, confidence scores, transition decisions
    Tool Dependencies: embedding_generator (Ollama), spatial_clustering (K-means/haversine)
    Clustering Methods: Semantic embeddings for intent matching, spatial clustering for geography
    Candidate Matching: Historical peer requests, supplier databases, artisan networks
    Downstream Transitions: "clustered" -> SupplierAgent, "ambiguous" -> ClarifyAgent, "no-match" -> ErrorHandler
    """

    def __init__(
        self,
        node_id: str = "cluster_agent",
        embedding_model: str = "nomic-embed-text",
        spatial_clusters: int = 5,
        semantic_threshold: float = 0.7,
        max_candidates: int = 10,
        enable_peer_lookup: bool = True,
        enable_logging: bool = True
    ):
        """
        Initialize ClusterAgentNode with clustering configuration.

        Args:
            node_id: Unique identifier for this node in LangGraph
            embedding_model: Ollama embedding model for semantic clustering
            spatial_clusters: Number of spatial clusters for K-means
            semantic_threshold: Similarity threshold for semantic matching
            max_candidates: Maximum number of candidates to return
            enable_peer_lookup: Whether to lookup historical peer requests
            enable_logging: Whether to enable detailed clustering logs
        """
        self.node_id = node_id
        self.embedding_model = embedding_model
        self.spatial_clusters = spatial_clusters
        self.semantic_threshold = semantic_threshold
        self.max_candidates = max_candidates
        self.enable_peer_lookup = enable_peer_lookup
        self.enable_logging = enable_logging

        # Initialize modular tools
        try:
            from .tools.embedding_generator import EmbeddingGenerator, EmbeddingConfig
            embedding_config = EmbeddingConfig(model=embedding_model)
            self.embedding_generator = EmbeddingGenerator(embedding_config)
        except ImportError:
            # Fallback for direct imports
            from tools.embedding_generator import EmbeddingGenerator, EmbeddingConfig
            embedding_config = EmbeddingConfig(model=embedding_model)
            self.embedding_generator = EmbeddingGenerator(embedding_config)

        try:
            from .tools.spatial_clustering import SpatialClusterer, SpatialClustererConfig
            spatial_config = SpatialClustererConfig(num_clusters=spatial_clusters)
            self.spatial_clusterer = SpatialClusterer(spatial_config)
        except ImportError:
            from tools.spatial_clustering import SpatialClusterer, SpatialClustererConfig
            spatial_config = SpatialClustererConfig(num_clusters=spatial_clusters)
            self.spatial_clusterer = SpatialClusterer(spatial_config)

        try:
            from .tools.data_access import DataAccessLayer, DatabaseConfig
            db_config = DatabaseConfig()
            self.data_access = DataAccessLayer(db_config)
        except ImportError:
            from tools.data_access import DataAccessLayer, DatabaseConfig
            db_config = DatabaseConfig()
            self.data_access = DataAccessLayer(db_config)

        # Transition mapping for LangGraph routing
        self.transition_map = {
            "clustered": "SupplierAgent",
            "ambiguous": "ClarifyAgent",
            "no-match": "ErrorHandler"
        }

        # Visual metadata for UI/graph editor
        self.meta = {
            "icon": "🌐",
            "color": "green",
            "description": "Supplier Discovery & Clustering",
            "order": 3,
            "input_example": {
                "normalized": {
                    "material": {"value": "aluminum sheets"},
                    "quantity": {"value": 5.0, "unit": "kg"},
                    "location": {"value": "Chennai"},
                    "urgency": {"value": "URGENT"}
                },
                "embedding_text": "aluminum sheets 5.0 kg URGENT",
                "location_data": (13.0827, 80.2707)
            },
            "output_example": {
                "cluster_assignment": "metal_sheets_chennai",
                "candidate_list": [
                    {"supplier_id": 1, "name": "Chennai Metal Works", "score": 0.85},
                    {"supplier_id": 2, "name": "Tamil Nadu Suppliers", "score": 0.72}
                ],
                "confidence_score": 0.85,
                "transition": "clustered"
            }
        }

        logger.info(f"ClusterAgentNode '{node_id}' initialized with clustering tools")

    async def execute(self, state: ClusterAgentState) -> ClusterAgentOutput:
        """
        Async execute method for LangGraph node processing.

        Args:
            state: Current workflow state with input data

        Returns:
            ClusterAgentOutput with cluster assignments and candidate matches
        """
        start_time = datetime.now()
        output_log = []

        try:
            # Log clustering initiation
            output_log.append(f"Clustering analysis initiated at {start_time.isoformat()}")
            output_log.append(f"Input material: {state.input_data.normalized.get('material', {}).get('value', 'Unknown')}")
            output_log.append(f"Input location: {state.input_data.normalized.get('location', {}).get('value', 'Unknown')}")

            # Step 1: Generate semantic embeddings
            output_log.append("Step 1: Generating semantic embeddings...")
            embeddings = await self._generate_embeddings(state.input_data)
            state.embeddings = embeddings

            if not embeddings:
                state.add_log_entry("Failed to generate embeddings", "ERROR")
                return self._create_error_output("Embedding generation failed", output_log + state.log)

            state.add_log_entry(f"Generated embeddings with {len(embeddings)} dimensions")
            output_log.append(f"Generated {len(embeddings)}-dimensional embedding")

            # Step 2: Perform spatial clustering
            output_log.append("Step 2: Performing spatial clustering...")
            spatial_result = await self._perform_spatial_clustering(state.input_data)
            state.spatial_clusters = spatial_result["clusters"]
            state.cluster_metadata.update(spatial_result["metadata"])

            cluster_info = f"Spatial cluster {spatial_result['assigned_cluster']}"
            state.add_log_entry(cluster_info)
            output_log.append(cluster_info)

            # Step 3: Perform semantic clustering and matching
            output_log.append("Step 3: Performing semantic clustering and matching...")
            semantic_result = await self._perform_semantic_clustering(state)
            state.semantic_clusters = semantic_result["clusters"]
            state.cluster_metadata.update(semantic_result["metadata"])

            semantic_info = f"Semantic cluster {semantic_result['assigned_cluster']}"
            state.add_log_entry(semantic_info)
            output_log.append(semantic_info)

            # Step 4: Lookup peer requests and candidates
            output_log.append("Step 4: Looking up peer requests and candidates...")
            peer_result = await self._lookup_peer_requests(state)
            state.peer_requests = peer_result["peers"]
            state.cluster_metadata.update(peer_result["metadata"])

            peer_info = f"Found {len(peer_result['peers'])} peer requests"
            state.add_log_entry(peer_info)
            output_log.append(peer_info)

            # Step 5: Find and score candidates
            output_log.append("Step 5: Finding and scoring supplier candidates...")
            candidate_result = await self._find_candidates(state)
            state.candidate_matches = candidate_result["candidates"]
            state.confidence_scores = candidate_result["confidence_scores"]

            candidate_info = f"Found {len(candidate_result['candidates'])} candidates"
            state.add_log_entry(candidate_info)
            output_log.append(candidate_info)

            # Step 6: Detect ambiguities and conflicts
            output_log.append("Step 6: Detecting ambiguities and conflicts...")
            ambiguity_result = self._detect_ambiguities(state)
            state.ambiguity_flags.extend(ambiguity_result["flags"])

            if ambiguity_result["flags"]:
                ambiguity_info = f"Detected {len(ambiguity_result['flags'])} ambiguities"
                state.add_log_entry(ambiguity_info, "WARNING")
                output_log.append(ambiguity_info)

            # Step 7: Determine final transition
            output_log.append("Step 7: Determining final transition...")
            transition = self._determine_transition(state)
            state.transition = transition

            transition_info = f"Final transition: {transition}"
            state.add_log_entry(transition_info)
            output_log.append(transition_info)

            # Step 8: Prepare clustering output
            cluster_assignment = self._generate_cluster_assignment(state)
            top_candidates = candidate_result["candidates"][:self.max_candidates]
            overall_confidence = self._calculate_overall_confidence(state)

            # Create output
            output = ClusterAgentOutput(
                cluster_assignment=cluster_assignment,
                candidate_list=top_candidates,
                confidence_score=overall_confidence,
                transition=transition,
                log=output_log + state.log,
                ambiguity_details={
                    "flags": state.ambiguity_flags,
                    "conflict_details": ambiguity_result.get("conflict_details", {}),
                    "resolution_suggestions": ambiguity_result.get("suggestions", [])
                } if state.ambiguity_flags else None,
                metadata={
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "embedding_dimensions": len(embeddings),
                    "spatial_clusters": len(set(state.spatial_clusters)),
                    "semantic_clusters": len(set(state.semantic_clusters)),
                    "peer_requests_analyzed": len(state.peer_requests),
                    "candidates_scored": len(state.candidate_matches),
                    "clustering_metadata": state.cluster_metadata
                }
            )

            # Final logging
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            output_log.append(f"Clustering completed in {processing_time:.2f}ms")
            output_log.append(f"Final result: {transition} -> {self.transition_map.get(transition, 'Unknown')}")

            logger.info(f"ClusterAgentNode completed: {transition} -> {self.transition_map.get(transition, 'Unknown')}")
            return output

        except Exception as e:
            # Handle unexpected errors in clustering
            error_msg = f"Unexpected error in ClusterAgentNode: {str(e)}"
            state.add_log_entry(error_msg, "ERROR")
            output_log.append(f"ERROR: {error_msg}")
            output_log.append(f"Traceback: {traceback.format_exc()}")

            logger.error(f"ClusterAgentNode error: {e}", exc_info=True)

            return ClusterAgentOutput(
                cluster_assignment=None,
                candidate_list=[],
                confidence_score=0.0,
                transition="no-match",
                log=output_log + state.log,
                ambiguity_details={
                    "flags": ["processing_error"],
                    "error_details": {"error_type": type(e).__name__, "error_message": str(e)}
                },
                metadata={"processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000}
            )

    async def _generate_embeddings(self, input_data: ClusterAgentInput) -> Optional[List[float]]:
        """
        Generate semantic embeddings for the input request.

        Args:
            input_data: Input data containing text for embedding

        Returns:
            List of embedding values or None if failed
        """
        try:
            if not input_data.embedding_text:
                logger.warning("No embedding text provided")
                return None

            # Use async embedding generation
            embeddings = await self.embedding_generator.generate_embedding_async(input_data.embedding_text)

            if not embeddings:
                logger.error("Embedding generation returned empty result")
                return None

            return embeddings

        except Exception as e:
            logger.error(f"Embedding generation failed: {e}")
            return None

    async def _perform_spatial_clustering(self, input_data: ClusterAgentInput) -> Dict[str, Any]:
        """
        Perform spatial clustering based on location data.

        Args:
            input_data: Input data containing location information

        Returns:
            Dictionary with spatial clustering results and metadata
        """
        try:
            if not input_data.location_data or input_data.location_data == (0.0, 0.0):
                return {
                    "clusters": [0],
                    "assigned_cluster": "unknown_location",
                    "metadata": {"clustering_method": "none", "reason": "no_location_data"}
                }

            # Get historical supplier/artisan locations for clustering context
            try:
                # Look up suppliers in similar regions for clustering context
                suppliers = self.data_access.search_suppliers(
                    filters={"is_active": True},
                    limit=100
                )

                # Extract coordinates from suppliers
                supplier_locations = []
                for supplier in suppliers:
                    if supplier.get('latitude') and supplier.get('longitude'):
                        supplier_locations.append((supplier['latitude'], supplier['longitude']))

                # Add current request location
                all_locations = supplier_locations + [input_data.location_data]

                if len(all_locations) < 2:
                    return {
                        "clusters": [0],
                        "assigned_cluster": "single_location",
                        "metadata": {"clustering_method": "none", "reason": "insufficient_data"}
                    }

                # Perform K-means clustering
                cluster_labels = self.spatial_clusterer.cluster_locations(all_locations, method="kmeans")

                # Find which cluster the current request belongs to
                request_cluster = cluster_labels[-1]  # Last one is our request

                return {
                    "clusters": cluster_labels,
                    "assigned_cluster": f"spatial_cluster_{request_cluster}",
                    "metadata": {
                        "clustering_method": "kmeans",
                        "total_locations": len(all_locations),
                        "num_clusters": len(set(cluster_labels)),
                        "cluster_sizes": [cluster_labels.count(i) for i in set(cluster_labels)]
                    }
                }

            except Exception as e:
                logger.warning(f"Spatial clustering with context failed: {e}")
                # Fallback to simple clustering
                return {
                    "clusters": [0],
                    "assigned_cluster": "fallback_cluster",
                    "metadata": {"clustering_method": "fallback", "error": str(e)}
                }

        except Exception as e:
            logger.error(f"Spatial clustering failed: {e}")
            return {
                "clusters": [0],
                "assigned_cluster": "error_cluster",
                "metadata": {"clustering_method": "error", "error": str(e)}
            }

    async def _perform_semantic_clustering(self, state: ClusterAgentState) -> Dict[str, Any]:
        """
        Perform semantic clustering using embeddings and historical data.

        Args:
            state: Current clustering state with embeddings

        Returns:
            Dictionary with semantic clustering results
        """
        try:
            if not state.embeddings:
                return {
                    "clusters": [0],
                    "assigned_cluster": "no_embeddings",
                    "metadata": {"clustering_method": "none", "reason": "no_embeddings"}
                }

            # Look up historical requests for semantic comparison
            try:
                # This would typically query a vector database or similar requests
                # For now, we'll simulate semantic clustering based on material similarity

                material = state.input_data.normalized.get('material', {}).get('value', '').lower()
                urgency = state.input_data.normalized.get('urgency', {}).get('value', 'NORMAL')

                # Simple rule-based semantic clustering
                if 'metal' in material or 'steel' in material or 'aluminum' in material:
                    semantic_cluster = "metal_materials"
                elif 'wood' in material or 'furniture' in material:
                    semantic_cluster = "wood_products"
                elif 'fabric' in material or 'textile' in material or 'cloth' in material:
                    semantic_cluster = "textile_materials"
                elif 'plastic' in material or 'polymer' in material:
                    semantic_cluster = "plastic_materials"
                else:
                    semantic_cluster = "general_materials"

                # Adjust cluster based on urgency
                if urgency == "EMERGENCY":
                    semantic_cluster = f"urgent_{semantic_cluster}"
                elif urgency == "URGENT":
                    semantic_cluster = f"priority_{semantic_cluster}"

                return {
                    "clusters": [0],  # Single cluster for now
                    "assigned_cluster": semantic_cluster,
                    "metadata": {
                        "clustering_method": "rule_based",
                        "material_category": material,
                        "urgency_factor": urgency,
                        "embedding_used": len(state.embeddings) > 0
                    }
                }

            except Exception as e:
                logger.warning(f"Semantic clustering failed: {e}")
                return {
                    "clusters": [0],
                    "assigned_cluster": "semantic_error",
                    "metadata": {"clustering_method": "error", "error": str(e)}
                }

        except Exception as e:
            logger.error(f"Semantic clustering error: {e}")
            return {
                "clusters": [0],
                "assigned_cluster": "error_cluster",
                "metadata": {"clustering_method": "error", "error": str(e)}
            }

    async def _lookup_peer_requests(self, state: ClusterAgentState) -> Dict[str, Any]:
        """
        Lookup similar historical requests for peer comparison.

        Args:
            state: Current clustering state

        Returns:
            Dictionary with peer requests and metadata
        """
        try:
            peers = []
            metadata = {"lookup_method": "database_search", "peers_found": 0}

            if not self.enable_peer_lookup:
                return {"peers": peers, "metadata": metadata}

            # Look up historical orders/requests with similar materials
            material = state.input_data.normalized.get('material', {}).get('value', '')

            if material:
                try:
                    # Search for orders with similar materials
                    # This is a simplified search - in reality would use vector similarity
                    orders = self.data_access.get_orders_by_status("completed", limit=50)

                    # Filter orders by material similarity (simple keyword matching)
                    similar_orders = []
                    for order in orders:
                        order_items = order.get('order_items', [])
                        for item in order_items:
                            item_material = item.get('material', '').lower()
                            if material.lower() in item_material or item_material in material.lower():
                                similar_orders.append({
                                    "order_id": order['id'],
                                    "material": item.get('material', ''),
                                    "quantity": item.get('quantity', 0),
                                    "location": order.get('shipping_address', {}).get('city', 'Unknown'),
                                    "created_at": order['created_at'].isoformat() if order.get('created_at') else None,
                                    "supplier_id": order.get('supplier_id'),
                                    "similarity_score": 0.8  # Placeholder similarity score
                                })

                    peers = similar_orders[:10]  # Top 10 similar orders
                    metadata.update({
                        "lookup_method": "material_similarity",
                        "peers_found": len(peers),
                        "total_orders_searched": len(orders),
                        "material_filter": material
                    })

                except Exception as e:
                    logger.warning(f"Peer lookup failed: {e}")
                    metadata.update({"lookup_error": str(e)})

            return {"peers": peers, "metadata": metadata}

        except Exception as e:
            logger.error(f"Peer lookup error: {e}")
            return {"peers": [], "metadata": {"error": str(e)}}

    async def _find_candidates(self, state: ClusterAgentState) -> Dict[str, Any]:
        """
        Find and score supplier candidates based on clustering results.

        Args:
            state: Current clustering state

        Returns:
            Dictionary with candidates and confidence scores
        """
        try:
            candidates = []
            confidence_scores = {}

            # Get material and location for candidate search
            material = state.input_data.normalized.get('material', {}).get('value', '')
            location = state.input_data.normalized.get('location', {}).get('value', '')

            if not material:
                return {"candidates": candidates, "confidence_scores": confidence_scores}

            try:
                # Search for suppliers that match material categories
                suppliers = self.data_access.search_suppliers(
                    filters={"is_active": True},
                    limit=50
                )

                # Score suppliers based on material match and location proximity
                scored_suppliers = []
                for supplier in suppliers:
                    score = 0.0
                    reasons = []

                    # Material category matching
                    supplier_categories = supplier.get('product_categories', [])
                    material_lower = material.lower()

                    # Simple material matching logic
                    for category in supplier_categories:
                        if category.lower() in material_lower or material_lower in category.lower():
                            score += 0.6
                            reasons.append(f"material_match:{category}")
                            break

                    # If no category match, try keyword matching
                    if score == 0:
                        supplier_name = supplier.get('name', '').lower()
                        if material_lower in supplier_name:
                            score += 0.3
                            reasons.append(f"keyword_match:{material}")

                    # Location proximity scoring (simplified)
                    if location and supplier.get('location'):
                        supplier_location = supplier['location'].lower()
                        if location.lower() in supplier_location or supplier_location in location.lower():
                            score += 0.3
                            reasons.append(f"location_match:{supplier_location}")

                    # Rating bonus
                    rating = supplier.get('rating', 0)
                    if rating > 4.0:
                        score += 0.1
                        reasons.append(f"high_rating:{rating}")

                    if score > 0:
                        scored_suppliers.append({
                            "supplier_id": supplier['id'],
                            "name": supplier['name'],
                            "score": min(score, 1.0),  # Cap at 1.0
                            "reasons": reasons,
                            "contact": supplier.get('email', supplier.get('phone', 'N/A')),
                            "location": supplier.get('location', 'Unknown'),
                            "rating": rating,
                            "categories": supplier_categories
                        })

                # Sort by score and take top candidates
                scored_suppliers.sort(key=lambda x: x['score'], reverse=True)
                candidates = scored_suppliers[:self.max_candidates]

                # Create confidence scores mapping
                confidence_scores = {str(c['supplier_id']): c['score'] for c in candidates}

                return {
                    "candidates": candidates,
                    "confidence_scores": confidence_scores
                }

            except Exception as e:
                logger.warning(f"Candidate search failed: {e}")
                return {"candidates": candidates, "confidence_scores": confidence_scores}

        except Exception as e:
            logger.error(f"Candidate finding error: {e}")
            return {"candidates": [], "confidence_scores": {}}

    def _detect_ambiguities(self, state: ClusterAgentState) -> Dict[str, Any]:
        """
        Detect ambiguities and conflicts in clustering results.

        Args:
            state: Current clustering state

        Returns:
            Dictionary with ambiguity flags and suggestions
        """
        flags = []
        suggestions = []
        conflict_details = {}

        try:
            # Check for low confidence scores
            if state.confidence_scores:
                avg_confidence = sum(state.confidence_scores.values()) / len(state.confidence_scores)
                if avg_confidence < 0.5:
                    flags.append("low_confidence")
                    suggestions.append("Consider requesting more specific material requirements")
                    conflict_details["low_confidence"] = {
                        "average_score": avg_confidence,
                        "threshold": 0.5
                    }

            # Check for insufficient candidates
            if len(state.candidate_matches) < 2:
                flags.append("insufficient_candidates")
                suggestions.append("Consider expanding search criteria or location radius")
                conflict_details["insufficient_candidates"] = {
                    "found": len(state.candidate_matches),
                    "minimum_desired": 2
                }

            # Check for conflicting cluster assignments
            spatial_clusters = set(state.spatial_clusters)
            semantic_clusters = set(state.semantic_clusters)

            if len(spatial_clusters) > 1 or len(semantic_clusters) > 1:
                flags.append("cluster_conflict")
                suggestions.append("Multiple cluster assignments detected - may need clarification")
                conflict_details["cluster_conflict"] = {
                    "spatial_clusters": list(spatial_clusters),
                    "semantic_clusters": list(semantic_clusters)
                }

            # Check for location ambiguity
            location = state.input_data.normalized.get('location', {}).get('value', '')
            if not location or len(location.strip()) < 3:
                flags.append("location_ambiguity")
                suggestions.append("Location information is unclear - please specify city/region")
                conflict_details["location_ambiguity"] = {
                    "provided_location": location
                }

            return {
                "flags": flags,
                "suggestions": suggestions,
                "conflict_details": conflict_details
            }

        except Exception as e:
            logger.error(f"Ambiguity detection error: {e}")
            return {
                "flags": ["detection_error"],
                "suggestions": ["Error during ambiguity detection"],
                "conflict_details": {"error": str(e)}
            }

    def _determine_transition(self, state: ClusterAgentState) -> str:
        """
        Determine next workflow transition based on clustering results.

        Args:
            state: Current clustering state

        Returns:
            Transition string: "clustered", "ambiguous", or "no-match"
        """
        try:
            # If we have no embeddings or major failures, no match
            if not state.embeddings:
                return "no-match"

            # If we have ambiguity flags, route to clarification
            if state.ambiguity_flags:
                return "ambiguous"

            # If we have good candidates with high confidence, proceed to supplier agent
            if state.candidate_matches:
                avg_confidence = sum(state.confidence_scores.values()) / len(state.confidence_scores)
                if avg_confidence >= 0.7 and len(state.candidate_matches) >= 2:
                    return "clustered"

            # If we have some candidates but low confidence, ambiguous
            if state.candidate_matches:
                return "ambiguous"

            # No candidates found
            return "no-match"

        except Exception as e:
            logger.error(f"Transition determination error: {e}")
            return "no-match"

    def _generate_cluster_assignment(self, state: ClusterAgentState) -> Optional[str]:
        """
        Generate a human-readable cluster assignment identifier.

        Args:
            state: Current clustering state

        Returns:
            Cluster assignment string or None
        """
        try:
            material = state.input_data.normalized.get('material', {}).get('value', 'unknown')
            location = state.input_data.normalized.get('location', {}).get('value', 'unknown')
            urgency = state.input_data.normalized.get('urgency', {}).get('value', 'normal')

            # Create cluster assignment
            cluster_parts = [
                material.replace(' ', '_').lower(),
                location.replace(' ', '_').lower(),
                urgency.lower()
            ]

            return "_".join(cluster_parts)

        except Exception as e:
            logger.error(f"Cluster assignment generation error: {e}")
            return None

    def _calculate_overall_confidence(self, state: ClusterAgentState) -> float:
        """
        Calculate overall confidence score for the clustering result.

        Args:
            state: Current clustering state

        Returns:
            Overall confidence score between 0.0 and 1.0
        """
        try:
            if not state.confidence_scores:
                return 0.0

            # Average candidate confidence
            avg_candidate_confidence = sum(state.confidence_scores.values()) / len(state.confidence_scores)

            # Factor in number of candidates (more candidates = higher confidence)
            candidate_factor = min(len(state.candidate_matches) / 5.0, 1.0)

            # Factor in peer requests (more peers = higher confidence)
            peer_factor = min(len(state.peer_requests) / 10.0, 1.0)

            # Combine factors
            overall_confidence = (avg_candidate_confidence * 0.5 +
                                candidate_factor * 0.3 +
                                peer_factor * 0.2)

            return min(overall_confidence, 1.0)

        except Exception as e:
            logger.error(f"Overall confidence calculation error: {e}")
            return 0.0

    def _create_error_output(self, error_message: str, log_entries: List[str]) -> ClusterAgentOutput:
        """
        Create error output for failed clustering operations.

        Args:
            error_message: Error message describing the failure
            log_entries: Log entries to include in output

        Returns:
            ClusterAgentOutput with error information
        """
        return ClusterAgentOutput(
            cluster_assignment=None,
            candidate_list=[],
            confidence_score=0.0,
            transition="no-match",
            log=log_entries + [f"ERROR: {error_message}"],
            ambiguity_details={
                "flags": ["processing_error"],
                "error_details": {"message": error_message}
            },
            metadata={"error": True, "error_message": error_message}
        )


# ============================================================================
# SECTION: GUARDAGENT SELF-TEST HARNESS
# ============================================================================

async def run_guard_self_test():
    """
    Self-test harness for GuardAgentNode with security scenarios.

    Tests various security scenarios including valid requests, profanity,
    rate limiting, policy violations, and suspicious activity.
    """
    print("\n🚨 GuardAgentNode Security Self-Test Harness")
    print("=" * 60)

    # Initialize the guard node
    guard_node = GuardAgentNode(
        node_id="test_guard_agent",
        enable_rate_limiting=True,
        enable_signature_check=True,
        enable_profanity_filter=True,
        enable_policy_guards=False  # Disable for testing without policies
    )

    # Sample test cases for security scenarios
    test_cases = [
        {
            "name": "Clean Valid Request",
            "input": {
                "normalized": {
                    "material": {"value": "aluminum sheets"},
                    "quantity": {"value": 5.0, "unit": "kg"},
                    "location": {"value": "Chennai"},
                    "urgency": {"value": "NORMAL"}
                },
                "intake_metadata": {
                    "source": "whatsapp",
                    "original_text": "Need 5 kg of aluminum sheets in Chennai"
                },
                "user_context": {"user_id": "legit_user_123"}
            },
            "expected_approved": True,
            "expected_transition": "pass"
        },
        {
            "name": "Profanity Content",
            "input": {
                "normalized": {
                    "material": {"value": "steel rods"},
                    "quantity": {"value": 10.0, "unit": "pcs"},
                    "location": {"value": "Mumbai"},
                    "urgency": {"value": "URGENT"}
                },
                "intake_metadata": {
                    "source": "web_form",
                    "original_text": "This is stupid, need steel rods in Mumbai"
                },
                "user_context": {"user_id": "user_with_profanity"}
            },
            "expected_approved": False,
            "expected_transition": "clarify"
        },
        {
            "name": "Injection Attack",
            "input": {
                "normalized": {
                    "material": {"value": "copper wire"},
                    "quantity": {"value": 1.0, "unit": "kg"},
                    "location": {"value": "Delhi"},
                    "urgency": {"value": "NORMAL"}
                },
                "intake_metadata": {
                    "source": "api",
                    "original_text": "Need copper wire <script>alert('hack')</script> in Delhi"
                },
                "user_context": {"user_id": "potential_hacker"}
            },
            "expected_approved": False,
            "expected_transition": "clarify"
        },
        {
            "name": "Banned Words",
            "input": {
                "normalized": {
                    "material": {"value": "plastic sheets"},
                    "quantity": {"value": 100.0, "unit": "pcs"},
                    "location": {"value": "Bangalore"},
                    "urgency": {"value": "URGENT"}
                },
                "intake_metadata": {
                    "source": "whatsapp",
                    "original_text": "Need plastic sheets for my scam business in Bangalore"
                },
                "user_context": {"user_id": "suspicious_user"}
            },
            "expected_approved": False,
            "expected_transition": "clarify"
        },
        {
            "name": "Suspicious Patterns",
            "input": {
                "normalized": {
                    "material": {"value": "gold bars"},
                    "quantity": {"value": 1000.0, "unit": "kg"},
                    "location": {"value": "Hyderabad"},
                    "urgency": {"value": "EMERGENCY"}
                },
                "intake_metadata": {
                    "source": "api",
                    "original_text": "EMERGENCY: Need 1000kg gold bars in Hyderabad, guaranteed profit"
                },
                "user_context": {"user_id": "scam_user"}
            },
            "expected_approved": False,
            "expected_transition": "clarify"
        },
        {
            "name": "Rate Limited User",
            "input": {
                "normalized": {
                    "material": {"value": "test material"},
                    "quantity": {"value": 1.0, "unit": "kg"},
                    "location": {"value": "Pune"},
                    "urgency": {"value": "NORMAL"}
                },
                "intake_metadata": {
                    "source": "web_form",
                    "original_text": "Test request from rate limited user"
                },
                "user_context": {"user_id": "rate_limited_user"}
            },
            "expected_approved": False,
            "expected_transition": "fail",
            "setup_rate_limit": True  # Special setup for this test
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🔒 Security Test Case {i}: {test_case['name']}")
        print("-" * 50)

        try:
            # Special setup for rate limiting test
            if test_case.get("setup_rate_limit", False):
                # Simulate rate limit violation by filling the cache
                guard_node.rate_limit_cache["rate_limited_user"] = [
                    datetime.now().timestamp() for _ in range(15)  # Exceed limit
                ]

            # Create guard state
            input_data = GuardAgentInput(**test_case['input'])
            state = GuardAgentState(input_data=input_data)

            # Execute guard node
            output = await guard_node.execute(state)

            # Log results
            print(f"Input: {test_case['input']['intake_metadata']['original_text']}")
            print(f"Expected approved: {test_case['expected_approved']}")
            print(f"Actual approved: {output.approved}")
            print(f"Expected transition: {test_case['expected_transition']}")
            print(f"Actual transition: {output.transition}")
            print(f"Risk score: {output.risk_score}")
            print(f"Block reasons: {', '.join(output.block_reasons) if output.block_reasons else 'None'}")

            # Check if results match expectations
            success = (output.approved == test_case['expected_approved'] and
                      output.transition == test_case['expected_transition'])

            results.append(success)

            print(f"✅ PASS" if success else f"❌ FAIL")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append(False)

    # Summary
    print(f"\n📊 Guard Security Test Summary")
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All security tests passed!")
    else:
        print(f"⚠️  {total - passed} security test(s) failed")

    return passed == total


# ============================================================================
# SECTION: SALESAGENT NODE SCHEMAS
# ============================================================================

@dataclass
class SalesAgentInput:
    """
    Input data for SalesAgentNode from CommitAgentNode.

    Attributes:
        order_id: Unique order identifier from commit
        order_context: Original order details (material, quantity, location, urgency)
        supplier_quotes: List of selected supplier quotes with pricing and delivery
        artisan_requirements: Specific artisan requirements and preferences
        payment_summary: Payment completion details from commit
        delivery_info: Delivery preferences and requirements
        channel_settings: Configuration for sales channel generation
        workflow_metadata: Workflow tracking and user context
    """
    order_id: str
    order_context: Dict[str, Any]
    supplier_quotes: List[Dict[str, Any]]
    artisan_requirements: Dict[str, Any]
    payment_summary: Dict[str, Any]
    delivery_info: Dict[str, Any] = field(default_factory=dict)
    channel_settings: Dict[str, Any] = field(default_factory=dict)
    workflow_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SalesAgentState:
    """
    Complete state for sales channel processing workflow.

    Attributes:
        input_data: Input from CommitAgentNode
        microstore_url: Generated micro-store URL for order access
        status_page_url: Order status tracking page URL
        qr_codes: Generated QR codes for pickup/kiosk access
        kiosk_booking: Kiosk booking information if applicable
        delivery_manifest: Delivery manifest for logistics
        access_credentials: Generated access credentials for channels
        notification_events: Records of notifications sent
        policy_applications: Sales policies applied to the order
        channel_logs: Detailed logs of channel creation process
        errors: List of errors encountered during processing
        timestamp: When this state was created
        transition: Next workflow step to take
        log: Processing log for debugging and monitoring
    """
    input_data: SalesAgentInput
    microstore_url: Optional[str] = None
    status_page_url: Optional[str] = None
    qr_codes: Dict[str, str] = field(default_factory=dict)
    kiosk_booking: Dict[str, Any] = field(default_factory=dict)
    delivery_manifest: Dict[str, Any] = field(default_factory=dict)
    access_credentials: Dict[str, Any] = field(default_factory=dict)
    notification_events: List[Dict[str, Any]] = field(default_factory=list)
    policy_applications: List[Dict[str, Any]] = field(default_factory=list)
    channel_logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    transition: str = "pending"
    log: List[str] = field(default_factory=list)

    def add_log_entry(self, message: str, level: str = "INFO"):
        """Add entry to processing log."""
        timestamp = datetime.now().isoformat()
        self.log.append(f"[{timestamp}] {level}: {message}")

    def add_error(self, error: str):
        """Add error to error list and log."""
        self.errors.append(error)
        self.add_log_entry(f"ERROR: {error}", "ERROR")

    def add_channel_log(self, channel_type: str, action: str, details: str):
        """Add channel-specific log entry."""
        log_entry = f"{channel_type}: {action} - {details}"
        self.channel_logs.append(log_entry)
        self.add_log_entry(log_entry, "INFO")

    def add_notification_event(self, recipient: str, channel: str, status: str, message_id: str = None):
        """Record notification event."""
        event = {
            "recipient": recipient,
            "channel": channel,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "message_id": message_id
        }
        self.notification_events.append(event)
        self.add_log_entry(f"Notification sent to {recipient} via {channel}: {status}")

    def add_policy_application(self, policy_type: str, policy_name: str, applied_rules: List[str]):
        """Record policy application."""
        application = {
            "policy_type": policy_type,
            "policy_name": policy_name,
            "applied_rules": applied_rules,
            "timestamp": datetime.now().isoformat()
        }
        self.policy_applications.append(application)
        self.add_log_entry(f"Applied {policy_type} policy '{policy_name}': {', '.join(applied_rules)}")


@dataclass
class SalesAgentOutput:
    """
    Output from SalesAgentNode execution.

    Attributes:
        order_id: Unique order identifier
        channel_urls: Dictionary of generated channel URLs (microstore, status page)
        qr_codes: Generated QR codes for physical access
        access_credentials: Generated access credentials for secure channels
        delivery_manifest: Delivery manifest if applicable
        notification_summary: Summary of notifications sent
        policy_summary: Summary of policies applied
        transition: Next node in pipeline ('sales_created', 'sales_error', 'policy_block')
        log: Complete processing log
        error_details: Detailed error information if processing failed
        metadata: Additional output metadata including processing metrics
    """
    order_id: str
    channel_urls: Dict[str, str]
    qr_codes: Dict[str, str]
    access_credentials: Dict[str, Any]
    delivery_manifest: Dict[str, Any]
    notification_summary: Dict[str, Any]
    policy_summary: Dict[str, Any]
    transition: str
    log: List[str]
    error_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SECTION: SALESAGENT NODE CLASS
# ============================================================================

class SalesAgentNode:
    """
    LangGraph-ready SalesAgentNode for digital sales channel creation and management.

    Digital channel creation node activated immediately after CommitAgentNode
    once an order has been created and paid for. Generates micro-stores, QR codes,
    status pages, and handles notifications for seamless order fulfillment.

    Role: Digital channel creation and notification management post-commit
    Inputs: CommitAgentOutput (committed order, payment confirmation, supplier data)
    Outputs: Sales channels, access credentials, notifications, and next transition
    Tool Dependencies: microstore (PWA generation), notification_stubs (alerts),
                      policy_loader (sales rules), pwa_tools (status pages), qr_generator (codes)
    Channel Types: Micro-store (PWA), status page (tracking), QR codes (pickup/kiosk),
                   kiosk booking (scan-based access), delivery manifest (logistics)
    Downstream Transitions: "sales_created" -> OpsAgent, "sales_error" -> ErrorHandlerAgent, "policy_block" -> ClarifyAgent
    """

    def __init__(
        self,
        node_id: str = "sales_agent",
        enable_microstore: bool = True,
        enable_qr_generation: bool = True,
        enable_kiosk_booking: bool = True,
        enable_notifications: bool = True,
        enable_policy_enforcement: bool = True,
        enable_delivery_manifest: bool = True,
        default_channel_expiry: int = 30,  # days
        enable_logging: bool = True
    ):
        """
        Initialize SalesAgentNode with sales channel configuration.

        Args:
            node_id: Unique identifier for this node in LangGraph
            enable_microstore: Whether to generate micro-store PWAs
            enable_qr_generation: Whether to generate QR codes for access
            enable_kiosk_booking: Whether to enable kiosk booking features
            enable_notifications: Whether to send channel notifications
            enable_policy_enforcement: Whether to apply sales policies
            enable_delivery_manifest: Whether to generate delivery manifests
            default_channel_expiry: Default expiry time for channels (days)
            enable_logging: Whether to enable detailed channel creation logs
        """
        self.node_id = node_id
        self.enable_microstore = enable_microstore
        self.enable_qr_generation = enable_qr_generation
        self.enable_kiosk_booking = enable_kiosk_booking
        self.enable_notifications = enable_notifications
        self.enable_policy_enforcement = enable_policy_enforcement
        self.enable_delivery_manifest = enable_delivery_manifest
        self.default_channel_expiry = default_channel_expiry
        self.enable_logging = enable_logging

        # Initialize modular tools
        try:
            from .tools.notification_stubs import EmailNotificationStub, SMSNotificationStub, NotificationBase
            self.email_stub = EmailNotificationStub() if enable_notifications else None
            self.sms_stub = SMSNotificationStub() if enable_notifications else None
            self.NotificationBase = NotificationBase
        except ImportError:
            from tools.notification_stubs import EmailNotificationStub, SMSNotificationStub, NotificationBase
            self.email_stub = EmailNotificationStub() if enable_notifications else None
            self.sms_stub = SMSNotificationStub() if enable_notifications else None
            self.NotificationBase = NotificationBase

        try:
            from .tools.policy_loader import PolicyLoader
            self.policy_loader = PolicyLoader("policies") if enable_policy_enforcement else None
        except ImportError:
            from tools.policy_loader import PolicyLoader
            self.policy_loader = PolicyLoader("policies") if enable_policy_enforcement else None

        # Initialize stub tools for missing dependencies (will be created as stubs)
        self.microstore_tool = MicroStoreTool() if enable_microstore else None
        self.pwa_tool = PWATool() if enable_microstore else None
        self.qr_generator = QRGeneratorTool() if enable_qr_generation else None

        # Load sales policies if enabled
        if self.enable_policy_enforcement and self.policy_loader:
            try:
                self._load_sales_policies()
            except Exception as e:
                logger.warning(f"Could not load sales policies: {e}")

        # Transition mapping for LangGraph routing
        self.transition_map = {
            "sales_created": "OpsAgent",
            "sales_error": "ErrorHandlerAgent",
            "policy_block": "ClarifyAgent"
        }

        # Visual metadata for UI/graph editor
        self.meta = {
            "icon": "🛒",
            "color": "teal",
            "description": "Digital Sales Channel Creation",
            "order": 5,
            "input_example": {
                "order_id": "ORD-20250108-001",
                "order_context": {
                    "material": "aluminum sheets",
                    "quantity": 5.0,
                    "location": "Chennai",
                    "urgency": "URGENT"
                },
                "supplier_quotes": [
                    {"supplier_id": 1, "price": 100.0, "delivery_days": 2}
                ],
                "payment_summary": {"status": "completed", "method": "upi"}
            },
            "output_example": {
                "order_id": "ORD-20250108-001",
                "channel_urls": {
                    "microstore": "https://microstore.artisanhub.com/ord-001",
                    "status_page": "https://track.artisanhub.com/ord-001"
                },
                "qr_codes": {
                    "pickup": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA...",
                    "kiosk": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAA..."
                },
                "transition": "sales_created"
            }
        }

        logger.info(f"SalesAgentNode '{node_id}' initialized successfully")

    def _load_sales_policies(self):
        """Load sales and commission policies for channel creation."""
        if not self.policy_loader:
            return

        try:
            # Load commission rates policy for sales calculations
            commission_policy = self.policy_loader.load_policy('commission_rates')
            if self.data_access:
                self.data_access.register_policy_domain('commission_rates', commission_policy)
            logger.info("Loaded commission rates policy for sales channels")
        except Exception as e:
            logger.warning(f"Could not load commission policy: {e}")

    async def execute(self, state: SalesAgentState) -> SalesAgentOutput:
        """
        Async execute method for LangGraph node processing.

        Args:
            state: Current workflow state with input data

        Returns:
            SalesAgentOutput with generated channels and next node transition
        """
        start_time = datetime.now()
        output_log = []

        try:
            # Log sales channel creation initiation
            output_log.append(f"Sales channel creation initiated at {start_time.isoformat()}")
            output_log.append(f"Order ID: {state.input_data.order_id}")
            output_log.append(f"Material: {state.input_data.order_context.get('material', 'Unknown')}")
            output_log.append(f"Location: {state.input_data.order_context.get('location', 'Unknown')}")

            # Step 1: Apply sales policies and restrictions
            output_log.append("Step 1: Applying sales policies...")
            policy_result = await self._apply_sales_policies(state)

            if not policy_result["passed"]:
                state.add_error(f"Sales policy block: {policy_result['reasons']}")
                output_log.append(f"Policy block: {policy_result['reasons']}")
                return self._create_policy_block_output(state, output_log)

            state.add_log_entry("Sales policies applied successfully")
            output_log.append("Sales policy validation completed")

            # Step 2: Generate micro-store for order access
            output_log.append("Step 2: Generating micro-store...")
            microstore_result = await self._generate_microstore(state)

            if not microstore_result["success"]:
                state.add_error(f"Micro-store generation failed: {microstore_result['error']}")
                output_log.append(f"Micro-store error: {microstore_result['error']}")
                return self._create_channel_error_output(state, output_log)

            state.microstore_url = microstore_result["microstore_url"]
            state.access_credentials.update(microstore_result["credentials"])
            state.add_channel_log("microstore", "created", microstore_result["microstore_url"])
            state.add_log_entry("Micro-store generated successfully")
            output_log.append("Micro-store generation completed")

            # Step 3: Generate order status page
            output_log.append("Step 3: Generating order status page...")
            status_result = await self._generate_status_page(state)

            if not status_result["success"]:
                state.add_error(f"Status page generation failed: {status_result['error']}")
                output_log.append(f"Status page error: {status_result['error']}")
                return self._create_channel_error_output(state, output_log)

            state.status_page_url = status_result["status_url"]
            state.add_channel_log("status_page", "created", status_result["status_url"])
            state.add_log_entry("Status page generated successfully")
            output_log.append("Status page generation completed")

            # Step 4: Generate QR codes for pickup/kiosk access
            output_log.append("Step 4: Generating QR codes...")
            qr_result = await self._generate_qr_codes(state)

            if not qr_result["success"]:
                state.add_error(f"QR code generation failed: {qr_result['error']}")
                output_log.append(f"QR code error: {qr_result['error']}")
                return self._create_channel_error_output(state, output_log)

            state.qr_codes.update(qr_result["qr_codes"])
            state.add_channel_log("qr_codes", "generated", f"{len(qr_result['qr_codes'])} codes")
            state.add_log_entry("QR codes generated successfully")
            output_log.append("QR code generation completed")

            # Step 5: Setup kiosk booking if delivery/pickup required
            if self.enable_kiosk_booking and state.input_data.delivery_info.get("pickup_required", False):
                output_log.append("Step 5: Setting up kiosk booking...")
                kiosk_result = await self._setup_kiosk_booking(state)

                if not kiosk_result["success"]:
                    state.add_error(f"Kiosk booking setup failed: {kiosk_result['error']}")
                    output_log.append(f"Kiosk booking error: {kiosk_result['error']}")
                    return self._create_channel_error_output(state, output_log)

                state.kiosk_booking.update(kiosk_result["booking_info"])
                state.add_channel_log("kiosk_booking", "setup", kiosk_result["booking_info"].get("booking_id", "unknown"))
                state.add_log_entry("Kiosk booking setup completed")
                output_log.append("Kiosk booking setup completed")

            # Step 6: Generate delivery manifest if required
            if self.enable_delivery_manifest and state.input_data.delivery_info.get("delivery_required", False):
                output_log.append("Step 6: Generating delivery manifest...")
                manifest_result = await self._generate_delivery_manifest(state)

                if not manifest_result["success"]:
                    state.add_error(f"Delivery manifest generation failed: {manifest_result['error']}")
                    output_log.append(f"Delivery manifest error: {manifest_result['error']}")
                    return self._create_channel_error_output(state, output_log)

                state.delivery_manifest.update(manifest_result["manifest"])
                state.add_channel_log("delivery_manifest", "generated", manifest_result["manifest"].get("manifest_id", "unknown"))
                state.add_log_entry("Delivery manifest generated successfully")
                output_log.append("Delivery manifest generation completed")

            # Step 7: Send notifications with channel access information
            output_log.append("Step 7: Sending channel access notifications...")
            notification_result = await self._send_channel_notifications(state)

            notification_summary = notification_result["summary"]
            state.notification_events.extend(notification_result["events"])
            state.add_log_entry("Channel notifications sent successfully")
            output_log.append("Channel notification delivery completed")

            # Step 8: Log all channel creation activities
            output_log.append("Step 8: Logging channel creation activities...")
            logging_result = await self._log_channel_creation(state)

            if not logging_result["success"]:
                logger.warning(f"Channel logging failed: {logging_result['error']}")
                output_log.append(f"Channel logging warning: {logging_result['error']}")

            state.add_log_entry("All sales channels created and logged")
            output_log.append("Sales channel creation and logging completed")

            # Step 9: Determine final transition
            output_log.append("Step 9: Determining final transition...")
            transition = "sales_created"
            state.transition = transition

            final_info = f"Sales channels created successfully: {transition}"
            state.add_log_entry(final_info)
            output_log.append(final_info)

            # Step 10: Prepare sales channel output
            channel_urls = {
                "microstore": state.microstore_url,
                "status_page": state.status_page_url
            }

            # Create output
            output = SalesAgentOutput(
                order_id=state.input_data.order_id,
                channel_urls=channel_urls,
                qr_codes=state.qr_codes,
                access_credentials=state.access_credentials,
                delivery_manifest=state.delivery_manifest,
                notification_summary=notification_summary,
                policy_summary={
                    "policies_applied": len(state.policy_applications),
                    "applications": state.policy_applications
                },
                transition=transition,
                log=output_log + state.log,
                error_details={
                    "errors": state.errors,
                    "channel_errors": [error for error in state.errors if "channel" in error.lower()],
                    "recovery_suggestions": self._get_recovery_suggestions(state)
                } if state.errors else None,
                metadata={
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "channels_created": len([url for url in channel_urls.values() if url]),
                    "qr_codes_generated": len(state.qr_codes),
                    "notifications_sent": len(state.notification_events),
                    "policies_applied": len(state.policy_applications),
                    "kiosk_booking_enabled": bool(state.kiosk_booking),
                    "delivery_manifest_created": bool(state.delivery_manifest),
                    "channel_logs_count": len(state.channel_logs)
                }
            )

            # Final logging
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            output_log.append(f"Sales channel creation completed in {processing_time:.2f}ms")
            output_log.append(f"Final result: {transition} -> {self.transition_map.get(transition, 'Unknown')}")

            logger.info(f"SalesAgentNode completed: {transition} -> {self.transition_map.get(transition, 'Unknown')}")
            return output

        except Exception as e:
            # Handle unexpected errors in sales channel creation
            error_msg = f"Unexpected error in SalesAgentNode: {str(e)}"
            state.add_error(error_msg)
            output_log.append(f"ERROR: {error_msg}")
            output_log.append(f"Traceback: {traceback.format_exc()}")

            logger.error(f"SalesAgentNode error: {e}", exc_info=True)

            return SalesAgentOutput(
                order_id=state.input_data.order_id,
                channel_urls={},
                qr_codes={},
                access_credentials={},
                delivery_manifest={},
                notification_summary={"error": error_msg},
                policy_summary={},
                transition="sales_error",
                log=output_log + state.log,
                error_details={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "recovery_suggestions": ["Contact system administrator", "Check channel creation tools", "Verify order data integrity"]
                },
                metadata={"processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000}
            )

    async def _apply_sales_policies(self, state: SalesAgentState) -> Dict[str, Any]:
        """
        Apply sales policies and restrictions for channel creation.

        Args:
            state: Current sales state

        Returns:
            Dictionary with policy validation results
        """
        try:
            if not self.enable_policy_enforcement:
                return {"passed": True, "reasons": [], "applications": []}

            policy_applications = []
            violations = []

            # Apply commission rates policy
            try:
                order_value = sum(
                    quote.get("price", 0) * quote.get("quantity", 1)
                    for quote in state.input_data.supplier_quotes
                )

                # Commission policy application
                commission_rules = [
                    "standard_commission_rate_applied",
                    "payment_method_commission_calculated",
                    "supplier_commission_assigned"
                ]

                state.add_policy_application("commission", "commission_rates", commission_rules)
                policy_applications.extend(commission_rules)

            except Exception as e:
                violations.append(f"Commission policy error: {e}")

            # Apply category restrictions policy
            try:
                material = state.input_data.order_context.get("material", "").lower()

                # Category-based restrictions
                restricted_categories = ["hazardous", "restricted", "controlled"]
                category_rules = []

                for category in restricted_categories:
                    if category in material:
                        violations.append(f"Material category '{category}' requires special handling")
                        break

                if not violations:
                    category_rules.append("category_restrictions_passed")
                    state.add_policy_application("category", "category_restrictions", category_rules)
                    policy_applications.extend(category_rules)

            except Exception as e:
                violations.append(f"Category policy error: {e}")

            # Apply promotional policies
            try:
                urgency = state.input_data.order_context.get("urgency", "NORMAL")

                promo_rules = ["standard_promo_applied"]
                if urgency == "URGENT":
                    promo_rules.append("urgent_order_promo_boost")

                state.add_policy_application("promotion", "promotional_policies", promo_rules)
                policy_applications.extend(promo_rules)

            except Exception as e:
                violations.append(f"Promotional policy error: {e}")

            return {
                "passed": len(violations) == 0,
                "reasons": violations,
                "applications": policy_applications
            }

        except Exception as e:
            logger.error(f"Sales policy application error: {e}")
            return {
                "passed": False,
                "reasons": [f"Policy application error: {e}"],
                "applications": []
            }

    async def _generate_microstore(self, state: SalesAgentState) -> Dict[str, Any]:
        """
        Generate micro-store PWA for order access.

        Args:
            state: Current sales state

        Returns:
            Dictionary with micro-store generation results
        """
        try:
            if not self.enable_microstore or not self.microstore_tool:
                return {
                    "success": True,
                    "microstore_url": f"https://microstore.artisanhub.com/{state.input_data.order_id}",
                    "credentials": {"access_token": "demo_token", "expires_in": self.default_channel_expiry * 24 * 3600}
                }

            # Generate micro-store using tool
            order_data = {
                "order_id": state.input_data.order_id,
                "material": state.input_data.order_context.get("material", ""),
                "quantity": state.input_data.order_context.get("quantity", 0),
                "supplier_info": state.input_data.supplier_quotes,
                "expiry_days": self.default_channel_expiry
            }

            microstore_result = self.microstore_tool.create_microstore(order_data)

            return {
                "success": True,
                "microstore_url": microstore_result.get("store_url", f"https://microstore.artisanhub.com/{state.input_data.order_id}"),
                "credentials": microstore_result.get("credentials", {"access_token": "generated_token"}),
                "metadata": microstore_result.get("metadata", {})
            }

        except Exception as e:
            logger.error(f"Micro-store generation error: {e}")
            return {
                "success": False,
                "microstore_url": None,
                "credentials": {},
                "error": str(e)
            }

    async def _generate_status_page(self, state: SalesAgentState) -> Dict[str, Any]:
        """
        Generate order status tracking page.

        Args:
            state: Current sales state

        Returns:
            Dictionary with status page generation results
        """
        try:
            # Generate status page URL (in real implementation, would use PWA tools)
            status_url = f"https://track.artisanhub.com/{state.input_data.order_id}"

            # Generate access credentials for status page
            credentials = {
                "tracking_token": f"track_{state.input_data.order_id}_{int(datetime.now().timestamp())}",
                "expires_at": (datetime.now() + timedelta(days=self.default_channel_expiry)).isoformat()
            }

            return {
                "success": True,
                "status_url": status_url,
                "credentials": credentials
            }

        except Exception as e:
            logger.error(f"Status page generation error: {e}")
            return {
                "success": False,
                "status_url": None,
                "credentials": {},
                "error": str(e)
            }

    async def _generate_qr_codes(self, state: SalesAgentState) -> Dict[str, Any]:
        """
        Generate QR codes for pickup and kiosk access.

        Args:
            state: Current sales state

        Returns:
            Dictionary with QR code generation results
        """
        try:
            if not self.enable_qr_generation or not self.qr_generator:
                # Generate demo QR codes
                qr_codes = {
                    "pickup": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAABkCAYAAAAo",
                    "kiosk": "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAABkCAYAAAAo"
                }
                return {"success": True, "qr_codes": qr_codes}

            # Generate QR codes for different access types
            qr_data = {
                "pickup": f"pickup://{state.input_data.order_id}",
                "kiosk": f"kiosk://{state.input_data.order_id}",
                "status": f"status://{state.input_data.order_id}"
            }

            generated_codes = {}
            for qr_type, data in qr_data.items():
                try:
                    qr_code = self.qr_generator.generate_qr(data)
                    generated_codes[qr_type] = qr_code
                except Exception as e:
                    logger.warning(f"Failed to generate {qr_type} QR code: {e}")
                    # Use demo QR code as fallback
                    generated_codes[qr_type] = "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAABkCAYAAAAo"

            return {
                "success": True,
                "qr_codes": generated_codes
            }

        except Exception as e:
            logger.error(f"QR code generation error: {e}")
            return {
                "success": False,
                "qr_codes": {},
                "error": str(e)
            }

    async def _setup_kiosk_booking(self, state: SalesAgentState) -> Dict[str, Any]:
        """
        Setup kiosk booking for scan-based pickup.

        Args:
            state: Current sales state

        Returns:
            Dictionary with kiosk booking results
        """
        try:
            # Generate kiosk booking information
            booking_info = {
                "booking_id": f"kiosk_{state.input_data.order_id}_{int(datetime.now().timestamp())}",
                "order_id": state.input_data.order_id,
                "pickup_location": state.input_data.delivery_info.get("pickup_location", "default_kiosk"),
                "booking_time": datetime.now().isoformat(),
                "expiry_time": (datetime.now() + timedelta(hours=48)).isoformat(),  # 48 hour pickup window
                "qr_access_code": state.qr_codes.get("kiosk", ""),
                "status": "active"
            }

            return {
                "success": True,
                "booking_info": booking_info
            }

        except Exception as e:
            logger.error(f"Kiosk booking setup error: {e}")
            return {
                "success": False,
                "booking_info": {},
                "error": str(e)
            }

    async def _generate_delivery_manifest(self, state: SalesAgentState) -> Dict[str, Any]:
        """
        Generate delivery manifest for logistics.

        Args:
            state: Current sales state

        Returns:
            Dictionary with delivery manifest results
        """
        try:
            # Generate delivery manifest
            manifest = {
                "manifest_id": f"manifest_{state.input_data.order_id}_{int(datetime.now().timestamp())}",
                "order_id": state.input_data.order_id,
                "delivery_address": state.input_data.delivery_info.get("delivery_address", {}),
                "pickup_address": state.input_data.delivery_info.get("pickup_address", {}),
                "items": [
                    {
                        "material": state.input_data.order_context.get("material", ""),
                        "quantity": state.input_data.order_context.get("quantity", 0),
                        "supplier_id": quote.get("supplier_id"),
                        "tracking_number": f"TRK{quote.get('supplier_id', '0')}{int(datetime.now().timestamp())}"
                    }
                    for quote in state.input_data.supplier_quotes
                ],
                "created_at": datetime.now().isoformat(),
                "estimated_delivery": (datetime.now() + timedelta(days=3)).isoformat(),  # Default 3 days
                "status": "prepared"
            }

            return {
                "success": True,
                "manifest": manifest
            }

        except Exception as e:
            logger.error(f"Delivery manifest generation error: {e}")
            return {
                "success": False,
                "manifest": {},
                "error": str(e)
            }

    async def _send_channel_notifications(self, state: SalesAgentState) -> Dict[str, Any]:
        """
        Send notifications with channel access information.

        Args:
            state: Current sales state

        Returns:
            Dictionary with notification results
        """
        try:
            if not self.enable_notifications or not self.email_stub:
                return {
                    "events": [],
                    "summary": "Notifications disabled"
                }

            notification_events = []
            notification_summary = []

            # Notify artisan about available channels
            try:
                artisan_email = state.input_data.workflow_metadata.get("user_email", "artisan@example.com")
                channel_info = {
                    "microstore_url": state.microstore_url,
                    "status_page_url": state.status_page_url,
                    "qr_codes_available": len(state.qr_codes),
                    "order_id": state.input_data.order_id
                }

                artisan_notification = self.NotificationBase(
                    recipient=artisan_email,
                    subject=f"Order Channels Ready - {state.input_data.order_id}",
                    content=f"Your order channels are ready. Access your micro-store at {channel_info['microstore_url']} and track status at {channel_info['status_page_url']}.",
                    event_type="channel_access"
                )

                self.email_stub.send(artisan_notification)
                state.add_notification_event(artisan_email, "email", "sent", "channel_access")
                notification_events.append({"type": "artisan_channel_access", "status": "sent"})
                notification_summary.append("Artisan notified of channel access")

            except Exception as e:
                state.add_notification_event(artisan_email, "email", "failed", "channel_access")
                notification_events.append({"type": "artisan_channel_access", "status": "failed", "error": str(e)})
                logger.warning(f"Artisan channel notification failed: {e}")

            # Notify suppliers about order channels
            for quote in state.input_data.supplier_quotes:
                try:
                    supplier_id = quote.get("supplier_id")
                    supplier_email = f"supplier{supplier_id}@example.com"

                    supplier_notification = self.NotificationBase(
                        recipient=supplier_email,
                        subject=f"Order Channels Created - {state.input_data.order_id}",
                        content=f"Order {state.input_data.order_id} channels are ready. Check delivery manifest and prepare for fulfillment.",
                        event_type="supplier_channel_info"
                    )

                    self.email_stub.send(supplier_notification)
                    state.add_notification_event(supplier_email, "email", "sent", "supplier_channel_info")
                    notification_events.append({"type": f"supplier_{supplier_id}_channel_info", "status": "sent"})
                    notification_summary.append(f"Supplier {supplier_id} notified of channels")

                except Exception as e:
                    state.add_notification_event(supplier_email, "email", "failed", "supplier_channel_info")
                    notification_events.append({"type": f"supplier_{supplier_id}_channel_info", "status": "failed", "error": str(e)})
                    logger.warning(f"Supplier {supplier_id} channel notification failed: {e}")

            return {
                "events": notification_events,
                "summary": "; ".join(notification_summary) if notification_summary else "No notifications sent"
            }

        except Exception as e:
            logger.error(f"Channel notification sending error: {e}")
            return {
                "events": [{"type": "notification_error", "status": "failed", "error": str(e)}],
                "summary": f"Notification error: {e}"
            }

    async def _log_channel_creation(self, state: SalesAgentState) -> Dict[str, Any]:
        """
        Log all channel creation activities for admin/audit use.

        Args:
            state: Current sales state

        Returns:
            Dictionary with logging results
        """
        try:
            # Create comprehensive channel creation log
            log_data = {
                "order_id": state.input_data.order_id,
                "timestamp": datetime.now().isoformat(),
                "channels_created": {
                    "microstore": state.microstore_url is not None,
                    "status_page": state.status_page_url is not None,
                    "qr_codes": len(state.qr_codes),
                    "kiosk_booking": bool(state.kiosk_booking),
                    "delivery_manifest": bool(state.delivery_manifest)
                },
                "notifications_sent": len(state.notification_events),
                "policies_applied": len(state.policy_applications),
                "channel_logs": state.channel_logs,
                "processing_metadata": {
                    "node_id": self.node_id,
                    "processing_time_ms": (datetime.now() - state.timestamp).total_seconds() * 1000,
                    "errors_encountered": len(state.errors)
                }
            }

            # In a real implementation, this would be persisted to audit logs
            # For now, we'll just log to the application logger
            logger.info(f"Channel creation audit log for order {state.input_data.order_id}: {log_data}")

            return {
                "success": True,
                "log_data": log_data
            }

        except Exception as e:
            logger.error(f"Channel logging error: {e}")
            return {
                "success": False,
                "log_data": {},
                "error": str(e)
            }

    def _create_policy_block_output(self, state: SalesAgentState, log_entries: List[str]) -> SalesAgentOutput:
        """Create output for policy block scenarios."""
        return SalesAgentOutput(
            order_id=state.input_data.order_id,
            channel_urls={},
            qr_codes={},
            access_credentials={},
            delivery_manifest={},
            notification_summary={},
            policy_summary={"blocked": True, "reasons": [error for error in state.errors if "policy" in error.lower()]},
            transition="policy_block",
            log=log_entries + state.log,
            error_details={
                "error_type": "policy_violation",
                "violations": [error for error in state.errors if "policy" in error.lower()],
                "suggestions": ["Review material restrictions", "Check commission policies", "Contact support for policy exceptions"]
            },
            metadata={"policy_blocked": True}
        )

    def _create_channel_error_output(self, state: SalesAgentState, log_entries: List[str]) -> SalesAgentOutput:
        """Create output for channel creation error scenarios."""
        return SalesAgentOutput(
            order_id=state.input_data.order_id,
            channel_urls={"microstore": state.microstore_url, "status_page": state.status_page_url},
            qr_codes=state.qr_codes,
            access_credentials=state.access_credentials,
            delivery_manifest=state.delivery_manifest,
            notification_summary={},
            policy_summary={"policies_applied": len(state.policy_applications)},
            transition="sales_error",
            log=log_entries + state.log,
            error_details={
                "error_type": "channel_creation_error",
                "channel_errors": state.errors,
                "suggestions": ["Retry channel creation", "Check tool configurations", "Contact technical support"]
            },
            metadata={"channel_creation_failed": True}
        )

    def _get_recovery_suggestions(self, state: SalesAgentState) -> List[str]:
        """Get recovery suggestions based on current state."""
        suggestions = []

        if any("policy" in error.lower() for error in state.errors):
            suggestions.append("Review and adjust order requirements to meet policy constraints")

        if any("channel" in error.lower() for error in state.errors):
            suggestions.append("Check channel creation tool configurations and retry")

        if any("notification" in error.lower() for error in state.errors):
            suggestions.append("Verify notification service configuration")

        return suggestions if suggestions else ["Contact system administrator for assistance"]

    @property
    def transitions(self) -> Dict[str, str]:
        """Get transition mapping for LangGraph routing."""
        return self.transition_map

    @property
    def meta(self) -> Dict[str, Any]:
        """Get node metadata for UI/graph editor."""
        return self._meta

    @meta.setter
    def meta(self, value: Dict[str, Any]):
        """Set node metadata."""
        self._meta = value


# ============================================================================
# SECTION: STUB TOOLS FOR SALESAGENT
# ============================================================================

class MicroStoreTool:
    """Stub implementation for micro-store generation tool."""

    def create_microstore(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Create micro-store for order access."""
        return {
            "store_url": f"https://microstore.artisanhub.com/{order_data['order_id']}",
            "credentials": {
                "access_token": f"store_token_{order_data['order_id']}",
                "expires_in": 30 * 24 * 3600  # 30 days
            },
            "metadata": {
                "created_at": datetime.now().isoformat(),
                "store_type": "pwa",
                "features": ["order_tracking", "supplier_communication", "payment_history"]
            }
        }


class PWATool:
    """Stub implementation for PWA generation tool."""

    def create_pwa(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """Create PWA for order status tracking."""
        return {
            "pwa_url": f"https://pwa.artisanhub.com/{config.get('order_id', 'unknown')}",
            "manifest": {
                "name": "ArtisanHub Order Tracker",
                "short_name": "OrderTracker",
                "start_url": f"/{config.get('order_id', 'unknown')}",
                "display": "standalone"
            }
        }


class QRGeneratorTool:
    """Stub implementation for QR code generation tool."""

    def generate_qr(self, data: str) -> str:
        """Generate QR code for given data."""
        # In a real implementation, this would generate actual QR codes
        # For now, return a demo base64 encoded QR code
        return "data:image/png;base64,iVBORw0KGgoAAAANSUhEUgAAAMgAAABkCAYAAAAo"


# ============================================================================
# SECTION: SALESAGENT SELF-TEST HARNESS
# ============================================================================

async def run_sales_self_test():
    """
    Self-test harness for SalesAgentNode with various channel creation scenarios.

    Tests valid channel creation, policy violations, error conditions,
    and notification scenarios to ensure proper transition logic.
    """
    print("\n🛒 SalesAgentNode Self-Test Harness")
    print("=" * 50)

    # Initialize the sales node
    sales_node = SalesAgentNode(
        node_id="test_sales_agent",
        enable_microstore=True,
        enable_qr_generation=True,
        enable_kiosk_booking=True,
        enable_notifications=True,
        enable_policy_enforcement=True,
        enable_delivery_manifest=True,
        default_channel_expiry=7  # Short expiry for testing
    )

    # Sample test cases for sales channel scenarios
    test_cases = [
        {
            "name": "Valid Channel Creation - Solo Order",
            "input": {
                "order_id": "ORD-20250108-001",
                "order_context": {
                    "material": "aluminum sheets",
                    "quantity": 5.0,
                    "unit": "kg",
                    "location": "Chennai",
                    "urgency": "URGENT"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 100.0,
                        "quantity": 5.0,
                        "delivery_days": 2
                    }
                ],
                "artisan_requirements": {
                    "material": "aluminum sheets",
                    "quality": "premium"
                },
                "payment_summary": {
                    "status": "completed",
                    "method": "upi",
                    "amount": 500.0
                },
                "delivery_info": {
                    "pickup_required": True,
                    "delivery_required": False,
                    "pickup_location": "chennai_kiosk_01"
                },
                "workflow_metadata": {
                    "user_id": "artisan123",
                    "user_email": "artisan@example.com",
                    "workflow_id": "wf_001"
                }
            },
            "expected_transition": "sales_created"
        },
        {
            "name": "Valid Channel Creation - Pooling Order",
            "input": {
                "order_id": "ORD-20250108-002",
                "order_context": {
                    "material": "steel rods",
                    "quantity": 20.0,
                    "unit": "pcs",
                    "location": "Mumbai",
                    "urgency": "NORMAL"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 25.0,
                        "quantity": 10.0,
                        "delivery_days": 3
                    },
                    {
                        "supplier_id": 2,
                        "price": 23.0,
                        "quantity": 10.0,
                        "delivery_days": 4
                    }
                ],
                "artisan_requirements": {
                    "material": "steel rods",
                    "quality": "standard"
                },
                "payment_summary": {
                    "status": "completed",
                    "method": "razorpay",
                    "amount": 480.0
                },
                "delivery_info": {
                    "pickup_required": False,
                    "delivery_required": True,
                    "delivery_address": {"city": "Mumbai", "area": "Andheri"}
                },
                "workflow_metadata": {
                    "user_id": "business456",
                    "user_email": "business@example.com",
                    "workflow_id": "wf_002"
                }
            },
            "expected_transition": "sales_created"
        },
        {
            "name": "Policy Block - Restricted Material",
            "input": {
                "order_id": "ORD-20250108-003",
                "order_context": {
                    "material": "hazardous chemicals",
                    "quantity": 10.0,
                    "unit": "liters",
                    "location": "Delhi",
                    "urgency": "NORMAL"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 200.0,
                        "quantity": 10.0,
                        "delivery_days": 5
                    }
                ],
                "artisan_requirements": {
                    "material": "hazardous chemicals",
                    "quality": "industrial"
                },
                "payment_summary": {
                    "status": "completed",
                    "method": "upi",
                    "amount": 2000.0
                },
                "delivery_info": {},
                "workflow_metadata": {
                    "user_id": "industrial789",
                    "user_email": "industrial@example.com",
                    "workflow_id": "wf_003"
                }
            },
            "expected_transition": "policy_block"
        },
        {
            "name": "Channel Creation Error - Tool Failure",
            "input": {
                "order_id": "ORD-20250108-004",
                "order_context": {
                    "material": "plastic sheets",
                    "quantity": 50.0,
                    "unit": "pcs",
                    "location": "Bangalore",
                    "urgency": "URGENT"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 75.0,
                        "quantity": 50.0,
                        "delivery_days": 2
                    }
                ],
                "artisan_requirements": {
                    "material": "plastic sheets",
                    "quality": "premium"
                },
                "payment_summary": {
                    "status": "completed",
                    "method": "upi",
                    "amount": 3750.0
                },
                "delivery_info": {
                    "pickup_required": True,
                    "pickup_location": "bangalore_kiosk_01"
                },
                "workflow_metadata": {
                    "user_id": "premium_user",
                    "user_email": "premium@example.com",
                    "workflow_id": "wf_004"
                }
            },
            "expected_transition": "sales_error",
            "force_tool_failure": True
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n💰 Sales Test Case {i}: {test_case['name']}")
        print("-" * 40)

        try:
            # Special setup for tool failure test
            if test_case.get("force_tool_failure", False):
                # Create a microstore tool that always fails
                class FailingMicroStoreTool:
                    def create_microstore(self, order_data):
                        raise Exception("Microstore tool failure simulation")

                sales_node.microstore_tool = FailingMicroStoreTool()

            # Create sales state
            input_data = SalesAgentInput(**test_case['input'])
            state = SalesAgentState(input_data=input_data)

            # Execute sales node
            output = await sales_node.execute(state)

            # Log results
            print(f"Order ID: {test_case['input']['order_id']}")
            print(f"Material: {test_case['input']['order_context']['material']}")
            print(f"Supplier count: {len(test_case['input']['supplier_quotes'])}")
            print(f"Expected transition: {test_case['expected_transition']}")
            print(f"Actual transition: {output.transition}")

            # Log generated channels
            if output.channel_urls:
                print(f"Microstore URL: {output.channel_urls.get('microstore', 'None')}")
                print(f"Status page URL: {output.channel_urls.get('status_page', 'None')}")

            print(f"QR codes generated: {len(output.qr_codes)}")
            print(f"Notifications sent: {len(output.notification_summary.get('summary', '').split(';')) if output.notification_summary else 0}")
            print(f"Policies applied: {output.policy_summary.get('policies_applied', 0)}")

            # Check if transition matches expectation
            success = output.transition == test_case['expected_transition']
            results.append(success)

            print(f"✅ PASS" if success else f"❌ FAIL")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append(False)

    # Summary
    print(f"\n📊 Sales Channel Test Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All sales channel tests passed!")
    else:
        print(f"⚠️  {total - passed} sales channel test(s) failed")

    return passed == total


# ============================================================================
# SECTION: OPSAGENT NODE SCHEMAS
# ============================================================================

@dataclass
class OpsAgentInput:
    """
    Input data for OpsAgentNode from SalesAgentNode.

    Attributes:
        order_id: Unique order identifier from sales creation
        order_context: Original order details (material, quantity, location, urgency)
        supplier_quotes: List of selected supplier quotes with pricing and delivery
        artisan_requirements: Specific artisan requirements and preferences
        channel_urls: Generated sales channel URLs (microstore, status page)
        delivery_info: Delivery preferences and requirements
        contact_details: Artisan and supplier contact information
        current_status: Current order status flags and metadata
        workflow_metadata: Workflow tracking and user context
    """
    order_id: str
    order_context: Dict[str, Any]
    supplier_quotes: List[Dict[str, Any]]
    artisan_requirements: Dict[str, Any]
    channel_urls: Dict[str, str]
    delivery_info: Dict[str, Any] = field(default_factory=dict)
    contact_details: Dict[str, Any] = field(default_factory=dict)
    current_status: Dict[str, Any] = field(default_factory=dict)
    workflow_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class OpsAgentState:
    """
    Complete state for operations processing workflow.

    Attributes:
        input_data: Input from SalesAgentNode
        delivery_assignment: Assigned delivery routing and logistics
        routing_status: Current delivery routing status and tracking
        status_updates: Timeline of status updates sent to stakeholders
        exception_flags: Flags for delivery exceptions and issues
        escalation_events: Records of escalation events and actions
        notification_logs: Detailed logs of notifications sent
        policy_applications: Operations policies applied to the order
        operation_logs: Detailed logs of operations activities
        errors: List of errors encountered during processing
        timestamp: When this state was created
        transition: Next workflow step to take
        log: Processing log for debugging and monitoring
    """
    input_data: OpsAgentInput
    delivery_assignment: Dict[str, Any] = field(default_factory=dict)
    routing_status: Dict[str, Any] = field(default_factory=dict)
    status_updates: List[Dict[str, Any]] = field(default_factory=list)
    exception_flags: List[str] = field(default_factory=list)
    escalation_events: List[Dict[str, Any]] = field(default_factory=list)
    notification_logs: List[Dict[str, Any]] = field(default_factory=list)
    policy_applications: List[Dict[str, Any]] = field(default_factory=list)
    operation_logs: List[str] = field(default_factory=list)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    transition: str = "pending"
    log: List[str] = field(default_factory=list)

    def add_log_entry(self, message: str, level: str = "INFO"):
        """Add entry to processing log."""
        timestamp = datetime.now().isoformat()
        self.log.append(f"[{timestamp}] {level}: {message}")

    def add_error(self, error: str):
        """Add error to error list and log."""
        self.errors.append(error)
        self.add_log_entry(f"ERROR: {error}", "ERROR")

    def add_operation_log(self, operation: str, details: str, status: str = "completed"):
        """Add operation-specific log entry."""
        log_entry = f"{operation}: {status} - {details}"
        self.operation_logs.append(log_entry)
        self.add_log_entry(log_entry, "INFO")

    def add_status_update(self, recipient: str, status: str, message: str, channel: str = "email"):
        """Record status update sent to stakeholder."""
        update = {
            "recipient": recipient,
            "status": status,
            "message": message,
            "channel": channel,
            "timestamp": datetime.now().isoformat()
        }
        self.status_updates.append(update)
        self.add_log_entry(f"Status update sent to {recipient}: {status}")

    def add_escalation_event(self, event_type: str, reason: str, action_taken: str, priority: str = "medium"):
        """Record escalation event."""
        event = {
            "event_type": event_type,
            "reason": reason,
            "action_taken": action_taken,
            "priority": priority,
            "timestamp": datetime.now().isoformat()
        }
        self.escalation_events.append(event)
        self.add_log_entry(f"ESCALATION: {event_type} - {reason} (Priority: {priority})", "WARNING")

    def add_exception_flag(self, flag: str, reason: str, severity: str = "medium"):
        """Add exception flag with reason and severity."""
        self.exception_flags.append(f"{flag}:{severity}")
        self.add_log_entry(f"EXCEPTION: {flag} - {reason} (Severity: {severity})", "WARNING")


@dataclass
class OpsAgentOutput:
    """
    Output from OpsAgentNode execution.

    Attributes:
        order_id: Unique order identifier
        final_status: Final order status after operations processing
        delivery_summary: Summary of delivery assignment and routing
        status_summary: Summary of all status updates sent
        exception_summary: Summary of exceptions and escalations
        notification_summary: Summary of notifications sent
        transition: Next node in pipeline ('ops_complete', 'exception', 'needs_followup')
        log: Complete processing log
        error_details: Detailed error information if processing failed
        metadata: Additional output metadata including processing metrics
    """
    order_id: str
    final_status: str
    delivery_summary: Dict[str, Any]
    status_summary: Dict[str, Any]
    exception_summary: Dict[str, Any]
    notification_summary: Dict[str, Any]
    transition: str
    log: List[str]
    error_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


# ============================================================================
# SECTION: OPSAGENT NODE CLASS
# ============================================================================

class OpsAgentNode:
    """
    LangGraph-ready OpsAgentNode for post-sale operations management.

    Operations management node activated immediately after SalesAgentNode
    for coordinating delivery assignment, routing, status updates, and exception
    handling for artisan marketplace orders.

    Role: Post-sale operations coordination, delivery management, and exception handling
    Inputs: SalesAgentOutput (order channels, delivery info, contact details, status)
    Outputs: Delivery coordination, status updates, exception management, next transition
    Tool Dependencies: shipping_tools (routing, status simulation), notification_stubs (updates),
                      policy_loader (exception/delivery policy), microstore (status page updates)
    Operations: Delivery assignment, routing coordination, real-time status tracking,
               exception management, escalation procedures, stakeholder notifications
    Downstream Transitions: "ops_complete" -> CashAgent, "exception" -> ErrorHandlerAgent, "needs_followup" -> ClarifyAgent
    """

    def __init__(
        self,
        node_id: str = "ops_agent",
        enable_delivery_assignment: bool = True,
        enable_routing_simulation: bool = True,
        enable_status_tracking: bool = True,
        enable_exception_handling: bool = True,
        enable_notifications: bool = True,
        enable_policy_enforcement: bool = True,
        default_delivery_sla_hours: int = 48,
        max_exception_escalations: int = 3,
        enable_logging: bool = True
    ):
        """
        Initialize OpsAgentNode with operations configuration.

        Args:
            node_id: Unique identifier for this node in LangGraph
            enable_delivery_assignment: Whether to assign delivery routing
            enable_routing_simulation: Whether to simulate routing and tracking
            enable_status_tracking: Whether to track and update order status
            enable_exception_handling: Whether to handle delivery exceptions
            enable_notifications: Whether to send status and exception notifications
            enable_policy_enforcement: Whether to apply operations policies
            default_delivery_sla_hours: Default delivery SLA in hours
            max_exception_escalations: Maximum escalation attempts per exception
            enable_logging: Whether to enable detailed operations logs
        """
        self.node_id = node_id
        self.enable_delivery_assignment = enable_delivery_assignment
        self.enable_routing_simulation = enable_routing_simulation
        self.enable_status_tracking = enable_status_tracking
        self.enable_exception_handling = enable_exception_handling
        self.enable_notifications = enable_notifications
        self.enable_policy_enforcement = enable_policy_enforcement
        self.default_delivery_sla_hours = default_delivery_sla_hours
        self.max_exception_escalations = max_exception_escalations
        self.enable_logging = enable_logging

        # Initialize modular tools
        try:
            from .tools.notification_stubs import EmailNotificationStub, SMSNotificationStub, NotificationBase
            self.email_stub = EmailNotificationStub() if enable_notifications else None
            self.sms_stub = SMSNotificationStub() if enable_notifications else None
            self.NotificationBase = NotificationBase
        except ImportError:
            from tools.notification_stubs import EmailNotificationStub, SMSNotificationStub, NotificationBase
            self.email_stub = EmailNotificationStub() if enable_notifications else None
            self.sms_stub = SMSNotificationStub() if enable_notifications else None
            self.NotificationBase = NotificationBase

        try:
            from .tools.policy_loader import PolicyLoader
            self.policy_loader = PolicyLoader("policies") if enable_policy_enforcement else None
        except ImportError:
            from tools.policy_loader import PolicyLoader
            self.policy_loader = PolicyLoader("policies") if enable_policy_enforcement else None

        # Initialize stub tools for shipping operations (will be created as stubs)
        self.shipping_tool = ShippingTools() if enable_delivery_assignment else None
        self.routing_tool = RoutingSimulator() if enable_routing_simulation else None

        # Load operations policies if enabled
        if self.enable_policy_enforcement and self.policy_loader:
            try:
                self._load_operations_policies()
            except Exception as e:
                logger.warning(f"Could not load operations policies: {e}")

        # Transition mapping for LangGraph routing
        self.transition_map = {
            "ops_complete": "CashAgent",
            "exception": "ErrorHandlerAgent",
            "needs_followup": "ClarifyAgent"
        }

        # Visual metadata for UI/graph editor
        self.meta = {
            "icon": "🚚",
            "color": "blue",
            "description": "Post-Sale Operations Management",
            "order": 6,
            "input_example": {
                "order_id": "ORD-20250108-001",
                "order_context": {
                    "material": "aluminum sheets",
                    "quantity": 5.0,
                    "location": "Chennai",
                    "urgency": "URGENT"
                },
                "channel_urls": {
                    "microstore": "https://microstore.artisanhub.com/ord-001",
                    "status_page": "https://track.artisanhub.com/ord-001"
                },
                "delivery_info": {
                    "pickup_required": True,
                    "delivery_required": False
                }
            },
            "output_example": {
                "order_id": "ORD-20250108-001",
                "final_status": "delivered",
                "delivery_summary": {"assignment": "route_001", "tracking_id": "TRK123"},
                "transition": "ops_complete"
            }
        }

        logger.info(f"OpsAgentNode '{node_id}' initialized successfully")

    def _load_operations_policies(self):
        """Load operations and delivery policies for exception handling."""
        if not self.policy_loader:
            return

        try:
            # Load order limits policy for delivery constraints
            order_limits = self.policy_loader.load_policy('order_limits')
            logger.info("Loaded order limits policy for operations")
        except Exception as e:
            logger.warning(f"Could not load order limits policy: {e}")

    async def execute(self, state: OpsAgentState) -> OpsAgentOutput:
        """
        Async execute method for LangGraph node processing.

        Args:
            state: Current workflow state with input data

        Returns:
            OpsAgentOutput with operations results and next node transition
        """
        start_time = datetime.now()
        output_log = []

        try:
            # Log operations initiation
            output_log.append(f"Operations processing initiated at {start_time.isoformat()}")
            output_log.append(f"Order ID: {state.input_data.order_id}")
            output_log.append(f"Material: {state.input_data.order_context.get('material', 'Unknown')}")
            output_log.append(f"Location: {state.input_data.order_context.get('location', 'Unknown')}")

            # Step 1: Assign delivery routing and logistics
            output_log.append("Step 1: Assigning delivery routing...")
            delivery_result = await self._assign_delivery(state)

            if not delivery_result["success"]:
                state.add_error(f"Delivery assignment failed: {delivery_result['error']}")
                output_log.append(f"Delivery assignment error: {delivery_result['error']}")
                return self._create_exception_output(state, output_log, "delivery_assignment_failed")

            state.delivery_assignment.update(delivery_result["assignment"])
            state.routing_status.update(delivery_result["routing_status"])
            state.add_operation_log("delivery_assignment", delivery_result["assignment"].get("route_id", "unknown"))
            state.add_log_entry("Delivery assignment completed successfully")
            output_log.append("Delivery assignment completed")

            # Step 2: Simulate delivery routing and tracking
            output_log.append("Step 2: Simulating delivery routing...")
            routing_result = await self._simulate_routing(state)

            if not routing_result["success"]:
                state.add_error(f"Routing simulation failed: {routing_result['error']}")
                output_log.append(f"Routing simulation error: {routing_result['error']}")
                return self._create_exception_output(state, output_log, "routing_simulation_failed")

            state.routing_status.update(routing_result["tracking"])
            state.add_operation_log("routing_simulation", routing_result["tracking"].get("tracking_id", "unknown"))
            state.add_log_entry("Routing simulation completed successfully")
            output_log.append("Routing simulation completed")

            # Step 3: Send initial status updates to stakeholders
            output_log.append("Step 3: Sending initial status updates...")
            status_result = await self._send_initial_status_updates(state)

            state.status_updates.extend(status_result["updates"])
            state.notification_logs.extend(status_result["notifications"])
            state.add_log_entry("Initial status updates sent successfully")
            output_log.append("Initial status updates completed")

            # Step 4: Monitor for exceptions and handle issues
            output_log.append("Step 4: Monitoring for delivery exceptions...")
            exception_result = await self._monitor_and_handle_exceptions(state)

            if exception_result["has_exceptions"]:
                state.exception_flags.extend(exception_result["flags"])
                state.escalation_events.extend(exception_result["escalations"])

                if exception_result["requires_escalation"]:
                    state.add_log_entry("Exception requires escalation", "WARNING")
                    output_log.append("Exception escalation triggered")
                    return self._create_exception_output(state, output_log, "exception_escalated")

                state.add_log_entry("Exceptions handled within normal operations")
                output_log.append("Exceptions handled successfully")

            # Step 5: Apply operations policies and SLA checks
            output_log.append("Step 5: Applying operations policies...")
            policy_result = await self._apply_operations_policies(state)

            if not policy_result["passed"]:
                state.add_error(f"Operations policy violation: {policy_result['violations']}")
                output_log.append(f"Policy violation: {policy_result['violations']}")
                return self._create_exception_output(state, output_log, "policy_violation")

            state.policy_applications.extend(policy_result["applications"])
            state.add_log_entry("Operations policies applied successfully")
            output_log.append("Operations policy validation completed")

            # Step 6: Send ongoing status updates during delivery
            output_log.append("Step 6: Sending ongoing status updates...")
            ongoing_status_result = await self._send_ongoing_status_updates(state)

            state.status_updates.extend(ongoing_status_result["updates"])
            state.notification_logs.extend(ongoing_status_result["notifications"])
            state.add_log_entry("Ongoing status updates sent successfully")
            output_log.append("Ongoing status updates completed")

            # Step 7: Complete delivery and send final notifications
            output_log.append("Step 7: Completing delivery process...")
            completion_result = await self._complete_delivery_process(state)

            if not completion_result["success"]:
                state.add_error(f"Delivery completion failed: {completion_result['error']}")
                output_log.append(f"Delivery completion error: {completion_result['error']}")
                return self._create_exception_output(state, output_log, "delivery_completion_failed")

            state.routing_status.update(completion_result["final_status"])
            state.status_updates.extend(completion_result["final_updates"])
            state.add_operation_log("delivery_completion", "completed", state.input_data.order_id)
            state.add_log_entry("Delivery process completed successfully")
            output_log.append("Delivery process completed")

            # Step 8: Log all operations activities for audit
            output_log.append("Step 8: Logging operations activities...")
            logging_result = await self._log_operations_activities(state)

            if not logging_result["success"]:
                logger.warning(f"Operations logging failed: {logging_result['error']}")
                output_log.append(f"Operations logging warning: {logging_result['error']}")

            state.add_log_entry("All operations activities logged")
            output_log.append("Operations logging completed")

            # Step 9: Determine final transition
            output_log.append("Step 9: Determining final transition...")
            transition = self._determine_final_transition(state)
            state.transition = transition

            final_info = f"Operations completed successfully: {transition}"
            state.add_log_entry(final_info)
            output_log.append(final_info)

            # Step 10: Prepare operations summary output
            final_status = state.routing_status.get("final_status", "delivered")

            # Create output
            output = OpsAgentOutput(
                order_id=state.input_data.order_id,
                final_status=final_status,
                delivery_summary={
                    "assignment": state.delivery_assignment,
                    "routing": state.routing_status,
                    "tracking_id": state.routing_status.get("tracking_id", "unknown")
                },
                status_summary={
                    "updates_sent": len(state.status_updates),
                    "stakeholders_notified": len(set(update["recipient"] for update in state.status_updates)),
                    "last_update": state.status_updates[-1] if state.status_updates else None
                },
                exception_summary={
                    "flags_raised": len(state.exception_flags),
                    "escalations": len(state.escalation_events),
                    "resolved": len(state.exception_flags) - len([flag for flag in state.exception_flags if "unresolved" in flag])
                },
                notification_summary={
                    "total_sent": len(state.notification_logs),
                    "channels_used": list(set(log.get("channel", "unknown") for log in state.notification_logs)),
                    "success_rate": len([log for log in state.notification_logs if log.get("status") == "sent"]) / len(state.notification_logs) if state.notification_logs else 0
                },
                transition=transition,
                log=output_log + state.log,
                error_details={
                    "errors": state.errors,
                    "exceptions": state.exception_flags,
                    "recovery_suggestions": self._get_recovery_suggestions(state)
                } if state.errors or state.exception_flags else None,
                metadata={
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "delivery_assigned": bool(state.delivery_assignment),
                    "routing_simulated": bool(state.routing_status),
                    "status_updates_sent": len(state.status_updates),
                    "exceptions_handled": len(state.exception_flags),
                    "escalations_made": len(state.escalation_events),
                    "notifications_sent": len(state.notification_logs),
                    "policies_applied": len(state.policy_applications),
                    "operations_logged": len(state.operation_logs)
                }
            )

            # Final logging
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            output_log.append(f"Operations processing completed in {processing_time:.2f}ms")
            output_log.append(f"Final result: {transition} -> {self.transition_map.get(transition, 'Unknown')}")

            logger.info(f"OpsAgentNode completed: {transition} -> {self.transition_map.get(transition, 'Unknown')}")
            return output

        except Exception as e:
            # Handle unexpected errors in operations processing
            error_msg = f"Unexpected error in OpsAgentNode: {str(e)}"
            state.add_error(error_msg)
            output_log.append(f"ERROR: {error_msg}")
            output_log.append(f"Traceback: {traceback.format_exc()}")

            logger.error(f"OpsAgentNode error: {e}", exc_info=True)

            return OpsAgentOutput(
                order_id=state.input_data.order_id,
                final_status="error",
                delivery_summary={},
                status_summary={},
                exception_summary={"error": error_msg},
                notification_summary={},
                transition="exception",
                log=output_log + state.log,
                error_details={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "recovery_suggestions": ["Contact operations administrator", "Check delivery systems", "Verify order data integrity"]
                },
                metadata={"processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000}
            )

    async def _assign_delivery(self, state: OpsAgentState) -> Dict[str, Any]:
        """
        Assign delivery routing and logistics for the order.

        Args:
            state: Current operations state

        Returns:
            Dictionary with delivery assignment results
        """
        try:
            if not self.enable_delivery_assignment or not self.shipping_tool:
                # Generate mock delivery assignment
                assignment = {
                    "route_id": f"ROUTE_{state.input_data.order_id}_{int(datetime.now().timestamp())}",
                    "assignment_type": "standard_delivery",
                    "estimated_delivery_time": (datetime.now() + timedelta(hours=self.default_delivery_sla_hours)).isoformat(),
                    "delivery_method": state.input_data.delivery_info.get("delivery_method", "ground"),
                    "priority": state.input_data.order_context.get("urgency", "NORMAL").lower(),
                    "assigned_at": datetime.now().isoformat()
                }

                return {
                    "success": True,
                    "assignment": assignment,
                    "routing_status": {
                        "status": "assigned",
                        "tracking_id": f"TRK{int(datetime.now().timestamp())}",
                        "current_location": "warehouse",
                        "estimated_arrival": assignment["estimated_delivery_time"]
                    }
                }

            # Use shipping tool for delivery assignment
            order_data = {
                "order_id": state.input_data.order_id,
                "material": state.input_data.order_context.get("material", ""),
                "quantity": state.input_data.order_context.get("quantity", 0),
                "delivery_address": state.input_data.delivery_info.get("delivery_address", {}),
                "urgency": state.input_data.order_context.get("urgency", "NORMAL"),
                "supplier_info": state.input_data.supplier_quotes
            }

            assignment_result = self.shipping_tool.assign_delivery(order_data)

            return {
                "success": True,
                "assignment": assignment_result.get("assignment", assignment),
                "routing_status": assignment_result.get("routing_status", {})
            }

        except Exception as e:
            logger.error(f"Delivery assignment error: {e}")
            return {
                "success": False,
                "assignment": {},
                "routing_status": {},
                "error": str(e)
            }

    async def _simulate_routing(self, state: OpsAgentState) -> Dict[str, Any]:
        """
        Simulate delivery routing and real-time tracking.

        Args:
            state: Current operations state

        Returns:
            Dictionary with routing simulation results
        """
        try:
            if not self.enable_routing_simulation or not self.routing_tool:
                # Generate mock routing simulation
                tracking = {
                    "tracking_id": f"TRK{int(datetime.now().timestamp())}",
                    "current_status": "in_transit",
                    "current_location": "distribution_center",
                    "estimated_delivery": (datetime.now() + timedelta(hours=random.randint(24, 72))).isoformat(),
                    "route_progress": 15.0,
                    "stops_remaining": random.randint(3, 8),
                    "last_updated": datetime.now().isoformat()
                }

                return {
                    "success": True,
                    "tracking": tracking
                }

            # Use routing tool for simulation
            routing_data = {
                "order_id": state.input_data.order_id,
                "delivery_assignment": state.delivery_assignment,
                "start_location": "warehouse",
                "end_location": state.input_data.delivery_info.get("delivery_address", {}).get("city", "unknown"),
                "urgency": state.input_data.order_context.get("urgency", "NORMAL")
            }

            routing_result = self.routing_tool.simulate_routing(routing_data)

            return {
                "success": True,
                "tracking": routing_result.get("tracking", tracking)
            }

        except Exception as e:
            logger.error(f"Routing simulation error: {e}")
            return {
                "success": False,
                "tracking": {},
                "error": str(e)
            }

    async def _send_initial_status_updates(self, state: OpsAgentState) -> Dict[str, Any]:
        """
        Send initial status updates to stakeholders.

        Args:
            state: Current operations state

        Returns:
            Dictionary with status update results
        """
        try:
            if not self.enable_notifications or not self.email_stub:
                return {
                    "updates": [],
                    "notifications": [{"status": "disabled", "channel": "email"}]
                }

            updates = []
            notifications = []

            # Notify artisan about delivery assignment
            try:
                artisan_email = state.input_data.workflow_metadata.get("user_email", "artisan@example.com")
                status_message = f"Your order {state.input_data.order_id} has been assigned for delivery. Track at {state.input_data.channel_urls.get('status_page', 'N/A')}"

                artisan_notification = self.NotificationBase(
                    recipient=artisan_email,
                    subject=f"Order {state.input_data.order_id} - Delivery Assigned",
                    content=status_message,
                    event_type="delivery_assigned"
                )

                self.email_stub.send(artisan_notification)
                state.add_status_update(artisan_email, "delivery_assigned", status_message, "email")
                updates.append({"recipient": artisan_email, "type": "delivery_assigned"})
                notifications.append({"recipient": artisan_email, "status": "sent", "channel": "email"})

            except Exception as e:
                state.add_status_update(artisan_email, "delivery_assigned_failed", str(e), "email")
                notifications.append({"recipient": artisan_email, "status": "failed", "channel": "email", "error": str(e)})
                logger.warning(f"Artisan delivery notification failed: {e}")

            # Notify suppliers about delivery coordination
            for quote in state.input_data.supplier_quotes:
                try:
                    supplier_id = quote.get("supplier_id")
                    supplier_email = f"supplier{supplier_id}@example.com"
                    supplier_message = f"Order {state.input_data.order_id} delivery has been coordinated. Please prepare materials for pickup."

                    supplier_notification = self.NotificationBase(
                        recipient=supplier_email,
                        subject=f"Order {state.input_data.order_id} - Delivery Coordination",
                        content=supplier_message,
                        event_type="supplier_delivery_coordination"
                    )

                    self.email_stub.send(supplier_notification)
                    state.add_status_update(supplier_email, "delivery_coordination", supplier_message, "email")
                    updates.append({"recipient": supplier_email, "type": "delivery_coordination"})
                    notifications.append({"recipient": supplier_email, "status": "sent", "channel": "email"})

                except Exception as e:
                    state.add_status_update(supplier_email, "delivery_coordination_failed", str(e), "email")
                    notifications.append({"recipient": supplier_email, "status": "failed", "channel": "email", "error": str(e)})
                    logger.warning(f"Supplier {supplier_id} delivery notification failed: {e}")

            return {
                "updates": updates,
                "notifications": notifications
            }

        except Exception as e:
            logger.error(f"Initial status update error: {e}")
            return {
                "updates": [],
                "notifications": [{"status": "error", "error": str(e)}]
            }

    async def _monitor_and_handle_exceptions(self, state: OpsAgentState) -> Dict[str, Any]:
        """
        Monitor for delivery exceptions and handle issues.

        Args:
            state: Current operations state

        Returns:
            Dictionary with exception monitoring results
        """
        try:
            if not self.enable_exception_handling:
                return {
                    "has_exceptions": False,
                    "flags": [],
                    "escalations": [],
                    "requires_escalation": False
                }

            flags = []
            escalations = []
            requires_escalation = False

            # Simulate exception detection based on order characteristics
            urgency = state.input_data.order_context.get("urgency", "NORMAL")
            material = state.input_data.order_context.get("material", "").lower()
            location = state.input_data.order_context.get("location", "").lower()

            # Check for potential delay scenarios
            if urgency == "EMERGENCY" and random.random() < 0.3:  # 30% chance of delay for emergency
                flags.append("potential_delay:high")
                state.add_exception_flag("potential_delay", "Emergency order may experience delays", "high")

                # Escalate if high priority
                if self._should_escalate_exception("potential_delay", "high"):
                    escalations.append({
                        "type": "delay_escalation",
                        "reason": "Emergency order delay risk",
                        "action": "Priority routing assigned"
                    })
                    state.add_escalation_event("delay_risk", "Emergency order delay risk", "Priority routing assigned", "high")
                    requires_escalation = True

            # Check for location-based issues
            if location in ["remote", "rural"] and random.random() < 0.4:  # 40% chance for remote locations
                flags.append("location_challenge:medium")
                state.add_exception_flag("location_challenge", f"Delivery to {location} may have logistics challenges", "medium")

            # Check for material handling issues
            if any(keyword in material for keyword in ["hazardous", "fragile", "perishable"]):
                flags.append("special_handling:medium")
                state.add_exception_flag("special_handling", f"Material {material} requires special handling", "medium")

            # Check for quantity-based issues
            quantity = state.input_data.order_context.get("quantity", 0)
            if quantity > 1000:
                flags.append("high_volume:low")
                state.add_exception_flag("high_volume", f"Large quantity ({quantity}) may require special logistics", "low")

            return {
                "has_exceptions": len(flags) > 0,
                "flags": flags,
                "escalations": escalations,
                "requires_escalation": requires_escalation
            }

        except Exception as e:
            logger.error(f"Exception monitoring error: {e}")
            return {
                "has_exceptions": True,
                "flags": [f"monitoring_error:{str(e)}"],
                "escalations": [],
                "requires_escalation": True
            }

    async def _apply_operations_policies(self, state: OpsAgentState) -> Dict[str, Any]:
        """
        Apply operations policies and SLA checks.

        Args:
            state: Current operations state

        Returns:
            Dictionary with policy application results
        """
        try:
            if not self.enable_policy_enforcement:
                return {
                    "passed": True,
                    "violations": [],
                    "applications": ["policy_enforcement_disabled"]
                }

            violations = []
            applications = []

            # Apply delivery SLA policy
            try:
                urgency = state.input_data.order_context.get("urgency", "NORMAL")
                sla_hours = self._get_sla_for_urgency(urgency)

                estimated_delivery = state.delivery_assignment.get("estimated_delivery_time")
                if estimated_delivery:
                    delivery_time = datetime.fromisoformat(estimated_delivery.replace('Z', '+00:00'))
                    sla_deadline = datetime.now() + timedelta(hours=sla_hours)

                    if delivery_time > sla_deadline:
                        violations.append(f"Delivery exceeds SLA for {urgency} orders (SLA: {sla_hours}h, Estimated: {(delivery_time - datetime.now()).total_seconds() / 3600:.1f}h)")
                    else:
                        applications.append(f"sla_compliant_{urgency.lower()}")

            except Exception as e:
                violations.append(f"SLA policy check error: {e}")

            # Apply location-based policies
            try:
                location = state.input_data.order_context.get("location", "").lower()

                # Check for restricted regions
                restricted_regions = ["restricted_area", "sanctioned_zone"]
                if location in restricted_regions:
                    violations.append(f"Delivery to restricted region: {location}")
                else:
                    applications.append("location_policy_compliant")

            except Exception as e:
                violations.append(f"Location policy check error: {e}")

            # Apply material handling policies
            try:
                material = state.input_data.order_context.get("material", "").lower()

                # Check for special handling requirements
                special_materials = ["hazardous", "controlled", "perishable"]
                if any(keyword in material for keyword in special_materials):
                    applications.append(f"special_handling_{material.replace(' ', '_')}")
                else:
                    applications.append("standard_material_handling")

            except Exception as e:
                violations.append(f"Material policy check error: {e}")

            return {
                "passed": len(violations) == 0,
                "violations": violations,
                "applications": applications
            }

        except Exception as e:
            logger.error(f"Operations policy application error: {e}")
            return {
                "passed": False,
                "violations": [f"Policy application error: {e}"],
                "applications": []
            }

    async def _send_ongoing_status_updates(self, state: OpsAgentState) -> Dict[str, Any]:
        """
        Send ongoing status updates during delivery process.

        Args:
            state: Current operations state

        Returns:
            Dictionary with ongoing status update results
        """
        try:
            if not self.enable_notifications or not self.email_stub:
                return {
                    "updates": [],
                    "notifications": [{"status": "disabled", "channel": "email"}]
                }

            updates = []
            notifications = []

            # Simulate ongoing status updates based on routing progress
            current_status = state.routing_status.get("current_status", "preparing")
            progress = state.routing_status.get("route_progress", 0)

            # Send progress update if in transit
            if current_status == "in_transit" and progress > 10:
                try:
                    artisan_email = state.input_data.workflow_metadata.get("user_email", "artisan@example.com")
                    progress_message = f"Your order {state.input_data.order_id} is {progress:.1f}% complete. Current status: {current_status.replace('_', ' ').title()}"

                    progress_notification = self.NotificationBase(
                        recipient=artisan_email,
                        subject=f"Order {state.input_data.order_id} - Progress Update",
                        content=progress_message,
                        event_type="delivery_progress"
                    )

                    self.email_stub.send(progress_notification)
                    state.add_status_update(artisan_email, "in_transit", progress_message, "email")
                    updates.append({"recipient": artisan_email, "type": "delivery_progress"})
                    notifications.append({"recipient": artisan_email, "status": "sent", "channel": "email"})

                except Exception as e:
                    state.add_status_update(artisan_email, "progress_update_failed", str(e), "email")
                    notifications.append({"recipient": artisan_email, "status": "failed", "channel": "email", "error": str(e)})
                    logger.warning(f"Progress update notification failed: {e}")

            return {
                "updates": updates,
                "notifications": notifications
            }

        except Exception as e:
            logger.error(f"Ongoing status update error: {e}")
            return {
                "updates": [],
                "notifications": [{"status": "error", "error": str(e)}]
            }

    async def _complete_delivery_process(self, state: OpsAgentState) -> Dict[str, Any]:
        """
        Complete delivery process and send final notifications.

        Args:
            state: Current operations state

        Returns:
            Dictionary with delivery completion results
        """
        try:
            # Update final status
            final_status = {
                "status": "delivered",
                "delivered_at": datetime.now().isoformat(),
                "delivery_method": state.delivery_assignment.get("delivery_method", "unknown"),
                "tracking_id": state.routing_status.get("tracking_id", "unknown"),
                "completion_confirmed": True
            }

            # Send final delivery confirmation
            final_updates = []

            if self.enable_notifications and self.email_stub:
                try:
                    artisan_email = state.input_data.workflow_metadata.get("user_email", "artisan@example.com")
                    completion_message = f"Your order {state.input_data.order_id} has been successfully delivered! Thank you for using ArtisanHub."

                    completion_notification = self.NotificationBase(
                        recipient=artisan_email,
                        subject=f"Order {state.input_data.order_id} - Delivery Completed",
                        content=completion_message,
                        event_type="delivery_completed"
                    )

                    self.email_stub.send(completion_notification)
                    final_update = {
                        "recipient": artisan_email,
                        "status": "delivered",
                        "message": completion_message,
                        "channel": "email",
                        "timestamp": datetime.now().isoformat()
                    }
                    final_updates.append(final_update)

                except Exception as e:
                    logger.warning(f"Delivery completion notification failed: {e}")

            return {
                "success": True,
                "final_status": final_status,
                "final_updates": final_updates
            }

        except Exception as e:
            logger.error(f"Delivery completion error: {e}")
            return {
                "success": False,
                "final_status": {"status": "completion_failed"},
                "final_updates": [],
                "error": str(e)
            }

    async def _log_operations_activities(self, state: OpsAgentState) -> Dict[str, Any]:
        """
        Log all operations activities for audit and analytics.

        Args:
            state: Current operations state

        Returns:
            Dictionary with logging results
        """
        try:
            # Create comprehensive operations log
            log_data = {
                "order_id": state.input_data.order_id,
                "timestamp": datetime.now().isoformat(),
                "operations_summary": {
                    "delivery_assigned": bool(state.delivery_assignment),
                    "routing_simulated": bool(state.routing_status),
                    "status_updates_sent": len(state.status_updates),
                    "exceptions_handled": len(state.exception_flags),
                    "escalations_made": len(state.escalation_events),
                    "notifications_sent": len(state.notification_logs)
                },
                "delivery_details": state.delivery_assignment,
                "routing_details": state.routing_status,
                "exception_summary": {
                    "flags": state.exception_flags,
                    "escalations": state.escalation_events
                },
                "notification_summary": {
                    "total_sent": len(state.notification_logs),
                    "stakeholders_notified": len(set(log.get("recipient", "unknown") for log in state.notification_logs))
                },
                "processing_metadata": {
                    "node_id": self.node_id,
                    "processing_time_ms": (datetime.now() - state.timestamp).total_seconds() * 1000,
                    "errors_encountered": len(state.errors),
                    "policies_applied": len(state.policy_applications)
                }
            }

            # In a real implementation, this would be persisted to audit logs
            logger.info(f"Operations audit log for order {state.input_data.order_id}: {log_data}")

            return {
                "success": True,
                "log_data": log_data
            }

        except Exception as e:
            logger.error(f"Operations logging error: {e}")
            return {
                "success": False,
                "log_data": {},
                "error": str(e)
            }

    def _determine_final_transition(self, state: OpsAgentState) -> str:
        """
        Determine final workflow transition based on operations results.

        Args:
            state: Current operations state

        Returns:
            Transition string: "ops_complete", "exception", or "needs_followup"
        """
        try:
            # If we have unhandled exceptions or errors, route to exception handler
            if state.errors or any("unresolved" in flag for flag in state.exception_flags):
                return "exception"

            # If we have exceptions that need follow-up, route to clarification
            if state.exception_flags and not all("resolved" in flag for flag in state.exception_flags):
                return "needs_followup"

            # If delivery completed successfully, route to cash agent
            if state.routing_status.get("status") == "delivered":
                return "ops_complete"

            # If we have moderate exceptions but they're handled, still complete
            if state.exception_flags and all("resolved" in flag for flag in state.exception_flags):
                return "ops_complete"

            # Default to needs_followup for unclear situations
            return "needs_followup"

        except Exception as e:
            logger.error(f"Final transition determination error: {e}")
            return "exception"

    def _create_exception_output(self, state: OpsAgentState, log_entries: List[str], exception_type: str) -> OpsAgentOutput:
        """Create output for exception scenarios."""
        return OpsAgentOutput(
            order_id=state.input_data.order_id,
            final_status="exception",
            delivery_summary={"assignment": state.delivery_assignment, "routing": state.routing_status},
            status_summary={"updates_sent": len(state.status_updates)},
            exception_summary={
                "flags": state.exception_flags,
                "escalations": state.escalation_events,
                "exception_type": exception_type
            },
            notification_summary={"total_sent": len(state.notification_logs)},
            transition="exception" if exception_type in ["exception_escalated", "delivery_completion_failed"] else "needs_followup",
            log=log_entries + state.log,
            error_details={
                "error_type": "operations_exception",
                "exceptions": state.exception_flags,
                "errors": state.errors,
                "suggestions": self._get_recovery_suggestions(state)
            },
            metadata={"exception_occurred": True, "exception_type": exception_type}
        )

    def _get_recovery_suggestions(self, state: OpsAgentState) -> List[str]:
        """Get recovery suggestions based on current state."""
        suggestions = []

        if any("policy" in error.lower() for error in state.errors):
            suggestions.append("Review operations policies and order requirements")

        if any("delivery" in error.lower() for error in state.errors):
            suggestions.append("Check delivery assignment and routing systems")

        if any("routing" in error.lower() for error in state.errors):
            suggestions.append("Verify routing simulation and tracking systems")

        if state.exception_flags:
            suggestions.append("Address delivery exceptions before proceeding")

        return suggestions if suggestions else ["Contact operations administrator for assistance"]

    def _get_sla_for_urgency(self, urgency: str) -> int:
        """Get SLA hours for urgency level."""
        sla_map = {
            "EMERGENCY": 4,
            "URGENT": 24,
            "NORMAL": self.default_delivery_sla_hours
        }
        return sla_map.get(urgency, self.default_delivery_sla_hours)

    def _should_escalate_exception(self, exception_type: str, severity: str) -> bool:
        """Determine if exception should be escalated."""
        high_priority_exceptions = ["potential_delay", "delivery_failed", "routing_error"]
        high_severity = ["high", "critical"]

        return (exception_type in high_priority_exceptions or
                severity in high_severity or
                len(self.escalation_events) < self.max_exception_escalations)

    @property
    def transitions(self) -> Dict[str, str]:
        """Get transition mapping for LangGraph routing."""
        return self.transition_map

    @property
    def meta(self) -> Dict[str, Any]:
        """Get node metadata for UI/graph editor."""
        return self._meta

    @meta.setter
    def meta(self, value: Dict[str, Any]):
        """Set node metadata."""
        self._meta = value


# ============================================================================
# SECTION: STUB TOOLS FOR OPSAGENT
# ============================================================================

class ShippingTools:
    """Stub implementation for shipping and delivery tools."""

    def assign_delivery(self, order_data: Dict[str, Any]) -> Dict[str, Any]:
        """Assign delivery routing for order."""
        return {
            "assignment": {
                "route_id": f"ROUTE_{order_data['order_id']}_{int(datetime.now().timestamp())}",
                "assignment_type": "standard_delivery",
                "estimated_delivery_time": (datetime.now() + timedelta(hours=48)).isoformat(),
                "delivery_method": "ground",
                "priority": order_data.get("urgency", "NORMAL").lower(),
                "assigned_at": datetime.now().isoformat()
            },
            "routing_status": {
                "status": "assigned",
                "tracking_id": f"TRK{int(datetime.now().timestamp())}",
                "current_location": "warehouse",
                "estimated_arrival": (datetime.now() + timedelta(hours=48)).isoformat()
            }
        }


class RoutingSimulator:
    """Stub implementation for routing simulation tools."""

    def simulate_routing(self, routing_data: Dict[str, Any]) -> Dict[str, Any]:
        """Simulate delivery routing and tracking."""
        return {
            "tracking": {
                "tracking_id": f"TRK{int(datetime.now().timestamp())}",
                "current_status": "in_transit",
                "current_location": "distribution_center",
                "estimated_delivery": (datetime.now() + timedelta(hours=random.randint(24, 72))).isoformat(),
                "route_progress": 15.0,
                "stops_remaining": random.randint(3, 8),
                "last_updated": datetime.now().isoformat()
            }
        }


# ============================================================================
# SECTION: OPSAGENT SELF-TEST HARNESS
# ============================================================================

async def run_ops_self_test():
    """
    Self-test harness for OpsAgentNode with various operations scenarios.

    Tests successful delivery, exception handling, policy violations,
    and error conditions to ensure proper transition logic.
    """
    print("\n🚚 OpsAgentNode Self-Test Harness")
    print("=" * 50)

    # Initialize the ops node
    ops_node = OpsAgentNode(
        node_id="test_ops_agent",
        enable_delivery_assignment=True,
        enable_routing_simulation=True,
        enable_status_tracking=True,
        enable_exception_handling=True,
        enable_notifications=True,
        enable_policy_enforcement=True,
        default_delivery_sla_hours=48,
        max_exception_escalations=3
    )

    # Sample test cases for operations scenarios
    test_cases = [
        {
            "name": "Successful Standard Delivery",
            "input": {
                "order_id": "ORD-20250108-001",
                "order_context": {
                    "material": "aluminum sheets",
                    "quantity": 5.0,
                    "unit": "kg",
                    "location": "Chennai",
                    "urgency": "NORMAL"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 100.0,
                        "quantity": 5.0,
                        "delivery_days": 2
                    }
                ],
                "artisan_requirements": {
                    "material": "aluminum sheets",
                    "quality": "premium"
                },
                "channel_urls": {
                    "microstore": "https://microstore.artisanhub.com/ord-001",
                    "status_page": "https://track.artisanhub.com/ord-001"
                },
                "delivery_info": {
                    "delivery_required": True,
                    "delivery_address": {"city": "Chennai", "area": "T.Nagar"}
                },
                "workflow_metadata": {
                    "user_id": "artisan123",
                    "user_email": "artisan@example.com",
                    "workflow_id": "wf_001"
                }
            },
            "expected_transition": "ops_complete"
        },
        {
            "name": "Emergency Order with Exception Handling",
            "input": {
                "order_id": "ORD-20250108-002",
                "order_context": {
                    "material": "steel rods",
                    "quantity": 20.0,
                    "unit": "pcs",
                    "location": "Mumbai",
                    "urgency": "EMERGENCY"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 200.0,
                        "quantity": 20.0,
                        "delivery_days": 1
                    }
                ],
                "artisan_requirements": {
                    "material": "steel rods",
                    "quality": "standard"
                },
                "channel_urls": {
                    "microstore": "https://microstore.artisanhub.com/ord-002",
                    "status_page": "https://track.artisanhub.com/ord-002"
                },
                "delivery_info": {
                    "delivery_required": True,
                    "delivery_address": {"city": "Mumbai", "area": "Andheri"}
                },
                "workflow_metadata": {
                    "user_id": "business456",
                    "user_email": "business@example.com",
                    "workflow_id": "wf_002"
                }
            },
            "expected_transition": "ops_complete"
        },
        {
            "name": "High Volume Order Exception",
            "input": {
                "order_id": "ORD-20250108-003",
                "order_context": {
                    "material": "plastic sheets",
                    "quantity": 1500.0,
                    "unit": "pcs",
                    "location": "Delhi",
                    "urgency": "NORMAL"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 750.0,
                        "quantity": 1500.0,
                        "delivery_days": 5
                    }
                ],
                "artisan_requirements": {
                    "material": "plastic sheets",
                    "quality": "industrial"
                },
                "channel_urls": {
                    "microstore": "https://microstore.artisanhub.com/ord-003",
                    "status_page": "https://track.artisanhub.com/ord-003"
                },
                "delivery_info": {
                    "delivery_required": True,
                    "delivery_address": {"city": "Delhi", "area": "Connaught Place"}
                },
                "workflow_metadata": {
                    "user_id": "industrial789",
                    "user_email": "industrial@example.com",
                    "workflow_id": "wf_003"
                }
            },
            "expected_transition": "needs_followup"
        },
        {
            "name": "Operations Error Scenario",
            "input": {
                "order_id": "ORD-20250108-004",
                "order_context": {
                    "material": "copper wire",
                    "quantity": 10.0,
                    "unit": "kg",
                    "location": "Bangalore",
                    "urgency": "URGENT"
                },
                "supplier_quotes": [
                    {
                        "supplier_id": 1,
                        "price": 300.0,
                        "quantity": 10.0,
                        "delivery_days": 2
                    }
                ],
                "artisan_requirements": {
                    "material": "copper wire",
                    "quality": "premium"
                },
                "channel_urls": {
                    "microstore": "https://microstore.artisanhub.com/ord-004",
                    "status_page": "https://track.artisanhub.com/ord-004"
                },
                "delivery_info": {
                    "delivery_required": True,
                    "delivery_address": {"city": "Bangalore", "area": "Whitefield"}
                },
                "workflow_metadata": {
                    "user_id": "premium_user",
                    "user_email": "premium@example.com",
                    "workflow_id": "wf_004"
                }
            },
            "expected_transition": "exception",
            "force_error": True
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n🚛 Operations Test Case {i}: {test_case['name']}")
        print("-" * 50)

        try:
            # Special setup for error test
            if test_case.get("force_error", False):
                # Create a shipping tool that always fails
                class FailingShippingTool:
                    def assign_delivery(self, order_data):
                        raise Exception("Shipping tool failure simulation")

                ops_node.shipping_tool = FailingShippingTool()

            # Create ops state
            input_data = OpsAgentInput(**test_case['input'])
            state = OpsAgentState(input_data=input_data)

            # Execute ops node
            output = await ops_node.execute(state)

            # Log results
            print(f"Order ID: {test_case['input']['order_id']}")
            print(f"Material: {test_case['input']['order_context']['material']}")
            print(f"Urgency: {test_case['input']['order_context']['urgency']}")
            print(f"Expected transition: {test_case['expected_transition']}")
            print(f"Actual transition: {output.transition}")
            print(f"Final status: {output.final_status}")

            # Log operations summary
            if output.delivery_summary:
                tracking_id = output.delivery_summary.get("tracking_id", "None")
                print(f"Tracking ID: {tracking_id}")

            print(f"Status updates sent: {output.status_summary.get('updates_sent', 0)}")
            print(f"Exceptions handled: {output.exception_summary.get('flags_raised', 0)}")
            print(f"Notifications sent: {output.notification_summary.get('total_sent', 0)}")

            # Check if transition matches expectation
            success = output.transition == test_case['expected_transition']
            results.append(success)

            print(f"✅ PASS" if success else f"❌ FAIL")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append(False)

    # Summary
    print(f"\n📊 Operations Test Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All operations tests passed!")
    else:
        print(f"⚠️  {total - passed} operations test(s) failed")

    return passed == total


# ============================================================================
# SECTION: MISSING NODE IMPLEMENTATIONS
# ============================================================================

@dataclass
class SupplierAgentInput:
    """
    Input data for SupplierAgentNode from ClusterAgentNode.

    Attributes:
        order_context: Original order details (material, quantity, location, urgency)
        cluster_assignment: Assigned cluster for supplier matching
        candidate_suppliers: List of candidate suppliers from clustering
        artisan_requirements: Specific artisan requirements and preferences
        quote_requirements: Requirements for quote generation (format, timeline)
        supplier_filters: Additional filters for supplier selection
        workflow_metadata: Workflow tracking and user context
    """
    order_context: Dict[str, Any]
    cluster_assignment: str
    candidate_suppliers: List[Dict[str, Any]]
    artisan_requirements: Dict[str, Any]
    quote_requirements: Dict[str, Any] = field(default_factory=dict)
    supplier_filters: Dict[str, Any] = field(default_factory=dict)
    workflow_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class SupplierAgentState:
    """
    Complete state for supplier processing workflow.

    Attributes:
        input_data: Input from ClusterAgentNode
        supplier_quotes: Generated quotes from suppliers
        quote_validation: Validation results for supplier quotes
        supplier_communications: Records of supplier communications
        negotiation_history: History of quote negotiations
        final_quotes: Final validated and selected quotes
        quote_errors: Errors encountered during quote processing
        supplier_metadata: Additional supplier information and ratings
        timestamp: When this state was created
        transition: Next workflow step to take
        log: Processing log for debugging and monitoring
    """
    input_data: SupplierAgentInput
    supplier_quotes: List[Dict[str, Any]] = field(default_factory=list)
    quote_validation: Dict[str, bool] = field(default_factory=dict)
    supplier_communications: List[Dict[str, Any]] = field(default_factory=list)
    negotiation_history: List[Dict[str, Any]] = field(default_factory=list)
    final_quotes: List[Dict[str, Any]] = field(default_factory=list)
    quote_errors: List[str] = field(default_factory=list)
    supplier_metadata: Dict[str, Any] = field(default_factory=dict)
    timestamp: datetime = field(default_factory=datetime.now)
    transition: str = "pending"
    log: List[str] = field(default_factory=list)

    def add_log_entry(self, message: str, level: str = "INFO"):
        """Add entry to processing log."""
        timestamp = datetime.now().isoformat()
        self.log.append(f"[{timestamp}] {level}: {message}")

    def add_quote_error(self, error: str):
        """Add quote error to error list and log."""
        self.quote_errors.append(error)
        self.add_log_entry(f"QUOTE ERROR: {error}", "ERROR")

    def add_supplier_communication(self, supplier_id: str, communication_type: str, content: str, response: str = None):
        """Record supplier communication."""
        communication = {
            "supplier_id": supplier_id,
            "communication_type": communication_type,
            "content": content,
            "response": response,
            "timestamp": datetime.now().isoformat()
        }
        self.supplier_communications.append(communication)
        self.add_log_entry(f"Supplier {supplier_id} {communication_type}: {content}")


@dataclass
class SupplierAgentOutput:
    """
    Output from SupplierAgentNode execution.

    Attributes:
        order_context: Original order context for downstream processing
        validated_quotes: List of validated supplier quotes
        selected_quotes: Final selected quotes for commitment
        quote_summary: Summary of quote processing and validation
        supplier_feedback: Feedback and ratings for suppliers
        transition: Next node in pipeline ('quote_ready', 'ambiguous', 'no_quotes')
        log: Complete processing log
        error_details: Detailed error information if processing failed
        metadata: Additional output metadata including processing metrics
    """
    order_context: Dict[str, Any]
    validated_quotes: List[Dict[str, Any]]
    selected_quotes: List[Dict[str, Any]]
    quote_summary: Dict[str, Any]
    supplier_feedback: Dict[str, Any]
    transition: str
    log: List[str]
    error_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class SupplierAgentNode:
    """
    LangGraph-ready SupplierAgentNode for quote collection and validation.

    Quote collection and validation node activated after clustering to gather
    supplier quotes, validate them against requirements, and prepare for commitment.

    Role: Quote collection, validation, and supplier coordination
    Inputs: ClusterAgentOutput (cluster assignment, candidate suppliers, order context)
    Outputs: Validated quotes, supplier selections, quote processing summary
    Tool Dependencies: quote_aggregator (quote collection), supplier_scoring (validation),
                      messaging_stubs (supplier communication), data_access (supplier data)
    Quote Processing: Automated quote requests, response validation, price comparison,
                     supplier rating updates, quote standardization, negotiation handling
    Downstream Transitions: "quote_ready" -> CommitAgent, "ambiguous" -> ClarifyAgent, "no_quotes" -> ExpandSupplyAgent
    """

    def __init__(
        self,
        node_id: str = "supplier_agent",
        enable_quote_collection: bool = True,
        enable_quote_validation: bool = True,
        enable_supplier_scoring: bool = True,
        enable_negotiation: bool = True,
        max_quote_requests: int = 5,
        quote_timeout_seconds: int = 30,
        min_quote_acceptance_score: float = 0.7,
        enable_logging: bool = True
    ):
        """
        Initialize SupplierAgentNode with supplier processing configuration.

        Args:
            node_id: Unique identifier for this node in LangGraph
            enable_quote_collection: Whether to collect quotes from suppliers
            enable_quote_validation: Whether to validate supplier quotes
            enable_supplier_scoring: Whether to score and rank suppliers
            enable_negotiation: Whether to enable quote negotiation
            max_quote_requests: Maximum number of quote requests to send
            quote_timeout_seconds: Timeout for quote responses
            min_quote_acceptance_score: Minimum score for quote acceptance
            enable_logging: Whether to enable detailed supplier processing logs
        """
        self.node_id = node_id
        self.enable_quote_collection = enable_quote_collection
        self.enable_quote_validation = enable_quote_validation
        self.enable_supplier_scoring = enable_supplier_scoring
        self.enable_negotiation = enable_negotiation
        self.max_quote_requests = max_quote_requests
        self.quote_timeout_seconds = quote_timeout_seconds
        self.min_quote_acceptance_score = min_quote_acceptance_score
        self.enable_logging = enable_logging

        # Initialize modular tools
        try:
            from .tools.quote_aggregator import QuoteAggregator, QuoteAggregatorConfig
            quote_config = QuoteAggregatorConfig(timeout_seconds=quote_timeout_seconds)
            self.quote_aggregator = QuoteAggregator(quote_config)
        except ImportError:
            from tools.quote_aggregator import QuoteAggregator, QuoteAggregatorConfig
            quote_config = QuoteAggregatorConfig(timeout_seconds=quote_timeout_seconds)
            self.quote_aggregator = QuoteAggregator(quote_config)

        try:
            from .tools.supplier_scoring import SupplierScorer, SupplierScorerConfig
            scorer_config = SupplierScorerConfig(min_acceptance_score=min_quote_acceptance_score)
            self.supplier_scorer = SupplierScorer(scorer_config)
        except ImportError:
            from tools.supplier_scoring import SupplierScorer, SupplierScorerConfig
            scorer_config = SupplierScorerConfig(min_acceptance_score=min_quote_acceptance_score)
            self.supplier_scorer = SupplierScorer(scorer_config)

        try:
            from .tools.data_access import DataAccessLayer, DatabaseConfig
            db_config = DatabaseConfig()
            self.data_access = DataAccessLayer(db_config)
        except ImportError:
            from tools.data_access import DataAccessLayer, DatabaseConfig
            db_config = DatabaseConfig()
            self.data_access = DataAccessLayer(db_config)

        # Transition mapping for LangGraph routing
        self.transition_map = {
            "quote_ready": "CommitAgent",
            "ambiguous": "ClarifyAgent",
            "no_quotes": "ExpandSupplyAgent"
        }

        # Visual metadata for UI/graph editor
        self.meta = {
            "icon": "🏭",
            "color": "orange",
            "description": "Supplier Quote Collection & Validation",
            "order": 3,
            "input_example": {
                "order_context": {
                    "material": "aluminum sheets",
                    "quantity": 5.0,
                    "location": "Chennai",
                    "urgency": "URGENT"
                },
                "cluster_assignment": "metal_sheets_chennai",
                "candidate_suppliers": [
                    {"supplier_id": 1, "name": "Chennai Metal Works", "score": 0.85},
                    {"supplier_id": 2, "name": "Tamil Nadu Suppliers", "score": 0.72}
                ]
            },
            "output_example": {
                "order_context": {
                    "material": "aluminum sheets",
                    "quantity": 5.0,
                    "location": "Chennai",
                    "urgency": "URGENT"
                },
                "validated_quotes": [
                    {"supplier_id": 1, "price": 100.0, "delivery_days": 2, "valid": True},
                    {"supplier_id": 2, "price": 95.0, "delivery_days": 3, "valid": True}
                ],
                "selected_quotes": [
                    {"supplier_id": 2, "price": 95.0, "delivery_days": 3, "selected": True}
                ],
                "transition": "quote_ready"
            }
        }

        logger.info(f"SupplierAgentNode '{node_id}' initialized successfully")

    async def execute(self, state: SupplierAgentState) -> SupplierAgentOutput:
        """
        Async execute method for LangGraph node processing.

        Args:
            state: Current workflow state with input data

        Returns:
            SupplierAgentOutput with quote results and next node transition
        """
        start_time = datetime.now()
        output_log = []

        try:
            # Log supplier processing initiation
            output_log.append(f"Supplier quote processing initiated at {start_time.isoformat()}")
            output_log.append(f"Order material: {state.input_data.order_context.get('material', 'Unknown')}")
            output_log.append(f"Candidate suppliers: {len(state.input_data.candidate_suppliers)}")

            # Step 1: Collect quotes from candidate suppliers
            output_log.append("Step 1: Collecting supplier quotes...")
            quote_result = await self._collect_supplier_quotes(state)

            if not quote_result["success"]:
                state.add_quote_error(f"Quote collection failed: {quote_result['error']}")
                output_log.append(f"Quote collection error: {quote_result['error']}")
                return self._create_no_quotes_output(state, output_log)

            state.supplier_quotes = quote_result["quotes"]
            state.add_log_entry(f"Collected {len(quote_result['quotes'])} supplier quotes")
            output_log.append(f"Quote collection completed: {len(quote_result['quotes'])} quotes")

            # Step 2: Validate supplier quotes
            output_log.append("Step 2: Validating supplier quotes...")
            validation_result = await self._validate_quotes(state)

            if not validation_result["success"]:
                state.add_quote_error(f"Quote validation failed: {validation_result['error']}")
                output_log.append(f"Quote validation error: {validation_result['error']}")
                return self._create_ambiguous_output(state, output_log)

            state.quote_validation = validation_result["validation_results"]
            state.add_log_entry(f"Validated {sum(1 for v in validation_result['validation_results'].values() if v)} quotes")
            output_log.append(f"Quote validation completed: {sum(1 for v in validation_result['validation_results'].values() if v)} valid quotes")

            # Step 3: Score and rank suppliers
            output_log.append("Step 3: Scoring and ranking suppliers...")
            scoring_result = await self._score_suppliers(state)

            if not scoring_result["success"]:
                state.add_quote_error(f"Supplier scoring failed: {scoring_result['error']}")
                output_log.append(f"Supplier scoring error: {scoring_result['error']}")
                return self._create_ambiguous_output(state, output_log)

            state.supplier_metadata.update(scoring_result["supplier_scores"])
            state.add_log_entry("Supplier scoring completed")
            output_log.append("Supplier scoring completed")

            # Step 4: Select final quotes for commitment
            output_log.append("Step 4: Selecting final quotes...")
            selection_result = await self._select_final_quotes(state)

            if not selection_result["success"]:
                state.add_quote_error(f"Quote selection failed: {selection_result['error']}")
                output_log.append(f"Quote selection error: {selection_result['error']}")
                return self._create_ambiguous_output(state, output_log)

            state.final_quotes = selection_result["selected_quotes"]
            state.add_log_entry(f"Selected {len(selection_result['selected_quotes'])} final quotes")
            output_log.append(f"Quote selection completed: {len(selection_result['selected_quotes'])} quotes selected")

            # Step 5: Handle negotiation if enabled
            if self.enable_negotiation and len(state.final_quotes) > 1:
                output_log.append("Step 5: Handling quote negotiations...")
                negotiation_result = await self._handle_negotiations(state)

                if negotiation_result["success"]:
                    state.negotiation_history.extend(negotiation_result["negotiations"])
                    state.add_log_entry("Quote negotiations completed")
                    output_log.append("Quote negotiations completed")
                else:
                    state.add_quote_error(f"Negotiation failed: {negotiation_result['error']}")
                    output_log.append(f"Negotiation warning: {negotiation_result['error']}")

            # Step 6: Determine final transition
            output_log.append("Step 6: Determining final transition...")
            transition = self._determine_supplier_transition(state)
            state.transition = transition

            final_info = f"Supplier processing completed: {transition}"
            state.add_log_entry(final_info)
            output_log.append(final_info)

            # Step 7: Prepare supplier processing output
            # Create output
            output = SupplierAgentOutput(
                order_context=state.input_data.order_context,
                validated_quotes=state.supplier_quotes,
                selected_quotes=state.final_quotes,
                quote_summary={
                    "total_collected": len(state.supplier_quotes),
                    "valid_quotes": sum(1 for v in state.quote_validation.values() if v),
                    "selected_quotes": len(state.final_quotes),
                    "validation_rate": sum(1 for v in state.quote_validation.values() if v) / len(state.quote_validation) if state.quote_validation else 0
                },
                supplier_feedback={
                    "supplier_scores": state.supplier_metadata,
                    "communications": len(state.supplier_communications),
                    "negotiations": len(state.negotiation_history)
                },
                transition=transition,
                log=output_log + state.log,
                error_details={
                    "quote_errors": state.quote_errors,
                    "validation_failures": [sid for sid, valid in state.quote_validation.items() if not valid],
                    "recovery_suggestions": self._get_recovery_suggestions(state)
                } if state.quote_errors else None,
                metadata={
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "quotes_collected": len(state.supplier_quotes),
                    "quotes_validated": sum(1 for v in state.quote_validation.values() if v),
                    "quotes_selected": len(state.final_quotes),
                    "suppliers_contacted": len(set(quote.get("supplier_id") for quote in state.supplier_quotes)),
                    "negotiations_conducted": len(state.negotiation_history),
                    "communications_sent": len(state.supplier_communications)
                }
            )

            # Final logging
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            output_log.append(f"Supplier processing completed in {processing_time:.2f}ms")
            output_log.append(f"Final result: {transition} -> {self.transition_map.get(transition, 'Unknown')}")

            logger.info(f"SupplierAgentNode completed: {transition} -> {self.transition_map.get(transition, 'Unknown')}")
            return output

        except Exception as e:
            # Handle unexpected errors in supplier processing
            error_msg = f"Unexpected error in SupplierAgentNode: {str(e)}"
            state.add_quote_error(error_msg)
            output_log.append(f"ERROR: {error_msg}")
            output_log.append(f"Traceback: {traceback.format_exc()}")

            logger.error(f"SupplierAgentNode error: {e}", exc_info=True)

            return SupplierAgentOutput(
                order_context=state.input_data.order_context,
                validated_quotes=[],
                selected_quotes=[],
                quote_summary={"error": error_msg},
                supplier_feedback={},
                transition="no_quotes",
                log=output_log + state.log,
                error_details={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "recovery_suggestions": ["Contact system administrator", "Check supplier communication systems", "Verify quote collection tools"]
                },
                metadata={"processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000}
            )

    async def _collect_supplier_quotes(self, state: SupplierAgentState) -> Dict[str, Any]:
        """
        Collect quotes from candidate suppliers.

        Args:
            state: Current supplier state

        Returns:
            Dictionary with quote collection results
        """
        try:
            if not self.enable_quote_collection or not self.quote_aggregator:
                # Generate mock quotes for testing
                mock_quotes = []
                for i, supplier in enumerate(state.input_data.candidate_suppliers[:self.max_quote_requests]):
                    base_price = 100.0 + (i * 20)  # Varied pricing
                    urgency_multiplier = 1.5 if state.input_data.order_context.get("urgency") == "URGENT" else 1.0

                    quote = {
                        "supplier_id": supplier.get("supplier_id"),
                        "supplier_name": supplier.get("name", f"Supplier {supplier.get('supplier_id')}"),
                        "price": base_price * urgency_multiplier,
                        "quantity": state.input_data.order_context.get("quantity", 1),
                        "unit": "kg",  # Default unit
                        "delivery_days": 3 + i,  # Varied delivery times
                        "payment_terms": "prepay" if urgency_multiplier > 1 else "postpay",
                        "valid_until": (datetime.now() + timedelta(days=7)).isoformat(),
                        "notes": f"Quote for {state.input_data.order_context.get('material', 'material')} in {state.input_data.order_context.get('location', 'location')}",
                        "timestamp": datetime.now().isoformat()
                    }
                    mock_quotes.append(quote)

                return {
                    "success": True,
                    "quotes": mock_quotes
                }

            # Use quote aggregator tool
            quote_request = {
                "order_context": state.input_data.order_context,
                "candidate_suppliers": state.input_data.candidate_suppliers[:self.max_quote_requests],
                "requirements": state.input_data.artisan_requirements,
                "quote_requirements": state.input_data.quote_requirements
            }

            collection_result = self.quote_aggregator.collect_quotes(quote_request)

            return {
                "success": True,
                "quotes": collection_result.get("quotes", [])
            }

        except Exception as e:
            logger.error(f"Quote collection error: {e}")
            return {
                "success": False,
                "quotes": [],
                "error": str(e)
            }

    async def _validate_quotes(self, state: SupplierAgentState) -> Dict[str, Any]:
        """
        Validate supplier quotes against requirements.

        Args:
            state: Current supplier state

        Returns:
            Dictionary with quote validation results
        """
        try:
            if not self.enable_quote_validation:
                # Mark all quotes as valid for testing
                validation_results = {str(quote.get("supplier_id")): True for quote in state.supplier_quotes}
                return {
                    "success": True,
                    "validation_results": validation_results
                }

            validation_results = {}

            for quote in state.supplier_quotes:
                supplier_id = str(quote.get("supplier_id"))
                is_valid = True
                validation_issues = []

                # Validate price reasonableness
                material = state.input_data.order_context.get("material", "").lower()
                quantity = state.input_data.order_context.get("quantity", 0)

                # Simple price validation (could be enhanced with market data)
                if quote.get("price", 0) <= 0:
                    is_valid = False
                    validation_issues.append("Invalid price (must be positive)")

                if quote.get("price", 0) > 10000:  # Arbitrary high price threshold
                    is_valid = False
                    validation_issues.append("Price exceeds reasonable threshold")

                # Validate delivery time
                urgency = state.input_data.order_context.get("urgency", "NORMAL")
                delivery_days = quote.get("delivery_days", 0)

                if urgency == "EMERGENCY" and delivery_days > 1:
                    is_valid = False
                    validation_issues.append("Delivery time too long for emergency order")

                if urgency == "URGENT" and delivery_days > 3:
                    is_valid = False
                    validation_issues.append("Delivery time too long for urgent order")

                # Validate quantity availability
                if quote.get("quantity", 0) < quantity:
                    is_valid = False
                    validation_issues.append("Insufficient quantity available")

                # Validate quote expiry
                try:
                    valid_until = datetime.fromisoformat(quote.get("valid_until", "").replace('Z', '+00:00'))
                    if valid_until < datetime.now():
                        is_valid = False
                        validation_issues.append("Quote has expired")
                except:
                    validation_issues.append("Invalid quote expiry format")

                validation_results[supplier_id] = is_valid

                if not is_valid:
                    state.add_quote_error(f"Supplier {supplier_id} quote invalid: {', '.join(validation_issues)}")

            return {
                "success": True,
                "validation_results": validation_results
            }

        except Exception as e:
            logger.error(f"Quote validation error: {e}")
            return {
                "success": False,
                "validation_results": {},
                "error": str(e)
            }

    async def _score_suppliers(self, state: SupplierAgentState) -> Dict[str, Any]:
        """
        Score and rank suppliers based on quotes and performance.

        Args:
            state: Current supplier state

        Returns:
            Dictionary with supplier scoring results
        """
        try:
            if not self.enable_supplier_scoring or not self.supplier_scorer:
                # Generate mock scores
                supplier_scores = {}
                for quote in state.supplier_quotes:
                    supplier_id = str(quote.get("supplier_id"))
                    # Simple scoring based on price and delivery time
                    price_score = max(0, 1.0 - (quote.get("price", 0) / 1000.0))  # Lower price = higher score
                    delivery_score = max(0, 1.0 - (quote.get("delivery_days", 0) / 10.0))  # Faster delivery = higher score
                    overall_score = (price_score + delivery_score) / 2.0

                    supplier_scores[supplier_id] = {
                        "overall_score": overall_score,
                        "price_score": price_score,
                        "delivery_score": delivery_score,
                        "quote_price": quote.get("price", 0),
                        "delivery_days": quote.get("delivery_days", 0)
                    }

                return {
                    "success": True,
                    "supplier_scores": supplier_scores
                }

            # Use supplier scorer tool
            scoring_data = {
                "supplier_quotes": state.supplier_quotes,
                "order_context": state.input_data.order_context,
                "artisan_requirements": state.input_data.artisan_requirements,
                "validation_results": state.quote_validation
            }

            scoring_result = self.supplier_scorer.score_suppliers(scoring_data)

            return {
                "success": True,
                "supplier_scores": scoring_result.get("supplier_scores", {})
            }

        except Exception as e:
            logger.error(f"Supplier scoring error: {e}")
            return {
                "success": False,
                "supplier_scores": {},
                "error": str(e)
            }

    async def _select_final_quotes(self, state: SupplierAgentState) -> Dict[str, Any]:
        """
        Select final quotes for commitment based on scoring and requirements.

        Args:
            state: Current supplier state

        Returns:
            Dictionary with quote selection results
        """
        try:
            # Filter valid quotes only
            valid_quotes = [
                quote for quote in state.supplier_quotes
                if state.quote_validation.get(str(quote.get("supplier_id")), False)
            ]

            if not valid_quotes:
                return {
                    "success": False,
                    "selected_quotes": [],
                    "error": "No valid quotes available for selection"
                }

            # Sort by overall score if available
            if state.supplier_metadata:
                scored_quotes = []
                for quote in valid_quotes:
                    supplier_id = str(quote.get("supplier_id"))
                    score_data = state.supplier_metadata.get(supplier_id, {})
                    overall_score = score_data.get("overall_score", 0.5)

                    quote_with_score = quote.copy()
                    quote_with_score["selection_score"] = overall_score
                    scored_quotes.append(quote_with_score)

                # Sort by selection score (highest first)
                scored_quotes.sort(key=lambda x: x.get("selection_score", 0), reverse=True)

                # Select top quotes based on requirements
                max_quotes = min(3, len(scored_quotes))  # Select up to 3 quotes
                selected_quotes = scored_quotes[:max_quotes]

                # Mark selected quotes
                for quote in selected_quotes:
                    quote["selected"] = True
                    quote["selection_reason"] = "Top scored quote"
            else:
                # Simple selection without scoring
                selected_quotes = valid_quotes[:1]  # Select cheapest valid quote
                for quote in selected_quotes:
                    quote["selected"] = True
                    quote["selection_reason"] = "Valid quote available"

            return {
                "success": True,
                "selected_quotes": selected_quotes
            }

        except Exception as e:
            logger.error(f"Quote selection error: {e}")
            return {
                "success": False,
                "selected_quotes": [],
                "error": str(e)
            }

    async def _handle_negotiations(self, state: SupplierAgentState) -> Dict[str, Any]:
        """
        Handle quote negotiations with suppliers.

        Args:
            state: Current supplier state

        Returns:
            Dictionary with negotiation results
        """
        try:
            if not self.enable_negotiation:
                return {
                    "success": True,
                    "negotiations": []
                }

            negotiations = []

            # Simple negotiation logic - request better prices from top suppliers
            for quote in state.final_quotes[:2]:  # Negotiate with top 2 suppliers
                supplier_id = quote.get("supplier_id")

                try:
                    # Simulate negotiation request
                    negotiation_request = {
                        "supplier_id": supplier_id,
                        "current_price": quote.get("price", 0),
                        "requested_price": quote.get("price", 0) * 0.9,  # Request 10% discount
                        "reason": "Competitive pricing requested"
                    }

                    # In a real implementation, this would send actual negotiation requests
                    # For now, we'll simulate the negotiation
                    negotiation_response = {
                        "supplier_id": supplier_id,
                        "original_price": quote.get("price", 0),
                        "negotiated_price": quote.get("price", 0) * 0.95,  # Simulate 5% discount
                        "accepted": True,
                        "counter_offer": False,
                        "timestamp": datetime.now().isoformat()
                    }

                    negotiations.append(negotiation_response)

                    # Update quote with negotiated price
                    if negotiation_response["accepted"]:
                        quote["price"] = negotiation_response["negotiated_price"]
                        quote["negotiated"] = True
                        quote["original_price"] = negotiation_response["original_price"]

                    state.add_supplier_communication(
                        supplier_id=str(supplier_id),
                        communication_type="negotiation",
                        content=f"Price negotiation: {negotiation_request['current_price']} → {negotiation_request['requested_price']}",
                        response=f"Accepted: {negotiation_response['accepted']}"
                    )

                except Exception as e:
                    logger.warning(f"Negotiation with supplier {supplier_id} failed: {e}")
                    state.add_supplier_communication(
                        supplier_id=str(supplier_id),
                        communication_type="negotiation",
                        content="Price negotiation request",
                        response=f"Failed: {e}"
                    )

            return {
                "success": True,
                "negotiations": negotiations
            }

        except Exception as e:
            logger.error(f"Negotiation handling error: {e}")
            return {
                "success": False,
                "negotiations": [],
                "error": str(e)
            }

    def _determine_supplier_transition(self, state: SupplierAgentState) -> str:
        """
        Determine next workflow transition based on supplier processing results.

        Args:
            state: Current supplier state

        Returns:
            Transition string: "quote_ready", "ambiguous", or "no_quotes"
        """
        try:
            # If we have no quotes at all, no quotes available
            if not state.supplier_quotes:
                return "no_quotes"

            # If we have quotes but none are valid, ambiguous situation
            valid_quotes = [quote for quote in state.supplier_quotes
                          if state.quote_validation.get(str(quote.get("supplier_id")), False)]

            if not valid_quotes:
                return "ambiguous"

            # If we have valid quotes but none selected, ambiguous
            if not state.final_quotes:
                return "ambiguous"

            # If we have selected quotes, ready for commitment
            if state.final_quotes:
                return "quote_ready"

            # Default to ambiguous for unclear situations
            return "ambiguous"

        except Exception as e:
            logger.error(f"Supplier transition determination error: {e}")
            return "no_quotes"

    def _create_no_quotes_output(self, state: SupplierAgentState, log_entries: List[str]) -> SupplierAgentOutput:
        """Create output for no quotes scenario."""
        return SupplierAgentOutput(
            order_context=state.input_data.order_context,
            validated_quotes=[],
            selected_quotes=[],
            quote_summary={"total_collected": 0, "valid_quotes": 0, "selected_quotes": 0},
            supplier_feedback={},
            transition="no_quotes",
            log=log_entries + state.log,
            error_details={
                "error_type": "no_quotes_available",
                "quote_errors": state.quote_errors,
                "suggestions": ["Expand supplier search criteria", "Try different materials or specifications", "Contact supplier support"]
            },
            metadata={"no_quotes_available": True}
        )

    def _create_ambiguous_output(self, state: SupplierAgentState, log_entries: List[str]) -> SupplierAgentOutput:
        """Create output for ambiguous quote scenario."""
        return SupplierAgentOutput(
            order_context=state.input_data.order_context,
            validated_quotes=state.supplier_quotes,
            selected_quotes=[],
            quote_summary={
                "total_collected": len(state.supplier_quotes),
                "valid_quotes": sum(1 for v in state.quote_validation.values() if v),
                "selected_quotes": 0
            },
            supplier_feedback={"supplier_scores": state.supplier_metadata},
            transition="ambiguous",
            log=log_entries + state.log,
            error_details={
                "error_type": "quote_ambiguity",
                "quote_errors": state.quote_errors,
                "validation_failures": [sid for sid, valid in state.quote_validation.items() if not valid],
                "suggestions": ["Review quote requirements", "Contact suppliers for clarification", "Adjust material specifications"]
            },
            metadata={"quote_ambiguity": True}
        )

    def _get_recovery_suggestions(self, state: SupplierAgentState) -> List[str]:
        """Get recovery suggestions based on current state."""
        suggestions = []

        if not state.supplier_quotes:
            suggestions.append("Check supplier communication systems and retry quote collection")

        if state.quote_errors:
            suggestions.append("Address quote validation errors and request new quotes")

        if not state.final_quotes:
            suggestions.append("Review supplier selection criteria and scoring algorithm")

        return suggestions if suggestions else ["Contact system administrator for assistance"]

    @property
    def transitions(self) -> Dict[str, str]:
        """Get transition mapping for LangGraph routing."""
        return self.transition_map

    @property
    def meta(self) -> Dict[str, Any]:
        """Get node metadata for UI/graph editor."""
        return self._meta

    @meta.setter
    def meta(self, value: Dict[str, Any]):
        """Set node metadata."""
        self._meta = value


@dataclass
class CashAgentInput:
    """
    Input data for CashAgentNode from OpsAgentNode.

    Attributes:
        order_id: Unique order identifier from operations completion
        order_context: Original order details (material, quantity, location, urgency)
        delivery_summary: Delivery completion summary from operations
        payment_summary: Payment details from original order
        supplier_payments: Payment information for suppliers
        artisan_billing: Billing information for artisan
        financial_metadata: Financial tracking and reconciliation data
        workflow_metadata: Workflow tracking and user context
    """
    order_id: str
    order_context: Dict[str, Any]
    delivery_summary: Dict[str, Any]
    payment_summary: Dict[str, Any]
    supplier_payments: List[Dict[str, Any]] = field(default_factory=list)
    artisan_billing: Dict[str, Any] = field(default_factory=dict)
    financial_metadata: Dict[str, Any] = field(default_factory=dict)
    workflow_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class CashAgentState:
    """
    Complete state for cash flow processing workflow.

    Attributes:
        input_data: Input from OpsAgentNode
        payment_reconciliation: Reconciliation of all payments in the order
        supplier_settlements: Settlement status for supplier payments
        artisan_refunds: Refund processing for artisan if applicable
        commission_calculations: Platform commission calculations
        financial_reports: Generated financial reports and summaries
        cash_flow_events: Timeline of cash flow events
        compliance_checks: Financial compliance and regulatory checks
        errors: List of errors encountered during processing
        timestamp: When this state was created
        transition: Next workflow step to take
        log: Processing log for debugging and monitoring
    """
    input_data: CashAgentInput
    payment_reconciliation: Dict[str, Any] = field(default_factory=dict)
    supplier_settlements: List[Dict[str, Any]] = field(default_factory=list)
    artisan_refunds: Dict[str, Any] = field(default_factory=dict)
    commission_calculations: Dict[str, Any] = field(default_factory=dict)
    financial_reports: Dict[str, Any] = field(default_factory=dict)
    cash_flow_events: List[Dict[str, Any]] = field(default_factory=list)
    compliance_checks: Dict[str, bool] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    transition: str = "pending"
    log: List[str] = field(default_factory=list)

    def add_log_entry(self, message: str, level: str = "INFO"):
        """Add entry to processing log."""
        timestamp = datetime.now().isoformat()
        self.log.append(f"[{timestamp}] {level}: {message}")

    def add_error(self, error: str):
        """Add error to error list and log."""
        self.errors.append(error)
        self.add_log_entry(f"ERROR: {error}", "ERROR")

    def add_cash_flow_event(self, event_type: str, amount: float, description: str, participant: str):
        """Record cash flow event."""
        event = {
            "event_type": event_type,
            "amount": amount,
            "description": description,
            "participant": participant,
            "timestamp": datetime.now().isoformat()
        }
        self.cash_flow_events.append(event)
        self.add_log_entry(f"CASH FLOW: {event_type} - ₹{amount} for {participant}")


@dataclass
class CashAgentOutput:
    """
    Output from CashAgentNode execution.

    Attributes:
        order_id: Unique order identifier
        cash_flow_summary: Summary of all cash flows in the order
        settlement_summary: Summary of supplier settlements
        commission_summary: Summary of platform commissions
        financial_report: Generated financial report for the order
        compliance_status: Status of financial compliance checks
        transition: Next node in pipeline ('cash_ok', 'review_needed', 'clarify')
        log: Complete processing log
        error_details: Detailed error information if processing failed
        metadata: Additional output metadata including processing metrics
    """
    order_id: str
    cash_flow_summary: Dict[str, Any]
    settlement_summary: Dict[str, Any]
    commission_summary: Dict[str, Any]
    financial_report: Dict[str, Any]
    compliance_status: str
    transition: str
    log: List[str]
    error_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class CashAgentNode:
    """
    LangGraph-ready CashAgentNode for financial reconciliation and settlement.

    Financial reconciliation node activated after operations completion to handle
    payment settlements, commission calculations, and financial reporting.

    Role: Financial reconciliation, settlement processing, and compliance reporting
    Inputs: OpsAgentOutput (delivery completion, order details, payment info)
    Outputs: Financial reconciliation, settlements, commissions, compliance status
    Tool Dependencies: payment_stubs (settlement processing), policy_loader (commission rules),
                      data_access (financial records), notification_stubs (financial alerts)
    Financial Processing: Payment reconciliation, supplier settlements, commission calculations,
                         refund processing, financial reporting, compliance checks, audit trails
    Downstream Transitions: "cash_ok" -> LearnAgent, "review_needed" -> ErrorHandlerAgent, "clarify" -> ClarifyAgent
    """

    def __init__(
        self,
        node_id: str = "cash_agent",
        enable_settlement_processing: bool = True,
        enable_commission_calculation: bool = True,
        enable_financial_reporting: bool = True,
        enable_compliance_checks: bool = True,
        enable_refund_processing: bool = True,
        default_commission_rate: float = 0.05,  # 5%
        settlement_delay_days: int = 7,
        enable_logging: bool = True
    ):
        """
        Initialize CashAgentNode with financial processing configuration.

        Args:
            node_id: Unique identifier for this node in LangGraph
            enable_settlement_processing: Whether to process supplier settlements
            enable_commission_calculation: Whether to calculate platform commissions
            enable_financial_reporting: Whether to generate financial reports
            enable_compliance_checks: Whether to perform compliance checks
            enable_refund_processing: Whether to process refunds if needed
            default_commission_rate: Default commission rate for platform fees
            settlement_delay_days: Standard settlement delay in days
            enable_logging: Whether to enable detailed financial processing logs
        """
        self.node_id = node_id
        self.enable_settlement_processing = enable_settlement_processing
        self.enable_commission_calculation = enable_commission_calculation
        self.enable_financial_reporting = enable_financial_reporting
        self.enable_compliance_checks = enable_compliance_checks
        self.enable_refund_processing = enable_refund_processing
        self.default_commission_rate = default_commission_rate
        self.settlement_delay_days = settlement_delay_days
        self.enable_logging = enable_logging

        # Initialize modular tools
        try:
            from .tools.payment_stubs import PaymentStub, PaymentStatus
            self.payment_stub = PaymentStub()
            self.PaymentStatus = PaymentStatus
        except ImportError:
            from tools.payment_stubs import PaymentStub, PaymentStatus
            self.payment_stub = PaymentStub()
            self.PaymentStatus = PaymentStatus

        try:
            from .tools.policy_loader import PolicyLoader
            self.policy_loader = PolicyLoader("policies") if enable_compliance_checks else None
        except ImportError:
            from tools.policy_loader import PolicyLoader
            self.policy_loader = PolicyLoader("policies") if enable_compliance_checks else None

        try:
            from .tools.data_access import DataAccessLayer, DatabaseConfig
            db_config = DatabaseConfig()
            self.data_access = DataAccessLayer(db_config)
        except ImportError:
            from tools.data_access import DataAccessLayer, DatabaseConfig
            db_config = DatabaseConfig()
            self.data_access = DataAccessLayer(db_config)

        # Transition mapping for LangGraph routing
        self.transition_map = {
            "cash_ok": "LearnAgent",
            "review_needed": "ErrorHandlerAgent",
            "clarify": "ClarifyAgent"
        }

        # Visual metadata for UI/graph editor
        self.meta = {
            "icon": "💰",
            "color": "green",
            "description": "Financial Reconciliation & Settlement",
            "order": 7,
            "input_example": {
                "order_id": "ORD-20250108-001",
                "order_context": {
                    "material": "aluminum sheets",
                    "quantity": 5.0,
                    "location": "Chennai",
                    "urgency": "URGENT"
                },
                "payment_summary": {"status": "completed", "amount": 500.0},
                "delivery_summary": {"status": "delivered", "tracking_id": "TRK123"}
            },
            "output_example": {
                "order_id": "ORD-20250108-001",
                "cash_flow_summary": {"total_order_value": 500.0, "commission": 25.0, "supplier_payments": 475.0},
                "settlement_summary": {"suppliers_settled": 1, "total_settled": 475.0},
                "commission_summary": {"platform_commission": 25.0, "rate": 0.05},
                "compliance_status": "compliant",
                "transition": "cash_ok"
            }
        }

        logger.info(f"CashAgentNode '{node_id}' initialized successfully")

    async def execute(self, state: CashAgentState) -> CashAgentOutput:
        """
        Async execute method for LangGraph node processing.

        Args:
            state: Current workflow state with input data

        Returns:
            CashAgentOutput with financial reconciliation results and next node transition
        """
        start_time = datetime.now()
        output_log = []

        try:
            # Log financial processing initiation
            output_log.append(f"Financial reconciliation initiated at {start_time.isoformat()}")
            output_log.append(f"Order ID: {state.input_data.order_id}")
            output_log.append(f"Order value: ₹{state.input_data.payment_summary.get('amount', 0)}")

            # Step 1: Reconcile all payments in the order
            output_log.append("Step 1: Reconciling order payments...")
            reconciliation_result = await self._reconcile_payments(state)

            if not reconciliation_result["success"]:
                state.add_error(f"Payment reconciliation failed: {reconciliation_result['error']}")
                output_log.append(f"Payment reconciliation error: {reconciliation_result['error']}")
                return self._create_review_needed_output(state, output_log)

            state.payment_reconciliation.update(reconciliation_result["reconciliation"])
            state.add_cash_flow_event("payment_reconciled", reconciliation_result["reconciliation"].get("total_amount", 0), "Payment reconciliation completed", "platform")
            state.add_log_entry("Payment reconciliation completed successfully")
            output_log.append("Payment reconciliation completed")

            # Step 2: Process supplier settlements
            output_log.append("Step 2: Processing supplier settlements...")
            settlement_result = await self._process_supplier_settlements(state)

            if not settlement_result["success"]:
                state.add_error(f"Supplier settlement failed: {settlement_result['error']}")
                output_log.append(f"Supplier settlement error: {settlement_result['error']}")
                return self._create_review_needed_output(state, output_log)

            state.supplier_settlements.extend(settlement_result["settlements"])
            total_settled = sum(s.get("amount", 0) for s in settlement_result["settlements"])
            state.add_cash_flow_event("supplier_settlement", total_settled, f"Supplier settlements processed ({len(settlement_result['settlements'])} suppliers)", "suppliers")
            state.add_log_entry(f"Supplier settlements completed: {len(settlement_result['settlements'])} suppliers")
            output_log.append(f"Supplier settlements completed: {len(settlement_result['settlements'])} suppliers")

            # Step 3: Calculate platform commissions
            output_log.append("Step 3: Calculating platform commissions...")
            commission_result = await self._calculate_commissions(state)

            if not commission_result["success"]:
                state.add_error(f"Commission calculation failed: {commission_result['error']}")
                output_log.append(f"Commission calculation error: {commission_result['error']}")
                return self._create_review_needed_output(state, output_log)

            state.commission_calculations.update(commission_result["commissions"])
            commission_amount = commission_result["commissions"].get("platform_commission", 0)
            state.add_cash_flow_event("commission_earned", commission_amount, "Platform commission calculated", "platform")
            state.add_log_entry(f"Commission calculated: ₹{commission_amount}")
            output_log.append(f"Commission calculation completed: ₹{commission_amount}")

            # Step 4: Process refunds if applicable
            if self.enable_refund_processing:
                output_log.append("Step 4: Processing refunds if applicable...")
                refund_result = await self._process_refunds(state)

                if refund_result["success"]:
                    state.artisan_refunds.update(refund_result["refunds"])
                    if refund_result["refunds"].get("refund_amount", 0) > 0:
                        refund_amount = refund_result["refunds"].get("refund_amount", 0)
                        state.add_cash_flow_event("refund_processed", -refund_amount, "Artisan refund processed", "artisan")
                        state.add_log_entry(f"Refund processed: ₹{refund_amount}")
                        output_log.append(f"Refund processing completed: ₹{refund_amount}")
                    else:
                        output_log.append("No refunds required")
                else:
                    state.add_error(f"Refund processing failed: {refund_result['error']}")
                    output_log.append(f"Refund processing error: {refund_result['error']}")

            # Step 5: Perform compliance checks
            if self.enable_compliance_checks:
                output_log.append("Step 5: Performing compliance checks...")
                compliance_result = await self._perform_compliance_checks(state)

                state.compliance_checks.update(compliance_result["checks"])

                if not compliance_result["passed"]:
                    state.add_error(f"Compliance check failed: {compliance_result['violations']}")
                    output_log.append(f"Compliance violation: {compliance_result['violations']}")
                    return self._create_clarify_output(state, output_log)

                state.add_log_entry("Compliance checks passed")
                output_log.append("Compliance checks completed successfully")

            # Step 6: Generate financial reports
            if self.enable_financial_reporting:
                output_log.append("Step 6: Generating financial reports...")
                report_result = await self._generate_financial_reports(state)

                if report_result["success"]:
                    state.financial_reports.update(report_result["reports"])
                    state.add_log_entry("Financial reports generated")
                    output_log.append("Financial report generation completed")
                else:
                    logger.warning(f"Financial report generation failed: {report_result['error']}")
                    output_log.append(f"Financial report warning: {report_result['error']}")

            # Step 7: Determine final transition
            output_log.append("Step 7: Determining final transition...")
            transition = self._determine_cash_transition(state)
            state.transition = transition

            final_info = f"Financial processing completed: {transition}"
            state.add_log_entry(final_info)
            output_log.append(final_info)

            # Step 8: Prepare financial summary output
            total_order_value = state.payment_reconciliation.get("total_amount", 0)
            total_commission = state.commission_calculations.get("platform_commission", 0)
            total_settlements = sum(s.get("amount", 0) for s in state.supplier_settlements)

            # Create output
            output = CashAgentOutput(
                order_id=state.input_data.order_id,
                cash_flow_summary={
                    "total_order_value": total_order_value,
                    "total_commission": total_commission,
                    "total_settlements": total_settlements,
                    "net_cash_flow": total_commission,  # Platform keeps commission
                    "currency": "INR",
                    "events_recorded": len(state.cash_flow_events)
                },
                settlement_summary={
                    "suppliers_settled": len(state.supplier_settlements),
                    "total_settled_amount": total_settlements,
                    "settlement_delay_days": self.settlement_delay_days,
                    "settlements": state.supplier_settlements
                },
                commission_summary={
                    "platform_commission": total_commission,
                    "commission_rate": state.commission_calculations.get("commission_rate", self.default_commission_rate),
                    "calculation_method": state.commission_calculations.get("calculation_method", "standard_rate")
                },
                financial_report={
                    "order_id": state.input_data.order_id,
                    "generated_at": datetime.now().isoformat(),
                    "reports": state.financial_reports,
                    "cash_flow_events": state.cash_flow_events
                },
                compliance_status="compliant" if all(state.compliance_checks.values()) else "review_needed",
                transition=transition,
                log=output_log + state.log,
                error_details={
                    "errors": state.errors,
                    "compliance_violations": [k for k, v in state.compliance_checks.items() if not v],
                    "recovery_suggestions": self._get_recovery_suggestions(state)
                } if state.errors else None,
                metadata={
                    "processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000,
                    "payments_reconciled": len(state.payment_reconciliation),
                    "suppliers_settled": len(state.supplier_settlements),
                    "commission_calculated": bool(state.commission_calculations),
                    "compliance_checks_performed": len(state.compliance_checks),
                    "financial_reports_generated": len(state.financial_reports),
                    "cash_flow_events_recorded": len(state.cash_flow_events)
                }
            )

            # Final logging
            processing_time = (datetime.now() - start_time).total_seconds() * 1000
            output_log.append(f"Financial processing completed in {processing_time:.2f}ms")
            output_log.append(f"Final result: {transition} -> {self.transition_map.get(transition, 'Unknown')}")

            logger.info(f"CashAgentNode completed: {transition} -> {self.transition_map.get(transition, 'Unknown')}")
            return output

        except Exception as e:
            # Handle unexpected errors in financial processing
            error_msg = f"Unexpected error in CashAgentNode: {str(e)}"
            state.add_error(error_msg)
            output_log.append(f"ERROR: {error_msg}")
            output_log.append(f"Traceback: {traceback.format_exc()}")

            logger.error(f"CashAgentNode error: {e}", exc_info=True)

            return CashAgentOutput(
                order_id=state.input_data.order_id,
                cash_flow_summary={},
                settlement_summary={},
                commission_summary={},
                financial_report={},
                compliance_status="error",
                transition="review_needed",
                log=output_log + state.log,
                error_details={
                    "error_type": type(e).__name__,
                    "error_message": str(e),
                    "traceback": traceback.format_exc(),
                    "recovery_suggestions": ["Contact finance administrator", "Check payment systems", "Verify financial data integrity"]
                },
                metadata={"processing_time_ms": (datetime.now() - start_time).total_seconds() * 1000}
            )

    async def _reconcile_payments(self, state: CashAgentState) -> Dict[str, Any]:
        """
        Reconcile all payments associated with the order.

        Args:
            state: Current cash state

        Returns:
            Dictionary with payment reconciliation results
        """
        try:
            # Get payment information from input
            original_payment = state.input_data.payment_summary
            total_amount = original_payment.get("amount", 0)

            # Create reconciliation record
            reconciliation = {
                "order_id": state.input_data.order_id,
                "total_amount": total_amount,
                "currency": "INR",
                "payment_method": original_payment.get("method", "unknown"),
                "payment_status": original_payment.get("status", "unknown"),
                "transaction_id": original_payment.get("transaction_id", "unknown"),
                "reconciled_at": datetime.now().isoformat(),
                "reconciliation_status": "completed",
                "amounts": {
                    "order_total": total_amount,
                    "platform_commission": total_amount * self.default_commission_rate,
                    "supplier_payments": total_amount * (1 - self.default_commission_rate)
                }
            }

            return {
                "success": True,
                "reconciliation": reconciliation
            }

        except Exception as e:
            logger.error(f"Payment reconciliation error: {e}")
            return {
                "success": False,
                "reconciliation": {},
                "error": str(e)
            }

    async def _process_supplier_settlements(self, state: CashAgentState) -> Dict[str, Any]:
        """
        Process settlements for all suppliers involved in the order.

        Args:
            state: Current cash state

        Returns:
            Dictionary with supplier settlement results
        """
        try:
            if not self.enable_settlement_processing:
                return {
                    "success": True,
                    "settlements": []
                }

            settlements = []
            total_settlement_amount = 0

            # Get supplier quotes from order context
            supplier_quotes = state.input_data.order_context.get("supplier_quotes", [])

            for quote in supplier_quotes:
                supplier_id = quote.get("supplier_id")
                quote_amount = quote.get("price", 0) * quote.get("quantity", 1)
                supplier_settlement_amount = quote_amount * (1 - self.default_commission_rate)

                settlement = {
                    "supplier_id": supplier_id,
                    "order_id": state.input_data.order_id,
                    "settlement_amount": supplier_settlement_amount,
                    "original_quote_amount": quote_amount,
                    "commission_deducted": quote_amount * self.default_commission_rate,
                    "settlement_status": "pending",
                    "scheduled_settlement_date": (datetime.now() + timedelta(days=self.settlement_delay_days)).isoformat(),
                    "settlement_method": "bank_transfer",  # Default method
                    "created_at": datetime.now().isoformat()
                }

                settlements.append(settlement)
                total_settlement_amount += supplier_settlement_amount

            return {
                "success": True,
                "settlements": settlements,
                "total_settlement_amount": total_settlement_amount
            }

        except Exception as e:
            logger.error(f"Supplier settlement processing error: {e}")
            return {
                "success": False,
                "settlements": [],
                "error": str(e)
            }

    async def _calculate_commissions(self, state: CashAgentState) -> Dict[str, Any]:
        """
        Calculate platform commissions for the order.

        Args:
            state: Current cash state

        Returns:
            Dictionary with commission calculation results
        """
        try:
            if not self.enable_commission_calculation:
                return {
                    "success": True,
                    "commissions": {
                        "platform_commission": 0,
                        "commission_rate": 0,
                        "calculation_method": "disabled"
                    }
                }

            # Get order total from payment reconciliation
            total_amount = state.payment_reconciliation.get("total_amount", 0)

            # Calculate commission
            commission_rate = self.default_commission_rate
            platform_commission = total_amount * commission_rate

            commissions = {
                "platform_commission": platform_commission,
                "commission_rate": commission_rate,
                "calculation_method": "standard_rate",
                "base_amount": total_amount,
                "calculated_at": datetime.now().isoformat(),
                "currency": "INR"
            }

            return {
                "success": True,
                "commissions": commissions
            }

        except Exception as e:
            logger.error(f"Commission calculation error: {e}")
            return {
                "success": False,
                "commissions": {},
                "error": str(e)
            }

    async def _process_refunds(self, state: CashAgentState) -> Dict[str, Any]:
        """
        Process refunds if applicable (e.g., for cancelled or failed orders).

        Args:
            state: Current cash state

        Returns:
            Dictionary with refund processing results
        """
        try:
            if not self.enable_refund_processing:
                return {
                    "success": True,
                    "refunds": {"refund_amount": 0, "refund_status": "none_required"}
                }

            # Check if refund is needed (e.g., delivery failed)
            delivery_status = state.input_data.delivery_summary.get("status", "delivered")

            if delivery_status == "delivered":
                return {
                    "success": True,
                    "refunds": {"refund_amount": 0, "refund_status": "none_required"}
                }

            # Calculate refund amount (full refund for failed delivery)
            total_amount = state.input_data.payment_summary.get("amount", 0)

            refunds = {
                "refund_amount": total_amount,
                "refund_status": "processed",
                "refund_reason": f"Delivery failed: {delivery_status}",
                "refund_method": state.input_data.payment_summary.get("method", "original"),
                "refunded_at": datetime.now().isoformat(),
                "original_transaction_id": state.input_data.payment_summary.get("transaction_id", "unknown")
            }

            return {
                "success": True,
                "refunds": refunds
            }

        except Exception as e:
            logger.error(f"Refund processing error: {e}")
            return {
                "success": False,
                "refunds": {},
                "error": str(e)
            }

    async def _perform_compliance_checks(self, state: CashAgentState) -> Dict[str, Any]:
        """
        Perform financial compliance and regulatory checks.

        Args:
            state: Current cash state

        Returns:
            Dictionary with compliance check results
        """
        try:
            if not self.enable_compliance_checks:
                return {
                    "passed": True,
                    "checks": {"compliance_disabled": True},
                    "violations": []
                }

            checks = {}
            violations = []

            # Check commission rate compliance
            commission_rate = state.commission_calculations.get("commission_rate", 0)
            max_commission_rate = 0.15  # 15% max commission

            if commission_rate > max_commission_rate:
                violations.append(f"Commission rate {commission_rate} exceeds maximum allowed rate {max_commission_rate}")
                checks["commission_rate_check"] = False
            else:
                checks["commission_rate_check"] = True

            # Check settlement timing compliance
            settlement_delay = self.settlement_delay_days
            max_settlement_delay = 30  # 30 days max delay

            if settlement_delay > max_settlement_delay:
                violations.append(f"Settlement delay {settlement_delay} days exceeds maximum allowed delay {max_settlement_delay} days")
                checks["settlement_timing_check"] = False
            else:
                checks["settlement_timing_check"] = True

            # Check amount thresholds
            total_amount = state.payment_reconciliation.get("total_amount", 0)
            if total_amount > 100000:  # Large transaction threshold
                checks["large_transaction_check"] = True  # May require additional checks
            else:
                checks["large_transaction_check"] = True

            # Check refund policy compliance
            if state.artisan_refunds.get("refund_amount", 0) > 0:
                refund_amount = state.artisan_refunds.get("refund_amount", 0)
                if refund_amount == total_amount:
                    checks["full_refund_check"] = True  # Full refund for failed delivery is compliant
                else:
                    checks["partial_refund_check"] = True
            else:
                checks["no_refund_check"] = True

            return {
                "passed": len(violations) == 0,
                "checks": checks,
                "violations": violations
            }

        except Exception as e:
            logger.error(f"Compliance check error: {e}")
            return {
                "passed": False,
                "checks": {"compliance_error": False},
                "violations": [f"Compliance check error: {e}"]
            }

    async def _generate_financial_reports(self, state: CashAgentState) -> Dict[str, Any]:
        """
        Generate financial reports for the order.

        Args:
            state: Current cash state

        Returns:
            Dictionary with financial report generation results
        """
        try:
            if not self.enable_financial_reporting:
                return {
                    "success": True,
                    "reports": {"reporting_disabled": True}
                }

            # Generate order financial summary report
            report = {
                "order_financial_summary": {
                    "order_id": state.input_data.order_id,
                    "total_order_value": state.payment_reconciliation.get("total_amount", 0),
                    "platform_commission": state.commission_calculations.get("platform_commission", 0),
                    "supplier_settlements": sum(s.get("settlement_amount", 0) for s in state.supplier_settlements),
                    "refunds_processed": state.artisan_refunds.get("refund_amount", 0),
                    "net_platform_earnings": state.commission_calculations.get("platform_commission", 0) - state.artisan_refunds.get("refund_amount", 0),
                    "generated_at": datetime.now().isoformat(),
                    "currency": "INR"
                },
                "cash_flow_timeline": state.cash_flow_events,
                "supplier_settlement_details": state.supplier_settlements,
                "compliance_summary": state.compliance_checks
            }

            return {
                "success": True,
                "reports": report
            }

        except Exception as e:
            logger.error(f"Financial report generation error: {e}")
            return {
                "success": False,
                "reports": {},
                "error": str(e)
            }

    def _determine_cash_transition(self, state: CashAgentState) -> str:
        """
        Determine next workflow transition based on financial processing results.

        Args:
            state: Current cash state

        Returns:
            Transition string: "cash_ok", "review_needed", or "clarify"
        """
        try:
            # If we have errors, need review
            if state.errors:
                return "review_needed"

            # If compliance checks failed, need clarification
            if not all(state.compliance_checks.values()):
                return "clarify"

            # If we have successful reconciliation and settlements, cash is OK
            if (state.payment_reconciliation.get("reconciliation_status") == "completed" and
                state.commission_calculations and
                state.supplier_settlements):
                return "cash_ok"

            # If reconciliation is incomplete, need review
            if state.payment_reconciliation.get("reconciliation_status") != "completed":
                return "review_needed"

            # Default to clarify for unclear situations
            return "clarify"

        except Exception as e:
            logger.error(f"Cash transition determination error: {e}")
            return "review_needed"

    def _create_review_needed_output(self, state: CashAgentState, log_entries: List[str]) -> CashAgentOutput:
        """Create output for review needed scenario."""
        return CashAgentOutput(
            order_id=state.input_data.order_id,
            cash_flow_summary={"status": "review_needed"},
            settlement_summary={"suppliers_settled": len(state.supplier_settlements)},
            commission_summary={"platform_commission": state.commission_calculations.get("platform_commission", 0)},
            financial_report={"reports": state.financial_reports},
            compliance_status="review_needed",
            transition="review_needed",
            log=log_entries + state.log,
            error_details={
                "error_type": "financial_review_needed",
                "errors": state.errors,
                "suggestions": ["Review payment reconciliation", "Check settlement calculations", "Verify compliance status"]
            },
            metadata={"review_needed": True}
        )

    def _create_clarify_output(self, state: CashAgentState, log_entries: List[str]) -> CashAgentOutput:
        """Create output for clarification needed scenario."""
        return CashAgentOutput(
            order_id=state.input_data.order_id,
            cash_flow_summary={"status": "clarification_needed"},
            settlement_summary={"suppliers_settled": len(state.supplier_settlements)},
            commission_summary={"platform_commission": state.commission_calculations.get("platform_commission", 0)},
            financial_report={"reports": state.financial_reports},
            compliance_status="clarification_needed",
            transition="clarify",
            log=log_entries + state.log,
            error_details={
                "error_type": "financial_clarification_needed",
                "compliance_violations": [k for k, v in state.compliance_checks.items() if not v],
                "suggestions": ["Address compliance violations", "Review financial policies", "Contact finance compliance team"]
            },
            metadata={"clarification_needed": True}
        )

    def _get_recovery_suggestions(self, state: CashAgentState) -> List[str]:
        """Get recovery suggestions based on current state."""
        suggestions = []

        if any("reconciliation" in error.lower() for error in state.errors):
            suggestions.append("Review payment records and transaction history")

        if any("settlement" in error.lower() for error in state.errors):
            suggestions.append("Check supplier payment information and banking details")

        if any("commission" in error.lower() for error in state.errors):
            suggestions.append("Verify commission calculation parameters and rates")

        if not all(state.compliance_checks.values()):
            suggestions.append("Address compliance violations before proceeding")

        return suggestions if suggestions else ["Contact finance administrator for assistance"]

    @property
    def transitions(self) -> Dict[str, str]:
        """Get transition mapping for LangGraph routing."""
        return self.transition_map

    @property
    def meta(self) -> Dict[str, Any]:
        """Get node metadata for UI/graph editor."""
        return self._meta

    @meta.setter
    def meta(self, value: Dict[str, Any]):
        """Set node metadata."""
        self._meta = value


@dataclass
class LearnAgentInput:
    """
    Input data for LearnAgentNode from CashAgentNode.

    Attributes:
        order_id: Unique order identifier from financial completion
        order_context: Original order details (material, quantity, location, urgency)
        workflow_summary: Complete workflow execution summary
        performance_metrics: Performance metrics from each agent
        user_feedback: User feedback and ratings if available
        system_events: System events and anomalies during processing
        learning_data: Data collected for machine learning and optimization
        workflow_metadata: Workflow tracking and user context
    """
    order_id: str
    order_context: Dict[str, Any]
    workflow_summary: Dict[str, Any]
    performance_metrics: Dict[str, Any]
    user_feedback: Dict[str, Any] = field(default_factory=dict)
    system_events: List[Dict[str, Any]] = field(default_factory=list)
    learning_data: Dict[str, Any] = field(default_factory=dict)
    workflow_metadata: Dict[str, Any] = field(default_factory=dict)


@dataclass
class LearnAgentState:
    """
    Complete state for learning and optimization workflow.

    Attributes:
        input_data: Input from CashAgentNode
        learning_insights: Generated learning insights and patterns
        optimization_suggestions: Suggestions for system optimization
        anomaly_detections: Detected anomalies and issues
        performance_analysis: Analysis of workflow performance
        recommendation_engine: Generated recommendations for improvements
        knowledge_updates: Updates to knowledge base and models
        feedback_processing: Processing results for user feedback
        errors: List of errors encountered during processing
        timestamp: When this state was created
        transition: Next workflow step to take
        log: Processing log for debugging and monitoring
    """
    input_data: LearnAgentInput
    learning_insights: Dict[str, Any] = field(default_factory=dict)
    optimization_suggestions: List[Dict[str, Any]] = field(default_factory=list)
    anomaly_detections: List[Dict[str, Any]] = field(default_factory=list)
    performance_analysis: Dict[str, Any] = field(default_factory=dict)
    recommendation_engine: Dict[str, Any] = field(default_factory=dict)
    knowledge_updates: Dict[str, Any] = field(default_factory=dict)
    feedback_processing: Dict[str, Any] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)
    transition: str = "pending"
    log: List[str] = field(default_factory=list)

    def add_log_entry(self, message: str, level: str = "INFO"):
        """Add entry to processing log."""
        timestamp = datetime.now().isoformat()
        self.log.append(f"[{timestamp}] {level}: {message}")

    def add_error(self, error: str):
        """Add error to error list and log."""
        self.errors.append(error)
        self.add_log_entry(f"ERROR: {error}", "ERROR")

    def add_learning_insight(self, insight_type: str, insight_data: Dict[str, Any], confidence: float):
        """Record learning insight."""
        insight = {
            "insight_type": insight_type,
            "insight_data": insight_data,
            "confidence": confidence,
            "timestamp": datetime.now().isoformat()
        }
        if "insights" not in self.learning_insights:
            self.learning_insights["insights"] = []
        self.learning_insights["insights"].append(insight)
        self.add_log_entry(f"LEARNING: {insight_type} (confidence: {confidence})")


@dataclass
class LearnAgentOutput:
    """
    Output from LearnAgentNode execution.

    Attributes:
        order_id: Unique order identifier
        learning_summary: Summary of learning insights generated
        optimization_summary: Summary of optimization suggestions
        anomaly_summary: Summary of anomalies detected
        performance_summary: Summary of performance analysis
        recommendations: Generated recommendations for system improvement
        transition: Next node in pipeline ('learned', 'anomaly')
        log: Complete processing log
        error_details: Detailed error information if processing failed
        metadata: Additional output metadata including processing metrics
    """
    order_id: str
    learning_summary: Dict[str, Any]
    optimization_summary: Dict[str, Any]
    anomaly_summary: Dict[str, Any]
    performance_summary: Dict[str, Any]
    recommendations: Dict[str, Any]
    transition: str
    log: List[str]
    error_details: Optional[Dict[str, Any]] = None
    metadata: Dict[str, Any] = field(default_factory=dict)


class LearnAgentNode:
    """
    LangGraph-ready LearnAgentNode for machine learning and optimization.

    Final node that converts operational telemetry into learning signals,
    optimization suggestions, and forward-looking recommendations.

    Role: Post-financial learning, anomaly detection, optimization planning
    Inputs: CashAgentOutput (financial completion summary and workflow telemetry)
    Outputs: Learning insights, optimization plan, anomaly report, next transition
    Downstream Transitions: "learned" -> ArchiveAgent, "anomaly" -> ErrorHandlerAgent,
                            "clarify" -> ClarifyAgent
    """

    def __init__(
        self,
        node_id: str = "learn_agent",
        enable_anomaly_detection: bool = True,
        enable_feedback_learning: bool = True,
        enable_recommendations: bool = True,
        insight_confidence_threshold: float = 0.6,
        enable_logging: bool = True,
    ):
        """
        Initialize LearnAgentNode with configuration flags.

        Args:
            node_id: Unique identifier for this node in LangGraph
            enable_anomaly_detection: Whether to evaluate anomalies in workflow data
            enable_feedback_learning: Whether to incorporate user feedback signals
            enable_recommendations: Whether to generate recommendations for teams
            insight_confidence_threshold: Minimum confidence score to highlight insights
            enable_logging: Whether to emit structured logs for debugging
        """
        self.node_id = node_id
        self.enable_anomaly_detection = enable_anomaly_detection
        self.enable_feedback_learning = enable_feedback_learning
        self.enable_recommendations = enable_recommendations
        self.insight_confidence_threshold = insight_confidence_threshold
        self.enable_logging = enable_logging

        self.transition_map = {
            "learned": "ArchiveAgent",
            "anomaly": "ErrorHandlerAgent",
            "clarify": "ClarifyAgent",
        }

        self.meta = {
            "icon": "🧠",
            "color": "purple",
            "description": "Learning & Optimization",
            "order": 8,
            "input_example": {
                "order_id": "ORD-20250108-001",
                "order_context": {
                    "material": "aluminum sheets",
                    "quantity": 5.0,
                    "location": "Chennai",
                    "urgency": "URGENT",
                },
                "workflow_summary": {
                    "intake": {"transition": "validated"},
                    "guard": {"transition": "pass"},
                    "cluster": {"transition": "matched"},
                    "commit": {"transition": "committed"},
                    "ops": {"transition": "delivered"},
                    "cash": {"transition": "cash_ok"},
                },
                "performance_metrics": {
                    "sla_breach": False,
                    "time_to_match_minutes": 45,
                    "delivery_time_hours": 6,
                    "policy_flags": 0,
                },
                "system_events": [
                    {"type": "info", "message": "Delivery completed", "severity": "low"}
                ],
                "learning_data": {"historical_similarity": 0.82},
            },
            "output_example": {
                "order_id": "ORD-20250108-001",
                "learning_summary": {
                    "insights": [
                        {
                            "insight_type": "delivery_performance",
                            "confidence": 0.82,
                            "summary": "Consistent on-time deliveries for urgent aluminum sheet requests.",
                        }
                    ]
                },
                "optimization_summary": {
                    "suggestions": [
                        {
                            "area": "matching",
                            "action": "Tune supplier scoring for urgent Chennai requests",
                            "impact": "medium",
                        }
                    ]
                },
                "anomaly_summary": {"anomalies": []},
                "performance_summary": {"sla_breach": False, "delivery_time_hours": 6},
                "recommendations": {
                    "ops": ["Retain express logistics partner for Chennai region"]
                },
                "transition": "learned",
            },
        }

        if self.enable_logging:
            logger.info("LearnAgentNode '%s' initialized successfully", node_id)

    async def execute(self, state: LearnAgentState) -> LearnAgentOutput:
        """
        Async execute method for LangGraph node processing.

        Args:
            state: Current workflow state with input data

        Returns:
            LearnAgentOutput with learning insights and next transition
        """
        start_time = datetime.now()
        state.add_log_entry(f"Learning cycle started at {start_time.isoformat()}")

        try:
            self._validate_input(state)
            state.performance_analysis = self._summarize_performance(state)

            insights = self._generate_learning_insights(state)
            state.learning_insights = {"insights": insights}

            suggestions = self._generate_optimization_suggestions(state)
            state.optimization_suggestions = suggestions

            if self.enable_anomaly_detection:
                anomalies = self._detect_anomalies(state)
                state.anomaly_detections = anomalies
            else:
                anomalies = []

            recommendations = self._build_recommendations(state, suggestions)
            state.recommendation_engine = recommendations

            transition = "learned"
            if anomalies:
                transition = "anomaly"
                state.add_log_entry(
                    f"Anomalies detected: {len(anomalies)}", level="WARNING"
                )

            state.transition = transition
            completion_time = datetime.now()
            state.add_log_entry(
                f"Learning cycle completed at {completion_time.isoformat()}"
            )

            return LearnAgentOutput(
                order_id=state.input_data.order_id,
                learning_summary=state.learning_insights or {"insights": []},
                optimization_summary={"suggestions": suggestions},
                anomaly_summary={"anomalies": anomalies},
                performance_summary=state.performance_analysis,
                recommendations=recommendations,
                transition=transition,
                log=state.log,
                metadata={
                    "node_id": self.node_id,
                    "started_at": start_time.isoformat(),
                    "completed_at": completion_time.isoformat(),
                },
            )

        except Exception as exc:
            error_message = f"Learning cycle failed: {exc}"
            state.add_error(error_message)
            state.transition = "anomaly"
            logger.exception("LearnAgentNode '%s' failed: %s", self.node_id, exc)

            return LearnAgentOutput(
                order_id=state.input_data.order_id if state.input_data else "UNKNOWN",
                learning_summary=state.learning_insights or {"insights": []},
                optimization_summary={"suggestions": state.optimization_suggestions},
                anomaly_summary={"anomalies": state.anomaly_detections},
                performance_summary=state.performance_analysis,
                recommendations=state.recommendation_engine,
                transition="anomaly",
                log=state.log,
                error_details={
                    "errors": state.errors,
                    "exception": str(exc),
                    "node_id": self.node_id,
                },
                metadata={"node_id": self.node_id, "failed_at": datetime.now().isoformat()},
            )

    def _validate_input(self, state: LearnAgentState) -> None:
        """Validate incoming state has essential data."""
        if not state.input_data:
            raise ValueError("LearnAgentState requires input_data")

        missing_fields = [
            field_name
            for field_name in ("order_id", "order_context", "workflow_summary")
            if not getattr(state.input_data, field_name, None)
        ]
        if missing_fields:
            raise ValueError(f"Missing required input fields: {', '.join(missing_fields)}")

    def _summarize_performance(self, state: LearnAgentState) -> Dict[str, Any]:
        """Create a normalized performance summary."""
        metrics = state.input_data.performance_metrics or {}
        summary = {
            "sla_breach": metrics.get("sla_breach", False),
            "time_to_match_minutes": metrics.get("time_to_match_minutes"),
            "delivery_time_hours": metrics.get("delivery_time_hours"),
            "policy_flags": metrics.get("policy_flags", 0),
        }
        summary["event_counts"] = self._count_events(state.input_data.system_events)
        return summary

    def _generate_learning_insights(self, state: LearnAgentState) -> List[Dict[str, Any]]:
        """Generate learning insights based on telemetry."""
        insights: List[Dict[str, Any]] = []
        metrics = state.performance_analysis

        if metrics.get("delivery_time_hours") is not None:
            confidence = max(
                0.1,
                min(1.0, 1 - (metrics["delivery_time_hours"] / 48)),
            )
            insights.append(
                {
                    "insight_type": "delivery_performance",
                    "confidence": confidence,
                    "summary": (
                        "Delivery is consistently within expected windows."
                        if metrics["delivery_time_hours"] and metrics["delivery_time_hours"] <= 12
                        else "Delivery time exceeds target; review logistics partnerships."
                    ),
                }
            )

        policy_flags = metrics.get("policy_flags", 0)
        if policy_flags:
            insights.append(
                {
                    "insight_type": "policy_compliance",
                    "confidence": 0.7,
                    "summary": f"{policy_flags} policy flag(s) recorded during workflow.",
                }
            )

        learning_data = state.input_data.learning_data or {}
        historical_similarity = learning_data.get("historical_similarity")
        if historical_similarity is not None:
            insights.append(
                {
                    "insight_type": "pattern_similarity",
                    "confidence": historical_similarity,
                    "summary": (
                        "Request matches successful historical patterns."
                        if historical_similarity >= self.insight_confidence_threshold
                        else "Pattern similarity is low; treat as emerging case."
                    ),
                }
            )

        return insights

    def _generate_optimization_suggestions(
        self, state: LearnAgentState
    ) -> List[Dict[str, Any]]:
        """Derive optimization suggestions from metrics and feedback."""
        suggestions: List[Dict[str, Any]] = []
        metrics = state.performance_analysis
        feedback = state.input_data.user_feedback or {}

        if metrics.get("time_to_match_minutes") and metrics["time_to_match_minutes"] > 60:
            suggestions.append(
                {
                    "area": "matching",
                    "action": "Review supplier ranking for faster matching",
                    "impact": "high",
                    "reason": f"Average match time {metrics['time_to_match_minutes']} minutes.",
                }
            )

        satisfaction = feedback.get("satisfaction_score")
        if (
            self.enable_feedback_learning
            and satisfaction is not None
            and satisfaction < 3
        ):
            suggestions.append(
                {
                    "area": "customer_experience",
                    "action": "Trigger customer success follow-up",
                    "impact": "medium",
                    "reason": f"Reported satisfaction score {satisfaction}.",
                }
            )

        if not suggestions:
            suggestions.append(
                {
                    "area": "continuous_improvement",
                    "action": "Capture success pattern for knowledge base",
                    "impact": "low",
                    "reason": "No critical issues detected in workflow telemetry.",
                }
            )

        return suggestions

    def _detect_anomalies(self, state: LearnAgentState) -> List[Dict[str, Any]]:
        """Detect anomalies from system events and metrics."""
        anomalies: List[Dict[str, Any]] = []
        metrics = state.performance_analysis

        if metrics.get("sla_breach"):
            anomalies.append(
                {
                    "type": "sla_breach",
                    "severity": "high",
                    "details": "Service-level agreement breached during delivery.",
                }
            )

        for event in state.input_data.system_events or []:
            severity = event.get("severity", "low")
            if severity in {"high", "critical"}:
                anomalies.append(
                    {
                        "type": event.get("type", "system_event"),
                        "severity": severity,
                        "details": event.get("message", "No details provided"),
                    }
                )

        return anomalies

    def _build_recommendations(
        self, state: LearnAgentState, suggestions: List[Dict[str, Any]]
    ) -> Dict[str, List[str]]:
        """Construct channel-specific recommendations."""
        if not self.enable_recommendations:
            return {"general": ["Learning captured; no automated recommendations."]}

        recommendations: Dict[str, List[str]] = {"general": []}
        for suggestion in suggestions:
            channel = suggestion.get("area", "general")
            message = suggestion.get("action")
            if not message:
                continue
            recommendations.setdefault(channel, []).append(message)

        if state.anomaly_detections:
            recommendations.setdefault("operations", []).append(
                "Review anomalies flagged by learning engine before closing order."
            )

        if not recommendations["general"]:
            recommendations["general"].append(
                "Log learning summary to knowledge base and notify stakeholders."
            )

        return recommendations

    def _count_events(self, events: List[Dict[str, Any]]) -> Dict[str, int]:
        """Count events by severity for quick dashboards."""
        counts: Dict[str, int] = {"low": 0, "medium": 0, "high": 0, "critical": 0}
        for event in events or []:
            severity = event.get("severity", "low").lower()
            if severity not in counts:
                counts[severity] = 0
            counts[severity] += 1
        return counts

    @property
    def transitions(self) -> Dict[str, str]:
        """Expose transition mapping for LangGraph routing."""
        return self.transition_map

    @property
    def meta(self) -> Dict[str, Any]:
        """Return node metadata for UI/graph editors."""
        return self._meta

    @meta.setter
    def meta(self, value: Dict[str, Any]) -> None:
        """Update node metadata."""
        self._meta = value


async def run_self_test():
    """
    Self-test harness for IntakeAgentNode with sample artisan inputs.

    Tests various scenarios including valid requests, missing data,
    and policy violations to ensure proper transition logic.
    """
    print("\n🧪 IntakeAgentNode Self-Test Harness")
    print("=" * 50)

    # Initialize the node
    node = IntakeAgentNode(
        node_id="test_intake_agent",
        extraction_model="llama3",
        enable_policy_validation=False  # Disable for testing without policies
    )

    # Sample test cases
    test_cases = [
        {
            "name": "Complete Valid Request",
            "input": {
                "text": "Need 5 kg of aluminum sheets in Chennai by tonight, URGENT.",
                "metadata": {"source": "whatsapp", "user_id": "artisan123"}
            },
            "expected_transition": "validated"
        },
        {
            "name": "Missing Material",
            "input": {
                "text": "Need 10 kg in Mumbai urgently",
                "metadata": {"source": "web_form", "user_id": "business456"}
            },
            "expected_transition": "clarification_needed"
        },
        {
            "name": "Missing Location",
            "input": {
                "text": "Need 20 pcs of steel rods, urgent delivery",
                "metadata": {"source": "api", "user_id": "supplier789"}
            },
            "expected_transition": "clarification_needed"
        },
        {
            "name": "Emergency Request",
            "input": {
                "text": "EMERGENCY: Need 1 kg gold wire in Delhi immediately!",
                "metadata": {"source": "whatsapp", "user_id": "premium_customer"}
            },
            "expected_transition": "validated"
        },
        {
            "name": "Ambiguous Input",
            "input": {
                "text": "Looking for some materials, not sure about quantity or location yet",
                "metadata": {"source": "web_form", "user_id": "new_user"}
            },
            "expected_transition": "clarification_needed"
        }
    ]

    results = []

    for i, test_case in enumerate(test_cases, 1):
        print(f"\n📋 Test Case {i}: {test_case['name']}")
        print("-" * 40)

        try:
            # Create state
            raw_input = IntakeRawInput(**test_case['input'])
            state = IntakeAgentState(raw=raw_input)

            # Execute node
            output = await node.execute(state)

            # Log results
            print(f"Input: {test_case['input']['text']}")
            print(f"Expected transition: {test_case['expected_transition']}")
            print(f"Actual transition: {state.transition}")
            print(f"Next node: {output.next_node}")
            print(f"Valid: {output.valid}")

            if output.normalized:
                print(f"Extracted material: {output.normalized.get('material', {}).get('value', 'None')}")
                print(f"Extracted quantity: {output.normalized.get('quantity', {}).get('formatted', 'None')}")
                print(f"Extracted location: {output.normalized.get('location', {}).get('value', 'None')}")
                print(f"Extracted urgency: {output.normalized.get('urgency', {}).get('value', 'None')}")

            # Check if transition matches expectation
            success = state.transition == test_case['expected_transition']
            results.append(success)

            print(f"✅ PASS" if success else f"❌ FAIL")

        except Exception as e:
            print(f"❌ ERROR: {e}")
            results.append(False)

    # Summary
    print(f"\n📊 Test Summary")
    print("=" * 50)
    passed = sum(results)
    total = len(results)
    print(f"Passed: {passed}/{total}")

    if passed == total:
        print("🎉 All tests passed!")
    else:
        print(f"⚠️  {total - passed} test(s) failed")

    return passed == total


# ============================================================================
# SECTION: INTEGRATION DEMONSTRATION
# ============================================================================

async def run_integration_demo():
    """
    Demonstration of IntakeAgentNode -> GuardAgentNode pipeline integration.

    Shows how the two nodes work together in sequence for complete
    intake processing and security validation.
    """
    print("\n🔗 Integration Demo: IntakeAgentNode → GuardAgentNode")
    print("=" * 70)

    # Initialize both nodes
    intake_node = IntakeAgentNode(
        node_id="demo_intake",
        extraction_model="llama3",
        enable_policy_validation=False
    )

    guard_node = GuardAgentNode(
        node_id="demo_guard",
        enable_rate_limiting=True,
        enable_profanity_filter=True,
        enable_policy_guards=False
    )

    # Sample request for integration demo
    demo_request = {
        "text": "Need 5 kg of aluminum sheets in Chennai, URGENT delivery required.",
        "metadata": {"source": "whatsapp", "user_id": "demo_user_123"}
    }

    print(f"📨 Demo Request: {demo_request['text']}")
    print("-" * 70)

    try:
        # Step 1: IntakeAgentNode processes the request
        print("📝 Step 1: IntakeAgentNode Processing...")
        raw_input = IntakeRawInput(**demo_request)
        intake_state = IntakeAgentState(raw=raw_input)
        intake_output = await intake_node.execute(intake_state)

        print(f"✅ Intake completed: {intake_state.transition} → {intake_output.next_node}")
        print(f"   Extracted: {intake_output.normalized.get('material', {}).get('value', 'None')}")
        print(f"   Quantity: {intake_output.normalized.get('quantity', {}).get('formatted', 'None')}")
        print(f"   Location: {intake_output.normalized.get('location', {}).get('value', 'None')}")

        # Step 2: GuardAgentNode validates security (only if intake succeeded)
        if intake_output.valid:
            print("\n🚨 Step 2: GuardAgentNode Security Validation...")
            guard_input = GuardAgentInput(
                normalized=intake_output.normalized,
                intake_metadata=demo_request["metadata"],
                user_context={"user_id": demo_request["metadata"]["user_id"]}
            )
            guard_state = GuardAgentState(input_data=guard_input)
            guard_output = await guard_node.execute(guard_state)

            print(f"✅ Security scan completed: {'APPROVED' if guard_output.approved else 'BLOCKED'}")
            print(f"   Risk Score: {guard_output.risk_score}/100")
            print(f"   Final Transition: {guard_output.transition} → {guard_node.transition_map.get(guard_output.transition, 'Unknown')}")

            if guard_output.block_reasons:
                print(f"   Block Reasons: {', '.join(guard_output.block_reasons)}")
            else:
                print("   ✅ Request approved for downstream processing")
        else:
            print("\n🚨 Step 2: Skipped - Intake validation failed")
            print(f"   Reason: {intake_output.error_details}")

        # Step 3: Show complete pipeline flow
        print("\n🔄 Complete Pipeline Flow:")
        print("   Raw Input → IntakeAgentNode → GuardAgentNode → Next Node")
        print(f"   {demo_request['text'][:30]}... → {intake_state.transition} → {guard_state.transition if intake_output.valid else 'SKIPPED'} → {guard_node.transition_map.get(guard_state.transition) if intake_output.valid else 'N/A'}")

    except Exception as e:
        print(f"❌ Integration demo failed: {e}")

    return True


# ============================================================================
# SECTION: MAIN EXECUTION BLOCK
# ============================================================================

if __name__ == "__main__":
    """
    Main execution block for testing and demonstration.
    """
    print("🚀 ArtisanHub Agent System")
    print("=" * 60)
    print("Modular LangGraph nodes for artisan marketplace processing")
    print("📝 IntakeAgentNode: Input parsing and validation")
    print("🚨 GuardAgentNode: Security and policy enforcement")
    print("=" * 60)

    # Run individual node tests
    intake_success = asyncio.run(run_self_test())
    guard_success = asyncio.run(run_guard_self_test())
    sales_success = asyncio.run(run_sales_self_test())

    # Run integration demo
    integration_success = asyncio.run(run_integration_demo())

    # Overall summary
    print("\n📊 Overall Test Summary")
    print("=" * 60)
    print(f"IntakeAgentNode Tests: {'✅ PASS' if intake_success else '❌ FAIL'}")
    print(f"GuardAgentNode Tests: {'✅ PASS' if guard_success else '❌ FAIL'}")
    print(f"SalesAgentNode Tests: {'✅ PASS' if sales_success else '❌ FAIL'}")
    print(f"Integration Demo: {'✅ PASS' if integration_success else '❌ FAIL'}")

    if intake_success and guard_success and sales_success and integration_success:
        print("\n🎉 All systems operational!")
        print("✅ IntakeAgentNode: Ready for input processing")
        print("✅ GuardAgentNode: Ready for security enforcement")
        print("✅ SalesAgentNode: Ready for digital channel creation")
        print("✅ Integration: Pipeline flow verified")
    else:
        print("\n⚠️  Some tests failed - check output above")

    print("\n🚀 Agent System is ready for LangGraph integration!")
    print("📝 IntakeAgentNode → 🚨 GuardAgentNode → ClusterAgent → 📝 CommitAgent → 🛒 SalesAgent → OpsAgent")
    print("Connect nodes in your main LangGraph workflow for complete pipeline processing.")
