from __future__ import annotations

import re


UNUSABLE_SUMMARY_PATTERNS = (
    re.compile(r"요약할\s+수\s+있는\s+(?:내용|정보)이?\s*없"),
    re.compile(r"요약할\s+수\s+없"),
    re.compile(r"(?:내용|정보|요약\s*정보).{0,20}(?:누락|제공되지\s*않|없습니다)"),
    re.compile(r"원문.{0,20}(?:포함되지\s*않|없습니다)"),
)


def usable_url_summary(value: object) -> str:
    """내용 부재를 알리는 placeholder 요약은 빈 값으로 정규화한다."""
    if not isinstance(value, str):
        return ""
    summary = value.strip()
    if not summary:
        return ""
    if any(pattern.search(summary) for pattern in UNUSABLE_SUMMARY_PATTERNS):
        return ""
    return summary
