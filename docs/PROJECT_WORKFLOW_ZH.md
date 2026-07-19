# CultivateAgent 项目流程手册

状态：使用中
最后更新：2026-07-09
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
    ingest/                         BibTeX、PDF、全文、GROBID TEI/JATS XML 导入
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
| Gate 1 corpus 审计 | `docs/BOVINE_CORPUS_GATE1_AUDIT.md`, `data/literature/bovine_corpus_gate1_issues.tsv` | `[AI]` + `[REVIEW]` | Manifest 或复核状态变化 |
| 人工复核队列 | `data/literature/bovine_human_review_queue.tsv` | `[HUMAN]` + `[AI]` | 证据裁决更新 |
| Corpus summary | `docs/BOVINE_CORPUS_MANIFEST.md` | `[AI]` | Manifest 或 gate 变化 |
| 方法文献登记表 | `data/literature/ai_for_science_method_sources.tsv` | `[AI]` + `[REVIEW]` | 算法或 pipeline 决策 |
| 方法综述 | `docs/AI_FOR_SCIENCE_METHOD_REVIEW.md` | `[AI]` + `[REVIEW]` | 方法决策 |
| 抽取评估 | `docs/EVAL_RESULTS.md`, `docs/MODEL_AGREEMENT.md` | `[AI]` | Evaluation run 后 |
| 抽取就绪度报告 | `docs/EXTRACTION_READINESS_H001_H016.md`, `docs/EXTRACTION_READINESS_H031_H033.md` 及对应 TSV | `[AI]` + `[REVIEW]` | live operator extraction 前 |
| 证据审计 | `docs/EVIDENCE_AUDIT_PROLIFERATION.md` | `[AI]` + `[REVIEW]` | Evidence export 或 gate 更新 |
| JATS group-statistics 审计 | `docs/BOVINE_JATS_GROUP_STATS_AUDIT.md`, `data/literature/bovine_jats_group_stats_*_audit.tsv` | `[AI]` + `[REVIEW]` | 已验证 JATS 来源或 table path 变化 |
| 复核定位包 | `docs/HUMAN_REVIEW_PACKET_H001_H016.md`, `docs/HUMAN_REVIEW_PACKET_H031_H033.md` | `[AI]` + `[HUMAN]` | source 可用性或 review queue 更新 |
| 人工裁决工作表 | `data/literature/bovine_adjudication_H001_H014.tsv` | `[HUMAN]` + `[AI]` | 人工证据复核前后 |
| 工作表校验报告 | `docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md` | `[AI]` + `[REVIEW]` | 工作表创建或编辑后 |
| 工作表状态报告 | `docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md` | `[AI]` + `[REVIEW]` | 工作表创建或编辑后 |
| 已裁决证据表 | `data/literature/bovine_evidence_table.tsv` | `[HUMAN]` + `[AI]` + `[REVIEW]` | 有效人工裁决导出后 |
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
- [x] `[AI]` 用 `python scripts/audit_bovine_corpus.py --require-pass` 自动检查 Gate 1 数量、必需 metadata 和 P1 人工确认状态。
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
- [x] `[AI]` 使用严格 paper-ID alignment 评估 corpus：每个 gold record 都必须
  计分，缺失预测记为 false negatives，额外 ID 单独报告，重复 ID 直接失败。
- [x] `[AI]` 将 gold-field presence 和 evidence attachment 与 paper-ID coverage、
  quote grounding 分开报告；只有书目信息的空壳记录不算实质抽取。
- [x] `[AI]` 按 0.75 non-missing 阈值分别评估八个 Gate 2 概念；总体覆盖率
  不能抵消某个概念失败，A-M `dose_range` 结果在专用 dose extraction 经复核前
  只能是 provisional。
- [x] `[AI]` operator mode 仅在同一条 verified quote 同时出现 component 和
  dose/range 时生成 component-dose record；保留 unit、comparison group、endpoint，
  未验证关系不能算 Gate 2 direct dose coverage。
- [x] `[AI]` 将明确报告的 culture stage 和 medium role/type 抽取到专用
  `D.culture_stage`、`E.medium_type`；不能由 endpoint 或成分列表推断。
- [ ] `[HUMAN]` 修改冻结的四篇 benchmark 前，先版本化并重新裁决 stage/type
  gold，同时保留每份报告使用的 raw predictions。
- [x] `[AI]` 支持可重放 T1/T2 bundle：保存 exact gold、全部 provider
  predictions、source hashes、文件 checksums、paper order、失败记录和报告配置；
  scoring 前拒绝 drift 或 tampering。
- [ ] `[REVIEW]` 提交 bundle 前检查 gold version、引用权限、secret scan、
  provider/model labels 和 byte-stable replay。
- [x] `[AI]` 保留 `data/evaluation/runs/mock-baseline-v1` 作为离线格式/重放
  exemplar；不能把 deterministic mock scores 引用为模型准确率或湿实验证据。
- [x] `[AI]` 为 R015、R016、R017、R023 生成 `medium-fulltext-v1`，覆盖全部
  380 个 paper x A-M field cells，包含 source/schema hashes、两个独立 reviewer
  slot 和最终 adjudication。
- [ ] `[HUMAN]` Reviewer 1 不查看 reviewer 2 独立完成；reviewer 2 独立完成；
  两者分别使用独立的 `reviewer_blank.tsv` 实例；合并进 controlled master 后，
  最后裁决全部 disagreement 和 unresolved field。
- [ ] `[REVIEW]` 运行 `prepare_medium_gold_review.py validate --require-ready`；
  只有 380/380 adjudicated 且 0 issues 后才能跑 production T1 scoring。
- [x] `[AI]` 为 R015/R016 和 28 个高风险字段准备 `medium-pilot-v1`
  （56 cells），使用 manifest-controlled field scope、盲法 merge 和同一 validator。
- [ ] `[HUMAN]` 先完成并裁决 56-cell pilot；只有两位 reviewer 均 56/56、
  0 issues、decision kappa >= 0.70 且状态 READY 后才扩展，否则修订说明并创建
  新 pilot version。若因只有一个 decision class 导致 kappa 不可估计，则要求
  exact agreement 1.0，并记录 prevalence limitation。
- [x] `[AI]` 提供只读的 `prepare_medium_gold_review.py passages` field-aware
  locator；它检查 source hash 且不修改 worksheet。Lexical no-hit 不能在未读原文时
  被标为 `not_reported`。
- [x] `[AI]` 在 live operator extraction 前运行 `cultivate extraction-readiness`，
  区分 source missing 和 section routing weak。
- [x] `[AI]` 合法导入 R045-R047 全文，并生成带 SHA-256 的 H031-H033 review
  packet 和 readiness 报告。3 项均 direct operator-ready；这只是原文导航，
  不是证据批准。
- [x] `[AI]` 将通过身份/许可验证的 Zotero 来源 R048-R051 纳入正式候选语料和
  H034-H037 队列。精确 metadata/全文均经过哈希检查；4/4 有 locator 且可直接
  operator routing，但未赋予任何 evidence decision。
- [x] `[AI]` 按固定 bovine satellite-cell/myoblast expansion scope 复核全部
  7 条来源验证的直接培养基 Europe PMC canary：5 条作为 open core-context
  候选进入 R052-R056/H038-H042，2 条 embryonic/mesenchymal stem-cell 研究因
  细胞谱系错误排除；所有裁决绑定来源与段落哈希，不代表证据批准。
- [x] `[AI]` 从来源验证的本地 JATS 重建 R052-R056 canonical metadata/plain
  text，并检查 DOI/PMCID/license/source hash。H038-H042 达到 5/5 direct
  operator-ready 和 5/5 hash-bound locator-ready；decision 仍全部 open。
- [x] `[AI]` live pilot 使用 `cultivate extract --ids ...`，让 H review IDs、
  source record IDs 或 paper IDs 精确选择 paper set。
- [x] `[AI]` 把全 operator provider-call failure 视为抽取失败；当所有
  operators 都是 `call_error` 时，不写空 extraction record。
- [x] `[AI]` 对 authentication、balance、permission、invalid-request、
  invalid-parameter、missing-model 等非暂态 provider 错误 fail-fast；对
  rate-limit/server 这类暂态错误保留 retry/backoff。
- [ ] `[REVIEW]` 标记稀疏或不可靠抽取。
- [ ] `[AI]` 只有当证据显示是技术失败时才修 parser 或 prompt；如果原文缺失，
  不要把它当代码问题。

命令：

```bash
cultivate ingest
cultivate ingest --grobid-tei --grobid-url http://localhost:8070  # 可选
cultivate triage
cultivate extraction-readiness --ids H001-H016 \
  --out docs/EXTRACTION_READINESS_H001_H016.md \
  --tsv data/literature/bovine_extraction_readiness_H001_H016.tsv
cultivate extraction-readiness --ids H031-H033 \
  --out docs/EXTRACTION_READINESS_H031_H033.md \
  --tsv data/literature/bovine_extraction_readiness_H031_H033.tsv
cultivate review-packet --ids H031-H033 --out docs/HUMAN_REVIEW_PACKET_H031_H033.md
python scripts/ingest_verified_sources.py \
  --verified-sources data/evaluation/gold/zotero-locator-heldout-v1/verified_sources.tsv
cultivate extraction-readiness --ids H034-H037 \
  --out docs/EXTRACTION_READINESS_H034_H037.md \
  --tsv data/literature/bovine_extraction_readiness_H034_H037.tsv
cultivate review-packet --ids H034-H037 --out docs/HUMAN_REVIEW_PACKET_H034_H037.md
python scripts/materialize_verified_jats.py
cultivate extraction-readiness --ids H038-H042 \
  --out docs/EXTRACTION_READINESS_H038_H042.md \
  --tsv data/literature/bovine_extraction_readiness_H038_H042.tsv
cultivate review-packet --ids H038-H042 --out docs/HUMAN_REVIEW_PACKET_H038_H042.md
cultivate extract --ids H014 --mode operators --provider openai --model deepseek-v4-flash
cultivate extract --ids H001-H014 --mode operators --provider openai --model deepseek-v4-flash
cultivate export
cultivate evidence-audit --outcome proliferation --out docs/EVIDENCE_AUDIT_PROLIFERATION.md
python scripts/evaluate_medium_corpus.py --provider mock_gpt --agreement-scope mock \
  --artifacts-out data/evaluation/runs/mock-baseline-v1 --out-dir /tmp/mock-baseline-v1
python scripts/evaluate_medium_corpus.py \
  --artifacts-in data/evaluation/runs/mock-baseline-v1 --out-dir /tmp/mock-baseline-v1-replay
python scripts/prepare_medium_gold_review.py validate \
  --manifest data/evaluation/gold/medium-fulltext-v1/manifest.json \
  --worksheet data/evaluation/gold/medium-fulltext-v1/review.tsv \
  --out docs/FULLTEXT_GOLD_VALIDATION_MEDIUM_V1.md
# 两份独立 reviewer 文件完成后：
python scripts/prepare_medium_gold_review.py merge \
  --master data/evaluation/gold/medium-fulltext-v1/review.tsv \
  --reviewer-1 /path/to/reviewer_1.tsv --reviewer-2 /path/to/reviewer_2.tsv \
  --out data/evaluation/gold/medium-fulltext-v1/review.tsv
python scripts/prepare_medium_gold_review.py passages \
  --manifest data/evaluation/gold/medium-pilot-v1/manifest.json \
  --record R015 --field E.growth_factors --out /tmp/r015-growth-factor-locators.md
```

Gate：

- Top-ranked records 的 evidence quote grounding rate >= 0.95。
- Species、cell type、stage、medium type、serum-free status、component
  identity、dose/range、endpoint 的 non-missing fraction >= 0.75。
- 目标 outcome 的 evidence audit 不能是 `NO-GO`。
- 每个进入设计空间的成分都能追溯到 source quote 和 normalized component。

### S4. 人工证据复核

目标：把抽取证据变成科学上可使用的证据。

方法规则：S4 采用 human-in-the-loop 的系统综述模式。AI 可以排序记录、生成
locator、预览短片段、校验工作表结构；但不能决定证据是否 supported、不能排除
source，也不能把变量推进湿实验 search space。这个规则来自 Cochrane 的重复检查和
透明决策原则、PRISMA/PRISMA-trAIce 对 AI-assisted review 的报告要求，以及
ASReview/RobotReviewer 这类自动化工具“辅助而不替代 reviewer”的边界。

Checklist：

- [ ] `[AI]` 用 `cultivate review-packet` 生成 passage locators。
- [ ] `[AI]` 用 `cultivate adjudication-template` 生成可人工填写的裁决工作表。
- [ ] `[AI]` 为所有 AI-assisted review 产物记录 provider、model、extraction
  mode、locator source 和 validator status。
- [ ] `[REVIEW]` 先用 2-3 条记录 pilot 工作表，确认 decision、range、notes 和
  conflict labels 能用，再扩大复核。
- [ ] `[HUMAN]` 优先复核 `H001-H016`。
- [ ] `[HUMAN]` 将每项标为 `supported`、`partial`、`unsupported`、
  `uncertain` 或 `defer`。
- [ ] `[HUMAN]` 添加简短 notes：formulation、dose、endpoint、caveat 或排除原因。
- [ ] `[HUMAN]` 对会影响湿实验变量的 outcome-direction 和 dose/range 行做独立
  复核。
- [ ] `[HUMAN]` 对定量 effect claim 填写 `numeric_effect_status`、
  `numeric_effect_metric`、`numeric_effect_value`、可选的
  `numeric_effect_variance` 和 `numeric_effect_notes`；direction-only 行使用
  `not_applicable`。
- [ ] `[AI]` 用 `cultivate adjudication-validate` 校验已填写工作表。
- [ ] `[AI]` 只把人工标记为 `supported` 或 `partial` 的行用
  `cultivate adjudication-export` 导出到
  `data/literature/bovine_evidence_table.tsv`。
- [ ] `[REVIEW]` 解决 AI 抽取和人工阅读的冲突。
- [ ] `[DOC]` 更新 `docs/BOVINE_CORPUS_MANIFEST.md`。

命令：

```bash
cultivate review-packet --ids H001-H016 --out docs/HUMAN_REVIEW_PACKET_H001_H016.md
cultivate adjudication-template --ids H001-H014 --out data/literature/bovine_adjudication_H001_H014.tsv
cultivate adjudication-status --out docs/HUMAN_ADJUDICATION_STATUS_H001_H014.md
cultivate adjudication-passages --ids H014 --max-ranges 1
cultivate adjudication-validate --worksheet data/literature/bovine_adjudication_H001_H014.tsv \
  --out docs/HUMAN_ADJUDICATION_VALIDATION_H001_H014.md
cultivate adjudication-export --worksheet data/literature/bovine_adjudication_H001_H014.tsv \
  --out data/literature/bovine_evidence_table.tsv
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
会影响第一轮设计的 outcome-direction 和 dose/range 行已经独立复核，或由
`[REVIEW]` 明确豁免；`docs/EVIDENCE_AUDIT_PROLIFERATION.md` 没有开放的
wet-lab-entry blocker。

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
- Codex 的 JATS/readiness、provider fail-fast、S4 review helpers、Claude
  DeepSeek comparison handoff、effect item 数字 quote verification 和
  quote-based log fold-change inference、effect item numeric adjudication
  fields，以及明确 treatment/control means 的 log-ratio/variance inference 合并入
  `main` 后，最新 main-line validation：focused numeric tests 通过；当前 managed
  sandbox 中排除 local-loopback GROBID mock test 后，66 tests passed、2 个
  optional tests skipped、1 个 deselected。
- Codex 现在使用 `/Users/tianyangsong/Desktop/Research/CultivateAgent-codex`；
  Claude 使用 `/Users/tianyangsong/Desktop/Research/CultivateAgent-claude`。
  短生命周期 feature branch 应及时合并到 `main` 并删除，避免 side branch 变成
  stale 状态。
- Smoke pipeline 通过。
- Demo optimization loop 通过。
- Extraction evaluator 和四篇文献 offline fixture 已有。
- Provider-agnostic LLM layer 已有，支持 offline mock mode，并支持
  `llm.extra_body` 透传 OpenAI-compatible provider 的专用参数。
- Operator extraction 已有，可把大 schema 拆成更小的 section-routed prompts。
- Structured-paper schema、plain-text fallback、GROBID TEI parsing 和
  JATS/Open Access XML parsing 已有。
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
- `scripts/run_evidence_parallel.py` 可以生成 effect-item exports，也可以用
  `--model`、`--max-tokens`、`--items-out` 生成受控 provider/model 对比文件；
  它会报告 tier counts，用来区分 direction-only evidence 和 quantitative
  effect-size evidence。
- `evidence.extract_effects` 现在会把 numeric `effect` 和 `variance` 字段与
  evidence quote 核对；quote 不支持的数字会被清空，不能作为 quantitative
  evidence 进入 random-effects pool。
- 明确写在 quote 中的 fold/percent change 可以转换成 log response ratio
  `ln(ratio)`；因为不会推断 variance，所以这最多仍是 tier 2。
- 明确写在 quote 中的 treatment/control means 也可以转换成
  `ln(treatment_mean/control_mean)`，并在可用时记录 endpoint/timepoint context。
  剂量、浓度、timepoint 和因子名里的数字不会被当作 response value。只有同一条
  quote 同时明确给出两组 mean、SD/SE/SEM 和 sample size 时，才会计算 ROM
  sampling variance。
- 百分比 effect inference 必须有明确 increase/decrease/change 语义；百分比后接
  reagent 或 medium 名称时按浓度排除。`N +/- M-fold` 只把 N 当 point estimate，
  M 是 error term；这些规则已有回归测试，仍需 S4 复核。
- `cultivate evidence` 会写出 raw `effect_items_<outcome>.json`。
- `cultivate evidence-audit` 能生成保守的 wet-lab-entry report。
- `cultivate extraction-readiness` 会在调用 LLM 前检查本地全文和 section routing
  是否足够支持 operator extractor，但不抽取、不裁决证据。当前 H001-H016 结果：
  14 个 direct-ready、0 个 full-text fallback-ready、2 个 R024 missing。生成报告
  现在记录 repo-relative 的 `data/papers/...` 路径，因此在 Codex/Claude worktree
  之间保持稳定。
- `cultivate review-packet` 能为人工复核生成 repo-relative 本地 full-text 字符范围
  locators，但不做 evidence adjudication。
- `cultivate adjudication-template` 和 `cultivate adjudication-validate` 能创建和
  检查带有可移植 `data/papers/...` 路径的 H001-H014 人工填写工作表，但不判断证据
  是否 supported。如果工作表中已有人工 decision，template 命令默认拒绝覆盖；只有
  显式传入 `--force` 才会覆盖；强制覆盖前会在工作表旁创建带时间戳的 `.bak` 备份，
  这些本地备份会被 git 忽略。工作表现在包含 `numeric_effect_status`、metric、
  value、variance 和 notes 字段；quote 自动推断的 tier 2 数值和未来 tier 1
  数值，在进入论文 claim 前都需要人工数字复核。
- `cultivate adjudication-status` 会汇总 blank、resolved、evidence-bearing 和 invalid
  decisions。当前 H001-H014 状态：0/14 resolved，0 个 evidence-bearing decisions，
  0 个 validation issues。
- `cultivate adjudication-passages` 能根据 worksheet range 输出短本地片段，帮助人工
  更快查看原文；它不是 AI 裁决，生成的 snippet 文件默认不应提交，除非确认引用权限。
- `cultivate adjudication-export` 会把有效的人工 `supported` 或 `partial`
  行导出到 `data/literature/bovine_evidence_table.tsv`；当前提交的证据表只有表头，
  因为还没有人工 decision。

### 8.2 已完成的文献和计划工作

- 第一阶段 wet-lab-facing target 已记录。
- Bovine manifest 有 56 条记录。
- 可执行 Gate 1 审计只统计设计纳入记录：44 篇同行评审来源、18 篇综述、26 篇
  原始研究、22 篇 bovine primary、26 篇含剂量的 primary，以及 9 篇 bovine
  serum-free primary。六项数量门槛和必需 metadata 均通过；但 23 条 P1
  core/core-context 中 0 条具有明确 human-verified 状态，因此 Gate 1 仍为
  `FAIL`。
- R045-R047 分别补充 microbial lysate 血清替代、Pichia 来源重组白蛋白，以及
  无血清条件下 donor variance 的边界明确证据。题名和 DOI 均由 Crossref 加
  PubMed 或出版社记录核对；它们均不视为已裁决证据。
- Human review queue 有 42 个 open tasks。
- 236 行 Zotero acquisition funnel 已确定性分区为：212 条 actionable、23 条
  exclusion（22 条 canonical DOI duplicate 和 1 条无 DOI 队内重复），以及 1 条
  暂停的同标题/不同 DOI 版本冲突；原始模型输出保持不变。
- 212 条 actionable 记录已完成可续跑的 Europe PMC/Crossref metadata 审计：
  75 条 Europe PMC JATS 候选、34 条额外 Crossref CC-VOR 候选、96 条许可未验证
  metadata，以及 7 条缺 DOI 记录。本轮没有下载全文；109 条候选仍必须通过来源
  DOI、文内许可和结构完整性的确定性验证。
- 有界 bovine-focused Europe PMC canary 已完成 10/10 条 JATS 来源级验证：其中
  7 条为直接培养基干预 primary study，3 条为牛细胞扩增背景研究。8/10 含结构化
  表格，3/10 含统计记号单元格；25 张表、996 个单元格和 58 个记号命中都只是
  extraction locator，不是定量证据，也不代表已进入 canonical corpus。
- 哈希绑定的 scope review 将 7 条 direct-medium canary 中 5 条纳入
  R052-R056 和 open tasks H038-H042，另 2 条因细胞谱系错误排除。独立
  acquisition replay 已验证 5/5 的来源哈希和 canonical DOI/PMCID 绑定；这只
  证明 scope eligibility，不是 evidence adjudication。
- R052-R056 已可从验证过的 JATS 哈希重复生成 canonical metadata 和 plain
  text。H038-H042 为 5/5 direct operator-ready、5/5 locator-ready；复核包带
  source hash，但不代表 evidence approval。
- R016 本地 identity 缺陷已修复。逐文件审计证明 PDF、plain text 和 JATS 原本
  就是正确来源，受污染的只有 mixed example-BibTeX 生成的 metadata 和 assets。
  原文件已保存在内容寻址的本地隔离目录，示例条目已纠正；离线 acquisition 回放
  已通过，且没有改变人工试点绑定的 source hash。
- 已验证 bovine JATS group-statistics 审计覆盖 14 个来源、37 张表和 2,103 个
  单元格，且不转录源数字。结果为 0 个完整 treatment/control
  mean-dispersion-n 结构：9 张表不完整、12 张统计表属于组成/模型/非培养基输出，
  16 张没有 group-stat 结构。因此该来源集不进入 DeepSeek cell-role 标注。
- AI-for-science 方法综述已存在。
- DeepSeek compatibility route 与显式 `deepseek-v4-flash` 的 effect-extraction
  对比已记录在 `docs/MODEL_COMPARISON_DEEPSEEK.md`；结论是显式 v4-flash run
  更干净、更批判，但仍然是 direction-only，因此不能替代人工复核，也不能替代
  后续 numeric effect-size extraction。
- Quote-level numeric gate 已实现：LLM 返回的 effect 或 variance 数字如果没有
  出现在已验证 quote 中，就不能把该 item 升级为 tier 1 或 tier 2 evidence。
- S4 人工工作表现在有独立的 numeric-effect review gate；一行可以在方向上
  supported，但定量值仍然保持 `partial`、`unsupported`、`uncertain` 或 `defer`。
- 方法文献登记表已加入 Cochrane ratio-measure guidance、
  Hedges/Gurevitch/Curtis response ratio，以及 Friedrich/Adhikari/Beyene
  ratio of means 和 metafor ROM implementation notes，用于支撑保守的
  quote-level log-ratio 和 variance extraction。
- 方法文献登记表已覆盖 autonomous labs、scientific RAG、information extraction、
  document parsing、ETL、systematic-review tooling、human-in-the-loop 证据复核、
  AI review reporting 和 Bayesian optimization。
- 当前方法决策：在生成湿实验设计前，优先提高 S3 全文抽取可靠性，并完成 S4
  evidence audit / 人工复核。

### 8.3 当前 Gate 状态

| Gate | 当前结果 | 含义 |
|---|---|---|
| Corpus Gate 1 | `FAIL`；6/6 数量检查和 metadata 通过 | 纳入同行评审来源 44/44；P1 core/core-context 人工确认 0/23 |
| Proliferation evidence audit | `NO-GO` | 当前 extracted evidence 不能支持湿实验入口 |
| Extraction readiness | 14 direct-ready, 0 fallback-ready, 2 missing | H001-H014 可跑 section-routed operators；H015-H016 需要 R024 |
| Gate 2 关键字段覆盖 | `FAIL`：当前 committed live benchmark 为 0/17 applicable concept-paper cells | 返回了 paper IDs，但没有 B-M 关键内容；fixture gold 的 stage、medium type 不可评估 |
| Critical human review | 16/16 open | H001-H014 工作表和证据表导出路径已存在，但尚无人工 decision |
| H001-H014 adjudication status | 0/14 resolved, 0 evidence-bearing | 状态报告确认工作表结构有效，但仍等待人工 decision |
| 已裁决证据表 | 0 行 | 来自空白工作表的仅表头导出；不是证据批准 |
| Review-packet 覆盖 | 14/16 有本地 locators | H001-H014 可进入高效人工复核 |
| 新来源 review packet | 3/3 有 SHA-256 绑定的本地 locators | H031-H033 对应 R045-R047；decision 全部保持 open |
| 新来源 extraction readiness | 3/3 direct-ready | R046 使用 Europe PMC JATS；R045/R047 来自合法本地或开放 PDF |
| Zotero 候选 packet/readiness | 4/4 locator-ready 且 direct-ready | H034-H037 对应 R048-R051；decision 全部保持 open |
| Europe PMC 纳入来源 packet/readiness | 5/5 locator-ready 且 direct-ready | H038-H042 对应 R052-R056；JATS materialization 可重复，decision 全部保持 open |
| DeepSeek 定量文本块下放 | `FAIL`；独立 silver recall 10/13（0.7692），此前为 10/12（0.8333） | 当前 prompt/model 的任务关闭；保留确定性预筛，复核转交更强模型 |
| DeepSeek metadata-linkage 下放 | `FAIL`；3 次 recall 均为 0.50，precision 1.00，Jaccard 1.00 | 稳定漏掉 3/6 个同领域跨论文错配；不得下放或自动修正 metadata |
| DeepSeek 页级候选定位下放 | `HOLD_AFTER_SHADOW`；gold 与来源独立 holdout 的 3+3 次 recall 均为 1.00，但 R053-R055 shadow 只减少 13.0% 摘要输入 | IDs-only 能力稳定，但相对 5.5% 确定性基线的增量太小，且无标签 shadow recall 未知，因此不接入生产路由 |
| Zotero acquisition 去重 | `PASS`；236 = 212 actionable + 23 excluded + 1 conflict | 只能从 actionable TSV 获取；冲突等待版本人工复核 |
| Zotero OA 发现审计 | `PASS`；212 = 75 EPMC JATS + 34 Crossref CC-VOR + 96 未验证 + 7 缺 DOI | 109 条 OA/许可候选只是线索，仍需来源级验证 |
| Europe PMC bovine JATS canary | `PASS`；10/10 来源验证，8/10 有表格，3/10 有统计记号单元格 | 获取路径可用；scope review 与 canonical promotion 仍是独立环节 |
| 已验证 JATS group-statistics readiness | `OFF_RAMP`；14 个来源、37 张表、2,103 个单元格、0 个完整结构 | R054 T5-T12 有 SEM 指针但没有表内 sample size；出现完整结构前不花 DeepSeek 调用 |
| Europe PMC bovine scope promotion | `PASS`；7/7 已复核，5 条 open 纳入，2 条错误谱系排除 | 来源/哈希 scope 裁决完成；纳入记录均未获得 evidence approval |
| 缺失 review-packet source | 2/16 | H015-H016 对应 R024，需要机构访问或人工提供主文全文 |
| Wet-lab design packet | 缺失 | 必须等待证据复核、search-space、稳健性和预注册 gate |

### 8.4 已知 Blocker 和风险

- 新 worktree 不会自动带有 ignored 的本地 paper assets（`data/papers/`）。
  运行 extraction-readiness 前需要本地复制或重新生成这些材料。
- 当前 managed Codex sandbox 不能完成对临时 `HTTPServer` 的本地 `urllib` POST，
  即使 command escalation 后也一样。因此
  `tests/test_pipeline.py::test_grobid_client_writes_and_parses_tei` 在此环境
  受阻，但非 loopback test suite 和 CLI smoke checks 不受影响。
- 一旦 reviewer 开始填写 `data/literature/bovine_adjudication_H001_H014.tsv`，
  不要再直接运行 `adjudication-template` 覆盖；除非已经保存人工版本，并且有意使用
  `--force`。强制覆盖会创建带时间戳的 `.bak`，但这只是兜底保护，不是常规复核流程，
  备份文件应留在本地。
- Live OpenAI/Anthropic extraction 太稀疏，不能算成功 model agreement。
- Gemini live comparison 未完成，因为没有 Gemini/Google key。
- OpenAI raw-response debugging 遇到 insufficient quota。
- 最新 DeepSeek-compatible H014 live pilot 已到达 provider，但当前环境 key
  认证失败；没有写入 extraction。
- DeepSeek compatibility route 与显式 v4-flash 的对比是质量检查，不是湿实验
  证据；两组输出都是 direction-only，必须经过人工裁决后才可能影响变量选择。
- 当前 corpus manifest 尚未完整全文抽取。
- GROBID service 是否可用属于外部条件；已有合法来源的 JATS/Open Access XML
  也可以直接解析。
- Cost、supplier、food-grade annotations 不完整。
- 当前 audit candidates 是 direction-only，不能作为定量湿实验证明。
- In-silico robustness 尚未在 reviewed bovine evidence 上运行。
- 尚无 wet-lab design packet，也无湿实验结果。
- 尚有 1 条 Zotero acquisition 版本冲突：bioRxiv DOI 与 corpus 中正式发表版本
  同标题。在人工确认预印本是否含值得保留的独有补充材料前，不得获取。

### 8.5 近期下一步

1. `[HUMAN]` 确认或修正 23 条 P1 core/core-context 的 manifest decision，特别
   检查 R045/R047 的外推限制和新增 H034-H042 的候选边界。
2. `[HUMAN]` 用当前 locator packet 和 `data/literature/bovine_adjudication_H001_H014.tsv`
   复核 H001-H014。
3. `[HUMAN]` 提供 R024 主文全文，或确认 R024 暂时 defer。
4. `[AI]` R024 可用后重新生成 `docs/HUMAN_REVIEW_PACKET_H001_H016.md`。
5. `[AI]` 校验已填写工作表，并运行 `cultivate adjudication-export` 更新
   `data/literature/bovine_evidence_table.tsv`。
6. `[AI]` 先用 `cultivate extract --ids H014 --mode operators` 跑小规模 live
   operator-extraction pilot，检查 grounding 和 raw extraction metadata；只有
   pilot 可接受后再扩大到 `--ids H001-H014`。
7. `[AI]` 在 source-verified figures/supplements 中寻找完整的 treatment/control
   mean-dispersion-n 结构。完整 pointer set 出现前保持 JATS table path off-ramp；
   所有数值必须绑定来源，并继续接受人工数字复核。
8. `[REVIEW]` 决定哪些变量可以进入 S5 search-space design。
9. `[LAB]` 并行确认 assay 限制和 reagent feasibility。

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
10. 只在该 agent 自己的 worktree 中工作。
11. 从第 8.3 节的下一个未通过 gate 继续。
12. 决定任务前，分别估算软件基础设施、湿实验入口准备度和完整论文流程的完成度；
    记录计算证据。若改动只提高可审计性而没有通过科学 gate，不提高完成度估计。

推荐接管 prompt：

```text
请继续 CultivateAgent，使用 docs/PROJECT_WORKFLOW_ZH.md 作为控制性流程手册，并
使用 docs/AI_COLLABORATION_PROTOCOL.md 作为多 agent 协作协议。除非新增
scope-change decision record，否则保持当前 bovine satellite-cell/myoblast 扩增
培养基优化目标。先 fetch、检查 git status 和 untracked files，再推进下一个未通过
gate。不要覆盖人工复核 notes、其他 agent 的文件，也不要编造缺失证据。
```
