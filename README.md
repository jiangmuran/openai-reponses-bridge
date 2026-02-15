# OpenAI Responses Adapter (本地兼容中间件)

一个轻量级反向代理，用于将旧版 OpenAI SDK 的 `/v1/chat/completions` 与 `/v1/completions` 请求适配到最新的 Responses API。只需改 Base URL，不改业务代码。

Lightweight reverse proxy that adapts legacy `/v1/chat/completions` and `/v1/completions` requests to the latest Responses API. Change only the Base URL, keep your business code intact.

## 核心特性 | Key Features

- 兼容旧 SDK 请求格式，自动映射到 Responses API
- 快速启动：跨系统一行命令交互式配置上游并启动
- 可扩展配置：模型映射、超时、日志级别、上游路径可配置
- 稳健转发：超时控制、错误统一返回、结构化日志
- 支持流式与非流式响应
- 新接口 `/v1/responses` 直接透传到上游
- 默认从下游透传认证头，无需额外配置

## 快速开始 | Quick Start

> 先下载项目，然后执行一行命令。以下命令会提示输入上游地址，并依次校验：`URL`、`URL/responses`、`URL/v1/responses`，全部通过才会启动。

### 方式一：下载 ZIP | Download ZIP

- GitHub 页面点击 Download ZIP，解压后进入目录

### 方式二：克隆 | Clone

```bash
git clone git@github.com:jiangmuran/openai-reponses-bridge.git
cd openai-reponses-bridge
```

### macOS / Linux

```bash
bash scripts/setup.sh && bash scripts/start.sh
```

### Windows (PowerShell)

```powershell
powershell -ExecutionPolicy Bypass -File scripts\setup.ps1; powershell -ExecutionPolicy Bypass -File scripts\start.ps1
```

### 传参方式（跳过交互） | Non-interactive

```bash
bash scripts/start.sh --upstream https://api.openai.com --api-key $OPENAI_API_KEY --port 8000
```

```powershell
powershell -ExecutionPolicy Bypass -File scripts\start.ps1 -Upstream https://api.openai.com -ApiKey $env:OPENAI_API_KEY -Port 8000
```

服务启动后：

```bash
curl http://localhost:8000/healthz
```

## 工作原理 | How It Works

1. 客户端仍然调用旧接口 `/v1/chat/completions` 或 `/v1/completions`
2. 服务将请求映射为 Responses API 结构
3. 请求转发到上游 `/v1/responses`
4. 返回结果转换为旧结构或流式 chunk

当客户端直接调用 `/v1/responses` 时，服务将请求与响应直接透传，不做结构改写。

## 配置 | Configuration

复制 `.env.example` 为 `.env` 并修改：

- `UPSTREAM_BASE_URL`: 上游 API 基础地址
- `UPSTREAM_API_KEY`: 上游密钥
- `UPSTREAM_API_KEY_HEADER`: 认证头（默认 `Authorization`）
- `PASS_THROUGH_AUTH`: 未设置上游 key 时是否透传下游认证头（默认 true）
- `UPSTREAM_RESPONSES_PATH`: Responses 路径（默认 `/v1/responses`）
- `REQUEST_TIMEOUT`: 请求超时秒数
- `LOG_LEVEL`: 日志级别
- `MODEL_MAP`: 模型映射 JSON（旧模型 -> 新模型）

## 接口 | Endpoints

- `POST /v1/chat/completions`：旧版 Chat Completions 适配
- `POST /v1/completions`：旧版 Completions 适配
- `POST /v1/responses`：新接口透传
- `GET /v1/models`：模型列表透传
- `GET /healthz`：健康检查

## 兼容性 | Compatibility

- 兼容旧版 OpenAI SDK 的 `/v1/chat/completions` 与 `/v1/completions`
- 新接口 `/v1/responses` 直接透传到上游
- 支持流式输出 (SSE)
- 支持常见上游 2xx/3xx/401/403/405 响应的健康验证

## 扩展点 | Extensibility

- 自定义参数映射：`src/adapter.py`
- 自定义流式转换：`src/streaming.py`
- 日志与可观测：`src/logging_setup.py`
- 配置与鉴权：`src/config.py`

## 日志 | Logging

默认输出结构化 JSON 日志，包含上游响应码与耗时，便于接入任意日志系统。

## 示例请求 | Example Request

```bash
curl http://localhost:8000/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"gpt-3.5-turbo","messages":[{"role":"user","content":"Hello"}]}'
```

```bash
curl http://localhost:8000/v1/responses \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENAI_API_KEY" \
  -d '{"model":"gpt-4.1-mini","input":"Hello"}'
```
## 鉴权透传 | Auth Pass-through

如果没有设置 `UPSTREAM_API_KEY`，服务会默认把下游请求中的认证头（默认 `Authorization`）透传到上游。
如果你的上游使用不同的认证头（如 `api-key`），请设置 `UPSTREAM_API_KEY_HEADER`。

## 故障排查 | Troubleshooting

- 启动前校验失败：检查上游地址是否正确，是否需要代理或 VPN
- 返回 401/403：确认下游请求是否携带有效密钥，或在 `.env` 中设置 `UPSTREAM_API_KEY`
- 流式中断：检查上游是否支持 SSE，并确认网络稳定

## 运行测试 | Tests

```bash
.venv/bin/pytest
```
