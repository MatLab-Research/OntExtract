"""
Verify LLM Orchestration is Functional

Quick test to confirm orchestration is being called and producing results.
Run this to verify orchestration works before documenting it.
"""

import sys
import os
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from app.services.integrated_langextract_service import IntegratedLangExtractService

def test_orchestration():
    """Test that LLM orchestration is functional"""

    print("Testing LLM Orchestration...")
    print("=" * 60)

    # Initialize service
    try:
        service = IntegratedLangExtractService()
        print(f"✓ Service initialized")
        print(f"  - Service ready: {service.service_ready}")
        print(f"  - Has orchestration coordinator: {hasattr(service, 'orchestration_coordinator')}")

        if hasattr(service, 'orchestration_coordinator'):
            coordinator = service.orchestration_coordinator
            print(f"  - Has orchestrator LLM: {coordinator.orchestrator_llm is not None}")
            if coordinator.orchestrator_llm:
                print(f"  - LLM type: {type(coordinator.orchestrator_llm).__name__}")
    except Exception as e:
        print(f"✗ Service initialization failed: {e}")
        return False

    # Test with sample document
    sample_text = """
    This document discusses agency theory in economics. The principal-agent problem
    arises when one party (the agent) makes decisions on behalf of another (the principal).
    This relationship dates back to the 1970s when economists first formalized the concept.
    """

    print("\nTesting two-stage analysis...")
    print("-" * 60)

    try:
        result = service.analyze_and_orchestrate_document(
            document_id=999,  # Test ID
            document_text=sample_text,
            user_id=1
        )

        print(f"✓ Analysis completed")
        print(f"  - Success: {result.get('success')}")
        print(f"  - Has Stage 1 (LangExtract): {'langextract_analysis' in result}")
        print(f"  - Has Stage 2 (Orchestration): {'orchestration_plan' in result}")

        if 'orchestration_plan' in result:
            orch = result['orchestration_plan']
            print(f"\n✓ ORCHESTRATION IS WORKING!")
            print(f"  - Selected tools: {orch.get('selected_tools', [])}")
            print(f"  - Confidence: {orch.get('confidence', 'N/A')}")
            print(f"  - Ready for execution: {orch.get('ready_for_execution', False)}")

            if 'tool_selection_reasoning' in orch:
                print(f"\n  LLM Reasoning:")
                reasoning = orch['tool_selection_reasoning']
                if isinstance(reasoning, dict):
                    for tool, reason in reasoning.items():
                        print(f"    - {tool}: {reason}")
                else:
                    print(f"    {reasoning}")

            return True
        else:
            print(f"\n⚠ Orchestration not in results")
            print(f"  This might be okay if Stage 2 failed gracefully")
            print(f"  Check logs for orchestration attempt")
            return False

    except Exception as e:
        print(f"\n✗ Analysis failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_orchestration()

    print("\n" + "=" * 60)
    if success:
        print("RESULT: LLM Orchestration is FUNCTIONAL ✓")
        print("\nNext steps:")
        print("1. Document the orchestration prompts (Day 6-7)")
        print("2. Show decision examples in case study (Day 3-5)")
        print("3. Add UI to display orchestration reasoning")
    else:
        print("RESULT: Orchestration needs investigation")
        print("\nCheck:")
        print("1. API keys (ANTHROPIC_API_KEY or OPENAI_API_KEY)")
        print("2. Service initialization errors")
        print("3. Log files for orchestration attempts")
    print("=" * 60)
