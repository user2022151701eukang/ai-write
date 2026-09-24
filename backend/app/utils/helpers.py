"""通用工具函数"""

import json
import re
from typing import Any, Dict, Optional

# 中文字符范围
_CJK_PATTERN = re.compile(r"[\u4e00-\u9fff]")
_WORD_PATTERN = re.compile(r"[A-Za-z0-9]+")


def strip_code_fence(text: str) -> str:
    """去除 LLM 输出中的 ```json ... ``` 代码块包裹"""
    if not text:
        return ""

    cleaned = text.strip()
    if cleaned.startswith("```"):
        lines = cleaned.split("\n")
        # 去掉首行 ```json 与末行 ```
        if lines[-1].strip().startswith("```"):
            lines = lines[1:-1]
        else:
            lines = lines[1:]
        cleaned = "\n".join(lines)
    return cleaned.strip()


def extract_json(text: str) -> Optional[Dict[str, Any]]:
    """从 LLM 输出中提取 JSON 对象，失败返回 None"""
    if not text:
        return None

    cleaned = strip_code_fence(text)

    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        pass

    # 退化为截取第一个 { 到最后一个 } 之间的内容
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(cleaned[start:end + 1])
        except json.JSONDecodeError:
            return None

    return None


def count_words(text: str) -> int:
    """统计字数（中文按字计数，英文按单词计数）"""
    if not text:
        return 0
    cjk_count = len(_CJK_PATTERN.findall(text))
    word_count = len(_WORD_PATTERN.findall(_CJK_PATTERN.sub(" ", text)))
    return cjk_count + word_count


def truncate(text: str, limit: int = 4000) -> str:
    """按字符数截断文本"""
    if not text:
        return ""
    if len(text) <= limit:
        return text
    return text[:limit] + "..."


# ----------------------------------------------------------------------
# AI 附加内容清理（模型常常在正文后追加「说明」「如需扩展…」等非论文内容）
# ----------------------------------------------------------------------
# 命中即从该行开始截断（这些句子只会出现在正文之外）
_META_LINE_PATTERNS = [
    re.compile(r"^如需.{0,60}(扩展|调整|补充|定制|生成|输出|修改|深化|精简|转换)"),
    re.compile(r"^若(您|你)?需要.{0,60}(扩展|调整|补充|定制|生成|输出|修改)"),
    re.compile(r"^(我|我们|本人)?(也)?(可以|可|随时|能够)(为)?(您|你)?(随时)?(定制|提供|生成|输出|调整|扩展|润色|改写|补充)"),
    re.compile(r"^希望(以上|这份|本文|这些).{0,40}"),
    re.compile(r"^(以上|上述)(内容|就是|为).{0,40}(扩展|调整|定制|参考|建议)?"),
    re.compile(r"^(全文|本文)?(已)?(采用|按照).{0,30}(格式|规范|要求).{0,10}(输出|生成|撰写)"),
]
# 引用块（>）中包含这些关键词时，视为 AI 附加说明
_META_QUOTE_KEYWORDS = ("说明", "注：", "注意：", "提示", "备注")
# 正文开头的客套/引导语（必须整行以冒号结尾，避免误删正文首句）
_PREAMBLE_PATTERN = re.compile(
    r"^(好的|当然|以下是|下面是|这是|我将为|接下来我)[^。！？；]{0,40}[:：]$"
)


def strip_ai_meta(text: str) -> str:
    """去除模型附加的非正文内容

    处理三类常见情况：
    1. 正文之后追加的「说明 / 注 / 提示」引用块；
    2. 正文之后追加的「如需扩展为…」「我可以为您…」等后续服务建议（从该行起截断）；
    3. Markdown 代码块围栏与开头的客套引导语。
    """
    if not text:
        return ""

    lines = text.replace("\r\n", "\n").split("\n")
    kept: list[str] = []

    for line in lines:
        stripped = line.strip()

        # 代码块围栏
        if stripped.startswith("```"):
            continue
        # 引用块形式的附加说明
        if stripped.startswith(">") and any(k in stripped for k in _META_QUOTE_KEYWORDS):
            continue
        # 后续服务建议 / 自述格式说明：从这里开始整段截断
        if stripped and any(pattern.match(stripped) for pattern in _META_LINE_PATTERNS):
            break
        kept.append(line)

    kept = _trim_trailing_quote_block(kept)

    # 去掉开头的客套引导语
    while kept:
        first = kept[0].strip()
        if not first:
            kept.pop(0)
            continue
        if _PREAMBLE_PATTERN.match(first) or (
            len(first) <= 40 and ("以下" in first or "下面" in first) and first.endswith(("：", ":"))
        ):
            kept.pop(0)
            continue
        break

    cleaned = "\n".join(kept).strip()
    # 合并过多空行
    cleaned = re.sub(r"\n{3,}", "\n\n", cleaned)
    return cleaned


def _trim_trailing_quote_block(lines: list) -> list:
    """去掉正文末尾的引用块（常见于模型的「说明」段落）"""
    result = list(lines)
    while result:
        last = result[-1].strip()
        if not last:
            result.pop()
            continue
        if last.startswith(">"):
            result.pop()
            continue
        break
    return result


def build_reference_text(reference: Dict[str, Any]) -> str:
    """拼接用于向量化的文献文本"""
    parts = [
        reference.get("title") or "",
        reference.get("authors") or "",
        reference.get("journal") or "",
        str(reference.get("year") or ""),
        reference.get("abstract") or "",
    ]
    return " ".join([p for p in parts if p]).strip()


def format_reference(reference: Dict[str, Any], style: str = "gbt") -> str:
    """
    将文献格式化为标准引用文本

    支持格式：
    - gbt: GB/T 7714  [序号] 作者. 题名[J]. 刊名, 年, 卷(期): 页码.
    - apa: 作者 (年). 题名. 刊名, 卷(期), 页码.
    - mla: 作者. "题名." 刊名, 年, 页码.
    """
    title = reference.get("title") or "N/A"
    authors = reference.get("authors") or "佚名"
    journal = reference.get("journal") or ""
    year = reference.get("year") or ""
    volume = reference.get("volume") or ""
    issue = reference.get("issue") or ""
    pages = reference.get("pages") or ""

    if style == "apa":
        volume_issue = f"{volume}({issue})" if volume else (f"({issue})" if issue else "")
        tail = ", ".join([p for p in [f"{journal}", volume_issue, pages] if p])
        return f"{authors} ({year}). {title}. {tail}."
    if style == "mla":
        return f'{authors}. "{title}." {journal}, {year}, {pages}.'

    # 默认 GB/T 7714
    volume_issue = f"{volume}({issue})" if volume else (f"({issue})" if issue else "")
    tail_parts = [p for p in [journal, volume_issue] if p]
    citation = f"{authors}. {title}[J]. {', '.join(tail_parts)}"
    if year:
        citation += f", {year}"
    if pages:
        citation += f": {pages}"
    return f"{citation}."


def chapter_to_markdown(title: str, content: str, level: int = 2) -> str:
    """将章节内容拼接为 Markdown"""
    heading = "#" * level
    return f"{heading} {title}\n\n{content}\n"


def assemble_paper(title: str, sections: Dict[str, str]) -> str:
    """将各章节内容组装为整篇论文 Markdown（逐章清理 AI 附加内容）"""
    parts = [f"# {title}\n"]
    for section_title, content in sections.items():
        parts.append(chapter_to_markdown(section_title, strip_ai_meta(content)))
    return "\n".join(parts)