from __future__ import annotations
from dataclasses import dataclass
from typing import Optional
import re
from abc import ABC, abstractmethod

@dataclass
class URL(ABC):
    raw: str
    url_type: str
    author: Optional[str] = None
    name: Optional[str] = None

    @abstractmethod
    def validate(self) -> bool:
        """Return True if the URL is valid for this type."""
        pass

    def display_name(self) -> str:
        return f"{self.author}/{self.name}" if self.author and self.name else self.raw


HF_MODEL_PATTERN = re.compile(r"^https?://huggingface\.co/([^/]+)/([^/]+)")

class ModelURL(URL):
    def __init__(self, raw: str):
        super().__init__(raw, "model")
        m = HF_MODEL_PATTERN.match(raw)
        if m:
            self.author = m.group(1)
            self.name = m.group(2)

    def validate(self) -> bool:
        return bool(HF_MODEL_PATTERN.match(self.raw))
    

HF_DATASET_PATTERN = re.compile(r"^https?://huggingface\.co/datasets/([^/]+)/([^/]+)")
IMAGENET_PATTERN = re.compile(r"^https?://www\.image-net\.org/data/.*")

class DatasetURL(URL):
    def __init__(self, raw: str):
        super().__init__(raw, "dataset")
        m = HF_DATASET_PATTERN.match(raw)
        if m:
            self.author = m.group(1)
            self.name = m.group(2)
        elif IMAGENET_PATTERN.match(raw):
            # ImageNet doesn’t use the same style, but keep fields consistent
            self.author = "imagenet"
            self.name = "imagenet"

    def validate(self) -> bool:
        return bool(HF_DATASET_PATTERN.match(self.raw) or IMAGENET_PATTERN.match(self.raw))


GITHUB_PATTERN = re.compile(r"^https?://github\.com/([^/]+)/([^/]+)")
GITLAB_PATTERN = re.compile(r"^https?://gitlab\.com/([^/]+)/([^/]+)")
HF_SPACES_PATTERN = re.compile(r"^https?://huggingface\.co/spaces/([^/]+)/([^/]+)")

class CodeURL(URL):
    def __init__(self, raw: str):
        super().__init__(raw, "code")
        for pattern, provider in [
            (GITHUB_PATTERN, "github"),
            (GITLAB_PATTERN, "gitlab"),
            (HF_SPACES_PATTERN, "huggingface_spaces"),
        ]:
            m = pattern.match(raw)
            if m:
                self.author = m.group(1)
                self.name = m.group(2)
                break

    def validate(self) -> bool:
        return bool(
            GITHUB_PATTERN.match(self.raw)
            or GITLAB_PATTERN.match(self.raw)
            or HF_SPACES_PATTERN.match(self.raw)
        )
    

def classify_url(raw: str) -> Optional[URL]:
    # 1. Hugging Face datasets (or ImageNet)
    if HF_DATASET_PATTERN.match(raw) or IMAGENET_PATTERN.match(raw):
        return DatasetURL(raw)

    # 2. Code hosting (GitHub, GitLab, Hugging Face Spaces)
    if (
        GITHUB_PATTERN.match(raw)
        or GITLAB_PATTERN.match(raw)
        or HF_SPACES_PATTERN.match(raw)
    ):
        return CodeURL(raw)

    # 3. Hugging Face models
    if HF_MODEL_PATTERN.match(raw):
        return ModelURL(raw)

    # 4. Anything else → unsupported
    return None

