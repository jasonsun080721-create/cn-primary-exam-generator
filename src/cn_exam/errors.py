"""组卷过程中可预期的错误。"""


class DataError(Exception):
    """题库文件缺失或不符合约定。"""


class ExamError(Exception):
    """参数、组卷或导出失败。"""
