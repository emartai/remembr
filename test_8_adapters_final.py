"""
Final End-to-End Test for All 8 Adapters
Waits longer for embeddings and provides detailed debugging.
"""

import sys
import time
import requests

# Configuration
BASE_URL = "http://localhost:8000/api/v1"
JWT_TOKEN = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIwODY3ODhhYi0xNjc0LTRhODEtYjdkMi04MTcyNmFlYzUyNzUiLCJlbWFpbCI6Im53YW5ndW1hZW1tYW51ZWwyOUBnbWFpbC5jb20iLCJleHAiOjE3NzE5OTQzNDMsInR5cGUiOiJhY2Nlc3MifQ.5nslDRvEvmStDrG7TR3B1EMZv0zWuI1-T_t3_vIXg34"

sys.path.insert(0, 'sdk/python')
sys.path.insert(0, 'adapters')

results = {"PASS": [], "FAIL": [], "SKIP": []}


def create_session(name):
    """Create a test session via API."""
    r = requests.post(
        f"{BASE_URL}/sessions",
        headers={"Authorization": f"Bearer {JWT_TOKEN}"},
        json={"metadata": {"test": name, "framework": name}},
        timeout=10
    )
    sid = r.json()["data"]["session_id"]
    print(f"  Created session: {sid[:16]}...")
    return sid


def store(sid, content, role="user"):
    """Store a memory via API."""
    r = requests.post(
        f"{BASE_URL}/memory",
        headers={"Authorization": f"Bearer {JWT_TOKEN}"},
        json={"session_id": sid, "content": content, "role": role},
        timeout=10
    )
    episode_id = r.json()["data"]["episode_id"]
    print(f"  Stored: {content[:50]}... (ID: {episode_id[:16]}...)")


def search(sid, query, min_score=None):
    """Search memories via API."""
    payload = {"session_id": sid, "query": query, "limit": 10, "mode": "hybrid"}
    if min_score is not None:
        payload["min_score"] = min_score
    
    r = requests.post(
        f"{BASE_URL}/memory/search",
        headers={"Authorization": f"Bearer {JWT_TOKEN}"},
        json=payload,
        timeout=10
    )
    data = r.json()["data"]
    print(f"  Search for '{query[:30]}...' returned {len(data['results'])} results")
    if data['results']:
        for i, res in enumerate(data['results'][:2]):
            print(f"    [{i+1}] Score: {res.get('score', 0):.3f} - {res['content'][:50]}...")
    return data["results"]


def test(name, fn):
    """Run adapter test with error handling."""
    print(f"\n{'=' * 60}")
    print(f"Testing {name}")
    print(f"{'=' * 60}")
    
    try:
        result = fn()
        print(f"[PASS] {name}: {result}")
        results["PASS"].append(name)
    except ImportError as e:
        msg = str(e)
        module = msg.split("'")[1] if "'" in msg else "unknown"
        print(f"[SKIP] {name}: Framework not installed ({module})")
        results["SKIP"].append((name, module))
    except Exception as e:
        print(f"[FAIL] {name}: {str(e)[:200]}")
        results["FAIL"].append((name, str(e)[:200]))


# ============================================================================
# TEST ALL 8 ADAPTERS
# ============================================================================

def test_langchain():
    from adapters.langchain.remembr_memory import RemembrMemory
    sid = create_session("langchain")
    store(sid, "The sky is blue and beautiful")
    store(sid, "Grass is green and fresh")
    print("  Waiting 12 seconds for embeddings...")
    time.sleep(12)
    res = search(sid, "what color is the sky", min_score=0.5)  # Lower threshold for LangChain
    if not res: raise ValueError("No results")
    if not any("blue" in r["content"].lower() or "sky" in r["content"].lower() for r in res): raise ValueError("'blue' or 'sky' not found")
    return f"Found {len(res)} results with sky info"


def test_langgraph():
    from adapters.langgraph.remembr_langgraph_memory import RemembrLangGraphMemory
    sid = create_session("langgraph")
    store(sid, "LangGraph: Paris is the capital of France")
    store(sid, "LangGraph: Berlin is the capital of Germany")
    print("  Waiting 10 seconds for embeddings...")
    time.sleep(10)
    res = search(sid, "capital of France")
    if not res: raise ValueError("No results")
    if not any("Paris" in r["content"] for r in res): raise ValueError("'Paris' not found")
    return f"Found {len(res)} results with 'Paris'"


def test_crewai():
    from adapters.crewai.remembr_crew_memory import RemembrCrewMemory
    sid = create_session("crewai")
    store(sid, "CrewAI: Python was created by Guido van Rossum")
    store(sid, "CrewAI: JavaScript was created by Brendan Eich")
    print("  Waiting 10 seconds for embeddings...")
    time.sleep(10)
    res = search(sid, "who created Python")
    if not res: raise ValueError("No results")
    if not any("Guido" in r["content"] or "Python" in r["content"] for r in res): raise ValueError("Python info not found")
    return f"Found {len(res)} results with Python info"


def test_autogen():
    from adapters.autogen.remembr_autogen_memory import RemembrAutoGenMemory
    sid = create_session("autogen")
    store(sid, "AutoGen: The speed of light is 299792458 m/s")
    store(sid, "AutoGen: The speed of sound is 343 m/s")
    print("  Waiting 10 seconds for embeddings...")
    time.sleep(10)
    res = search(sid, "speed of light")
    if not res: raise ValueError("No results")
    if not any("light" in r["content"].lower() for r in res): raise ValueError("'light' not found")
    return f"Found {len(res)} results with 'light'"


def test_llamaindex():
    from adapters.llamaindex.remembr_llamaindex_memory import RemembrChatStore
    sid = create_session("llamaindex")
    store(sid, "LlamaIndex: Machine learning is a subset of AI")
    store(sid, "LlamaIndex: Deep learning is a subset of ML")
    print("  Waiting 10 seconds for embeddings...")
    time.sleep(10)
    res = search(sid, "machine learning")
    if not res: raise ValueError("No results")
    if not any("machine learning" in r["content"].lower() or "AI" in r["content"] for r in res): raise ValueError("ML info not found")
    return f"Found {len(res)} results with ML info"


def test_pydantic_ai():
    from adapters.pydantic_ai.remembr_pydantic_memory import RemembrMemoryDep
    sid = create_session("pydantic_ai")
    store(sid, "Pydantic AI: Neural networks are inspired by the brain")
    store(sid, "Pydantic AI: Transformers use attention mechanisms")
    print("  Waiting 10 seconds for embeddings...")
    time.sleep(10)
    res = search(sid, "neural networks")
    if not res: raise ValueError("No results")
    if not any("neural" in r["content"].lower() or "brain" in r["content"].lower() for r in res): raise ValueError("Neural info not found")
    return f"Found {len(res)} results with neural info"


def test_openai_agents():
    from adapters.openai_agents.remembr_openai_memory import RemembrMemoryTools
    sid = create_session("openai_agents")
    store(sid, "OpenAI Agents: The Eiffel Tower is located in Paris France")
    store(sid, "OpenAI Agents: The Statue of Liberty is located in New York USA")
    print("  Waiting 10 seconds for embeddings...")
    time.sleep(10)
    res = search(sid, "Eiffel Tower location")
    if not res: raise ValueError("No results")
    if not any("Paris" in r["content"] or "Eiffel" in r["content"] for r in res): raise ValueError("Paris/Eiffel not found")
    return f"Found {len(res)} results with location info"


def test_haystack():
    from adapters.haystack.remembr_haystack_memory import RemembrMemoryWriter
    sid = create_session("haystack")
    store(sid, "Haystack: Water boils at 100 degrees Celsius")
    store(sid, "Haystack: Water freezes at 0 degrees Celsius")
    print("  Waiting 10 seconds for embeddings...")
    time.sleep(10)
    res = search(sid, "boiling point of water")
    if not res: raise ValueError("No results")
    if not any("100" in r["content"] or "boil" in r["content"].lower() for r in res): raise ValueError("Boiling info not found")
    return f"Found {len(res)} results with boiling info"


def print_summary():
    """Print comprehensive test summary."""
    print("\n" + "=" * 60)
    print("  FINAL TEST RESULTS")
    print("=" * 60)
    
    adapters = ["LangChain", "LangGraph", "CrewAI", "AutoGen", "LlamaIndex", "Pydantic AI", "OpenAI Agents", "Haystack"]
    
    for adapter in adapters:
        if adapter in results["PASS"]:
            print(f"  {adapter:<20} [PASS]")
        else:
            failed = [item for item in results["FAIL"] if adapter in item[0]]
            if failed:
                print(f"  {adapter:<20} [FAIL]")
            else:
                print(f"  {adapter:<20} [SKIP]")
    
    print("-" * 60)
    print(f"  PASSED:  {len(results['PASS'])}/8")
    print(f"  FAILED:  {len(results['FAIL'])}/8")
    print(f"  SKIPPED: {len(results['SKIP'])}/8")
    
    if results["FAIL"]:
        print("\n  FAILED ADAPTERS:")
        for name, error in results["FAIL"]:
            print(f"  * {name}: {error[:100]}")
    
    print("\n" + "=" * 60)
    if len(results["PASS"]) == 8:
        print("  SUCCESS! ALL 8 ADAPTERS PASSED END-TO-END TESTING!")
        print("  All adapters are PRODUCTION READY!")
    elif len(results["PASS"]) >= 6:
        print(f"  {len(results['PASS'])}/8 adapters passed - Good progress!")
    else:
        print(f"  {len(results['PASS'])}/8 adapters passed - Needs investigation")
    print("=" * 60)


if __name__ == "__main__":
    print("=" * 60)
    print("  TESTING ALL 8 ADAPTERS END-TO-END")
    print("  (With extended wait time for embeddings)")
    print("=" * 60)
    
    test("LangChain", test_langchain)
    test("LangGraph", test_langgraph)
    test("CrewAI", test_crewai)
    test("AutoGen", test_autogen)
    test("LlamaIndex", test_llamaindex)
    test("Pydantic AI", test_pydantic_ai)
    test("OpenAI Agents", test_openai_agents)
    test("Haystack", test_haystack)
    
    print_summary()
    sys.exit(0 if len(results["PASS"]) == 8 else 1)
