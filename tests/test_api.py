"""Test script for Remembr API"""
import requests
import json

# API Configuration
BASE_URL = "http://localhost:8000/api/v1"
API_KEY = "rmbr_0TnG4QrehzLinNXz9Yye6lXDd_efw6gv"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

print("=" * 80)
print("REMEMBR API TEST")
print("=" * 80)

# 1. Create a session
print("\n1. Creating a session...")
session_data = {
    "metadata": {
        "user_name": "Emmanuel",
        "context": "Testing Remembr memory system"
    }
}

response = requests.post(f"{BASE_URL}/sessions", json=session_data, headers=headers)
print(f"Status: {response.status_code}")
session_result = response.json()
print(json.dumps(session_result, indent=2))

session_id = session_result["data"]["session_id"]
print(f"\n✓ Session created: {session_id}")

# 2. Add memories to the session
print("\n2. Adding memories...")
memories = [
    {
        "session_id": session_id,
        "content": "Emmanuel is learning how to use the Remembr API for memory management.",
        "role": "user",
        "metadata": {"topic": "learning"}
    },
    {
        "session_id": session_id,
        "content": "Remembr uses pgvector for semantic search and Jina AI for embeddings.",
        "role": "assistant",
        "metadata": {"topic": "technical"}
    },
    {
        "session_id": session_id,
        "content": "The system successfully connected to PostgreSQL, Redis, and Jina AI.",
        "role": "system",
        "metadata": {"topic": "deployment"}
    }
]

for i, memory in enumerate(memories, 1):
    response = requests.post(f"{BASE_URL}/memory", json=memory, headers=headers)
    print(f"Memory {i}: {response.status_code}")
    if response.status_code == 200:
        result = response.json()
        print(f"  ✓ Episode ID: {result['data']['episode_id']}")

# 3. Search memories
print("\n3. Searching memories with semantic query...")
search_data = {
    "query": "How does Remembr work?",
    "session_id": session_id,
    "limit": 5
}

response = requests.post(f"{BASE_URL}/memory/search", json=search_data, headers=headers)
print(f"Status: {response.status_code}")
search_result = response.json()
print(f"\nFound {search_result['data']['total']} results:")
for i, result in enumerate(search_result['data']['results'], 1):
    print(f"\n  Result {i}:")
    print(f"    Content: {result['content'][:80]}...")
    print(f"    Score: {result.get('score', 'N/A')}")
    print(f"    Role: {result.get('role', 'N/A')}")

# 4. List all sessions
print("\n4. Listing all sessions...")
response = requests.get(f"{BASE_URL}/sessions", headers=headers)
print(f"Status: {response.status_code}")
sessions_result = response.json()
print(f"Total sessions: {sessions_result['data']['total']}")
for session in sessions_result['data']['sessions']:
    session_id = session.get('session_id') or session.get('id')
    print(f"  - {session_id}: {session.get('metadata', {})}")

# 5. Get session details
print(f"\n5. Getting session details for {session_id}...")
response = requests.get(f"{BASE_URL}/sessions/{session_id}", headers=headers)
print(f"Status: {response.status_code}")
session_detail = response.json()
print(json.dumps(session_detail['data'], indent=2))

print("\n" + "=" * 80)
print("✓ API TEST COMPLETED SUCCESSFULLY!")
print("=" * 80)
