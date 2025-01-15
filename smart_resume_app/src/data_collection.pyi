from typing import Dict, Any, Optional
from pathlib import Path


class DataAnonymizer:
    patterns: Dict[str, str]

    def __init__(self) -> None: ...

    def anonymize_text(self, text: str) -> str: ...

    def add_pattern(self, name: str, pattern: str) -> None: ...


class DataCollector:
    storage_path: Path
    anonymizer: DataAnonymizer

    def __init__(self, storage_path: str = ...) -> None: ...

    def save_training_data(
        self,
        resume_text: str,
        job_description: str,
        tailored_output: str,
        extra_metadata: Optional[Dict[str, Any]] = None
    ) -> None: ...

    def get_training_stats(self) -> Dict[str, Any]: ...
