"""
Pipeline Status Manager

Provides real-time status updates for document processing pipelines
using WebSocket communication. Tracks progress through the 6-stage
temporal semantic evolution analysis pipeline.
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional
from enum import Enum

logger = logging.getLogger(__name__)


class StageStatus(Enum):
    """Pipeline stage status types."""
    PENDING = "pending"
    ACTIVE = "active"
    COMPLETED = "completed"
    ERROR = "error"
    SKIPPED = "skipped"


class PipelineStatusManager:
    """
    Manages real-time pipeline status updates via WebSockets.
    
    Provides status tracking for the 6-stage document processing pipeline:
    1. Document Intake & Analysis
    2. LLM Analysis & Tool Selection  
    3. NLP Processing Pipeline
    4. Semantic Drift Analysis
    5. Result Interpretation
    6. Output Generation
    """
    
    PIPELINE_STAGES = {
        'document_intake': {
            'name': 'Document Intake & Analysis',
            'steps': [
                'uploading_document',
                'extracting_text',
                'detecting_format',
                'extracting_metadata',
                'validating_content'
            ]
        },
        'llm_analysis': {
            'name': 'LLM Analysis & Tool Selection',
            'steps': [
                'analyzing_content',
                'selecting_nlp_tools',
                'determining_time_period',
                'choosing_embedding_models',
                'configuring_parameters'
            ]
        },
        'nlp_processing': {
            'name': 'Multi-Tool NLP Processing',
            'steps': [
                'running_spacy_pipeline',
                'extracting_collocations',
                'generating_embeddings',
                'calculating_features',
                'processing_dependencies'
            ]
        },
        'semantic_analysis': {
            'name': 'Semantic Drift Analysis',
            'steps': [
                'calculating_drift_metrics',
                'analyzing_neighborhoods',
                'comparing_periods',
                'generating_confidence_scores',
                'detecting_change_patterns'
            ]
        },
        'interpretation': {
            'name': 'LLM Result Interpretation',
            'steps': [
                'interpreting_nlp_results',
                'synthesizing_findings',
                'generating_insights',
                'validating_conclusions',
                'calculating_overall_confidence'
            ]
        },
        'output_generation': {
            'name': 'Output Generation',
            'steps': [
                'structuring_results',
                'generating_narratives',
                'creating_visualizations',
                'saving_experiment',
                'preparing_export'
            ]
        }
    }
    
    def __init__(self, socketio=None):
        """
        Initialize the pipeline status manager.
        
        Args:
            socketio: Flask-SocketIO instance for WebSocket communication
        """
        self.socketio = socketio
        self._active_pipelines: Dict[str, Dict[str, Any]] = {}
        
        if not socketio:
            logger.warning("No SocketIO instance provided - status updates will be logged only")
    
    async def start_pipeline(self, experiment_id: str, 
                           pipeline_config: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Initialize a new pipeline processing session.
        
        Args:
            experiment_id: Unique identifier for the experiment
            pipeline_config: Pipeline configuration and metadata
            
        Returns:
            Pipeline initialization status
        """
        config = pipeline_config or {}
        
        pipeline_status = {
            'experiment_id': experiment_id,
            'status': 'initialized',
            'start_time': datetime.utcnow().isoformat(),
            'current_stage': 'document_intake',
            'total_stages': len(self.PIPELINE_STAGES),
            'completed_stages': 0,
            'config': config,
            'stage_details': {
                stage_id: {
                    'status': StageStatus.PENDING.value,
                    'progress': 0,
                    'start_time': None,
                    'end_time': None,
                    'details': '',
                    'error_message': None,
                    'substeps': {
                        step: {'status': StageStatus.PENDING.value, 'progress': 0}
                        for step in stage_data['steps']
                    }
                }
                for stage_id, stage_data in self.PIPELINE_STAGES.items()
            }
        }
        
        self._active_pipelines[experiment_id] = pipeline_status
        
        # Emit pipeline started event
        await self._emit_update(experiment_id, 'pipeline_started', {
            'total_stages': len(self.PIPELINE_STAGES),
            'stages': list(self.PIPELINE_STAGES.keys()),
            'config': config
        })
        
        logger.info(f"Pipeline started for experiment {experiment_id}")
        return pipeline_status
    
    async def update_stage_status(self, 
                                experiment_id: str, 
                                stage: str, 
                                status: StageStatus, 
                                details: str = "",
                                progress: Optional[int] = None,
                                metadata: Dict[str, Any] = None) -> None:
        """
        Update the status of a pipeline stage.
        
        Args:
            experiment_id: Experiment identifier
            stage: Stage identifier (must be in PIPELINE_STAGES)
            status: New status for the stage
            details: Human-readable status details
            progress: Progress percentage (0-100)
            metadata: Additional metadata for the stage
        """
        if experiment_id not in self._active_pipelines:
            logger.error(f"Pipeline {experiment_id} not found")
            return
        
        if stage not in self.PIPELINE_STAGES:
            logger.error(f"Unknown stage: {stage}")
            return
        
        pipeline = self._active_pipelines[experiment_id]
        stage_info = pipeline['stage_details'][stage]
        
        # Update stage status
        old_status = stage_info['status']
        stage_info['status'] = status.value
        stage_info['details'] = details
        
        if progress is not None:
            stage_info['progress'] = max(0, min(100, progress))
        
        # Set timestamps
        current_time = datetime.utcnow().isoformat()
        
        if status == StageStatus.ACTIVE and old_status == StageStatus.PENDING.value:
            stage_info['start_time'] = current_time
            pipeline['current_stage'] = stage
        elif status in [StageStatus.COMPLETED, StageStatus.ERROR, StageStatus.SKIPPED]:
            stage_info['end_time'] = current_time
            if status == StageStatus.COMPLETED:
                stage_info['progress'] = 100
                pipeline['completed_stages'] += 1
        
        # Add metadata
        if metadata:
            stage_info['metadata'] = stage_info.get('metadata', {})
            stage_info['metadata'].update(metadata)
        
        # Emit update
        await self._emit_update(experiment_id, 'stage_update', {
            'stage': stage,
            'stage_name': self.PIPELINE_STAGES[stage]['name'],
            'status': status.value,
            'details': details,
            'progress': stage_info['progress'],
            'start_time': stage_info['start_time'],
            'end_time': stage_info['end_time'],
            'metadata': stage_info.get('metadata', {})
        })
        
        logger.info(f"Pipeline {experiment_id} - Stage {stage}: {status.value} - {details}")
    
    async def update_substep_progress(self, 
                                    experiment_id: str, 
                                    stage: str, 
                                    substep: str, 
                                    progress: int,
                                    details: str = "") -> None:
        """
        Update progress of a substep within a stage.
        
        Args:
            experiment_id: Experiment identifier
            stage: Stage identifier
            substep: Substep identifier
            progress: Progress percentage (0-100)
            details: Status details for the substep
        """
        if experiment_id not in self._active_pipelines:
            return
        
        pipeline = self._active_pipelines[experiment_id]
        
        if stage not in pipeline['stage_details']:
            return
        
        stage_info = pipeline['stage_details'][stage]
        
        if substep not in stage_info['substeps']:
            logger.warning(f"Unknown substep {substep} in stage {stage}")
            return
        
        # Update substep
        substep_info = stage_info['substeps'][substep]
        substep_info['progress'] = max(0, min(100, progress))
        substep_info['details'] = details
        
        if progress >= 100:
            substep_info['status'] = StageStatus.COMPLETED.value
        elif progress > 0:
            substep_info['status'] = StageStatus.ACTIVE.value
        
        # Calculate overall stage progress from substeps
        total_substeps = len(stage_info['substeps'])
        completed_progress = sum(
            sub['progress'] for sub in stage_info['substeps'].values()
        )
        stage_progress = int(completed_progress / total_substeps)
        stage_info['progress'] = stage_progress
        
        # Emit substep update
        await self._emit_update(experiment_id, 'substep_update', {
            'stage': stage,
            'substep': substep,
            'progress': progress,
            'details': details,
            'stage_progress': stage_progress
        })
    
    async def add_stage_error(self, 
                            experiment_id: str, 
                            stage: str, 
                            error_message: str,
                            error_details: Dict[str, Any] = None) -> None:
        """
        Add an error to a pipeline stage.
        
        Args:
            experiment_id: Experiment identifier
            stage: Stage identifier
            error_message: Human-readable error message
            error_details: Additional error details and metadata
        """
        if experiment_id not in self._active_pipelines:
            return
        
        pipeline = self._active_pipelines[experiment_id]
        
        if stage in pipeline['stage_details']:
            stage_info = pipeline['stage_details'][stage]
            stage_info['error_message'] = error_message
            stage_info['error_details'] = error_details or {}
        
        await self.update_stage_status(
            experiment_id, stage, StageStatus.ERROR, 
            f"Error: {error_message}", metadata=error_details
        )
        
        # Emit error event
        await self._emit_update(experiment_id, 'stage_error', {
            'stage': stage,
            'error_message': error_message,
            'error_details': error_details
        })
        
        logger.error(f"Pipeline {experiment_id} - Stage {stage} error: {error_message}")
    
    async def complete_pipeline(self, 
                              experiment_id: str, 
                              results: Dict[str, Any] = None) -> None:
        """
        Mark pipeline as completed and emit final results.
        
        Args:
            experiment_id: Experiment identifier
            results: Final pipeline results
        """
        if experiment_id not in self._active_pipelines:
            return
        
        pipeline = self._active_pipelines[experiment_id]
        pipeline['status'] = 'completed'
        pipeline['end_time'] = datetime.utcnow().isoformat()
        pipeline['results'] = results or {}
        
        # Calculate total processing time
        start_time = datetime.fromisoformat(pipeline['start_time'].replace('Z', '+00:00'))
        end_time = datetime.fromisoformat(pipeline['end_time'].replace('Z', '+00:00'))
        processing_time = (end_time - start_time).total_seconds()
        
        pipeline['processing_time_seconds'] = processing_time
        
        # Emit completion event
        await self._emit_update(experiment_id, 'pipeline_completed', {
            'processing_time': processing_time,
            'completed_stages': pipeline['completed_stages'],
            'total_stages': pipeline['total_stages'],
            'results': results
        })
        
        logger.info(f"Pipeline {experiment_id} completed in {processing_time:.1f} seconds")
    
    async def _emit_update(self, 
                          experiment_id: str, 
                          event_type: str, 
                          data: Dict[str, Any]) -> None:
        """
        Emit WebSocket update to connected clients.
        
        Args:
            experiment_id: Experiment identifier
            event_type: Type of update event
            data: Event data to send
        """
        if not self.socketio:
            logger.debug(f"Pipeline {experiment_id} - {event_type}: {data}")
            return
        
        update_data = {
            'experiment_id': experiment_id,
            'event_type': event_type,
            'timestamp': datetime.utcnow().isoformat(),
            **data
        }
        
        try:
            await self.socketio.emit(
                'pipeline_update', 
                update_data, 
                room=f'experiment_{experiment_id}'
            )
        except Exception as e:
            logger.error(f"Failed to emit pipeline update: {e}")
    
    def get_pipeline_status(self, experiment_id: str) -> Optional[Dict[str, Any]]:
        """
        Get current status of a pipeline.
        
        Args:
            experiment_id: Experiment identifier
            
        Returns:
            Pipeline status data or None if not found
        """
        return self._active_pipelines.get(experiment_id)
    
    def get_active_pipelines(self) -> List[str]:
        """
        Get list of active pipeline experiment IDs.
        
        Returns:
            List of experiment IDs with active pipelines
        """
        return [
            exp_id for exp_id, pipeline in self._active_pipelines.items()
            if pipeline['status'] in ['initialized', 'running']
        ]
    
    def cleanup_completed_pipelines(self, max_age_hours: int = 24) -> int:
        """
        Clean up old completed pipelines to free memory.
        
        Args:
            max_age_hours: Maximum age in hours before cleanup
            
        Returns:
            Number of pipelines cleaned up
        """
        current_time = datetime.utcnow()
        expired_pipelines = []
        
        for exp_id, pipeline in self._active_pipelines.items():
            if pipeline['status'] in ['completed', 'failed']:
                end_time_str = pipeline.get('end_time')
                if end_time_str:
                    end_time = datetime.fromisoformat(end_time_str.replace('Z', '+00:00'))
                    age_hours = (current_time - end_time).total_seconds() / 3600
                    
                    if age_hours > max_age_hours:
                        expired_pipelines.append(exp_id)
        
        # Remove expired pipelines
        for exp_id in expired_pipelines:
            del self._active_pipelines[exp_id]
            logger.info(f"Cleaned up expired pipeline: {exp_id}")
        
        return len(expired_pipelines)


# Global pipeline manager instance
_pipeline_manager = None


def get_pipeline_manager(socketio=None) -> PipelineStatusManager:
    """Get the global pipeline status manager."""
    global _pipeline_manager
    if _pipeline_manager is None:
        _pipeline_manager = PipelineStatusManager(socketio)
    elif socketio and not _pipeline_manager.socketio:
        _pipeline_manager.socketio = socketio
    return _pipeline_manager


def reset_pipeline_manager():
    """Reset the global pipeline manager (for testing)."""
    global _pipeline_manager
    _pipeline_manager = None