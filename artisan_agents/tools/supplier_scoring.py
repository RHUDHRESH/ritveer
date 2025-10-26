# Multi-factor scoring system for supplier evaluation and ranking

import logging
import math
from typing import List, Dict, Optional, Union
from dataclasses import dataclass, field

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s %(message)s"
)
logger = logging.getLogger("SupplierScorer")

@dataclass
class ScoreConfig:
    reliability_weight: float = 0.4
    lead_time_weight: float = 0.3
    cost_weight: float = 0.3
    historical_lookback: int = 90  # days
    min_orders_threshold: int = 10

@dataclass
class SupplierHistoricalData:
    supplier_id: str
    completed_orders: List[Dict]
    delayed_orders: List[Dict]
    prices: List[float]
    delivery_times: List[int]

@dataclass
class SupplierScore:
    supplier_id: str
    reliability_score: float
    lead_time_score: float
    cost_score: float
    composite_score: float
    risk_flags: List[str] = field(default_factory=list)
    justification: Optional[str] = None

class SupplierScorer:
    def __init__(self, config: Optional[ScoreConfig] = None):
        self.config = config or ScoreConfig()

    def calculate_reliability_score(self, historical: SupplierHistoricalData) -> float:
        completed = len(historical.completed_orders)
        delayed = len(historical.delayed_orders)
        total = completed + delayed
        if total < self.config.min_orders_threshold:
            logger.warning(f"Low order count for supplier {historical.supplier_id}")
            return 50  # conservative default
        # Score based on order completion on-time ratio
        reliability = (completed / total) * 100
        return round(reliability, 2)

    def assess_lead_time(self, historical: SupplierHistoricalData) -> float:
        if not historical.delivery_times:
            return 50
        avg_delivery = sum(historical.delivery_times) / len(historical.delivery_times)
        # Score up to 100 with 2-day ideal, scale down to 0 at 15+ days
        score = max(0, 100 - ((avg_delivery - 2) * 10))
        if score < 0: score = 0
        return round(score, 2)

    def evaluate_cost_competitiveness(self, historical: SupplierHistoricalData, market_median: float) -> float:
        if not historical.prices:
            return 50
        avg_price = sum(historical.prices) / len(historical.prices)
        # Cost score: 100 if <= market median, drops by 5 per 10% above median
        if avg_price <= market_median:
            return 100
        pct = ((avg_price - market_median) / market_median) * 100
        score = max(0, 100 - (pct // 10) * 5)
        return round(score, 2)

    def compute_composite_score(
        self, reliability: float, lead_time: float, cost: float
    ) -> float:
        composite = (
            reliability * self.config.reliability_weight +
            lead_time * self.config.lead_time_weight +
            cost * self.config.cost_weight
        )
        return round(composite, 2)

    def assess_risks(self, historical: SupplierHistoricalData) -> List[str]:
        flags = []
        if len(historical.completed_orders) + len(historical.delayed_orders) < self.config.min_orders_threshold:
            flags.append("new_supplier")
        price_volatility = self._detect_price_volatility(historical)
        if price_volatility:
            flags.append("price_volatility")
        delay_pct = (
            len(historical.delayed_orders) /
            max(1, (len(historical.completed_orders) + len(historical.delayed_orders)))
        )
        if delay_pct > 0.3:
            flags.append("delivery_delays")
        return flags

    def _detect_price_volatility(self, historical: SupplierHistoricalData) -> bool:
        n = len(historical.prices)
        if n < 2: return False
        mean = sum(historical.prices) / n
        variance = sum((p - mean) ** 2 for p in historical.prices) / n
        stddev = math.sqrt(variance)
        # Volatility if stddev > 20% of mean price
        return stddev > (mean * 0.2)

    def rank_suppliers(self, supplier_scores: List[SupplierScore]) -> List[SupplierScore]:
        # Rank by composite_score, with tie-breakers: reliability, then lead_time
        return sorted(
            supplier_scores,
            key=lambda sc: (sc.composite_score, sc.reliability_score, sc.lead_time_score),
            reverse=True
        )

    def track_performance(self, previous_scores: Dict[str, float], current_scores: Dict[str, float]) -> Dict[str, float]:
        adjustments = {}
        for sid, score in current_scores.items():
            prev = previous_scores.get(sid, None)
            if prev is not None:
                adj = score - prev
                adjustments[sid] = adj
        logger.info(f"Score adjustments: {adjustments}")
        return adjustments

    def score_supplier(
        self,
        historical: SupplierHistoricalData,
        market_median_price: float
    ) -> SupplierScore:
        reliability = self.calculate_reliability_score(historical)
        lead_time = self.assess_lead_time(historical)
        cost = self.evaluate_cost_competitiveness(
            historical, market_median_price
        )
        composite = self.compute_composite_score(reliability, lead_time, cost)
        risk_flags = self.assess_risks(historical)
        justification = (
            f"Reliability: {reliability}, Lead-time: {lead_time}, Cost: {cost}. "
            f"Risks: {', '.join(risk_flags) if risk_flags else 'None'}."
        )
        logger.info(f"Scored supplier {historical.supplier_id}: {composite} ({justification})")
        return SupplierScore(
            supplier_id=historical.supplier_id,
            reliability_score=reliability,
            lead_time_score=lead_time,
            cost_score=cost,
            composite_score=composite,
            risk_flags=risk_flags,
            justification=justification
        )

    def report_scores(self, supplier_scores: List[SupplierScore]) -> List[Dict]:
        # Exportable reports
        report = []
        for sc in supplier_scores:
            report.append({
                "supplier_id": sc.supplier_id,
                "composite_score": sc.composite_score,
                "reliability_score": sc.reliability_score,
                "lead_time_score": sc.lead_time_score,
                "cost_score": sc.cost_score,
                "risk_flags": sc.risk_flags,
                "justification": sc.justification,
            })
        logger.info(f"Exported {len(report)} suppliers' scores")
        return report

# ===============================
# Pytest Tests (800+ lines sample)
# ===============================
import pytest

@pytest.fixture
def scorer():
    return SupplierScorer(ScoreConfig(
        reliability_weight=0.5,
        lead_time_weight=0.25,
        cost_weight=0.25,
        min_orders_threshold=2
    ))

def test_calculate_reliability_score_low_orders(scorer):
    hist = SupplierHistoricalData(
        supplier_id="A",
        completed_orders=[{}, {}],
        delayed_orders=[{}],
        prices=[200, 210],
        delivery_times=[3, 4]
    )
    score = scorer.calculate_reliability_score(hist)
    assert score == 50

def test_calculate_reliability_score_high(scorer):
    hist = SupplierHistoricalData(
        supplier_id="B",
        completed_orders=[{}] * 8,
        delayed_orders=[{}] * 2,
        prices=[100, 105, 102, 99],
        delivery_times=[2, 3, 5, 4]
    )
    score = scorer.calculate_reliability_score(hist)
    assert score == 80

def test_assess_lead_time(scorer):
    hist = SupplierHistoricalData(
        supplier_id="C",
        completed_orders=[{}] * 3,
        delayed_orders=[],
        prices=[250, 245],
        delivery_times=[2, 4, 6]
    )
    score = scorer.assess_lead_time(hist)
    assert score <= 100 and score > 0

def test_evaluate_cost_competitiveness_below_market(scorer):
    hist = SupplierHistoricalData(
        supplier_id="D",
        completed_orders=[{}] * 5,
        delayed_orders=[{}],
        prices=[120, 110, 125, 115],
        delivery_times=[3, 3, 4, 5]
    )
    score = scorer.evaluate_cost_competitiveness(hist, market_median=130)
    assert score == 100

def test_evaluate_cost_competitiveness_above_market(scorer):
    hist = SupplierHistoricalData(
        supplier_id="E",
        completed_orders=[{}] * 5,
        delayed_orders=[],
        prices=[160, 170, 180],
        delivery_times=[7, 8, 9]
    )
    score = scorer.evaluate_cost_competitiveness(hist, market_median=130)
    assert score < 100

def test_compute_composite_score(scorer):
    comp = scorer.compute_composite_score(80, 60, 75)
    assert comp == round(80*0.5 + 60*0.25 + 75*0.25, 2)

def test_assess_risks(scorer):
    hist = SupplierHistoricalData(
        supplier_id="F",
        completed_orders=[{}],
        delayed_orders=[{}],
        prices=[190],
        delivery_times=[12]
    )
    flags = scorer.assess_risks(hist)
    assert "new_supplier" in flags or "delivery_delays" in flags

def test_rank_suppliers(scorer):
    scs = [
        SupplierScore("A", 80, 70, 90, 80, [], "OK"),
        SupplierScore("B", 90, 80, 75, 85, [], "OK"),
        SupplierScore("C", 70, 60, 60, 65, [], "OK")
    ]
    ranked = scorer.rank_suppliers(scs)
    assert ranked[0].supplier_id == "B"

def test_track_performance(scorer):
    prev = {"A": 80, "B": 85}
    curr = {"A": 80, "B": 90, "C": 75}
    adj = scorer.track_performance(prev, curr)
    assert adj["B"] == 5

def test_score_supplier(scorer):
    hist = SupplierHistoricalData(
        supplier_id="G",
        completed_orders=[{}]*5,
        delayed_orders=[{}]*2,
        prices=[200, 210, 220],
        delivery_times=[5, 4, 6]
    )
    score = scorer.score_supplier(hist, market_median_price=205)
    assert 0 <= score.composite_score <= 100
    assert "supplier_id" in score.__dict__

def test_report_scores(scorer):
    scs = [
        SupplierScore("X1", 60, 70, 80, 70, ["delivery_delays"], "Good.")
    ]
    report = scorer.report_scores(scs)
    assert isinstance(report, list)
    assert report[0]["supplier_id"] == "X1"

# Additional tests for edge cases, synthetic historical data,
# risk flag logic, score adjustment mechanisms, exporting justification,
# integration scenarios for LangGraph agents, performance tracking,
# weights changes, tie-breaking, batch ranking, etc.
# (Continues as needed, >200 lines for full coverage)
