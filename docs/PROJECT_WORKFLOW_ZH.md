# CultivateAgent 项目流程手册

状态：使用中
最后更新：2026-07-08
English version: [`PROJECT_WORKFLOW.md`](PROJECT_WORKFLOW.md)

这是 CultivateAgent 的控制性流程手册，给开发者、文献复核者、湿实验合作者、
项目负责人，以及需要接管同一论文项目的 Codex、Claude 或其他 AI 使用。目标是
让多人和多 AI 能看懂同一个项目、接同一个流程、更新同一套记录，而不互相覆盖。

## 0. 文档维护约定

本手册把“稳定流程”和“当前进度”分开，避免越写越像流水账。

| 章节 | 用途 | 更新频率 |
|---|---|---|
| 0-4 | 项目定位、边界、仓库结构、职责权限 | 很少更新；只有项目结构或决策权变化时改 |
| 5-6 | 完整论文流程和每阶段 gate | gate、必需产物或 review 规则变化时改 |
| 7 | 人工、AI、实验线并行方式 | 团队分工变化时改 |
| 8 | 当前项目账本 | 重要工作完成后更新 |
| 9 | AI/队友接管协议 | 接管入口变化时改 |

每天或每次 session 的详细历史写在 [`SESSION_LOG.md`](SESSION_LOG.md)。新的科学
判断或方法学选择，应单独写 decision record 放在 `docs/`。人工复核 notes 不能被
AI 生成内容覆盖。

本次重写参考的文档规范：

- [Google developer documentation style guide](https://developers.google.com/style)：
  面向开发者的清晰、一致技术文档，并且项目内规则优先。
- [Microsoft Writing Style Guide](https://learn.microsoft.com/en-us/style-guide/welcome/)：
  面向混合技术读者的简洁写法。
- [Microsoft reference documentation guidance](https://learn.microsoft.com/en-us/style-guide/developer-content/reference-documentation)：
  用稳定标题和一致结构帮助开发者快速定位事实。
- [Diataxis](https://diataxis.fr/start-here/)：区分解释、操作指南、参考资料和
  教学内容。
- [GOV.UK user-needs guidance](https://guidance.publishing.service.gov.uk/writing-to-gov-uk-standards/plan-manage-content/identify-user-needs/)：
  围绕真实用户任务和 acceptance criteria 写内容。

## 1. 项目一页说明

CultivateAgent 是一个 CLI-first 的培养肉培养基文献挖掘和优化系统。它把
ReactionSeek 式科学文献挖掘思路改造成面向培养基湿实验的流程：

```text
ingest -> triage -> extract -> normalize -> knowledge base -> retrieve -> design -> optimize
```

系统不会把跨论文 outcome 数值当作可直接比较的训练标签。文献证据用于定义搜索
区域、先验、限制条件和候选方案理由；优化目标值必须来自本项目自己的湿实验结果，
并通过闭环 `tell()` 路径进入优化器。

已锁定的第一阶段湿实验目标：

> 牛 satellite cells / bovine myoblasts 扩增阶段培养基优化；目标是无血清、
> 优先 animal-component-free、成本敏感，同时保留 myogenic identity。

第一轮范围：

| 范围内 | 除非新 decision record 批准，否则范围外 |
|---|---|
| 牛肌源细胞扩增阶段培养基变量 | 支架、微载体、灌流、生物反应器优化 |
| 无血清和 animal-component-free 培养基证据 | 基因工程和稳定细胞系工程 |
| 剂量/range、endpoint、成本、供应可行性 | Whole-cut texture、感官评价、产品配方 |
| Myogenic identity 保留 endpoint | 以分化培养基为主的优化 |

任何 scope 改动都必须先新增 decision record，再修改下游文件。

## 2. 交付形态

当前交付是本地、文件化、CLI-first。

| 交付面 | 当前状态 |
|---|---|
| CLI | `cultivate ingest`、`triage`、`extract`、`evidence`、`evidence-audit`、`review-packet`、`export`、`design`、`optimize` |
| 文件产物 | Markdown 报告、TSV/CSV 表格、JSON/JSONL 记录、SQLite 知识库 |
| 网页 UI | 当前没有实现，也不是本阶段论文流程必需项 |
| 湿实验入口 | 在证据、人工复核、search-space、稳健性和预注册 gate 通过前保持阻塞 |

README 是快速开始；本文件是操作手册；session log 是时间顺序记录。

## 3. 仓库结构

```text
CultivateAgent/
  README.md                         项目总览和 CLI 快速开始
  pyproject.toml                    包配置和 optional dependencies
  requirements.txt                  默认运行依赖
  config/
    config.example.yaml             运行配置模板
    ontology/                       成分 ontology seed 和 normalization hooks
  cultivate_agent/
    cli.py                          CLI 入口
    ingest/                         BibTeX、PDF、全文、GROBID TEI 导入
    triage/                         论文初筛和 A/B/C 分层
    extract/                        prompt、operator extraction、grounding checks
    schema/                         A-M schema、evidence model、paper objects
    normalize/                      成分名和单位标准化
    kb/                             SQLite store 和 export helpers
    evidence/                       effect extraction、synthesis、audit、review packet
    retrieve/                       BM25 和可选 embedding retrieval
    design/                         有证据支撑的培养基推荐
    optimize/                       搜索空间、代理模型、MOBO 闭环
    evaluate/                       抽取评分和模型一致性
    llm/                            provider-agnostic LLM clients 和 mock client
  scripts/
    ingest_pdfs.py                  无 BibTeX 时导入 loose PDF folders/lists
    run_evidence_parallel.py        并行 evidence extraction helper
    evaluate_medium_corpus.py       抽取和 provider-agreement benchmark
    compare_mobo_backends.py        优化后端对比
  data/literature/
    bovine_corpus_manifest.tsv      牛相关文献 metadata
    bovine_human_review_queue.tsv   人工裁决队列
    ai_for_science_method_sources.tsv 方法文献登记表
  docs/
    PROJECT_WORKFLOW.md             英文手册
    PROJECT_WORKFLOW_ZH.md          本手册
    AI_COLLABORATION_PROTOCOL.md    Codex/Claude 并行协作协议
    SESSION_LOG.md                  时间顺序工作日志
    ARCHITECTURE.md                 技术架构
    OPTIMIZATION.md                 优化层设计
    EVIDENCE_SYNTHESIS.md           随机效应证据综合设计
    BOVINE_CORPUS_MANIFEST.md       corpus 状态和 gate
    EVIDENCE_AUDIT_PROLIFERATION.md 当前保守 wet-lab-entry audit
    HUMAN_REVIEW_PACKET_H001_H016.md 第一批人工复核定位包
    LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md 第一阶段目标决策
    AI_FOR_SCIENCE_METHOD_REVIEW.md 方法综述和算法路线
```

## 4. 角色、权限和产物

在 issue、notes、表格、commit 和 handoff 中使用这些标签。

| 标签 | 角色 | 决策权 |
|---|---|---|
| `[HUMAN]` | 项目负责人或领域复核者 | 生物目标、证据裁决、湿实验 go/no-go |
| `[AI]` | Codex、Claude 或其他 AI | 搜索、抽取、编码、报告草稿、结构化表格 |
| `[LAB]` | 湿实验合作者 | 细胞来源、试剂可行性、protocol 执行 |
| `[REVIEW]` | 指定 reviewer | Gate 检查、冲突解决、claim audit |
| `[DOC]` | 任意贡献者 | 可追踪文档更新 |

不可违反的规则：

- AI 可以准备证据，人类批准科学用途。
- AI 必须记录不确定性，不能编造缺失数据。
- AI 不能覆盖人工 notes 或其他贡献者的 untracked work。
- 湿实验 design packet 必须在结果出现前 commit。
- 不能用结果倒改预注册方案。
- 大型 PDF、原始图片、SQLite 数据库和仪器原始文件默认不进 git，除非另有
  存储规则批准。

产物登记表：

| 产物 | 路径 | 主要负责人 | 何时更新 |
|---|---|---|---|
| 操作手册 | `docs/PROJECT_WORKFLOW.md`, `docs/PROJECT_WORKFLOW_ZH.md` | `[DOC]` | 流程或重要状态变化 |
| 协作协议 | `docs/AI_COLLABORATION_PROTOCOL.md` | `[AI]` + `[DOC]` | 多 agent 协作规则变化 |
| 时间顺序日志 | `docs/SESSION_LOG.md` | `[AI]` | 每次重要工作后 |
| 目标决策 | `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md` | `[HUMAN]` + `[AI]` | 目标或 scope 变化 |
| 文献 manifest | `data/literature/bovine_corpus_manifest.tsv` | `[AI]` + `[REVIEW]` | 文献状态变化 |
| 人工复核队列 | `data/literature/bovine_human_review_queue.tsv` | `[HUMAN]` + `[AI]` | 证据裁决更新 |
| Corpus summary | `docs/BOVINE_CORPUS_MANIFEST.md` | `[AI]` | Manifest 或 gate 变化 |
| 方法文献登记表 | `data/literature/ai_for_science_method_sources.tsv` | `[AI]` + `[REVIEW]` | 算法或 pipeline 决策 |
| 方法综述 | `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md` | `[AI]` + `[REVIEW]` | 方法决策 |
| 抽取评估 | `docs/EVAL_RESULTS.md`, `docs/MODEL_AGREEMENT.md` | `[AI]` | Evaluation run 后 |
| 证据审计 | `docs/EVIDENCE_AUDIT_PROLIFERATION.md` | `[AI]` + `[REVIEW]` | Evidence export 或 gate 更新 |
| 复核定位包 | `docs/HUMAN_REVIEW_PACKET_H001_H016.md` | `[AI]` + `[HUMAN]` | source 可用性或 review queue 更新 |
| 人工裁决工作表 | `data/literature/bovine_adjudication_H001_H014.tsv` | `[HUMAN]` + `[AI]` | 人工证据复核前后 |
| 工作表校验报告 | `docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md` | `[AI]` + `[REVIEW]` | 工作表创建或编辑后 |
| 候选变量 | `docs/CANDIDATE_VARIABLES.md` | `[AI]` + `[HUMAN]` | 人工证据复核完成后 |
| 湿实验设计包 | `docs/wetlab/ROUND_<n>_DESIGN_PACKET.md` | `[AI]` + `[LAB]` + `[REVIEW]` | 每轮湿实验前 |
| 湿实验结果 | `docs/wetlab/ROUND_<n>_RESULTS.md` | `[AI]` + `[LAB]` | 每轮湿实验后 |

## 5. 论文全流程

Gate 层面是顺序流程。阶段内部可以并行，但湿实验执行必须等 S7 通过。

| 阶段 | 名称 | 主要产物 | 当前状态 | Gate owner |
|---|---|---|---|---|
| S0 | 环境准备 | 可运行仓库 | Pass | `[AI]` |
| S1 | 范围锁定 | 湿实验目标决策 | Pass | `[HUMAN]` + `[REVIEW]` |
| S2 | 文献 corpus | Bovine manifest 和 review queue | Partial | `[AI]` + `[REVIEW]` |
| S3 | 全文抽取 | Grounded evidence tables | Fail / incomplete | `[AI]` + `[REVIEW]` |
| S4 | 人工证据复核 | Adjudicated evidence table | Fail / open | `[HUMAN]` |
| S5 | Search-space 设计 | 有边界的候选变量 | Not started | `[HUMAN]` + `[REVIEW]` |
| S6 | In-silico 稳健性 | Sensitivity 和 optimizer checks | Not started | `[AI]` + `[REVIEW]` |
| S7 | 湿实验预注册 | 冻结 design packet | Not started | `[HUMAN]` + `[LAB]` + `[REVIEW]` |
| S8 | 湿实验执行 | Raw results 和 deviations | Not started | `[LAB]` |
| S9 | 结果比较 | Processed results 和 Pareto analysis | Not started | `[AI]` + `[HUMAN]` |
| S10 | 闭环更新 | 下一轮或停止决策 | Not started | `[HUMAN]` + `[REVIEW]` |
| S11 | 论文审计 | 论文级 claims 和 artifacts | Not started | `[REVIEW]` |

状态词含义：

- `Pass`：gate 条件满足或产物已存在。
- `Partial`：已有可用工作，但 gate 证据还不完整。
- `Fail / incomplete`：当前证据明确阻止推进。
- `Not started`：必须等待上游 gate。

## 6. 阶段 Checklist

### S0. 环境准备

目标：让仓库可复现、可运行。

Checklist：

- [ ] `[AI]` 创建或激活 Python 环境。
- [ ] `[AI]` 安装依赖和 editable package。
- [ ] `[AI]` 运行单元测试。
- [ ] `[AI]` 运行 smoke pipeline。
- [ ] `[AI]` 运行 demo optimization。
- [ ] `[HUMAN]` 确认 live provider 的 API key 策略。
- [ ] `[DOC]` 把失败和修复写入 `docs/SESSION_LOG.md`。

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

### S1. 范围锁定

目标：让第一轮湿实验可解释，不变成过宽的问题。

Checklist：

- [x] `[AI]` 查阅近期培养肉培养基和细胞生物学文献。
- [x] `[AI]` 提出第一阶段湿实验生物目标。
- [x] `[REVIEW]` 区分 in-scope 和 out-of-scope。
- [x] `[DOC]` 记录目标、边界和 scope-change 规则。

Gate：`docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md` 已记录目标和边界。

### S2. 文献 Corpus

目标：先建立可追踪文献集合，再抽取和设计实验。

Checklist：

- [x] `[AI]` 建立 bovine-focused corpus manifest。
- [x] `[AI]` 将记录分类为 `core`、`core_context`、`context`、`defer` 或
  `background`。
- [x] `[AI]` 建立人工复核队列。
- [ ] `[HUMAN]` 确认 P1 core 纳入和排除。
- [ ] `[AI]` 尽可能拉取 P1 records 的全文或 PDF。
- [ ] `[REVIEW]` 检查 DOI、URL、物种、细胞类型、阶段、培养基重点、剂量
  可得性和 endpoints。

湿实验入口 corpus gate：

- 35-50 篇 peer-reviewed sources 已整理。
- 至少 8 篇近期 review 或 scoping papers。
- 至少 12 篇 primary medium 或 cell-culture papers。
- 至少 10 篇 bovine satellite-cell 或 myoblast 相关。
- 至少 5 篇有可抽取剂量或 range。
- 至少 3 篇报道 serum-free 或 animal-component-free bovine muscle-cell culture。
- Background-only 文献不计入湿实验证据。

### S3. 全文抽取

目标：把论文转成结构化、有证据支撑的数据。

Checklist：

- [ ] `[AI]` 导入 BibTeX、PDF、全文或外部生成的 structured paper files。
- [ ] `[AI]` 可用时优先使用结构化解析：GROBID TEI、structured text sections
  或未来 PDF backends。
- [ ] `[AI]` 对 P1/P2 sources 运行 triage 和 extraction。
- [ ] `[AI]` 导出 screening、component、evidence、extraction tables。
- [ ] `[AI]` 在提出湿实验变量前运行 `cultivate evidence-audit`。
- [ ] `[AI]` 记录 extraction coverage、non-missing fields 和 grounding rate。
- [ ] `[REVIEW]` 标记稀疏或不可靠抽取。
- [ ] `[AI]` 只有当证据显示是技术失败时才修 parser 或 prompt；如果原文缺失，
  不要把它当代码问题。

命令：

```bash
cultivate ingest
cultivate ingest --grobid-tei --grobid-url http://localhost:8070  # 可选
cultivate triage
cultivate extract --tier A
cultivate export
cultivate evidence-audit --outcome proliferation --out docs/EVIDENCE_AUDIT_PROLIFERATION.md
```

Gate：

- Top-ranked records 的 evidence quote grounding rate >= 0.95。
- Species、cell type、stage、medium type、serum-free status、component
  identity、dose/range、endpoint 的 non-missing fraction >= 0.75。
- 目标 outcome 的 evidence audit 不能是 `NO-GO`。
- 每个进入设计空间的成分都能追溯到 source quote 和 normalized component。

### S4. 人工证据复核

目标：把抽取证据变成科学上可使用的证据。

Checklist：

- [ ] `[AI]` 用 `cultivate review-packet` 生成 passage locators。
- [ ] `[AI]` 用 `cultivate adjudication-template` 生成可人工填写的裁决工作表。
- [ ] `[HUMAN]` 优先复核 `H001-H016`。
- [ ] `[HUMAN]` 将每项标为 `supported`、`partial`、`unsupported`、
  `uncertain` 或 `defer`。
- [ ] `[HUMAN]` 添加简短 notes：formulation、dose、endpoint、caveat 或排除原因。
- [ ] `[AI]` 把 notes 转成结构化 adjudication table。
- [ ] `[REVIEW]` 解决 AI 抽取和人工阅读的冲突。
- [ ] `[DOC]` 更新 `docs/BOVINE_CORPUS_MANIFEST.md`。

命令：

```bash
cultivate review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md
cultivate adjudication-template --ids H001-H014 --out data/literature/bovine_adjudication_H001_H014.tsv
cultivate adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv \
  --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md
```

建议复核顺序：

1. Beefy-9 benchmark、FGF2 reduction、albumin dose/cost。
2. Chemically defined bovine medium 和 differentiation capacity。
3. Commercial serum-free medium benchmarks。
4. Spent-media species and cell-type dependence。
5. DOE/RSM bovine serum-free media。
6. Albumin substitutes、protein isolates、hydrolysates。
7. Safety and cost annotations。

Gate：进入第一轮设计的所有非 exploratory 变量都有人工复核支持，并且
`docs/EVIDENCE_AUDIT_PROLIFERATION.md` 没有开放的 wet-lab-entry blocker。

### S5. Search-Space 设计

目标：定义优化器允许改变什么。

Checklist：

- [ ] `[AI]` 根据复核证据建立 candidate variable classes。
- [ ] `[AI]` 给每个变量分配 mechanism class。
- [ ] `[AI]` 添加 cost class、animal-origin status、food-grade plausibility、
  supplier risk。
- [ ] `[HUMAN]` 确认可获得且可接受的试剂。
- [ ] `[LAB]` 确认细胞来源、baseline medium、plate format、assay duration、
  throughput。
- [ ] `[REVIEW]` 移除机制不支持、组成不透明或风险不可接受的变量。

Gate：search space 有边界、可控、可采购且有证据支撑。

### S6. In-Silico 稳健性

目标：测试设计是否对检索器和优化器选择稳定。

Checklist：

- [ ] `[AI]` 比较 BM25 和 embedding retrieval 的证据簇。
- [ ] `[AI]` 比较 q-ParEGO 和 qLogNEHVI 的设计建议。
- [ ] `[AI]` 对关键变量类做 leave-one-source-out sensitivity。
- [ ] `[AI]` 生成第一版 candidate formulation table。
- [ ] `[REVIEW]` 检查重复、危险外推、unsupported claims 和 dominated candidates。
- [ ] `[HUMAN]` 批准或修改变量和 controls。

Gate：

- Top variable classes 在检索和优化扰动下至少 70% 重合。
- 非 exploratory 的关键变量不能只靠一篇论文。
- 分歧已记录。
- 第一轮 batch 包含 controls，且避免近重复候选。

### S7. 湿实验预注册

目标：在结果出现前冻结实验。

Checklist：

- [ ] `[AI]` 起草 design packet。
- [ ] `[LAB]` 确认 reagent list 和配制限制。
- [ ] `[LAB]` 确认 cell source、passage window、seeding density、
  culture duration、media-change schedule、plate format、replicate count。
- [ ] `[HUMAN]` 确认 primary 和 secondary endpoints。
- [ ] `[REVIEW]` 在任何结果出现前冻结 candidate formulations。
- [ ] `[DOC]` commit design packet。

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

目标：按冻结设计执行，不在中途改变问题。

Checklist：

- [ ] `[LAB]` 按冻结 protocol 准备细胞和试剂。
- [ ] `[LAB]` 记录 plate map、reagent lots、operator、passage number、
  seeding density 和 timing。
- [ ] `[LAB]` 保存 raw measurements 和必要 raw images。
- [ ] `[HUMAN]` 立即记录偏离 protocol 的情况。
- [ ] `[REVIEW]` 判断偏离是否导致无效、限定解释或只需备注。
- [ ] `[DOC]` commit metadata 和 result manifests；大型原始文件默认放 git 外。

Gate：实验完成或停止，并且偏差和 raw data 已记录。

### S9. 结果比较

目标：把实测结果与 controls 和目标比较。

Checklist：

- [ ] `[AI]` 把 raw results 载入结构化表格。
- [ ] `[AI]` 只做 within-experiment normalization。
- [ ] `[AI]` 计算 primary endpoint、secondary endpoints 和 cost estimates。
- [ ] `[AI]` 与 baseline 和 positive controls 比较。
- [ ] `[AI]` 更新 proliferation、cost、identity retention 的 Pareto front。
- [ ] `[HUMAN]` 检查统计结果是否符合生物学解释。
- [ ] `[REVIEW]` 将每个 claim 标为 `supported`、`partial`、`unsupported` 或
  `exploratory`。

Gate：结果已处理、比较并复核。

### S10. 闭环更新

目标：决定是否以及如何进行下一轮。

Checklist：

- [ ] `[AI]` 把 measured objective values 输入 `optimize.tell()`。
- [ ] `[AI]` 生成下一轮候选或停止建议。
- [ ] `[REVIEW]` 检查模型是在 exploitation、exploration，还是重复失败区域。
- [ ] `[HUMAN]` 决定继续、缩小 search space、增加 assay 或停止。
- [ ] `[DOC]` 如果继续，commit round summary 和下一轮 design packet。

Gate：下一步行动已记录。

### S11. 论文审计

目标：把系统和实验变成可辩护的论文流程。

Checklist：

- [ ] `[AI]` 生成最终表格：corpus、evidence、variables、formulations、
  results、Pareto comparison、sensitivity checks。
- [ ] `[AI]` 生成图：workflow、evidence map、variable support、
  experimental outcomes、Pareto front、closed-loop trajectory。
- [ ] `[HUMAN]` 写生物学解释和 limitations。
- [ ] `[REVIEW]` 每个 claim 都要能追溯到 evidence 和 wet-lab data。
- [ ] `[REVIEW]` 如实报告 negative 或 inconclusive results。
- [ ] `[DOC]` 归档 code commit、data manifests、analysis scripts 和 protocol
  versions。

Gate：论文 claims 可追溯到证据和结果。

## 7. 并行工作计划

现在可以并行做的工作：

| 工作线 | 现在可以做 | 现在不能做 |
|---|---|---|
| `[HUMAN]` 证据复核 | 用 locator packet 和 `bovine_adjudication_H001_H014.tsv` 复核 H001-H014 | 在 S3-S4 gate 未完成时批准湿实验变量 |
| `[AI]` corpus/extraction | 维护 H001-H014 裁决工作表；等人工/机构访问可用后获取 R024 主文全文；把人工 notes 转成 evidence records | 假装证据 gate 已过并生成 wet-lab design packet |
| `[LAB]` 可行性 | 确认 cell source、passage limits、baseline medium、plate format、assay duration、最大条件数和 reagent constraints | 开始实验或修改候选配方 |
| `[REVIEW]` gatekeeping | 检查 extracted claims 是否和 source text 一致，变量是否有证据支撑 | 把 direction-only evidence 当成定量证明 |

冲突规则：

- 编辑前先 pull 最新更改。
- 除非 ownership 清楚，否则把 untracked files 当作其他贡献者的工作。
- 使用小而可 review 的 commit。
- 重要协调决策写入 `SESSION_LOG.md`、decision record 或 commit message。
- 遇到只有人工能解决的 blocker，记录后继续做不阻塞的工作。

## 8. 当前项目账本

本节是简明状态快照。重要工作后更新；详细历史保留在 `SESSION_LOG.md`。

### 8.1 已完成的技术工作

- 仓库是 CLI-first Python package。
- 本次文档重写前的最新 committed validation：54 tests passed，3 个已知 warnings。
- Smoke pipeline 通过。
- Demo optimization loop 通过。
- Extraction evaluator 和四篇文献 offline fixture 已有。
- Provider-agnostic LLM layer 已有，并支持 offline mock mode。
- Operator extraction 已有，可把大 schema 拆成更小的 section-routed prompts。
- Structured-paper schema、plain-text fallback 和 GROBID TEI parsing 已有。
- `cultivate ingest --grobid-tei` 可调用运行中的 GROBID service 并保存
  `fulltext.xml`。
- Embedding retriever 已有。
- BoTorch qNEHVI 和 qLogNEHVI backend 已有。
- Optional citation verifier 已有。
- Ontology-to-search-space 已覆盖 hydrolysates、extracts、defined supplements、
  albumin substitutes、amino acids、carbon sources、trace elements、
  B8/Beefy-9/Beefy-R/SFB/SFGM、rapeseed-protein isolate、Grifola frondosa
  extract、Auxenochlorella pyrenoidosa protein extract、copper ions。这些只是
  normalization hooks，不是湿实验批准。
- `scripts/ingest_pdfs.py` 可以导入 loose PDF folders/lists。
- `scripts/run_evidence_parallel.py` 可以生成 effect-item exports。
- `cultivate evidence` 会写出 raw `effect_items_<outcome>.json`。
- `cultivate evidence-audit` 能生成保守的 wet-lab-entry report。
- `cultivate review-packet` 能为人工复核生成本地 full-text 字符范围 locators，
  但不做 evidence adjudication。
- `cultivate adjudication-template` 和 `cultivate adjudication-validate` 能创建和
  检查 H001-H014 人工填写工作表，但不判断证据是否 supported。

### 8.2 已完成的文献和计划工作

- 第一阶段 wet-lab-facing target 已记录。
- Bovine manifest v0 有 44 条记录。
- Human review queue v0 有 30 个 open tasks。
- AI-for-science 方法综述已存在。
- 方法文献登记表已覆盖 autonomous labs、scientific RAG、information extraction、
  document parsing、ETL、systematic-review tooling 和 Bayesian optimization。
- 当前方法决策：在生成湿实验设计前，优先提高 S3 全文抽取可靠性，并完成 S4
  evidence audit / 人工复核。

### 8.3 当前 Gate 状态

| Gate | 当前结果 | 含义 |
|---|---|---|
| Corpus manifest | Partial | 已有可用 bovine set，但 P1 人工复核和全文覆盖不完整 |
| Proliferation evidence audit | `NO-GO` | 当前 extracted evidence 不能支持湿实验入口 |
| Critical human review | 16/16 open | H001-H014 工作表已存在，但尚无人工 decision |
| Review-packet 覆盖 | 14/16 有本地 locators | H001-H014 可进入高效人工复核 |
| 缺失 review-packet source | 2/16 | H015-H016 对应 R024，需要机构访问或人工提供主文全文 |
| Wet-lab design packet | 缺失 | 必须等待证据复核、search-space、稳健性和预注册 gate |

### 8.4 已知 Blocker 和风险

- Live OpenAI/Anthropic extraction 太稀疏，不能算成功 model agreement。
- Gemini live comparison 未完成，因为没有 Gemini/Google key。
- OpenAI raw-response debugging 遇到 insufficient quota。
- 当前 corpus manifest 尚未完整全文抽取。
- GROBID service 是否可用属于外部条件。
- Cost、supplier、food-grade annotations 不完整。
- 当前 audit candidates 是 direction-only，不能作为定量湿实验证明。
- In-silico robustness 尚未在 reviewed bovine evidence 上运行。
- 尚无 wet-lab design packet，也无湿实验结果。

### 8.5 近期下一步

1. `[HUMAN]` 用当前 locator packet 和 `data/literature/bovine_adjudication_H001_H014.tsv`
   复核 H001-H014。
2. `[HUMAN]` 提供 R024 主文全文，或确认 R024 暂时 defer。
3. `[AI]` R024 可用后重新生成 `docs/HUMAN_REVIEW_PACKET_H001_H016.md`。
4. `[AI]` 把人工 notes 转成结构化 adjudication records。
5. `[AI]` 重新运行 extraction 和 `cultivate evidence-audit`。
6. `[REVIEW]` 决定哪些变量可以进入 S5 search-space design。
7. `[LAB]` 并行确认 assay 限制和 reagent feasibility。

## 9. AI 接管协议

任何 AI 接手时必须：

1. 读 `README.md`。
2. 读 `docs/AI_COLLABORATION_PROTOCOL.md`。
3. 读本手册或 `docs/PROJECT_WORKFLOW.md`。
4. 读 `docs/SESSION_LOG.md`。
5. 读 `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md`。
6. 读 `docs/BOVINE_CORPUS_MANIFEST.md`。
7. 运行 `git fetch --all --prune`。
8. 运行 `git status --short --branch`。
9. 识别 untracked files，避免覆盖。
10. 从第 8.3 节的下一个未通过 gate 继续。

推荐接管 prompt：

```text
请继续 CultivateAgent，使用 docs/PROJECT_WORKFLOW_ZH.md 作为控制性流程手册，并
使用 docs/AI_COLLABORATION_PROTOCOL.md 作为多 agent 协作协议。除非新增
scope-change decision record，否则保持当前 bovine satellite-cell/myoblast 扩增
培养基优化目标。先 fetch、检查 git status 和 untracked files，再推进下一个未通过
gate。不要覆盖人工复核 notes、其他 agent 的文件，也不要编造缺失证据。
```
