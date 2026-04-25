from __future__ import annotations

from packages.core_domain.service_interaction_chat import ChatCommandControllerMixin
from packages.core_domain.service_interaction_cluster import ClusterPlanningServiceMixin
from packages.core_domain.service_interaction_session import InteractionSessionServiceMixin


class InteractionServiceMixin(
    ChatCommandControllerMixin,
    ClusterPlanningServiceMixin,
    InteractionSessionServiceMixin,
):
    """Interaction facade composed from focused service mixins."""

