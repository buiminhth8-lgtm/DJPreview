"""T11：LLM Call Logger 单元测试。"""

import json

from packages.llm.call_logger import LLMCallLogger


def _log_args(**overrides):
    args = {
        "project_id": None,
        "task_name": "generate_music_spec",
        "provider": "deepseek",
        "model": "deepseek-chat",
        "request": {"messages": [{"role": "user", "content": "测试"}]},
    }
    args.update(overrides)
    return args


def test_log_with_project_id(tmp_path):
    logger = LLMCallLogger(base_dir=tmp_path)
    path = logger.log_call(**_log_args(project_id="song-123"))
    assert path is not None
    assert path.exists()
    assert path.parent.name == "llm_calls"
    assert path.parent.parent.name == "song-123"
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["project_id"] == "song-123"
    assert data["provider"] == "deepseek"
    assert data["task_name"] == "generate_music_spec"


def test_log_without_project_id_goes_to_global_dir(tmp_path):
    base = tmp_path / "data" / "projects"
    logger = LLMCallLogger(base_dir=base)
    path = logger.log_call(**_log_args())
    assert path is not None
    assert path.parent.name == "llm_calls"
    assert path.parent.parent == tmp_path / "data"
    assert path.parent.parent.name == "data"


def test_log_never_contains_authorization_or_api_key(tmp_path):
    logger = LLMCallLogger(base_dir=tmp_path)
    path = logger.log_call(
        **_log_args(
            request={"api_key": "sk-secret", "authorization": "Bearer sk-secret", "messages": []},
            parsed={"ok": True},
        )
    )
    assert path is not None
    content = path.read_text(encoding="utf-8")
    assert "sk-secret" not in content
    assert "Authorization" not in content
    json.loads(content)


def test_log_failure_does_not_break_main_flow(tmp_path):
    blocked = tmp_path / "blocked"
    blocked.write_text("i am a file", encoding="utf-8")
    logger = LLMCallLogger(base_dir=blocked)
    assert logger.log_call(**_log_args(project_id="song")) is None
