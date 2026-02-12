# OpenAI Responses Adapter (本地兼容中间件)

一个轻量级反向代理，用于将旧版 OpenAI SDK 的 `/v1/chat/completions` 与 `/v1/completions` 请求适配到最新的 Responses API。只需改 Base URL，不改业务代码。

Lightweight reverse proxy that adapts legacy `/v1/chat/completions` and `/v1/completions` requests to the latest Responses API. Change only the Base URL, keep your business code intact.

## 核心特性 | Key Features

- 兼容旧 SDK 请求格式，自动映射到 Responses API
- 快速启动：跨系统一行命令交互式配置上游并启动
- 可扩展配置：模型映射、超时、日志级别、上游路径可配置
- 稳健转发：超时控制、错误统一返回、结构化日志
- 支持流式与非流式响应

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
## 鉴权透传 | Auth Pass-through

如果没有设置 `UPSTREAM_API_KEY`，服务会默认把下游请求中的认证头（默认 `Authorization`）透传到上游。
