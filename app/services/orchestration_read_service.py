"""Authorized read models for orchestration results, status, and provenance."""

import json
from html import escape
from html.parser import HTMLParser

import markdown

from app import db
from app.models.document import Document
from app.models.experiment import Experiment
from app.models.experiment_document import ExperimentDocument
from app.models.experiment_orchestration_run import ExperimentOrchestrationRun
from app.models.user import User
from app.services.base_service import NotFoundError, PermissionError
from app.services.orchestration_status_service import OrchestrationStatusService


class _SafeMarkdownHTMLParser(HTMLParser):
    """Keep formatting tags while discarding links, attributes, and active HTML."""

    ALLOWED_TAGS = {
        'p', 'br', 'strong', 'em', 'code', 'pre', 'blockquote',
        'ul', 'ol', 'li', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
        'table', 'thead', 'tbody', 'tr', 'th', 'td', 'hr',
    }
    VOID_TAGS = {'br', 'hr'}

    def __init__(self):
        super().__init__(convert_charrefs=False)
        self.output = []

    def handle_starttag(self, tag, attrs):
        if tag in self.ALLOWED_TAGS:
            self.output.append(f'<{tag}>')

    def handle_startendtag(self, tag, attrs):
        if tag in self.VOID_TAGS:
            self.output.append(f'<{tag}>')

    def handle_endtag(self, tag):
        if tag in self.ALLOWED_TAGS and tag not in self.VOID_TAGS:
            self.output.append(f'</{tag}>')

    def handle_data(self, data):
        self.output.append(escape(data))

    def handle_entityref(self, name):
        self.output.append(f'&{name};')

    def handle_charref(self, name):
        self.output.append(f'&#{name};')


class OrchestrationReadService:
    """Constrain orchestration read data to an experiment owner or administrator."""

    @classmethod
    def results_context(cls, experiment_id, run_id, actor_id):
        experiment, run = cls.authorized_run(
            run_id,
            actor_id,
            experiment_id=experiment_id,
        )
        documents = cls._documents(experiment)
        processing_results = cls._processing_results(run.processing_results)
        duration = cls._duration(run)
        return {
            'experiment': experiment,
            'run': run,
            'duration': duration,
            'total_operations': sum(
                len(results) for results in processing_results.values()
            ),
            'document_count': len(documents),
            'document_lookup': {
                str(document.id): cls._document(document)
                for document in documents
            },
            'processing_results': processing_results,
            'insights_html': cls._markdown(run.cross_document_insights),
            'evolution_html': cls._markdown(run.term_evolution_analysis),
            'temporal_periods': cls._temporal_periods(experiment),
        }

    @classmethod
    def run_provenance(cls, experiment_id, run_id, actor_id):
        _, run = cls.authorized_run(
            run_id,
            actor_id,
            experiment_id=experiment_id,
        )
        return {
            '@context': 'http://www.w3.org/ns/prov',
            '@type': 'prov:Bundle',
            'prov:generatedAtTime': (
                run.started_at.isoformat() if run.started_at else None
            ),
            'experiment': {
                '@id': f'experiment:{experiment_id}',
                '@type': 'prov:Entity',
                'prov:type': 'Experiment',
            },
            'orchestration_run': {
                '@id': f'run:{run.id}',
                '@type': 'prov:Activity',
                'prov:startedAtTime': (
                    run.started_at.isoformat() if run.started_at else None
                ),
                'prov:endedAtTime': (
                    run.completed_at.isoformat() if run.completed_at else None
                ),
                'prov:used': f'experiment:{experiment_id}',
                'status': run.status,
                'confidence': run.confidence,
            },
            'strategy': {
                '@id': f'strategy:{run.id}',
                '@type': 'prov:Entity',
                'prov:wasGeneratedBy': f'run:{run.id}',
                'recommended_strategy': cls._dictionary(run.recommended_strategy),
                'modified_strategy': cls._dictionary(run.modified_strategy),
                'reasoning': run.strategy_reasoning,
            },
            'execution_trace': (
                run.execution_trace if isinstance(run.execution_trace, list) else []
            ),
            'results': {
                '@id': f'results:{run.id}',
                '@type': 'prov:Entity',
                'prov:wasGeneratedBy': f'run:{run.id}',
                'cross_document_insights': run.cross_document_insights,
                'term_evolution_analysis': run.term_evolution_analysis,
            },
        }

    @classmethod
    def experiment_provenance(
        cls,
        experiment_id,
        actor_id,
        orchestration_service,
    ):
        cls.authorized_experiment(experiment_id, actor_id)
        return orchestration_service.get_orchestration_provenance(experiment_id)

    @classmethod
    def processing_status(cls, experiment_id, actor_id):
        cls.authorized_experiment(experiment_id, actor_id)
        return OrchestrationStatusService.get_experiment_processing_status(
            experiment_id
        )

    @classmethod
    def latest_run(cls, experiment_id, actor_id, status_service=None):
        cls.authorized_experiment(experiment_id, actor_id)
        service = status_service or OrchestrationStatusService()
        return service.get_latest_active_run(experiment_id)

    @classmethod
    def run_status(cls, run_id, actor_id):
        cls.authorized_run(run_id, actor_id)
        return OrchestrationStatusService.get_run_status(run_id)

    @staticmethod
    def authorized_experiment(experiment_id, actor_id):
        experiment = db.session.get(Experiment, experiment_id)
        if not experiment:
            raise NotFoundError('Experiment not found')
        actor = db.session.get(User, actor_id)
        if not actor or not actor.can_edit_resource(experiment):
            raise PermissionError('Permission denied')
        return experiment

    @classmethod
    def authorized_run(cls, run_id, actor_id, experiment_id=None):
        run = db.session.get(ExperimentOrchestrationRun, run_id)
        if not run or (
            experiment_id is not None and run.experiment_id != experiment_id
        ):
            raise NotFoundError('Orchestration run not found')
        experiment = cls.authorized_experiment(run.experiment_id, actor_id)
        return experiment, run

    @staticmethod
    def _documents(experiment):
        documents = {}
        associations = ExperimentDocument.query.filter_by(
            experiment_id=experiment.id
        ).all()
        for association in associations:
            if association.document:
                documents[association.document.id] = association.document
        for document in experiment.documents:
            documents[document.id] = document
        for document in Document.query.filter_by(
            experiment_id=experiment.id
        ).all():
            documents[document.id] = document
        return [documents[key] for key in sorted(documents)]

    @staticmethod
    def _document(document):
        return {
            'id': document.id,
            'uuid': str(document.uuid),
            'title': document.title or f'Document {document.id}',
            'authors': document.authors,
            'publication_date': (
                str(document.publication_date.year)
                if document.publication_date else None
            ),
            'version_number': document.version_number,
            'version_type': document.version_type,
        }

    @classmethod
    def _processing_results(cls, value):
        if not isinstance(value, dict):
            return {}
        normalized = {}
        for document_id, tool_results in value.items():
            if not isinstance(tool_results, dict):
                continue
            tools = {}
            for tool_name, result in tool_results.items():
                if isinstance(result, dict):
                    item = dict(result)
                else:
                    item = {'results': result}
                item['status'] = cls._status(item.get('status'))
                tools[str(tool_name)] = item
            normalized[str(document_id)] = tools
        return normalized

    @staticmethod
    def _status(value):
        if not isinstance(value, str) or not value.strip():
            return 'success'
        return value.strip().lower()[:30]

    @staticmethod
    def _duration(run):
        if not run.completed_at or not run.started_at:
            return None
        seconds = max(
            0.0,
            (run.completed_at - run.started_at).total_seconds(),
        )
        return {
            'seconds': seconds,
            'formatted': f'{int(seconds // 60)}m {int(seconds % 60)}s',
        }

    @staticmethod
    def _markdown(value):
        if not isinstance(value, str) or not value.strip():
            return None
        generated = markdown.markdown(
            escape(value.strip()),
            extensions=['fenced_code', 'tables', 'nl2br'],
        )
        sanitizer = _SafeMarkdownHTMLParser()
        sanitizer.feed(generated)
        sanitizer.close()
        return ''.join(sanitizer.output)

    @classmethod
    def _temporal_periods(cls, experiment):
        if experiment.experiment_type != 'temporal_evolution':
            return []
        config = cls._configuration(experiment)
        periods = config.get('time_periods') or config.get('named_periods') or []
        return periods if isinstance(periods, list) else []

    @staticmethod
    def _configuration(experiment):
        if isinstance(experiment.configuration, dict):
            return dict(experiment.configuration)
        if not experiment.configuration:
            return {}
        try:
            parsed = json.loads(experiment.configuration)
            return parsed if isinstance(parsed, dict) else {}
        except (json.JSONDecodeError, TypeError):
            return {}

    @staticmethod
    def _dictionary(value):
        return dict(value) if isinstance(value, dict) else {}
