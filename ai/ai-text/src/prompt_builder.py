from pathlib import Path
import re

DEFAULT_TITLE_PATTERN = re.compile(
    r"^텍스트-(?:\d{4}\.\d{2}\.\d{2}(?:-\d{4})?|\d{4}-\d{2}-\d{2})$"
)
def load_prompt(path: Path) -> str: return path.read_text(encoding="utf-8")
def format_category_definitions(definitions: list[dict]) -> str:
    lines: list[str] = []
    for item in definitions:
        examples = ", ".join(item.get("examples", [])) or "없음"
        category_id = item.get("id", item["name"])
        lines.append(f"- {category_id} | {item['name']}: {item['description']} (예: {examples})")
    return "\n".join(lines)

def format_category_names(categories: list[str], definitions: list[dict] | None = None) -> str:
    if definitions:
        return "\n".join(f"- {item.get('id', item['name'])} | {item['name']}" for item in definitions)
    return "\n".join(f"- {category}" for category in categories)

def build_prompt(
    template: str,
    content: str,
    categories: list[str],
    title: str = "",
    category_definitions: list[dict] | None = None,
    include_category_descriptions: bool = True,
) -> str:
    if "{{CONTENT}}" not in template: raise ValueError("프롬프트에 {{CONTENT}}가 없습니다.")
    if "{{TITLE_CONTEXT}}" not in template: raise ValueError("프롬프트에 {{TITLE_CONTEXT}}가 없습니다.")
    if "{{CATEGORY_DEFINITIONS}}" in template and include_category_descriptions and not category_definitions:
        raise ValueError("프롬프트에 사용할 카테고리 정의가 없습니다.")
    meaningful_title = title.strip() if title and not DEFAULT_TITLE_PATTERN.fullmatch(title.strip()) else ""
    title_context = f"입력 제목:\n{meaningful_title}\n\n" if meaningful_title else ""
    category_context = (format_category_definitions(category_definitions or [])
                        if include_category_descriptions else format_category_names(categories, category_definitions))
    return (template.replace("{{CATEGORIES}}", ", ".join(categories))
            .replace("{{CATEGORY_DEFINITIONS}}", category_context)
            .replace("{{TITLE_CONTEXT}}", title_context).replace("{{CONTENT}}", content))
