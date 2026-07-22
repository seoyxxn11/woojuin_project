import csv, json
from pathlib import Path
import pytest
from src.auto_evaluator import evaluate, speed_scores
from src.comparison import compare_result_directories
from src.dataset_loader import load_categories, load_category_definitions, load_memo_dataset
from src.metrics import classification_metrics, nullable_average, percentile
from src.prompt_builder import build_prompt
from src.report_generator import generate_auto_report, generate_final_report, generate_mode_report
from src.response_parser import output_schema, parse_response
from src.result_writer import append_jsonl, read_jsonl, write_json
from run_tests import all_mode_command, args as cli_args

VALID={"summary":"S3 업로드와 파일명 중복 처리를 구현한다.","category":"학습·지식","tags":["Spring Boot","S3","업로드"],"keywords":["이미지 업로드","파일명","중복 처리"]}
CATEGORIES=["생활·할 일","학습·지식","취업·커리어","여행·장소","음식·맛집","쇼핑·제품","건강·운동","문화·콘텐츠","돈·재테크","아이디어·영감","기타"]
def raw(value=VALID): return json.dumps(value,ensure_ascii=False)
def test_normal_json(): assert parse_response(raw(),CATEGORIES)["schemaValid"]
def test_markdown_json(): assert parse_response(f"```json\n{raw()}\n```",CATEGORIES)["jsonValid"]
def test_extra_text():
    r=parse_response("설명\n"+raw()+"\n끝",CATEGORIES); assert r["jsonValid"] and r["extraTextDetected"]
def test_think_tag():
    r=parse_response("<think>비공개 사고</think>"+raw(),CATEGORIES); assert r["schemaValid"] and r["thinkingTagDetected"]

def test_category_confidence_range_and_extra_field():
    valid = json.dumps({"category":"학습·지식","confidence":.91}, ensure_ascii=False)
    assert parse_response(valid, CATEGORIES, "category-only")["schemaValid"]
    out_of_range = json.dumps({"category":"학습·지식","confidence":1.1}, ensure_ascii=False)
    assert not parse_response(out_of_range, CATEGORIES, "category-only")["schemaValid"]
    extra = json.dumps({"category":"학습·지식","confidence":.9,"summary":"불필요"}, ensure_ascii=False)
    assert not parse_response(extra, CATEGORIES, "category-only")["schemaValid"]
    boolean = json.dumps({"category":"학습·지식","confidence":True}, ensure_ascii=False)
    assert not parse_response(boolean, CATEGORIES, "category-only")["schemaValid"]

def test_mode_specific_schema_rejects_unrequested_fields():
    assert parse_response('{"summary":"한 문장입니다."}', CATEGORIES, "summary-only")["schemaValid"]
    assert not parse_response('{"summary":"한 문장입니다.","category":"학습·지식"}', CATEGORIES, "summary-only")["schemaValid"]
    metadata = '{"tags":["a","b","c"],"keywords":["d","e","f"]}'
    assert parse_response(metadata, CATEGORIES, "metadata-only")["schemaValid"]
@pytest.mark.parametrize("change",[
    {"keywords":None},{"category":"미분류"},{"tags":["a","b"]},{"tags":["a","a","b"]}
])
def test_schema_failures(change):
    value=VALID.copy()
    if change.get("keywords", "present") is None: value.pop("keywords")
    else: value.update(change)
    assert not parse_response(raw(value),CATEGORIES)["schemaValid"]
def test_keyword_recall_and_forbidden():
    info=parse_response(raw(),CATEGORIES); expected={"categories":["학습·지식"],"requiredKeywords":["S3","없는 말"],"summaryPoints":[],"forbiddenClaims":["파일명 중복 처리"]}
    e=evaluate(info,expected,CATEGORIES); assert e["requiredKeywordRecall"]==.5 and e["possibleHallucination"]

def test_empty_semantic_answers_are_not_zero():
    info=parse_response(raw(),CATEGORIES)
    result=evaluate(info,{"categories":["학습·지식"],"requiredKeywords":[],"summaryPoints":[],"forbiddenClaims":[]},CATEGORIES)
    assert result["requiredKeywordRecall"] is None
    assert result["summaryPointRecall"] is None
    assert result["possibleHallucination"] is None
    assert nullable_average([result], "requiredKeywordRecall") is None
def test_speed_score(): assert speed_scores({"a":100,"b":200})=={"a":5.0,"b":2.5}

def test_percentile_and_classification_metrics():
    assert percentile([1,2,3,4,5], .95) == pytest.approx(4.8)
    rows = [
        {"expectedCategory":"학습·지식","generatedCategory":"학습·지식"},
        {"expectedCategory":"학습·지식","generatedCategory":"아이디어·영감"},
        {"expectedCategory":"아이디어·영감","generatedCategory":"아이디어·영감"},
    ]
    metrics=classification_metrics(rows,["학습·지식","아이디어·영감"])
    assert metrics["accuracy"] == pytest.approx(2/3)
    assert metrics["macroPrecision"] == pytest.approx(.75)
    assert metrics["macroRecall"] == pytest.approx(.75)
    assert metrics["macroF1"] == pytest.approx(2/3)
    assert metrics["confusionMatrix"]["학습·지식"]["아이디어·영감"] == 1

def test_failed_response_is_preserved(tmp_path):
    path=tmp_path/"raw"/"results.jsonl"
    row={"testId":"TEXT-001","rawResponse":"not json","error":{"requestFailed":True,"errorType":"INVALID_JSON"}}
    append_jsonl(path,row)
    assert read_jsonl(path)==[row]

def test_report_uses_na_and_result_comparison(tmp_path):
    metadata={"testMode":"summary-only","datasetType":"memo","datasetCount":1,"models":["m"],"promptVersion":"v1","startedAt":"start","completedAt":"end","environment":"test","options":{"temperature":0,"seed":42,"thinking":False,"contextLength":4096},"categories":CATEGORIES}
    row={"testId":"TEXT-001","model":"m","runType":"WARM","responseReceived":True,"jsonValid":True,"schemaValid":True,"outputConstraintValid":True,"requestFailed":False,"requiredKeywordRecall":None,"summaryPointRecall":None,"possibleHallucination":None,"totalDurationMs":100,"tokensPerSecond":10,"promptEvalCount":20,"evalCount":5,"loadDurationMs":1,"evalDurationMs":50}
    first=tmp_path/"first"; first.mkdir()
    write_json(first/"run-metadata.json",metadata); write_json(first/"evaluation-results.json",[row])
    generate_mode_report(metadata,[row],CATEGORIES,first/"report.md")
    assert "N/A" in (first/"report.md").read_text(encoding="utf-8")
    output=compare_result_directories([first],tmp_path)
    assert (output/"comparison-report.md").is_file()

def test_legacy_integrated_report_handles_missing_semantic_answers(tmp_path):
    row={"model":"m","runType":"WARM","requestFailed":False,"responseReceived":True,"jsonValid":True,"schemaValid":True,"categoryCorrect":True,"requiredKeywordRecall":None,"forbiddenClaimCount":None,"totalDurationMs":100,"tokensPerSecond":10,"summarySentenceCountValid":True,"categoryValueValid":True,"tagCountValid":True,"tagDuplicateFree":True,"keywordCountValid":True,"keywordDuplicateFree":True,"loadDurationMs":1,"promptEvalCount":10,"evalCount":5,"possibleHallucination":None}
    output=tmp_path/"legacy.md"
    generate_auto_report([row],output)
    assert "N/A" in output.read_text(encoding="utf-8")

def test_all_modes_forwards_shared_options():
    options=cli_args(["--all-modes","--models","qwen3:4b","qwen3:8b","--memo-only","--repeat","2","--test-ids","TEXT-001"])
    command=all_mode_command(options,"category-only",Path("combined"))
    assert "--all-modes" not in command
    assert "--category-only" in command
    assert "qwen3:4b" in command and "qwen3:8b" in command
    assert "--memo-only" in command and "TEXT-001" in command and "2" in command
    assert command[-2:] == ["--output-parent", "combined"]

def test_all_modes_is_mutually_exclusive_with_single_mode():
    with pytest.raises(SystemExit):
        cli_args(["--all-modes","--integrated"])

def test_category_folders_drive_prompt_and_schema(tmp_path):
    (tmp_path / "새 카테고리").mkdir()
    (tmp_path / "기타").mkdir()
    categories = load_categories(tmp_path)
    prompt = build_prompt("분류: {{CATEGORIES}}\n{{TITLE_CONTEXT}}내용: {{CONTENT}}", "메모", categories)
    schema = output_schema(categories)
    assert "새 카테고리" in prompt
    assert schema["properties"]["category"]["enum"] == categories
    assert "title" not in schema["properties"]

def test_category_definitions_match_folders_and_reach_prompt(tmp_path):
    memo=tmp_path/"memo"; (memo/"학습·지식").mkdir(parents=True)
    path=tmp_path/"categories.json"
    path.write_text(json.dumps([{"name":"학습·지식","description":"기술과 지식 정리 중심","examples":["JWT 구현"]}],ensure_ascii=False),encoding="utf-8")
    definitions=load_category_definitions(path,memo)
    prompt=build_prompt("{{CATEGORY_DEFINITIONS}}\n{{TITLE_CONTEXT}}{{CONTENT}}","본문",["학습·지식"],category_definitions=definitions)
    assert "기술과 지식 정리 중심" in prompt and "JWT 구현" in prompt

def test_default_title_is_excluded_and_user_title_is_included():
    template = "분류: {{CATEGORIES}}\n{{TITLE_CONTEXT}}내용: {{CONTENT}}"
    default_prompt = build_prompt(template, "본문", CATEGORIES, "텍스트-2026.07.20-0905")
    user_prompt = build_prompt(template, "본문", CATEGORIES, "JWT 재발급 구조 정리")
    assert "텍스트-2026.07.20-0905" not in default_prompt
    assert "입력 제목:\nJWT 재발급 구조 정리" in user_prompt

def test_load_memos_with_explicit_and_automatic_ids(tmp_path):
    development = tmp_path / "학습·지식"
    career = tmp_path / "취업·커리어"
    development.mkdir(); career.mkdir()
    (development / "002-S3 업로드.txt").write_text("S3 업로드 메모", encoding="utf-8")
    (career / "면접 준비.txt").write_text("백엔드 면접 준비", encoding="utf-8")
    rows = load_memo_dataset(tmp_path)
    by_path = {row["sourcePath"]: row for row in rows}
    assert by_path["학습·지식/002-S3 업로드.txt"]["testId"] == "TEXT-002"
    assert by_path["학습·지식/002-S3 업로드.txt"]["idAutoAssigned"] is False
    assert by_path["취업·커리어/면접 준비.txt"]["testId"] == "TEXT-001"
    assert by_path["취업·커리어/면접 준비.txt"]["idAutoAssigned"] is True
    assert by_path["취업·커리어/면접 준비.txt"]["expected"]["categories"] == ["취업·커리어"]

def test_duplicate_memo_id_is_rejected(tmp_path):
    development = tmp_path / "학습·지식"
    career = tmp_path / "취업·커리어"
    development.mkdir(); career.mkdir()
    (development / "001-첫 메모.txt").write_text("첫 메모", encoding="utf-8")
    (career / "001-둘째 메모.txt").write_text("둘째 메모", encoding="utf-8")
    with pytest.raises(ValueError, match="중복 메모 ID"):
        load_memo_dataset(tmp_path)
def _write_csv(path: Path, rows: list[dict]):
    with path.open('w',encoding='utf-8-sig',newline='') as f:
        w=csv.DictWriter(f,fieldnames=rows[0]); w.writeheader(); w.writerows(rows)
def test_manual_incomplete(tmp_path):
    (tmp_path/'detail').mkdir(); _write_csv(tmp_path/'manual-evaluation.csv',[{"model":"m","summaryQuality":"","factuality":"","tagQuality":"","readability":"","hallucinationLevel":""}])
    assert not generate_final_report(tmp_path)
def test_manual_complete(tmp_path):
    (tmp_path/'detail').mkdir(); _write_csv(tmp_path/'manual-evaluation.csv',[{"model":"m","summaryQuality":"5","factuality":"5","tagQuality":"5","readability":"5","hallucinationLevel":"NONE"}])
    _write_csv(tmp_path/'detail'/'auto-evaluation.csv',[{"model":"m","runType":"WARM","requestFailed":"False","totalDurationMs":"100","categoryCorrect":"True","requiredKeywordRecall":"1","schemaValid":"True","tokensPerSecond":"10"}])
    assert generate_final_report(tmp_path) and (tmp_path/'ai-text-comparison-final.csv').exists()
    rows = list(csv.DictReader((tmp_path/'ai-text-comparison-final.csv').open(encoding='utf-8-sig')))
    assert float(rows[0]['total']) == 100.0
