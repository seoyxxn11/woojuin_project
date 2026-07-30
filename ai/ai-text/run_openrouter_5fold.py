from __future__ import annotations

import argparse
import json
import os
import time
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent
DEFAULT_DATASET = ROOT / "dataset" / "tester" / "정우현-5fold"
DEFAULT_DEFINITIONS = ROOT / "config" / "generated" / "category-descriptions-20260722-164953.json"
MODEL = "qwen/qwen3-8b"
API_URL = "https://openrouter.ai/api/v1/chat/completions"
OLLAMA_MODEL = "qwen3:8b"
OLLAMA_URL = "http://localhost:11434/api/chat"


DESCRIPTION_PROMPT = """당신은 한국어 콘텐츠 분류 체계를 설계하는 AI입니다.

아래 샘플은 "{category_name}" 카테고리에 사람이 분류한 URL 데이터입니다.
샘플의 공통적인 중심 목적을 바탕으로 설명을 작성하세요.

작성 규칙:
1. description은 이 카테고리에 포함해야 하는 내용의 범위를 한국어 한 문장으로 설명하세요.
2. 데이터에 없는 세부 범위를 임의로 확대하지 마세요.
3. 카테고리 이름을 반복하기보다 판단 기준과 사용 목적을 명확히 쓰세요.
4. examples는 원문을 복사하지 말고 특징을 일반화한 짧은 예시 3개를 작성하세요.
5. 다른 카테고리와 겹치는 내용은 중심 목적을 기준으로 구분하세요.
6. JSON 객체만 출력하세요.

전체 카테고리:
{all_categories}

카테고리 데이터:
{samples}

출력 형식:
{{"description":"string","examples":["string","string","string"]}}"""


CLASSIFICATION_PROMPT = """당신은 사용자가 저장한 콘텐츠의 카테고리별 적합도를 판단하는 AI입니다.

카테고리 정보:
{definitions}

분류 원칙:
1. 보통 가장 중심적인 카테고리 하나가 존재합니다.
2. 두 개 이상의 카테고리가 핵심 내용을 각각 직접 설명할 때만 여러 카테고리를 반환하세요.
3. 특정 단어, 간접 언급, 배경 정보만으로 카테고리를 추가하지 마세요.
4. 핵심 주제와 사용자가 나중에 다시 찾을 가능성이 높은 목적을 기준으로 판단하세요.
5. 각 score는 0.0부터 1.0 사이입니다.
6. 적합도가 높은 순서대로 직접 관련된 카테고리만 반환하세요.
7. 제공된 categoryId와 categoryName만 사용하세요.
8. 적합한 카테고리가 없으면 빈 배열을 반환할 수 있습니다.
9. JSON 외의 설명이나 Markdown을 출력하지 마세요.

출력 형식:
{{"categories":[{{"categoryId":"CATEGORY_ID","categoryName":"카테고리 이름","score":0.0}}]}}

입력 콘텐츠:
{content}"""


def load_env(path: Path) -> None:
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, value = stripped.split("=", 1)
        if key.strip() == "OPENROUTER_API_KEY" and key.strip() not in os.environ:
            os.environ[key.strip()] = value.strip().strip("\"'")


def read_json(path: Path) -> Any:
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, ensure_ascii=False, indent=2), encoding="utf-8")


def item_content(value: dict[str, Any], max_chars: int) -> str:
    parts = []
    if value.get("title"):
        parts.append(f"제목: {value['title']}")
    preview = value.get("preview") or {}
    if preview.get("description"):
        parts.append(f"미리보기: {preview['description']}")
    body = value.get("summary") or value.get("content")
    if body:
        parts.append(f"본문: {str(body)[:max_chars]}")
    if value.get("url"):
        parts.append(f"URL: {value['url']}")
    return "\n".join(parts)


def summarized_item_content(value: dict[str, Any]) -> str:
    title = str(value.get("title") or "").strip()
    summary = str(value.get("summary") or "").strip()
    if not title:
        raise ValueError("최종 title이 비어 있습니다")
    if not summary:
        raise ValueError("최종 summary가 비어 있습니다")
    return f"제목: {title}\n요약: {summary}"


def load_fold_item(path: Path, metadata_dataset: Path | None) -> dict[str, Any]:
    if metadata_dataset is None:
        return read_json(path)
    metadata_path = metadata_dataset / path.parent.name / path.name
    if not metadata_path.exists():
        raise ValueError(f"제목·요약 데이터가 없습니다: {metadata_path}")
    return read_json(metadata_path)


def extract_json(text: str) -> Any:
    cleaned = text.strip()
    if cleaned.startswith("```"):
        cleaned = cleaned.split("\n", 1)[1].rsplit("```", 1)[0].strip()
    try:
        return json.loads(cleaned)
    except json.JSONDecodeError:
        start = cleaned.find("{")
        end = cleaned.rfind("}")
        if start >= 0 and end > start:
            return json.loads(cleaned[start : end + 1])
        raise


def call_model(
    provider: str,
    api_key: str | None,
    prompt: str,
    schema: dict[str, Any],
    retries: int = 5,
) -> dict[str, Any]:
    if provider == "openrouter":
        payload = {
            "model": MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "temperature": 0,
            "response_format": {
                "type": "json_schema",
                "json_schema": {"name": "result", "strict": True, "schema": schema},
            },
        }
        url = API_URL
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
            "HTTP-Referer": "https://github.com/ssafy",
            "X-OpenRouter-Title": "Woojuin AI Text Evaluation",
        }
    else:
        payload = {
            "model": OLLAMA_MODEL,
            "messages": [{"role": "user", "content": prompt}],
            "stream": False,
            "think": False,
            "format": schema,
            "options": {"temperature": 0, "seed": 42, "num_ctx": 8192},
        }
        url = OLLAMA_URL
        headers = {"Content-Type": "application/json"}
    data = json.dumps(payload).encode("utf-8")
    last_error: Exception | None = None
    for attempt in range(1, retries + 1):
        request = Request(
            url,
            data=data,
            method="POST",
            headers=headers,
        )
        try:
            started = time.perf_counter()
            with urlopen(request, timeout=180) as response:
                raw = json.loads(response.read().decode("utf-8"))
            latency_ms = round((time.perf_counter() - started) * 1000, 2)
            if provider == "openrouter":
                message = raw["choices"][0]["message"]["content"]
                usage = raw.get("usage")
                resolved_model = raw.get("model")
                request_id = raw.get("id")
            else:
                message = raw["message"]["content"]
                usage = {
                    "prompt_tokens": raw.get("prompt_eval_count"),
                    "completion_tokens": raw.get("eval_count"),
                    "total_tokens": (
                        (raw.get("prompt_eval_count") or 0) + (raw.get("eval_count") or 0)
                    ),
                }
                resolved_model = raw.get("model")
                request_id = None
            return {
                "parsed": extract_json(message),
                "rawText": message,
                "usage": usage,
                "latencyMs": latency_ms,
                "model": resolved_model,
                "requestId": request_id,
            }
        except (HTTPError, URLError, TimeoutError, KeyError, json.JSONDecodeError) as exc:
            last_error = exc
            if attempt == retries:
                break
            time.sleep(min(2 ** attempt, 20))
    raise RuntimeError(f"OpenRouter 호출 실패: {last_error}")


DESCRIPTION_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "description": {"type": "string"},
        "examples": {
            "type": "array",
            "minItems": 3,
            "maxItems": 3,
            "items": {"type": "string"},
        },
    },
    "required": ["description", "examples"],
}

CATEGORY_SCHEMA = {
    "type": "object",
    "additionalProperties": False,
    "properties": {
        "categories": {
            "type": "array",
            "items": {
                "type": "object",
                "additionalProperties": False,
                "properties": {
                    "categoryId": {"type": "string"},
                    "categoryName": {"type": "string"},
                    "score": {"type": "number", "minimum": 0, "maximum": 1},
                },
                "required": ["categoryId", "categoryName", "score"],
            },
        }
    },
    "required": ["categories"],
}


def files_by_category(root: Path) -> dict[str, list[Path]]:
    return {
        directory.name: sorted(directory.glob("*.txt"))
        for directory in sorted(root.iterdir())
        if directory.is_dir()
    }


def validate_folds(dataset: Path) -> None:
    folds = sorted(dataset.glob("fold-*"))
    if len(folds) != 5:
        raise ValueError(f"fold가 5개여야 합니다: {len(folds)}")
    test_names: list[str] = []
    for fold in folds:
        train = {p.name for p in (fold / "category-summary").rglob("*.txt")}
        test = {p.name for p in (fold / "classification").rglob("*.txt")}
        overlap = train & test
        if overlap:
            raise ValueError(f"{fold.name} train/test 중복: {sorted(overlap)[:5]}")
        if len(train | test) != 112:
            raise ValueError(f"{fold.name} 전체 항목 수 오류: {len(train | test)}")
        test_names.extend(test)
    duplicates = [name for name, count in Counter(test_names).items() if count != 1]
    if duplicates or len(test_names) != 112:
        raise ValueError(f"테스트 fold 배정 오류: total={len(test_names)}, duplicates={duplicates[:5]}")


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dataset", type=Path, default=DEFAULT_DATASET)
    parser.add_argument("--output", type=Path)
    parser.add_argument("--fold", choices=[f"fold-{index}" for index in range(1, 6)])
    parser.add_argument("--provider", choices=["openrouter", "ollama"], default="openrouter")
    parser.add_argument(
        "--metadata-dataset",
        type=Path,
        help="최종 title과 summary가 반영된 데이터셋. 지정하면 원문 대신 title+summary만 사용합니다.",
    )
    args = parser.parse_args()

    load_env(ROOT.parent.parent / ".env")
    api_key = os.environ.get("OPENROUTER_API_KEY")
    if args.provider == "openrouter" and not api_key:
        raise ValueError("OPENROUTER_API_KEY가 없습니다")

    dataset = args.dataset.resolve()
    metadata_dataset = args.metadata_dataset.resolve() if args.metadata_dataset else None
    validate_folds(dataset)
    if metadata_dataset:
        metadata_files = list(metadata_dataset.rglob("*.txt"))
        if len(metadata_files) != 112:
            raise ValueError(f"제목·요약 데이터는 112건이어야 합니다: {len(metadata_files)}")
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    output = (
        args.output or ROOT / "results" / f"{stamp}-{args.provider}-qwen3-8b-5fold"
    ).resolve()
    output.mkdir(parents=True, exist_ok=True)

    base_definitions = read_json(DEFAULT_DEFINITIONS)
    category_names = [item["name"] for item in base_definitions]
    all_categories = "\n".join(f"- {name}" for name in category_names)
    evaluation_rows = []

    selected_folds = sorted(dataset.glob(args.fold or "fold-*"))
    for fold in selected_folds:
        fold_output = output / fold.name
        definitions_path = fold_output / "category-descriptions.json"
        if definitions_path.exists():
            definitions = read_json(definitions_path)
        else:
            definitions = []
            train_by_category = files_by_category(fold / "category-summary")
            for index, base in enumerate(base_definitions, 1):
                name = base["name"]
                checkpoint = fold_output / "description-calls" / f"{base['id']}.json"
                if checkpoint.exists():
                    response = read_json(checkpoint)
                else:
                    samples = []
                    for path in train_by_category.get(name, [])[:20]:
                        value = load_fold_item(path, metadata_dataset)
                        content = (
                            summarized_item_content(value)
                            if metadata_dataset
                            else item_content(value, 1200)
                        )
                        samples.append(f"[{path.stem}]\n{content}")
                    prompt = DESCRIPTION_PROMPT.format(
                        category_name=name,
                        all_categories=all_categories,
                        samples="\n\n".join(samples),
                    )
                    response = call_model(
                        args.provider, api_key, prompt, DESCRIPTION_SCHEMA
                    )
                    write_json(checkpoint, response)
                definitions.append({**base, **response["parsed"]})
                print(f"[{fold.name}] 설명 {index}/{len(base_definitions)}: {name}", flush=True)
            write_json(definitions_path, definitions)

        definition_text = "\n".join(
            f"- {item['id']} | {item['name']}: {item['description']} "
            f"(예: {', '.join(item.get('examples', []))})"
            for item in definitions
        )
        test_by_category = files_by_category(fold / "classification")
        test_files = [path for paths in test_by_category.values() for path in paths]
        for index, path in enumerate(test_files, 1):
            checkpoint = fold_output / "classification-calls" / f"{path.stem}.json"
            if checkpoint.exists():
                response = read_json(checkpoint)
            else:
                value = load_fold_item(path, metadata_dataset)
                content = (
                    summarized_item_content(value)
                    if metadata_dataset
                    else item_content(value, 6000)
                )
                prompt = CLASSIFICATION_PROMPT.format(
                    definitions=definition_text,
                    content=content,
                )
                response = call_model(
                    args.provider, api_key, prompt, CATEGORY_SCHEMA
                )
                write_json(checkpoint, response)
            predicted = response["parsed"].get("categories", [])
            expected = path.parent.name
            row = {
                "fold": fold.name,
                "file": path.name,
                "expected": expected,
                "predicted": predicted,
                "top1": predicted[0]["categoryName"] if predicted else None,
                "correct": bool(predicted and predicted[0]["categoryName"] == expected),
                "usage": response.get("usage"),
                "latencyMs": response.get("latencyMs"),
            }
            evaluation_rows.append(row)
            print(f"[{fold.name}] 분류 {index}/{len(test_files)}: {path.name}", flush=True)
        write_json(fold_output / "evaluation-results.json", [
            row for row in evaluation_rows if row["fold"] == fold.name
        ])

    all_rows = []
    for path in sorted(output.glob("fold-*/evaluation-results.json")):
        all_rows.extend(read_json(path))
    correct = sum(row["correct"] for row in all_rows)
    summary = {
        "model": MODEL if args.provider == "openrouter" else OLLAMA_MODEL,
        "provider": args.provider,
        "dataset": str(dataset),
        "metadataDataset": str(metadata_dataset) if metadata_dataset else None,
        "classificationInput": (
            "category name + category description + title + summary"
            if metadata_dataset
            else "category name + category description + raw content"
        ),
        "descriptionCalls": 55,
        "classificationCalls": len(all_rows),
        "totalExpectedCalls": 55 + len(all_rows),
        "items": len(all_rows),
        "top1Correct": correct,
        "top1Accuracy": correct / len(all_rows) if all_rows else 0,
        "createdAt": datetime.now().astimezone().isoformat(),
    }
    write_json(output / "evaluation-results.json", all_rows)
    write_json(output / "summary.json", summary)
    print(json.dumps(summary, ensure_ascii=False, indent=2))
    print(f"OUTPUT={output}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
