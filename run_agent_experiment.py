#!/usr/bin/env python3
"""
Execute the 'Agent Semantic Evolution (1910-2024)' experiment from the JCDL paper.
This script runs the complete 5-stage LLM orchestration workflow.
"""

import os
import sys
import json
from pathlib import Path

# Add the project root to the path
sys.path.insert(0, str(Path(__file__).parent))

from app import create_app, db
from app.models import User, Experiment, Document, Term
from datetime import datetime

def main():
    """Execute the agent semantic evolution experiment."""

    # Create app context
    app = create_app()

    with app.app_context():
        print("="*70)
        print("AGENT SEMANTIC EVOLUTION EXPERIMENT (1910-2024)")
        print("JCDL Paper Case Study")
        print("="*70)
        print()

        # Get or create user
        user = User.query.filter_by(email='test@example.com').first()
        if not user:
            print("Creating test user...")
            user = User(
                username='researcher',
                email='test@example.com',
                account_status='active'
            )
            user.set_password('test123')
            db.session.add(user)
            db.session.commit()
            print(f"✓ Created user: {user.email}")
        else:
            print(f"✓ Using existing user: {user.email}")

        print()

        # Create or get focus term
        term = Term.query.filter_by(term_text='agent').first()
        if not term:
            print("Creating focus term 'agent'...")
            term = Term(
                term_text='agent',
                description='A person or entity that acts on behalf of another (legal); an autonomous system that perceives and acts (AI); one who acts with intention (philosophy)',
                research_domain='Cross-disciplinary',
                status='active',
                user_id=user.id
            )
            db.session.add(term)
            db.session.commit()
            print(f"✓ Created term: {term.term_text} (ID: {term.id})")
        else:
            print(f"✓ Using existing term: {term.term_text} (ID: {term.id})")

        print()

        # Create experiment
        print("Creating experiment...")
        config_data = {
            'focus_term': 'agent',
            'temporal_span': '114 years',
            'start_year': 1910,
            'end_year': 2024,
            'disciplines': ['Law', 'Philosophy', 'Artificial Intelligence', 'Lexicography'],
            'document_count': 7
        }

        experiment = Experiment(
            name='Agent Semantic Evolution (1910-2024)',
            description='Tracking conceptual migration of "agent" from legal representation through philosophical agency to computational autonomy across 114 years',
            experiment_type='temporal_evolution',
            user_id=user.id,
            term_id=term.id,
            status='draft',
            configuration=json.dumps(config_data)  # Convert dict to JSON string
        )
        db.session.add(experiment)
        db.session.commit()

        print(f"✓ Created experiment: {experiment.name}")
        print(f"  ID: {experiment.id}")
        print(f"  Type: {experiment.experiment_type}")
        print(f"  Focus term: agent")
        print(f"  Temporal span: 1910-2024 (114 years)")
        print()

        # Document upload information
        pdf_files = [
            ("AGENT 1910.pdf", "Black's Law Dictionary 2nd Edition", 1910, "Law"),
            ("Anscombe-Intention-1956.pdf", "Anscombe - Intention", 1957, "Philosophy"),
            ("Wooldridge and Jennings - 1995 - Intelligent agents theory and practice.pdf",
             "Wooldridge & Jennings - Intelligent Agents", 1995, "AI"),
            ("AGENT.pdf", "Black's Law Dictionary 11th Edition", 2019, "Law"),
            ("Chapter 2 (Agents) Artificial Intelligence_ A Modern Approach-Prentice Hall (2020).pdf",
             "Russell & Norvig - AI: A Modern Approach Ch. 2", 2020, "AI"),
            ("AGENT 2024.pdf", "Black's Law Dictionary 12th Edition", 2024, "Law"),
            ("agent, n.¹ & adj. meanings, etymology and more _ Oxford English Dictionary.pdf",
             "OED - agent", 2024, "Lexicography")
        ]

        print("=" * 70)
        print("NEXT STEPS:")
        print("=" * 70)
        print()
        print(f"Experiment created successfully (ID: {experiment.id})")
        print()
        print("Documents to upload (N=7):")
        for i, (filename, title, year, discipline) in enumerate(pdf_files, 1):
            print(f"  {i}. {title} ({year}) - {discipline}")
            print(f"     File: experiments/{filename}")
        print()
        print("To continue, upload these documents through:")
        print(f"  Web UI: http://localhost:8765/experiments/{experiment.id}")
        print(f"  Or run the upload script (to be created)")
        print()
        print("Expected results per paper:")
        print("  - 247 total segments")
        print("  - 279 extracted entities")
        print("  - 23 tool executions")
        print("  - 6 semantic shifts identified")
        print("  - 92% strategy confidence")
        print()

if __name__ == '__main__':
    main()
