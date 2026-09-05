# ask-matt 路由 skill 的写法、功能与作用

> **写于** 2026-09-05，供 #7「路由的定位机制」参考。起手件把本项目的路由定为「ask-matt 型只读路由」，本文把 ask-matt 拆开看：它是怎么写的、干什么、不干什么、已知哪里会坏，最后映射到本项目的路由。
> **来源等级**：只读一手来源，全部是本机已装的 `mattpocock-skills` 插件 1.2.3 版原文（缓存于 `~/.claude/plugins/cache/claude-plugins-official/mattpocock-skills/1.2.3/`）：`skills/engineering/ask-matt/SKILL.md`、同目录 `PHASE-BOUNDARIES.md` 与 `agents/openai.yaml`、`docs/engineering/ask-matt.md`（面向人的说明页）、`.agents/invocation.md`、`.agents/writing-docs.md`、`skills/productivity/writing-for-agents/SKILL-MECHANICS.md`、`CLAUDE.md`、`CHANGELOG.md`、`.claude-plugin/plugin.json`。未访问网络。
> **红线**：不含任何案件材料。

---

## 1. 一句话

`ask-matt` 是一张**手写的、只推荐不触发的、用户亲手调用的**skill 地图。你描述处境，它告诉你该打哪个 skill、按什么顺序、中间哪几步要人拍板，然后**停下**。它不读你装了什么，只认作者自己那一套。

## 2. 写法解剖

### 2.1 文件形态

| 文件 | 大小 | 作用 |
| --- | --- | --- |
| `SKILL.md` | 11.5 KB | 地图本体，全部是散文 + 编号步骤 |
| `PHASE-BOUNDARIES.md` | 4.3 KB | 被 SKILL.md 指向的展开文件：五选一的决策树与理由 |
| `agents/openai.yaml` | 5 行 | Codex 侧元数据 |

三个文件，没有脚本，没有模板，没有资源目录。

### 2.2 frontmatter 与 Codex 对应物

```yaml
---
name: ask-matt
description: Ask which skill or flow fits your situation. A router over the skills in this repo.
disable-model-invocation: true
---
```

```yaml
# agents/openai.yaml
interface:
  display_name: "Ask Matt"
  short_description: "Find the right skill or workflow"
policy:
  allow_implicit_invocation: false
```

要点：

- **用户亲手调用**。`disable-model-invocation: true` 与 `allow_implicit_invocation: false` 成对出现，两边 harness 同步；`.agents/invocation.md` 的规则是「一个 skill 在两边要么都是用户调用，要么都不是」。
- **description 面向人，不面向模型**。因为模型看不见它，description 不写触发词清单（「Use when the user says…」），只写一句给人浏览斜杠命令时读的话。
- **代价是零上下文占用、但要人记得它存在**。`SKILL-MECHANICS.md` 把这个取舍说透：用户调用的 skill 不占模型的常驻上下文，但「你就是那份索引」。当用户调用的 skill 多到记不住，就用一个**路由 skill** 来治：一个 skill 记住其他所有，人只需记一个。

### 2.3 正文结构

开头一句：「You don't remember every skill, so ask.」然后用一段定义**词汇**：**flow** 是穿过若干 skill 的一条路；大多数路走在一条 **main flow** 上；两条 **on-ramp** 汇入主线；其余是 **standalone**，或者是垫在底下的 **vocabulary layer**。这四个词就是全篇的骨架，后面每个 `##` 各占一个：

| 节 | 内容形态 | 写法特征 |
| --- | --- | --- |
| The main flow: idea → ship | 编号 1–3 步，步内有「Branch:」分叉 | 每个分叉是一个**可判定的问题**（「能不能全在对话里解决」「跨不跨会话」），不是偏好 |
| Context hygiene | 两段散文 | 说清哪几步必须在同一个上下文窗口里，为什么 |
| On-ramps | 三个加粗条目 | 每条是「处境 → skill」，并说明它之后怎么汇入主线 |
| Codebase health | 一条 | 周期性维护 |
| Vocabulary underneath | 两条 | 模型可调用的参考层，其他 skill 会自动拉进来 |
| Phase boundaries | 五个选项 + 指向展开文件 | 有序决策树，「第一个 yes 胜出」 |
| Standalone | 十来条 | 每条一段，都写明**与最近邻居的分界线** |
| Precondition | 一条 | 先跑 setup |

### 2.4 反复出现的写作手法

1. **每条都写分界线，不只写用途**。典型句式是「X 还是 Y，取决于 Z」：`grill-me` 还是 `grill-with-docs` 取决于有没有工作目录；`grill-with-docs` 还是 `wayfinder` 取决于一个会话装不装得下。说明页把这条列为验收项：「两个 skill 相近时，它说该用哪个、为什么另一个不对」。
2. **把人拍板的位置写进路线**。主线里明确「读审查」「确认」在哪一步；说明页的验收项是「它给回来的路线提到在哪里 clear 或 compact、在哪里要你审，而不只是一串 skill 名」。
3. **模糊选择用有序树，不用列表**。Phase boundaries 五选一：按顺序问五个问题，第一个 yes 胜出，`/compact` 放在最底下当默认，理由单独放在 `PHASE-BOUNDARIES.md` 里。这是「用顺序替代判断」的写法：问题本身仍有品味成分，但**按顺序问**就够了。
4. **skill 名当标签写，不当指令写**。`.agents/invocation.md` 专门区分：其他 skill 里的「去跑 X」必须写成「Call the Skill tool with "X"」才会真的触发；而路由散文里的 `/skill` 只是给人看的标签，**不是在触发任何东西**，所以保留斜杠写法。
5. **长理由外置**。SKILL.md 只放结论与顺序，展开的推理放进被指向的 `PHASE-BOUNDARIES.md`；说明页也说 SKILL.md 「不复述步骤，人选工具不需要 runbook」。
6. **散文，不是清单**。作者自己在说明页记录了投诉：路由大半是确定性的，散文难扫读。他的辩护是散文承载的是**条件的那一半**（分叉、人在哪拍板、何时清上下文），扁平清单恰好会丢掉这些；想要压缩版就直接说「只给我顺序」。

### 2.5 维护规则

`CLAUDE.md` 里写死一条：凡新增、改名、删除某个用户可达的 skill，或改了它在流程里的位置，必须重读 `ask-matt/SKILL.md` 并更新，「一个从没提到新 skill、或仍指向已删 skill 的路由，是一个撒谎的路由」。CHANGELOG 显示这条规则是在 #406 补齐五个漏掉的 skill 之后加的；#763 又补了两个从未提到的（`grilling`、`resolving-merge-conflicts`）。**手写地图必然滞后**，作者靠规则而不是靠扫描来对冲。

配套地，每个 skill 的说明页 `## Where it fits` 一节都必须链回 `ask-matt`，「让每页都是一个节点，永远不必自己重画整张图」。图只画一次，画在路由里。

## 3. 功能与作用

### 3.1 它做什么

- **把处境放到一条路的某一步上**。说明页强调：这和「按关键词匹配一个 skill」是两种不同的答案。四类路（主线、汇入线、独立件、底层词汇）全在 skill 里带着。
- **只推荐，然后停**。不 grill、不写 spec、不开文件、不触发它刚点名的 skill；给回来的是「下一句该打什么」，你自己打。
- **手写的一套之内的地图**。不扫描本机装了什么，不覆盖你自己或别人写的 skill；三次有人提议「读本地 `skills/` 目录自动推荐」，都被明确拒绝。

### 3.2 它靠什么原理成立

- **不变量：用户调用的 skill 无法被任何其他 skill 触发**，包括路由。所以「只提示不触发」不是设计偏好，是机制上的必然（`invocation.md`）。
- **路由是二手来源**。说明页最后一句：「路由与某个 `SKILL.md` 不一致时，`SKILL.md` 是对的」。

### 3.3 说明页给的验收项（原文五条，可直接当测试）

1. 结尾点名该打什么，然后停，不自己开工。
2. 给回的路线提到在哪清/压上下文、在哪要人审，不只是 skill 名单。
3. 两个相近 skill，说清用哪个、另一个为什么不对。
4. 凡对另一个 skill 行为的断言，追踪里能看到它真的去读了那个 `SKILL.md`。
5. 你在答案里认出自己的处境，而不是最近似的通用场景。

## 4. 已知缺陷（作者自己记录、未修）

| 缺陷 | 机理 | 对本项目的含义 |
| --- | --- | --- |
| 声称「一半 skill 没装」 | 被路由指向的 skill 多数标了 `disable-model-invocation: true`，harness 注入给模型的 skill 列表里没有它们，模型把列表当成全集，报「未安装」。曾有会话因此把整条 spec 流程判为不存在。 | 与 #11 研究结论同源：**路由必须自持编排 skill 清单**，并且要明说「这些入口存在，即使不在你看到的列表里」。 |
| 描述了某 skill 并不具备的行为 | 路由按自己对每个 skill 的一行摘要作答，从不主动打开对方的 `SKILL.md`；一次会话记录到三处，包括凭「turn the thread into a spec」这句摘要建议跳过 `to-spec`。 | 路由持有的清单要**短到不会撒谎**：只放名字、一句用途、参数；凡涉及对方行为的断言，让路由去读对方原文。 |
| 散文难扫读 | 见 §2.4 第 6 条 | 律师侧的三问答案应当是**固定形状**（表或三行），地图部分才用散文。 |
| 手写滞后 | 靠 `CLAUDE.md` 维护规则对冲 | 本项目同样要一条「改 skill 清单必改路由」的规则，落点在 skill 清单票之后。 |
| 建议用户改 `SKILL.md` | 插件安装是只读的，更新会覆盖 | 律师侧的个性化不能落在 skill 文件里。 |

## 5. 映射到本项目的路由

`CONTEXT.md`「路由」条：随时可调用的只读地图，根据提示词回答当前节点、上一完成、下一任务，需要能力时指向 skill 并帮编排提示词，不触发 skill。与 ask-matt 相比，**同**与**异**各一半：

### 5.1 照搬的

- 用户亲手调用、两边 harness 成对标记、description 面向人。
- 只推荐然后停；输出是「下一句该打什么」。
- 自持清单；skill 名当标签写。
- 每个入口写分界线（生成还是重出、确认还是不适用、节点不适用还是模块不适用）。
- 把律师拍板的位置写进路线（读审查报告 → 确认或再出一版）。
- 长理由外置到被指向的文件；维护规则写进 `AGENTS.md`（等 skill 清单票之后）。
- 五条验收项原样可用，第 4 条（断言行为前先读对方原文）尤其要保留。

### 5.2 本项目多出来的一层

ask-matt 是**无状态**的：它的全部输入是你描述的处境。本项目的路由在同一张静态地图之上多了一层**读图定位**：先读案件图，案件图里没有的按「领域」名读领域图，由数组顺序与条目推出的状态回答三问，再从三问的第一项推出该打的入口。原型（`prototype/路由定位` 分支）验证的正是这一层；ask-matt 对这一层没有可借的写法，只有可借的**输出形状**：答案 = 你在哪一步 + 下一句该打什么 + 你要拍板的点。

### 5.3 一处要提前决定的差异

ask-matt 把 phase boundaries 这类**模糊选择**写成有序决策树。本项目路由里对应的模糊选择是「下一任务从领域图里挑哪一个」（原型里的「最早未做」与「当前之后」两策略）。若这条最终不能靠图里的事实判定，照 ask-matt 的办法：定顺序、写理由、外置到展开文件，而不是留给模型临场判断。
