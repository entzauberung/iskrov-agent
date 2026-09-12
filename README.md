# Iskrov Agent

> 云端控制，本地执行。

Iskrov Agent 是一个单实例 Agent 运行时：模型规划、策略、审批、预算、证据、调度和恢复集中在控制面；本机只保留注册、受限、可授权的工具执行面。

如果你需要研究“如何基于证据推进推理”的协议，请使用 [Progressive Reasoning Protocol](https://github.com/entzauberung/prp)。如果你需要可以接入模型、工作区和本地设备的 Agent 服务，请使用本仓库。

```text
iPad / Web / CLI / 兼容接口
              |
        Native Agent API
              |
云端：模型 · 规划 · 策略 · 审批 · 证据 · 预算 · 调度
              |
      CLOUD 执行或 Bridge claim/lease
              |
      授权工作区中的注册工具
```

当前版本：`0.1.1` · Python `3.12+` · AGPL-3.0-only · SQLite 单实例参考部署。

## 产品定位

Iskrov Agent 改变的是 Agent 的使用方式：iPad 或其他客户端可以作为远程控制端，创建任务、查看事件、检查证据、处理审批、取消运行；模型推理和本地工作区操作由服务端与 Bridge 协同完成。

设备端不需要运行完整 Agent，不接触 Provider 凭据，也不直接获得任意主机路径。需要访问本机工作区时，服务端为具体的 tool call 选择已注册 Bridge，Bridge 领取 claim、在边界内执行并以幂等方式提交结果。

## 核心能力

- `DIRECT`、`CASCADE`、`PLANNED`、`PROGRESSIVE` 四种运行策略；
- OpenAI-compatible、OpenAI Responses 和 Anthropic Messages Provider 适配器；
- Native Session、Run、Event、Tool Call、Approval、Cancel 和 Recovery；
- `list_files`、`read_file`、`search_text`、`apply_patch`、`run_targeted_test`、`get_diff`、`get_status` 等注册工具；
- owner-scoped Workspace、Snapshot、ChangeSet、Merge、Budget 和 Evidence；
- 无模型本地 Bridge，支持 claim、lease、heartbeat、断线恢复和幂等回传；
- OpenAI Chat/Responses 与 Anthropic Messages 的受限兼容入口。

## 控制面和执行面

### 云端控制面

- 接收任务并选择模型、策略和执行位置；
- 调用 Provider，协调 Planner、Worker、Analyzer 和 Verifier；
- 管理预算、审批、事件、证据、修订和最终状态；
- 在需要时创建 Bridge tool call，并负责 claim/lease 的生命周期。

### 本地执行面

- 不运行模型，不拥有云端规划或审批权限；
- 只执行注册且边界受限的工具；
- 在授权工作区中读取、修改和验证；
- 通过游标、heartbeat 和幂等结果支持断线恢复。

## 安全边界

模型不能获得任意 shell、任意主机路径、未注册网络或权限提升。写操作经过 Policy 和 Approval；测试使用预注册的结构化命令。

`HOST` 是路径边界，不是操作系统沙箱；`SANDBOXED` 需要真实 Linux `bubblewrap`。当前产品是单实例参考实现，不提供生产 SLA、分布式队列、SSO、计费或 Kubernetes。

## 与 PRP 的关系

PRP 定义证据门控的 Progressive revision：是否允许打开下一版执行图。Iskrov Agent 在此基础上实现 Provider、调度、审批、SQLite、Workspace、Merge、Bridge 和 Recovery。

因此两者可以独立发布：PRP 是协议研究仓，Iskrov 是使用该语义的 Agent 产品。安装 Iskrov 不等于安装 PRP 研究仓。

## 安装

```bash
python -m pip install .
```

开发环境：

```bash
python -m pip install -e '.[dev]'
pytest -q
ruff check .
mypy
```

要求 Python 3.12 或更高版本。

## 配置 Provider

下面示例配置一个 OpenAI-compatible Worker profile。请替换占位值，不要把凭据或本地配置文件提交到仓库。

```bash
export PRP_WORKER_PROFILE='{"alias":"worker","provider":"openai_compatible","model":"your-model","role":"WORKER","base_url":"https://models.example/v1","context_window_tokens":32000,"max_output_tokens":4000}'
```

## 本地运行

本地任务不要求 HTTP 服务：

```bash
prp local run "summarise this repository" --workspace .
```

需要接口时启动默认只绑定回环地址的服务：

```bash
prp serve
```

审批暂停的本地任务：

```bash
prp local approve <request_id> --workspace .
prp local deny <request_id> --workspace . --reason "not allowed"
```

安装后的命令 `prp` 和 `prp-bridge` 为历史兼容名称；包身份是 `iskrov-agent`，产品身份是 Iskrov Agent。

## API

Native Agent API 是产品主接口，覆盖 Session、Run、Event、Tool Call、Approval、Bridge Client 和 Cancel。OpenAI Chat/Responses 与 Anthropic Messages 入口只接受声明的兼容子集，并映射到同一个控制器。

服务提供 `/health` 和 `/ready` 检查。精确请求和响应契约见 [`src/prp_runtime/api/`](src/prp_runtime/api/)。

## 项目状态

`0.1.1` 是单实例参考产品版本，不声称完整兼容 Codex、Claude Code、MCP 或 A2A，也不声称 benchmark 优势或模型质量优势。架构和 PRP 映射见 [`docs/architecture.md`](docs/architecture.md) 与 [`docs/prp-integration.md`](docs/prp-integration.md)。

## 英文说明

英文完整说明见 [README.en.md](README.en.md)。

## 许可证

Iskrov Agent 使用 [AGPL-3.0-only](LICENSE) 许可证。通过网络提供修改版本时，需要遵守对应源码提供义务。品牌边界见 [NOTICE](NOTICE) 和 [TRADEMARKS.md](TRADEMARKS.md)。
