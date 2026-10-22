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
- 词语表全部 220 个词，放在对应单元的 `textbook_words`。第 3、7、8、12、14、19、22、23、26、27 课在词语表里没有条目，这是对照课本后的结果，没有用教辅补词。
- 识字表、写字表的单字记在课文的 `recognize`、`write_chars`，语文园地的字记在单元的 `garden_recognize`、`garden_write`。识字表里的蓝色多音字另记在 `recognize_review`，不计入 250 个生字。这些单字先作数据，供以后的写生字题使用，当前不出题。
- 各单元语文园地的日积月累记在 `accumulation`。第 5 单元目录和正文都没有语文园地。
- 《暮江吟》《题西林壁》《雪梅》《凉州词》《出塞》《夏日绝句》全文。其中《出塞》课本作“但使龙城飞将在”。
- 课文脚注里的署名。没有人名的课，记的是脚注里的出处，例如《王戎不取道旁李》选自《世说新语·雅量》，课文没有署刘义庆。

还没有写进卷面的内容：

- 习作页上的作前指导没有逐字抄入。卷面习作仍是自编题干，只用已经核对的习作题目。
- 例文《我家的杏熟了》《小木船》只记下脚注，正文未收录。
- 仍受著作权保护的现代课文原文。阅读短文和选词填空是自编练习。

八个单元都有词语表里的词，看拼音从这些词里抽，并避开已经印在卷面上的词。

## 增加一个版本的数据

1. 复制 `data/_template.yaml`。
2. 保存为 `data/<版本编号>/grade<年级>_term<学期>.yaml`。目录名必须等于文件里的 `edition.id`。JSON 也可以，文件名相同、后缀为 `.json`。
3. 只填写核对过的课文标题、作者、古诗、词语和单字。现代课文原文不要粘贴进仓库。
4. `textbook_words` 收词语表里的词，`source` 使用 `textbook`。有这些词时，看拼音只从这里抽，不再用课文标题凑词语。写字表的单字放在 `write_chars`，不要写进 `textbook_words`。
5. 运行 `cn-exam --list`，再按上面的命令出一份卷，并用 `pytest` 确认学生卷不含 `答案：`。

字段说明、来源标记和不要编造写字表的规则见 [CONTRIBUTING.md](CONTRIBUTING.md)。

找题库的顺序：`--data-dir`、环境变量 `CN_EXAM_DATA_DIR`、安装包内的 `cn_exam/data`、仓库根目录的 `data/`、当前目录的 `data/`。

## 测试

```bash
pytest
```

测试覆盖组卷、满分 100、古诗原文，以及学生卷不出现答案字段、未默写诗句和答案卷专有说明。

## 路线图

- 用识字表、写字表的单字增加写生字题，用日积月累增加积累题。
- 增加其他年级，以及其他版本（例如苏教版、北师大版）。
- 增加改病句等题型。题干仍然来自数据文件，不在程序里编造课文。
- 出卷前的 HTML 预览。

## 许可

MIT License。版权所有：jasonsun080721-create。
