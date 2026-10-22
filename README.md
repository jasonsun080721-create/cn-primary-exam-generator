# cn-primary-exam-generator

English summary: a Python package and `cn-exam` CLI that builds printable Chinese primary-school language exams. Give it an edition, grade, term, and unit (or a midterm/final range). It writes an A4 student `.docx` and a separate answer key. PDF export runs when LibreOffice is installed. Question banks live in YAML or JSON under `data/`. The starter set is 人教版（统编版）2026秋新版四年级上册, units 1–8. Vocabulary is entered only after it is read from the textbook pages; unfinished lessons stay as TODOs.

小学语文试卷生成器。指定教材版本、年级、学期和单元（或期中、期末范围），生成 A4 学生卷和单独的答案卷。学生卷不写答案。

## 能做什么

- 题型：看拼音写词语、古诗默写或补写、选词填空、判断与选择、阅读理解、习作。
- 拼音用 [pypinyin](https://pypi.org/project/pypinyin/) 标注；多音字、通假字可在数据里手写覆盖。
- 默认满分 100。没有题目的题型不占分，分数按权重重新分到其余题型，结果是整数。
- 同一条命令默认使用固定种子，重复运行得到同一份试卷。`--seed` 可以换一套题。
- 本机有 `soffice` 或 `libreoffice` 时，同时导出 PDF。

## 安装

需要 Python 3.10 或更高版本。

```bash
pip install -e ".[dev]"
```

## 使用

```bash
cn-exam --edition rj2026 --grade 4 --term 1 --unit 1
cn-exam --edition rj2026 --grade 4 --term 1 --unit 3
cn-exam --edition rj2026 --grade 4 --term 1 --exam midterm
cn-exam --edition rj2026 --grade 4 --term 1 --exam final
cn-exam --edition rj2026 --grade 4 --term 1 --units 1-2
cn-exam --list
```

第 1 单元默认写到当前目录的 `out/`：

- `rj2026_4年级上册_第1单元练习卷_学生卷.docx`
- `rj2026_4年级上册_第1单元练习卷_答案.docx`

也可以 `python -m cn_exam`，参数相同。

在代码里调用：

```python
from cn_exam import generate_exam

result = generate_exam(edition="rj2026", grade=4, term=1, unit=1, output_dir="out")
print(result.student_docx)
print(result.answer_docx)
```

调整题型权重和满分：

```bash
cn-exam --edition rj2026 --grade 4 --term 1 --unit 3 \
  --points pinyin=16,classical=18,cloze=12,choice=12,reading=24,writing=18 \
  --total 100
```

权重只对实际有题的题型生效，并重新分配到 `--total`。

## 起步数据里有什么

版本编号 `rj2026`，四年级上册，单元 1–8。期中按第 1–4 单元，期末按第 1–8 单元。这是本仓库的出卷范围，课本目录本身不写期中、期末。

目录来源：电子课本网 [四年级上册（2026秋版）](http://www.dzkbw.com/books/rjb/yuwen/xs4s_2026/) 的目录页，并与国家中小学智慧教育平台上《（根据2022年版课程标准修订）义务教育教科书·语文四年级上册》（内容编号 `5cd7e623-5c38-4602-871a-3fba8a551db2`）的页面核对。词语表只收录从该平台词语表页读清的词。

| 单元 | 课文 | 习作题目 |
| --- | --- | --- |
| 1 | 观潮、繁星、现代诗二首（秋晚的江上、花牛歌） | 推荐一个好地方 |
| 2 | 一个豆荚里的五粒豆、夜间飞行的秘密、方帽子店、田忌赛马 | 我的家人 |
| 3 | 古诗三首（暮江吟、题西林壁、雪梅）、爬山虎的脚、蟋蟀的住宅 | 写观察日记 |
| 4 | 盘古开天地、精卫填海、普罗米修斯、女娲补天 | 我和____过一天 |
| 5 | 麻雀、爬天都峰；例文《我家的杏熟了》《小木船》 | 生活万花筒 |
| 6 | 长城、颐和园、秦兵马俑 | 中国的世界文化遗产 |
| 7 | 牛和鹅、一只窝囊的大老虎、陀螺、王戎不取道旁李 | 我的心儿怦怦跳 |
| 8 | 我将无我，不负人民、为中华之崛起而读书、延安，我把你追寻、古诗三首（凉州词、出塞、夏日绝句） | 写信 |

已写入题库的内容：

- 上表的课文标题、篇目和习作题目。口语交际题目记在各单元说明和判断题里：我们与环境，爱护眼睛、保护视力，我是小小讲解员，安慰。
- 词语表第 1、2、4、5、6 课中已读清的词，放在对应单元的 `textbook_words`。第 1、2 单元因此会出“看拼音，写词语”。
- 《暮江吟》《题西林壁》《雪梅》全文。《凉州词》《出塞》《夏日绝句》按统编通行文本录入。《夏日绝句》的作者李清照和末两句已在课本页上看到。《出塞》用“龙城”，这一字本次页图没有逐字复核。
- 能核对的文学常识：巴金、安徒生、叶圣陶、法布尔，田忌赛马中孙膑的安排，以及盘古、精卫、普罗米修斯、女娲故事里稳定的情节。

还没有写完、文件里仍标着 TODO 的内容：

- 词语表第 7 课和第 8–27 课。第 3 课《现代诗二首》在词语表第 1 页上没有单独条目。
- 识字表、写字表。页面能打开，字太小，除第 1 课外没有逐字确认，所以没有录入。
- 各单元“日积月累”。有一页印着〔唐〕高适《别董大》，末句是“天下谁人不识君”，同一页没有看清单元号。
- 课文署名和任何仍受著作权保护的课文原文。阅读短文、选词填空和习作题干是自编练习，只借用已经核对的习作题目。

第 3、4 单元还没有词语表，看拼音会退回古诗或标题里没有印在卷头的词。第 5–7 单元在词语表补上之前，标题已印在卷头，通常不出看拼音。

## 增加一个版本的数据

1. 复制 `data/_template.yaml`。
2. 保存为 `data/<版本编号>/grade<年级>_term<学期>.yaml`。目录名必须等于文件里的 `edition.id`。JSON 也可以，文件名相同、后缀为 `.json`。
3. 只填写核对过的课文标题、作者、古诗和写字表。现代课文原文不要粘贴进仓库。
4. `textbook_words` 的 `source` 使用 `textbook`。有写字表时，生成器只用写字表，不再用课文标题凑词语。
5. 运行 `cn-exam --list`，再按上面的命令出一份卷，并用 `pytest` 确认学生卷不含 `答案：`。

字段说明、来源标记和不要编造写字表的规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。

找题库的顺序：`--data-dir`、环境变量 `CN_EXAM_DATA_DIR`、安装包内的 `cn_exam/data`、仓库根目录的 `data/`、当前目录的 `data/`。

## 测试

```bash
pytest
```

测试覆盖组卷、满分 100、古诗原文，以及学生卷不出现答案字段、未默写诗句和答案卷专有说明。

## 路线图

- 把词语表第 7–27 课和识字表、写字表、日积月累按课本页补全。
- 增加其他年级，以及其他版本（例如苏教版、北师大版）。
- 增加改病句等题型。题干仍然来自数据文件，不在程序里编造课文。
- 出卷前的 HTML 预览。

## 许可

MIT License。版权所有：jasonsun080721-create。
