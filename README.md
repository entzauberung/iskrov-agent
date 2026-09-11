# Iskrov Agent

> 云端推理，本地执行。

Iskrov Agent 是一个独立的云端控制、本地执行 Agent 产品。它把模型推理、规划、审批、证据、预算和调度集中在控制面，把本机收敛为一个轻量、封闭、可授权的工具执行面。

```text
云端：模型 · 规划 · 审批 · 证据 · 调度
本机：受限工具 · 工作区操作 · 结果回传
```

当前版本：`0.0.1` · Python `3.12+` · AGPL-3.0-only · 单实例 SQLite · 无 Docker

## 产品定位

Iskrov Agent 不是聊天 UI，也不是一个要求每台机器下载完整 CLI 的本地 Agent。它适合这样的任务：模型需要检查代码、提出修改、运行受限验证，并且整个过程必须有边界、有证据、可恢复。

云端控制面负责“决定做什么以及是否允许做”；本地执行面负责“在授权工作区内执行什么以及返回什么”。两者通过受限的工具调用、claim、lease 和结果提交连接。

## 解决的问题

普通模型 API 解决的是：

```text
发送消息 -> 获得回答
```

工程 Agent 还必须回答：

- 这次操作是否被允许
- 哪些证据证明任务完成
- 写入前是否需要审批
- 失败后应该重试、切换、修订还是停止
- 服务或客户端重启后能否安全恢复

Iskrov Agent 面向的是这条完整执行链，而不是单纯的文本生成。

## 架构

### Cloud Control Plane

- 接收任务并选择执行策略
- 调用配置好的模型 provider
- 协调 Planner、Worker、Analyzer 和 Verifier
- 管理预算、审批、事件、恢复和最终状态
- 在需要时向本地 Bridge 派发工具调用

### Local Execution Plane

- 不运行模型
- 不拥有云端规划或审批权限
- 只执行注册且边界受限的本地工具
- 不需要下载完整的 Agent CLI
- 支持断线后的 claim 恢复和幂等结果回传

## 工具边界

Agent 只能使用注册工具：

`list_files` · `read_file` · `search_text` · `apply_patch` · `run_targeted_test` · `get_diff` · `get_status`

写操作经过 Policy 和 Approval。测试使用预注册的结构化命令。模型不能获得任意 shell、任意主机路径、未注册网络或自行提升权限。

## 执行策略

| 策略 | 适用场景 | 行为 |
|---|---|---|
| `DIRECT` | 简单任务 | 一个 WorkUnit、一次 Attempt、一次验证 |
| `CASCADE` | 多模型回退 | 仅在可重试失败时进入下一个 profile |
| `PLANNED` | 有依赖的任务图 | Planner 提案 DAG，Worker 按依赖执行 |
| `PROGRESSIVE` | 需要证据和修订 | 执行、合并、验证、复用和有限 revision |

`PROGRESSIVE` 是 Iskrov Agent 支持的一种执行策略。它不是产品名称，也不是本仓库唯一的理论身份。渐进式推理的独立协议研究位于 [Progressive Reasoning Protocol](https://github.com/entzauberung/prp)。

## 安全与隔离

- 默认本地路径边界是 `HOST`，它不是操作系统级沙箱
- 选择 `SANDBOXED` 时必须有真实 Linux `bubblewrap`
- 顺序 `LOCAL + HOST + DIRECT` 可以在已授权工作区内就地执行
- 并行、`PLANNED` 和 `PROGRESSIVE` 使用隔离 Slot 与 ChangeSet
- 进程信封限制并发、attempt、token、槽位和拷贝容量
- 资源耗尽返回结构化错误，不静默切换位置、策略或隔离模式

## 快速开始

安装：

```bash
uv pip install .
```

配置一个 OpenAI-compatible Worker profile：

```bash
export PRP_WORKER_PROFILE='{"alias":"worker","provider":"openai_compatible","model":"your-model","role":"WORKER","base_url":"https://models.example/v1","context_window_tokens":32000,"max_output_tokens":4000}'
```

启动本地单进程任务：

```bash
prp local run "summarise this repository" --workspace .
```

本地执行不依赖 HTTP 服务。需要接口时，可以显式启动默认只绑定回环地址的服务：

```bash
prp serve
```

如果任务因审批暂停：

```bash
prp local approve <request_id> --workspace .
prp local deny <request_id> --workspace . --reason "not allowed"
```

## 项目边界

Iskrov Agent 是单实例参考产品，不承诺生产 SLA。当前不提供多租户计费、SSO、分布式队列、Kubernetes，也不声称完整兼容 Codex、Claude Code、MCP 或 A2A。

它不是任意 shell，也不是模型训练平台。模型质量取决于配置的 provider；Agent 负责把执行过程置于明确的工具、策略、证据和预算边界内。

## 与 PRP 的关系

这是两个独立产品：

- **PRP**：Apache-2.0 的协议研究项目，定义渐进式推理的事实、状态机和修订法则。
- **Iskrov Agent**：AGPL-3.0-only 的 Agent 产品，使用这些概念实现云端控制与本地工具执行。

PRP 可以被其他 runtime 实现，Iskrov Agent 也不等于 PRP 的唯一实现。两个项目可以独立演进、独立发布、独立接受贡献。

## 开源与许可证

Iskrov Agent 采用 [GNU Affero General Public License v3.0-only](LICENSE)。如果通过网络向用户提供修改后的版本，需要遵守 AGPL-3.0-only 的对应源码提供义务。详见 [NOTICE](NOTICE) 和 [TRADEMARKS.md](TRADEMARKS.md)。
