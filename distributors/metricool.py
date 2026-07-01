import os, json, urllib.request
from datetime import datetime, timezone

BASE_URL = "https://app.metricool.com/api/v2"

# Phase 6: distribute_content() used to auto-publish every CONTENT_AGENT output
# straight to real Instagram/TikTok accounts with zero human review — an LLM's
# unreviewed text going live on a real brand's social presence on every cycle.
# Default to draft now; publishing requires an explicit opt-in.
AUTO_PUBLISH = os.getenv("NIL_AGENCY_AUTO_PUBLISH","0") == "1"

class MetricoolDistributor:
    def __init__(self):
        self.token   = os.getenv("METRICOOL_TOKEN","")
        self.blog_id = os.getenv("METRICOOL_BLOG_ID","")

    def available(self):
        return bool(self.token and self.blog_id)

    def _req(self, path, method="GET", data=None):
        body = json.dumps(data).encode() if data else None
        req  = urllib.request.Request(BASE_URL+path, data=body, method=method, headers={
            "Authorization": f"Bearer {self.token}",
            "Content-Type": "application/json"
        })
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read())

    def get_best_time(self, platform="instagram"):
        try:
            r = self._req(f"/analytics/besttime?blog_id={self.blog_id}&network={platform}")
            return r.get("best_time", datetime.now(timezone.utc).isoformat())
        except:
            return datetime.now(timezone.utc).isoformat()

    def schedule_post(self, content, platform="instagram", scheduled_at=None, draft=None):
        if not scheduled_at:
            scheduled_at = self.get_best_time(platform)
        if draft is None:
            draft = not AUTO_PUBLISH
        try:
            r = self._req("/posts","POST",{
                "blog_id": self.blog_id,
                "text": content[:2200],
                "network": platform,
                "publication_date": scheduled_at if isinstance(scheduled_at,str) else scheduled_at.isoformat(),
                "draft": draft,
            })
            return {"status":"draft" if draft else "scheduled","platform":platform,"result":r}
        except Exception as e:
            return {"status":"error","platform":platform,"error":str(e)}

def distribute_content(text, platforms=("instagram","tiktok")):
    d = MetricoolDistributor()
    if not d.available():
        print("  [METRICOOL] token not set")
        return []
    results = []
    for p in platforms:
        r = d.schedule_post(text, p)
        mode = "DRAFT (review required)" if r["status"]=="draft" else "PUBLISHED"
        print(f"  [METRICOOL] {p}: {r['status']} [{mode}]")
        results.append(r)
    if not AUTO_PUBLISH:
        print("  [METRICOOL] NIL_AGENCY_AUTO_PUBLISH not set — all posts saved as drafts, none went live")
    return results
