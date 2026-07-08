# LangGraph Trajectory Intent Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add an optional LangGraph mission workflow and a deterministic UAV trajectory / intent recognition module while preserving real DeepSeek / OpenAI-compatible interfaces.

**Architecture:** Keep the current rule-based workflow as the default backend. Add `langgraph_workflow.py` as an optional backend that imports LangGraph only when requested. Add separate `trajectory.py` and `intent_recognition.py` modules so trajectory analysis is independently testable and later replaceable by a neural classifier.

**Tech Stack:** Python 3.10+, standard library, optional `langgraph`, existing unittest suite, existing DeepSeek/OpenAI-compatible provider adapter.

## Global Constraints

- Keep the existing rule-based workflow as the default path.
- Add a real LangGraph backend that uses `StateGraph`, `START`, `END`, `compile()`, and `invoke()` when `langgraph` is installed.
- Do not break or replace the existing DeepSeek / OpenAI-compatible provider adapter.
- Add CLI selection for mission graph backend: `--graph-backend rule-based|langgraph`.
- Add a small UAV trajectory module that accepts structured points with latitude, longitude, altitude, timestamp, speed, heading, roll, pitch, and yaw.
- Add trajectory summary features: point count, duration, altitude trend, speed trend, heading change, mean speed, and mean altitude.
- Add an intent recognition module that maps trajectory summaries to `area_search`, `target_tracking`, `return_to_base`, `loitering`, or `transit`.
- Add a CLI mode for trajectory intent recognition from a JSON file.
- Keep all new functionality testable without network calls and without requiring a real DeepSeek API key.
- Document LangGraph usage, optional dependency installation, trajectory input format, and CLI examples in `README.md`.

---

### Task 1: Optional LangGraph Backend

**Files:**
- Create: `src/uav_mission_agent/langgraph_workflow.py`
- Modify: `src/uav_mission_agent/workflow.py`
- Modify: `src/uav_mission_agent/cli.py`
- Test: `tests/test_langgraph_workflow.py`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `run_agent_workflow(text, knowledge_base=None, llm_provider=None)`, `LLMProvider`
- Produces: `run_langgraph_workflow(text, knowledge_base=None, llm_provider=None) -> dict[str, Any]`
- Produces: `run_mission_workflow(text, knowledge_base=None, llm_provider=None, graph_backend="rule-based") -> dict`

- [ ] **Step 1: Write failing LangGraph backend test**

```python
def test_langgraph_backend_uses_stategraph_nodes_in_order(self):
    fake_api = FakeLangGraphAPI()

    result = run_langgraph_workflow(
        "use 3 UAVs to search area A",
        graph_api=fake_api,
    )

    self.assertEqual(fake_api.graph.nodes, [
        "task_parser_agent",
        "knowledge_retriever_agent",
        "mission_planner_agent",
        "mission_reviewer_agent",
    ])
    self.assertTrue(fake_api.graph.compiled)
    self.assertEqual(result["graph_backend"], "langgraph")
    self.assertIn("mission_config", result)
```

Run: `python -B -m unittest tests.test_langgraph_workflow -v`

Expected: FAIL because `uav_mission_agent.langgraph_workflow` does not exist.

- [ ] **Step 2: Implement minimal LangGraph module**

Implement `LangGraphUnavailableError`, `_load_langgraph_api()`, `build_langgraph_app()`, and `run_langgraph_workflow()`. Use LangGraph API names `StateGraph`, `START`, `END`, `add_node`, `add_edge`, `compile`, and `invoke`. The fake API test supplies the same names.

- [ ] **Step 3: Verify LangGraph unit test passes**

Run: `python -B -m unittest tests.test_langgraph_workflow -v`

Expected: PASS.

- [ ] **Step 4: Write failing workflow/CLI backend tests**

Add tests that `run_mission_workflow("use 3 UAVs to search area A", graph_backend="langgraph")` calls the LangGraph backend through an injectable runner, and that CLI accepts `--graph-backend langgraph`.

Run: `python -B -m unittest tests.test_cli tests.test_workflow -v`

Expected: FAIL because `graph_backend` is not wired yet.

- [ ] **Step 5: Wire backend selection**

Add `graph_backend` to `workflow.py` and `--graph-backend` to `cli.py`. Keep `rule-based` as default. Preserve all current LLM provider flags.

- [ ] **Step 6: Verify backend selection**

Run: `python -B -m unittest tests.test_cli tests.test_workflow tests.test_langgraph_workflow -v`

Expected: PASS.

### Task 2: UAV Trajectory Summary

**Files:**
- Create: `src/uav_mission_agent/trajectory.py`
- Test: `tests/test_trajectory.py`

**Interfaces:**
- Produces: `TrajectoryPoint`
- Produces: `TrajectorySummary`
- Produces: `load_trajectory_points(data: list[dict[str, Any]]) -> list[TrajectoryPoint]`
- Produces: `summarize_trajectory(points: list[TrajectoryPoint]) -> TrajectorySummary`

- [ ] **Step 1: Write failing trajectory summary tests**

```python
def test_summarize_trajectory_reports_trends_and_heading_change(self):
    points = load_trajectory_points([
        {"timestamp": 0, "latitude": 30.0, "longitude": 120.0, "altitude": 100, "speed": 10, "heading": 0, "roll": 0, "pitch": 1, "yaw": 0},
        {"timestamp": 10, "latitude": 30.001, "longitude": 120.001, "altitude": 120, "speed": 12, "heading": 90, "roll": 5, "pitch": 2, "yaw": 90},
        {"timestamp": 20, "latitude": 30.002, "longitude": 120.002, "altitude": 140, "speed": 14, "heading": 180, "roll": -5, "pitch": 1, "yaw": 180},
    ])

    summary = summarize_trajectory(points)

    self.assertEqual(summary.point_count, 3)
    self.assertEqual(summary.duration_seconds, 20)
    self.assertEqual(summary.altitude_trend, "climbing")
    self.assertEqual(summary.speed_trend, "accelerating")
    self.assertEqual(summary.heading_change_degrees, 180)
```

Run: `python -B -m unittest tests.test_trajectory -v`

Expected: FAIL because `trajectory.py` does not exist.

- [ ] **Step 2: Implement trajectory dataclasses and summary**

Implement required-field validation, numeric conversion, mean altitude/speed, trend classification, and heading change normalization.

- [ ] **Step 3: Verify trajectory tests**

Run: `python -B -m unittest tests.test_trajectory -v`

Expected: PASS.

### Task 3: UAV Intent Recognition

**Files:**
- Create: `src/uav_mission_agent/intent_recognition.py`
- Test: `tests/test_intent_recognition.py`

**Interfaces:**
- Consumes: `load_trajectory_points`, `summarize_trajectory`, `TrajectoryPoint`
- Produces: `IntentRecognitionResult`
- Produces: `recognize_intent(points: list[TrajectoryPoint]) -> IntentRecognitionResult`

- [ ] **Step 1: Write failing intent recognition tests**

```python
def test_recognizes_loitering_from_high_heading_change_and_low_displacement(self):
    points = load_trajectory_points([
        {"timestamp": 0, "latitude": 30.0, "longitude": 120.0, "altitude": 100, "speed": 4, "heading": 0, "roll": 10, "pitch": 0, "yaw": 0},
        {"timestamp": 10, "latitude": 30.0001, "longitude": 120.0001, "altitude": 101, "speed": 4, "heading": 160, "roll": -10, "pitch": 0, "yaw": 160},
        {"timestamp": 20, "latitude": 30.0002, "longitude": 120.0001, "altitude": 101, "speed": 4, "heading": 320, "roll": 12, "pitch": 0, "yaw": 320},
    ])

    result = recognize_intent(points)

    self.assertEqual(result.intent, "loitering")
    self.assertGreater(result.confidence, 0.5)
```

Run: `python -B -m unittest tests.test_intent_recognition -v`

Expected: FAIL because `intent_recognition.py` does not exist.

- [ ] **Step 2: Implement deterministic intent rules**

Implement rule order: return-to-base when altitude descends and speed decreases; loitering when heading change is high and displacement is small; area search when heading change is moderate/high with enough points; target tracking when speed is stable and heading change is moderate; transit as fallback.

- [ ] **Step 3: Verify intent tests**

Run: `python -B -m unittest tests.test_intent_recognition -v`

Expected: PASS.

### Task 4: CLI Trajectory Intent Mode and Docs

**Files:**
- Modify: `src/uav_mission_agent/cli.py`
- Modify: `README.md`
- Create: `examples/trajectory_intent_example.json`
- Test: `tests/test_cli.py`

**Interfaces:**
- Consumes: `recognize_intent(points)`
- Produces CLI output with keys `intent`, `confidence`, `summary`, and `evidence`.

- [ ] **Step 1: Write failing CLI trajectory test**

```python
def test_trajectory_intent_mode_reads_json_file(self):
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "trajectory.json"
        path.write_text(json.dumps([
            {"timestamp": 0, "latitude": 30.0, "longitude": 120.0, "altitude": 100, "speed": 4, "heading": 0, "roll": 10, "pitch": 0, "yaw": 0},
            {"timestamp": 10, "latitude": 30.0001, "longitude": 120.0001, "altitude": 101, "speed": 4, "heading": 160, "roll": -10, "pitch": 0, "yaw": 160},
            {"timestamp": 20, "latitude": 30.0002, "longitude": 120.0001, "altitude": 101, "speed": 4, "heading": 320, "roll": 12, "pitch": 0, "yaw": 320},
        ]), encoding="utf-8")
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            main(["--trajectory-intent", str(path)])
        result = json.loads(output.getvalue())
    self.assertIn(result["intent"], {"area_search", "target_tracking", "return_to_base", "loitering", "transit"})
    self.assertIn("summary", result)
```

Run: `python -B -m unittest tests.test_cli -v`

Expected: FAIL because CLI has no `--trajectory-intent`.

- [ ] **Step 2: Implement CLI mode and example JSON**

Add `--trajectory-intent PATH`; load JSON with UTF-8; call `load_trajectory_points` and `recognize_intent`; print `result.to_dict()`.

- [ ] **Step 3: Update README**

Document optional LangGraph install, `--graph-backend langgraph`, `--trajectory-intent`, and keep DeepSeek provider examples.

- [ ] **Step 4: Verify full suite and safety scans**

Run:

```powershell
python -B -m unittest discover -s tests -v
python -B -c "import ast, pathlib; files=list(pathlib.Path('src').rglob('*.py')); [ast.parse(f.read_text(encoding='utf-8'), filename=str(f)) for f in files]; print(f'AST syntax check passed for {len(files)} files')"
git diff --check
```

Expected: all commands exit 0.
