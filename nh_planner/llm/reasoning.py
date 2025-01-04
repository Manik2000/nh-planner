import json
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class ReasoningStep:
    description: str
    sql_query: Optional[str] = None
    result: Optional[str] = None
    error: Optional[str] = None


class ReasoningChain:
    def __init__(self):
        self.steps: List[ReasoningStep] = []

    def add_step(self, step: ReasoningStep):
        self.steps.append(step)

    def get_summary(self) -> str:
        """Get a summary of all steps for context"""
        summary = []
        for i, step in enumerate(self.steps, 1):
            summary.append(f"Step {i}: {step.description}")
            if step.sql_query:
                summary.append(f"Query: {step.sql_query}")
            if step.result:
                summary.append(f"Result: {step.result}")
            if step.error:
                summary.append(f"Error: {step.error}")
        return "\n".join(summary)
