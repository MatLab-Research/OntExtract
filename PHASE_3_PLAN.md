# Phase 3: Business Logic Extraction Plan

**Started**: November 16, 2025
**Goal**: Extract business logic from routes into dedicated service classes

---

## Current State Analysis

### Business Logic Found in Routes

#### experiments/crud.py (405 lines)
- ❌ Validation logic (required fields, document/reference selection)
- ❌ Experiment creation logic
- ❌ Document/reference association logic
- ❌ Database operations scattered throughout
- ❌ JSON serialization/deserialization

#### experiments/pipeline.py (844 lines)
- ❌ Complex processing status aggregation
- ❌ Progress calculation logic
- ❌ Operation type counting
- ❌ Status determination
- ❌ Data transformation for views

#### processing routes
- ❌ Job management logic
- ❌ Batch processing coordination
- ❌ Status tracking

---

## Refactoring Strategy

### Phase 3.1: Foundation (This Session)
**Time**: 2-3 hours

Create base infrastructure for business logic extraction:

1. **Base Service Class** (`app/services/base_service.py`)
   - Common functionality for all services
   - Database session management
   - Error handling utilities
   - Logging setup

2. **DTOs with Pydantic** (`app/dto/`)
   - Request DTOs for validation
   - Response DTOs for consistent API responses
   - Automatic validation and serialization

3. **Service Layer Structure**
   ```
   app/services/
   ├── base_service.py
   ├── experiment_service.py      # NEW
   ├── document_service.py         # NEW
   ├── processing_service.py       # NEW
   └── [existing services...]
   ```

4. **DTO Structure**
   ```
   app/dto/
   ├── __init__.py
   ├── base.py                     # Base DTO classes
   ├── experiment_dto.py           # Experiment-related DTOs
   ├── document_dto.py             # Document-related DTOs
   └── processing_dto.py           # Processing-related DTOs
   ```

### Phase 3.2: Experiment Service (Next Session)
**Time**: 3-4 hours

Extract business logic from experiments routes:

1. **ExperimentService** (`app/services/experiment_service.py`)
   - `create_experiment(data: CreateExperimentDTO) -> Experiment`
   - `update_experiment(id, data: UpdateExperimentDTO) -> Experiment`
   - `delete_experiment(id) -> bool`
   - `get_experiment(id) -> Experiment`
   - `list_experiments(filters) -> List[Experiment]`
   - `add_documents_to_experiment(experiment_id, document_ids)`
   - `add_references_to_experiment(experiment_id, reference_ids)`

2. **DTOs**
   - `CreateExperimentDTO` - Validate experiment creation data
   - `UpdateExperimentDTO` - Validate experiment updates
   - `ExperimentResponseDTO` - Consistent API responses

3. **Route Refactoring**
   - experiments/crud.py becomes thin controller
   - All validation in DTOs
   - All business logic in ExperimentService
   - Routes just coordinate: validate → call service → return response

### Phase 3.3: Processing Service (Future Session)
**Time**: 3-4 hours

Extract processing pipeline logic:

1. **ProcessingService** (`app/services/processing_service.py`)
   - `get_document_pipeline_status(experiment_id) -> PipelineStatusDTO`
   - `calculate_processing_progress(exp_doc_id) -> ProgressData`
   - `start_document_processing(exp_doc_id, processing_type)`
   - `get_processing_artifacts(processing_id) -> List[Artifact]`

2. **Complex Logic Extraction**
   - Operation counting logic → service method
   - Progress calculation → service method
   - Status aggregation → service method

---

## Implementation Pattern

### Before (Route with Business Logic)

```python
@experiments_bp.route('/create', methods=['POST'])
@api_require_login_for_write
def create():
    """Create a new experiment - requires login"""
    try:
        data = request.get_json()

        # VALIDATION LOGIC (should be in DTO)
        if not data.get('name'):
            return jsonify({'error': 'Experiment name is required'}), 400

        if not data.get('experiment_type'):
            return jsonify({'error': 'Experiment type is required'}), 400

        # BUSINESS LOGIC (should be in service)
        experiment = Experiment(
            name=data['name'],
            description=data.get('description', ''),
            experiment_type=data['experiment_type'],
            user_id=current_user.id,
            configuration=json.dumps(data.get('configuration', {}))
        )

        db.session.add(experiment)
        db.session.flush()

        # More business logic...
        for doc_id in data.get('document_ids', []):
            document = Document.query.filter_by(id=doc_id).first()
            if document:
                experiment.add_document(document)

        db.session.commit()

        return jsonify({
            'success': True,
            'experiment_id': experiment.id
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500
```

### After (Thin Controller with Service)

```python
# app/dto/experiment_dto.py
from pydantic import BaseModel, Field, validator
from typing import List, Optional, Dict

class CreateExperimentDTO(BaseModel):
    """DTO for experiment creation with validation"""
    name: str = Field(..., min_length=1, max_length=200)
    description: Optional[str] = Field(None, max_length=2000)
    experiment_type: str = Field(..., regex='^(temporal_analysis|semantic_drift|domain_comparison)$')
    document_ids: List[int] = Field(default_factory=list)
    reference_ids: List[int] = Field(default_factory=list)
    configuration: Dict = Field(default_factory=dict)

    @validator('document_ids', 'reference_ids')
    def validate_at_least_one_document(cls, v, values):
        """Ensure at least one document or reference"""
        if 'document_ids' in values:
            if len(values['document_ids']) == 0 and len(v) == 0:
                raise ValueError('At least one document or reference required')
        return v

class ExperimentResponseDTO(BaseModel):
    """DTO for experiment API responses"""
    success: bool
    experiment_id: Optional[int] = None
    message: Optional[str] = None
    error: Optional[str] = None

# app/services/experiment_service.py
class ExperimentService(BaseService):
    """Business logic for experiment operations"""

    def create_experiment(self, data: CreateExperimentDTO, user_id: int) -> Experiment:
        """
        Create a new experiment

        Args:
            data: Validated experiment data
            user_id: ID of user creating experiment

        Returns:
            Created experiment instance
        """
        # Business logic here
        experiment = Experiment(
            name=data.name,
            description=data.description,
            experiment_type=data.experiment_type,
            user_id=user_id,
            configuration=json.dumps(data.configuration)
        )

        db.session.add(experiment)
        db.session.flush()

        # Add documents
        for doc_id in data.document_ids:
            document = Document.query.filter_by(id=doc_id).first()
            if document:
                experiment.add_document(document)

        # Add references
        for ref_id in data.reference_ids:
            reference = Document.query.filter_by(id=ref_id, document_type='reference').first()
            if reference:
                experiment.add_reference(reference, include_in_analysis=True)

        db.session.commit()

        return experiment

# app/routes/experiments/crud.py (AFTER - Thin Controller)
@experiments_bp.route('/create', methods=['POST'])
@api_require_login_for_write
def create():
    """Create a new experiment - requires login"""
    try:
        # Validate using DTO (automatic validation)
        data = CreateExperimentDTO(**request.get_json())

        # Call service (all business logic there)
        experiment = experiment_service.create_experiment(data, current_user.id)

        # Return response DTO
        return ExperimentResponseDTO(
            success=True,
            experiment_id=experiment.id,
            message='Experiment created successfully'
        ).dict(), 201

    except ValidationError as e:
        return ExperimentResponseDTO(
            success=False,
            error=str(e)
        ).dict(), 400
    except Exception as e:
        logger.error(f"Error creating experiment: {e}")
        return ExperimentResponseDTO(
            success=False,
            error='Failed to create experiment'
        ).dict(), 500
```

---

## Benefits

### ✅ Testability
- Business logic can be tested without Flask context
- Mock database easily
- Unit test DTOs independently

### ✅ Reusability
- Same business logic can be used from:
  - Web routes
  - API endpoints
  - CLI commands
  - Background jobs
  - Tests

### ✅ Maintainability
- Clear separation of concerns
- Single Responsibility Principle
- Business logic in one place
- Routes become simple coordinators

### ✅ Type Safety
- Pydantic validation ensures data integrity
- Type hints throughout
- Catch errors early

### ✅ Documentation
- DTOs serve as API documentation
- Clear contracts between layers
- Self-documenting code

---

## Success Criteria

### Phase 3.1 (Foundation)
- [ ] BaseService class created
- [ ] Base DTO classes created
- [ ] Directory structure set up
- [ ] Proof of concept with one route

### Phase 3.2 (Experiment Service)
- [ ] ExperimentService with all CRUD operations
- [ ] All experiment DTOs created
- [ ] experiments/crud.py refactored to thin controller
- [ ] No business logic remains in routes
- [ ] All validation in DTOs

### Phase 3 Complete
- [ ] All major routes refactored
- [ ] Services created for each domain
- [ ] DTOs for all API endpoints
- [ ] Routes are < 50 lines each
- [ ] Business logic 100% testable
- [ ] Backward compatible (no breaking API changes)

---

## Next Steps

1. Create base infrastructure (BaseService, base DTOs)
2. Implement ExperimentService with DTOs
3. Refactor experiments/crud.py to use service
4. Repeat for processing, references, terms routes
5. Add tests for services
6. Document new patterns

---

**Ready to start Phase 3.1: Create foundation infrastructure**
