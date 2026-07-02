import os, json, urllib.request
from datetime import datetime, timezone

class GitHubQueue:
    def __init__(self):
        self.token = os.getenv("GITHUB_TOKEN","")
        self.repo  = os.getenv("GITHUB_REPO","")
        self.base  = f"https://api.github.com/repos/{self.repo}"

    def available(self):
        return bool(self.token and self.repo and "/" in self.repo)

    def _req(self, path, method="GET", data=None):
        body = json.dumps(data).encode() if data else None
        req  = urllib.request.Request(self.base+path, data=body, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Accept": "application/vnd.github.v3+json",
            "Content-Type": "application/json",
            "X-GitHub-Api-Version": "2022-11-28"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())

    def get_tasks(self):
        issues = self._req("/issues?labels=nil-agency-task&state=open&per_page=20")
        tasks  = []
        for issue in issues:
            title = issue.get("title","")
            agent, instruction = "CONTENT_AGENT", title
            if title.startswith("[") and "]" in title:
                end = title.index("]")
                agent, instruction = title[1:end].strip(), title[end+1:].strip()
            priority = 3
            for lbl in issue.get("labels",[]):
                if lbl.get("name","").startswith("priority-"):
                    try: priority = int(lbl["name"].split("-")[1])
                    except: pass
            tasks.append({
                "task_id": f"gh-{issue['number']}", "agent": agent,
                "priority": priority, "status": "pending",
                "instruction": instruction, "context_files": [],
                "created_at": issue["created_at"], "deadline": None,
                "source": "github-issue", "issue_number": issue["number"]
            })
        return tasks

    def close_task(self, number, summary, output_path):
        ts   = datetime.now(timezone.utc).isoformat()
        body = f"COMPLETE\n\nSummary: {summary}\nOutput: {output_path}\n{ts}"
        self._req(f"/issues/{number}/comments","POST",{"body":body})
        self._req(f"/issues/{number}","PATCH",{"state":"closed"})
