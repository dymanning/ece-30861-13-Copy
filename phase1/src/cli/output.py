"""
output.py
-----------
Responsible for building and formatting output in NDJSON.

Summary
- Collects per-metric results.
- Computes weighted NetScore and accumulates latencies.
- Produces single-line JSON objects suitable for auto-grader validation.

Notes
import json

# single dict → NDJSON line
d = {"name":"bert-base-uncased","category":"MODEL","net_score": 0.95}
print(json.dumps(d))  # one line

"""

"""
=====================================================================
 Required Output Fields (NDJSON Schema)
=====================================================================

 Field Name                Type        Range/Options             Notes
 ---------------------------------------------------------------------
 name                      string      -                        Model / dataset / code name

 category                  string      [MODEL, DATASET, CODE]   Category type

 net_score                 float       0-1                      Overall quality score
 net_score_latency         int         milliseconds             Time to compute net_score

 ramp_up_time              float       0-1                      Ease of ramp-up
 ramp_up_time_latency      int         milliseconds             Time to compute ramp_up_time

 bus_factor                float       0-1                      Knowledge concentration (higher = safer)
 bus_factor_latency        int         milliseconds             Time to compute bus_factor

 performance_claims        float       0-1                      Evidence of claims (benchmarks, evals)
 performance_claims_latency int        milliseconds             Time to compute claims

 license                   float       0-1                      License clarity & permissiveness
 license_latency           int         milliseconds             Time to compute license info

 size_score                object      {str -> float}           Dictionary mapping hardware types to floats
                                           raspberry_pi          (0-1), indicating model size compatibility
                                           jetson_nano           with each device
                                           desktop_pc
                                           aws_server

 size_score_latency        int         milliseconds             Time to compute size score

 dataset_and_code_score    float       0-1                      If dataset + example code are well documented
 dataset_and_code_latency  int         milliseconds             Time to compute availability score

 dataset_quality           float       0-1                      Dataset quality
 dataset_quality_latency   int         milliseconds             Time to compute dataset quality

 code_quality              float       0-1                      Code style, maintainability
 code_quality_latency      int         milliseconds             Time to compute code quality

=====================================================================
"""

import json
from typing import Dict, List, Union, cast

from src.metrics.metric import Metric
from src.cli.url import ModelURL

def build_output(model: ModelURL, metrics: List[Metric], weights: Dict[str, float], net_latency: int) -> str:
    output: Dict[str, str | float | int | dict] = {
        "name": model.name or "",   # ensure str, never None
        "category": "MODEL",
    }

    net_score = 0.0

    for m in metrics:
        weight = weights[m.name]

        if m.name == "size_score" and isinstance(m.score, dict):
            avg_score = (
                m.score["raspberry_pi"]
                + m.score["jetson_nano"]
                + m.score["desktop_pc"]
                + m.score["aws_server"]
            ) / 4
            net_score += weight * avg_score
        elif isinstance(m.score, float):
            net_score += weight * m.score
        else:
            # Defensive: in case a metric fails and score is None
            net_score += 0.0

    # Use orchestrator-measured latency
    output["net_score"] = round(net_score, 2)
    output["net_score_latency"] = net_latency

    for m in metrics:
        output.update(m.as_dict())

    return json.dumps(output, separators=(",", ":"))
