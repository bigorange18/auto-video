# Data conventions

Runtime content is stored in the tracked JSON files in this directory. Article
bodies are stored as Markdown under `content/posts/`, which is the only public
article source.

`articles.json` is a legacy snapshot and is not read by the server.

Project records use one canonical shape:

```json
{
  "slug": "personal-site",
  "name": "个人主页重构",
  "category": "web",
  "summary": "One-line project summary",
  "description": "Background, work, and outcome",
  "stack": ["Vue 3", "Node.js"],
  "repoUrl": "https://github.com/example/project",
  "demoUrl": "https://example.com",
  "status": "active",
  "featured": true
}
```

Allowed project categories are `web`, `ai`, `content`, `ops`, `learning`, and `other`.
Allowed project statuses are `active`, `maintained`, `planned`, and `archived`.
The server normalizes project records before reading or writing them.

Task records use a canonical project relationship and explicit visibility:

```json
{
  "id": "task_001",
  "title": "Add task API",
  "projectSlug": "personal-site",
  "visibility": "private",
  "status": "in_progress",
  "priority": "high",
  "dueDate": "2026-11-01",
  "tags": ["api"],
  "notes": "Internal notes are never exposed publicly"
}
```

Public tasks are available at:

```text
GET /api/public/tasks?projectSlug=personal-site&status=in_progress
```

The public endpoint excludes notes, visibility, and all private tasks.

Automated tools can upsert tasks through `POST /api/integration/tasks` with a
Bearer token. The `externalId` field is the stable idempotency key and is not
included in public API responses.

The authoritative task API contract is in `../docs/API.md`.
