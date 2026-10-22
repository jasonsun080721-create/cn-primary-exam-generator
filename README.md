# cn-primary-exam-generator

English summary: a Python package and `cn-exam` CLI that builds printable Chinese primary-school language exams. Give it an edition, grade, term, and unit (or a midterm/final range). It writes an A4 student `.docx` and a separate answer key. PDF export runs when LibreOffice is installed. Question banks live in YAML or JSON under `data/`. The starter set is 人教版（统编版）2026秋新版四年级上册, units 1–4. Official character lists are left as TODOs instead of being invented.

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

版本编号 `rj2026`，四年级上册，单元 1–4：

| 单元 | 课文 |
| --- | --- |
| 1 | 观潮、繁星、现代诗二首 |
| 2 | 一个豆荚里的五粒豆、夜间飞行的秘密、方帽子店、田忌赛马 |
| 3 | 古诗三首（暮江吟、题西林壁、雪梅）、爬山虎的脚、蟋蟀的住宅 |
| 4 | 盘古开天地、精卫填海、普罗米修斯、女娲补天 |

已核对并写入题库的内容：

- 上表中的课文标题。
- 《暮江吟》《题西林壁》《雪梅》全文。诗句按统编教材通行文本，不带标点；《雪梅》署名为宋·卢钺。
- 能核对的作者和故事要点：巴金、安徒生、叶圣陶、法布尔《昆虫记》、田忌赛马里孙膑的安排、三首诗的作者，以及盘古、精卫、普罗米修斯、女娲故事里稳定的情节。

没有写入的内容：

- 写字表、词语表。`textbook_words` 是空列表，文件里有 TODO。
- 《现代诗二首》的具体篇目。旧版篇目未拿来冒充 2026 秋新版。
- 《观潮》《夜间飞行的秘密》《方帽子店》和神话课文的教材署名，以及任何仍受著作权保护的课文原文。
- 官方口语交际、习作题目。卷中的阅读短文和习作是自编练习，试卷页脚写明了这一点。

因此第 1、2、4 单元目前不出“看拼音，写词语”：标题已经印在卷头，不能再当作默写答案。第 3 单元用古诗里未印在卷面上的词语出这一题。补上写字表后，该题会自动出现。期中范围在数据里暂定为第 1–2 单元，期末暂定为已收录的第 1–4 单元，学校进度不同就改 `exam_ranges`。

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

- 补齐四年级上册第 5–8 单元，并录入核对后的写字表、词语表、官方习作。
- 增加其他年级，以及其他版本（例如苏教版、北师大版）。
- 增加改病句等题型。题干仍然来自数据文件，不在程序里编造课文。
- 出卷前的 HTML 预览。

## 许可

MIT License。版权所有：jasonsun080721-create。
