# UAV Mission Intelligence Agent

> 这是一个面向无人机任务理解、规划辅助、知识检索和结构化任务配置的 LLM/Agent 项目。
>
> This is a UAV-domain LLM/Agent project for mission understanding, planning assistance, knowledge retrieval, and structured mission configuration.

UAV Mission Intelligence Agent 是一个面向无人机任务理解与任务规划辅助的公开原型项目。项目接收自然语言无人机任务请求，提取任务目标、区域、约束和协同条件，检索本地无人机规划知识，并生成包含规划建议、风险说明和 JSON 配置的结构化任务方案。

UAV Mission Intelligence Agent is a public prototype for UAV mission understanding and planning assistance. It takes a natural-language UAV mission request, extracts mission goals, areas, constraints, and coordination conditions, retrieves local UAV planning knowledge, and generates a structured mission plan with recommendations, risks, and JSON configuration.

## Project Overview / 项目概述

本项目围绕无人机任务智能展开，重点是把自然语言任务描述转化为可解释、可评估的结构化任务方案。当前版本使用离线规则和轻量 Agent 工作流实现核心流程，后续可以替换为真实 LLM、LangGraph 和向量数据库。

This project focuses on UAV mission intelligence, converting natural-language mission requests into explainable and evaluable structured mission plans. The current version uses offline rules and a lightweight Agent workflow for the core pipeline, with a clear path toward real LLM calls, LangGraph, and vector databases.

| Project part / 项目部分 | Description / 内容说明 |
|---|---|
| Mission input / 任务输入 | 接收中文自然语言无人机任务描述，例如区域搜索、禁飞区规避、多机协同和弱通信约束。<br>Accepts Chinese natural-language UAV mission requests, such as area search, no-fly-zone avoidance, multi-UAV coordination, and weak-communication constraints. |
| Agent workflow / Agent 工作流 | 通过 `task_parser_agent -> knowledge_retriever_agent -> mission_planner_agent -> mission_reviewer_agent` 完成解析、检索、规划和复核。<br>Uses `task_parser_agent -> knowledge_retriever_agent -> mission_planner_agent -> mission_reviewer_agent` to parse, retrieve, plan, and review. |
| Structured output / 结构化输出 | 输出任务字段、规划建议、风险说明和 JSON mission configuration。<br>Outputs task fields, planning recommendations, risk notes, and JSON mission configuration. |
| Benchmark / 场景评估 | 使用多场景 benchmark 评估任务解析、目标覆盖、约束覆盖和风险关键词覆盖。<br>Uses a multi-scenario benchmark to evaluate task parsing, objective coverage, constraint coverage, and risk keyword coverage. |
| Dashboard / 可视化页面 | 生成本地 HTML 页面，集中展示任务输入、Agent 节点流、规划结果和 benchmark 分数。<br>Generates a local HTML page that presents mission input, Agent node flow, planning results, and benchmark scores. |

当前版本保持离线、轻依赖，因此无需 API Key 就能快速运行。项目结构也为后续接入 LangGraph、向量数据库和真实 LLM 调用预留了扩展路径。

The first version is intentionally offline and dependency-light, so it can run quickly without API keys. The architecture is prepared for later LangGraph, vector database, and real LLM integration.

## Key Features / 核心功能

- 解析中文无人机任务描述。<br>
  Parses Chinese UAV mission descriptions.
- 提取无人机数量、搜索区域、禁飞区、任务目标和协同约束。<br>
  Extracts UAV count, search areas, no-fly zones, objectives, and coordination constraints.
- 从本地知识库检索无人机任务规划知识。<br>
  Retrieves UAV planning knowledge from a local knowledge base.
- 生成搜索、覆盖、禁飞区规避和弱通信协同相关的规划建议。<br>
  Generates planning recommendations for search, coverage, no-fly-zone avoidance, and weak communication.
- 输出结构化 JSON 任务配置。<br>
  Outputs a structured JSON mission configuration.
- 运行小型无人机任务 benchmark，并给出场景级评分。<br>
  Runs a mini UAV mission benchmark with scenario-level scoring.
- 提供 Agent 节点追踪和复核输出，增强可解释性。<br>
  Provides an Agent-style node trace and review output for explainability.
- 生成本地 HTML 可视化页面，展示任务输入、Agent 节点流、规划输出和 benchmark 分数。<br>
  Generates a local HTML dashboard for mission input, Agent node flow, planning output, and benchmark scores.
- 包含单元测试和示例输出，便于复现实验结果。<br>
  Includes unit tests and example output for reproducible checks.

## Example Scenario / 示例任务

下面是一个典型的中文无人机任务输入，要求 3 架无人机搜索指定区域、避开禁飞区、优先覆盖可疑目标点，并在弱通信条件下保持协同。

The following is a typical Chinese UAV mission input. It asks three UAVs to search a target area, avoid a no-fly zone, prioritize suspicious target points, and maintain coordination under weak communication.

Input / 输入：

```text
使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。
```

输出结果包括任务字段解析、相关无人机规划知识、规划建议、任务风险和 JSON 任务配置。

The output includes task parsing, retrieved UAV planning knowledge, planning recommendations, mission risks, and JSON mission configuration.

Representative output / 示例输出：[`examples/example_output.json`](examples/example_output.json)

## Agent Workflow / Agent 工作流

当前系统采用一个离线、无外部依赖的 Agent 图。每个节点都会读取和写入显式共享状态，最终输出可以包含 `agent_trace` 数组，用来解释哪些节点被执行、每个节点消费了什么输入、产生了什么输出。

The current implementation is a dependency-free Agent graph. Each node reads and writes an explicit shared state, and the final output can include an `agent_trace` array that explains which nodes ran, what they consumed, and what they produced.

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

这种实现方式让当前原型易于运行，同时保留了向 LangGraph 多节点工作流升级的清晰路径。

This keeps the current prototype easy to run while preserving a clean path toward LangGraph-based multi-node workflows.

## Architecture / 架构说明

项目按任务解析、知识检索、规划生成、benchmark 评估、CLI 入口和 HTML 可视化进行模块化拆分，便于后续替换为真实 LLM、向量检索或 LangGraph 节点。

The project is modularized around task parsing, knowledge retrieval, planning generation, benchmark evaluation, CLI execution, and HTML visualization, making it easy to later replace components with a real LLM, vector retrieval, or LangGraph nodes.

| Module / 模块 | Responsibility / 职责 |
|---|---|
| `task_parser.py` | 从自然语言输入中提取结构化任务字段。<br>Extract structured mission fields from natural-language input. |
| `agent_graph.py` | 以可追踪 Agent 节点方式运行解析、检索、规划和复核流程。<br>Run parser, retriever, planner, and reviewer as traceable Agent nodes. |
| `knowledge_base.py` | 使用轻量 RAG 风格评分器检索相关无人机规划片段。<br>Retrieve relevant UAV planning snippets with a lightweight RAG-style scorer. |
| `planner.py` | 生成规划建议、风险说明和任务配置。<br>Generate recommendations, risk notes, and mission configuration. |
| `workflow.py` | 编排端到端任务智能流程。<br>Orchestrate the end-to-end mission intelligence workflow. |
| `scenario_loader.py` | 加载结构化无人机 benchmark 场景。<br>Load structured UAV benchmark scenarios. |
| `evaluator.py` | 根据场景期望对任务方案进行评分。<br>Score mission plans against scenario expectations. |
| `benchmark.py` | 在场景集上运行工作流并汇总指标。<br>Run the workflow across a scenario set and summarize metrics. |
| `dashboard.py` | 生成本地静态 HTML 可视化页面。<br>Generate a local static HTML visualization page. |
| `cli.py` | 提供命令行运行入口。<br>Provide a command-line entry point. |

项目目录结构如下，核心代码位于 `src/uav_mission_agent/`，示例、benchmark 数据、评估结果和 dashboard 分别放在独立目录中。

The project layout is shown below. Core code lives in `src/uav_mission_agent/`, while examples, benchmark data, evaluation results, and the dashboard are organized in separate directories.

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

## Quick Start / 快速开始

先克隆仓库并进入项目目录。

First, clone the repository and enter the project directory.

```bash
git clone https://github.com/poliment/uav-mission-intelligence-agent.git
cd uav-mission-intelligence-agent
```

运行完整测试套件，确认本地环境可以正常执行。

Run the full test suite to confirm that the local environment works correctly.

```bash
python -m unittest discover -s tests -v
```

在 Windows PowerShell 中运行单条任务示例。

Run a single-mission example on Windows PowerShell.

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

如果希望看到 Agent 节点执行轨迹，可以使用 `--trace` 参数。

Use the `--trace` flag if you want to inspect the Agent node execution trace.

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --trace "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

在 macOS 或 Linux 上运行单条任务示例。

Run a single-mission example on macOS or Linux.

```bash
PYTHONPATH=src python -m uav_mission_agent.cli "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

运行小型 benchmark，评估任务解析、目标覆盖、约束覆盖、风险关键词和结构化配置等指标。

Run the mini benchmark to evaluate task parsing, objective coverage, constraint coverage, risk keywords, and structured configuration.

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --benchmark data\scenarios
```

代表性 benchmark 结果保存在 [`results/example_evaluation.json`](results/example_evaluation.json)。

A representative benchmark result is available at [`results/example_evaluation.json`](results/example_evaluation.json).

生成本地 HTML dashboard，用于本地运行结果检查，集中呈现任务输入、Agent 节点流、规划输出和 benchmark 分数。

Generate the local HTML dashboard for local result inspection, presenting the mission input, Agent node flow, planning output, and benchmark scores in one page.

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --dashboard dashboard\uav_mission_dashboard.html
```

生成后可以直接用浏览器打开 [`dashboard/uav_mission_dashboard.html`](dashboard/uav_mission_dashboard.html)。

After generation, open [`dashboard/uav_mission_dashboard.html`](dashboard/uav_mission_dashboard.html) directly in a browser.

也可以选择 editable install，之后直接通过模块方式运行 CLI。

You can also use an editable install and then run the CLI as a module.

```bash
python -m pip install -e .
python -m uav_mission_agent.cli "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

## Sample Output Fragment / 输出片段示例

下面展示的是输出 JSON 的核心结构，包括解析后的任务、任务配置和 Agent 复核结果。

The following fragment shows the core JSON output structure, including the parsed task, mission configuration, and Agent review result.

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

## Implementation Notes / 实现说明

- 任务领域明确，工作流围绕无人机任务规划构建，而不是通用聊天流程。<br>
  The task domain is explicit; the workflow is designed for UAV mission planning rather than generic chat behavior.
- 结构化推理清晰，系统把解析、检索、规划和配置生成拆分为不同阶段。<br>
  Structured reasoning is clear; the pipeline separates parsing, retrieval, planning, and configuration generation.
- Agent 可追踪，每个节点记录执行顺序、输入键、输出键和复核状态。<br>
  The Agent graph is traceable, recording node order, input keys, output keys, and review status.
- 包含 benchmark 评估，不只停留在单条示例，而是包含结构化无人机场景和评估器。<br>
  Benchmark evaluation is included through structured UAV scenarios and an evaluator, instead of only a single example.
- dashboard 用于结果检查，CLI 可以生成静态 HTML 页面，展示本地运行结果。<br>
  The dashboard supports result inspection; the CLI can generate a static HTML page for local outputs.
- RAG-ready，本地知识检索器后续可以替换为 FAISS、Chroma 或其他向量数据库。<br>
  The project is RAG-ready; the local knowledge retriever can later be replaced by FAISS, Chroma, or another vector database.
- Agent-ready，每个模块都可以进一步升级为 LangGraph 节点。<br>
  The project is Agent-ready; each module can become a LangGraph node in a future multi-agent workflow.
- 当前原型可测试、可离线运行，当前行为由单元测试覆盖，不依赖网络访问。<br>
  The current prototype is testable and offline; current behavior is covered by unit tests and runs without network access.

## Mini Benchmark / 小型 Benchmark

当前 benchmark 包含三个无人机任务场景，覆盖区域搜索、动态禁飞区重规划、多无人机目标跟踪和弱通信协同等能力。

The current benchmark contains three UAV mission scenarios covering area search, dynamic no-fly-zone replanning, multi-UAV target tracking, and weak-communication coordination.

| Scenario / 场景 | Capability tested / 测试能力 |
|---|---|
| `area_search_low_bandwidth` | 区域搜索、弱通信协同、禁飞区规避。<br>Area search, weak communication, and no-fly-zone avoidance. |
| `no_fly_zone_replan` | 动态禁飞区重规划和障碍规避。<br>Dynamic no-fly-zone replanning and obstacle avoidance. |
| `target_tracking_multi_uav` | 多无人机目标跟踪和协同。<br>Multi-UAV target tracking and coordination. |

评估维度包括无人机数量提取、搜索区域提取、禁飞区提取、目标覆盖、约束覆盖和风险关键词覆盖。

Evaluation dimensions include UAV count extraction, search area extraction, no-fly-zone extraction, objective coverage, constraint coverage, and risk keyword coverage.

Current sample result / 当前示例结果：

```text
total_scenarios: 3
average_score: 1.0
passed_scenarios: 3
```

## Current Test Coverage / 当前测试覆盖

当前测试套件覆盖中文无人机任务字段提取、相关知识检索、端到端输出结构、场景加载、benchmark 评分、CLI benchmark 模式、Agent trace 输出、本地 HTML dashboard 渲染和 CLI dashboard 生成模式。

The current test suite validates Chinese UAV mission field extraction, relevant UAV knowledge retrieval, end-to-end workflow output structure, scenario loading, benchmark scoring, CLI benchmark mode, Agent graph trace output, local HTML dashboard rendering, and CLI dashboard generation mode.

Run / 运行：

```bash
python -m unittest discover -s tests -v
```

Expected result / 预期结果：

```text
Ran 19 tests
OK
```

## Roadmap / 路线图

- 用 LangGraph 实现当前的无依赖 Agent 图。<br>
  Replace the dependency-free Agent graph with a LangGraph implementation of the current nodes.
- 用 FAISS 或 Chroma 替换本地轻量检索器。<br>
  Replace the local retriever with FAISS or Chroma.
- 增加 OpenAI-compatible API 的 LLM provider adapter。<br>
  Add an LLM provider adapter for OpenAI-compatible APIs.
- 增加面向仿真器的结构化 YAML 输出。<br>
  Add structured YAML output for simulator-style mission configuration.
- 扩展更多无人机场景，包括区域搜索、目标跟踪、禁飞区规避、弱通信和多无人机任务分配。<br>
  Add more UAV scenarios, including area search, target tracking, no-fly-zone avoidance, weak communication, and multi-UAV task allocation.
- 增加更难的 benchmark case，例如模糊指令和冲突约束。<br>
  Add harder benchmark cases with ambiguous commands and conflicting constraints.
- 在静态 dashboard 基线之后，增加交互式 Streamlit 页面或 FastAPI 服务。<br>
  Add an interactive Streamlit page or FastAPI service after the static dashboard baseline.

## Project Summary / 项目总结

构建了一个无人机领域 LLM/Agent 原型，能够将自然语言无人机任务请求转化为结构化任务方案，并结合可追踪 Agent 节点、任务解析、RAG 风格本地知识检索、规划建议、风险解释、JSON 配置输出和 benchmark 场景评估。

Built a UAV-domain LLM/Agent prototype that converts natural-language UAV mission requests into structured mission plans by combining traceable Agent nodes, task parsing, RAG-style local knowledge retrieval, planning recommendations, risk explanation, JSON configuration output, and benchmark-style scenario evaluation.
