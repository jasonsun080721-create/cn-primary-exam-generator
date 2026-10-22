# 参与贡献

感谢你给题库或程序补内容。改动请保持可核对：课文标题、作者、古诗、写字表都要能指出依据。不能核对的内容写成 TODO，不要填成看似官方的词表。

## 环境

```bash
pip install -e ".[dev]"
pytest
cn-exam --edition rj2026 --grade 4 --term 1 --unit 1 --no-pdf
```

Python 3.10 及以上。提交前跑通 `pytest`。

## 新增一个教材版本

一条数据对应一个版本、一个年级、一个学期。路径：

```text
data/<edition-id>/grade<grade>_term<term>.yaml
```

`edition-id` 用小写字母、数字，例如 `rj2026`。目录名必须和文件中的 `edition.id` 相同。`.yml` 和 `.json` 同样可用。下划线开头的文件和目录不会被 `--list` 扫到，`data/_template.yaml` 是模板。

复制模板后至少修改：

- `edition.id`、`edition.name`、`edition.series_label`、年级、学期、`book_name`
- `units` 里的课文标题
- `exam_ranges.midterm` 和 `exam_ranges.final` 覆盖的单元号

然后：

```bash
cn-exam --list
cn-exam --edition <edition-id> --grade <年级> --term <1或2> --unit 1 --no-pdf
```

## 数据规则

1. 写字表、词语表只在对照过纸质课本或出版社目录后写入 `textbook_words`。`source` 填 `textbook`。空列表是合法的，表示还没核对。
2. 有 `textbook_words` 时，看拼音写词语只从这里抽词。没有时，才退回课文标题词和古诗中的词，并且会丢掉已经印在卷头或题干里的词，避免答案直接露在卷面上。
3. 古诗 `lines` 只保留汉字，五言或七言，不要标点。作者、朝代要和教材署名一致；有文献分歧时写在 `teacher_note`，这段话只出现在答案卷。
4. 不要把仍受著作权保护的现代课文、译文粘贴进仓库。阅读短文使用 `origin: original_practice`，并在 `credit` 里写明“自编阅读材料”。公有领域原文使用 `origin: public_domain`。
5. 作者不确定就设 `author_status: todo`，不要猜署名。已核对才用 `verified`，并且 `author` 不能为空。
6. 选词填空的句子里用 `____` 表示空，`answer` 必须是 `bank` 中的一项。
7. 判断题 `kind` 为 `judge`，`answer` 只能是 `对` 或 `错`，不要写 `options`。选择题 `kind` 为 `single`，`answer` 是 `A`、`B`、`C`……
8. 每个 `id` 在同一单元内唯一。
9. 官方习作题目未核实时，习作用 `origin: original_practice`，不要把旧版习作题目写成 2026 秋新版的官方题目。

`schema_version` 目前是 `1`。加载器拒绝未定义字段，拼错的键会直接报错。

## 词语的 source

| source | 含义 |
| --- | --- |
| `textbook` | 已核对的写字表或词语表 |
| `lesson_title` | 来自课文标题，不是写字表 |
| `poem` | 来自古诗原文 |
| `content_fact` | 已核对的文学常识用词，不是写字表 |
| `original_practice` | 自编练习词。卷面说明里会注明不是教材写字表 |

多音字填写 `pinyin`，例如诗中“阁笔”可写 `gē bǐ`。留空则用 pypinyin 的带声调拼音。

## 学生卷不能泄题

生成器把题目拆成两份：

- `SafeQuestion` 只有题干、选项、空格数量。学生卷渲染函数只接收它。
- 答案、解析、需要默写的诗句留在内部对象里，只写进答案卷。答案行以 `答案：` 开头。

新增题型时保持这个拆分。测试在 `tests/test_no_answers.py`：哨兵词语、整句诗和答案卷专有说明不得出现在学生卷的 `word/document.xml`、页眉和页脚里。

## 代码风格

- 缩进 4 个空格。
- 函数和变量用 `snake_case`，类用 `PascalCase`。
- 关键分支用中文注释说明为什么这样做。
- 单行不超过 120 个字符。
- 提交说明使用 Conventional Commits，例如 `feat: 录入某版写字表`、`fix: 古诗补写不再印出后半首`。

## 题型权重

默认权重：看拼音 16、古诗 18、选词填空 12、判断与选择 12、阅读 24、习作 18，合计 100。单题还有上限，例如看拼音每词最多 2 分，避免两个标题词占掉二十分。上限仍不够凑满满分时，剩余分数进入习作。
