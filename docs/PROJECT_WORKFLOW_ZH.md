# CultivateAgent 项目操作手册

状态：使用中  
最后更新：2026-07-07  
English version: [`PROJECT_WORKFLOW.md`](PROJECT_WORKFLOW.md)

这份文档是 CultivateAgent 的中文项目操作手册，给开发者、文献复核者、湿实验
合作者、项目负责人，以及需要接管项目的 Codex、Claude 或其他 AI 使用。

## 1. 文档规范

本手册参考了 Diataxis、Google developer documentation、Microsoft procedure
guidance 和 GitLab documentation style 的写法，采用以下原则：

- 把背景解释、操作步骤、参考信息、当前状态分开。
- 使用稳定阶段编号，避免每次更新都重写整篇文档。
- 每个阶段只放属于该阶段的 checklist。
- review gate 和普通任务分开写。
- 每个关键产物都写清路径和负责人。
- 当前状态集中放在第 9 节，便于持续更新。

更新规则：

- 第 2-8 节只在项目流程变化时修改。
- 第 9 节在每次重要工作后更新。
- 新的科学决策写成单独 decision record，放在 `docs/`。
- AI 不允许覆盖人工复核 notes。

## 2. 项目概述

CultivateAgent 是一个 CLI-first 的培养肉培养基文献挖掘和优化系统。它借鉴
ReactionSeek 的思路：

1. 用 LLM 从论文中抽取结构化事实；
2. 用确定性工具校验、标准化并追溯这些事实；
3. 把证据存入可查询知识库；
4. 针对具体生物目标检索证据；
5. 生成有引用支撑的培养基变量建议；
6. 用多目标贝叶斯优化选择可预注册的湿实验批次。

当前第一阶段湿实验目标：

> 牛 satellite cells / bovine myoblasts 的扩增阶段培养基优化，目标是
> 无血清、优先 animal-component-free、成本敏感，同时保留 myogenic identity。

当前范围边界：

- 范围内：牛肌源细胞扩增阶段的培养基变量。
- 第一轮范围外：支架、微载体、灌流、生物反应器、基因工程、whole-cut
  texture、感官评价、以分化培养基为主的优化。

## 3. 仓库结构

```text
CultivateAgent/
  README.md                         项目总览和 CLI 快速开始
  pyproject.toml                    包配置和 optional dependencies
  requirements.txt                  默认运行依赖
  config/
    config.example.yaml             运行配置模板
  cultivate_agent/
    cli.py                          CLI 入口
    ingest/                         BibTeX、PDF、全文导入
    triage/                         论文初筛和 A/B/C 分层
    extract/                        LLM prompt、JSON 解析、grounding check
    schema/                         A-M 抽取 schema 和 evidence model
    normalize/                      成分名和单位标准化
    kb/                             SQLite 知识库和导出
    retrieve/                       BM25 和可选 embedding retriever
    design/                         有证据支撑的培养基推荐
    optimize/                       搜索空间、代理模型、MOBO 闭环
    evaluate/                       抽取评分和模型一致性
    llm/                            OpenAI、Anthropic、Gemini、mock client
  scripts/
    evaluate_medium_corpus.py       抽取和模型一致性 benchmark
    compare_mobo_backends.py        优化后端对比
  data/
    library.example.bib             BibTeX 示例
    literature/
      bovine_corpus_manifest.tsv    文献 metadata
      bovine_human_review_queue.tsv 人工复核队列
  docs/
    ARCHITECTURE.md                 技术架构
    OPTIMIZATION.md                 优化层设计
    PROJECT_WORKFLOW.md             英文操作手册
    PROJECT_WORKFLOW_ZH.md          本手册
    LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md
    BOVINE_CORPUS_MANIFEST.md
    SESSION_LOG.md
    REVIEW_BY_NEXT_ENGINEER.md
```

当前交付界面：

- CLI 命令：`cultivate ingest`、`cultivate extract`、`cultivate export`、
  `cultivate design`、`cultivate optimize`。
- 数据产物：TSV、CSV、JSONL、SQLite、Markdown。
- 现在没有生产级网页 UI。dashboard 可以以后做，但不是当前交付形式。

## 4. 角色和职责

在任务、review notes、commit 和 handoff 中使用这些标签。

| 标签 | 负责人 | 典型职责 |
|---|---|---|
| `[人工]` | 项目负责人或领域复核者 | 科学判断、范围确认、证据裁决 |
| `[AI]` | Codex、Claude 或其他 AI | 搜索、抽取、编码、表格整理、报告草稿 |
| `[实验]` | 湿实验合作者 | 细胞、试剂、protocol 可行性、实验执行 |
| `[复核]` | 指定 reviewer | gate 检查、冲突解决、claim audit |
| `[记录]` | 任意贡献者 | 可追踪文档更新 |

冲突规则：

- AI 可以准备证据，人类批准科学用途。
- AI 不能覆盖人工 notes。
- 湿实验 design 必须在结果出现前 commit。
- 不能用结果倒改预注册方案。
- 任何 scope 变化都必须有新的 decision record。

## 5. 产物登记表

| 产物 | 路径或预期路径 | 负责人 | 何时更新 |
|---|---|---|---|
| 操作手册 | `docs/PROJECT_WORKFLOW.md`, `docs/PROJECT_WORKFLOW_ZH.md` | `[记录]` | 流程变化或重要状态更新 |
| Session log | `docs/SESSION_LOG.md` | `[AI]` | 每次重要工作后 |
| 湿实验目标决策 | `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md` | `[人工]` + `[AI]` | 目标决策或 scope 变化 |
| 文献 manifest | `data/literature/bovine_corpus_manifest.tsv` | `[AI]` + `[复核]` | 新文献或文献状态变化 |
| 人工复核队列 | `data/literature/bovine_human_review_queue.tsv` | `[人工]` + `[AI]` | 证据复核 |
| Corpus summary | `docs/BOVINE_CORPUS_MANIFEST.md` | `[AI]` | manifest 或 review gate 变化 |
| 抽取评估 | `docs/EVAL_RESULTS.md`, `docs/MODEL_AGREEMENT.md` | `[AI]` | evaluation run 后 |
| 优化评估 | `docs/OPTIMIZATION_BENCHMARK.md` | `[AI]` | optimizer benchmark 后 |
| 证据表 | `data/literature/bovine_evidence_table.tsv` | `[AI]` + `[复核]` | 全文抽取后 |
| 候选变量 | `docs/CANDIDATE_VARIABLES.md` | `[AI]` + `[人工]` | 证据复核后 |
| 设计包 | `docs/wetlab/ROUND_<n>_DESIGN_PACKET.md` | `[AI]` + `[实验]` + `[复核]` | 每轮湿实验前 |
| 结果记录 | `docs/wetlab/ROUND_<n>_RESULTS.md` | `[AI]` + `[实验]` | 每轮湿实验后 |

除非有单独的数据存储规则，不要把大型 PDF、原始图片、SQLite 数据库或仪器原始文件
提交进 git。

## 6. 生命周期总览

| 阶段 | 名称 | 主要产物 | 当前 gate 状态 |
|---|---|---|---|
| S0 | 环境准备 | 可运行仓库 | pass |
| S1 | 目标锁定 | 湿实验目标决策 | pass |
| S2 | 文献 corpus | bovine manifest 和 review queue | partial |
| S3 | 全文抽取 | grounded evidence tables | fail |
| S4 | 人工证据复核 | adjudicated evidence | fail |
| S5 | Search-space 设计 | 有边界的候选变量 | fail |
| S6 | In-silico 稳健性 | 稳定设计依据 | fail |
| S7 | 湿实验预注册 | 已 commit 的 design packet | fail |
| S8 | 湿实验执行 | raw results 和偏差记录 | not started |
| S9 | 结果比较 | processed results 和 Pareto analysis | not started |
| S10 | 闭环更新 | 下一轮设计或停止决策 | not started |
| S11 | 论文审计 | 论文级 claims 和 artifacts | not started |

## 7. 阶段 Checklist

### S0. 环境准备

目的：让仓库可复现、可运行。

Checklist：

- [ ] `[AI]` 创建或激活 Python 环境。
- [ ] `[AI]` 安装依赖和 editable package。
- [ ] `[AI]` 运行单元测试。
- [ ] `[AI]` 运行 smoke pipeline。
- [ ] `[人工]` 确认 API key 策略，以及是否允许 live provider calls。
- [ ] `[记录]` 把失败和修复写入 `docs/SESSION_LOG.md`。

命令：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
.venv/bin/python -m pytest -q
.venv/bin/python -m cultivate_agent.cli smoke
```

Gate S0：测试和 smoke 通过，或 blocker 已记录且有修复计划。

### S1. 目标锁定

目的：避免第一轮湿实验变成无法解释的大而全项目。

Checklist：

- [x] `[AI]` 查阅近年培养肉培养基和细胞生物学文献。
- [x] `[AI]` 提出第一阶段湿实验目标。
- [x] `[复核]` 区分 in-scope 和 out-of-scope。
- [x] `[记录]` 记录决策。

Gate S1：目标和边界已记录。

Scope-change 流程：

- [ ] `[人工]` 说明想改变什么。
- [ ] `[AI]` 收集支持和反对证据。
- [ ] `[复核]` 判断会影响哪些产物和 gate。
- [ ] `[记录]` 先新增 decision record，再改下游文件。

### S2. 文献 Corpus

目的：先建立可追踪文献集合，再做抽取和实验设计。

Checklist：

- [x] `[AI]` 建立 bovine-focused corpus manifest。
- [x] `[AI]` 将记录分类为 `core`、`core_context`、`context`、`defer` 或
  `background`。
- [x] `[AI]` 建立人工复核队列。
- [ ] `[人工]` 确认 P1 core 纳入/排除。
- [ ] `[AI]` 尽可能拉取 P1 全文或 PDF。
- [ ] `[复核]` 检查 DOI、URL、物种、细胞类型、阶段、培养基重点、
  剂量可得性和 endpoints。

Gate S2 湿实验入口条件：

- 35-50 篇 peer-reviewed sources；
- 至少 8 篇近期 review 或 scoping papers；
- 至少 12 篇 primary medium 或 cell-culture papers；
- 至少 10 篇 bovine satellite-cell 或 myoblast 相关；
- 至少 5 篇有可抽取剂量或 range；
- 至少 3 篇报道 serum-free 或 animal-component-free bovine muscle-cell culture；
- background-only 文献不计入湿实验证据。

### S3. 全文抽取

目的：把论文转成结构化、有证据支撑的数据。

Checklist：

- [ ] `[AI]` 导入 BibTeX、PDF 或全文。
- [ ] `[AI]` 对 P1/P2 文献运行 triage 和 extraction。
- [ ] `[AI]` 导出 screening、component、evidence、extraction tables。
- [ ] `[AI]` 记录 extraction coverage 和 grounding rate。
- [ ] `[复核]` 标记稀疏或不可靠的抽取。
- [ ] `[AI]` 只有在证据显示是技术问题时，才修 parser 或 prompt；如果是原文
  缺信息，不要把它当代码问题。

命令：

```bash
cultivate ingest
cultivate triage
cultivate extract --tier A
cultivate export
```

Gate S3：

- top-ranked records 的 evidence quote grounding rate >= 0.95；
- 关键字段 non-missing fraction >= 0.75；
- 每个进入设计空间的成分都能追溯到 source quote 和 normalized component。

### S4. 人工证据复核

目的：把抽取证据变成科学上可使用的证据。

Checklist：

- [ ] `[人工]` 优先复核 `data/literature/bovine_human_review_queue.tsv` 中的
  `H001-H016`。
- [ ] `[人工]` 将每项标为 `supported`、`partial`、`unsupported`、`uncertain`
  或 `defer`。
- [ ] `[人工]` 添加简短 notes：formulation、dose、endpoint、caveat 或排除原因。
- [ ] `[AI]` 把 notes 转成结构化 adjudication table。
- [ ] `[复核]` 解决 AI 抽取和人工阅读的冲突。
- [ ] `[记录]` 更新 `docs/BOVINE_CORPUS_MANIFEST.md`。

建议顺序：

1. Beefy-9 benchmark、FGF2 reduction、albumin dose/cost。
2. Chemically defined bovine medium 和 differentiation capacity。
3. Commercial serum-free medium benchmarks。
4. Spent-media species and cell-type dependence。
5. DOE/RSM bovine serum-free media。
6. Albumin substitutes、protein isolates、hydrolysates。
7. Safety and cost annotations。

Gate S4：进入第一轮设计的所有非 exploratory 变量，都有人类复核支持。

### S5. Search-Space 设计

目的：定义优化器允许改变什么。

Checklist：

- [ ] `[AI]` 根据复核证据建立 candidate variable classes。
- [ ] `[AI]` 给每个变量分配 mechanism class。
- [ ] `[AI]` 添加 cost class、animal-origin status、food-grade plausibility、
  supplier risk。
- [ ] `[人工]` 确认可获得且可接受的试剂。
- [ ] `[实验]` 确认细胞来源、baseline medium、plate format、assay duration、
  throughput。
- [ ] `[复核]` 移除机制不支持、组成不透明或风险不可接受的变量。

候选变量通常限制在 4-6 类，例如：

- basal medium choice or simplification；
- FGF2 concentration；
- insulin、transferrin、selenium axis；
- albumin or albumin substitute；
- lipid or fatty-acid carrier；
- amino-acid or metabolic supplement；
- evidence-gated hydrolysate or extract。

Gate S5：search space 有边界、可控、可采购且有证据支撑。

### S6. In-Silico 稳健性

目的：测试设计是否对检索器和优化器选择稳定。

Checklist：

- [ ] `[AI]` 比较 BM25 和 embedding retrieval 的证据簇。
- [ ] `[AI]` 比较 q-ParEGO 和 qLogNEHVI 的设计建议。
- [ ] `[AI]` 对关键变量类做 leave-one-source-out sensitivity。
- [ ] `[AI]` 生成第一版 candidate formulation table。
- [ ] `[复核]` 检查重复、危险外推、unsupported claims 和 dominated candidates。
- [ ] `[人工]` 批准或修改变量和 controls。

Gate S6：

- top variable classes 在检索和优化扰动下至少 70% 重合；
- 非 exploratory 的关键变量不能只靠一篇论文；
- 分歧已记录；
- 第一轮 batch 包含 controls，且避免近重复候选。

### S7. 湿实验预注册

目的：在结果出现前冻结实验。

Checklist：

- [ ] `[AI]` 起草 design packet。
- [ ] `[实验]` 确认 reagent list 和配制限制。
- [ ] `[实验]` 确认 cell source、passage window、seeding density、
  culture duration、media-change schedule、plate format、replicate count。
- [ ] `[人工]` 确认 primary 和 secondary endpoints。
- [ ] `[复核]` 在任何结果出现前冻结 candidate formulations。
- [ ] `[记录]` commit design packet。

最小 design packet：

- biological target and scope statement；
- 文献纳入/排除标准；
- candidate formulation table；
- positive、negative、baseline controls；
- endpoint definitions；
- replicate plan；
- stopping and failure criteria；
- analysis plan；
- caveats and unsupported claims；
- 支撑每个变量的 exact citations。

Gate S7：design packet 已在湿实验开始前 commit。

### S8. 湿实验执行

目的：按冻结设计执行，不在中途改变问题。

Checklist：

- [ ] `[实验]` 按冻结 protocol 准备细胞和试剂。
- [ ] `[实验]` 记录 plate map、reagent lots、operator、passage number、
  seeding density 和 timing。
- [ ] `[实验]` 保存 raw measurements 和必要 raw images。
- [ ] `[人工]` 立即记录偏离 protocol 的情况。
- [ ] `[复核]` 判断偏离是否导致无效、限定解释或只需备注。
- [ ] `[记录]` commit metadata 和 result manifests。大型原始文件默认放 git 外。

Gate S8：实验完成或停止，并且偏差和 raw data 已记录。

### S9. 结果比较

目的：把实测结果与 controls 和目标比较。

Checklist：

- [ ] `[AI]` 把 raw results 载入结构化表格。
- [ ] `[AI]` 只做 within-experiment normalization。
- [ ] `[AI]` 计算 primary endpoint、secondary endpoints 和 cost estimates。
- [ ] `[AI]` 与 baseline 和 positive controls 比较。
- [ ] `[AI]` 更新 proliferation、cost、identity retention 的 Pareto front。
- [ ] `[人工]` 检查统计结果是否符合生物学解释。
- [ ] `[复核]` 将每个 claim 标为 `supported`、`partial`、`unsupported` 或
  `exploratory`。

Gate S9：结果已处理、比较，且 claim labels 已复核。

### S10. 闭环更新

目的：决定是否以及如何进行下一轮。

Checklist：

- [ ] `[AI]` 把 measured objective values 输入 `optimize.tell()`。
- [ ] `[AI]` 生成下一轮候选或停止建议。
- [ ] `[复核]` 检查模型是在 exploitation、exploration，还是重复失败区域。
- [ ] `[人工]` 决定继续、缩小 search space、增加 assay 或停止。
- [ ] `[记录]` 如果继续，commit round summary 和下一轮 design packet。

Gate S10：下一步行动已记录。

### S11. 论文审计

目的：把系统和实验变成可辩护的论文流程。

Checklist：

- [ ] `[AI]` 生成最终表格：corpus、evidence、variables、formulations、
  results、Pareto comparison、sensitivity checks。
- [ ] `[AI]` 生成图：workflow、evidence map、variable support、
  experimental outcomes、Pareto front、closed-loop trajectory。
- [ ] `[人工]` 写生物学解释和 limitations。
- [ ] `[复核]` 每个 claim 都要能追溯到 evidence 和 wet-lab data。
- [ ] `[复核]` 如实报告 negative 或 inconclusive results。
- [ ] `[记录]` 归档 code commit、data manifests、analysis scripts 和 protocol
  versions。

Gate S11：论文 claims 可追溯到证据和结果。

## 8. 并行工作计划

人工线：

- 复核 `H001-H016`。
- 确认细胞来源和 assay 限制。
- 确认试剂可获得性和预算上限。
- 批准候选变量类。
- 湿实验前签字确认 pre-registration。

AI 线：

- 拉取和整理 P1 全文。
- 抽取 component tables、dose ranges、endpoints、quotes。
- 建立 `data/literature/bovine_evidence_table.tsv`。
- 把人工 notes 转成 adjudicated evidence records。
- 生成 candidate variable classes。
- 跑 retrieval 和 optimizer robustness checks。
- 起草 design packets 和 analysis reports。

实验线：

- 确认细胞来源、passage limits 和培养限制。
- 确认 control media 和 assay protocol。
- 确认 throughput：每轮条件数和重复数。
- 只执行已冻结并 commit 的 design。
- 按约定结构返回 raw results。

## 9. 当前项目记录

重要工作后更新本节。

### 9.1 已完成

- 仓库是 CLI-first Python package。
- 最新验证：`.venv/bin/python -m pytest -q` 为 26 passed，3 个已知 warnings。
- Smoke pipeline 通过。
- Demo optimization loop 通过。
- Extraction evaluator 已有。
- 四篇文献的 offline evaluation fixture 已有。
- Embedding retriever 已有。
- BoTorch qNEHVI 和 qLogNEHVI backend 已有。
- Optional citation verifier 已有。
- Ontology-to-search-space 已覆盖 hydrolysates、extracts、defined supplements、
  albumin substitutes、amino acids、carbon sources、trace elements。
- Extraction evaluation 已支持 live provider mode。
- Parser 支持 A-M block letters 和 schema attribute block names。
- 第一阶段 wet-lab-facing target 已记录。
- Bovine manifest v0 有 44 条记录。
- Human review queue v0 有 30 个 open tasks。
- 英文和中文操作手册已存在。

### 9.2 已知问题

- Live OpenAI/Anthropic extraction 太稀疏，不能算成功 model agreement。
- Gemini live comparison 未完成，因为没有 Gemini/Google key。
- OpenAI raw-response debugging 遇到 insufficient quota。
- 当前 corpus manifest 尚未全文抽取。
- Human review queue 仍未完成。
- Cost、supplier、food-grade annotations 不完整。
- In-silico robustness 尚未在 bovine manifest 上运行。
- 尚未生成或冻结 wet-lab design packet。
- 尚无湿实验结果。

### 9.3 近期下一步

1. `[AI]` 拉取所有 P1 core records 的全文。
2. `[AI]` 抽取 exact formulations、dose ranges、endpoints、quotes。
3. `[人工]` 复核 H001-H016。
4. `[AI]` 建立 adjudicated bovine evidence table。
5. `[复核]` 决定哪些变量可进入第一轮 search space。
6. `[AI]` 只有在前置 gate 通过后，才起草第一版 design packet。

## 10. AI 接管协议

任何 AI 接手时：

1. 读 `README.md`。
2. 读本手册或 `docs/PROJECT_WORKFLOW.md`。
3. 读 `docs/SESSION_LOG.md`。
4. 读 `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md`。
5. 读 `docs/BOVINE_CORPUS_MANIFEST.md`。
6. 运行 `git status --short --branch`。
7. 从下一个未通过 gate 继续。

推荐接管 prompt：

```text
请继续 CultivateAgent，使用 docs/PROJECT_WORKFLOW_ZH.md 作为控制流程。
除非新增 scope-change decision record，否则保持当前 bovine satellite-cell/myoblast
扩增培养基优化目标。先检查 git status，再推进下一个未通过 gate。不要覆盖人工复核 notes。
```
