"""Multi-factor scoring service for stock trend prediction.

This service provides multi-factor scoring combining technical, valuation,
market, sentiment, and money flow factors.
"""
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger(__name__)


class ScoringService:
    """Multi-factor scoring system for stock trend prediction."""

    @staticmethod
    def calculate_money_flow_score(moneyflow_data: Dict[str, Any]) -> Dict[str, Any]:
        """Calculate money flow score (-100 to +100) based on main force net inflow.

        Args:
            moneyflow_data: Money flow data dict with net_5d_total and latest values

        Returns:
            Dict with score (-100 to +100), signals list, and source
        """
        try:
            if "error" in moneyflow_data:
                logger.warning(f"Money flow score error: {moneyflow_data['error']}")
                return {"score": 0, "signals": ["资金流数据获取失败"], "source": "none"}

            net_5d = moneyflow_data.get("net_5d_total", 0)
            if net_5d is None:
                net_5d = 0

            score = 0
            signals = []

            if net_5d > 0:
                # Normalize score: larger inflow = higher positive score
                # Cap at 100 for very large inflows
                score = min(100, int(net_5d / 1_000_000))  # Assuming 万元, scale appropriately
                if score > 100:
                    score = 100
                elif score < 0:
                    score = 0
                signals.append(f"5日主力净流入(+{net_5d/1_0000:.1f}万元)")
            elif net_5d < 0:
                score = max(-100, int(net_5d / 1_000_000))
                if score < -100:
                    score = -100
                elif score > 0:
                    score = 0
                signals.append(f"5日主力净流出({net_5d/1_0000:.1f}万元)")
            else:
                signals.append("资金流持平")

            return {
                "score": score,
                "signals": signals,
                "source": moneyflow_data.get("market", "unknown"),
                "net_5d_total": net_5d,
            }
        except Exception as e:
            logger.error(f"Error calculating money flow score: {e}")
            return {"score": 0, "signals": [f"计算错误: {str(e)}"], "source": "error"}

    @staticmethod
    def calculate_composite_score(
        technical_score: float = 0,
        valuation_score: float = 0,
        market_score: float = 0,
        sentiment_score: float = 0,
        money_flow_score: float = 0,
    ) -> Dict[str, Any]:
        """Calculate weighted composite score.

        Weights:
        - Technical: 30%
        - Valuation: 20%
        - Market: 15%
        - Sentiment: 25%
        - Money Flow: 10%
        """
        weights = {
            "technical": 0.30,
            "valuation": 0.20,
            "market": 0.15,
            "sentiment": 0.25,
            "money_flow": 0.10,
        }

        composite = (
            technical_score * weights["technical"]
            + valuation_score * weights["valuation"]
            + market_score * weights["market"]
            + sentiment_score * weights["sentiment"]
            + money_flow_score * weights["money_flow"]
        )

        direction = "up" if composite > 15 else "down" if composite < -15 else "neutral"

        return {
            "composite_score": round(composite, 1),
            "direction": direction,
            "weights": weights,
        }
