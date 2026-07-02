#!/usr/bin/env python3
"""
NIL AGENCY — Task Injector
Quickly add tasks to the queue from the command line.

Usage:
    python3 task.py add --agent CONTENT_AGENT --priority 1 "Write a post about..."
    python3 task.py list
    python3 task.py status
    python3 task.py clear-completed
"""

import json
import uuid
import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).parent
QUEUE_FILE = BASE_DIR / "tasks" / "queue.json"
COMPLETED_DIR = BASE_DIR / "tasks" / "completed"

AGENTS = [
    "CONTENT_AGENT",
    "BRAND_AGENT",
    "WORLDBUILDING_AGENT",
    "MUSIC_AGENT",
    "CODE_AGENT",
    "RESEARCH_AGENT",
    "ORCHESTRATOR"
]

def read_queue():
    if not QUEUE_FILE.exists():
        return []
    return json.loads(QUEUE_FILE.read_text())

def write_queue(tasks):
    QUEUE_FILE.write_text(json.dumps(tasks, indent=2))

def cmd_add(args):
    tasks = read_queue()
    task = {
        "task_id": str(uuid.uuid4()),
        "agent": args.agent,
        "priority": args.priority,
        "status": "pending",
        "instruction": args.instruction,
        "context_files": args.context or [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "deadline": None,
        "source": "manual"
    }
    tasks.append(task)
    write_queue(tasks)
    print(f"✓ Task added: {task['task_id'][:8]} [{args.agent}] P{args.priority}")

def cmd_list(args):
    tasks = read_queue()
    if not tasks:
        print("Queue empty.")
        return
    pending = [t for t in tasks if t["status"] == "pending"]
    running = [t for t in tasks if t["status"] == "running"]
    print(f"\nQueue ({len(pending)} pending, {len(running)} running):\n")
    for t in sorted(tasks, key=lambda x: (x.get("priority", 3), x.get("created_at", ""))):
        status_icon = {"pending": "○", "running": "●", "failed": "✗"}.get(t["status"], "?")
        print(f"  {status_icon} P{t['priority']} [{t['agent']:20}] {t['task_id'][:8]} | {t['instruction'][:60]}...")

def cmd_status(args):
    tasks = read_queue()
    completed = list(COMPLETED_DIR.glob("*.json")) if COMPLETED_DIR.exists() else []
    failed = list(COMPLETED_DIR.glob("FAILED_*.json")) if COMPLETED_DIR.exists() else []
    print(f"\nNIL AGENCY STATUS")
    print(f"  Pending:   {len([t for t in tasks if t['status'] == 'pending'])}")
    print(f"  Running:   {len([t for t in tasks if t['status'] == 'running'])}")
    print(f"  Completed: {len(completed) - len(failed)}")
    print(f"  Failed:    {len(failed)}")
    # Recent outputs
    outputs_dir = BASE_DIR / "outputs"
    if outputs_dir.exists():
        all_outputs = list(outputs_dir.rglob("output.*"))
        print(f"  Outputs:   {len(all_outputs)} files")

def cmd_clear(args):
    completed = list(COMPLETED_DIR.glob("[0-9]*.json")) if COMPLETED_DIR.exists() else []
    for f in completed:
        f.unlink()
    print(f"✓ Cleared {len(completed)} completed tasks")

# ── Shortcut commands ───────────────────────────────────────────────────────────

def quick_add(agent, instruction, priority=3):
    """Quick add without CLI args."""
    tasks = read_queue()
    task = {
        "task_id": str(uuid.uuid4()),
        "agent": agent,
        "priority": priority,
        "status": "pending",
        "instruction": instruction,
        "context_files": [],
        "created_at": datetime.now(timezone.utc).isoformat(),
        "deadline": None,
        "source": "quick"
    }
    tasks.append(task)
    write_queue(tasks)
    return task["task_id"]

# ── CLI ─────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="NIL AGENCY Task Manager")
    sub = parser.add_subparsers(dest="command")

    add_p = sub.add_parser("add", help="Add a task to the queue")
    add_p.add_argument("instruction", help="Task instruction")
    add_p.add_argument("--agent", default="CONTENT_AGENT", choices=AGENTS)
    add_p.add_argument("--priority", type=int, default=3, choices=[1,2,3,4,5])
    add_p.add_argument("--context", nargs="*", help="Context file paths")
    add_p.set_defaults(func=cmd_add)

    list_p = sub.add_parser("list", help="List pending tasks")
    list_p.set_defaults(func=cmd_list)

    status_p = sub.add_parser("status", help="Show agency status")
    status_p.set_defaults(func=cmd_status)

    clear_p = sub.add_parser("clear-completed", help="Clear completed task logs")
    clear_p.set_defaults(func=cmd_clear)

    args = parser.parse_args()
    if not args.command:
        parser.print_help()
        sys.exit(0)
    args.func(args)

if __name__ == "__main__":
    main()
