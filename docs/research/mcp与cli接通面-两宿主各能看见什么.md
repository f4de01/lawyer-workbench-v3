# 以 MCP 或 CLI 接通可视化插件：两宿主各能看见什么、代价各多少

> **写于** 2026-09-13，对应 issue #138（`wayfinder:research`），挂在地图 #122 下，阻塞 #127。**本票只查事实、不选型。**
> **每条结论标性质**：**［源码事实］**＝本机已安装的官方源码或二进制字符串、官方文档、官方规范里明确写着；**［本机实测］**＝这台机今天跑出来的；**［设计推断］**＝从上述推出、没有一处明说；**［须实测］**＝现在答不了；**［查不到］**＝找过、没找着，不补脑。
> **本机基线**（2026-09-13）：Windows 11 Pro 26200；`claude` 2.1.270；`codex-cli` 0.154.0（源码对照 `openai/codex` 标签 `rust-v0.154.0`）；Codex 桌面应用 `OpenAI.Codex` 26.908.4834.0（`owl-app.ini` 记 `AppVersion=26.908.40834`），其渲染层从包内 `app/resources/app.asar`（324,915,597 字节）抽字符串；`python` 3.14.2 与 `python3.9` 3.9.25（uv）；Codex 自带插件 `visualize@openai-bundled` 1.0.37、`codex-app-tools` 0.1.4。
> **红线**：本文不含任何案件材料、不含案件路径。实测全在会话 scratchpad 的临时目录里做（`os.mkdir`，装完即弃）；实测脚本在 `docs/research/mcp与cli接通面/`。
> **不重查、只引用**：#126 `docs/research/可视化形态四条-事实与代价.md`（分支 `research/可视化形态四条`）、#132 `docs/research/assets分发实测与visualize在TUI的退化.md`（分支 `research/assets分发与visualize退化`）。

---

## 0. 结论速览

| 问题 | 答案 | 性质 |
| --- | --- | --- |
| MCP 工具结果里的 `image` 块，Codex 桌面应用给不给人看 | **给。** 桌面渲染层有一段专门的内容块渲染器：`image` 渲成 `<img>`（最高 12rem，可点开）、alt 文案 "Image returned by tool"；`audio` 渲成 `<audio controls>`；`text` 装进标题为 "plaintext" 的代码式容器（**不当 Markdown 渲**）；`resource_link` 只显示一行 "Read {name}"；`resource` 显示 URI / MIME type / Annotations / Content 四行，Content 放 `<pre>`（**HTML 不渲染**）。整个工具调用默认折叠成一行 `{tool}`，另有 "Show raw tool call output" 开关 | 源码事实（app.asar 字符串）；真看一眼仍是须实测 |
| 同一块在 Codex 终端 TUI 里 | 只打一行 `<image content>` / `tool result (image output)`；`resource` 打 `embedded resource: {uri}`，`resource_link` 打 `link: {uri}` | 源码事实（`tui/src/history_cell/mcp_result.rs`） |
| 同一块在 Claude Code 终端里 | 终端显示 `[Image]` 占位；模型侧收到多模态图片（改写成 Anthropic API 的 `image/base64`）；`resource` 改写成一行 `[Resource at {uri}] {text}`，`resource_link` 改写成 `[Resource link: {name}] {uri}` | 源码事实 + 本机实测（子探针） |
| 两宿主的模型侧收不收 image | **都收**：Codex `image` → `InputImage`（data URL，detail 默认 High）；Claude Code → `image/base64`，MIME 只认 jpeg/png/gif/webp，SVG 之类落盘换成路径 | 源码事实 + 本机实测 |
| MCP 结果上限 | Codex：模型侧按 `truncation_policy`（内置模型 10,000 token）截 text、image 不计入；给客户端的事件副本超 1 MiB 折成文本预览。本机实测 60,000 字符 text 块整段到达模型（input_tokens +2.5 万）；400,000 字符那次 input_tokens 只 +400（本机开着 `context_management` 未转正特性，归因不了）。Claude Code：默认 25,000 token（`MAX_MCP_OUTPUT_TOKENS`），超 10,000 警告，超限**存盘换路径**而不是拒绝 | 源码事实 + 本机实测 |
| stdio server 谁拉起、何时杀 | 两宿主都在**会话开始时全部拉起**（不懒加载）；Codex 每个线程一套，退出时硬杀（Windows Job Object `KILL_ON_JOB_CLOSE`；本机实测 server 日志没有 stdin 关闭那一行）；Claude Code 正常退出关管道（server 收到 stdin EOF）。宿主被强杀：Codex Windows 靠 Job 句柄带走，macOS 无 PDEATHSIG；Claude Code 查不到 | 源码事实 + 本机实测 / 须实测 |
| 启动与工具超时默认 | Codex 源码 30 s / 300 s，**官方文档写 10 s / 60 s，两处不一致**；Claude Code `MCP_TIMEOUT` 30,000 ms、`MCP_TOOL_TIMEOUT` 默认约 28 小时、stdio 空闲超时 30 分钟 | 源码事实 |
| python stdio server 冷启动 | Popen 到 `initialize` 应答：3.14 为 20–24 ms，3.9 为 33–48 ms；Claude Code 从拉起到 python 进脚本 0.43 s | 本机实测 |
| 登记处 | Codex：`~/.codex/config.toml [mcp_servers.<n>]`，或插件 `.codex-plugin/plugin.json` 的 `mcpServers` → `.mcp.json`（字段与 config.toml 同名），或 skill 的 `agents/openai.yaml` `dependencies.tools[type=mcp]`（宿主提示安装、写进全局 config.toml）。Claude Code：`.mcp.json`、`~/.claude.json`、插件 `.claude-plugin/plugin.json` 的 `mcpServers`（`${CLAUDE_PLUGIN_ROOT}`）。**skills.sh 一个字节都不带**（`skills` 1.5.26 的 `cli.mjs` 无 `mcpServers`）；**离线兜底包也不带**（`pack-offline.py` 只拷 skill 目录） | 源码事实 |
| CLI stdout 谁看见 | 两宿主 stdout 都先进模型；Codex 桌面在 "STEPS_COMMANDS" 明细里流式显示命令输出（超长加 `[output truncated]`），TUI 显示折叠的命令格；Claude Code 终端显示工具结果、`Ctrl+O` 展开 | 源码事实 |
| 模型转述的 Markdown 表格 / Mermaid | Codex 桌面：`marked` 开着 `gfm:true`、表格渲成 `<table>` 且有 "Table preview" 弹窗，Mermaid 围栏块渲成图（`mermaidDiagram.preview/expand/download`）。Codex TUI 本机实测：表格渲成对齐文本加 `━━━` 分隔线，Mermaid 块**原样打成一行文本**。Claude Code 终端：表格渲成框线（CHANGELOG），Mermaid 无渲染 | 源码事实 + 本机实测 |
| CLI 写出的 PNG 能不能给人看 | Codex 桌面：**查不到**一条"把本地图片文件显示给用户"的通道（`view_image` 是模型输入；`visualize{}` 只认 HTML 片段）；Claude Code 终端不渲染图像（#126 A.4） | 查不到 / 源码事实 |
| Codex 桌面有没有律师可用的终端 | **有。** 官方文档 "Integrated terminal"：每个会话自带一个终端，右上角图标或 `` Ctrl+` ``；Windows 可选 PowerShell / CMD / Git Bash / WSL；渲染层带 `xterm` + `node-pty`。交互式 TUI 查看器能不能在里面跑：须实测 | 源码事实 / 须实测 |
| `visualize` 内联通道除 HTML 还认什么 | 桌面那套提示词全文抄在 3.4：表格走普通 Markdown，小型静态图走 Mermaid 围栏块，交互与动态走 `visualize{"path":…}` 的 HTML 片段；`sandbox:` 链接是下载通道 | 源码事实 |
| tkinter | 本机两版 python 都带 Tk 8.6；窗口进程在父进程退出后活着、窗口关即退。律师那台 Apple CLT 3.9.6 带不带 `_tkinter`、Tk 哪版：**查不到**，须实测；python.org 官方原文 "do not use the Apple-supplied Pythons" | 本机实测 / 查不到 |
| pywebview / wry | pywebview 要 `pip install` 加 pyobjc（mac）或 pythonnet + .NET + WebView2（Win），与零第三方依赖冲突；wry 是 Rust 库、无预编译产物 | 源码事实 |
| ADR-0011「不设 MCP server」的前提 | 当年的理由是"两个 CLI 都不渲染、落盘文件是唯一可见通道"；今天 Codex 桌面应用会渲 MCP 结果里的 image，也会渲回复里的 Mermaid 与表格。前提变了一半，裁定要不要改归 #127 | 源码事实 + 设计推断 |

---

## 1. MCP 交出去的东西，宿主怎么呈现

MCP 规范 2026-07-28 的工具结果内容块只有五种：`text`、`image`、`audio`、`resource_link`、`resource`（#126 D.5）。下面按宿主逐类记。

### 1.1 Codex：模型侧收到什么

`codex-rs/protocol/src/models.rs` 的 `CallToolResult::as_function_call_output_payload()` 与 `convert_mcp_content_to_items()`：**［源码事实］**

| 块 | 给模型的形态 |
| --- | --- |
| `text` | `InputText`（`_meta["codex/encryptedContent"]` 为 true 时转 `EncryptedContent`） |
| `image` | `InputImage { image_url: "data:{mimeType};base64,{data}", detail }`，detail 取 `_meta["codex/imageDetail"]`，缺省 `High`。**进多模态输入，不丢** |
| `audio` | `InputAudio`（data URL） |
| `resource` / `resource_link` / 未知 | 落进 `#[serde(other)] Unknown`，**整块 JSON 序列化成文本**给模型 |

同函数还有一条：`structured_content` 非空且没有 EncryptedContent 时，**整个 payload 改成序列化后的 structuredContent，content 块不发**（单元测试 `preserves_structured_mcp_content` 就是这么断言的）。**［源码事实］**

**但本机实测与这条源码读法对不上**：探针 server 同时返回四个内容块与 `structuredContent: {"probe":"ok"}`，`codex exec` 里模型把 text 块原文、`resource_link` 的 uri、内嵌资源的 `<b>PROBE_HTML_OK</b>` 全部逐字复述，还说"我看见了图片"；带与不带 structuredContent 两组（text 块各 60,000 字符）的 `input_tokens` 只差 5（84,833 对 84,838），模型两次都描述出全部四块。**［本机实测］** 哪一层让 content 绕过了那段代码（`gpt-6-astra` 走的序列化路径、code-mode 宿主，或别的），本票没有追到；**「structuredContent 会不会吞掉 content」在 Codex 上按实测是不会，按源码是会**，留作**［须实测］**（换模型、关掉本机开着的 `context_management` 未转正特性各跑一次）。

TUI 展示：`tui/src/history_cell/mcp_result.rs` 把 `image` 打成 `<image content>`、`audio` 打成 `<audio content>`、`resource` 打成 `embedded resource: {uri}`、`resource_link` 打成 `link: {uri}`；`mcp.rs` 的 `McpImageOutputCell` 只出一行 `tool result (image output)`。**TUI 不渲染图片。［源码事实］**

### 1.2 Codex 桌面应用：给人看什么

桌面渲染层（`app.asar`）里有一段按 `block.type` 分支的 React 组件，i18n 消息 id 全在 `codex.mcpTool.*` 下（共 117 条）。逐类：**［源码事实］**

| 块 | 桌面怎么画 |
| --- | --- |
| `image` | `<img className="max-h-48 w-max max-w-full … object-contain" src="data:{mimeType};base64,{data}">`，alt 为 `codex.mcpTool.contentBlock.imageAlt` = "Image returned by tool"；外面套一个可点开的查看器（`getItems` → 灯箱） |
| `audio` | `<audio controls preload="metadata" src="data:…">` |
| `text` | 一个带 sticky 标题 "plaintext"（`codex.mcpTool.textBlock.plaintextTitle`）的容器，正文在 `<pre class="whitespace-pre-wrap …">` 里，容器 `max-h-48 overflow-y-auto`。**text 块不当 Markdown 渲**（表格、Mermaid 在这里都是原文） |
| `resource_link` | 一行 `codex.mcpTool.resourceLink.reading` = "Read {resourceLinkName}"（取 title ?? name ?? uri），**没有打开动作** |
| `resource`（embedded） | 四行：URI、MIME type、Annotations、Content；Content 是 `<pre class="max-h-48 overflow-auto …">`。**`text/html` 资源不会被渲成 HTML** |
| 未知 | JSON 美化后放 `<pre>` |

块上的 `annotations`（audience / priority / lastModified）以一行 "Annotations: …" 附在块下；进桌面前还有一道 `select(content, fits(annotations))` 的过滤，按 audience 挑给人看的块。**［源码事实］**（过滤规则的具体取值没有抽到，**［查不到］**）

工具调用整体：默认折叠成 `codex.mcpTool.collapsedLabel.toolOnly` = "{tool}" 一行；工具栏有 "Show raw tool call output"（弹出 "Raw {server}.{tool} tool call output"）；无内容时 "Tool returned no content"。**［源码事实］** 折叠是默认态、要点开才见图，这一条是从消息 id 的命名推出的，**［设计推断］**。

**MCP App（SEP-1865）那条通道桌面已经有壳**：`codex.mcpTool.mcpAppIframeTitle`、`mcpAppLoading`、`mcpAppTooLarge`（"Failed to load MCP app: HTML exceeds the maximum supported size."）、`openApp` / `openAppInTab`，以及 `ui/update-model-context`、`ui/download-file` 的 RPC 处理；但本机 `codex features list` 里 `enable_mcp_apps` 仍是 `under development / false`（#126 A.1 不变）。**［源码事实］**

以上全部是从渲染层代码抽的字符串，**没有亲眼在桌面应用里看过一次 MCP 图片**。**［须实测］**：把 `probe_server.py` 登进 `~/.codex/config.toml`、在桌面应用里调一次 `probe_view`，看折叠态与展开态。

### 1.3 Claude Code 终端

（本节来自子探针在本机的实测与 `claude.exe` 字符串、`code.claude.com/docs` 原文。）

- **`image` 块 → 模型多模态输入**：`stream-json --verbose` 里 `tool_result.content` 的形状是 `[{type:"text",…},{type:"image",source:{type:"base64",media_type:"image/png",data:…}}]`，即 MCP 的 `{data,mimeType}` 被改写成 Anthropic API 的 `image/base64`；模型两次都答"收到一张 1×1 PNG"。**［本机实测］** 支持的 MIME 集合 `image/jpeg`、`image/png`、`image/gif`、`image/webp`；不支持的（如 SVG）**落盘并在结果里换成路径**（CHANGELOG 2.1.144；模板 `Binary content ({mime}, {size}) saved to {path}`）。**［源码事实］**
- **终端给人看什么**：MCP 结果渲染函数遇 `image` 块显示 `"[Image]"`；空结果 `"(No content)"`；超阈值在上方加一行 "Large MCP response (~N tokens), this can fill up context quickly"。MCP 调用默认折叠成 "Called {server} N times" / "Queried {server}" 一行，`Ctrl+O` 展开。**［源码事实］**
- **`resource` / `resource_link`**：有 `resource.text` 的改写成一行 `[Resource at {uri}] {text}`；有 `resource.blob` 的走上面的二进制分支；`resource_link` 改写成 `[Resource link: {name}] {uri} ({description})`；其它未知类型改写成 `[{type}]`。stream-json 另有 `mcp_meta.resource_links` 字段把原始 `resource_link` 块（最多 50 条、64 KiB）交给宿主 "so a host renders the files without parsing that line"。**［源码事实］** `audio` 块没找到专门处理，按兜底变成 `[audio]`，**［设计推断］**。
- **MCP 资源的 `@server:uri` 引用**（文档原文）："Resources are automatically fetched and included as attachments when referenced"，另有内置 `ListMcpResourcesTool` / `ReadMcpResourceTool`。**［源码事实］**
- **终端不渲染图像、不渲染 HTML**：#126 A.4 已坐实，不重查。

### 1.4 字节 / 字符上限

**Codex**［源码事实］
- 模型侧：`core/src/tools/handlers/mcp.rs` 取工具自己的 `output_token_limit`，否则用模型的 `truncation_policy`；内置模型 `models.json` 里全部是 `{"mode":"tokens","limit":10000}`（gpt-5.2 为 bytes 10000），再加 20% 序列化余量；截断只切 text 段，**`InputImage` 原样保留不计入预算**，`InputAudio` 按估算 token 计、超了丢。全局可用 `tool_output_token_limit`，每工具可用 `[mcp_servers.<n>.tools.<tool>] output_token_limit`。
- 给客户端（app-server 事件）：`MCP_TOOL_CALL_EVENT_RESULT_MAX_BYTES` = 1 MiB，超过时事件副本折成一个 text 预览块，模型侧不受影响。
- shell 输出作对照：`DEFAULT_MAX_OUTPUT_TOKENS = 10_000`、`UNIFIED_EXEC_OUTPUT_MAX_BYTES = 1 MiB`。
- **本机实测**：60,000 字符 text 块，模型报开头结尾各 20 个 X、"没有别的字符"，`input_tokens` 比小结果那次高约 2.5 万，**整段到达、没截**；400,000 字符那次 `input_tokens` 只比基线高 400，模型仍说"没有截断标记"。两次都不能对上"10,000 token 截断"这条源码规则；本机开着 `context_management`（`under development`）特性，是不是它在背后收拾，**［须实测］**（关掉再跑）。
- `mcp_2026_07_28` 特性旗：MCP 协议版本 2026-07-28 的协商开关（本机 `under development / false`，走 2025-06-18），与大小无关。

**Claude Code**［源码事实，文档原文］
- "Output warning threshold: Claude Code displays a warning when any MCP tool output exceeds 10,000 tokens"；"Default limit: the default maximum is 25,000 tokens"（`MAX_MCP_OUTPUT_TOKENS`）；"Over the limit: when a result with no image content exceeds the limit, Claude Code saves it to a file and replaces it in the conversation with a message that names the file path"。工具可自带 `_meta["anthropic/maxResultSizeChars"]`（硬上限 500,000 字符），但 "has no effect on tools that return image content"。
- 含 image 且超限时具体怎么办，文档与二进制都没有明句，**［查不到］**。
- 对照 Bash：默认内联约 30,000 字符，超过存盘换路径（`BASH_MAX_OUTPUT_LENGTH` 最大 150,000）。

---

## 2. MCP server 在这个体系里的生命周期与分发面

### 2.1 谁拉起、何时杀、宿主崩溃时怎样

**Codex**［源码事实，`rust-v0.154.0`］
- **归属粒度是线程（会话）**：`codex-mcp/src/runtime.rs` "Owns all mutable MCP state for one Codex thread. pub struct McpRuntime"。TUI 与 `codex exec` 一进程一线程；桌面应用（app-server）多线程即多套 server 进程。
- **拉起时机**：会话启动即拉起，不是懒加载。本机实测：`codex exec` 下探针 server 日志 `start` → `initialize` → `notifications/initialized` → `tools/list` 全在 2 ms 内、发生在会话开头；模型第一次 `tools/call` 在 20–25 s 后（模型往返）。**［本机实测］**
- **怎么拉**：`rmcp-client/src/stdio_server_launcher.rs`：`Command::new(resolved_program).current_dir(cwd).env_clear().envs(envs).args(args)`，**不经 shell**；Unix `process_group(0)`；Windows 用 `JobObject::create_without_breakaway()` 挂起式创建再放进 Job，失败则退化为单进程句柄；`kill_on_drop(true)`。
- **怎么杀**：`Op::Shutdown` 或提交通道关闭 → `mcp_runtime.shutdown()` → "terminate stdio server processes"；Unix 先 SIGTERM 进程组、2 s 后 SIGKILL；Windows `job.terminate()`。桌面/app-server 侧线程无订阅者且空闲 `thread_unload_delay`（默认 60 s）后 10 s 内 `shutdown_and_wait()`。**本机实测**：`codex exec` 退出后探针 PID 不在了，server 日志里**没有** "stdin closed, exiting" 那一行，即被硬杀、不是关管道。
- **宿主崩溃**：Windows Job 带 `JOB_OBJECT_LIMIT_KILL_ON_JOB_CLOSE`（`utils/pty/src/win/job.rs`），宿主死亡句柄关闭即杀整个 Job；Unix/macOS 全仓 grep **无 prctl / PDEATHSIG**，宿主被 SIGKILL 时子进程存活**［设计推断］**，律师那台 mac 上**［须实测］**。
- **超时默认**：源码 `rmcp_client.rs` `DEFAULT_STARTUP_TIMEOUT = 30s`、`DEFAULT_TOOL_TIMEOUT = 300s`；**官方文档（learn.chatgpt.com/docs/extend/mcp、config-reference）写的是 "Default: 10." 与 "Default: 60."**，两处不一致，本票不判谁对。本机现成的两份登记：`config.toml` 的 `node_repl` 写 `startup_timeout_sec = 120`；`codex-app-tools` 的 `.mcp.json` 写 `startup_timeout_sec: 10, tool_timeout_sec: 3600`。另有 `mcp_optional_startup_grace_ms`（可选 server 的共享等待，源码默认 1 s）。

**Claude Code**［源码事实 + 本机实测（子探针）］
- **拉起时机**：会话启动时所有配置的 stdio server 全部拉起（工具定义走 ToolSearch 延迟加载，**进程本身不延迟**）。实测 claude 拉起 → python 进脚本 0.432 s（两次一致），随后 `initialize`、`tools/list` 立即到。cli-reference：`--mcp-config` 配 `-p` 时 "waits for still-pending servers to connect before running the first turn, up to the `MCP_TIMEOUT` startup timeout, 30 seconds by default"。文档明说 "Stdio servers are local processes, and Claude Code doesn't reconnect them automatically."
- **正常退出**：`claude -p` 退出后探针 PID 不在；server 日志末行 `stdin EOF, exiting`（tools/call 应答后 2.5–4.8 s 收到 EOF），即**关管道、让它自己退**。
- **宿主被杀 / 崩溃**：文档没说，本次未测强杀，**［查不到］**。CHANGELOG 里的相关修复：1.0.36 "stdio MCP servers were not terminating properly on exit"、2.1.6 "`mcp list` … leaving orphaned MCP server processes"、2.1.15 "stdio server timeout not killing child process"、2.1.153 "[VSCode] … orphaned MCP servers" on Windows。
- **超时**：`MCP_TIMEOUT` 30,000 ms（启动）；`MCP_TOOL_TIMEOUT` 默认 100,000,000 ms（约 28 小时，"Stdio and WebSocket servers have no per-request timer"）；`CLAUDE_CODE_MCP_TOOL_IDLE_TIMEOUT` stdio 默认 1,800,000 ms（30 分钟）；`CLAUDE_CODE_MCP_AUTO_BACKGROUND_MS` 120,000；`MCP_CONNECT_TIMEOUT_MS` 5,000。`.mcp.json` 每 server 的 `timeout` 字段（毫秒，≥1000 才生效）覆盖。
- `SessionEnd` hook 与 MCP server 关闭谁先谁后：hooks 文档没有一句，**［查不到］**。

**冷启动开销**［本机实测，`coldstart.py`，Popen 到收到 `initialize` 应答，各 5 次］

| 解释器 | 耗时 |
| --- | --- |
| python 3.14.2（python.org 安装管理器那份） | 20 / 22 / 22 / 23 / 24 ms |
| python 3.9.25（uv 管理，对应律师机的 3.9 下限） | 33 / 37 / 39 / 42 / 48 ms |

零依赖、只 `import sys, json, os, time` 的 server，冷启动是几十毫秒量级；两宿主在会话开头就拉，模型第一次调用前早已就绪。律师那台 mac 的 `/usr/bin/python3` **［须实测］**。

### 2.2 登记与分发：四处的字段形状，两条渠道带不带

**Codex `~/.codex/config.toml [mcp_servers.<name>]`**［源码事实，`config/src/mcp_types.rs` `RawMcpServerConfig`］：`command, args, env, env_vars, cwd, http_headers, env_http_headers, url, bearer_token_env_var, http_headers_helper, environment_id, auth, startup_timeout_sec(f64), startup_timeout_ms, tool_timeout_sec, enabled, required, supports_parallel_tool_calls, omit_tools_from, default_tools_approval_mode, enabled_tools, disabled_tools, scopes, oauth{client_id,callback_url,callback_port}, oauth_resource, tools.<tool>.{approval_mode, output_token_limit}`。`env_vars` 是**白名单透传**（从宿主 Codex 进程环境读）。官方 config-reference 列的同一组里**没有** `omit_tools_from`、`supports_parallel_tool_calls`。项目级 `.codex/config.toml` 可带 `[mcp_servers]`（文档："you can also scope MCP servers to a project with .codex/config.toml (trusted projects only)"；源码 `PROJECT_LOCAL_CONFIG_DENYLIST` 不含 `mcp_servers`），但 open issue #13025 "Codex Desktop ignores project .codex/config.toml MCP server"。`codex mcp add/list/get/remove/login/logout` 写的是全局那份。

**Codex `.codex-plugin/plugin.json` 的 `mcpServers`**［源码事实］：`core-plugins/src/manifest.rs` 取路径或内联对象；`.mcp.json` 顶层 `{"mcpServers": {...}}`，每项经 `normalize_plugin_mcp_server_value` 后 `serde_json::from_value::<McpServerConfig>`，**字段与 config.toml 完全同名**。本机自带的 `codex-app-tools` 就是范本：`plugin.json` 只有 `"mcpServers": "./.mcp.json"`，`.mcp.json` 里 `command`（`cmd.exe /d /s /c call ./scripts/launch_….cmd ./server.mjs`）、`cwd`（绝对路径）、`enabled: false`、`omit_tools_from: ["deferred"]`、`default_tools_approval_mode: "approve"`、`tools.<x>.approval_mode: "prompt"`、`env_vars`（白名单 10 个名字）、`startup_timeout_sec: 10`、`tool_timeout_sec: 3600`、`env`。用户侧可用 `[plugins."<plugin>".mcp_servers.<n>]` 覆盖 `enabled / default_tools_approval_mode / enabled_tools`。**Agent Plugins**（`developers.openai.com/plugins`）格式更严：根目录 `mcp.json`，stdio `command` 须是裸可执行名或 `./` 路径，`cwd` 只许 `./`、`${PLUGIN_ROOT}`、`${PLUGIN_DATA}`；官方示例只给了 `streamable-http`。

**Codex skill 声明 MCP 依赖**［源码事实，文档原文］：`agents/openai.yaml` 可写
```yaml
dependencies:
  tools:
    - type: "mcp"
      value: "<server 名>"
      description: "…"
      transport: "streamable_http" | "stdio"
      url: "…"        # 或 command: "…"
```
`core/src/mcp_skill_dependencies.rs`：仅 `type == "mcp"`、特性 `skill_mcp_dependency_install`（stable、默认 true）且 **first-party originator** 时弹 "Install" / "Continue anyway"；stdio 时 `command` **整串、不拆 args**，写进**全局** `~/.codex/config.toml`。这条随 skill 目录走、skills.sh 拷得到，但"first-party originator"这个条件对第三方 skill 到底放不放行，**［须实测］**。`SKILL.md` 正文不能声明依赖。

**Claude Code `.mcp.json`（项目级）**［源码事实，文档原文］：`{"mcpServers": {"<name>": {type, command, args, env, url, headers, timeout, request_timeout_ms}}}`；`type` 缺省 stdio，"A JSON entry that has a `url` but no `type` is a configuration error"；`${VAR}` 与 `${VAR:-default}` 在 `command / args / env / url / headers` 里展开，缺变量时"uses the unexpanded `${VAR}` text as-is"并在 `claude mcp list` 报警。作用域三档：Local（`~/.claude.json` 的 `projects[<path>].mcpServers`，默认）、Project（`.mcp.json`，随版本库）、User（`~/.claude.json` 顶层）；优先级 Local > Project > User > Plugin > claude.ai connectors，"fields are not merged across scopes"。项目级 server 交互会话要审批（`enableAllProjectMcpServers` / `enabledMcpjsonServers` / `disabledMcpjsonServers` 三键，拒绝优先），`claude -p` 与 SDK 会话"loads project-scoped servers without asking"。

**Claude Code `.claude-plugin/plugin.json` 的 `mcpServers`**［源码事实，plugins-reference］：`string | array | object`，"MCP config paths or inline config"，示例 `"./mcp-config.json"`；`${CLAUDE_PLUGIN_ROOT}` 可用于 `command / args / env`，"changes when the plugin updates"；"At session startup, Claude Code connects the servers for enabled plugins automatically"。插件自带的 agent 不许带 `mcpServers`。

**skills.sh 那条渠道带不带**：`skills` 1.5.26 的 `dist/cli.mjs` 里 `mcpServers` **零命中**，全文含 "mcp" 的只有 `mcpjam` 这个 agent 目录名。它只拷 `<skills 根>/<skill 目录名>/`（#132 A.5），仓库根或 `.claude-plugin/`、`.codex-plugin/` 下的任何 MCP 登记**一个字节都不带**。**［源码事实］** 唯一能随 skill 目录到达的是上面那份 `agents/openai.yaml` 的依赖声明（只对 Codex 有意义）。

**离线兜底包带不带**：`scripts/pack-offline.py` 按 `.claude-plugin/plugin.json` 的 `skills` 数组拷 skill 目录，全文没有 `mcp` 字样；`.mcp.json` 若放仓库根，不在任何 skill 目录下，**不带**。**［源码事实］**

**两个插件市场**：整仓克隆（#126 C.2、C.3），`.mcp.json` 与两份 plugin.json 里的 `mcpServers` 都能到；到了之后各宿主按各自的 plugin.json 读。**［源码事实 + 设计推断］**

### 2.3 PATH 里没有 `python` 对 MCP 启动命令意味着什么；已知稳定性问题

- **Codex**：MCP server 的进程环境是 `env_clear()` 后只放白名单（Windows：`PATH, PATHEXT, SHELL, COMSPEC, SYSTEMROOT, WINDIR, SYSTEMDRIVE, USERNAME, USERDOMAIN, USERPROFILE, HOMEDRIVE, HOMEPATH, PROGRAMFILES, PROGRAMFILES(X86), PROGRAMW6432, PROGRAMDATA, LOCALAPPDATA, APPDATA, TEMP, TMP, TMPDIR, POWERSHELL, PWSH`；Unix：`HOME, LOGNAME, PATH, SHELL, USER, __CF_USER_TEXT_ENCODING, LANG, LC_ALL, TERM, TMPDIR, TZ`）加 `env_vars` 点名的；**PATH 来自宿主 Codex 进程，不是沙箱**。Windows 上用 `which::which_in(program, 那个 PATH, cwd)` 连 `PATHEXT` 一起解析；所以 `command = "python"` 找的是宿主 PATH 上的 `python.exe/.cmd/.bat`。**［源码事实］** #126 B.2 记的"Codex 沙箱 PATH 无 `python`"说的是模型跑 shell 命令那条路，与 MCP 拉起是两条路。**［设计推断］** 律师那台 mac 只有 `python3`（`/usr/bin/python3`），写 `command = "python"` 大概率找不到，写 `python3` 才对，**［须实测］**。
- **Claude Code**：`.mcp.json` 直接写 `"command": "python"`（不加 `cmd /c`、不写 `.exe`），Windows 原生 `claude.exe` 在 Git Bash 里 `claude -p` 能拉起 `python.exe`（`status: connected`）。**［本机实测］** 当前 mcp 文档里**没有** "cmd /c npx" 那段（**［查不到］**）；CHANGELOG 2.1.119 "Windows: removed false-positive 'Windows requires cmd /c wrapper' MCP config warning"。旧要求是为 `npx` 这种 `.cmd` 垫片，`python.exe` 不受影响，**［设计推断］**。
- **Codex 官方 issue（open，按评论数）**：#40715 / #40819 Windows 与 WSL 上 "invalid transport in mcp_servers.codex_app"（71 / 65 评）；#6465 VS Code 扩展不认 MCP；#19425 stdio server 被 `/mcp` 发现但工具没进桌面线程；#6020 initialize 握手 connection closed；**#30408 MCP server 进程按线程泄漏、不清理（9+ GB RSS）**；#12491 Codex.app 1300+ 僵尸 MCP 子进程；#26984 stdio fd 泄漏 + 孤儿；#38754 Windows 单任务内 stdio server 反复拉起不回收；#34614 Windows 终止漏掉 cmd.exe/node.exe 孙进程；#26956 中断/超时后从不通知 MCP server 停；#22072 `startup_timeout_sec` 不覆盖 OAuth 引导；#29396 给内置 server 设 `startup_timeout_sec` 反报 invalid transport。**［源码事实］**（只列不评）
- **Claude Code 官方 issue（open，标题含 mcp、按 👍）**：#3433 GitHub 远程 MCP OAuth 连不上；#1785 MCP Sampling；#10447 CLI 开关 MCP server；#16210 SDK 不读项目级 MCP；#64654 plugin:github MCP HTTP 400；#33969 每回合工具调用上限回归；#10071 断线重连；#65036 / #26281 OAuth token 不刷新；#26073 Windows MSIX "Edit Config" 打开错的 claude_desktop_config.json；#23669 Agent Teams 每成员 MCP 配置。**［源码事实］**（只列不评）

### 2.4 与本仓库既有裁定的关系

- **ADR-0011「不设 MCP server」当年的理由**（正文原话）：调研票 #11 查到 "MCP App 消费一个 JSON（`structuredContent`）加一段模型可读文本（`content`），且 Claude Code 与 Codex 两个 CLI 都还不渲染，落盘文件是唯一可见通道"；于是"引擎不出任何呈现物。不出 HTML、不加读视图 CLI 子命令、不设 MCP server"，并把 `图视图.json` / `图视图.md` 留作"将来 MCP App 的 `structuredContent` / `content`"。**［源码事实］**
- **今天变了的一半**：Codex 桌面应用会把 MCP 结果里的 `image` 块渲成图给人看（1.2），会把回复里的 Mermaid 与表格渲出来（3.1）；MCP App 的壳在桌面渲染层里已经有，只是旗未转正。**没变的一半**：两个终端 TUI 仍不渲染；`text` 块与 `text/html` 资源在桌面里也只当纯文本。**［源码事实］** 要不要据此改 ADR-0011 是 #127 的事。
- **两份 plugin.json 今天只有 `skills` 一项**（#126 D.4 不变）。接 MCP 等于：Codex 侧加 `mcpServers` + 一份 `.mcp.json`，Claude 侧加 `mcpServers`（可指同一份 `.mcp.json`，字段形状两边不同：Codex 认 `cwd / enabled / omit_tools_from / default_tools_approval_mode / tools.*`，Claude 认 `type / timeout / ${VAR}`），登记处从 2 变 4（两份 plugin.json 各一处 + `.mcp.json` 两个宿主各读一遍）；skills.sh 与离线包两条渠道对它视而不见。**［设计推断］**

---

## 3. CLI 交出去的东西，宿主怎么呈现

### 3.1 stdout 去哪，模型转述的表格 / Mermaid 渲不渲

**stdout 先进模型，人看的是宿主自己的"命令格"**：
- Codex：`item/commandExecution/outputDelta` 流式推给客户端；桌面聚合显示，超长时前置一行 `[output truncated]`（`app.asar`）；本机 `config.toml [desktop] conversationDetailMode = "STEPS_COMMANDS"` 是显示命令明细的档位。TUI 显示折叠的命令格。**［源码事实］**
- Claude Code：Bash 结果内联约 30,000 字符（1.4），终端显示工具结果、`Ctrl+O` 展开。**［源码事实］**
- 两边都**不**把 stdout 当 Markdown 渲：Codex 桌面对 MCP `text` 块用 `<pre>`（1.2），命令输出同理是等宽原文。**［源码事实 + 设计推断］**

**模型把 stdout 里的 Markdown 转述进回复之后**：

| | 表格 | Mermaid 围栏块 |
| --- | --- | --- |
| Codex 桌面应用 | `marked` 以 `gfm: true` 初始化，`renderer.table` 出 `<table><thead>…`；另有 "Table preview" 弹窗（`markdown.tablePreview`）**［源码事实］** | 渲成图：内置 mermaid 库（`mermaid.initialize`）与 `mermaidDiagram.preview / expand / download / copySource / invalidOrUnsupported`（"Invalid or unsupported diagram"）、`codeBlock.mermaid.loadingDiagram`（"Loading diagram"）**［源码事实］**；`gpt-6-astra` 的系统提示原话 "Your answer is being rendered by an application for the user. … You may format with GitHub-flavored Markdown"（`models.json`） |
| Codex 终端 TUI | **渲成对齐文本表**：本机 winpty 实测，两列两行的表出来是 `列A    列B` / `━━━━━  ━━━━━` / `1      2`（`tui_table.py`）**［本机实测］** | **围栏剥掉、正文原样打成一行** `graph TD; A-->B`，无图、无提示 **［本机实测］** |
| Claude Code 终端 | 渲成框线表（CHANGELOG："Added markdown table support"；2.1.141 "rendering as a bordered grid"；窄终端回退成竖排键值；超 200 行截）**［源码事实］** | 文档与 CHANGELOG 无 "mermaid" 一词 **［查不到］**；按普通代码块显示 **［设计推断］** |

### 3.2 CLI 写出的图片文件（PNG / SVG）能不能给人看

- **Codex 桌面应用**：`view_image` 是模型输入（#126 已记）。渲染层里图片能进对话的通道有三条：用户附件（`type: image | localImage`）、MCP 结果里的 `image` 块（1.2）、MCP App 的 `ui/update-model-context`（"Shared an image from {appName}"）。**没有找到"模型指一个本地图片路径、宿主把它内联给人看"的通道**。**［查不到］** `visualize` 的 `SKILL.md` 提到 "Never add `sandbox:` links to inline visualization HTML unless the user specifically requests a download"，说明桌面认 `sandbox:` 链接作**下载**通道；它是不是也能内联显示图片，**［查不到］**。自带 `browser` 插件能开 `file://`（#126 A.5），那是模型驱动的浏览器，不是给律师看的窗口。
- **Codex 终端 TUI**：TUI 内联图片的两条 issue（`#29451`、`#35755`）至今 open（#126 A.3）。
- **Claude Code 终端**：不渲染图像（#126 A.4）；MCP 结果里的 image 也只显示 `[Image]`（1.3）。
- **结论（事实层面）**：CLI 落盘一张 PNG，**两宿主都没有一条把它直接给律师看的官方通道**；能给人看的图只有走 MCP `image` 块进 Codex 桌面这一条（1.2），或落盘后律师自己打开。**［源码事实 + 查不到］**

### 3.3 Codex 桌面应用有没有律师自己可用的内置终端

**有。［源码事实］**
- 官方文档 "Integrated terminal"（learn.chatgpt.com/docs/integrated-terminal）原文："Each chat in the ChatGPT desktop app includes a terminal scoped to its current project or worktree. Open it from the terminal icon in the top-right corner of the app, or press Ctrl+`." "ChatGPT can read the current terminal output, so it can check a running development server or refer to a failed build while it works with you." Windows 页："You can also choose the default integrated terminal. … Options include: PowerShell, Command Prompt, Git Bash, WSL"。（文档站现已把 Codex app 改称 "ChatGPT desktop app"。）
- 渲染层：`app.asar` 里 `xterm` 242 处、`node-pty` 28 处；设置项 `integratedTerminalShell`（枚举 `powershell | commandPrompt | gitBash | wsl`）、`defaultTerminalLocation`（`bottom | right`，本机 `config.toml [desktop]` 记的就是它）；命令 "Open terminal" / "Open the terminal panel"；标签 "Terminal {index}"、"Open bottom terminal"、"Background terminal"、"Stop all background terminals"；错误态 "The terminal encountered an error / Try reloading the terminal"。
- **交互式 TUI 查看器（curses / Textual）能不能在里面跑**：xterm + node-pty（Windows 下是 ConPTY）是标准的终端仿真栈，按理能跑全屏 TUI，**［设计推断］**；没有跑过，**［须实测］**。终端与会话同一个 cwd（"scoped to its current project or worktree"），律师要打命令仍是自己打。

### 3.4 `visualize` 内联通道除 HTML 外还认什么；桌面那套提示词全文

从桌面应用随包的 `codex.exe`（`app/resources/codex.exe`，297,858,352 字节）抽 `### Visualizations` 段，**共三种不同文本**：桌面（code-mode）那套 1 处，终端那套 12 处（两份措辞几乎相同、只在后面的 "Rules for getting work done" 分叉）。桌面那套**全文**（`viz_prompt.py` 抽出，`\n` 已还原）：**［源码事实］**

> ### Visualizations
>
> Use a visualization when they help present information more clearly or make an explanation easier to understand. Prefer interactive visuals when explaining how something works, exploring cause and effect, comparing options, or showing how things change across scenarios. The user does not need to explicitly request a visualization.
>
> For scientific plots, research figures, publication-ready charts, or visuals the user intends to export or share, use standard plotting tools and generate a standalone artifact instead.
>
> Use tables for mappings or comparisons. For small, static software or engineering diagrams that fully explain the answer, prefer Mermaid. Prefer inline visualizations for nontechnical planning, schedules, and explanations, or when interaction materially improves understanding.
>
> Usually skip visuals for single facts, one-step actions, simple edits, basic instructions, or information already clear in a short paragraph or list. Compact notation and small examples do not count as visualizations.

终端那套（同一二进制，12 处；#126 A.3 已摘，这里补全文）：

> ### Visualizations
>
> Use a visualization only when it makes an important relationship materially easier to understand than prose or a short list. Do not add one merely because an answer has components or steps.
>
> Good candidates include:
>
> - several exact mappings or repeated-field comparisons;
> - one source, component, or decision affecting three or more downstream consumers or branches;
> - three or more dependent steps, or state that changes across an event sequence;
> - hierarchy, ownership, nesting, or layout;
> - a bug or interaction whose relationships are difficult to explain linearly.
>
> Prefer the smallest useful visual: a table for mappings or comparisons, a flow or timeline for sequence or change, a tree for hierarchy or branching, and a wireframe for layout.
>
> Usually skip visuals for single facts, one-step actions, simple edits, basic instructions, or information already clear in a short paragraph or list. Compact notation and small examples do not count as visualizations.

同一段在 `models.json` 里也有：只有 `gpt-6-astra` 的 `instructions_template` 带桌面那套（含 Mermaid 句），gpt-5.x 系只带 "GitHub-flavored Markdown" 句。**［源码事实］** #132 B.3 记的"TUI 会话提示词里两套都没进"仍成立（`codex debug prompt-input` 零命中）。

于是这条通道**认三样**：**［源码事实］**
1. **表格**：普通 Markdown 表，`visualize` 的 `SKILL.md` 明写 "Use a normal Markdown table when the user asks for a table; return it directly and do not create a visualization file"；
2. **Mermaid**：静态结构，"return a normal fenced Mermaid block and no visualization file"；
3. **HTML 片段**：动态 / 交互 / 空间关系，落盘 `<title>.html` 后回复里单起一行 `visualize{"path":"…"}`，可加 `"mode":"wide"`（1,024px）与 `title`；片段里可调宿主提供的 `window.openai.sendFollowUpMessage({ prompt, title })` 与 `Tweak` 助手；CSP 只放 `cdnjs.cloudflare.com`、`esm.sh`、`cdn.jsdelivr.net`、`unpkg.com`、`fonts.googleapis.com`、`fonts.gstatic.com`、`fonts.bunny.net`；1 MB 内、不许 `fetch`。

**纯文本图**（flow / timeline / tree / wireframe）只在终端那套提示词里，是给模型用文字排的，不是一条渲染通道。桌面渲染层的 `inline_visualization` 事件名 `__codex_inline_visualization_ready__ / _error__ / _click__ / _download__ / _hover__ / _height__` 与 `<style id="codex-visualization-document-overflow">` 印证它是 iframe 内联、按内容定高。**［源码事实］** 真在桌面里看它渲一次，仍是 #132 D 留下的**［须实测］**。

---

## 4. CLI 拉起窗口的最轻量选项（Tauri 见 #126 F.4，不重查）

只查安装面、分发面与进程寿命，不查界面。本机没有 mac，mac 侧一律**［须实测］**。

### 4.1 `tkinter`

- **Apple 自带 python3 带不带 Tk**：python.org 官方页 "IDLE and tkinter with Tcl/Tk on macOS" 原文 "If you are using macOS 10.6 or later, the Apple-supplied Tcl/Tk 8.5 has serious bugs that can cause application crashes. If you wish to use IDLE or Tkinter, **do not use the Apple-supplied Pythons**."；"Using Python on macOS" 原文把 `/usr/bin/python3` 定性为 "a usually older and incomplete version of Python provided by and for use by the Apple development tools"。**［源码事实］** 但 Command Line Tools 那份 3.9.6 到底有没有 `_tkinter`、链哪版 Tk，Python 与 Apple 文档都没有逐项说明，**［查不到］**；那句常见的 "DEPRECATION WARNING: The system version of Tk is deprecated" 在 CPython 3.9 与上游 Tk 源码里都 grep 不到，只能是 Apple 自己的补丁，**［设计推断］**。律师机上跑 `/usr/bin/python3 -m tkinter` 一次就知道，**［须实测］**。
- **Windows**：python.org 完整安装包 `Include_tcltk` 默认 `1`（"Install Tcl/Tk support and IDLE"）；Microsoft Store 版带 IDLE 即带 tkinter；嵌入式发行版不带。**［源码事实］** 本机两版都在：3.14.2 与 3.9.25 的 `tkinter.TkVersion` 均为 8.6。**［本机实测］**
- **画树**：`tkinter.Canvas` 只要标准库；`python -m tkinter` 是官方自检（"should open a window demonstrating a simple Tk interface … showing what version of Tcl/Tk is installed"）。**［源码事实］**
- **进程寿命**：`mainloop()` "processes events until all windows are destroyed"；脚本本身就是 GUI 进程时，**窗口寿命 = 进程寿命**。**［源码事实 + 设计推断］** 本机实测（`tk_lifetime.py`）：用 `pythonw.exe` + `DETACHED_PROCESS` 起一个 20 秒后自毁的窗口、父进程立刻退出：3 秒后窗口进程 `pythonw` 活着、标题 `probe-tk`；25 秒后进程不在，**窗口关即进程退，父进程退出不带走它**。**［本机实测］** 官方依据：Microsoft "When the system is terminating a process, it does not terminate any child processes"；但同一控制台被用户关掉时所有附着进程收 `CTRL_CLOSE_EVENT`（用 `pythonw` / `DETACHED_PROCESS` 脱离即可）；POSIX "Termination of a process does not directly terminate its children"，只有控制终端那条路发 SIGHUP，`start_new_session=True` 脱离。**［源码事实］** 宿主（Claude Code / Codex）会不会把子进程关进 Job 一起收：Codex 对 MCP server 会（2.1），对 shell 起的子进程 #126 B.2 测过"这台机上没有"；Claude Code **［查不到］**。

### 4.2 `pywebview`、`wry`、系统自带 WebView 的零安装拉起

| 方式 | 律师 mac 要装什么 | Win11 要装什么 | 窗口寿命 = 进程寿命？ | 性质 |
| --- | --- | --- | --- | --- |
| `pywebview` | `pip install pywebview` ⇒ 五个 `pyobjc-*` 第三方包（官方 "PyObjC comes preinstalled with the Python bundled in macOS" 指的是早年 Python 2.7；CLT 3.9.6 带不带 `objc` 查不到） | `pythonnet` + .NET 4.0+ + WebView2 Runtime | `webview.start()` "Start a GUI loop"，返回时点官方没写 | 源码事实 / 查不到 |
| `wry` | Rust 工具链 + `cargo` 编译；README 只有 Rust 示例，**无预编译可执行文件** | 同左 | 不适用（是库，v0.57.0，`rust-version 1.85`） | 源码事实 / 查不到 |
| `mshta.exe` + `.hta` | 不适用 | **零安装**（本机 `C:\Windows\System32\mshta.exe` 在）；引擎是 IE/MSHTML，文档模式靠 `<meta http-equiv="x-ua-compatible">` 最高到 IE 系列；Microsoft Learn 对 mshta 本身没有弃用公告 | 每个 `.hta` 一个 `mshta.exe` 进程（Q&A 口径，非正式文档） | 源码事实 / 查不到 / 须实测（ES6+ 能否跑） |
| Edge `--app=<url>` | mac 无 Edge 预装；Safari 无此开关 | **零安装**（本机 `msedge.exe` 在）；`--app` 在 Microsoft Learn 正式文档里**查不到**，Chromium 官方开关表两条抓取路径 404、只有第三方镜像 | **否**：窗口属于浏览器进程，浏览器已有别的窗口时关它不退 | 查不到 / 设计推断 |
| WebView2 直接起窗（不装 SDK） | 不适用 | Runtime 随 Win11 预装（Microsoft "The Evergreen WebView2 Runtime will be included as part of the Windows 11 operating system"；本机注册表 `pv = 152.0.4191.66`），但官方支持面只有 Win32 C/C++、.NET、WinUI，**无"仅 PowerShell / Python 标准库"路径**，社区做法仍要借 SDK 的托管 DLL | 须实测 | 源码事实 / 查不到 |
| `open` / `webbrowser` 交给默认浏览器 | 零安装；`open -W` 才等应用退出，默认立即返回（Apple 在线 man page 已下线，引第三方摘录） | 零安装（`os.startfile`） | **否**，与调用者无父子关系 | 源码事实 / 设计推断 |
| `swift` 脚本 / JXA 起 WKWebView | `swift` 是否在 Command Line Tools 里：Apple 页未点名（列的是 clang、git、xcrun、xctrace）；JXA 建 NSWindow+WKWebView 无官方记载 | 不适用 | 须实测 | 查不到 / 须实测 |

Python 标准库 `webbrowser` 3.9：macOS 走 `osascript` 的 `open location "<url>"`，Windows 走 `os.startfile(url)`，两边都忽略 `new` / `autoraise`，**没有传 `--app` 之类开关的通道**；要用应用模式只能自己 `subprocess` 起浏览器可执行文件。**［源码事实］** #126 I.3 记的"`webbrowser.open()` 不能直接喂文件名、要先 `as_uri()`"仍有效。

---

## 5. 收口

### 5.1 五行五列

| | Codex 桌面应用能看见什么 | Claude Code 能看见什么 | 要装什么 | 常驻物 | 分发面 |
| --- | --- | --- | --- | --- | --- |
| **MCP 工具结果** | `image` 渲成 `<img>`（最高 12rem，可点开）；`audio` 出播放器；`text` 放进 "plaintext" 代码容器、**不当 Markdown 渲**；`resource_link` 只一行 "Read {name}"；`resource` 的 Content 放 `<pre>`、**HTML 不渲**；整个调用默认折叠成一行 "{tool}"、要点开 ［源码事实］；真看一眼 ［须实测］ | 终端只显示 `[Image]` 占位与折叠的 "Called {server} N times"（`Ctrl+O` 展开）；`resource` 改写成 `[Resource at uri] text` 一行；模型侧收到图 ［源码事实 + 本机实测］ | 律师机：一个 python 解释器（零第三方依赖 server 几十毫秒冷启动）；宿主：登记一处 | server 进程随会话起落：Codex 每线程一套、退出硬杀（Windows Job 带走，macOS 崩溃时存活 ［设计推断/须实测］）；Claude Code 退出关管道、崩溃时下场 ［查不到］ | 两个插件市场到（各宿主读各自 plugin.json 的 `mcpServers`）；**skills.sh 不带、离线包不带**；Codex 另可走 skill 的 `openai.yaml` 依赖声明（写进全局 config.toml，第三方 skill 放不放行 ［须实测］） |
| **MCP 资源** | 工具结果里的 `resource` / `resource_link` 同上：只显示 URI、MIME、原文；`resources/read` 的宿主处理只在 MCP App 壳里见到，`enable_mcp_apps` 仍 false ［源码事实］ | `@server:uri` 引用后"fetched and included as attachments"，`ListMcpResourcesTool` / `ReadMcpResourceTool` 供模型用；给人看的是文本 ［源码事实］ | 同上 | 同上 | 同上 |
| **CLI stdout** | 进模型；桌面在 STEPS_COMMANDS 明细里流式显示原文（超长 `[output truncated]`）；模型转述后表格渲 `<table>`、Mermaid 渲成图 ［源码事实］ | 进模型；终端显示结果（约 30,000 字符内联）；模型转述后表格渲成框线表，Mermaid 原样代码块 ［源码事实 / 查不到］ | 无 | 无 | 五条渠道都到（#132） |
| **CLI 写图片** | **查不到**给律师看的通道：`view_image` 是模型输入，`visualize{}` 只认 HTML 片段，`browser` 插件是模型的浏览器 | 终端不渲染图像 ［源码事实，#126 A.4］ | 无 | 无 | 五条渠道都到 |
| **CLI 拉窗口** | 与宿主无关的外部窗口；桌面另有律师可用的内置终端（`` Ctrl+` ``，PowerShell/CMD/Git Bash/WSL），TUI 查看器能否在其中跑 ［须实测］ | 同左（外部窗口） | tkinter：Windows 官方包默认带、本机 Tk 8.6；律师 mac 的 CLT 3.9.6 带不带 ［查不到/须实测］。pywebview：pip 装第三方。wry：Rust 编译。mshta / Edge `--app` / WebView2 Runtime：Win11 零安装（后两者无官方开关或无 SDK 路径）。`open` / `webbrowser`：零安装 | tkinter / mshta：**窗口寿命 = 进程寿命**，父进程退出不带走（本机实测）；浏览器 `--app` / `open`：窗口不等于进程 | 随 skill 目录走的纯 python 五条渠道都到；任何第三方包或二进制没有渠道 |

### 5.2 「轻量」「稳定」拆成可度量的项（只填数，不下结论）

| 项 | MCP server（stdio，python 零依赖） | CLI + 落盘 HTML / `visualize{}`（#126 第 3、5 条） | CLI 拉 tkinter 窗口 | CLI 拉浏览器 / `--app` |
| --- | --- | --- | --- | --- |
| 律师机安装件数 | 0（系统 python） | 0 | 0（若 CLT python 带 `_tkinter`；否则 1：python.org 安装包）［须实测］ | 0 |
| 会话期进程数 | +1 常驻（会话开始拉、结束杀；Codex 桌面每线程 +1） | 0 | 窗口开着时 +1，关即 0 | 0（复用浏览器进程） |
| 登记处数 | Codex 侧 1（`config.toml` 或插件 `.mcp.json`）+ Claude 侧 1（`.mcp.json` 或插件 `mcpServers`）+ 两份 plugin.json 各加一项 = **4** | 0（只是 skill 目录里的文件） | 0 | 0 |
| 分发渠道覆盖 | 插件市场 2/5；skills.sh、junction（开发机能到但验不了）、离线包不带登记 | 5/5 | 5/5 | 5/5 |
| 宿主升级时会坏的面 | 登记字段形状（Codex 文档与源码的默认超时已不一致；`mcp_2026_07_28` 协议切换待转正）；桌面渲染层的折叠/`<img>` 行为；Codex `enable_mcp_apps` 转正与否 | `visualize{}` 契约（`SKILL.md` 1.0.37）与 TUI 退化行为（#132） | 无宿主面 | 浏览器 `--app` 开关无官方文档 |
| 已知官方 open issue（本文列出的） | Codex 11 条 + Windows 专项 8 条 + 超时 7 条；Claude Code 15 条（多为 OAuth / 连接器） | 2 条（TUI 内联图片 `#29451`、`#35755`） | 0 | 0 |
| 谁清理 | 宿主（Codex 硬杀；Claude 关管道）；崩溃时 Codex/Windows 靠 Job，macOS 与 Claude Code ［须实测/查不到］ | 无需 | 律师关窗 | 律师关窗 |
| 冷启动 | 20–48 ms（python 3.14 / 3.9，本机） | 0 | tkinter 起窗未量 ［须实测］ | 浏览器启动未量 |
| 律师看得见图的宿主 | Codex 桌面（`image` 块）；Claude Code 终端看不见 | Codex 桌面（`visualize{}`）；两个终端都看不见 | 两宿主都看得见（外部窗口） | 两宿主都看得见（外部窗口） |

### 5.3 本票留下的须实测清单

| # | 要测什么 | 在哪测 | 卡住谁 |
| --- | --- | --- | --- |
| 1 | Codex 桌面应用里 MCP 结果 `image` 块的真实呈现：折叠态、展开态、点开灯箱 | 本机桌面应用，登记 `probe_server.py` | MCP 那条路 |
| 2 | Codex 上 `structuredContent` 到底吞不吞 `content`（源码说吞、实测没吞）；`context_management` 关掉后 60k / 400k 字符的 text 块各到多少 | 本机 `codex exec` | 1.1、1.4 |
| 3 | macOS 上宿主被强杀时 stdio server 的下场（Codex 无 PDEATHSIG；Claude Code 文档没说） | 律师那台 mac | 2.1 |
| 4 | 律师 mac 的 `/usr/bin/python3`：`command = "python3"` 能否被两宿主拉起；`import _tkinter` 成不成、Tk 哪版、有没有弃用警告 | 律师那台 mac | 2.3、4.1 |
| 5 | Codex skill `openai.yaml` 的 MCP 依赖声明对第三方 skill 放不放行（"first-party originator" 条件） | 本机 Codex | 2.2 |
| 6 | 交互式 TUI 查看器在 Codex 桌面内置终端里能不能跑 | 本机桌面应用 | 3.3 |
| 7 | `visualize{}` 在桌面里的真实渲染（#132 D 留下的） | 本机桌面应用 | 3.4 |
| 8 | mshta 跑 ES6+ 页面；WebView2 无 SDK 拉窗；`swift` 在 CLT 里有没有 | Win11 / 律师 mac | 4.2 |

### 5.4 本票查不到的

- Codex 桌面对 MCP 内容块按 `annotations.audience` 过滤的具体规则（1.2）。
- Codex 桌面把 CLI 写出的本地图片文件内联给人看的通道；`sandbox:` 链接能否内联显示（3.2）。
- Claude Code：含 image 且超 `MAX_MCP_OUTPUT_TOKENS` 时的处理；宿主被杀时子进程下场；`SessionEnd` 与 MCP 关闭的先后；终端 Mermaid 渲染；当前文档里的 "cmd /c" 段落（1.4、2.1、2.3、3.1）。
- Apple CLT 3.9.6 是否带 `_tkinter` 与 `objc`；那句 Tk 弃用警告的出处；`swift` 是否随 CLT；JXA 建 WKWebView 窗（4.1、4.2）。
- Edge `--app` 的微软正式文档；Chromium 官方开关表（抓取 404）；WebView2 仅靠 PowerShell / Python 标准库起窗的官方路径（4.2）。

---

## 6. 来源

**本机源码、二进制字符串与实测**（2026-09-13，Windows 11 Pro 26200）
- Codex 桌面应用包 `C:\Program Files\WindowsApps\OpenAI.Codex_26.908.4834.0_x64__2p2nqsd0c76g0\app\resources\`：`app.asar`（渲染层，`codex.mcpTool.*` 117 条消息 id、MCP 内容块渲染组件、`marked` gfm、mermaid、xterm/node-pty、`integratedTerminalShell` / `defaultTerminalLocation`、`__codex_inline_visualization_*`）、`codex.exe`（三种 `### Visualizations` 段）、`plugins/openai-bundled/`、`owl-app.ini`
- `~/.codex/config.toml`（`[mcp_servers.node_repl]`、`[desktop]`、`[plugins.*]`）；`~/.codex/plugins/cache/openai-bundled/{visualize/1.0.37, codex-app-tools/0.1.4}`（`SKILL.md`、`.codex-plugin/plugin.json`、`.mcp.json`）；`codex features list`、`codex --help`、`codex exec --help`、`codex mcp --help`
- `openai/codex` 源码（标签 `rust-v0.154.0`，main HEAD 2026-09-13 复核）：`codex-rs/protocol/src/models.rs`、`core/src/tools/handlers/mcp.rs`、`core/src/mcp_tool_call.rs`、`core/src/session/handlers.rs`、`codex-mcp/src/{runtime,connection_manager,rmcp_client,plugin_config}.rs`、`rmcp-client/src/{stdio_server_launcher,program_resolver,utils,protocol_mode}.rs`、`config/src/{mcp_types,config_toml,loader/mod}.rs`、`core-plugins/src/manifest.rs`、`core/src/mcp_skill_dependencies.rs`、`ext/skills/src/loader/metadata.rs`、`tui/src/history_cell/{mcp_result,mcp}.rs`、`utils/pty/src/win/job.rs`、`models-manager/models.json`、`features/src/lib.rs`
- `claude.exe` 2.1.270 字符串（MCP 结果渲染、`MAX_MCP_OUTPUT_TOKENS` 默认、超时常量、image MIME 集合）；`raw.githubusercontent.com/anthropics/claude-code/main/CHANGELOG.md`
- `skills` 1.5.26（`npm pack skills@latest`，`dist/cli.mjs`）；本仓库 `scripts/pack-offline.py`、`.claude-plugin/plugin.json`、`.codex-plugin/plugin.json`、`docs/adr/0011`、`docs/agents/skills.md`
- 实测脚本（`docs/research/mcp与cli接通面/`）：`probe_server.py`（零依赖 stdio MCP server，回 text / image / resource_link / resource）、`coldstart.py`、`codex_size.py`、`tui_table.py`（winpty 跑 TUI）、`tk_lifetime.py`、`viz_prompt.py`、`asar_ctx.py`、`asar_near.py`；Claude Code 侧的探针由子代理在 scratchpad 里跑，形状同 `probe_server.py`
- 本机 `python -c "import tkinter"`（3.14.2 / 3.9.25）、`where mshta`、注册表 `HKLM\SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-…}`

**官方一手网页**（全部访问于 2026-09-13）
- OpenAI：`developers.openai.com/codex/*`（308 → `learn.chatgpt.com/docs/extend/mcp`、`/docs/config-file/config-reference`、`/docs/build-skills`、`/docs/integrated-terminal`、`/docs/windows/windows-app`、`/docs/app`）；`developers.openai.com/plugins/build/plugins`；`github.com/openai/codex` issues（第 2.3 节编号）
- Anthropic：`code.claude.com/docs/en/{mcp,plugins-reference,settings,cli-reference,hooks,env-vars,tools-reference,interactive-mode,terminal-config}`；`github.com/anthropics/claude-code` issues（第 2.3 节编号）
- MCP：`modelcontextprotocol.io/specification/2026-07-28`（内容块五种，#126 D.5 已查）
- Python：`docs.python.org/3/library/{tkinter,webbrowser,subprocess}.html`、`docs.python.org/3/using/{mac,windows}.html`、`docs.python.org/3.9/using/windows.html`、`python.org/download/mac/tcltk/`、CPython 3.9 `Lib/webbrowser.py`、`Lib/tkinter/__main__.py`
- pywebview：`pywebview.flowrl.com/guide/installation.html`、`/api/`、`github.com/r0x0r/pywebview`、`pypi.org/pypi/pywebview/json`；wry：`github.com/tauri-apps/wry`（README、Cargo.toml）
- Microsoft Learn：Terminating a Process、HandlerRoutine、Creation of a Console、Job Objects、WebView2 distribution / get-started、HTA（previous-versions ms536496）、IE lifecycle FAQ、Edge kiosk；`pubs.opengroup.org` `_exit()`
- Apple：`developer.apple.com/documentation/xcode/installing-the-command-line-tools`、WKWebView、JavaScript for Automation Release Notes、AppleScript Language Guide `open location`（Apple 在线 `open(1)` man page 已下线）；第三方摘录 `ss64.com/mac/open.html`、`peter.sh/experiments/chromium-command-line-switches/`（仅在一手页面 404 时引用，均已标注）
