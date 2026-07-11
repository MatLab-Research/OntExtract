"""Shared dependencies for experiment temporal routes."""

import logging

from app.services.ontserve_client import get_ontserve_client
from app.services.temporal_service import get_temporal_service

logger = logging.getLogger("app.routes.experiments.temporal")
temporal_service = get_temporal_service()
ontserve_client = get_ontserve_client()
