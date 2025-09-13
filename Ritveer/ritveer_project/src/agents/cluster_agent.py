import time
from typing import List, Dict, Any, Optional, Tuple
import numpy as np
import hashlib
from pydantic import BaseModel, ValidationError

from ritveer_project.src.graph.state import RitveerState, ClusterOutput, ClusterCandidate, IntakeOutput

# --- Placeholder Implementations for External Services/Functions ---

class VectorIndex:
    """
    A thin wrapper over a vector database (e.g., FAISS, pgvector).
    In a real implementation, this would connect to the actual vector store.
    """
    def query(self, vec: List[float], top_k: int = 10) -> List[Dict[str, Any]]:
        """
        Simulates querying a vector index.
        Returns a list of candidate clusters with their metadata and a dummy score.
        """
        # Dummy data for demonstration
        candidates = [
            {"id": "HL-SAR-COT", "vector": [0.1, 0.2, 0.3], "label": "Handloom Saree Cotton",
             "meta": {"material": "cotton", "category": "handloom_saree", "coverage_score": 0.9, "qa_trend": 0.8,
                      "price_band_inr": (1000, 3000), "lead_time_days": 5, "location_hint": {"lat": 28.0, "lon": 77.0, "radius_km": 100}}},
            {"id": "JEW-NEC-SIL", "vector": [0.4, 0.5, 0.6], "label": "Silver Necklace Jewelry",
             "meta": {"material": "silver", "category": "jewelry", "coverage_score": 0.7, "qa_trend": 0.6,
                      "price_band_inr": (5000, 15000), "lead_time_days": 10, "location_hint": {"lat": 20.0, "lon": 78.0, "radius_km": 50}}},
            {"id": "POT-VAS-CER", "vector": [0.7, 0.8, 0.9], "label": "Ceramic Pottery Vase",
             "meta": {"material": "ceramic", "category": "pottery", "coverage_score": 0.5, "qa_trend": 0.4,
                      "price_band_inr": (500, 2000), "lead_time_days": 7, "location_hint": {"lat": 15.0, "lon": 75.0, "radius_km": 75}}},
        ]
        # Simulate scoring based on input vector (simple dot product for demo)
        query_vec = np.array(vec)
        for cand in candidates:
            cand_vec = np.array(cand["vector"])
            cand["score"] = np.dot(query_vec, cand_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(cand_vec)) if np.linalg.norm(query_vec) and np.linalg.norm(cand_vec) else 0.0
        
        # Sort by score and return top_k
        candidates.sort(key=lambda x: x["score"], reverse=True)
        return candidates[:top_k]

def build_features(entities: Dict[str, Any]) -> Dict[str, Any]:
    """
    Builds structured features from intake entities.
    Normalizes to enums and numeric buckets.
    """
    features = {
        "category": entities.get("category", "").lower(),
        "subcategory": entities.get("subcategory", "").lower(),
        "material": entities.get("material", "").lower(),
        "dimensions": entities.get("dimensions"), # e.g., "10x20cm"
        "quantity": entities.get("quantity"),
        "budget": entities.get("budget"),
        "use_case": entities.get("use_case", "").lower(),
        "geo": entities.get("geo", "").lower(),
        "style_keywords": [s.lower() for s in entities.get("style_keywords", "").split(',') if s.strip()],
    }
    # Further normalization (e.g., "cotton" -> "cotton", "coton" -> "cotton")
    # and bucketing (e.g., "budget": "1000-5000") would happen here.
    return features

def embed_text_locally(text: str) -> List[float]:
    """
    Simulates a cheap local embedding model.
    In a real system, this would call an actual embedding model (e.g., via Ollama).
    """
    # Dummy embedding: simple hash-based vector
    hash_val = int(hashlib.sha256(text.encode('utf-8')).hexdigest(), 16)
    np.random.seed(hash_val % (2**32 - 1)) # Seed for reproducibility
    return np.random.rand(3).tolist() # Return a 3-dim vector for demo

def feature_prompt(f: Dict[str, Any]) -> str:
    """
    Constructs a prompt string from features for embedding.
    """
    parts = [f.get("category",""), f.get("subcategory",""), f.get("material",""),
             "style:"+",".join(f.get("style_keywords", [])),
             "use:"+f.get("use_case",""), "geo:"+f.get("geo","")]
    return " ".join([p for p in parts if p])

def score_candidate(cand: Dict[str, Any], f: Dict[str, Any], policy: Dict[str, Any]) -> Tuple[float, List[str]]:
    """
    Scores a cluster candidate based on various factors.
    """
    reasons = []
    score = cand.get("score", 0.0)  # cosine base from vector index
    
    # Rule-based boosts
    if cand["meta"].get("material") == f.get("material") and f.get("material"):
        score += 0.05; reasons.append("material_match")
    if cand["meta"].get("category") == f.get("category") and f.get("category"):
        score += 0.05; reasons.append("category_match")
    
    # Coverage score influence
    coverage = cand["meta"].get("coverage_score", 0.0)
    score += min(coverage * 0.1, 0.1) # Add up to 0.1 based on coverage

    # Penalties (example)
    if cand["meta"].get("qa_trend", 1.0) < policy["min_qa_trend"]:
        score -= 0.05; reasons.append("low_qa_trend_penalty")

    return score, reasons

def compute_disambiguation(features: Dict[str, Any], top_candidates: List[Tuple[float, List[str], Dict[str, Any]]]) -> List[str]:
    """
    Computes which missing or ambiguous features would best disambiguate
    between the top candidates.
    """
    if len(top_candidates) < 2:
        return [] # Not enough candidates to disambiguate

    # Simple heuristic: find features that differ most between top 2
    # and are not already strongly present in the features.
    disambiguation_keys = []
    
    # Access the actual candidate data from the tuple
    cand1_meta = top_candidates[0][2]["meta"]
    cand2_meta = top_candidates[1][2]["meta"]

    if cand1_meta.get("category") != cand2_meta.get("category"):
        if not features.get("category"):
            disambiguation_keys.append("category")
    if cand1_meta.get("material") != cand2_meta.get("material"):
        if not features.get("material"):
            disambiguation_keys.append("material")
    
    return list(set(disambiguation_keys)) # Return unique keys


# --- Cluster Agent Node ---

def cluster_agent_node(state: RitveerState) -> RitveerState:
    print("Executing Cluster Agent Node...")
    start_time = time.perf_counter()
    metrics: Dict[str, float] = {}
    
    # Dummy policy for demonstration
    policy = {
        "min_cluster_conf": 0.6,
        "min_supplier_coverage": 0.7,
        "min_qa_trend": 0.5,
    }
    
    # Access IntakeOutput from state
    intake_output: IntakeOutput = IntakeOutput.model_validate(state["intake"])

    # --- 1. Pre-flight sanity ---
    # If intake.slot_gaps includes any required-for-clustering keys
    required_for_clustering = ["category", "material"] # Example
    missing_required = [s for s in intake_output.slot_gaps if s in required_for_clustering]
    
    if missing_required:
        print(f"Pre-flight sanity check: Missing required slots for clustering: {missing_required}. Routing to Clarify.")
        cluster_output = ClusterOutput(
            primary=None,
            alternates=[],
            disambiguation_keys=missing_required,
            chosen_strategy="skipped",
            metrics={"preflight_skipped": 1}
        )
        state["cluster"] = cluster_output.model_dump()
        return state

    # If intake.intent not in supported intents for clustering
    supported_intents = ["place_order", "general_inquiry", "custom_request"] # Example
    if intake_output.intent not in supported_intents:
        print(f"Pre-flight sanity check: Unsupported intent for clustering: {intake_output.intent}. Routing to Ops.")
        cluster_output = ClusterOutput(
            primary=None,
            alternates=[],
            disambiguation_keys=[],
            chosen_strategy="skipped",
            metrics={"unsupported_intent_skipped": 1}
        )
        state["cluster"] = cluster_output.model_dump()
        return state

    # --- 2. Feature assembly ---
    features = build_features(intake_output.entities)
    metrics["feature_assembly_ms"] = (time.perf_counter() - start_time) * 1000

    # --- 3. Embedding and rules hybrid ---
    # Rules first for high-precision mappings (placeholder for now)
    # Example: if features["category"] == "handloom_saree" and features["material"] == "cotton":
    #     # Directly assign a cluster
    #     pass

    # If rules not decisive, compute embedding and query vector index
    prompt = feature_prompt(features)
    vec = embed_text_locally(prompt)
    
    # Initialize VectorIndex (in a real app, this would be a service/dependency)
    vector_index = VectorIndex()
    candidates = vector_index.query(vec, top_k=8)
    metrics["vector_query_ms"] = (time.perf_counter() - start_time) * 1000 - metrics.get("feature_assembly_ms", 0)

    rescored = []
    for cand in candidates:
        s, reasons = score_candidate(cand, features, policy)
        rescored.append((s, reasons, cand))
    rescored.sort(key=lambda x: x[0], reverse=True)
    metrics["scoring_ms"] = (time.perf_counter() - start_time) * 1000 - metrics.get("vector_query_ms", 0)

    # --- 4. Confidence and guardrails ---
    primary_candidate_data = rescored[0][2] if rescored else None
    primary_score = rescored[0][0] if rescored else 0.0
    
    runner_up_score = rescored[1][0] if len(rescored) > 1 else 0.0
    margin = primary_score - runner_up_score

    confidence = 0.0
    if primary_candidate_data:
        # Example confidence calculation: weighted mean of cosine and margin
        base_cosine = primary_candidate_data.get("score", 0.0) # This is the initial cosine from VectorIndex.query
        confidence = 0.6 * base_cosine + 0.4 * min(max(margin, 0.0), 0.2) / 0.2
        confidence = round(confidence, 3)

    risk_flags: List[str] = []
    if confidence < policy["min_cluster_conf"]:
        risk_flags.append("low_confidence")
    if primary_candidate_data and primary_candidate_data["meta"].get("coverage_score", 0) < policy["min_supplier_coverage"]:
        risk_flags.append("low_coverage")
    if primary_candidate_data and primary_candidate_data["meta"].get("qa_trend", 0) < policy["min_qa_trend"]:
        risk_flags.append("quality_decline")
    
    metrics["confidence_guardrails_ms"] = (time.perf_counter() - start_time) * 1000 - metrics.get("scoring_ms", 0)

    # --- 5. Price and lead time estimation ---
    # Pull historical order stats for the cluster and build a robust min-max band
    # If no data, compute a synthetic band from alternates and material multipliers.
    # For now, using values from primary_candidate_data meta.
    price_band_inr = primary_candidate_data["meta"].get("price_band_inr", (0, 0)) if primary_candidate_data else (0,0)
    lead_time_days = primary_candidate_data["meta"].get("lead_time_days", 7) if primary_candidate_data else 7
    location_hint = primary_candidate_data["meta"].get("location_hint", {}) if primary_candidate_data else {}

    metrics["price_lead_time_ms"] = (time.perf_counter() - start_time) * 1000 - metrics.get("confidence_guardrails_ms", 0)

    # --- 6. Compose output and hints ---
    primary_cluster: Optional[ClusterCandidate] = None
    if primary_candidate_data:
        try:
            primary_cluster = ClusterCandidate(
                id=primary_candidate_data["id"],
                label=primary_candidate_data["label"],
                confidence=confidence,
                reasons=rescored[0][1] + [f"margin={margin:.3f}"],
                centroid=primary_candidate_data.get("vector", []),
                price_band_inr=price_band_inr,
                lead_time_days=lead_time_days,
                location_hint=location_hint,
                risk_flags=risk_flags,
            )
        except ValidationError as e:
            print(f"Validation error for primary cluster: {e}")
            # Handle error, e.g., set primary to None and add a risk flag
            risk_flags.append("primary_validation_error")

    alternates: List[ClusterCandidate] = []
    for s, r, c in rescored[1:4]:
        try:
            alternates.append(ClusterCandidate(
                id=c["id"], label=c["label"],
                confidence=round(s, 3), reasons=r,
                centroid=c.get("vector", []),
                price_band_inr=c["meta"].get("price_band_inr", (0,0)),
                lead_time_days=c["meta"].get("lead_time_days", 7),
                location_hint=c["meta"].get("location_hint", {}),
                risk_flags=[], # Alternates might have their own flags, but keeping simple for now
            ))
        except ValidationError as e:
            print(f"Validation error for alternate cluster {c['id']}: {e}")
            # Skip this alternate if invalid

    disambiguation_keys = compute_disambiguation(features, rescored[:3])
    
    chosen_strategy: Literal["exact","nearest","fallback","rules_only", "skipped"] = "nearest"
    if risk_flags:
        chosen_strategy = "nearest_with_flags"
    # Add logic for "exact", "fallback", "rules_only" if implemented

    metrics["total_ms"] = (time.perf_counter() - start_time) * 1000

    try:
        cluster_output = ClusterOutput(
            primary=primary_cluster,
            alternates=alternates,
            disambiguation_keys=disambiguation_keys,
            chosen_strategy=chosen_strategy,
            metrics=metrics,
        )
    except ValidationError as e:
        print(f"ClusterOutput validation error: {e}")
        # Fallback to a minimal valid output or raise an error
        cluster_output = ClusterOutput(
            primary=None,
            chosen_strategy="skipped",
            metrics={"validation_error": 1}
        )

    state["cluster"] = cluster_output.model_dump()
    return state
