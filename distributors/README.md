# NIL AGENCY — Distributors

## Metricool
1. https://app.metricool.com -> Settings -> Integrations -> API -> copy token
2. Add to .env:
   METRICOOL_TOKEN=your_token
   METRICOOL_BLOG_ID=your_blog_id
Saves CONTENT_AGENT outputs as **drafts** to Instagram + TikTok by default —
nothing goes live until reviewed in Metricool. Set
`NIL_AGENCY_AUTO_PUBLISH=1` to publish automatically instead (not
recommended until you trust the output unreviewed).
