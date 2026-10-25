# czl-web Task API

任务接口的权威说明。修改任务路由、字段或认证方式时，必须同步更新本文档。

实现位置：

- 路由：`server/index.js`
- 数据读写：`server/store.js`
- 项目关联字段：`shared/projectSchema.js`
- 数据结构约定：`data/README.md`

## 认证与环境变量

公开读取接口不需要认证。

集成写入接口使用 Bearer Token：

```text
TASKS_API_TOKEN=<long-random-token>
```

该变量只放在服务端环境或 `.env` 中，禁止提交到 Git，也不要暴露给浏览器前端。

## 任务字段

```json
{
  "id": "task_001",
  "externalId": "codex-task-001",
  "title": "完成项目工作台",
  "projectSlug": "personal-site",
  "visibility": "private",
  "status": "in_progress",
  "priority": "high",
  "dueDate": "2026-11-01",
  "tags": ["frontend", "api"],
  "notes": "内部备注",
  "createdAt": "2026-10-25T00:00:00.000Z",
  "updatedAt": "2026-10-25T00:00:00.000Z"
}
```

枚举值：

- `status`: `todo` | `in_progress` | `done`
- `priority`: `low` | `medium` | `high`
- `visibility`: `private` | `public`
- `projectSlug`: 必须对应 `data/content.json` 中已有项目的 `slug`

`externalId` 是外部系统的稳定幂等键。`notes` 和 `visibility` 只用于内部管理。

## 接口一：公开读取任务

```http
GET /api/public/tasks
```

查询参数：

| 参数 | 必填 | 说明 |
|---|---|---|
| `projectSlug` | 否 | 按项目 slug 筛选 |
| `status` | 否 | `todo`、`in_progress`、`done` 或 `all`，默认 `all` |

示例：

```http
GET /api/public/tasks?projectSlug=personal-site&status=in_progress
```

响应：

```json
{
  "success": true,
  "data": {
    "tasks": [
      {
        "id": "task_001",
        "title": "完成项目工作台",
        "projectSlug": "personal-site",
        "priority": "high",
        "status": "in_progress",
        "dueDate": "2026-11-01",
        "tags": ["frontend", "api"],
        "createdAt": "2026-10-25T00:00:00.000Z",
        "updatedAt": "2026-10-25T00:00:00.000Z"
      }
    ],
    "total": 1,
    "filters": {
      "projectSlug": "personal-site",
      "status": "in_progress"
    }
  }
}
```

安全规则：

- 只返回 `visibility=public` 的任务
- 不返回 `notes`
- 不返回 `visibility`
- 不返回 `externalId`

## 接口二：集成写入任务

```http
POST /api/integration/tasks
Authorization: Bearer <TASKS_API_TOKEN>
Content-Type: application/json
```

同一 IP 默认限制为每分钟 60 次请求。

必填字段：

| 字段 | 说明 |
|---|---|
| `externalId` | 外部系统稳定标识，最长 128；仅允许字母、数字、`.`、`_`、`:`、`-` |
| `title` | 任务标题 |

可选字段，括号内为创建任务时的默认值：

| 字段 | 默认值 |
|---|---|
| `projectSlug` | `""` |
| `status` | `todo` |
| `priority` | `medium` |
| `visibility` | `private` |
| `dueDate` | `""` |
| `tags` | `[]` |
| `notes` | `""` |

更新已有任务时，只有请求体中明确提供的字段会覆盖原值；未提供的字段保持不变。

请求示例：

```bash
curl -X POST http://127.0.0.1:8788/api/integration/tasks \
  -H "Authorization: Bearer $TASKS_API_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "externalId": "codex-task-001",
    "title": "完成任务 API 文档",
    "projectSlug": "personal-site",
    "status": "in_progress",
    "priority": "high",
    "visibility": "private",
    "dueDate": "2026-11-01",
    "tags": ["docs", "api"],
    "notes": "内部开发备注"
  }'
```

### Upsert 语义

- 相同 `externalId` 不存在：创建任务，返回 `201`
- 相同 `externalId` 已存在：更新该任务，返回 `200`
- 任务数据库中的 `id` 不会因后续更新而变化
- 每次写入都会刷新 `updatedAt`
- 局部更新不会清空未提交的 `projectSlug`、`status`、`visibility`、`dueDate`、`tags` 或 `notes`

创建成功响应：

```json
{
  "success": true,
  "message": "任务已创建",
  "data": {
    "task": {
      "id": "task_001",
      "externalId": "codex-task-001",
      "title": "完成任务 API 文档"
    },
    "created": true
  }
}
```

更新成功响应结构相同，`message` 为 `任务已更新`，`created` 为 `false`。

### 错误码

| 状态码 | 含义 |
|---|---|
| `200` | 已更新原任务 |
| `201` | 已创建新任务 |
| `400` | `externalId`、标题、项目、状态、优先级或可见性无效 |
| `401` | 缺少或错误的 Bearer Token |
| `429` | 请求频率过高 |
| `503` | 服务端未配置 `TASKS_API_TOKEN` |

## 后台管理接口

后台仍使用签名 Cookie 会话和同源校验：

```text
GET    /api/admin/tasks
GET    /api/admin/tasks/summary
POST   /api/admin/tasks
PATCH  /api/admin/tasks/:id
DELETE /api/admin/tasks/:id
```

集成写入接口用于服务端自动化，不应使用管理员 Cookie。浏览器前端也不应持有 `TASKS_API_TOKEN`。
