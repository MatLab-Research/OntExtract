from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, FloatField, SelectField, IntegerField
from wtforms.validators import DataRequired, Length, NumberRange, Optional


class AddTermForm(FlaskForm):
    """Form for adding new terms with first version."""
    
    # Term basic information
    term_text = StringField(
        'Term Text',
        validators=[DataRequired(), Length(min=1, max=255)],
        render_kw={'placeholder': 'Enter the term or phrase'}
    )
    
    description = TextAreaField(
        'Description',
        validators=[Optional(), Length(max=2000)],
        render_kw={'placeholder': 'Brief description of the term (optional)', 'rows': 3}
    )
    
    etymology = TextAreaField(
        'Etymology',
        validators=[Optional(), Length(max=1000)],
        render_kw={'placeholder': 'Etymology or origin information (optional)', 'rows': 2}
    )
    
    research_domain = StringField(
        'Research Domain',
        validators=[Optional(), Length(max=255)],
        render_kw={'placeholder': 'e.g., Philosophy, Science, Politics'}
    )
    
    selection_rationale = TextAreaField(
        'Selection Rationale',
        validators=[Optional(), Length(max=1000)],
        render_kw={'placeholder': 'Why this term is important for semantic change analysis', 'rows': 3}
    )
    
    historical_significance = TextAreaField(
        'Historical Significance',
        validators=[Optional(), Length(max=1000)],
        render_kw={'placeholder': 'Historical context and significance', 'rows': 3}
    )
    
    notes = TextAreaField(
        'Additional Notes',
        validators=[Optional(), Length(max=2000)],
        render_kw={'placeholder': 'Any additional notes or context', 'rows': 3}
    )
    
    # First version information
    meaning_description = TextAreaField(
        'Meaning Description',
        validators=[DataRequired(), Length(min=10, max=2000)],
        render_kw={'placeholder': 'Describe the meaning of this term in this period', 'rows': 4}
    )
    
    temporal_period = StringField(
        'Temporal Period',
        validators=[DataRequired(), Length(min=1, max=255)],
        render_kw={'placeholder': 'e.g., "1800-1850", "Early 20th Century"'}
    )
    
    temporal_start_year = IntegerField(
        'Start Year',
        validators=[Optional(), NumberRange(min=1000, max=2100)],
        render_kw={'placeholder': '1800'}
    )
    
    temporal_end_year = IntegerField(
        'End Year',
        validators=[Optional(), NumberRange(min=1000, max=2100)],
        render_kw={'placeholder': '1850'}
    )
    
    corpus_source = StringField(
        'Corpus Source',
        validators=[Optional(), Length(max=500)],
        render_kw={'placeholder': 'Source of evidence for this meaning'}
    )
    
    source_citation = TextAreaField(
        'Source Citation',
        validators=[Optional(), Length(max=1000)],
        render_kw={'placeholder': 'Academic citation for this meaning (e.g., dictionary, paper, etc.)', 'rows': 2}
    )
    
    context_anchor = StringField(
        'Context Anchors',
        validators=[Optional(), Length(max=1000)],
        render_kw={'placeholder': 'Related terms (comma-separated)'}
    )
    
    fuzziness_score = FloatField(
        'Fuzziness Score',
        validators=[Optional(), NumberRange(min=0.0, max=1.0)],
        render_kw={'placeholder': '0.7', 'step': '0.1'}
    )
    
    confidence_level = SelectField(
        'Confidence Level',
        choices=[
            ('high', 'High - Very confident in this definition'),
            ('medium', 'Medium - Reasonably confident'),
            ('low', 'Low - Uncertain or provisional')
        ],
        default='medium',
        validators=[DataRequired()]
    )


class EditTermForm(FlaskForm):
    """Form for editing existing terms."""

    term_text = StringField(
        'Term Text',
        validators=[DataRequired(), Length(min=1, max=255)],
        render_kw={'readonly': True, 'class': 'form-control-plaintext'}
    )

    research_domain = StringField(
        'Research Domain',
        validators=[Optional(), Length(max=255)],
        render_kw={'placeholder': 'e.g., Philosophy, Science, Politics'}
    )

    notes = TextAreaField(
        'Additional Notes',
        validators=[Optional(), Length(max=2000)],
        render_kw={'placeholder': 'Any additional notes or context', 'rows': 3}
    )

    status = SelectField(
        'Status',
        choices=[
            ('active', 'Active'),
            ('provisional', 'Provisional'),
            ('deprecated', 'Deprecated')
        ],
        default='active',
        validators=[DataRequired()]
    )


class AddVersionForm(FlaskForm):
    """Form for adding new versions to existing terms."""
    
    meaning_description = TextAreaField(
        'Meaning Description',
        validators=[DataRequired(), Length(min=10, max=2000)],
        render_kw={'rows': 4}
    )
    
    temporal_period = StringField(
        'Temporal Period',
        validators=[DataRequired(), Length(min=1, max=255)]
    )
    
    temporal_start_year = IntegerField(
        'Start Year',
        validators=[Optional(), NumberRange(min=1000, max=2100)]
    )
    
    temporal_end_year = IntegerField(
        'End Year',
        validators=[Optional(), NumberRange(min=1000, max=2100)]
    )
    
    corpus_source = StringField(
        'Corpus Source',
        validators=[Optional(), Length(max=500)]
    )
    
    context_anchor = StringField(
        'Context Anchors',
        validators=[Optional(), Length(max=1000)]
    )
    
    fuzziness_score = FloatField(
        'Fuzziness Score',
        validators=[Optional(), NumberRange(min=0.0, max=1.0)]
    )
    
    confidence_level = SelectField(
        'Confidence Level',
        choices=[
            ('high', 'High'),
            ('medium', 'Medium'),
            ('low', 'Low')
        ],
        default='medium',
        validators=[DataRequired()]
    )
    
    notes = TextAreaField(
        'Version Notes',
        validators=[Optional(), Length(max=1000)]
    )