"""
metrics_integration.py
----------------------
Integration with Phase 1 metrics system.

Imports and runs all Phase 1 metrics (bus_factor, code_quality, dataset_quality,
dataset_and_code, license, performance_claims, ramp_up_time, size) and returns
structured rating data for artifacts.
"""

import sys
import os
from typing import Dict, Any, Optional
import multiprocessing as mp

# Add phase1 to path so we can import its modules
phase1_path = os.path.join(os.path.dirname(__file__), '../../..', 'phase1')
if phase1_path not in sys.path:
    sys.path.insert(0, phase1_path)

from src.metrics.bus_factor import BusFactorMetric
from src.metrics.code_quality import CodeQualityMetric
from src.metrics.dataset_and_code import DatasetAndCodeMetric
from src.metrics.dataset_quality import DatasetQualityMetric
from src.metrics.performance_claims import PerformanceClaimsMetric
from src.metrics.ramp_up_time import RampUpTimeMetric
from src.metrics.size import SizeMetric
from src.cli.url import CodeURL, DatasetURL, ModelURL
from src.metrics.metric import Metric


def run_metric(metric: Metric) -> Metric:
    """Helper function to run a metric (for multiprocessing pool)."""
    metric.run()
    return metric


class MetricsIntegration:
    """Integration service for Phase 1 metrics."""
    
    # Default metric weights (from Phase 1)
    DEFAULT_WEIGHTS = {
        "ramp_up_time": 0.1,
        "bus_factor": 0.15,
        "performance_claims": 0.1,
        "size_score": 0.1,
        "dataset_and_code_score": 0.15,
        "dataset_quality": 0.15,
        "code_quality": 0.15,
    }
    
    @staticmethod
    def calculate_metrics(
        model_url: str,
        code_url: Optional[str] = None,
        dataset_url: Optional[str] = None,
        weights: Optional[Dict[str, float]] = None
    ) -> Dict[str, Any]:
        """
        Calculate all metrics for an artifact.
        
        Args:
            model_url: Hugging Face model URL (e.g., "username/model-name")
            code_url: GitHub code repository URL
            dataset_url: Hugging Face dataset URL
            weights: Custom metric weights (uses defaults if not provided)
            
        Returns:
            Dictionary with rating metrics and quality score
        """
        if weights is None:
            weights = MetricsIntegration.DEFAULT_WEIGHTS
        
        try:
            # Parse URLs
            model = ModelURL(model_url)
            code = CodeURL(code_url) if code_url else None
            dataset = DatasetURL(dataset_url) if dataset_url else None
            
            # Initialize metrics
            metrics = [
                RampUpTimeMetric(model),
                BusFactorMetric(code, model),
                PerformanceClaimsMetric(model),
                SizeMetric(model),
                DatasetAndCodeMetric(model),
                DatasetQualityMetric(dataset),
                CodeQualityMetric(code, model),
            ]
            
            # Run metrics in parallel
            with mp.Pool(processes=min(len(metrics), mp.cpu_count())) as pool:
                metrics = pool.map(run_metric, metrics)
            
            # Aggregate scores
            rating = MetricsIntegration._build_rating(metrics, weights)
            
            return rating
            
        except Exception as e:
            # Return default scores on error
            return MetricsIntegration._default_rating()
    
    @staticmethod
    def _build_rating(metrics: list, weights: Dict[str, float]) -> Dict[str, Any]:
        """Build rating structure from metric scores."""
        rating = {}
        quality_score = 0.0
        
        for m in metrics:
            weight = weights.get(m.name, 0.0)
            
            if m.name == "size_score" and isinstance(m.score, dict):
                # Extract size_score structure
                rating["size_score"] = {
                    "raspberry_pi": m.score.get("raspberry_pi", 0.0),
                    "jetson_nano": m.score.get("jetson_nano", 0.0),
                    "desktop_pc": m.score.get("desktop_pc", 0.0),
                    "aws_server": m.score.get("aws_server", 0.0),
                }
                # Use average for quality calculation
                avg_score = sum(rating["size_score"].values()) / len(rating["size_score"])
                quality_score += weight * avg_score
            else:
                # Regular float score
                score = float(m.score) if m.score is not None else 0.0
                rating[m.name] = score
                quality_score += weight * score
        
        # Add overall quality score
        rating["quality"] = round(quality_score, 2)
        
        return rating
    
    @staticmethod
    def _default_rating() -> Dict[str, Any]:
        """Return default rating when metrics fail."""
        return {
            "quality": 0.0,
            "size_score": {
                "raspberry_pi": 0.0,
                "jetson_nano": 0.0,
                "desktop_pc": 0.0,
                "aws_server": 0.0,
            },
            "code_quality": 0.0,
            "dataset_quality": 0.0,
            "performance_claims": 0.0,
            "bus_factor": 0.0,
            "ramp_up_time": 0.0,
            "dataset_and_code_score": 0.0,
        }
