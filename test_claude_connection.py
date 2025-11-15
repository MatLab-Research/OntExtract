#!/usr/bin/env python3
"""Test Claude API connection"""

import os
from langchain_anthropic import ChatAnthropic
from langchain_core.prompts import ChatPromptTemplate

def test_claude():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set")
        return False

    print(f"API Key present: {api_key[:10]}...")

    try:
        client = ChatAnthropic(
            model="claude-sonnet-4-20250514",
            api_key=api_key,
            temperature=0.2,
            max_tokens=100
        )

        prompt = ChatPromptTemplate.from_messages([
            ("system", "You are a helpful assistant."),
            ("user", "Say 'Hello, I am Claude and I am working!' in exactly those words.")
        ])

        chain = prompt | client

        print("Sending test message to Claude...")
        import asyncio
        response = asyncio.run(chain.ainvoke({}))

        print(f"✓ Response received: {response.content}")
        return True

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == '__main__':
    success = test_claude()
    exit(0 if success else 1)
