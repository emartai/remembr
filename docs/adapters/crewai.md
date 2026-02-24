# CrewAI Adapter

## Install

```bash
pip install remembr-crewai-adapter crewai remembr
```

## Single-agent usage

```python
from remembr import RemembrClient
from adapters.crewai.remembr_crew_memory import RemembrCrewMemory

client = RemembrClient(api_key="<API_KEY>", base_url="https://api.remembr.dev/api/v1")
memory = RemembrCrewMemory(client=client, agent_id="agent-a", team_id="team-1")

memory.save("Escalate P1 incidents immediately")
print(memory.search("P1 incidents"))
```

## Multi-agent shared memory example

```python
from adapters.crewai.remembr_crew_memory import RemembrSharedCrewMemory

shared = RemembrSharedCrewMemory(client=client, team_id="team-1")
shared.save("Team standard: include rollback plan in every change request")

# Attach to crew; each agent reads same shared memory
# shared.inject_into_crew(crew)
```
