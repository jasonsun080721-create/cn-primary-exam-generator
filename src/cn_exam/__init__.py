"""小学语文试卷生成器。"""

from importlib.metadata import PackageNotFoundError, version

from cn_exam.errors import DataError, ExamError
from cn_exam.generate import generate_exam
from cn_exam.models import GenerateResult

try:
    __version__ = version("cn-primary-exam-generator")
except PackageNotFoundError:
    __version__ = "0.1.0"

__all__ = [
    "DataError",
    "ExamError",
    "GenerateResult",
    "generate_exam",
    "__version__",
]
