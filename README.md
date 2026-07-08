# UAV Mission Intelligence Agent

面向无人机任务规划与态势理解的 LLM/Agent 项目雏形。

这个仓库的目标不是做一个泛泛的聊天机器人，而是把无人机任务规划、集群协同、RAG 和 Agent 工作流结合起来，形成一个适合求职展示的工程项目。

## Why This Project

无人机算法岗位关注 ROS、PX4、航迹规划、仿真和实物验证；LLM/Agent 岗位关注 RAG、工具调用、结构化输出和多步骤工作流。本项目把两条线合到一个具体场景：

> 输入自然语言无人机任务，系统解析任务约束，检索无人机领域知识，生成规划建议、风险解释和结构化任务配置。

## MVP Workflow

```text
Natural language UAV mission
        |
        v
Task parser
        |
        v
Local UAV knowledge retrieval
        |
        v
Planning agent
        |
        v
JSON mission plan
```

## Current Features

- Parse Chinese UAV mission requests.
- Extract UAV count, search areas, no-fly zones, objectives, and constraints.
- Retrieve local UAV planning knowledge with a lightweight RAG-style retriever.
- Generate planning recommendations and risk notes.
- Export a structured JSON mission configuration.

## Quick Start

Run tests:

```bash
python -m unittest discover -s tests -v
```

Run the demo:

PowerShell:

```bash
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

Bash:

```bash
PYTHONPATH=src python -m uav_mission_agent.cli "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

Editable install:

```bash
python -m pip install -e .
python -m uav_mission_agent.cli "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

See `examples/example_output.json` for a representative output.

## Roadmap

- Replace the local retriever with FAISS or Chroma.
- Add LangGraph nodes for parser, retriever, planner, verifier, and config generator.
- Add real LLM provider adapters.
- Add mission scenario files and simulator-friendly JSON/YAML output.
- Add a Streamlit or FastAPI demo.
