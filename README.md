# UAV Mission Intelligence Agent

> A UAV-domain LLM/Agent portfolio project for mission understanding, planning assistance, knowledge retrieval, and structured mission configuration.

This project connects my UAV/swarm robotics background with practical LLM/Agent engineering. It takes a natural-language UAV mission request, extracts mission constraints, retrieves local UAV planning knowledge, and generates a structured mission plan with recommendations, risks, and JSON configuration.

## Portfolio Positioning

This repository is designed as a job-facing project for roles such as:

| Target role | What this project demonstrates |
|---|---|
| LLM Application Engineer | RAG-style retrieval, structured output, domain-specific reasoning workflow |
| Agent Engineer | Multi-step agent workflow: parse -> retrieve -> plan -> explain -> configure |
| UAV / Robotics Algorithm Engineer | UAV mission planning concepts, no-fly-zone constraints, weak-communication coordination |
| AI Solution Engineer | Turning domain knowledge into a runnable decision-support demo |

The first version is intentionally offline and dependency-light, so recruiters and interviewers can run it quickly without API keys. The architecture is prepared for later LangGraph, vector database, and real LLM integration.

## Key Features

- Parses Chinese UAV mission descriptions.
- Extracts UAV count, search areas, no-fly zones, objectives, and coordination constraints.
- Retrieves UAV planning knowledge from a local knowledge base.
- Generates planning recommendations for search, coverage, no-fly-zone avoidance, and weak communication.
- Outputs a structured JSON mission configuration.
- Includes unit tests and an example output for quick review.

## Example Scenario

Input:

```text
使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。
```

Output includes:

- task parsing: UAV count, search area, no-fly zone, objectives, constraints
- retrieved UAV planning knowledge
- planning recommendations
- mission risks
- JSON mission configuration

Representative output: [`examples/example_output.json`](examples/example_output.json)

## System Workflow

```text
Natural-language UAV mission
        |
        v
Task Parser
        |
        v
Local UAV Knowledge Retriever
        |
        v
Mission Planning Agent
        |
        v
Recommendations + Risks + JSON Config
```

## Architecture

| Module | Responsibility |
|---|---|
| `task_parser.py` | Extract structured mission fields from natural-language input |
| `knowledge_base.py` | Retrieve relevant UAV planning snippets with a lightweight RAG-style scorer |
| `planner.py` | Generate recommendations, risk notes, and mission configuration |
| `workflow.py` | Orchestrate the end-to-end mission intelligence workflow |
| `cli.py` | Provide a command-line demo entry point |

Project layout:

```text
uav-mission-intelligence-agent/
+-- examples/
|   +-- mission_zh.txt
|   +-- example_output.json
+-- src/
|   +-- uav_mission_agent/
|       +-- cli.py
|       +-- knowledge_base.py
|       +-- models.py
|       +-- planner.py
|       +-- task_parser.py
|       +-- workflow.py
+-- tests/
|   +-- test_task_parser.py
|   +-- test_workflow.py
+-- pyproject.toml
+-- README.md
```

## Quick Start

Clone the repository:

```bash
git clone https://github.com/poliment/uav-mission-intelligence-agent.git
cd uav-mission-intelligence-agent
```

Run tests:

```bash
python -m unittest discover -s tests -v
```

Run the demo on Windows PowerShell:

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

Run the demo on macOS/Linux:

```bash
PYTHONPATH=src python -m uav_mission_agent.cli "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

Optional editable install:

```bash
python -m pip install -e .
python -m uav_mission_agent.cli "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

## Sample Output Fragment

```json
{
  "task": {
    "drone_count": 3,
    "search_areas": ["区域A"],
    "avoid_zones": ["禁飞区B"],
    "objectives": ["area_search", "coverage", "suspicious_target_search"],
    "constraints": [
      "low_bandwidth_coordination",
      "avoid_no_fly_zone",
      "multi_uav_coordination"
    ]
  },
  "mission_config": {
    "uav_count": 3,
    "coordination_mode": "distributed_low_bandwidth",
    "planning_policy": "coverage_first_with_constraint_avoidance"
  }
}
```

## Technical Highlights

- **Domain grounding:** The workflow is built around UAV mission planning rather than generic chatbot behavior.
- **Structured reasoning:** The pipeline separates parsing, retrieval, planning, and configuration generation.
- **RAG-ready design:** The local knowledge retriever can later be replaced by FAISS, Chroma, or another vector database.
- **Agent-ready design:** Each module can become a LangGraph node in a future multi-agent workflow.
- **Testable MVP:** Current behavior is covered by unit tests and runs without network access.

## Current Test Coverage

The first test suite validates:

- Chinese UAV mission field extraction
- Relevant UAV knowledge retrieval
- End-to-end workflow output structure

Run:

```bash
python -m unittest discover -s tests -v
```

Expected result:

```text
Ran 3 tests
OK
```

## Roadmap

- Add a LangGraph implementation of the current workflow nodes.
- Replace the local retriever with FAISS or Chroma.
- Add an LLM provider adapter for OpenAI-compatible APIs.
- Add structured YAML output for simulator-style mission configuration.
- Add more UAV scenarios: area search, target tracking, no-fly-zone avoidance, weak communication, and multi-UAV task allocation.
- Add a Streamlit or FastAPI demo for visual presentation.

## Resume Summary

Built a UAV-domain LLM/Agent prototype that converts natural-language UAV mission requests into structured mission plans by combining task parsing, RAG-style local knowledge retrieval, planning recommendations, risk explanation, and JSON configuration output.
