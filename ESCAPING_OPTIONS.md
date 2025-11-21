# LangChain Prompt Escaping - Options

## Problem
LangChain's `ChatPromptTemplate` interprets `{variable}` as template variables.
JSON examples in prompts cause errors unless braces are escaped as `{{` or `}}`.

## Current State
- We build full prompts via Python f-strings (all variables filled)
- We pass prompts to `ChatPromptTemplate.from_messages()`
- We invoke with empty dict: `chain.ainvoke({})`
- **We don't actually use LangChain template variables!**

---

## Option 1: Utility Function Approach ✅ SAFER

**What**: Use `escape_for_langchain_template()` in prompts.py

**Changes needed**:
```python
# app/orchestration/prompts.py
from app.orchestration.prompt_utils import escape_for_langchain_template

def get_synthesis_prompt(...) -> str:
    # Build prompt normally
    prompt = f"""You are synthesizing insights...

    Return JSON with:
    {{
        "cross_document_insights": "...",
        "generated_term_cards": [...]
    }}
    """

    # Escape before returning
    return escape_for_langchain_template(prompt)
```

**Pros**:
- Minimal code changes (add 1 line per prompt function)
- Explicit and clear what's happening
- Easy to debug - can inspect escaped output
- Works with existing LangChain chain architecture

**Cons**:
- Extra processing step
- Need to remember to call it

---

## Option 2: Remove ChatPromptTemplate ✅ CLEANER

**What**: Pass messages directly to LLM without template processing

**Changes needed**:
```python
# app/orchestration/experiment_nodes.py
from langchain_core.messages import HumanMessage

async def analyze_experiment_node(state):
    # ... build prompt_text ...

    # BEFORE:
    # prompt = ChatPromptTemplate.from_messages([("user", prompt_text)])
    # chain = prompt | claude_client | json_parser
    # response = await call_llm_with_retry(lambda: chain.ainvoke({}))

    # AFTER:
    chain = claude_client | json_parser
    response = await call_llm_with_retry(
        lambda: chain.ainvoke([HumanMessage(content=prompt_text)])
    )
```

**Pros**:
- No escaping needed at all!
- Simpler, more direct
- Slightly better performance (no template processing)
- Future-proof - won't hit escaping issues

**Cons**:
- Need to change all 3 LLM nodes (analyze, recommend, synthesize)
- Different pattern from typical LangChain examples
- If we later want template variables, need to refactor back

---

## Recommendation: **Option 2**

Since we:
1. Don't use template variables (passing empty `{}`)
2. Build complete prompts via f-strings
3. Want to avoid escaping issues entirely

**Option 2 is cleaner and more maintainable.**

### Implementation Steps:

1. Update `analyze_experiment_node()` (line 90-96)
2. Update `recommend_strategy_node()` (similar pattern)
3. Update `synthesize_experiment_node()` (similar pattern)
4. Remove quadruple braces from prompts.py (revert to normal JSON)
5. Test all 3 experiment types

**Risk**: Low - this is a simpler pattern, less can go wrong

---

## Alternative: Hybrid Approach

Use **Option 2** for new code, keep **Option 1** utility for emergency fixes.

If we ever need actual template variables in the future, we can:
- Use the utility function for those specific prompts
- Or use LangChain's `PromptTemplate.from_template()` with explicit variable declarations
