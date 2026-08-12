"""RIC meta models."""


from typing import Literal

from pydantic import Field

from orchestrator.models.meta.common import Category5G, Component5G


# TODO later
class RIC(Component5G):
    """5G RAN Intelligent Controller."""

    category: Literal[Category5G.RIC] = Field(default=Category5G.RIC, frozen=True)
