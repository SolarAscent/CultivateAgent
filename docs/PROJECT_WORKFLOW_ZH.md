# CultivateAgent 项目全流程指南

日期：2026-07-07

English version: [`PROJECT_WORKFLOW.md`](PROJECT_WORKFLOW.md)

适用对象：开发者、文献复核者、湿实验合作者、项目负责人，以及需要接管项目的
Codex、Claude 或其他 AI。

这份文档是 CultivateAgent 的中文操作总手册。目标是让所有参与者都知道：

- 项目现在是什么结构；
- 每一步谁负责；
- 哪些事情可以并行；
- 哪些地方必须 review；
- 什么条件下才能进入湿实验；
- 最终如何完成结果比较、结果评价和论文级记录。

## 角色标记

为了避免多人和多个 AI 同时工作时互相覆盖，所有任务都尽量用以下标记：

- `[人工]`：需要人类科学判断、方向决策或最终确认。
- `[AI]`：Codex、Claude 或其他 AI 可以执行。
- `[实验]`：需要湿实验人员或实验室负责人确认/执行。
- `[复核]`：明确的检查、审阅、确认环节。
- `[门槛]`：阶段关卡。未满足前不要进入下一阶段。
- `[记录]`：需要写入文档、表格、commit 或实验记录。

## 项目是什么

CultivateAgent 是一个面向培养肉培养基优化的文献挖掘与实验设计系统。
它借鉴 ReactionSeek 的思想：

1. 用 LLM 从论文里抽取结构化事实；
2. 用确定性工具校验、标准化这些事实；
3. 把结果存入知识库；
4. 根据目标检索证据；
5. 生成有证据支撑的培养基变量建议；
6. 用多目标贝叶斯优化生成可预注册的下一轮实验批次。

当前第一阶段湿实验目标已经锁定为：

> 牛 satellite cells / bovine myoblasts 的扩增阶段培养基优化，
> 目标是无血清、优先 animal-component-free、成本敏感，同时保留 myogenic identity。

第一轮只优化 **medium variables**。暂时不做支架、微载体、灌流、生物反应器、
基因工程、whole-cut texture、感官评价，也不把分化培养基作为第一轮主要优化对象。
这些可以作为后续阶段，但不能混进第一轮问题里。

## 给开发者看的项目结构

```text
CultivateAgent/
  README.md                         项目总览和 CLI 快速开始
  pyproject.toml                    包配置和 optional deps
  requirements.txt                  默认依赖
  config/
    config.example.yaml             运行配置模板
  cultivate_agent/
    cli.py                          命令行入口
    ingest/                         BibTeX、PDF、全文导入
    triage/                         论文初筛和 A/B/C 分层
    extract/                        LLM 抽取 prompt 和 parser
    schema/                         A-M 抽取 schema 和 evidence 结构
    normalize/                      成分名、单位、剂量标准化
    kb/                             SQLite 知识库和导出
    retrieve/                       BM25 和 embedding 检索
    design/                         有证据支撑的培养基推荐
    optimize/                       搜索空间、代理模型、MOBO 优化
    evaluate/                       抽取评估指标
    llm/                            OpenAI / Anthropic / Gemini / mock 后端
  scripts/
    evaluate_medium_corpus.py       抽取和模型一致性评估
    compare_mobo_backends.py        q-ParEGO/qNEHVI/qLogNEHVI 对比
  data/
    library.example.bib             BibTeX 示例
    literature/
      bovine_corpus_manifest.tsv    牛肌源培养基文献 manifest
      bovine_human_review_queue.tsv 人工复核任务队列
  docs/
    ARCHITECTURE.md
    OPTIMIZATION.md
    PROJECT_WORKFLOW.md             英文总流程
    PROJECT_WORKFLOW_ZH.md          中文总流程
    LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md
    BOVINE_CORPUS_MANIFEST.md
    SESSION_LOG.md
    REVIEW_BY_NEXT_ENGINEER.md
```

开发注意事项：

- 不要随意扩大第一轮目标。当前第一轮只能动培养基变量。
- 不要把不同论文里的 outcome 当作可直接比较的训练标签。
- 所有关键抽取值都要有 evidence quote。
- `data/literature/*.tsv` 是人工整理的元数据，可以进 git；PDF、SQLite、
  原始全文和大文件默认不要进 git。
- 改代码后要跑测试。
- 科学决策要写进 `docs/`，不能只留在聊天记录里。

## 当前系统最终呈现方式

现在的系统不是网页，也不是 dashboard。

当前呈现方式是：

- 终端 CLI：`cultivate ingest / extract / export / design / optimize`
- Markdown 文档：决策记录、流程说明、复核说明
- TSV / CSV / JSONL：文献表、证据表、成分表、候选实验表、结果表

论文工作流最终应该形成一个 **design and validation package**：

- 文献 manifest；
- 人工复核后的 evidence table；
- 标准化成分和剂量表；
- 有边界的 search space；
- 预注册 candidate formulation table；
- wet-lab protocol summary；
- 原始和处理后的实验结果；
- 与 baseline/control 的比较；
- 统计分析和解释；
- 论文图表和方法记录。

网页可以以后做，但现在不应该先做网页。现在最重要的是证据链和湿实验验证链。

## 从 0 到论文完成的总流程

### Phase 0：项目环境和可运行性

目标：确保仓库可以稳定运行。

- [ ] `[AI]` 创建或更新 Python 环境。
- [ ] `[AI]` 安装依赖和 editable package。
- [ ] `[AI]` 跑单元测试和 smoke test。
- [ ] `[人工]` 确认本地路径、API key 策略、是否允许调用云端模型。
- [ ] `[记录]` 把环境、分支、失败点写入 `docs/SESSION_LOG.md`。

常用命令：

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
pip install -e .
.venv/bin/python -m pytest -q
.venv/bin/python -m cultivate_agent.cli smoke
```

`[门槛]` 测试和 smoke 通过，或者失败原因和修复计划已记录。

### Phase 1：科学目标锁定

目标：只选一个第一轮能真正做湿实验的问题。

- [x] `[AI]` 查阅近年培养肉培养基和细胞生物学综述。
- [x] `[AI]` 给出第一阶段湿实验目标建议。
- [x] `[复核]` 明确 in scope 和 out of scope。
- [x] `[记录]` 写入
  `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md`。

当前锁定目标：

- 牛 satellite cells / bovine myoblasts；
- 扩增/增殖阶段；
- 无血清，优先 animal-component-free；
- 成本敏感；
- 保留 myogenic identity；
- 只动培养基变量。

`[门槛]` 如果要换方向，必须新增决策记录，说明为什么换、证据是什么、
会影响哪些表和 gate。

### Phase 2：文献 corpus 建立

目标：先建立可追踪的文献集合，再谈抽取和湿实验。

- [x] `[AI]` 建立 bovine-focused corpus manifest。
- [x] `[AI]` 给每篇文献标注 `core`、`core_context`、`context`、
  `defer` 或 `background`。
- [x] `[AI]` 建立人工复核队列。
- [ ] `[人工]` 确认 P1 core 文献是否应该纳入。
- [ ] `[AI]` 拉取 P1 文献全文/PDF。
- [ ] `[复核]` 检查 DOI、URL、物种、细胞类型、阶段、培养基类型、
  是否有剂量和 endpoint。

文件：

- `data/literature/bovine_corpus_manifest.tsv`
- `data/literature/bovine_human_review_queue.tsv`
- `docs/BOVINE_CORPUS_MANIFEST.md`

`[门槛]` 进入湿实验前，corpus 至少应满足：

- 35-50 篇 peer-reviewed sources；
- 至少 8 篇近年综述或共识/范围综述；
- 至少 12 篇 primary medium/cell-culture papers；
- 至少 10 篇 bovine satellite-cell/myoblast 相关；
- 至少 5 篇有可抽取剂量/range；
- 至少 3 篇报道 serum-free 或 animal-component-free bovine muscle-cell culture；
- background-only 文献不能算作湿实验证据。

### Phase 3：全文抽取

目标：把文献转为结构化、可追踪的数据。

- [ ] `[AI]` 导入 BibTeX、PDF 或全文。
- [ ] `[AI]` 对 P1/P2 文献运行 triage 和 extraction。
- [ ] `[AI]` 导出 screening、component、evidence、extraction 表。
- [ ] `[AI]` 记录 extraction coverage 和 grounding rate。
- [ ] `[复核]` 标出稀疏、不可信或失败的抽取。
- [ ] `[AI]` 只有在确认是 parser/prompt 问题时才修代码；如果是文献内容缺失，
  不要假装修代码能解决。

命令：

```bash
cultivate ingest
cultivate triage
cultivate extract --tier A
cultivate export
```

预期导出：

- `screening_table.csv`
- `medium_components.csv`
- `evidence.csv`
- `extractions.jsonl`

`[门槛]` 抽取可靠性通过条件：

- top records 的 evidence quote grounding rate >= 0.95；
- 关键字段 non-missing fraction >= 0.75；
- 每个进入设计空间的成分都要能追溯到 source quote 和 normalized record。

### Phase 4：人工证据复核

目标：把 AI 抽到的证据变成可信科学证据。

- [ ] `[人工]` 优先复核 `bovine_human_review_queue.tsv` 中的 `H001-H016`。
- [ ] `[人工]` 给每项标记 `supported`、`partial`、`unsupported`、
  `uncertain` 或 `defer`。
- [ ] `[人工]` 写简短 notes：formulation、dose、endpoint、caveat、
  或排除原因。
- [ ] `[AI]` 把人工 notes 整理成结构化 adjudication table。
- [ ] `[复核]` 解决 AI 抽取和人工阅读之间的冲突。
- [ ] `[记录]` 更新 `docs/BOVINE_CORPUS_MANIFEST.md` 里的 gate 状态。

建议人工复核顺序：

1. Beefy-9、FGF2 降低、albumin 剂量/成本；
2. chemically defined bovine medium 和 differentiation capacity；
3. commercial SFM benchmark；
4. spent-media species/cell-type dependence；
5. DOE/RSM bovine serum-free media；
6. albumin substitutes、protein isolate、hydrolysate；
7. safety 和 cost annotations。

`[门槛]` 所有进入第一轮实验设计的变量，必须有人类复核支持，或者明确标为
exploratory。

### Phase 5：候选变量和 search space

目标：定义优化器允许改变什么。

- [ ] `[AI]` 根据复核后的证据建立候选变量类。
- [ ] `[AI]` 给每个变量标注 mechanism class。
- [ ] `[AI]` 标注 cost class、animal-origin status、food-grade plausibility、
  supplier risk。
- [ ] `[人工]` 确认实验室能买到/能用哪些试剂。
- [ ] `[实验]` 确认细胞来源、baseline medium、plate format、assay duration、
  measurement capacity。
- [ ] `[复核]` 移除机制不清、组成不透明、供应/安全风险过高的变量。

候选变量通常控制在 4-6 类，例如：

- basal medium choice or simplification；
- FGF2 concentration；
- insulin/transferrin/selenium axis；
- albumin or albumin substitute；
- lipid/fatty-acid carrier；
- amino-acid/metabolic supplement；
- evidence-gated hydrolysate or extract。

`[门槛]` search space 必须有边界、可控、可采购、且有证据支撑。

### Phase 6：in-silico robustness 和设计包草案

目标：确认第一轮实验不是某一篇文献、某一个检索器或某一个优化器的偶然产物。

- [ ] `[AI]` 比较 BM25 和 embedding retrieval 的证据簇。
- [ ] `[AI]` 用 q-ParEGO 和 qLogNEHVI 做优化器扰动。
- [ ] `[AI]` 做 leave-one-source-out sensitivity。
- [ ] `[AI]` 生成第一版 candidate formulation table。
- [ ] `[复核]` 检查重复设计、过度外推、 unsupported claims、
  或被更便宜方案支配的候选。
- [ ] `[人工]` 批准或修改候选变量和 controls。

`[门槛]` 通过条件：

- top variable classes 在检索/优化扰动下至少 70% 重合；
- 非 exploratory 的关键变量不能只靠一篇文献支撑；
- 分歧被明确记录；
- 第一轮 batch 包含 controls，且没有大量近重复候选。

### Phase 7：湿实验预注册

目标：实验开始前冻结问题、候选和分析方法。

- [ ] `[AI]` 起草 pre-registration packet。
- [ ] `[实验]` 确认 reagent list 和配制限制。
- [ ] `[实验]` 确认细胞来源、passage window、seeding density、culture duration、
  media-change schedule、plate format、replicate count。
- [ ] `[人工]` 确认 primary endpoint 和 secondary endpoints。
- [ ] `[复核]` 在任何结果出现前冻结候选 formulations。
- [ ] `[记录]` 把 design packet commit 到 git。

最小 design packet：

- biological target and scope statement；
- 文献纳入/排除标准；
- candidate formulation table；
- positive、negative、baseline controls；
- endpoint definitions；
- replicate plan；
- stopping/failure criteria；
- planned analysis；
- caveats and unsupported claims；
- 支持每个变量的 exact citations。

`[门槛]` design packet commit 之后，湿实验才能开始。

### Phase 8：湿实验执行

目标：按预注册方案执行，不边做边改问题。

- [ ] `[实验]` 按冻结 protocol 准备细胞和试剂。
- [ ] `[实验]` 记录 plate map、reagent lots、operator、passage number、
  seeding density、时间点。
- [ ] `[实验]` 保存 raw measurements 和必要 raw images。
- [ ] `[人工]` 立即记录任何偏离 protocol 的情况。
- [ ] `[复核]` 判断偏离是否导致实验无效、需要限定解释，还是只需记录。
- [ ] `[记录]` 大文件放 git 外，metadata 和 result manifest 进 git。

不要在同一轮中途调 formulation。需要改，就开新一轮并重新预注册。

### Phase 9：结果处理、比较和评价

目标：把实验结果与 controls 和目标进行比较。

- [ ] `[AI]` 把 raw results 整理为结构化结果表。
- [ ] `[AI]` 只做 within-experiment normalization。
- [ ] `[AI]` 计算 primary endpoint、secondary endpoints 和成本估计。
- [ ] `[AI]` 与 baseline 和 positive controls 比较。
- [ ] `[AI]` 更新 Pareto front：proliferation vs cost vs identity retention。
- [ ] `[人工]` 检查统计结果是否符合生物学解释。
- [ ] `[复核]` 给每个结论标记 supported、partial、unsupported 或 exploratory。

不能把湿实验结果和异质文献 outcome 直接当作同一标签比较。文献定义搜索空间，
真正的 objective values 来自自己的实验。

### Phase 10：闭环更新

目标：用实测结果决定下一轮实验。

- [ ] `[AI]` 把实测 objective values 输入 `optimize.tell()`。
- [ ] `[AI]` 在同一 search space 或有记录的新 search space 中生成下一轮候选。
- [ ] `[复核]` 检查模型是在 exploitation、exploration，还是重复失败区域。
- [ ] `[人工]` 决定继续一轮、缩小 search space、增加 assay，还是停止。
- [ ] `[记录]` commit round summary 和下一轮 design packet。

`[门槛]` 新一轮湿实验必须重新预注册。

### Phase 11：论文级分析和写作

目标：把系统和实验变成可以投稿/答辩/组会汇报的完整证据链。

- [ ] `[AI]` 生成最终表格：corpus、evidence、variables、formulations、
  results、Pareto comparison、sensitivity checks。
- [ ] `[AI]` 生成图：workflow、literature evidence map、variable support、
  experimental outcomes、Pareto front、closed-loop trajectory。
- [ ] `[人工]` 写生物学解释和 limitations。
- [ ] `[复核]` 每个 claim 都要能追溯到文献证据或湿实验数据。
- [ ] `[复核]` 诚实报告 negative 或 inconclusive results。
- [ ] `[记录]` 归档代码 commit、数据 manifest、分析脚本和 protocol 版本。

论文结论只能说 gate 证明了的事情：

- 文献挖掘流程可追踪；
- search space 有证据支撑；
- wet-lab batch 是预注册的；
- 实测结果相对 controls 的提升、失败或 trade-off 如数据所示；
- 系统在多大程度上减少试错，必须由实验设计和结果支持。

## 并行工作方式

可以并行，但不同角色要写不同文件，避免冲突。

### 人工线

- [ ] 复核 `H001-H016`。
- [ ] 确认细胞来源和 assay 限制。
- [ ] 确认试剂可获得性和预算上限。
- [ ] 批准第一版候选变量类。
- [ ] 湿实验前签字确认 pre-registration packet。

### AI 线

- [ ] 拉取和整理 P1 全文。
- [ ] 抽取 component tables、dose ranges、endpoints、quotes。
- [ ] 建立 `bovine_evidence_table.tsv`。
- [ ] 把人工 notes 整理为 adjudicated evidence records。
- [ ] 生成 candidate variable classes。
- [ ] 跑 retrieval 和 optimizer robustness checks。
- [ ] 起草 design packet 和分析报告。

### 实验线

- [ ] 确认细胞来源、passage limits、培养限制。
- [ ] 确认 control media 和 assay protocol。
- [ ] 确认 throughput：每轮条件数和重复数。
- [ ] 只执行已经冻结并 commit 的 design。
- [ ] 按约定格式返回 raw results。

### 冲突避免规则

- 同一批 TSV 行不要多人同时改。
- AI 不能覆盖人工 notes。
- 人工决策优先于 AI 建议，但必须记录。
- 改 scope 必须写 decision record。
- wet-lab design 必须在结果出现前 commit。
- 不允许用结果倒改预注册方案。

## 当前状态快照

### 已完成

- [x] 项目是 CLI-first Python package。
- [x] 最新测试：`.venv/bin/python -m pytest -q` 为 26 passed，3 个已知 warnings。
- [x] smoke pipeline 通过。
- [x] demo optimization loop 通过。
- [x] extraction evaluator 已有。
- [x] 四篇真实文献的 offline evaluation fixture 已有。
- [x] embedding retriever 已有。
- [x] BoTorch qNEHVI 和 qLogNEHVI backend 已有。
- [x] optional citation verifier 已有。
- [x] ontology-to-search-space 已扩展到 hydrolysate、extract、
  defined supplement、albumin substitute 等类别。
- [x] extraction evaluation 已支持 live provider mode。
- [x] parser 已支持 A-M block letters 和 schema attribute block names。
- [x] 第一阶段 wet-lab-facing target 已决策并记录。
- [x] bovine-focused manifest v0 已有，44 条记录。
- [x] human review queue v0 已有，30 个 open tasks。
- [x] 英文项目总流程 `docs/PROJECT_WORKFLOW.md` 已有。
- [x] 中文项目总流程 `docs/PROJECT_WORKFLOW_ZH.md` 已有。

### 已发现问题

- [ ] OpenAI/Anthropic live extraction 太稀疏，不能算成功模型一致性结果。
- [ ] Gemini live comparison 未完成，因为没有 Gemini/Google key。
- [ ] OpenAI raw-response debug 遇到 quota 不足。
- [ ] 当前 corpus manifest 还没有全文抽取。
- [ ] human review queue 仍全部 open。
- [ ] cost、supplier、food-grade annotations 还没补全。
- [ ] in-silico robustness 还没在 bovine manifest 上运行。
- [ ] 尚未生成或冻结 wet-lab design packet。
- [ ] 尚无湿实验结果。

### 当前最优下一步

1. `[AI]` 拉取所有 P1 core records 的全文。
2. `[AI]` 抽取 exact formulations、dose ranges、endpoints、quotes。
3. `[人工]` 复核 H001-H016。
4. `[AI]` 建立 adjudicated bovine evidence table。
5. `[复核]` 决定哪些变量能进入第一轮 search space。
6. `[AI]` 生成第一版 design packet 草案。

## 给其他 AI 的接管规则

任何 AI 接手时，按顺序读：

1. `README.md`
2. `docs/PROJECT_WORKFLOW_ZH.md` 或 `docs/PROJECT_WORKFLOW.md`
3. `docs/SESSION_LOG.md`
4. `docs/LITERATURE_DECISION_RECORD_WETLAB_ENTRY.md`
5. `docs/BOVINE_CORPUS_MANIFEST.md`
6. `git status --short --branch`

不要在 gate 没过时宣称项目完成。不要覆盖人工 notes。不要扩大 scope，除非写了新的
decision record。

推荐接管 prompt：

```text
请继续 CultivateAgent，使用 docs/PROJECT_WORKFLOW_ZH.md 作为控制流程。
除非新增 scope-change decision record，否则保持当前 bovine satellite-cell/myoblast
扩增培养基优化目标。先检查 git status，再推进下一个未完成 gate。不要覆盖人工复核 notes。
```

## Gate 总表

| Gate | 通过条件 | 当前状态 |
|---|---|---|
| Phase 0 环境 | tests/smoke 通过或 blocker 已记录 | pass |
| 目标锁定 | target 和边界已记录 | pass |
| corpus coverage | 文献数量和类型满足要求 | partial |
| extraction reliability | 抽取 grounded 且不稀疏 | fail |
| human review | top variables 已人工复核 | fail |
| search space | 变量有边界、可采购、有证据 | fail |
| in-silico robustness | 检索/优化扰动稳定 | fail |
| pre-registration | wet-lab 前 design packet 已 commit | fail |
| wet-lab execution | 冻结 protocol 已执行且偏差有记录 | not started |
| result comparison | raw results 已与 controls/objectives 比较 | not started |
| manuscript audit | claims 可追溯到证据和数据 | not started |
