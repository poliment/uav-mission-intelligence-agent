# UAV Mission Intelligence Agent / 无人机任务智能体

[![Tests](https://github.com/poliment/uav-mission-intelligence-agent/actions/workflows/test.yml/badge.svg)](https://github.com/poliment/uav-mission-intelligence-agent/actions/workflows/test.yml)

![UAV Mission Intelligence Agent demo / 无人机任务智能体演示](docs/assets/uav-mission-demo.png)

![UAV mission execution visualization / 无人机任务执行可视化](docs/assets/mission-execution-visualization.svg)

![Expanded UAV benchmark coverage / 扩展后的无人机基准覆盖](docs/assets/benchmark-coverage.svg)

## Project Introduction / 项目介绍

UAV Mission Intelligence Agent is an offline-first prototype for UAV mission understanding, retrieval-assisted planning, and deterministic swarm feasibility checks. / UAV Mission Intelligence Agent 是一个离线优先的无人机任务智能体原型，用于任务理解、检索增强规划和确定性的集群可行性校验。

The project turns Chinese natural-language mission requests into structured mission plans, retrieves local UAV planning knowledge with vector RAG, evaluates constraints such as no-fly zones, battery, communication, and target assignment, and returns traceable JSON outputs for demos, benchmarks, and future simulator integration. / 本项目将中文自然语言任务请求转换为结构化任务方案，通过本地向量 RAG 检索无人机规划知识，评估禁飞区、电量、通信和目标分配等约束，并输出可追踪的 JSON 结果，便于演示、基准评测和未来仿真系统集成。

The implementation intentionally separates LLM-facing reasoning from deterministic engineering logic, so the agent can explain mission intent while algorithmic modules decide whether a plan is feasible. / 该实现刻意将面向 LLM 的推理说明与确定性工程逻辑分离，因此智能体可以解释任务意图，而算法模块负责判断方案是否可执行。

## What It Does / 功能定位

- **Mission parsing / 任务解析**: Parses Chinese UAV mission requests into UAV count, search areas, no-fly zones, objectives, and coordination constraints. / 将中文无人机任务请求解析为无人机数量、搜索区域、禁飞区、任务目标和协同约束。
- **Local RAG retrieval / 本地 RAG 检索**: Retrieves planning references with deterministic local vectors and records `score`, `rank`, `retriever`, and `matched_tags` evidence. / 使用确定性的本地向量检索规划参考，并记录 `score`、`rank`、`retriever` 和 `matched_tags` 等证据字段。
- **Planning output / 规划输出**: Produces recommendations, risks, structured mission configuration, schema-wrapped output, and Agent trace records. / 生成规划建议、风险提示、结构化任务配置、Schema 包装结果和 Agent 节点追踪记录。
- **Provider flexibility / 模型供应商灵活性**: Runs offline by default, with optional DeepSeek, OpenAI-compatible, and LangGraph-backed refinement paths. / 默认离线运行，同时可选接入 DeepSeek、OpenAI 兼容接口和 LangGraph 后端进行增强。
- **Swarm feasibility / 集群可行性**: Models multi-UAV state and checks grid movement, obstacles, no-fly zones, battery reserve, communication coverage, and target assignment. / 建模多无人机状态，并校验网格移动、障碍物、禁飞区、电量余量、通信覆盖和目标分配。
- **Evaluation and demo / 评测与演示**: Runs benchmark reports, provider comparison, estimated cost summaries, local mission visualization, and an optional FastAPI + HTML demo. / 支持基准评测、供应商对比、成本估算、本地任务可视化，以及可选的 FastAPI + HTML 交互演示。

## Technical Architecture / 技术架构

The core workflow is a small Agent pipeline: parse the mission, retrieve relevant planning knowledge, draft a plan, review risk and structure, then emit a machine-readable result. / 核心工作流是一个小型 Agent 管线：先解析任务，再检索相关规划知识，随后生成方案、复核风险与结构，最后输出机器可读结果。

```text
Mission request / 任务请求
        |
        v
task_parser_agent / 任务解析节点
        |
        v
knowledge_retriever_agent / 知识检索节点  ---> local vector RAG / 本地向量 RAG
        |
        v
mission_planner_agent / 任务规划节点       ---> optional LLM provider / 可选模型供应商
        |
        v
mission_reviewer_agent / 任务复核节点
        |
        v
Structured plan + risks + JSON config + Agent trace
结构化方案 + 风险提示 + JSON 配置 + Agent 追踪

Swarm extension / 集群扩展

SwarmMissionState / 集群任务状态
        |
        +--> SwarmGridEnvironment / 集群网格环境
        |       +-- grid, obstacle, no-fly-zone, communication, battery, target events
        |       +-- 网格、障碍物、禁飞区、通信、电量、目标事件
        |
        +--> swarm_algorithms.py / 集群算法模块
                +-- A* path planning / A* 路径规划
                +-- battery feasibility / 电量可行性
                +-- communication coverage / 通信覆盖
                +-- candidate scoring / 候选评分
                +-- target assignment / 目标分配
```

The architecture keeps dependency-free local execution as the default path, while optional extras add vector-store adapters, LangGraph orchestration, or a web demo only when needed. / 该架构将无额外依赖的本地执行作为默认路径，只有在需要时才通过可选扩展加入向量库适配、LangGraph 编排或网页演示能力。

## Module Map / 模块说明

The repository is organized around clear module responsibilities, making it easier to test the Agent workflow and the swarm algorithm layer independently. / 仓库按清晰的模块职责组织，便于分别测试 Agent 工作流和集群算法层。

| Module / 模块 | Responsibility / 职责 |
|---|---|
| `task_parser.py` | Extracts structured fields from Chinese mission text. / 从中文任务文本中提取结构化字段。 |
| `agent_graph.py` | Runs parser, retriever, planner, and reviewer nodes with trace output. / 串联解析、检索、规划和复核节点，并输出追踪记录。 |
| `knowledge_base.py`, `embeddings.py`, `retrievers.py` | Provide local vector RAG and optional FAISS/Chroma adapter boundaries. / 提供本地向量 RAG，并保留可选 FAISS/Chroma 适配边界。 |
| `planner.py`, `schemas.py`, `workflow.py` | Generate and validate mission plans for the default workflow. / 为默认工作流生成并校验任务方案。 |
| `llm_provider.py` | Supports offline, DeepSeek, and OpenAI-compatible provider paths. / 支持离线、DeepSeek 和 OpenAI 兼容供应商路径。 |
| `swarm_models.py` | Defines UAV agent states, mission events, detected targets, and swarm memory. / 定义无人机智能体状态、任务事件、检测目标和集群记忆。 |
| `swarm_environment.py` | Simulates a deterministic 2D grid environment for swarm checks. / 模拟用于集群校验的确定性二维网格环境。 |
| `swarm_algorithms.py` | Provides A* planning, battery checks, communication checks, scoring, and assignment. / 提供 A* 路径规划、电量校验、通信校验、评分和分配算法。 |
| `mission_visualization.py`, `dashboard.py` | Render local mission visuals and dashboard reports. / 渲染本地任务可视化和仪表盘报告。 |
| `demo_service.py`, `demo_app.py`, `demo_cli.py` | Serve the optional FastAPI demo experience. / 提供可选的 FastAPI 演示服务。 |
| `benchmark.py`, `benchmark_v2.py`, `evaluator.py` | Evaluate mission quality, latency, provider comparison, and estimated cost. / 评估任务质量、延迟、供应商对比和估算成本。 |

## Swarm upgrade status / 集群升级状态

The swarm layer adds deterministic tools that can be called before accepting an LLM-generated coordination plan. / 集群层增加了确定性工具，可在接受 LLM 生成的协同方案之前执行可行性校验。

| Layer / 层级 | Module / 模块 | Status / 状态 |
|---|---|---|
| Swarm data models / 集群数据模型 | `swarm_models.py` | Models UAV agents, grid positions, detected targets, mission events, swarm memory, and mission state. / 建模无人机智能体、网格位置、检测目标、任务事件、集群记忆和任务状态。 |
| Virtual environment / 虚拟环境 | `swarm_environment.py` | Provides a bounded 2D grid, obstacles, no-fly zones, communication checks, battery drain, target discovery, and tick events. / 提供有边界的二维网格、障碍物、禁飞区、通信检查、电量消耗、目标发现和时钟事件。 |
| Traditional algorithms / 传统算法 | `swarm_algorithms.py` | Uses A* paths with battery, communication, scoring, and target-assignment checks. / 使用 A* 路径，并结合电量、通信、评分和目标分配校验。 |

`swarm_algorithms.py` exposes `astar_path(...)`, `check_battery_feasibility(...)`, `check_communication_coverage(...)`, `score_candidate_for_target(...)`, and `assign_targets_to_uavs(...)` as explainable planning primitives. / `swarm_algorithms.py` 暴露 `astar_path(...)`、`check_battery_feasibility(...)`、`check_communication_coverage(...)`、`score_candidate_for_target(...)` 和 `assign_targets_to_uavs(...)` 作为可解释的规划基础能力。

## Quick Start / 快速开始

The default workflow runs offline and does not require API keys or external services. / 默认工作流可离线运行，不需要 API key 或外部服务。

```bash
git clone https://github.com/poliment/uav-mission-intelligence-agent.git
cd uav-mission-intelligence-agent
python -m unittest discover -s tests -v
```

Run a single mission from Windows PowerShell with the source path enabled. / 在 Windows PowerShell 中启用源码路径并运行单条任务。

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli "使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。"
```

Show the Agent trace when you need to inspect each workflow node. / 需要查看每个工作流节点时，可以输出 Agent 追踪记录。

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --trace "使用3架无人机搜索区域A，避开禁飞区B，并保持弱通信条件下协同。"
```

Generate schema-wrapped output for downstream tools or tests. / 为下游工具或测试生成带 Schema 包装的输出。

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --schema-output "使用3架无人机搜索区域A，避开禁飞区B，并保持弱通信条件下协同。"
```

## Benchmarks and Dashboard / 基准评测与仪表盘

The benchmark commands evaluate local scenario files and can include provider comparison fields such as score, latency, token usage, and estimated cost. / 基准评测命令会评估本地场景文件，并可包含得分、延迟、Token 用量和估算成本等供应商对比字段。

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --benchmark data\scenarios
```

Benchmark v2 uses the offline provider by default and can be expanded with optional provider settings. / Benchmark v2 默认使用离线供应商，也可以通过可选供应商设置扩展。

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --benchmark-v2 data\scenarios
```

The dashboard command writes a local HTML report that combines mission output, Agent trace, benchmark scores, and provider comparison. / 仪表盘命令会生成本地 HTML 报告，整合任务输出、Agent 追踪、基准得分和供应商对比。

```powershell
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --dashboard dashboard\uav_mission_dashboard.html
```

## RAG Retrieval / RAG 检索

The default retrieval backend is `local-vector`, which uses deterministic sparse vectors and cosine similarity, so it runs without API keys, network calls, FAISS, Chroma, or embedding services. / 默认检索后端是 `local-vector`，它使用确定性的稀疏向量和余弦相似度，因此无需 API key、网络调用、FAISS、Chroma 或嵌入服务即可运行。

Optional vector-store integrations are available through install extras. / 可选向量库集成可以通过安装扩展启用。

```powershell
python -m pip install -e ".[rag-faiss]"
python -m pip install -e ".[rag-chroma]"
```

Supported backend names are `local-vector`, `keyword`, `faiss`, and `chroma`. / 支持的后端名称包括 `local-vector`、`keyword`、`faiss` 和 `chroma`。

## Interactive Demo / 交互式 Demo

The optional demo package starts a local FastAPI service with mission input, provider selection, Agent trace, structured JSON output, provider comparison, and mission visualization. / 可选演示包会启动本地 FastAPI 服务，提供任务输入、供应商选择、Agent 追踪、结构化 JSON 输出、供应商对比和任务可视化。

```powershell
pip install -e ".[demo]"
uav-mission-agent-demo --host 127.0.0.1 --port 8000
```

Use a local environment file when you want provider keys during a demo without committing secrets into the repository. / 演示时如果需要供应商密钥，可以使用本地环境文件，避免把密钥提交到仓库。

```powershell
uav-mission-agent-demo --env-file D:\epacode\working\.secrets\deepseek.env
```

Open `http://127.0.0.1:8000` after the server starts. / 服务启动后打开 `http://127.0.0.1:8000`。

## Example Outputs / 示例输出

Representative outputs are kept in the repository for quick inspection and regression checks. / 仓库中保留了代表性输出，便于快速查看和回归检查。

- `examples/example_output.json`: Example mission-planning result. / 示例任务规划结果。
- `results/example_evaluation.json`: Example evaluation report. / 示例评估报告。
- `docs/assets/mission-execution-visualization.svg`: Mission execution visualization asset. / 任务执行可视化资源。

Typical mission input is Chinese because the current parser is optimized for Chinese UAV mission requests. / 典型任务输入使用中文，因为当前解析器主要面向中文无人机任务请求优化。

```text
使用3架无人机搜索区域A，避开禁飞区B，优先覆盖可疑目标点，并保持弱通信条件下协同。
```

The output includes parsed task fields, retrieved planning knowledge, recommendations, risks, JSON mission configuration, optional schema envelope, and optional Agent trace. / 输出内容包括解析后的任务字段、检索到的规划知识、规划建议、风险提示、JSON 任务配置、可选 Schema 包装和可选 Agent 追踪。

## Testing / 测试

The test suite is offline by default and uses fake or local providers, so CI does not require API keys. / 测试套件默认离线运行，并使用模拟或本地供应商，因此 CI 不需要 API key。

```bash
python -m unittest discover -s tests -v
```

Pytest can also be used when it is available in the local environment. / 本地环境安装 pytest 时也可以使用 pytest。

```bash
PYTHONPATH=src python -m pytest
```

## Project Structure / 项目结构

The repository keeps source code, test cases, benchmark data, example outputs, and public documentation assets separate. / 仓库将源码、测试、基准数据、示例输出和公开文档资源分开管理。

```text
uav-mission-intelligence-agent/
+-- data/scenarios/                 benchmark scenario data / 基准场景数据
+-- dashboard/                      generated local dashboard / 生成的本地仪表盘
+-- docs/assets/                    README and dashboard visuals / README 与仪表盘视觉资源
+-- examples/                       sample mission and trajectory inputs / 示例任务与轨迹输入
+-- results/                        sample benchmark outputs / 示例基准输出
+-- src/uav_mission_agent/          project source modules / 项目源码模块
+-- tests/                          unit tests / 单元测试
+-- pyproject.toml                  package metadata / 包元数据
+-- README.md                       project documentation / 项目文档
```

## Provider and Secret Hygiene / 模型供应商与密钥管理

Live provider calls are optional, and the default path remains offline for reproducible demos and tests. / 实时模型供应商调用是可选能力，默认路径保持离线，以便演示和测试可复现。

DeepSeek can be enabled with an environment variable when live refinement is needed. / 需要实时增强时，可以通过环境变量启用 DeepSeek。

```powershell
$env:DEEPSEEK_API_KEY="your-api-key"
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --llm-provider deepseek "use 3 UAVs to search area A"
```

OpenAI-compatible APIs can be configured with a key, model name, and base URL. / OpenAI 兼容接口可以通过密钥、模型名称和基础 URL 配置。

```powershell
$env:OPENAI_API_KEY="your-api-key"
$env:PYTHONPATH="src"
python -m uav_mission_agent.cli --llm-provider openai-compatible --llm-model gpt-4o-mini --llm-base-url https://api.openai.com/v1 "use 3 UAVs to search area A"
```

Keep API keys in environment variables or local env files, and do not commit keys, screenshots containing keys, or private env files. / 请将 API key 保存在环境变量或本地环境文件中，不要提交密钥、包含密钥的截图或私有环境文件。

## Roadmap / 路线图

- Connect the swarm algorithm layer to a high-level swarm coordinator. / 将集群算法层接入更高层的集群协调器。
- Add dynamic replanning demos for low battery, target discovery, and weak communication. / 增加低电量、目标发现和弱通信场景下的动态重规划演示。
- Expose swarm plan, event, and dialogue demos through the FastAPI UI. / 在 FastAPI 界面中展示集群方案、事件和对话演示。
- Extend benchmark coverage for role assignment, A* feasibility, and communication constraints. / 扩展角色分配、A* 可行性和通信约束的基准覆盖。
- Add richer visualization for multi-UAV grid movement and event timelines. / 为多无人机网格移动和事件时间线增加更丰富的可视化。
