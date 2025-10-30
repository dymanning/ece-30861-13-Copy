"""
main.py
---------
Top-level program dispatcher.

Summary
- Entry point invoked by the ./run script.
- Loads URL input (file or inline).
- Delegates handling to the URL factory and model handler.
- Orchestrates metric execution and output generation.
"""
# Phase 1 Imports
import multiprocessing as mp
import sys
import time
from typing import Any

from src.cli.cli import parse_args, parse_url_file
from src.cli.output import build_output
from src.git import validate_github_token
from src.logging import setup_logger, validate_log_file
from src.metrics.bus_factor import BusFactorMetric
from src.metrics.code_quality import CodeQualityMetric
from src.metrics.dataset_and_code import DatasetAndCodeMetric
from src.metrics.dataset_quality import DatasetQualityMetric
from src.metrics.license import LicenseMetric
from src.metrics.performance_claims import PerformanceClaimsMetric
from src.metrics.ramp_up_time import RampUpTimeMetric
from src.metrics.size import SizeMetric

# CloudWatch Logging Setup
import logging
import watchtower
import boto3

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

session = boto3.Session()
handler = watchtower.CloudWatchLogHandler(
    log_group="TrustworthyRegistryLogs",
    stream_name="app-stream",
    boto3_session=session
)
logger.addHandler(handler)
logger.info("Application started successfully.")


# Phase 1 Implementation
def run_metric(metric: Any) -> Any:
    metric.run()
    return metric


def main(argv=None):
    log_file = validate_log_file()
    validate_github_token()

    setup_logger(log_file)

    cli_args = parse_args(argv)

    if cli_args.command == "process":
        lines = parse_url_file(cli_args.url_file)

        # Define metric weights (adjust as needed)
        weights = {
            "ramp_up_time": 0.1,
            "bus_factor": 0.15,
            "performance_claims": 0.1,
            "license": 0.1,
            "size_score": 0.1,
            "dataset_and_code_score": 0.15,
            "dataset_quality": 0.15,
            "code_quality": 0.15,
        }

        results = []
        for line in lines:
            code_url, dataset_url, model_url = line

            metrics = [
                RampUpTimeMetric(model_url),
                BusFactorMetric(code_url, model_url),
                PerformanceClaimsMetric(model_url),
                LicenseMetric(model_url),
                SizeMetric(model_url),
                DatasetAndCodeMetric(model_url),
                DatasetQualityMetric(dataset_url),
                CodeQualityMetric(code_url, model_url),
            ]

            output_str = ""
            # If line contains a model url, process it
            if model_url:
                start = time.time()
                with mp.Pool(processes=min(len(metrics), mp.cpu_count())) as pool:
                    metrics = pool.map(run_metric, metrics)
                net_latency = int((time.time() - start) * 1000)

                output_str = build_output(
                    model_url, metrics, weights, net_latency)
                results.append(output_str)
            if not model_url:
                print(f"Skipping line (no model url): {lines}", file=sys.stderr)
                continue

        for r in results:
            print(r)


# Allows us to run with 'python3 main.py [args]'
if __name__ == "__main__":
    main(sys.argv[1:])
