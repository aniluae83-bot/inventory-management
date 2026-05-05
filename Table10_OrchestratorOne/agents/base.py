"""Abstract base for all OrchestratorOne specialist agents."""
from __future__ import annotations
from abc import ABC, abstractmethod
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent))
from orchestrator import WorkstreamAnalysis

class SpecialistAgent(ABC):
    workstream: str

    @abstractmethod
    def run(
        self,
        intake_deal_id: str,
        intake_target: str,
        document_text: str,
        document_type: str,
        counterparty_countries: list[str],
        verbose: bool = False,
    ) -> WorkstreamAnalysis: ...
