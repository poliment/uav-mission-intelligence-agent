# UAV Mission Intelligence Agent

> A UAV-domain LLM/Agent portfolio project for mission understanding, planning assistance, knowledge retrieval, and structured mission configuration.

This project connects my UAV/swarm robotics background with practical LLM/Agent engineering. It takes a natural-language UAV mission request, extracts mission constraints, retrieves local UAV planning knowledge, and generates a structured mission plan with recommendations, risks, and JSON configuration.

## Portfolio Positioning

This repository is designed as a job-facing project for roles such as:

| Target role | What this project demonstrates |
|---|---|
| LLM Application Engineer | RAG-style retrieval, structured output, domain-specific reasoning workflow |
| Agent Engineer | Traceable multi-node Agent workflow: parse -> retrieve -> plan -> review |
| UAV / Robotics Algorithm Engineer | UAV mission planning concepts, no-fly-zone constraints, weak-communication coordination |
| AI Solution Engineer | Turning domain knowledge into a runnable decision-support demo |

The first version is intentionally offline and dependency-light, so recruiters and interviewers can run it quickly without API keys. The architecture is prepared for later LangGraph, vector database, and real LLM integration.

## Key Features

- Parses Chinese UAV mission descriptions.
- Extracts UAV count, search areas, no-fly zones, objectives, and coordination constraints.
- Retrieves UAV planning knowledge from a local knowledge base.
- Generates planning recommendations for search, coverage, no-fly-zone avoidance, and weak communication.
- Outputs a structured JSON mission configuration.
- Runs a mini UAV mission benchmark with scenario-level scoring.
- Provides an Agent-style node trace and review output for explainability.
- Generates a local HTML dashboard for mission input, Agent node flow, planning output, and benchmark scores.
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

## Agent Workflow

```text
Natural-language UAV mission
        |
        v
task_parser_agent
        |
        v
knowledge_retriever_agent
        |
        v
mission_planner_agent
        |
        v
mission_reviewer_agent
        |
        v
Recommendations + Risks + JSON Config + Agent Trace
```

The current implementation is a dependency-free Agent graph. Each node reads and writes an explicit shared state, and the final output can include an `agent_trace` array that explains which nodes ran, what they consumed, and what they produced. This keeps the MVP easy to run while preserving a clean path toward LangGraph.

## Architecture

| Module | Responsibility |
|---|---|
| `task_parser.py` | Extract structured mission fields from natural-language input |
| `agent_graph.py` | Run parser, retriever, planner, and reviewer as traceable Agent nodes |
| `knowledge_base.py` | Retrieve relevant UAV planning snippets with a lightweight RAG-style scorer |
| `planner.py` | Generate recommendations, risk notes, and mission configuration |
| `workflow.py` | Orchestrate the end-to-end mission intelligence workflow |
| `scenario_loader.py` | Load structured UAV benchmark scenarios |
| `evaluator.py` | Score mission plans against scenario expectations |
| `benchmark.py` | Run the workflow across a scenario set and summarize metrics |
| `dashboard.py` | Generate a local static HTML visualization page |
| `cli.py` | Provide a command-line demo entry point |

Project layout:

```text
uav-mission-intelligence-agent/
+-- examples/
|   +-- mission_zh.txt
|   +-- example_output.json
+-- data/
|   +-- scenarios/
|       +-- area_search_low_bandwidth.json
|       +-- no_fly_zone_replan.json
|       +-- target_tracking_multi_uav.json
+-- results/
|   +-- example_evaluation.json
+-- dashboard/
|   +-- uav_mission_dashboard.html
+-- src/
|   +-- uav_mission_agent/
|       +-- benchmark.py
|       +-- cli.py
|       +-- dashboard.py
|       +-- agent_graph.py
|       +-- evaluator.py
|       +-- knowledge_base.py
|       +-- models.py
|       +-- planner.py
|       +-- scenario_loader.py
|       +-- task_parser.py
|       +-- workflow.py
+-- tests/
|   +-- test_agent_graph.py
|   +-- test_benchmark.py
|   +-- test_cli.py
|   +-- test_dashboard.py
|   +-- test_evaluator.py
|   +-- test_scenario_loader.py
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

Show Agent trace:

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --trace "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

Run the demo on macOS/Linux:

```bash
PYTHONPATH=src python -m uav_mission_agent.cli "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

Run the mini benchmark:

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --benchmark data\scenarios
```

The benchmark evaluates task parsing, expected objectives, mission constraints, risk keyword coverage, and structured mission configuration. A representative benchmark result is available at [`results/example_evaluation.json`](results/example_evaluation.json).

Generate the local HTML dashboard:

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --dashboard dashboard\uav_mission_dashboard.html
```

Then open [`dashboard/uav_mission_dashboard.html`](dashboard/uav_mission_dashboard.html) in a browser. The page shows the mission input, traceable Agent node flow, planning recommendations, risk notes, mission configuration, and benchmark score bars in one job-facing view.

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
  },
  "agent_review": {
    "ready": true,
    "warning_count": 0
  }
}
```

## Technical Highlights

- **Domain grounding:** The workflow is built around UAV mission planning rather than generic chatbot behavior.
- **Structured reasoning:** The pipeline separates parsing, retrieval, planning, and configuration generation.
- **Agent traceability:** The Agent graph records node order, input keys, output keys, and review status.
- **Benchmark-style evidence:** The project includes structured UAV scenarios and an evaluator instead of only a single demo.
- **Presentation-ready dashboard:** The CLI can generate a static HTML page for local demos and GitHub evidence.
- **RAG-ready design:** The local knowledge retriever can later be replaced by FAISS, Chroma, or another vector database.
- **Agent-ready design:** Each module can become a LangGraph node in a future multi-agent workflow.
- **Testable MVP:** Current behavior is covered by unit tests and runs without network access.

## Mini Benchmark

The current benchmark contains three UAV mission scenarios:

| Scenario | Capability tested |
|---|---|
| `area_search_low_bandwidth` | Area search, weak communication, no-fly-zone avoidance |
| `no_fly_zone_replan` | Dynamic no-fly-zone replanning and obstacle avoidance |
| `target_tracking_multi_uav` | Multi-UAV target tracking and coordination |

Evaluation dimensions:

- UAV count extraction
- search area extraction
- no-fly-zone extraction
- objective coverage
- constraint coverage
- risk keyword coverage

Current sample result:

```text
total_scenarios: 3
average_score: 1.0
passed_scenarios: 3
```

## Current Test Coverage

The first test suite validates:

- Chinese UAV mission field extraction
- Relevant UAV knowledge retrieval
- End-to-end workflow output structure
- scenario loading
- benchmark scoring
- CLI benchmark mode
- Agent graph trace output
- local HTML dashboard rendering
- CLI dashboard generation mode

Run:

```bash
python -m unittest discover -s tests -v
```

Expected result:

```text
Ran 19 tests
OK
```

## Roadmap

- Replace the dependency-free Agent graph with a LangGraph implementation of the current nodes.
- Replace the local retriever with FAISS or Chroma.
- Add an LLM provider adapter for OpenAI-compatible APIs.
- Add structured YAML output for simulator-style mission configuration.
- Add more UAV scenarios: area search, target tracking, no-fly-zone avoidance, weak communication, and multi-UAV task allocation.
- Add harder benchmark cases with ambiguous commands and conflicting constraints.
- Add an interactive Streamlit or FastAPI demo after the static dashboard baseline.

## Resume Summary

Built a UAV-domain LLM/Agent prototype that converts natural-language UAV mission requests into structured mission plans by combining traceable Agent nodes, task parsing, RAG-style local knowledge retrieval, planning recommendations, risk explanation, JSON configuration output, and benchmark-style scenario evaluation.
