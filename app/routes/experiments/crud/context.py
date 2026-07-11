"""Shared dependencies for experiment CRUD routes."""

import logging

from app.services.experiment_service import get_experiment_service

logger = logging.getLogger("app.routes.experiments.crud")
experiment_service = get_experiment_service()
