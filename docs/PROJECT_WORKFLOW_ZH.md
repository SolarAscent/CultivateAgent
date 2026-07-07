# CultivateAgent 项目手册

状态：使用中  
最后更新：2026-07-07  
English version: [`PROJECT_WORKFLOW.md`](PROJECT_WORKFLOW.md)

这是 CultivateAgent 的控制性项目手册，给开发者、文献复核者、湿实验合作者、
项目负责人，以及需要接管同一项目的 Codex、Claude 或其他 AI 使用。它不是日记，
而是让多人和多 AI 不冲突地推进同一个论文项目的操作地图。

## 0. 如何使用本手册

| 你想做什么 | 看哪里 |
|---|---|
| 先理解项目 | 第 1-3 节 |
| 知道谁负责什么 | 第 4 节 |
| 找到该改哪个文件 | 第 5 节 |
| 看完整论文流程 | 第 6 节 |
| 执行某个阶段 | 第 7 节 |
| 让人工、AI、实验队友并行开工 | 第 8 节 |
| 查看当前进度、问题、下一步 | 第 9 节 |
| 把项目交给另一个 AI 或队友 | 第 10 节 |

维护规则：

- 第 1-8 节定义稳定流程，不要因为每日进展频繁改动。
- 第 9 节是当前状态账本，重要工作后更新这里。
- 新的科学决策单独写 decision record，放在 `docs/`。
- `docs/SESSION_LOG.md` 保持时间顺序记录。
- AI 不允许覆盖人工复核 notes。

本结构参考了以下文档写法：

- [Diataxis](https://diataxis.fr/)：区分解释、操作、教程式上手和参考资料。
- [Google developer documentation style guide](https://developers.google.com/style)：
  保持任务导向、清晰一致。
- [Microsoft Learn contributor guide](https://learn.microsoft.com/en-us/contribute/)：
  强调可维护的文档归属和更新流程。
- [GitLab documentation style guide](https://docs.gitlab.com/development/documentation/styleguide/)：
  强调 topic-based、可扫描的文档结构。

## 1. 项目定义

CultivateAgent 是一个 CLI-first 的培养肉培养基文献挖掘和优化系统。它把
ReactionSeek 式流程改造成面向培养肉湿实验的闭环：

1. 收集并初筛文献；
2. 用 LLM 和确定性 grounding check 抽取结构化事实；
3. 标准化成分、剂量、单位、物种、细胞类型和 endpoint；
4. 把证据存入可查询知识库；
5. 针对锁定生物目标检索证据；
6. 生成有引用支撑的培养基假设；
7. 用多目标贝叶斯优化选择有边界的湿实验批次；
8. 比较湿实验结果并进入下一轮闭环。

锁定的第一阶段湿实验目标：

> 牛 satellite cells / bovine myoblasts 的扩增阶段培养基优化，目标是
> 无血清、优先 animal-component-free、成本敏感，同时保留 myogenic identity。

第一轮范围：

| 范围内 | 第一轮范围外 |
|---|---|
| 牛肌源细胞扩增阶段培养基变量 | 支架、微载体、灌流、生物反应器 |
| 无血清和 animal-component-free 证据 | 基因工程和稳定细胞系工程 |
| 成本和供应可行性 | Whole-cut texture 和感官评价 |
| Myogenic identity 保留 endpoint | 以分化培养基为主的优化 |

任何 scope 改动都必须先新增 decision record，再修改下游文件。

## 2. 交付形态

当前交付界面：

- CLI 命令：`cultivate ingest`、`cultivate extract`、`cultivate export`、
  `cultivate design`、`cultivate optimize`。
- 主要产物：Markdown、TSV、CSV、JSONL、SQLite 和评估报告。
- 当前没有生产级网页 UI。以后可以增加 dashboard，但它不是目前默认交付方式。

在第 7 节和第 9 节的证据与设计 gate 通过前，不能进入湿实验。

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
    ingest/                         BibTeX、PDF、全文和 structured-paper 导入
    triage/                         论文初筛和 A/B/C 分层
    extract/                        LLM prompt、JSON 解析、grounding check
    schema/                         A-M schema、evidence model、structured paper objects
    normalize/                      成分名和单位标准化
    kb/                             SQLite 知识库和导出
    retrieve/                       BM25 和可选 embedding retrieval
    design/                         有证据支撑的培养基推荐
    optimize/                       搜索空间、代理模型、MOBO 闭环
    evaluate/                       抽取评分和模型一致性
    llm/                            OpenAI、Anthropic、Gemini、mock clients
  scripts/
    evaluate_medium_corpus.py       抽取和模型一致性 benchmark
    compare_mobo_backends.py        优化后端对比
  data/
    library.example.bib             BibTeX 示例
    literature/
      bovine_corpus_manifest.tsv    牛相关文献 metadata
      bovine_human_review_queue.tsv 人工复核队列
      ai_for_science_method_sources.tsv 方法文献登记表
  docs/
    PROJECT_WORKFLOW.md             英文手册
    PROJECT_WORKFLOW_ZH.md          本手册
    SESSION_LOG.md                  时间顺序工作记录
    ARCHITECTURE.md                 技术架构
    OPTIMIZATION.md                 优化层设计
    AI_FOR_SCIENCE_METHOD_REVIEW.md AI-for-science 方法综述
    LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md
    BOVINE_CORPUS_MANIFEST.md
    REVIEW_BY_NEXT_ENGINEER.md
```

## 4. 角色和决策权

在任务、review notes、commit 和 handoff 中使用这些标签。

| 标签 | 角色 | 决策权 |
|---|---|---|
| `[人工]` | 项目负责人或领域复核者 | 生物目标、证据裁决、湿实验 go/no-go |
| `[AI]` | Codex、Claude 或其他 AI | 搜索、抽取、编码、报告草稿、结构化表格 |
| `[实验]` | 湿实验合作者 | 细胞来源、试剂可行性、protocol 执行 |
| `[复核]` | 指定 reviewer | Gate 检查、冲突解决、claim audit |
| `[记录]` | 任意贡献者 | 可追踪文档更新 |

规则：

- AI 可以准备证据，人类批准科学用途。
- AI 必须记录不确定性，不能编造缺失数据。
- AI 不能覆盖人工 notes。
- 湿实验 design packet 必须在结果出现前 commit。
- 不能用结果倒改预注册方案。
- 大型 PDF、原始图片、SQLite 数据库和仪器原始文件默认不进 git，除非另有
  存储规则。

## 5. 产物登记表

| 产物 | 路径 | 负责人 | 何时更新 |
|---|---|---|---|
| 项目手册 | `docs/PROJECT_WORKFLOW.md`, `docs/PROJECT_WORKFLOW_ZH.md` | `[记录]` | 流程变化或重要状态更新 |
| 时间顺序日志 | `docs/SESSION_LOG.md` | `[AI]` | 每次重要工作后 |
| 湿实验目标决策 | `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md` | `[人工]` + `[AI]` | 目标或 scope 变化 |
| 文献 manifest | `data/literature/bovine_corpus_manifest.tsv` | `[AI]` + `[复核]` | 文献状态变化 |
| 人工复核队列 | `data/literature/bovine_human_review_queue.tsv` | `[人工]` + `[AI]` | 证据裁决 |
| Corpus summary | `docs/BOVINE_CORPUS_MANIFEST.md` | `[AI]` | Manifest 或 gate 变化 |
| 方法文献登记表 | `data/literature/ai_for_science_method_sources.tsv` | `[AI]` + `[复核]` | 算法或 pipeline 决策 |
| 方法综述 | `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md` | `[AI]` + `[复核]` | 方法决策 |
| 抽取评估 | `docs/EVAL_RESULTS.md`, `docs/MODEL_AGREEMENT.md` | `[AI]` | Evaluation run 后 |
| 优化评估 | `docs/OPTIMIZATION_BENCHMARK.md` | `[AI]` | Optimizer benchmark 后 |
| 证据表 | `data/literature/bovine_evidence_table.tsv` | `[AI]` + `[复核]` | 全文抽取和复核后 |
| 候选变量 | `docs/CANDIDATE_VARIABLES.md` | `[AI]` + `[人工]` | 证据复核完成后 |
| 湿实验设计包 | `docs/wetlab/ROUND_<n>_DESIGN_PACKET.md` | `[AI]` + `[实验]` + `[复核]` | 每轮湿实验前 |
| 湿实验结果 | `docs/wetlab/ROUND_<n>_RESULTS.md` | `[AI]` + `[实验]` | 每轮湿实验后 |

## 6. 生命周期总览

| 阶段 | 名称 | 主要产物 | 当前状态 |
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

只有当 gate 满足，或 blocker 被明确记录后，才允许推进到下一阶段。

## 7. 阶段 Checklist

### S0. 环境准备

目的：让仓库可复现、可运行。

Checklist：

- [ ] `[AI]` 创建或激活 Python 环境。
- [ ] `[AI]` 安装依赖和 editable package。
- [ ] `[AI]` 运行单元测试。
- [ ] `[AI]` 运行 smoke pipeline。
- [ ] `[AI]` 运行 demo optimization。
- [ ] `[人工]` 确认 live provider 的 API key 策略。
- [ ] `[记录]` 把失败和修复写入 `docs/SESSION_LOG.md`。

命令：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
.venv/bin/python -m pytest -q
.venv/bin/python -m cultivate_agent.cli smoke
.venv/bin/python -m cultivate_agent.cli optimize --demo --rounds 6
```

Gate：测试、smoke 和 demo optimization 通过，或 blocker 已记录且有修复计划。

### S1. 目标锁定

目的：避免第一轮湿实验变成太宽、无法解释的问题。

Checklist：

- [x] `[AI]` 查阅近期培养肉培养基和细胞生物学文献。
- [x] `[AI]` 提出第一阶段湿实验目标。
- [x] `[复核]` 区分 in-scope 和 out-of-scope。
- [x] `[记录]` 把目标写入 decision record。

Gate：目标、边界和 scope-change 规则已记录。

### S2. 文献 Corpus

目的：先建立可追踪文献集合，再做抽取和实验设计。

Checklist：

- [x] `[AI]` 建立 bovine-focused corpus manifest。
- [x] `[AI]` 将记录分类为 `core`、`core_context`、`context`、`defer` 或
  `background`。
- [x] `[AI]` 建立人工复核队列。
- [ ] `[人工]` 确认 P1 core 纳入和排除。
- [ ] `[AI]` 尽可能拉取 P1 全文或 PDF。
- [ ] `[复核]` 检查 DOI、URL、物种、细胞类型、阶段、培养基重点、
  剂量可得性和 endpoints。

湿实验入口 gate：

- 35-50 篇 peer-reviewed sources 已整理。
- 至少 8 篇近期 review 或 scoping papers。
- 至少 12 篇 primary medium 或 cell-culture papers。
- 至少 10 篇 bovine satellite-cell 或 myoblast 相关。
- 至少 5 篇有可抽取剂量或 range。
- 至少 3 篇报道 serum-free 或 animal-component-free bovine muscle-cell
  culture。
- Background-only 文献不计入湿实验证据。

### S3. 全文抽取

目的：把论文转成结构化、有证据支撑的数据。

Checklist：

- [ ] `[AI]` 导入 BibTeX、PDF、全文或外部生成的 structured paper 文件。
- [ ] `[AI]` 可用时优先使用结构化解析：GROBID TEI、structured text sections
  或未来 PDF backend。
- [ ] `[AI]` 对 P1/P2 文献运行 triage 和 extraction。
- [ ] `[AI]` 导出 screening、component、evidence、extraction tables。
- [ ] `[AI]` 记录 extraction coverage、non-missing fields 和 grounding rate。
- [ ] `[复核]` 标记稀疏或不可靠抽取。
- [ ] `[AI]` 只有在证据显示是技术问题时，才修 parser 或 prompt；如果原文缺失，
  不要把它当代码问题。

命令：

```bash
cultivate ingest
cultivate triage
cultivate extract --tier A
cultivate export
```

Gate：

- Top-ranked records 的 evidence quote grounding rate >= 0.95。
- Species、cell type、stage、medium type、serum-free status、component
  identity、dose/range、endpoint 的 non-missing fraction >= 0.75。
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

建议复核顺序：

1. Beefy-9 benchmark、FGF2 reduction、albumin dose/cost。
2. Chemically defined bovine medium 和 differentiation capacity。
3. Commercial serum-free medium benchmarks。
4. Spent-media species and cell-type dependence。
5. DOE/RSM bovine serum-free media。
6. Albumin substitutes、protein isolates、hydrolysates。
7. Safety and cost annotations。

Gate：进入第一轮设计的所有非 exploratory 变量都有人工复核支持。

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

Gate：search space 有边界、可控、可采购且有证据支撑。

### S6. In-Silico 稳健性

目的：测试设计是否对检索器和优化器选择稳定。

Checklist：

- [ ] `[AI]` 比较 BM25 和 embedding retrieval 的证据簇。
- [ ] `[AI]` 比较 q-ParEGO 和 qLogNEHVI 的设计建议。
- [ ] `[AI]` 对关键变量类做 leave-one-source-out sensitivity。
- [ ] `[AI]` 生成第一版 candidate formulation table。
- [ ] `[复核]` 检查重复、危险外推、unsupported claims 和 dominated candidates。
- [ ] `[人工]` 批准或修改变量和 controls。

Gate：

- Top variable classes 在检索和优化扰动下至少 70% 重合。
- 非 exploratory 的关键变量不能只靠一篇论文。
- 分歧已记录。
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

- Biological target and scope statement。
- 文献纳入/排除标准。
- Candidate formulation table。
- Positive、negative、baseline controls。
- Endpoint definitions。
- Replicate plan。
- Stopping and failure criteria。
- Analysis plan。
- Caveats and unsupported claims。
- 支撑每个变量的 exact citations。

Gate：design packet 已在湿实验开始前 commit。

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

Gate：实验完成或停止，并且偏差和 raw data 已记录。

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

Gate：结果已处理、比较并复核。

### S10. 闭环更新

目的：决定是否以及如何进行下一轮。

Checklist：

- [ ] `[AI]` 把 measured objective values 输入 `optimize.tell()`。
- [ ] `[AI]` 生成下一轮候选或停止建议。
- [ ] `[复核]` 检查模型是在 exploitation、exploration，还是重复失败区域。
- [ ] `[人工]` 决定继续、缩小 search space、增加 assay 或停止。
- [ ] `[记录]` 如果继续，commit round summary 和下一轮 design packet。

Gate：下一步行动已记录。

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

Gate：论文 claims 可追溯到证据和结果。

## 8. 并行工作协议

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
- Gate 通过后起草 design packets 和 analysis reports。

实验线：

- 确认细胞来源、passage limits 和培养限制。
- 确认 control media 和 assay protocol。
- 确认 throughput：每轮条件数和重复数。
- 只执行已冻结并 commit 的 design。
- 按约定结构返回 raw results。

并行规则：人工复核、AI 抽取可靠性加固、实验可行性确认可以同时进行。湿实验执行
必须等 S7 通过。

## 9. 当前项目账本

重要工作后更新本节。不要把状态更新散落到前面的流程定义里。

### 9.1 阶段账本

| 阶段 | 已完成 | 未解决问题 | 下一步 |
|---|---|---|---|
| S0 | Package 可安装，测试通过，smoke 通过，demo optimization 通过 | Provider credentials 和 quota 属于外部条件 | 每次改动后保持 gate 绿色 |
| S1 | Wet-lab target 和边界已记录 | 除非新 decision record，否则 scope 不能漂移 | 保持 bovine expansion-medium focus |
| S2 | 44 条 bovine manifest 和 30 项 review queue 已建 | P1 人工复核和全文获取未完成 | 人工复核 H001-H016；AI 拉取 P1 全文 |
| S3 | Structured paper schema、plain-text fallback、section routing、GROBID TEI parser 已有 | PDF-to-TEI service/client 未实现；corpus 尚未全文抽取 | 增加 PDF-to-structured backend 并跑 P1 extraction |
| S4 | Review queue 已有 | 尚无 adjudicated evidence table | 把人工 notes 转成结构化 adjudication |
| S5 | Ontology 可把更多 component classes 暴露给 search space | Candidate variables 未批准 | 只在 S3-S4 gate 后建立 |
| S6 | MOBO backend 和 benchmark script 已有 | 尚未在 bovine evidence 上跑 robustness | S5 后跑 retrieval 和 optimizer sensitivity |
| S7 | Pre-registration 格式已定义 | 尚无冻结 design packet | 证据和稳健性 gate 后起草 |
| S8 | 执行记录要求已定义 | 尚无湿实验 | 等 S7 |
| S9 | 分析要求已定义 | 尚无湿实验结果 | 等 S8 |
| S10 | 闭环更新要求已定义 | 尚无 measured objectives | 等 S9 |
| S11 | 论文审计要求已定义 | 尚无最终 claims 或 figures | 等 validated results |

### 9.2 已完成的技术工作

- 仓库是 CLI-first Python package。
- 最新验证：`.venv/bin/python -m pytest -q` 为 29 passed，3 个已知 warnings。
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
- Structured-paper schema 和 plain-text fallback 已有。
- Extractor 可以根据 structured sections 路由不同 block 的上下文，并记录 routing
  metadata。
- 已能把外部 GROBID 生成的 TEI XML 解析为 `StructuredPaper`。

### 9.3 已完成的文献和计划工作

- 第一阶段 wet-lab-facing target 已记录。
- Bovine manifest v0 有 44 条记录。
- Human review queue v0 有 30 个 open tasks。
- AI-for-science 方法综述已存在。
- 方法文献登记表已覆盖 autonomous labs、scientific RAG、information extraction、
  document parsing、ETL 和 Bayesian optimization。
- 当前方法决策：在生成新的湿实验设计前，优先提高 S3 全文抽取可靠性。

### 9.4 已知 blocker 和风险

- Live OpenAI/Anthropic extraction 太稀疏，不能算成功 model agreement。
- Gemini live comparison 未完成，因为没有 Gemini/Google key。
- OpenAI raw-response debugging 遇到 insufficient quota。
- 当前 corpus manifest 尚未全文抽取。
- Optional GROBID service/client 执行尚未实现；当前只支持解析已有
  GROBID-flavored TEI XML 和 plain text。
- Human review queue 仍未完成。
- Cost、supplier、food-grade annotations 不完整。
- In-silico robustness 尚未在 bovine manifest 上运行。
- 尚未生成或冻结 wet-lab design packet。
- 尚无湿实验结果。

### 9.5 近期下一步

1. `[AI]` 增加 optional GROBID service/client 执行或其他 structured PDF backend，
   用于从 PDF 生成 TEI。
2. `[AI]` 拉取所有 P1 core records 的全文。
3. `[AI]` 抽取 exact formulations、dose ranges、endpoints、quotes。
4. `[人工]` 复核 `H001-H016`。
5. `[AI]` 建立 adjudicated bovine evidence table。
6. `[复核]` 决定哪些变量可进入第一轮 search space。
7. `[AI]` 只有在前置 gate 通过后，才起草第一版 design packet。

## 10. AI 接管协议

任何 AI 接手时：

1. 读 `README.md`。
2. 读本手册或 `docs/PROJECT_WORKFLOW.md`。
3. 读 `docs/SESSION_LOG.md`。
4. 读 `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md`。
5. 读 `docs/BOVINE_CORPUS_MANIFEST.md`。
6. 运行 `git status --short --branch`。
7. 从第 9.1 节的下一个未通过 gate 继续。

推荐接管 prompt：

```text
请继续 CultivateAgent，使用 docs/PROJECT_WORKFLOW_ZH.md 作为控制手册。
除非新增 scope-change decision record，否则保持当前 bovine satellite-cell/myoblast
扩增培养基优化目标。先检查 git status，再推进下一个未通过 gate。不要覆盖人工复核
notes，也不要编造缺失证据。
```
