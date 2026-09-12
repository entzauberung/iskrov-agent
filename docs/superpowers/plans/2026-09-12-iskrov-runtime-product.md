# Iskrov Agent Runtime Product Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** 把 Iskrov Agent 的运行时边界、PRP 映射、API 产品定位和 iPad/Bridge 使用方式写成可执行的产品说明，并验证现有实现入口。

**Architecture:** Iskrov 保留完整云端控制面、本地执行面和兼容 API。PRP 只提供 Progressive 语义；Iskrov 自己拥有 provider、审批、调度、SQLite、workspace、Bridge 和恢复实现。

**Tech Stack:** Python 3.12+, FastAPI, Pydantic, SQLite/aiosqlite, httpx, pytest.

**Spec:** `README.md`, `src/prp_runtime/app.py`, `src/prp_runtime/control/progressive.py`, `src/prp_runtime/client/bridge.py`.

## Global Constraints

- 不读取或写入 `.env*`、凭据文件或受保护配置。
- 不添加全局依赖；缺少测试依赖时只记录并执行可用验证。
- 本地工具必须注册、受限、可审计；模型不能获得任意 shell 或任意主机路径。
- Iskrov 不声称是 PRP 的唯一实现。

### Task 1: 完成产品 README 和架构契约

**Files:**
- Modify: `README.md`
- Create: `docs/architecture.md`

- [ ] 写清控制面、执行面、设备接口和 PRP 映射。
- [ ] 写清 Native API 是主接口，OpenAI/Anthropic 是兼容入口。
- [ ] 写清 iPad 是远程控制端，Bridge 才是本地执行端。

### Task 2: 补充 PRP 映射与运行边界文档

**Files:**
- Create: `docs/prp-integration.md`

- [ ] 给出 PRP fact 与 Iskrov domain/runtime fact 的映射表。
- [ ] 标注哪些策略和实体属于 Iskrov 扩展。
- [ ] 写出任务生命周期和审批/Bridge 恢复路径。

### Task 3: 验证现有运行时

**Files:**
- No source changes unless validation reveals a concrete defect.

- [ ] 运行可用的静态编译检查。
- [ ] 尝试 pytest，记录缺失开发依赖而不是修改系统环境。
- [ ] 检查 FastAPI app factory 和 CLI 入口可导入。
