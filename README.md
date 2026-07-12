# UAV Mission Intelligence Agent / 无人机任务智能体

[![Tests](https://github.com/poliment/uav-mission-intelligence-agent/actions/workflows/test.yml/badge.svg)](https://github.com/poliment/uav-mission-intelligence-agent/actions/workflows/test.yml)

![Streamlit UAV swarm mission console / Streamlit 无人机集群任务控制台](docs/assets/streamlit-swarm-console.jpg)

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
- **Swarm coordination / 集群协调**: Assigns per-UAV roles from a natural-language mission and replans after low-battery, target-detection, and degraded-communication events. / 根据自然语言任务为每架无人机分配角色，并在低电量、目标发现和通信下降事件后执行重规划。
- **Multi-agent collaboration / 多智能体协作**: Converts real swarm events and assignment changes into a structured agent message timeline with explicit senders, recipients, acknowledgements, and memory links. / 将真实集群事件和任务变更转换为结构化智能体消息时间线，包含明确的发送者、接收者、确认消息和记忆关联。
- **Evaluation and demo / 评测与演示**: Runs benchmark reports, provider comparison, local mission visualization, a Python Streamlit console, and a compatible FastAPI JSON service. / 支持基准评测、供应商对比、本地任务可视化、Python Streamlit 控制台和兼容的 FastAPI JSON 服务。

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

Natural-language swarm mission / 自然语言集群任务
        |
        v
swarm_coordinator.py / Swarm Coordinator
        |
        +--> SwarmMissionState + SwarmMemory / 集群状态与记忆
        +--> optional provider explanation / 可选模型解释增强
        +--> swarm_dialogue.py / structured collaboration messages / 结构化协作消息
        +--> swarm_demo.py / deterministic shared demo session / 确定性共享演示会话
        +--> streamlit_app.py + swarm_visualization.py / Python UI + Plotly map
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
| `swarm_coordinator.py` | Converts natural-language swarm missions and runtime events into checked role assignments, rationale, and memory updates. / 将自然语言集群任务和运行事件转换为经过校验的角色分配、决策解释和记忆更新。 |
| `swarm_dialogue.py` | Builds event-linked UAV reports, task handoffs, relay acknowledgements, coordinator summaries, and memory records. / 生成与事件关联的无人机报告、任务接替、中继确认、协调器总结和记忆记录。 |
| `swarm_demo.py`, `swarm_visualization.py` | Share the deterministic four-UAV session and render its 20×20 Plotly map. / 共享确定性的四机演示会话，并渲染 20×20 Plotly 地图。 |
| `streamlit_app.py` | Provides the Python-only five-view mission console. / 提供纯 Python 编写的五视图任务控制台。 |
| `mission_visualization.py`, `dashboard.py` | Render local mission visuals and dashboard reports. / 渲染本地任务可视化和仪表盘报告。 |
| `demo_service.py`, `demo_app.py`, `demo_cli.py`, `api_cli.py` | Preserve single-mission helpers and expose separate Streamlit and FastAPI launchers. / 保留单任务能力，并分别提供 Streamlit 与 FastAPI 启动入口。 |
| `benchmark.py`, `benchmark_v2.py`, `evaluator.py` | Evaluate mission quality, latency, provider comparison, and estimated cost. / 评估任务质量、延迟、供应商对比和估算成本。 |

## Swarm upgrade status / 集群升级状态

The swarm layer adds deterministic tools that can be called before accepting an LLM-generated coordination plan. / 集群层增加了确定性工具，可在接受 LLM 生成的协同方案之前执行可行性校验。

| Layer / 层级 | Module / 模块 | Status / 状态 |
|---|---|---|
| Swarm data models / 集群数据模型 | `swarm_models.py` | Models UAV agents, grid positions, detected targets, mission events, swarm memory, and mission state. / 建模无人机智能体、网格位置、检测目标、任务事件、集群记忆和任务状态。 |
| Virtual environment / 虚拟环境 | `swarm_environment.py` | Provides a bounded 2D grid, obstacles, no-fly zones, communication checks, battery drain, target discovery, and tick events. / 提供有边界的二维网格、障碍物、禁飞区、通信检查、电量消耗、目标发现和时钟事件。 |
| Traditional algorithms / 传统算法 | `swarm_algorithms.py` | Uses A* paths with battery, communication, scoring, and target-assignment checks. / 使用 A* 路径，并结合电量、通信、评分和目标分配校验。 |
| High-level coordination / 高层集群协调 | `swarm_coordinator.py` | Assigns `scout`, `tracker`, `relay`, `reserve`, and `returning` roles, then records explainable decisions in swarm memory. / 分配 `scout`、`tracker`、`relay`、`reserve` 和 `returning` 角色，并将可解释决策写入集群记忆。 |
| Multi-Agent Collaboration / 多智能体协作 | `swarm_dialogue.py` | Produces a UI-ready agent message timeline from target, battery, handoff, relay, and coordinator messages. / 根据目标、电量、接替、中继和协调器消息生成可供 UI 使用的智能体消息时间线。 |
| Demo/UI integration / Demo 与界面集成 | `swarm_demo.py`, `streamlit_app.py`, `swarm_visualization.py` | Shares one stateful deterministic session across five Streamlit views and exposes the same scenario through JSON APIs. / 在五个 Streamlit 视图中共享一个有状态确定性会话，并通过 JSON API 暴露相同场景。 |

`swarm_algorithms.py` exposes `astar_path(...)`, `check_battery_feasibility(...)`, `check_communication_coverage(...)`, `score_candidate_for_target(...)`, and `assign_targets_to_uavs(...)` as explainable planning primitives. / `swarm_algorithms.py` 暴露 `astar_path(...)`、`check_battery_feasibility(...)`、`check_communication_coverage(...)`、`score_candidate_for_target(...)` 和 `assign_targets_to_uavs(...)` 作为可解释的规划基础能力。

`SwarmCoordinator` keeps deterministic assignments authoritative while an optional provider may add recommendation and risk text. Dynamic replanning / 动态重规划 currently handles `battery_warning`, `target_detected`, and `communication_degraded` events. / `SwarmCoordinator` 始终以确定性分配为准，可选模型供应商仅补充建议和风险文本；当前动态重规划支持低电量、目标发现和通信下降三类事件。

`SwarmDialogueEngine` wraps those real replanning results and records every structured message as an `agent_message` event in `SwarmMemory`. Messages therefore explain actual state changes instead of forming an unrelated free-form chat. / `SwarmDialogueEngine` 包装真实重规划结果，并将每条结构化消息作为 `agent_message` 事件写入 `SwarmMemory`，因此消息解释的是实际状态变化，而不是无关的自由聊天。

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

## Swarm Coordinator Offline Demo / 集群协调器离线演示

Run the fixed Stage 4 scenario to print both a natural-language four-UAV mission plan and a low-battery event response. The output includes role assignments, rule rationale, A* and constraint checks, assignment changes, and memory updates. / 运行阶段 4 固定场景，可同时输出自然语言四机任务方案和低电量事件响应；结果包含角色分配、规则解释、A* 与约束校验、任务变更和记忆更新。

```powershell
$env:PYTHONPATH="src"
python examples/swarm_coordinator_demo.py
```

## Multi-Agent Collaboration Offline Demo / 多智能体协作离线演示

Run the fixed Stage 5 scenario to process target detection, low-battery task handoff, and degraded-communication relay support in one ordered timeline. Each message includes sender, recipients, type, trigger event, memory event id, and structured coordination evidence. / 运行阶段 5 固定场景，可在同一条有序时间线中展示目标发现、低电量任务接替和通信下降中继支援；每条消息都包含发送者、接收者、类型、触发事件、记忆事件 id 和结构化协调证据。

```powershell
$env:PYTHONPATH="src"
python examples/swarm_dialogue_demo.py
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

The optional demo package starts a local Streamlit mission console written in Python. It defaults to an offline, reproducible four-UAV session; an online provider can enhance only the initial plan, while event handling and Agent dialogue remain deterministic. / 可选演示包会启动一个纯 Python 编写的本地 Streamlit 任务控制台。默认使用离线、可复现的四机共享会话；在线供应商只增强初始方案，事件处理与 Agent 对话仍保持确定性。

```powershell
pip install -e ".[demo]"
uav-mission-agent-demo --host 127.0.0.1 --port 8000
```

Add `--no-browser` for a headless launch. Open `http://127.0.0.1:8000` when the process is ready. / 无界面启动时增加 `--no-browser`；进程就绪后打开 `http://127.0.0.1:8000`。

The console has five operational views. / 控制台包含五个操作视图。

- **Swarm Plan**: 4 roles, A* paths, battery checks, communication checks, and provider advisory. / 四机角色、A* 路径、电量校验、通信校验和供应商建议。
- **Event Response**: Process the fixed target, battery, and communication events one by one or together. / 逐个或一次性处理固定的目标、电量和通信事件。
- **Agent Dialogue**: Inspect 9 structured messages and their 9 memory links. / 查看 9 条结构化消息及对应的 9 个记忆关联。
- **Mission Intelligence**: Inspect the legacy single-mission Agent trace, SVG, validation, and JSON. / 查看原单任务 Agent 追踪、SVG、校验和 JSON。
- **Evaluation**: Inspect offline benchmark and provider comparison results. / 查看离线基准和供应商对比结果。

Use a local environment file when you want provider keys during a demo without committing secrets into the repository. / 演示时如果需要供应商密钥，可以使用本地环境文件，避免把密钥提交到仓库。

```powershell
uav-mission-agent-demo --env-file D:\epacode\working\.secrets\deepseek.env
```

FastAPI remains available as a stateless JSON compatibility layer and can run on a separate port. / FastAPI 继续作为无状态 JSON 兼容层，可在另一个端口启动。

```powershell
uav-mission-agent-api --host 127.0.0.1 --port 8010
```

Available routes are `GET /`, `GET /api/health`, `POST /api/mission`, `GET /api/benchmark`, `GET /api/swarm/demo-plan`, `GET /api/swarm/demo-events`, and `GET /api/swarm/demo-dialogue`. The three swarm routes create fresh offline sessions so their output is stable across calls. / 三个集群接口每次创建新的离线会话，因此多次调用结果保持稳定。

## Example Outputs / 示例输出

Representative outputs are kept in the repository for quick inspection and regression checks. / 仓库中保留了代表性输出，便于快速查看和回归检查。

- `examples/example_output.json`: Example mission-planning result. / 示例任务规划结果。
- `examples/swarm_coordinator_demo.py`: Reproducible Swarm Coordinator plan and event-response demo. / 可复现的集群协调任务规划与事件响应示例。
- `examples/swarm_dialogue_demo.py`: Reproducible three-event multi-agent collaboration timeline. / 可复现的三事件多智能体协作时间线。
- `results/example_evaluation.json`: Example evaluation report. / 示例评估报告。
- `docs/assets/streamlit-swarm-console.jpg`: Credential-free Streamlit console screenshot. / 不含凭据的 Streamlit 控制台截图。
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

Install the Demo and Test extras to run Streamlit AppTest, Plotly, and FastAPI TestClient coverage. / 安装 Demo 与 Test 扩展后可运行 Streamlit AppTest、Plotly 和 FastAPI TestClient 测试。

```bash
python -m pip install -e ".[demo,test]"
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
+-- .streamlit/                     Streamlit theme / Streamlit 主题
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

- Extend benchmark coverage for role assignment, A* feasibility, and communication constraints. / 扩展角色分配、A* 可行性和通信约束的基准覆盖。
- Connect the deterministic session to a simulator adapter without changing its public API. / 在不改变公共 API 的前提下连接确定性会话与仿真器适配层。
- Add optional deployment and authentication profiles while keeping local mode offline-first. / 在保持本地离线优先的同时增加可选部署与认证配置。
