"""Shared dependencies for experiment orchestration routes."""

import logging

from app.services.orchestration_service import get_orchestration_service

logger = logging.getLogger("app.routes.experiments.orchestration")
orchestration_service = get_orchestration_service()
