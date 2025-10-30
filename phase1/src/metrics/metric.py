"""
metric.py
---------------
Abstract base class for project metrics.

Summary
Each metric:
- Has a unique name.
- Stores the raw data it needs for calculation.
- Computes a score in the range [0,1].
- Records its own computation latency (milliseconds).
- Exports results in a dict format for NDJSON output.

To add a new metric:
1. Subclass Metric.
2. Implement calculate_score(self) using self.data.
3. Optionally override __init__ to set a default name.
"""

import time
from typing import Any, Dict, Optional, Union


class Metric():
    """
    Base class for all metrics.

    Attributes:
        name (str): Unique identifier for the metric.
        data (dict): Parsed metadata required for scoring.
        score (float): Computed score in [0,1].
        latency (int): Computation time in milliseconds.

    Subclasses must implement:
        calculate_score(self) -> float
    """

    def __init__(self, name: str):
        self.name = name
        self.data: Optional[Dict[str, Any]] = None
        self.score: Optional[Union[float, Dict[str, float]]] = None
        self.latency: Optional[int] = None

    def get_data(self) -> Dict[str, Any]:
        """Optionally fetch data. Default is empty dict."""
        return {}

    def set_data(self, data: Dict[str, Any]) -> None:
        """Attach metadata needed to calculate metric."""
        self.data = data

    def calculate_score(self) -> Union[float, Dict[str, float]]:
        """
        Compute the metric score.

        Must be implemented by subclasses.
        Should return a float [0, 1]
        """
        return 0.0
    
    def run(self) -> None:
        """
        Calculates metric with latency and sets fields.
        If anything fails, fallback score is 0 (float or dict depending on metric type).
        """
        start = time.time()
        try:
            if self.data is None:
                self.data = self.get_data()
            self.score = self.calculate_score()
        except Exception:
            # Detect if metric is supposed to return a dict (like size_score)
            if self.name == "size_score":
                self.score = {
                    "raspberry_pi": 0.0,
                    "jetson_nano": 0.0,
                    "desktop_pc": 0.0,
                    "aws_server": 0.0,
                }
            else:
                self.score = 0.0
            self.data = {}
        finally:
            self.latency = int((time.time() - start) * 1000)


    def as_dict(self) -> Dict[str, Any]:
        """
        Returns metric data as a dictionary, supports both float and dict scores.
        """
        if isinstance(self.score, dict):
            return {
                self.name: self.score,
                f"{self.name}_latency": self.latency,
            }
        else:
            return {
                self.name: float(self.score) if self.score is not None else 0.0,
                f"{self.name}_latency": self.latency,
            }