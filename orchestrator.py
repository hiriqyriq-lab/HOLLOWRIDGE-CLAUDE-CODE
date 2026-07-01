#!/usr/bin/env python3
import os, json, time, uuid, socket, logging, traceback, argparse, subprocess
from datetime import datetime, timezone
from pathlib import Path
import anthropic
from dotenv import load_dotenv
load_dotenv()

BASE_DIR      = Path(__file__).parent
TASKS_DIR     = BASE_DIR/"tasks"
COMPLETED_DIR = TASKS_DIR/"completed"
OUTPUTS_DIR   = BASE_DIR/"outputs"
AGENTS_DIR    = BASE_DIR/"agents"
MEMORY_DIR    = BASE_DIR/"memory"
LOGS_DIR      = BASE_DIR/"logs"
QUEUE_FILE    = TASKS_DIR/"queue.json"
CANON_FILE    = MEMORY_DIR/"canon.json"
SESSION_LOG   = MEMORY_DIR/"session_log.md"
ERROR_LOG     = LOGS_DIR/"errors.log"
ACTIVITY_LOG  = LOGS_DIR/"activity.log"
LOCK_FILE     = TASKS_DIR/".lock.json"
SPEND_FILE    = MEMORY_DIR/"spend.json"

MODEL         = os.getenv("NIL_AGENCY_MODEL","claude-sonnet-4-6")
MAX_TOKENS    = int(os.getenv("NIL_AGENCY_MAX_TOKENS","8096"))
POLL_INTERVAL = int(os.getenv("NIL_AGENCY_POLL_INTERVAL","60"))
LOCK_TTL      = int(os.getenv("NIL_AGENCY_LOCK_TTL","900"))   # 15 min: local pm2 (thesis)
                                                                # and scheduled runs (antithesis)
                                                                # can otherwise both claim the same
                                                                # task — see PHASE_3_SYNTHESIS.md
GIT_SYNC      = os.getenv("NIL_AGENCY_GIT_SYNC","0") == "1"
MAX_DAILY_SPEND_USD = float(os.getenv("NIL_AGENCY_MAX_DAILY_SPEND_USD","15.0"))
# Approximate $/million tokens. Not exact billing — a conservative circuit
# breaker, not an invoice. See PHASE_5_SYNTHESIS.md.
PRICE_PER_MTOK = {"default": {"input": 3.0, "output": 15.0}}

LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(ACTIVITY_LOG), logging.StreamHandler()])
log = logging.getLogger("nil-agency")

def log_error(ctx, err):
    with open(ERROR_LOG,"a") as f:
        f.write(f"\n[{datetime.now(timezone.utc).isoformat()}] {ctx}:\n{traceback.format_exc()}\n")
    log.error(f"{ctx}: {err}")

# ── Cross-environment lock (Phase 3) ────────────────────────────────────────────
# Phase 1 (local/pm2) runs a perpetual loop; Phase 2 (GitHub Actions) runs on an
# hourly cron. Nothing stopped both from claiming the same queue.json entry at
# once. This lock makes "who's currently working" explicit and visible in git,
# so the two execution modes cooperate instead of racing.

def holder_id(mode: str) -> str:
    return f"{mode}:{socket.gethostname()}:{os.getpid()}"

def acquire_lock(mode: str) -> bool:
    TASKS_DIR.mkdir(exist_ok=True)
    if LOCK_FILE.exists():
        try:
            held = json.loads(LOCK_FILE.read_text())
            age = time.time() - datetime.fromisoformat(held["acquired_at"]).timestamp()
            if age < LOCK_TTL and held["holder"] != holder_id(mode):
                log.info(f"Lock held by {held['holder']} ({age:.0f}s old, ttl {LOCK_TTL}s) — yielding this cycle")
                return False
        except Exception:
            pass  # corrupt/partial lock file — treat as stale, reclaim it
    LOCK_FILE.write_text(json.dumps({
        "holder": holder_id(mode), "mode": mode,
        "acquired_at": datetime.now(timezone.utc).isoformat()
    }, indent=2))
    return True

def release_lock():
    if LOCK_FILE.exists():
        try: LOCK_FILE.unlink()
        except Exception: pass

# ── Git sync (Phase 3) ──────────────────────────────────────────────────────────
# Phase 2's GitHub Actions workflow commits outputs/memory/tasks back to the repo
# after every run, so cloud-run canon stays authoritative in git. Phase 1's local
# mode never did — a local run's canon.json and session_log.md only ever existed
# on disk, invisible to the next cloud run. --git-sync (or NIL_AGENCY_GIT_SYNC=1)
# closes that gap by giving local mode the same commit-back behavior.

def git_sync(task_id: str):
    if not GIT_SYNC:
        return
    try:
        subprocess.run(["git","add","outputs/","memory/","tasks/completed/"], cwd=BASE_DIR, check=False)
        diff = subprocess.run(["git","diff","--cached","--quiet"], cwd=BASE_DIR)
        if diff.returncode == 0:
            return  # nothing staged
        subprocess.run(["git","commit","-m",f"NIL AGENCY local sync — {task_id[:8]}"], cwd=BASE_DIR, check=False)
        subprocess.run(["git","push"], cwd=BASE_DIR, check=False)
        log.info("  git-sync: pushed local run outputs")
    except Exception as e:
        log.warning(f"git-sync skipped: {e}")

def load_canon():
    try: return json.loads(CANON_FILE.read_text()) if CANON_FILE.exists() else {}
    except: return {}

def save_canon(canon):
    MEMORY_DIR.mkdir(exist_ok=True)
    canon["last_updated"] = datetime.now(timezone.utc).isoformat()
    CANON_FILE.write_text(json.dumps(canon, indent=2))

# ── Canon write-back (Phase 4) ───────────────────────────────────────────────────
# save_canon() existed since Phase 2 but nothing ever called it: every cycle loaded
# canon.json to inject "ESTABLISHED CANON" into the system prompt, but no output
# was ever recorded back into it. confirmed_lore/confirmed_copy/etc. stayed empty
# forever — the continuity mechanism was decorative. This closes the loop.

CANON_SECTION = {
    "WORLDBUILDING_AGENT": ("worldbuilding", "confirmed_lore"),
    "BRAND_AGENT":         ("brand",         "confirmed_copy"),
    "RESEARCH_AGENT":      ("research",      "completed_syntheses"),
    "CONTENT_AGENT":       ("content",       "published_topics"),
    "MUSIC_AGENT":         ("music",         "released_content"),
    "CODE_AGENT":          ("code",          "changes"),
}

def update_canon(canon, task, summary, output_path):
    section, key = CANON_SECTION.get(task.get("agent","CONTENT_AGENT"), ("content","published_topics"))
    canon.setdefault(section, {})
    canon[section].setdefault(key, [])
    canon[section][key].append({
        "task_id": task["task_id"],
        "instruction": task["instruction"][:200],
        "summary": summary,
        "output_path": output_path,
        "recorded_at": datetime.now(timezone.utc).isoformat(),
    })
    return canon

# ── Budget circuit breaker (Phase 5) ─────────────────────────────────────────────
# Nothing in Phase 1-4 caps spend: the loop calls the Anthropic API every cycle,
# forever, with no ceiling. A stuck retry, a runaway autonomous-task cycle, or
# just running unattended for weeks turns into an unbounded bill. This adds a
# daily cap, checked *before* each API call, tracked in memory/spend.json so it
# holds across both local and cloud runs (same file, git-synced like canon).

def load_spend():
    if SPEND_FILE.exists():
        try: return json.loads(SPEND_FILE.read_text())
        except Exception: pass
    return {"date": None, "tokens_today": 0, "cost_today_usd": 0.0,
            "total_tokens": 0, "total_cost_usd": 0.0, "runs": []}

def estimate_cost_usd(model, input_tokens, output_tokens):
    rates = PRICE_PER_MTOK.get(model, PRICE_PER_MTOK["default"])
    return (input_tokens/1_000_000)*rates["input"] + (output_tokens/1_000_000)*rates["output"]

def _today():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d")

def over_budget(spend):
    if spend.get("date") != _today():
        return False  # new day, not yet spent anything
    return spend.get("cost_today_usd", 0.0) >= MAX_DAILY_SPEND_USD

def record_spend(spend, model, input_tokens, output_tokens):
    today = _today()
    if spend.get("date") != today:
        spend["date"] = today
        spend["tokens_today"] = 0
        spend["cost_today_usd"] = 0.0
    cost = estimate_cost_usd(model, input_tokens, output_tokens)
    spend["tokens_today"] += input_tokens + output_tokens
    spend["cost_today_usd"] += cost
    spend["total_tokens"] = spend.get("total_tokens", 0) + input_tokens + output_tokens
    spend["total_cost_usd"] = spend.get("total_cost_usd", 0.0) + cost
    spend.setdefault("runs", []).append({
        "at": datetime.now(timezone.utc).isoformat(),
        "input_tokens": input_tokens, "output_tokens": output_tokens,
        "cost_usd": round(cost, 6),
    })
    spend["runs"] = spend["runs"][-200:]  # bounded history
    return spend

def save_spend(spend):
    MEMORY_DIR.mkdir(exist_ok=True)
    SPEND_FILE.write_text(json.dumps(spend, indent=2))

def append_session_log(agent, task_id, summary):
    MEMORY_DIR.mkdir(exist_ok=True)
    ts = datetime.now(timezone.utc).isoformat()
    with open(SESSION_LOG,"a") as f:
        f.write(f"{ts} | {agent:25} | {task_id[:8]} | {summary[:120]}\n")

def get_recent_log(n=30):
    if not SESSION_LOG.exists(): return ""
    return "\n".join(SESSION_LOG.read_text().splitlines()[-n:])

def build_system_prompt(agent_name, canon):
    agent_file = AGENTS_DIR/f"{agent_name.lower()}.md"
    base  = agent_file.read_text() if agent_file.exists() else (BASE_DIR/"CLAUDE.md").read_text()
    ak    = agent_name.lower().replace("_agent","")
    pfx   = ""
    if canon.get(ak):
        pfx += f"\n\n## ESTABLISHED CANON\n```json\n{json.dumps(canon[ak],indent=2)}\n```\n"
    recent = get_recent_log(20)
    if recent:
        pfx += f"\n\n## RECENT OUTPUTS (avoid repetition)\n```\n{recent}\n```\n"
    return pfx + base

# Phase 7: get_tasks() re-fetches every open nil-agency-task issue each cycle.
# complete_task() writes a local COMPLETED_DIR record *before* attempting to
# close the GitHub issue, and swallows close_task() failures (network error,
# permissions, etc.) as a warning. If closing fails, the issue stays open and
# — since nothing checked local completion state — got reprocessed (and
# re-billed, and potentially re-published) on every subsequent cycle forever.

def completed_task_ids():
    if not COMPLETED_DIR.exists(): return set()
    return {p.stem for p in COMPLETED_DIR.glob("*.json") if not p.name.startswith("FAILED_")}

def read_queue(gh=None):
    tasks = []
    if QUEUE_FILE.exists():
        try: tasks = [t for t in json.loads(QUEUE_FILE.read_text()) if t.get("status")=="pending"]
        except: pass
    if gh and gh.available():
        try:
            seen = {t["task_id"] for t in tasks} | completed_task_ids()
            tasks += [t for t in gh.get_tasks() if t["task_id"] not in seen]
        except Exception as e: log.warning(f"GitHub queue: {e}")
    return sorted(tasks, key=lambda t:(t.get("priority",3),t.get("created_at","")))

def write_queue(tasks):
    local = [t for t in tasks if not t.get("task_id","").startswith("gh-")]
    TASKS_DIR.mkdir(exist_ok=True)
    QUEUE_FILE.write_text(json.dumps(local, indent=2))

def mark_running(task_id):
    if not QUEUE_FILE.exists(): return
    tasks = json.loads(QUEUE_FILE.read_text())
    for t in tasks:
        if t["task_id"]==task_id:
            t["status"]="running"; t["started_at"]=datetime.now(timezone.utc).isoformat()
    write_queue(tasks)

def complete_task(task, output_path, summary, gh=None):
    tasks = json.loads(QUEUE_FILE.read_text()) if QUEUE_FILE.exists() else []
    write_queue([t for t in tasks if t["task_id"]!=task["task_id"]])
    COMPLETED_DIR.mkdir(exist_ok=True)
    (COMPLETED_DIR/f"{task['task_id']}.json").write_text(json.dumps({
        **task,"status":"completed","completed_at":datetime.now(timezone.utc).isoformat(),
        "output_path":output_path,"summary":summary},indent=2))
    if gh and task.get("source")=="github-issue" and task.get("issue_number"):
        try: gh.close_task(task["issue_number"],summary,output_path)
        except Exception as e:
            log.warning(f"GitHub close failed for issue #{task['issue_number']}: {e} — "
                        f"local completion recorded so it won't be reprocessed, but the "
                        f"issue itself is still open on GitHub and should be closed manually")
    log.info(f"OK {task['task_id'][:8]} -> {output_path}")

def fail_task(task, error):
    tasks = json.loads(QUEUE_FILE.read_text()) if QUEUE_FILE.exists() else []
    write_queue([t for t in tasks if t["task_id"]!=task["task_id"]])
    COMPLETED_DIR.mkdir(exist_ok=True)
    (COMPLETED_DIR/f"FAILED_{task['task_id']}.json").write_text(json.dumps({
        **task,"status":"failed","failed_at":datetime.now(timezone.utc).isoformat(),"error":error},indent=2))
    log.warning(f"FAIL {task['task_id'][:8]}: {error}")

def run_agent(client, task, canon):
    agent = task.get("agent","CONTENT_AGENT")
    system = build_system_prompt(agent, canon)
    ctx = ""
    for cf in task.get("context_files",[]):
        p = Path(cf)
        if p.exists(): ctx += f"\n\n--- {p.name} ---\n{p.read_text()}"
    resp = client.messages.create(model=MODEL,max_tokens=MAX_TOKENS,system=system,
        messages=[{"role":"user","content":task["instruction"]+ctx}])
    text = resp.content[0].text
    ak   = agent.lower().replace("_agent","")
    ts   = datetime.now(timezone.utc).strftime("%Y-%m-%d_%H-%M")
    odir = OUTPUTS_DIR/ak/f"{ts}_{task['task_id'][:8]}"
    odir.mkdir(parents=True,exist_ok=True)
    ext  = "html" if "<html" in text.lower() else "md"
    (odir/f"output.{ext}").write_text(text)
    (odir/"metadata.json").write_text(json.dumps({
        "task_id":task["task_id"],"agent":agent,"model":MODEL,
        "input_tokens":resp.usage.input_tokens,"output_tokens":resp.usage.output_tokens,
        "completed_at":datetime.now(timezone.utc).isoformat()},indent=2))
    summary = text[:150].replace("\n"," ").strip()+"..."
    log.info(f"  {agent} -> {odir.name} ({resp.usage.output_tokens} tok)")
    return str(odir), summary, text, resp.usage.input_tokens, resp.usage.output_tokens

AUTONOMOUS = [
    {"agent":"WORLDBUILDING_AGENT","priority":5,"instruction":"Expand lore for one of the five Immortal Bloodline Houses (Aurveil, Morrval, Sylvorne, Vaelthorn, Veilwynn). Choose least developed. 600-word origin myth, cosmological domain, PIE root *kwel-* relationship, active conflict with another House. Hegelian dialectic throughout."},
    {"agent":"CONTENT_AGENT","priority":5,"instruction":"Write a cybercelebrities post analyzing how algorithmic recommendation flattens the distinction between sincere esoteric output and aesthetic performance of esotericism in underground music. Dense prose, no headers, single thesis close."},
    {"agent":"RESEARCH_AGENT","priority":5,"instruction":"Dialectical synthesis: hyperstition vs brand mythology. Thesis: brands as hyperstitions that make themselves real. Antithesis: hyperstition needs instability, brands need coherence. Synthesis: retrocausal brand where future product state determines present identity. Connect to TEMPORIS VESTIMENTUM genome."},
    {"agent":"BRAND_AGENT","priority":5,"instruction":"Three notarikon dissections for LOVEBACKWARD. Each letter initial for a word in a mythological phrase. Same method as GRIEVES and RELIGION. Output as formatted lore table, one dissection variant per row."},
]

def gen_auto():
    import random
    b = random.choice(AUTONOMOUS)
    return {**b,"task_id":str(uuid.uuid4()),"status":"pending",
            "context_files":[],"created_at":datetime.now(timezone.utc).isoformat(),
            "deadline":None,"source":"autonomous"}

def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cycles",type=int,default=0)
    parser.add_argument("--mode",default="local",choices=["local","github-actions"])
    parser.add_argument("--git-sync",action="store_true",help="commit+push outputs/memory after each task (local mode)")
    args = parser.parse_args()
    global GIT_SYNC
    GIT_SYNC = GIT_SYNC or args.git_sync

    api_key = os.getenv("ANTHROPIC_API_KEY")
    if not api_key:
        log.error("ANTHROPIC_API_KEY not set"); raise SystemExit(1)
    client = anthropic.Anthropic(api_key=api_key)

    gh = None
    try:
        from github_queue import GitHubQueue
        gh = GitHubQueue()
        log.info(f"GitHub queue: {'active' if gh.available() else 'no credentials'}")
    except ImportError: pass

    dist = None
    try:
        from distributors.metricool import distribute_content, MetricoolDistributor
        if MetricoolDistributor().available():
            dist = distribute_content; log.info("Metricool: active")
        else: log.info("Metricool: no token")
    except ImportError: pass

    log.info(f"NIL AGENCY v2 | mode={args.mode} | cycles={'inf' if not args.cycles else args.cycles}")

    cycle = 0
    while True:
        if args.cycles and cycle >= args.cycles:
            log.info(f"Done: {cycle} cycles"); break
        cycle += 1
        log.info(f"-- Cycle {cycle} --")
        if not acquire_lock(args.mode):
            time.sleep(min(POLL_INTERVAL, 30) if args.mode=="local" else 5)
            continue
        spend = load_spend()
        if over_budget(spend):
            log.warning(f"Daily spend cap (${MAX_DAILY_SPEND_USD:.2f}) reached "
                        f"(${spend['cost_today_usd']:.2f} spent) — skipping cycle")
            release_lock()
            if args.cycles and cycle>=args.cycles: break
            time.sleep(POLL_INTERVAL if args.mode=="local" else 5)
            continue
        try:
            canon = load_canon()
            tasks = read_queue(gh)
            if not tasks:
                auto = gen_auto()
                cur  = json.loads(QUEUE_FILE.read_text()) if QUEUE_FILE.exists() else []
                cur.append(auto); write_queue(cur); tasks=[auto]
            task = tasks[0]
            log.info(f"-> [{task['agent']}] {task['instruction'][:80]}...")
            mark_running(task["task_id"])
            opath, summary, text, in_tok, out_tok = run_agent(client, task, canon)
            save_spend(record_spend(spend, MODEL, in_tok, out_tok))
            complete_task(task, opath, summary, gh)
            append_session_log(task["agent"], task["task_id"], summary)
            save_canon(update_canon(canon, task, summary, opath))
            if task["agent"]=="CONTENT_AGENT" and dist: dist(text)
            git_sync(task["task_id"])
        except anthropic.RateLimitError:
            log.warning("Rate limited 60s"); time.sleep(60)
        except anthropic.APIError as e:
            log_error("api",e); time.sleep(30)
        except KeyboardInterrupt:
            log.info("Shutdown."); release_lock(); break
        except Exception as e:
            log_error("loop",e); time.sleep(10)
        finally:
            release_lock()
        if not (args.cycles and cycle>=args.cycles):
            if args.mode=="local": time.sleep(POLL_INTERVAL)

if __name__=="__main__":
    main()
