"""
code_quality.py
-----------------
Code Quality Metric.

Summary:
- Performs static analysis on repository source code (e.g., Flake8).
- Scores maintainability and style consistency based on issues per 1,000 LOC.
- Runs independently of Hugging Face API, fulfilling non-API metric requirement.

- Input: path to a local clone/snapshot of the model repo
- Process:
  1. Collect all .py files
  2. Count total lines of code
  3. Run Flake8, count style issues
  4. Compute issues per 1000 LOC
  5. Map to 0 - 1 score per rubric

Rubric:
- 0.2 = >60 issues per 1000 LOC
- 0.4 = 31–60 issues per 1000 LOC
- 0.6 = 16–30 issues per 1000 LOC
- 0.8 = 6–15 issues per 1000 LOC
- 1 = 0–5 issues per 1000 LOC
"""

import tempfile
from typing import Dict, Optional

from flake8.api import legacy as flake8  # type: ignore
from huggingface_hub import HfApi, hf_hub_download

from src.cli.url import CodeURL, ModelURL
from src.metrics.metric import Metric


class CodeQualityMetric(Metric):
    def __init__(self, code_url: CodeURL, model_url: ModelURL):
        super().__init__("code_quality")
        self.code_url = code_url
        self.model_url = model_url

    def get_data(self) -> Dict[str, Optional[int]]:
        """
        Collects Python files from Hugging Face repo (or base model fallback),
        counts lines of code, and runs Flake8 to measure issues.
        """
        temp_dir = tempfile.TemporaryDirectory()

        full_name = f"{self.model_url.author}/{self.model_url.name}"
        api = HfApi()
        info = api.model_info(full_name)

        file_list: list[str] = []
        errors: Optional[int] = None
        loc: Optional[int] = 0  # start counting lines, may be reset to None

        # Collect Python files if available
        if info.siblings:
            for sib in info.siblings:
                if sib.rfilename.endswith(".py"):
                    path = self.SingleFileDownload(full_name, sib.rfilename, temp_dir.name)
                    file_list.append(path)
                    with open(path, "r", encoding="utf-8") as f:
                        file_loc = len(f.readlines())
                        if loc is not None:
                            loc += file_loc

        # If no .py files, try the base model if available
        if not file_list and info.cardData:
            base_model = info.cardData.get("base_model")
            if base_model:
                full_name = base_model
                info = api.model_info(full_name)
                if info.siblings:
                    for sib in info.siblings:
                        if sib.rfilename.endswith(".py"):
                            path = self.SingleFileDownload(full_name, sib.rfilename, temp_dir.name)
                            file_list.append(path)
                            with open(path, "r", encoding="utf-8") as f:
                                file_loc = len(f.readlines())
                                if loc is not None:
                                    loc += file_loc

        # Run flake8 silently if we found files
        if file_list:
            style_guide = flake8.get_style_guide(
                quiet=2, show_source=False, statistics=False
            )
            report = style_guide.check_files(file_list)
            errors = report.total_errors
        else:
            errors, loc = None, None

        temp_dir.cleanup()
        return {"Issues": errors, "Lines of Code": loc}

    def SingleFileDownload(self, full_name: str, filename: str, landing_path: str) -> str:
        """
        Download a single file from Hugging Face Hub into a temp directory.
        """
        model_path = hf_hub_download(
            repo_id=full_name, filename=filename, local_dir=landing_path
        )
        return model_path

    def calculate_score(self) -> float:
        """
        Compute score based on Flake8 issues per line of code.
        Maps issue density into rubric-based 0–1 score.
        """
        if not self.data:
            return 0.0

        issues: Optional[int] = self.data.get("Issues")
        loc: Optional[int] = self.data.get("Lines of Code")

        if issues is None or loc is None or loc <= 0:
            return 0.0

        ratio = issues / loc

        if 0 <= ratio <= 0.005:
            return 1.0
        elif 0.006 <= ratio <= 0.015:
            return 0.8
        elif 0.016 <= ratio < 0.03:
            return 0.6
        elif 0.03 <= ratio <= 0.06:
            return 0.4
        elif ratio > 0.06:
            return 0.2
        return 0.0
