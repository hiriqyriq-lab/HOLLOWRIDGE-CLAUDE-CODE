#!/usr/bin/env python3
import os, json, time, uuid, logging, traceback, argparse
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

MODEL         = os.getenv("NIL_AGENCY_MODEL","claude-sonnet-4-6")
MAX_TOKENS    = int(os.getenv("NIL_AGENCY_MAX_TOKENS","8096"))
POLL_INTERVAL = int(os.getenv("NIL_AGENCY_POLL_INTERVAL","60"))

LOGS_DIR.mkdir(exist_ok=True)
logging.basicConfig(level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler(ACTIVITY_LOG), logging.StreamHandler()])
log = logging.getLogger("nil-agency")

def log_error(ctx, err):
    with open(ERROR_LOG,"a") as f:
        f.write(f"\n[{datetime.now(timezone.utc).isoformat()}] {ctx}:\n{traceback.format_exc()}\n")
    log.error(f"{ctx}: {err}")

def load_canon():
    try: return json.loads(CANON_FILE.read_text()) if CANON_FILE.exists() else {}
    except: return {}

def save_canon(canon):
    MEMORY_DIR.mkdir(exist_ok=True)
    canon["last_updated"] = datetime.now(timezone.utc).isoformat()
    CANON_FILE.write_text(json.dumps(canon, indent=2))

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

def read_queue(gh=None):
    tasks = []
    if QUEUE_FILE.exists():
        try: tasks = [t for t in json.loads(QUEUE_FILE.read_text()) if t.get("status")=="pending"]
        except: pass
    if gh and gh.available():
        try:
            seen = {t["task_id"] for t in tasks}
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
        except Exception as e: log.warning(f"GitHub close: {e}")
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
    return str(odir), summary, text

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
    args = parser.parse_args()

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
            opath, summary, text = run_agent(client, task, canon)
            complete_task(task, opath, summary, gh)
            append_session_log(task["agent"], task["task_id"], summary)
            if task["agent"]=="CONTENT_AGENT" and dist: dist(text)
        except anthropic.RateLimitError:
            log.warning("Rate limited 60s"); time.sleep(60)
        except anthropic.APIError as e:
            log_error("api",e); time.sleep(30)
        except KeyboardInterrupt:
            log.info("Shutdown."); break
        except Exception as e:
            log_error("loop",e); time.sleep(10)
        if not (args.cycles and cycle>=args.cycles):
            if args.mode=="local": time.sleep(POLL_INTERVAL)

if __name__=="__main__":
    main()
