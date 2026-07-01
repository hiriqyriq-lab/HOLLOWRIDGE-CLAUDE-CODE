"""
Phase 8: orchestrator.py had zero automated tests despite CODE_AGENT's own
standard ("tests must pass, linters must clear"). Covers the lock (Phase 3),
canon write-back (Phase 4), budget circuit breaker (Phase 5), and GitHub
Issue idempotency (Phase 7) mechanisms.
"""
import json

import pytest

import orchestrator as orch


@pytest.fixture(autouse=True)
def isolated_dirs(tmp_path, monkeypatch):
    """Redirect every module-level path constant into a throwaway tmp_path
    so tests never touch the real repo's tasks/, outputs/, or memory/."""
    monkeypatch.setattr(orch, "TASKS_DIR", tmp_path / "tasks")
    monkeypatch.setattr(orch, "COMPLETED_DIR", tmp_path / "tasks" / "completed")
    monkeypatch.setattr(orch, "OUTPUTS_DIR", tmp_path / "outputs")
    monkeypatch.setattr(orch, "MEMORY_DIR", tmp_path / "memory")
    monkeypatch.setattr(orch, "QUEUE_FILE", tmp_path / "tasks" / "queue.json")
    monkeypatch.setattr(orch, "CANON_FILE", tmp_path / "memory" / "canon.json")
    monkeypatch.setattr(orch, "SESSION_LOG", tmp_path / "memory" / "session_log.md")
    monkeypatch.setattr(orch, "LOCK_FILE", tmp_path / "tasks" / ".lock.json")
    monkeypatch.setattr(orch, "SPEND_FILE", tmp_path / "memory" / "spend.json")
    monkeypatch.setattr(orch, "HEARTBEAT_FILE", tmp_path / "memory" / "heartbeat.json")
    yield


class TestLock:
    def test_fresh_acquire(self):
        assert orch.acquire_lock("local") is True

    def test_second_holder_blocked_while_fresh(self):
        assert orch.acquire_lock("local") is True
        assert orch.acquire_lock("github-actions") is False

    def test_release_then_reacquire(self):
        orch.acquire_lock("local")
        orch.release_lock()
        assert orch.acquire_lock("github-actions") is True

    def test_stale_lock_past_ttl_is_reclaimed(self):
        orch.LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        orch.LOCK_FILE.write_text(json.dumps({
            "holder": "local:host:1", "mode": "local",
            "acquired_at": "2020-01-01T00:00:00+00:00",
        }))
        assert orch.acquire_lock("github-actions") is True

    def test_same_holder_can_reacquire_its_own_lock(self):
        orch.acquire_lock("local")
        assert orch.acquire_lock("local") is True

    def test_corrupt_lock_file_is_reclaimed(self):
        orch.LOCK_FILE.parent.mkdir(parents=True, exist_ok=True)
        orch.LOCK_FILE.write_text("not json")
        assert orch.acquire_lock("local") is True


class TestCanonWriteBack:
    @pytest.mark.parametrize("agent,section,key", [
        ("WORLDBUILDING_AGENT", "worldbuilding", "confirmed_lore"),
        ("BRAND_AGENT", "brand", "confirmed_copy"),
        ("RESEARCH_AGENT", "research", "completed_syntheses"),
        ("CONTENT_AGENT", "content", "published_topics"),
        ("MUSIC_AGENT", "music", "released_content"),
        ("CODE_AGENT", "code", "changes"),
    ])
    def test_update_canon_routes_to_correct_section(self, agent, section, key):
        task = {"task_id": "t1", "agent": agent, "instruction": "do a thing"}
        canon = orch.update_canon({}, task, "summary text", "/outputs/x")
        assert canon[section][key][0]["task_id"] == "t1"

    def test_unknown_agent_falls_back_to_content(self):
        task = {"task_id": "t2", "agent": "MYSTERY_AGENT", "instruction": "??"}
        canon = orch.update_canon({}, task, "summary", "/outputs/x")
        assert canon["content"]["published_topics"][0]["task_id"] == "t2"

    def test_save_and_load_round_trip(self):
        canon = orch.update_canon({}, {"task_id": "t3", "agent": "CONTENT_AGENT", "instruction": "x"}, "s", "/o")
        orch.save_canon(canon)
        loaded = orch.load_canon()
        assert loaded["content"]["published_topics"][0]["task_id"] == "t3"
        assert "last_updated" in loaded


class TestBudgetCircuitBreaker:
    def test_fresh_state_is_not_over_budget(self):
        spend = orch.load_spend()
        assert spend["date"] is None
        assert orch.over_budget(spend) is False

    def test_record_spend_accumulates_tokens_and_cost(self):
        spend = orch.record_spend(orch.load_spend(), "default", 1000, 1000)
        assert spend["cost_today_usd"] > 0
        assert spend["total_tokens"] == 2000

    def test_over_budget_flips_true_once_cap_exceeded(self, monkeypatch):
        monkeypatch.setattr(orch, "MAX_DAILY_SPEND_USD", 0.001)
        spend = orch.record_spend(orch.load_spend(), "default", 1_000_000, 1_000_000)
        assert orch.over_budget(spend) is True

    def test_save_load_round_trip(self):
        spend = orch.record_spend(orch.load_spend(), "default", 500, 500)
        orch.save_spend(spend)
        assert orch.load_spend()["total_tokens"] == 1000

    def test_runs_history_is_bounded(self):
        spend = orch.load_spend()
        for _ in range(250):
            spend = orch.record_spend(spend, "default", 1, 1)
        assert len(spend["runs"]) == 200


class TestGitHubIssueIdempotency:
    def test_completed_task_ids_excludes_failed_records(self):
        orch.COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
        (orch.COMPLETED_DIR / "gh-1.json").write_text("{}")
        (orch.COMPLETED_DIR / "FAILED_gh-2.json").write_text("{}")
        assert orch.completed_task_ids() == {"gh-1"}

    def test_read_queue_skips_already_completed_github_issue(self):
        orch.COMPLETED_DIR.mkdir(parents=True, exist_ok=True)
        (orch.COMPLETED_DIR / "gh-1.json").write_text("{}")

        class FakeGH:
            def available(self): return True
            def get_tasks(self):
                return [
                    {"task_id": "gh-1", "agent": "CONTENT_AGENT", "priority": 3, "created_at": "x"},
                    {"task_id": "gh-2", "agent": "CONTENT_AGENT", "priority": 3, "created_at": "x"},
                ]

        tasks = orch.read_queue(FakeGH())
        assert [t["task_id"] for t in tasks] == ["gh-2"]

    def test_write_queue_filters_out_github_ids(self):
        orch.write_queue([
            {"task_id": "local-1", "priority": 3, "created_at": "x"},
            {"task_id": "gh-99", "priority": 3, "created_at": "x"},
        ])
        saved = json.loads(orch.QUEUE_FILE.read_text())
        assert [t["task_id"] for t in saved] == ["local-1"]


class TestTaskLifecycle:
    def test_mark_running_sets_status_and_timestamp(self):
        orch.write_queue([{"task_id": "t1", "priority": 3, "created_at": "x", "status": "pending"}])
        orch.mark_running("t1")
        saved = json.loads(orch.QUEUE_FILE.read_text())
        assert saved[0]["status"] == "running"
        assert "started_at" in saved[0]

    def test_complete_task_removes_from_queue_and_writes_record(self):
        task = {"task_id": "t1", "priority": 3, "created_at": "x", "status": "pending",
                "agent": "CONTENT_AGENT", "instruction": "x"}
        orch.write_queue([task])
        orch.complete_task(task, "/outputs/x", "did the thing", gh=None)
        assert json.loads(orch.QUEUE_FILE.read_text()) == []
        record = json.loads((orch.COMPLETED_DIR / "t1.json").read_text())
        assert record["status"] == "completed"

    def test_fail_task_writes_failed_record(self):
        task = {"task_id": "t1", "priority": 3, "created_at": "x", "status": "pending"}
        orch.write_queue([task])
        orch.fail_task(task, "boom")
        record = json.loads((orch.COMPLETED_DIR / "FAILED_t1.json").read_text())
        assert record["status"] == "failed"
        assert record["error"] == "boom"


class TestSystemPrompt:
    def test_includes_established_canon_when_present(self):
        canon = {"worldbuilding": {"confirmed_lore": [{"task_id": "t1"}]}}
        prompt = orch.build_system_prompt("WORLDBUILDING_AGENT", canon)
        assert "ESTABLISHED CANON" in prompt

    def test_omits_established_canon_when_empty(self):
        prompt = orch.build_system_prompt("WORLDBUILDING_AGENT", {})
        assert "ESTABLISHED CANON" not in prompt

    def test_includes_recent_outputs_once_session_log_has_entries(self):
        orch.append_session_log("CONTENT_AGENT", "abcdef12", "did something")
        prompt = orch.build_system_prompt("CONTENT_AGENT", {})
        assert "RECENT OUTPUTS" in prompt


class TestConfigCheck:
    def test_fails_without_api_key(self, monkeypatch, capsys):
        monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
        assert orch.run_config_check() is False
        assert "[FAIL]" in capsys.readouterr().out

    def test_passes_with_api_key(self, monkeypatch, capsys):
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        assert orch.run_config_check() is True
        assert "CONFIG OK" in capsys.readouterr().out

    def test_makes_no_network_calls(self, monkeypatch):
        # anthropic.Anthropic() must never be constructed by --check
        monkeypatch.setenv("ANTHROPIC_API_KEY", "sk-ant-fake")
        monkeypatch.setattr(orch.anthropic, "Anthropic",
                             lambda *a, **k: (_ for _ in ()).throw(AssertionError("should not construct client")))
        orch.run_config_check()


class TestRateLimitBackoff:
    def test_grows_with_attempt_number(self):
        assert orch.backoff_seconds(0) < orch.backoff_seconds(1) < orch.backoff_seconds(2)

    def test_never_below_base_sleep(self):
        for attempt in range(5):
            assert orch.backoff_seconds(attempt) >= orch.RATE_LIMIT_BASE_SLEEP

    def test_capped_at_max_sleep_plus_jitter(self):
        # large attempt count should saturate at the max, not grow unbounded
        assert orch.backoff_seconds(50) <= orch.RATE_LIMIT_MAX_SLEEP * 1.25

    def test_jitter_makes_repeated_calls_vary(self):
        values = {orch.backoff_seconds(2) for _ in range(20)}
        assert len(values) > 1  # near-certain with random jitter over 20 draws


class TestHeartbeat:
    def test_no_heartbeat_yet_is_not_flagged_stale(self, capsys):
        assert orch.check_heartbeat() is True
        assert "No heartbeat recorded" in capsys.readouterr().out

    def test_fresh_heartbeat_is_ok(self, capsys):
        orch.write_heartbeat("local", 5)
        assert orch.check_heartbeat() is True
        assert "[OK]" in capsys.readouterr().out

    def test_stale_heartbeat_is_flagged(self, monkeypatch, capsys):
        import datetime as dt
        old = (dt.datetime.now(dt.timezone.utc) - dt.timedelta(seconds=orch.HEARTBEAT_STALE_SECONDS + 100)).isoformat()
        orch.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        orch.HEARTBEAT_FILE.write_text(json.dumps({"last_cycle_at": old, "mode": "local", "cycle": 3}))
        assert orch.check_heartbeat() is False
        assert "[STALE]" in capsys.readouterr().out

    def test_corrupt_heartbeat_is_flagged(self):
        orch.MEMORY_DIR.mkdir(parents=True, exist_ok=True)
        orch.HEARTBEAT_FILE.write_text("not json")
        assert orch.check_heartbeat() is False

    def test_write_heartbeat_round_trip(self):
        orch.write_heartbeat("github-actions", 7)
        hb = json.loads(orch.HEARTBEAT_FILE.read_text())
        assert hb["mode"] == "github-actions"
        assert hb["cycle"] == 7


class TestStructuredCanonAndContradictions:
    def test_extract_entities_finds_mentioned_houses(self):
        text = "House Aurveil and House Morrval clashed over the Sylvorne border."
        assert set(orch.extract_worldbuilding_entities(text)) == {"Aurveil", "Morrval", "Sylvorne"}

    def test_extract_entities_case_insensitive_and_empty_when_none(self):
        assert orch.extract_worldbuilding_entities("aurveil rises") == ["Aurveil"]
        assert orch.extract_worldbuilding_entities("no houses mentioned here") == []

    def test_first_origin_claim_recorded_without_flag(self):
        task = {"task_id": "t1", "agent": "WORLDBUILDING_AGENT", "instruction": "x"}
        canon = orch.update_worldbuilding_structure({}, task, "The founding myth of House Aurveil begins...", "/o1")
        assert canon["worldbuilding"]["houses"]["Aurveil"]["has_recorded_origin"] is True
        assert canon["worldbuilding"]["contradiction_flags"] == []

    def test_second_origin_claim_for_same_house_is_flagged(self):
        canon = {}
        t1 = {"task_id": "t1", "agent": "WORLDBUILDING_AGENT", "instruction": "x"}
        t2 = {"task_id": "t2", "agent": "WORLDBUILDING_AGENT", "instruction": "y"}
        canon = orch.update_worldbuilding_structure(canon, t1, "The founding myth of House Aurveil begins...", "/o1")
        canon = orch.update_worldbuilding_structure(canon, t2, "Another founding myth for House Aurveil claims...", "/o2")
        assert len(canon["worldbuilding"]["contradiction_flags"]) == 1
        assert canon["worldbuilding"]["contradiction_flags"][0]["house"] == "Aurveil"

    def test_mention_without_origin_claim_does_not_flag(self):
        canon = {}
        t1 = {"task_id": "t1", "agent": "WORLDBUILDING_AGENT", "instruction": "x"}
        t2 = {"task_id": "t2", "agent": "WORLDBUILDING_AGENT", "instruction": "y"}
        canon = orch.update_worldbuilding_structure(canon, t1, "The founding myth of House Aurveil begins...", "/o1")
        canon = orch.update_worldbuilding_structure(canon, t2, "House Aurveil skirmishes with House Morrval.", "/o2")
        assert canon["worldbuilding"]["contradiction_flags"] == []
        assert canon["worldbuilding"]["houses"]["Aurveil"]["mention_count"] == 2

    def test_mention_count_and_outputs_accumulate(self):
        canon = {}
        for i in range(3):
            task = {"task_id": f"t{i}", "agent": "WORLDBUILDING_AGENT", "instruction": "x"}
            canon = orch.update_worldbuilding_structure(canon, task, "House Vaelthorn does something.", f"/o{i}")
        assert canon["worldbuilding"]["houses"]["Vaelthorn"]["mention_count"] == 3
        assert len(canon["worldbuilding"]["houses"]["Vaelthorn"]["outputs"]) == 3
