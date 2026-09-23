<div align="center">
  <img src="assets/cover.png" alt="HeiGe-SuanMing · 像做技术分析一样算命" width="100%">
</div>

# HeiGe-SuanMing

> **作者说明**
>
> 我是这个项目的作者。开发到当前版本后，我回看这些测算结果时，发现它们在一些时候显得过于准确，容易让人产生很强的现实对应感。出于谨慎，我决定不再继续开发更细、更强的预测功能。
>
> 目前项目保留的能力，大家可以自行测算，建议纯当作娱乐和自我观察参考。结果如有相似，请当作巧合，不要把它当成确定的人生判断，也不要据此做医疗、法律、投资或其他重大决定。
>
> 希望大家多起一些好的念头，保持行动，给自己创造一个更好的未来。这个项目后续暂不再更新，感谢理解。

<div align="center">

![Skill](https://img.shields.io/badge/skill-1.18.0-7c3aed.svg)
![Engine](https://img.shields.io/badge/engine-1.5.0-0e7490.svg)
![Agents](https://img.shields.io/badge/agents-universal-orange.svg)
![Recommended](https://img.shields.io/badge/recommended-Claude%20Opus%204.8-d97706.svg)
![License](https://img.shields.io/badge/license-PolyForm%20NC-64748b.svg)

**黑哥算命 · 八字/紫微命理排盘推演 + 占测引擎（梅花 · 六爻 · 奇门遁甲）+ 手机号八星结构分析 | Bazi & Zi Wei Dou Shu destiny engines, Meihua, Liu Yao & Qi Men Dun Jia divination engines, plus an independent phone-energy analyzer, that compute first, then reason**

像做技术分析一样算命：排盘、起卦、装卦交给脚本算准，推演按固定方法论逐层展开，每个结论都标注依据。

[先选需求](#先选需求) • [快速开始](#快速开始-quick-start) • [这是什么](#这是什么-what-is-this) • [为什么不一样](#为什么不一样-why-its-different) • [核心方法论](#核心方法论-methodology) • [知识底座](#知识底座-knowledge-base) • [命盘样例](#命盘样例-sample) • [可视化命书](#可视化命书-visual-report) • [多 Agent 支持](#多-agent-支持-works-with-any-agent) • [免责声明](#免责声明-disclaimer)

</div>

## v1.18.0 更新：手机号八星报告先看结果，再看解读

新增并完善独立的手机号八星结构分析引擎 `scripts/phone_energy.py`，当前引擎版本为 `0.2.0`。输入手机号、车牌、门牌或其他数字串后，报告会先展示脱敏号码、相邻数字拆分、八星分布、主导主题和尾部组合，再用白话解释这些标签可能对应的日常场景，并给出可以试做七天的小行动。

报告默认不写入完整手机号，数字对、规则 profile、解读文案和行动建议分别保留，方便复核计算依据。手机号八星与八字、紫微、梅花、六爻、奇门保持独立，不会自动合并成一个命运分。原有标准报告末尾的功能提示继续保留，用户选择后才执行。

正式版本：[v1.18.0](https://github.com/HeiGeAi/HeiGe-SuanMing/releases/tag/v1.18.0)。手机号八星输入契约与规则边界见 [`references/24_phone_energy.md`](references/24_phone_energy.md)，标准报告提示见 [`references/23_report_next_steps.md`](references/23_report_next_steps.md)。

## 先选需求

先区分「根据生辰看命盘」和「问一件具体的事」。选一个入口即可，无需一次运行全部引擎。

| 你想做什么 | 入口 | 一次准备这些信息 |
| --- | --- | --- |
| 根据生辰看整体命盘，或只看事业等一个维度 | 八字 `scripts/paipan.py` | 出生年月日、阳历或农历、性别；已知时分、出生地和当时的时区一并提供 |
| 看紫微十二宫、四化与大限 | 紫微 `scripts/ziwei.py` | 出生年月日、历法、出生时辰、性别；农历注明是否闰月 |
| 比较两人的相处模式 | 八字合参 `scripts/paipan.py` | 两人的生辰分别填写，历法、时区、地点不能相互代用；不知道的时辰明确写未知 |
| 问一件事，已有数字或指定起卦时间 | 梅花 `scripts/meihua.py` | 具体问题、关注期限，以及两个正整数或起卦年月日时 |
| 已摇好六次卦，想装卦解读 | 六爻 `scripts/liuyao.py` | 具体问题、起卦日期时间，六次结果按初爻到上爻填写（6、7、8、9） |
| 用奇门看某个时刻的一件事 | 奇门 `scripts/qimen.py` | 具体问题、起局年月日时分；明确时间口径，已指定排局法时一并说明 |
| 分析手机号、车牌或其他数字串的八星结构 | 手机号八星 `scripts/phone_energy.py` | 数字串和类型（手机号、车牌、门牌或通用数字）；不需要出生日期 |

给 Agent 的可复制示例（以下均为演示输入）：

```text
读取本项目 SKILL.md。按八字看事业：公历 2000 年 8 月 16 日 03:30，女，上海，UTC+8。
先给三句话结论，再列主要依据与局限，完成对应主题的 HTML 命书。
```

```text
读取本项目 SKILL.md。用梅花数字起卦，数字 34、43。
我问的是未来一个月的求职进展，关注面试准备与现实行动；先给简短解读和依据。
```

**信息不全时会怎样：**八字不知道出生时间可以只排年月日三柱；紫微需要出生时辰，不能借用三柱模式。未提供出生地或时区时，不声称已完成真太阳时或历史时区校正。脚本不会自动识别地点对应的历史夏令时，`--china-dst` 仅提示核对，不替你修改钟表时间。非法日期、不存在的闰月、超出支持范围的日期应先纠正，不能补造一个命盘继续解释。

脚本计算与固定用例通过测试，说明结果可复现；不代表命理或占测具有经验证的预测效度。准备好后进入[快速开始](#快速开始-quick-start)。

---

## 这是什么 What is this

HeiGe-SuanMing 是一个**四柱八字命理引擎**，并内置**紫微斗数**第二命理引擎（批一生）、**梅花易数**、**六爻纳甲**、**奇门遁甲**三个占测引擎（占一时一事），以及一个独立的**手机号八星数字结构引擎**，能跑在任何"会读文件 + 能调 Python"的 AI Agent 里（推荐 Claude Code + Claude Opus 4.8）。八字部分把算命拆成两层：

**第一层：排盘用脚本算，绝不靠模型手推。**
`scripts/paipan.py` 基于 `lunar_python` 做精确干支推算，自动处理三件最容易错的事：以**立春**定年柱（不是正月初一）、以**节气**定月柱（不是农历月）、在明确经度与时区后按**真太阳时**校正时柱。再往上算齐藏干、十神、纳音、长生十二宫、旬空、胎元命宫身宫、地支刑冲合会、五行力量加权、神煞、大运流年。

**第二层：推演按固定方法论走，结论必带依据。**
`SKILL.md` 规定了严密顺序：定旺衰 → 取用神 → 判格局 → 析岁运 → 落十神六亲 → 分维度断语。每一条断语后面都注明推理链（出自哪个十神、哪个宫位、哪步大运），孤证不立，中间推理全程透明。

一句话：**让排盘可复现、让推演有据可查。**

### 它能做什么

- ✅ **精确排盘**：立春定年、节气定月、真太阳时校正，闰月（负数月输入，如 `-2` = 闰二月）与子时流派可选，支持公历 1600-2200 年
- ✅ **旺衰量化**：五行力量加权打分，给出同党异党参考，再结合月令通根综合定档
- ✅ **取用神**：调候（穷通宝鉴）+ 扶抑 + 通关 + 病药，五法择用
- ✅ **判格局**：八格成败救应，从格 / 专旺 / 化气 / 魁罡等特殊格局核验
- ✅ **大运流年**：自动顺逆起运、逐步十神，引动用神还是忌神一目了然；可用 `--target-date` 把应期细到流月流日干支事实（断语止于月，不做每日吉凶）
- ✅ **分维度详断**：性格 / 事业 / 财运 / 婚姻 / 健康 / 学业 / 六亲，逐条带依据
- ✅ **趋避建议**：用神落到方位、颜色、行业、注意事项，务实不玄
- ✅ **养生调养**：按用神喜忌 + 寒暖燥湿体质，给针对性的作息、饮食、情志、运动建议，认准用神、缺啥补啥是误区，参考非医嘱
- ✅ **色彩服饰**：用神色落到衣着、首饰、配饰、随身物、居家办公，以颜色为主轴、宝石按色参考，审美优先、不承诺转运
- ✅ **合婚合参**：双盘对照夫妻星宫、用神互补、日柱年支合冲、大运同步，只断相处模式与磨合点，不打分、不下「合 / 不合」判词
- ✅ **可视化命书**：推演完成后自动生成一页东方雅致的 HTML 命书并直接打开，便于保存、回看、分享（断语与文字版逐字一致，只要文字版说一声即可）；每个内容区块配**「黑哥解读」白话框**，把伤官、调候、值符这类专业术语逐个翻译成普通人能看懂的话
- ✅ **梅花易数占卜（第二引擎）**：时间 / 数字 / 物象起卦，脚本算准本卦互卦变卦与体用定位，按体用生克断一件事的顺逆与过程，占卜非命理、一事一占、趋势化不打分
- ✅ **六爻纳甲占卜（第三引擎）**：摇卦装卦全交脚本（纳甲干支、八宫世应、六亲、六神、动变卦、月建日辰旬空），按用神旺衰与动静生克细断一事，装卦定式以京房体系回归测试钉死
- ✅ **紫微斗数安星（第四引擎）**：十二宫定位、五行局、紫微天府双星系、四化、六吉、禄存、六煞、大限小限、**命主身主、宫干飞化与离心向心自化、大限四化**交脚本按已测试口径计算；选定固定锚点曾与 iztro 2.5.8 显式配置比对，边界差异已记录
- ✅ **奇门遁甲排局（第五引擎）**：时家转盘排局交脚本按已测试口径计算（**拆补与置闰双排局法**、地盘三奇六仪、旬首值符值使、天盘九星、八门飞宫、八神、旬空驿马、星门伏吟反吟），并输出**断局标注层**（逐宫十干克应、九星旺衰、击刑入墓门迫、格局清单、五不遇时）；置闰法有 35 项固定期望电池，但外部 oracle 的原始快照与版本仍需后续补档
- ✅ **手机号八星结构分析（独立引擎 v0.2.0）**：按相邻数字对识别八星（天医、生气、延年、伏位、绝命、祸害、五鬼、六煞），输出主导星、吉凶结构、尾部组合、0/5 修饰、未识别数字对和规则依据；默认脱敏，不保存完整手机号，不混入出生日期命理

### 适合谁

- 想认真研究八字、对**推理过程透明度**有要求的人
- 算过命但受够了"铁口直断、只给结论不给依据"的人
- 想用一套**可复现、可审计**的方式做自我认知参考的人

---

## 为什么不一样 Why it's different

市面上的算命，痛点通常在两头：排盘容易算错，推演无从复盘。这个引擎把两头都钉死。

| 维度 | 手推 / 普通 AI 算命 | HeiGe-SuanMing |
|---|---|---|
| **排盘** | 常错在正月初一定年、农历月定月、忽略真太阳时 | 脚本精确推算，立春定年 + 节气定月 + 真太阳时校正 |
| **旺衰** | 拍脑袋说身强身弱 | 五行加权打分 + 月令通根综合，临界值回到细节辨 |
| **结论** | 铁口直断，只给结果 | 每条断语标注推理链，出自哪个十神 / 宫位 / 用神 |
| **佐证** | 单一信号就下死断 | 一象多看，至少两处佐证（星 + 宫，或 原局 + 岁运） |
| **过程** | 黑箱，无法复盘 | 旺衰打分、取用逻辑、格局成败全程展示 |
| **语气** | 承诺祸福、贩卖焦虑 | 趋势化表达（易 / 倾向 / 利于 / 需注意），落到趋避建议 |

核心差别就一句：**它把"为什么这么断"全摊开给你看。**

---

## 核心方法论 Methodology

引擎遵循一套固定顺序，**先定旺衰用神，再谈一切**，顺序不可乱：

```
第 0 步  收集确认输入（阳历/农历、时间、性别、出生地经度）
第 1 步  精确排盘：运行 paipan.py，完整命盘呈现为事实基础
第 2 步  读盘定盘面：日主、月令、地支刑冲合会逐一标出
第 3 步  判旺衰：月令 / 通根 / 生扶 / 党众 / 定档（五看）
第 4 步  取用神：调候 ≥ 扶抑 > 通关 > 病药（五法）
第 5 步  判格局：八格取法、成败救应、特殊格局核验
第 6 步  析岁运：大运流年引动用神还是忌神，定应期
第 7 步  落宫位：十神六亲落年月日时，看刑冲合害
第 8 步  分维度：性格/事业/财运/婚姻/健康/学业/六亲，逐条带依据
第 9 步  趋避与调养：用神落到方位、行业，再给色彩服饰（穿戴随身环境）与作息饮食情志的个性化建议
第 10 步 总评：3-5 句收束命局核心结构与一生大势
第 11 步 可视化：（默认交付）把整份命书自动做成一页 HTML 报告，给出路径并直接打开
第 12 步 功能提示：报告末尾固定列出其他功能、用途、示例说法和所需信息，用户选择后再展开
```

> **交互范式：先选目标、一次补齐必要信息，核心自动完成。** 输入足够后，排盘、与问题相关的推演、HTML 命书连续交付。先看短结论，再看依据和完整报告；只问事业就聚焦事业，额外合婚、养生详单或其他引擎不会自动全部展开。

知识底座放在 `references/`，推演时按需调用：

| 文件 | 内容 |
|---|---|
| `00_gainian_suoyin.md` | 概念→篇目检索索引：按推演步骤 / 核心概念 / 典籍溯源定位该读哪篇，不知看哪篇先查这里 |
| `01_paipan_jichu.md` | 干支五行阴阳、地支藏干、十神生成、长生十二宫、刑冲合害会 |
| `02_wangshuai_yongshen.md` | 旺衰五看、取用神五法、**流派仲裁决策树**（多用神候选听谁的）、用神喜忌定义、常见误区 |
| `03_tiaohou_qiongtong.md` | 穷通宝鉴十干分十二月调候用神速查表 |
| `04_shishen_xiangyi.md` | 十神类象、四柱宫位、六亲取用、分维度断法 |
| `05_geju.md` | 八格取法、成败救应、从格 / 专旺 / 化气等特殊格局 |
| `06_shensha.md` | 常用神煞查法、吉凶象义、使用原则 |
| `07_keshihua_baoshu.md` | 可视化命书：默认交付时机与输出规范、HTML 结构模板、黑哥解读白话框铁律、字体可靠性铁律、五行配色映射 |
| `08_gufu_duanyu.md` | 古籍赋文经验断语：渊海 / 三命 / 神峰赋诀分维度精选，短引＋白话＋调用提示 |
| `09_shenfeng_tongkao.md` | 神峰通考：病药说、动静说、盖头截脚、伤官伤尽辨、十干体象、辟谬批判 |
| `10_mingli_yueyan.md` | 命理约言理性派：生克扶抑总纲、用神精神说、格局正变、神煞纳音小运胎元祛魅清单 |
| `11_sanming_tonghui.md` | 三命通会：旺相休囚死五态、寄生十二宫体用、十神立名、格局神煞集成纲目、大运太岁取法 |
| `12_dianji_yuanliu.md` | 典籍源流导航：宋明清民国 12 部命书的贡献、对应篇目、公版出处与调用路径 |
| `13_ditian_sui.md` | 滴天髓：衰旺真机、中和为贵、体用精神、极旺极衰辩证、气势顺逆通关、寒暖燥湿、任注实证 |
| `14_ziping_zhenquan.md` | 子平真诠：月令取格、顺逆取用、相神护格、成败救应、格局高低、用神变化、行运同看 |
| `15_yangsheng_tiaoyang.md` | 五行养生调养：把用神喜忌、缺失、过旺、寒暖燥湿，翻译成针对性的作息、饮食、情志、运动建议（认准用神，缺啥补啥是误区，参考非医嘱） |
| `16_secai_fushi.md` | 色彩服饰调候：把用神喜忌、寒暖燥湿，翻译成针对性的衣着、首饰、配饰、随身物、居家办公色彩与材质（认用神色，缺啥穿啥是误区；颜色为主轴、宝石按色参考不神化，参考非转运） |
| `17_hehun.md` | 正派合婚双盘合参：双方婚姻象 + 用神互补 + 日柱年支合冲 + 大运同步，只断相处模式与磨合点（禁打分、禁「合 / 不合」判词；属相相冲一票否决、合婚煞法等旧法不取） |
| `18_meihua_yishu.md` | 梅花易数占卜引擎（第二引擎，非命理）：起卦法、先天八卦数、体用生克断事、互变卦、卦气应期、八卦万物类象、《梅花易数》源流（占卜非命理、一事一占、不打分，配 `scripts/meihua.py`） |
| `19_liuyao.md` | 六爻纳甲占卜引擎（第三引擎，非命理）：摇卦装卦、纳甲八宫世应六亲六神、取用神六亲对照、旺衰动静生克、空亡月破应期、京房至《增删卜易》源流（配 `scripts/liuyao.py`） |
| `20_ziwei.md` | 紫微斗数安星引擎（第四引擎，命理）：十二宫定位、命宫干支五行局、紫微天府双星系（含天府定位公式纠错）、四化、六吉、禄存、六煞、大限小限、命主身主、宫干飞化与自化及断法框架层；选定锚点与 iztro 2.5.8 显式配置比对（配 `scripts/ziwei.py`） |
| `21_qimen.md` | 奇门遁甲排局篇（第五引擎，占测）：时家转盘排局（拆补与置闰双排局法、72 局表、三元符头公式、地盘三奇六仪、旬首值符值使、天盘九星、八门飞宫、八神、旬空驿马、星门伏吟反吟）；置闰法有 35 项固定期望电池，外部比对原始快照与版本尚未归档（配 `scripts/qimen.py`） |
| `22_qimen_duanju.md` | 奇门遁甲断局篇：用神体系与分事类定式、十干克应 81 组全表、吉凶格局判定条件、四害与旺衰、门星神吉凶、九步断局流程、应期十三法（引擎输出可计算标注，断语按此篇展开） |

其中 `00` 是概念检索入口，`01-07` 是推演主干，`08-14` 是经典典籍深化层，把方法论锚回《渊海子平》《滴天髓》《穷通宝鉴》《子平真诠》《三命通会》《神峰通考》《命理约言》等原典，《滴天髓》《子平真诠》两大主干更各有专篇（`13`、`14`）；`15`、`16` 是第 9 步的调养落地篇，把用神喜忌翻译成作息饮食情志（`15`）与色彩服饰（`16`）建议，`17` 是正派合婚双盘合参篇，`18`、`19`、`21`、`22` 是占测引擎篇（梅花易数、六爻纳甲、奇门遁甲排局与断局，占一时一事，与八字命理分属不同门类），`20` 是紫微斗数命理引擎（批一生，安星+命主身主+飞化）。这一层结构化、带出处、可直接读取，任何模型（不限于 Claude）接上 `references/` 都能据此推演，断准度有据可依。古籍多托名辑录，文中凡有争议处均标「存疑」，引用前先认版本。

---

## 知识底座 Knowledge Base

算得准的前提是**有典可循、有例可照、有测可验**。这套引擎的底座做了四件事，让推演经得起追问：

**一、把方法论锚回原典。** `references/08-14` 七篇深化层，把每个论断都接回《渊海子平》《滴天髓》《穷通宝鉴》《子平真诠》《三命通会》《神峰通考》《命理约言》。旺衰中和派的《滴天髓》（`13`）与格局派的《子平真诠》（`14`）两大主干各立专篇，原文＋白话＋调用提示俱全，引用前先认版本、争议处标「存疑」，孤证不立。

**二、四个完整命例照着学。** `cases/` 收了 4 个脱敏命例，覆盖 4 个日主、4 种旺衰结构（身强用财官 / 身弱用印比 / 调候为急 / 专旺候选与常格复核）。每例都是 `paipan.py` 实跑真盘＋第 0 到 10 步走全＋每条断语带依据，是把方法论落到一个真盘的最佳模板。

**三、多用神冲突有决策树仲裁。** 调候、扶抑、格局、病药各执一词时该听谁的？`references/02` 给了一条五级优先级阶梯（先验从格 → 再急调候 → 扶抑定向 → 格局定点 → 病药校验），把流派之争收敛成一套可执行的取舍顺序。

**四、排盘边界有回归测试兜底。** `tests/` 共 434 个测试（八字 158 + 梅花 49 + 六爻 43 + 紫微 72 + 奇门 75 + 手机号八星 23 + 命例复现 8 + 发布契约 6）。八字覆盖日期变更线、合婚乙方独立时区与完整双盘、节气秒级边界；梅花锁定农历小月、闰月与换算后年份；六爻锁定两种子时换日口径与默认值兼容；紫微锁定闰月十五、十六分界、晚子时及立春交接时刻；奇门直接断言跨年符头完整六元组、非法干支有界失败，以及置闰阈值保存与输出重放；手机号八星锁定相邻数字对、0/5 修饰、隐私脱敏、短号码、CLI、白话解读库、未分类边界、排序和 HTML 报告边界。四个命例的输出与文档中的命令逐字比对，正文的十神、藏干、起运、大运与流年事实也与引擎对照，专旺候选须披露缺少的组合条件；HTML 示例盘面及大运星运与引擎对照；既有古法定式、节气、未知时辰、大运、飞化、固定盘等回归继续保留。测试证明固定输入符合仓库中的预期，不等于覆盖所有年份、所有流派或独立证明外部 oracle；改动脚本后仍须运行 `./.venv/bin/python -m unittest discover -s tests`。

---

## 命盘样例 Sample

输入 `1990 年 5 月 15 日 14:30 男，出生地中国广州`，调用方已明确启用 `--china-dst` 核时提示，脚本输出（节选）：

```
════════════════════ 八字命盘 ════════════════════
公历：1990-05-15 14:30　性别：男　生肖：马　星座：金牛
农历：一九九〇年四月廿一
节气：立夏（1990-05-06）后第 9 天，下一节气 小满
夏令时：出生于 1990 年中国夏令时实施期（4/15–9/16，钟表较北京标准时快 1 小时）。若所记为当时钟表时间，真实时间应减 1 小时再定时柱，请核对。

【四柱】     年柱    月柱    日柱    时柱
  天干十神   比肩    劫财    日主    伤官  
  天干       庚(金)    辛(金)    庚(金)    癸(水)
  地支       午(火)    巳(火)    辰(土)    未(土)
  藏干       丁己     丙戊庚    戊乙癸    己丁乙  
  藏干十神   正官/正印   七杀/偏印/比肩   偏印/正财/伤官   正印/正官/正财  
  星运       沐浴      长生      养       冠带  
  纳音       路旁土    白蜡金    白蜡金    杨柳木  
  旬空       戌亥      申酉      申酉      申酉  

【日主】庚金，生于 巳（火） 月令
【胎元】壬申　【命宫】辛巳　【身宫】己丑

【地支刑冲合会】
  六合：年午·时未→合火/土
  三会：巳午未三会火方(年午·月巳·时未)

【五行个数】木0　火2　土2　金3　水1　｜缺：木
【五行力量】（天干1 / 藏干本气1·中气0.5·余气0.2 / 月支司令×2）
  木:0.7  火:3.5  土:3.5  金:3.4  水:1.2
  同党(扶日主)=6.9  [比劫(金)3.4 + 印(土)3.5]
  异党(耗日主)=5.4  [食伤(水)1.2 + 财(木)0.7 + 官杀(火)3.5]
  同党占比 56% → 量化参考：偏强（最终旺衰须结合月令得失·通根透干·刑冲合会综合判断）

【神煞】天乙贵人(时)　天德贵人(月)　月德贵人(年·日)　将星(年)　华盖(日)　魁罡(日)　寡宿(日)

【大运】顺排　8岁起运（虚岁，1997-08-04）
  幼运 1-7岁（1990-）
  壬午　 8-17岁　1997年起　[食神/正官/正印]　星运:沐浴
  癸未　18-27岁　2007年起　[伤官/正印/正官/正财]　星运:冠带
  甲申　28-37岁　2017年起　[偏财/比肩/食神/偏印]　星运:临官
  ……（后续大运与流年略）
```

脚本只负责把这些**事实**算准。拿到命盘后，Claude 再按方法论逐层推演旺衰、用神、格局、岁运，给出带依据的断语。

---

## 可视化命书 Visual Report

<p align="center">
  <a href="https://raw.githack.com/HeiGeAi/HeiGe-SuanMing/main/examples/%E7%A4%BA%E4%BE%8B-%E5%85%AB%E5%AD%97%E5%91%BD%E4%B9%A6.html"><img src="assets/visual-hero.jpg" alt="可视化命书 · 卷首命格诗" width="100%"></a>
  <br><sub>点图在线预览完整命书长卷 · 卷首命格诗四句点出命局核心（虚拟生辰演示）</sub>
</p>

完成当前主题所需计算与推演后，Agent 会把对应文字报告做成**一页可视化 HTML** 端到你面前：写入工作目录、给出路径、能打开就顺手帮你打开。只想要文字版，说一声就停在文字版。

它把文字推演原样"呈现"成一卷东方雅致的命书长卷，不为排版另造任何结论：

- **一页长卷**：卷首命格诗、命盘全图、五行能量条、旺衰用神、大运时间轴、流年逐年、分维度详断、趋避清单、色彩服饰、养生调养、综合总评，一屏一主角顺次铺开
- **签名时刻**：把命局命门（最关键的用神或缺神）单字放大成全屏主视觉，一眼记住这盘的钥匙
- **字体零塌**：思源宋体为骨架、系统宋体兜底，断网或加载失败也工整不掉字；层次靠字重拉开，不赌未必预装的书法体
- **依据随行**：每个断语块保留依据标签（如 `伤官透月干为用`），与文字版推理链逐字一致
- **可脱敏**：对外分享可换虚构生辰重新排盘、断语写通用向，不留可对号入座的隐私

<p align="center">
  <a href="https://raw.githack.com/HeiGeAi/HeiGe-SuanMing/main/examples/%E7%A4%BA%E4%BE%8B-%E5%85%AB%E5%AD%97%E5%91%BD%E4%B9%A6.html"><img src="assets/visual-sig.jpg" alt="签名时刻 · 满盘五火独缺一水" width="100%"></a>
  <br><sub>签名时刻：本例满盘五火、独缺一水，命门「水」单字放大成全屏，过目不忘（点图在线预览）</sub>
</p>

想看完整效果，点 **[在线预览](https://raw.githack.com/HeiGeAi/HeiGe-SuanMing/main/examples/%E7%A4%BA%E4%BE%8B-%E5%85%AB%E5%AD%97%E5%91%BD%E4%B9%A6.html)**（raw.githack 实时渲染，无需克隆；在 GitHub 上直接点 `.html` 只会看到源码，这是 GitHub 不渲染网页的限制）。源码见 [`examples/示例-八字命书.html`](./examples/示例-八字命书.html)，方法论与结构模板见 [`references/07_keshihua_baoshu.md`](./references/07_keshihua_baoshu.md)。

> 先完成当前主题的计算与有依据的解释，再制作 HTML。完整命书走第 0 至 10 步，单维度报告保留必要基础并聚焦该主题。只求排盘、JSON 或明确纯文字的任务按用户范围交付。

---

## 快速开始 Quick Start

先把完整仓库和 Python 依赖准备好，再让 Agent 读取 `SKILL.md`。下列步骤在项目自己的虚拟环境安装依赖，不需要修改系统 Python。

### 1. 克隆完整仓库并安装依赖

macOS／Linux（终端中运行，需要先安装 Git 和 Python 3）：

```bash
git clone https://github.com/HeiGeAi/HeiGe-SuanMing.git bazi-mingli
cd bazi-mingli
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
./.venv/bin/python scripts/paipan.py --version
```

Windows（PowerShell，需要先安装 Git 和 Python 3）：

```powershell
git clone https://github.com/HeiGeAi/HeiGe-SuanMing.git bazi-mingli
Set-Location bazi-mingli
py -3 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe scripts/paipan.py --version
```

Windows 如果未安装 `py` 启动器，用已安装的 Python 3 命令替换 `py -3`。两种方式均直接调用虚拟环境解释器，无需激活脚本或更改 PowerShell 执行策略。

### 2. 让 Agent 读取技能

在克隆目录打开 Agent，发送：

```text
请读取当前目录 SKILL.md，按我的目标选择引擎，并使用本项目 .venv 的 Python 执行脚本。
我要看八字事业方向：公历 2000 年 8 月 16 日，女，出生时间不知道，上海，UTC+8。
请按三柱说明可判断的部分和局限，完成对应主题的 HTML 命书。
```

若要安装为 Claude Code 技能，可把克隆目标改为其 skills 目录下的 `bazi-mingli`（macOS／Linux 常用 `~/.claude/skills/bazi-mingli`，Windows 对应用户目录的 `.claude\skills\bazi-mingli`），进入该目录再创建 `.venv`。技能被宿主识别后可输入 `/bazi-mingli`；没有识别时仍可用上面的「读取 SKILL.md」方式调用。其他 Agent 见[多 Agent 支持](#多-agent-支持-works-with-any-agent)。

输入时请区分「不知道」和「没填」。八字未知时辰会省略时柱及依赖它的判断，不会伪造精确起运日期。23 点附近、闰月、历史夏令时或跨时区出生，需要明确对应口径；缺失项会集中询问，已明确的信息不重复确认。

### 直接跑脚本（可选）

六个计算引擎脚本都可以脱离对话单独运行。以下在项目根目录执行，输出的是排盘、起卦或数字结构结果；推演与 HTML 命书由 Agent 按 `SKILL.md` 完成。

```bash
# 八字排盘
./.venv/bin/python scripts/paipan.py 2000 8 16 3 30 --gender female --lng 121.5 --tz 8
# 八字三柱盘（未知出生时辰）
./.venv/bin/python scripts/paipan.py 2000 8 16 --gender female
# 梅花易数起卦（数字起卦占一件事）
./.venv/bin/python scripts/meihua.py --numbers 34 43 --query "问未来一个月求职进展"
# 六爻装卦（23 点附近用 --zi-sect 明确换日口径，默认 2=午夜换日）
./.venv/bin/python scripts/liuyao.py --yao 787888 --date 2026 6 5 23 50 --zi-sect 2
# 紫微斗数安星（默认闰月十六日起按下一月安宫，生年干支按春节分界；23 点附近用 --zi-sect 明确晚子时取日口径，默认 2=不换日）
./.venv/bin/python scripts/ziwei.py 2000 8 16 3 30 --gender female --year-divide normal
# 奇门遁甲排局（时家转盘·拆补法）
./.venv/bin/python scripts/qimen.py 2026 7 9 10 30
# 手机号八星结构（JSON 默认脱敏，适合程序继续处理）
./.venv/bin/python scripts/phone_energy.py 138-123-45678 --kind mobile --json --pretty
# 手机号八星结构（排除国内手机号常见首位 1 后再分析）
./.venv/bin/python scripts/phone_energy.py 13812345678 --exclude-leading-one
# 手机号八星 HTML 报告（沿用项目命书视觉风格）
./.venv/bin/python scripts/phone_energy.py 13812345678 --html output/手机号八星报告.html
```

手机号八星当前使用 `eight_star_v1` 规则 profile。它按相邻两位数字重叠分析，识别八星组合并单独记录 `0`、`5` 的隐藏或增强修饰。HTML 报告先展示脱敏号码、相邻数字拆解、八星分布、主导主题和尾部结果，再使用独立的 `eight_star_reading_v1` 解读文案，把主题翻译成白话、生活场景、自查问题、沟通句式和七天行动练习。输出默认只保留脱敏号码、数字对和结构统计，不保存完整手机号；这套结构分析不需要出生日期，也不会自动与八字或其他引擎合并。完整输入契约和规则边界见 [`references/24_phone_energy.md`](references/24_phone_energy.md)，解读文案见 [`references/phone_energy_readings_v1.json`](references/phone_energy_readings_v1.json)。

Windows 将上述 `./.venv/bin/python` 换成 `.\.venv\Scripts\python.exe`，其余参数相同。八字的 `--tz` 与 `--lng` 不是其他引擎的通用参数；梅花、六爻、紫微和奇门不自动接收出生地并换算时区，调用前须确定其输入时间口径。

八字常用选项：`--lunar`（按农历，闰月用负数月表示，如 `-2` = 闰二月）、`--lng <经度>`（真太阳时，范围 -180~180，东经正西经负）、`--tz <时区偏移>`（出生地时区，默认 +8，配合 `--lng` 使用）、`--china-dst`（明确按中国 1986-1991 夏令时规则提示核时，不根据经度自动推断国别）、`--years <起始年> <年数>`（流年区间，默认从当前干支年或出生年中较晚者开始，按立春分界起 10 年）、`--target-date <年 月 日>`（指定日流年流月流日干支事实，断语止于月）、`--partner <年 月 日 [时] [分]>` 配 `--partner-lunar` / `--partner-gender` / `--partner-lng` / `--partner-tz` / `--partner-china-dst`（合婚双盘对照，乙方时辰可缺省，历法、地点、时区与夏令时口径独立声明）、`--json`（结构化输出）、`--zi-sect <1|2>`（子时流派）。支持公历 1600-2200 年；完整四柱盘的起运时刻会换算回出生地时区，起运与流年岁数统一按出生地公历年计虚岁；未知时辰三柱盘不伪造时柱或精确起运日期。

### v1.16.0 口径与输入契约说明

历史版本：[v1.16.0](https://github.com/HeiGeAi/HeiGe-SuanMing/releases/tag/v1.16.0)（2026-09-06）。奇门引擎同步更新为 `v1.2.1`。

- 八字 `v1.5.0`：跨国际日期变更线的等价经度不再产生虚假整日真太阳时偏移；合婚乙方可独立声明经度、时区并省略未知时辰。JSON 的 `partner_chart` 保存乙方完整排盘，`partner_input` 保存输入口径；原有 `partner_pillars`、`partner_calendar` 等摘要字段继续保留，读取完整双盘时不必另算乙方。
- 梅花 `v1.2.0`：农历小月、不存在的闰月及换算后年份越界会返回明确中文错误；`--lunar` 与 `--zi-sect` 只允许和 `--time` 同用。
- 六爻 `v1.2.0`：新增 `--zi-sect 1|2`，默认 2 保持旧结果，并在 `日月.子时流派` 记录有效口径。
- 紫微 `v1.3.0`：默认 `fix_leap=true`，按实际农历日判断闰月十六日起改用下一月安宫；默认 `year_divide=normal` 按春节换排盘采用年，可选 `exact` 按 `lunar_python` 的立春交接时刻切换。原始输入与两项口径写入 `input`，实际农历年保留在 `lunar.年干支`，排盘采用年与安宫月写入 `calculation`。这两个边界规则不声称与 iztro 2.5.8 的所有行为完全一致。

### v1.15.0 结构化输出迁移说明

本版修正了两个旧字段的不准确语义，依赖 JSON 的调用方需要按下列规则读取：

- 紫微 `v1.2.0`：「禄存」不再误入 `十二宫.*.六煞`；请读取宫级 `禄存` 布尔值或顶层 `禄存`。`六煞` 现只包含擎羊、陀罗、地空、地劫、火星、铃星。
- 奇门 `v1.2.0`：顶层 `伏吟` 与 `反吟` 现表示星或门任一成立；需区分时请读取 `星伏吟`、`星反吟`、`门伏吟`、`门反吟` 四个明确字段。

---

## 多 Agent 支持 Works with any agent

技能核心是一层方法论、六个计算引擎脚本和知识底座，**不绑定任何特定 Agent**。接入时保留完整仓库，包括 `SKILL.md`、`scripts/`、`references/`、依赖清单与许可证；示例、资源和测试也随包保留，便于核对视觉交付和版本。只粘贴提示词或只复制一个脚本，不等于安装了完整技能。

先按[快速开始](#快速开始-quick-start)安装一次完整仓库和 `.venv`，不同 Agent 可以读取同一个已安装目录，无需重复安装或启动多个 Agent 协作。这里的「多 Agent 支持」指宿主兼容，不是运行时必须委派多个模型。

把以下指引中的路径换成实际安装位置，再接进 Agent 规则文件或直接作为本次任务发给它：

```text
读取已安装目录中的 SKILL.md，先按用户目标选择八字、紫微、梅花、六爻、奇门或手机号八星。
脚本使用该目录 .venv 的 Python 执行，路径以本机为准；排盘不靠模型手推。
必要信息集中补齐，先给简短结论，再展开依据与局限。
命理核心任务默认完成相应 HTML 命书，用户明确只要文字时除外；不自动展开全部延伸功能。
```

规则文件位置因 Agent 而异：

<details>
<summary><b>Codex（OpenAI）</b></summary>

写进项目根目录的 `AGENTS.md`，或全局 `~/.codex/AGENTS.md`。Codex 启动时自动加载，之后直接说"排个八字"即可。
</details>

<details>
<summary><b>Cursor</b></summary>

在 `.cursor/rules/` 下新建一条规则文件（`.mdc`），或写进项目根目录的 `.cursorrules`。
</details>

<details>
<summary><b>Cline</b></summary>

写进工作区根目录的 `.clinerules`（单文件或同名文件夹均可）。
</details>

<details>
<summary><b>Windsurf</b></summary>

写进 `.windsurf/rules/` 下的规则文件，或旧版 `.windsurfrules`。
</details>

<details>
<summary><b>Continue</b></summary>

把克隆目录加入上下文，并在 `config` 的 `rules` 里补一条上面的指引。
</details>

<details>
<summary><b>GitHub Copilot</b></summary>

写进 `.github/copilot-instructions.md`，对整个仓库生效。
</details>

<details>
<summary><b>通用方式（任意 Agent）</b></summary>

不依赖规则文件也行：直接对 Agent 说"读取 HeiGe-SuanMing/SKILL.md 并严格按它执行，排盘调用 scripts/paipan.py、起卦调用 scripts/meihua.py、装卦调用 scripts/liuyao.py、安星调用 scripts/ziwei.py、排局调用 scripts/qimen.py、手机号结构调用 scripts/phone_energy.py"，它就能照着跑。六个计算引擎脚本本身也能脱离对话单独运行（见上方[快速开始](#快速开始-quick-start)）。
</details>

### 为什么推荐 Claude Code + Claude Opus 4.8

仓库保留 Claude Code + Claude Opus 4.8 作为作者的使用推荐，不将它视为唯一运行条件或跨模型评测结论。选择其他宿主时，重点确认它能读完整技能目录、调用指定 Python，并把脚本结果与解释依据对应起来。模型负责解释，不能用模型名称代替输入校验与结果验收。

---

## 项目结构 Architecture

```
HeiGe-SuanMing/
├── SKILL.md                      # 主提示词：十二步方法论与输出结构（你的 Agent 读这个）
├── scripts/
│   ├── paipan.py                 # 八字精确排盘引擎（基于 lunar_python）
│   ├── meihua.py                 # 梅花易数起卦引擎（先天八卦数+互变+体用）
│   ├── liuyao.py                 # 六爻装卦引擎（纳甲+八宫世应+六亲+六神）
│   ├── ziwei.py                  # 紫微斗数安星引擎（十二宫+五行局+双星系+四化）
│   ├── qimen.py                  # 奇门遁甲排局引擎（时家转盘·拆补法定局+星门神）
│   └── phone_energy.py           # 手机号八星结构引擎（相邻数字对+0/5 修饰）
├── references/                   # 命理知识底座，推演时按需调用
│   ├── 00_gainian_suoyin.md      # 命理概念 → 篇目检索索引（先看这里再按需深读）
│   ├── 01_paipan_jichu.md
│   ├── 02_wangshuai_yongshen.md  # 含取用神四派仲裁决策树
│   ├── 03_tiaohou_qiongtong.md
│   ├── 04_shishen_xiangyi.md
│   ├── 05_geju.md
│   ├── 06_shensha.md
│   ├── 07_keshihua_baoshu.md     # 可视化命书：一页 HTML 报告产出规范
│   ├── 08_gufu_duanyu.md         # 古籍赋文经验断语：渊海 / 三命 / 神峰赋诀精选
│   ├── 09_shenfeng_tongkao.md    # 神峰通考：病药说、动静说、盖头截脚、十干体象
│   ├── 10_mingli_yueyan.md       # 命理约言：理性派论法与祛魅清单
│   ├── 11_sanming_tonghui.md     # 三命通会：旺衰五态、十二宫、十神、格局神煞纲目
│   ├── 12_dianji_yuanliu.md      # 典籍源流与调用路径导航地图
│   ├── 13_ditian_sui.md          # 滴天髓：衰旺真机、中和、体用精神、寒暖燥湿
│   ├── 14_ziping_zhenquan.md     # 子平真诠：月令顺逆、相神、成败救应、格局高低
│   ├── 15_yangsheng_tiaoyang.md  # 五行养生调养：用神喜忌落到作息饮食情志运动
│   ├── 16_secai_fushi.md         # 色彩服饰调候：用神色落到衣着首饰随身环境
│   ├── 17_hehun.md               # 正派合婚双盘合参：用神互补+日柱年支合冲，不打分
│   ├── 18_meihua_yishu.md        # 梅花易数占卜引擎：起卦+体用+互变，占一时一事
│   ├── 19_liuyao.md              # 六爻纳甲占卜引擎：装卦+用神+旺衰生克应期
│   ├── 20_ziwei.md               # 紫微斗数安星引擎：十二宫+双星系+四化+命主飞化，命理批一生
│   ├── 21_qimen.md               # 奇门遁甲排局篇：拆补置闰定局+布盘+值符值使
│   ├── 22_qimen_duanju.md        # 奇门遁甲断局篇：用神+克应81表+格局+应期十三法
│   ├── 24_phone_energy.md        # 手机号八星输入契约、规则 profile 与隐私边界
│   ├── phone_energy_rules_v1.json # 八星映射与 0/5 修饰规则
│   └── phone_energy_readings_v1.json # 八星白话解读、生活场景与七天行动文案
├── cases/                        # 完整推演范例，照着学怎么把方法落到真盘
│   ├── 01_shenqiang_caiguan.md   # 身强用财官
│   ├── 02_shenruo_yinbi.md       # 身弱用印比
│   ├── 03_tiaohou.md             # 调候为急
│   └── 04_conge.md               # 专旺候选与常格复核
├── tests/
│   ├── test_paipan.py            # 八字排盘回归测试（古法定式为基准）
│   ├── test_meihua.py            # 梅花起卦回归测试（观梅占黄金例）
│   ├── test_liuyao.py            # 六爻装卦回归测试（京房纳甲定式）
│   ├── test_ziwei.py             # 紫微安星回归测试（含 iztro 2.5.8 固定锚点）
│   ├── test_qimen.py             # 奇门排局回归测试（固定逐宫期望与置闰电池）
│   ├── test_phone_energy.py      # 手机号八星回归测试（数字对、修饰、脱敏、CLI 与白话 HTML 报告）
│   └── test_release_contract.py  # 最低依赖、版本、文档与打印契约
├── examples/
│   └── 示例-八字命书.html         # 可视化命书样例（虚拟生辰，脱敏教学向）
├── assets/
│   ├── cover.png                 # README 题图
│   ├── visual-hero.jpg           # 可视化命书 · 卷首命格诗
│   └── visual-sig.jpg            # 可视化命书 · 签名时刻
├── requirements.txt
├── LICENSE
└── README.md
```

## 系统要求 Requirements

- 任意"能读文件 + 跑 Python"的 AI Agent（推荐 Claude Code + Claude Opus 4.8）
- Python 3.7 to 3.13
- `lunar_python == 1.4.8`，固定排盘底座，升级前须跑完整回归

---

## English

**HeiGe-SuanMing** is a Bazi (Four Pillars of Destiny) engine that runs inside any AI agent able to read local files and run Python (Claude Code + Claude Opus 4.8 recommended). It splits fortune-telling into two layers so the whole thing stays reproducible and auditable. It also ships a second destiny-reading engine, **Zi Wei Dou Shu (Purple Star Astrology)**, plus three divination engines: **Meihua Yishu (Plum Blossom I-Ching)**, **Liu Yao (Najia hexagram casting)**, and **Qi Men Dun Jia (hour-based rotating-plate chart casting)**. Fixed Zi Wei and Qi Men cases are covered by repository tests; external oracle snapshots for the historical Qi Men comparisons have not yet been archived.

**Layer 1 — the chart is computed, never hand-derived.** `scripts/paipan.py` uses `lunar_python` for precise stem-branch calculation, automatically handling the three things people get wrong most often: setting the year pillar by **Lichun** (start of spring, not lunar new year), the month pillar by **solar terms** (not the lunar month), and optional **true solar time** correction when longitude and time zone are explicit. On top of that it computes hidden stems, ten gods, nayin, the twelve life stages, void branches, branch interactions (combinations / clashes / punishments), weighted five-element strength, symbolic stars, and the luck/annual pillars.

**Layer 2 — the reading follows a fixed methodology, every claim cites its basis.** `SKILL.md` enforces a strict order: strength → useful god → structure → luck cycles → ten-gods/relatives → dimensional readings → guidance plus personalized health-cultivation and color/attire advice (lifestyle, diet, rest, and what to wear, tuned to the useful god, not folk "supplement what's missing"). Each statement notes its reasoning chain, no single-signal verdicts, full reasoning shown.

**Grounded in the classics, checked by tests.** The `references/` knowledge base anchors methods back to canonical texts, including Yuanhai Ziping, Ditian Sui, Qiongtong Baojian, Ziping Zhenquan, and Sanming Tonghui. `cases/` ships four fully worked, desensitized readings. The suite contains 434 checks: Bazi 158, Meihua 49, Liu Yao 43, Zi Wei Dou Shu 72, Qi Men Dun Jia 75, Phone energy 23, documented examples 8, and release contracts 6. They cover calendar and solar-term boundaries, unknown-hour output, leap months, midnight conventions, the international date line, partner time zones, fixed iztro anchors, two palace-by-palace Qi Men charts, a 35-case leap-adjustment battery, and phone-energy pair, privacy, short-number, reading-library, unclassified fallback, ordering, and HTML report boundaries. These tests establish repository behavior for fixed cases; they do not prove every year, school, or external oracle.

**A one-page visual report, delivered by default.** Once the requested reading is done, the agent renders it into a single elegant HTML scroll and opens it for you (just say so if you only want the text version): chart, five-element bars, luck timeline, dimensional readings, personalized health-cultivation and color/attire advice, and a full-screen close-up of the chart's pivotal element. The text stays verbatim-identical to the reading, and fonts fall back gracefully so nothing breaks offline. See the [live preview](https://raw.githack.com/HeiGeAi/HeiGe-SuanMing/main/examples/%E7%A4%BA%E4%BE%8B-%E5%85%AB%E5%AD%97%E5%91%BD%E4%B9%A6.html), built from a fictional birth date. (GitHub serves `.html` as source, so use this link rather than opening the file directly.)

**Runs anywhere, tuned for Claude Code.** The core is `SKILL.md` (methodology), six scripts (`scripts/paipan.py`, `scripts/meihua.py`, `scripts/liuyao.py`, `scripts/ziwei.py`, `scripts/qimen.py`, and `scripts/phone_energy.py`), plus `references/` (knowledge base). Outputs are deterministic when all effective inputs are explicit; for example, pass `--years` because the Bazi default window intentionally starts from the current Ganzhi year. Any agent that reads local files and runs Python can drive it (Codex, Cursor, Cline, Windsurf, Continue, Copilot, and so on): clone the repo, install deps, and point the agent's rules file at `SKILL.md`. Claude Code + Claude Opus 4.8 remains the author's recommendation, not a cross-model benchmark result or a runtime requirement. Install the complete repository in a virtual environment, then use the interpreter from that environment. Start with the requested goal, collect missing inputs together, and present a short answer before the supporting evidence; optional extensions are not run automatically.

Claude Code setup:

```bash
git clone https://github.com/HeiGeAi/HeiGe-SuanMing.git ~/.claude/skills/bazi-mingli
cd ~/.claude/skills/bazi-mingli
python3 -m venv .venv
./.venv/bin/python -m pip install -r requirements.txt
```

Then type `/bazi-mingli` in Claude Code and give it a birth date, time, and gender. For other agents, see the [多 Agent 支持](#多-agent-支持-works-with-any-agent) section above.

---

## 免责声明 Disclaimer

本项目是对**中国传统命理学（四柱八字）的数字化整理与研究工具**，定位为传统文化学习与自我认知的参考，供研究、学习、自省之用。

- 命理推演是基于经典模型的**倾向性、概率性分析**，不构成对任何人命运、健康、婚姻、财富的预言或保证。
- 本工具**不宣扬封建迷信**，不承诺改运、消灾、转运，不提供任何形式的趋吉避凶"法术"。
- 所有结论仅供参考。涉及健康、婚姻、投资、职业等真实人生决策，请以现实情况为准，结合专业意见理性判断。
- 请勿将本工具用于任何违法用途，或借命理之名行欺诈、敛财、制造焦虑之实。

This project is a research and study tool for traditional Chinese metaphysics (Bazi). Its readings are probabilistic, model-based tendencies, not predictions or guarantees. It does not promise to change fate or ward off misfortune. For real-life decisions, rely on reality and professional advice.

---

## 致谢 | Credits

排盘精度由 [lunar_python](https://github.com/6tail/lunar-python) 提供支撑。

## 许可证 | License

PolyForm Noncommercial 1.0.0 © 2026 [HeiGeAi (Blake Xu)](https://github.com/HeiGeAi)

本项目源码公开，但采用 **PolyForm Noncommercial License 1.0.0**，属于**源码可用的非商业许可**，不是 OSI 定义的开源许可证。要点：

1. **非商业使用免费**：个人研究、学习、自用、兴趣项目，随便用、随便改、随便分享
2. **必须保留署名**：二开、Fork、再分发都要保留版权与来源声明，别去掉署名冒充原创
3. **禁止任何商业用途**：不得用于盈利产品、付费服务、商业化分发，或任何带商业目的的场景；**未经授权的商业化即视为违反本协议**
4. **商用须先授权**：想商用？先开 Issue 或私信作者单独谈授权，谈拢了再用

完整法律条款见 [`LICENSE`](./LICENSE)。源码可读，理性看命。

**English:** This project is source-available under **PolyForm Noncommercial 1.0.0** — free for any noncommercial use (study, research, personal projects), with attribution required. **Any commercial use requires a separate license from the author** (open an Issue or reach out). Unauthorized commercial use violates the license.

## 更多源码公开工具

本项目属于问问黑哥的源码公开工具库。全部项目的清单、用途和协议，见 [heigeai.com/opensource](https://www.heigeai.com/opensource/)。
