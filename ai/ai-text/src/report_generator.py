from collections import defaultdict
from pathlib import Path
import csv, math, statistics
from .auto_evaluator import speed_scores
from .metrics import classification_metrics, confidence_metrics, nullable_average, nullable_rate, operational_metrics
from .result_writer import write_csv

def percentile(values: list[float], q: float) -> float:
    if not values: return 0.0
    values = sorted(values); index = (len(values)-1)*q; lo, hi = math.floor(index), math.ceil(index)
    return values[lo] if lo == hi else values[lo] + (values[hi]-values[lo])*(index-lo)

def _truth(value: object) -> bool:
    return value is True or (isinstance(value, str) and value.strip().lower() in ("true", "1", "yes"))
def _pct(rows: list[dict], key: str) -> float: return 100 * sum(_truth(x.get(key)) for x in rows) / len(rows) if rows else 0
def _avg(rows: list[dict], key: str) -> float:
    vals = [float(x[key]) for x in rows if x.get(key) not in (None, "")]
    return statistics.mean(vals) if vals else 0
def _table(headers: list[str], rows: list[list]) -> str:
    return "| " + " | ".join(headers) + " |\n|" + "|".join(["---"] + ["---:" for _ in headers[1:]]) + "|\n" + "\n".join("| " + " | ".join(map(str, r)) + " |" for r in rows)

def generate_auto_report(rows: list[dict], output: Path) -> None:
    groups = defaultdict(list)
    for r in rows: groups[r["model"]].append(r)
    summary, constraints, speeds, failures, hallucinations = [], [], [], [], []
    for model, items in groups.items():
        warm = [x for x in items if x["runType"] == "WARM" and not x.get("requestFailed")]
        durations = [float(x.get("totalDurationMs", 0)) for x in warm]
        required_recall = nullable_average(items, "requiredKeywordRecall")
        forbidden_values = [int(x["forbiddenClaimCount"]) for x in items if x.get("forbiddenClaimCount") is not None]
        summary.append([model,len(items),f"{_pct(items,'responseReceived'):.1f}%",f"{_pct(items,'jsonValid'):.1f}%",f"{_pct(items,'schemaValid'):.1f}%",f"{_pct(items,'categoryCorrect'):.1f}%",_display(required_recall, True),sum(forbidden_values) if forbidden_values else "N/A",f"{_avg(warm,'totalDurationMs'):.1f}",f"{percentile(durations,.95):.1f}",f"{_avg(warm,'tokensPerSecond'):.1f}"])
        constraints.append([model]+[f"{_pct(items,k):.1f}%" for k in ('summarySentenceCountValid','categoryValueValid','tagCountValid','tagDuplicateFree','keywordCountValid','keywordDuplicateFree')])
        cold = [x for x in items if x["runType"] == "COLD"]
        speeds.append([model,f"{_avg(cold,'totalDurationMs'):.1f}",f"{_avg(warm,'totalDurationMs'):.1f}",f"{statistics.median(durations) if durations else 0:.1f}",f"{percentile(durations,.95):.1f}",f"{_avg(warm,'promptEvalCount'):.1f}",f"{_avg(warm,'evalCount'):.1f}",f"{_avg(warm,'tokensPerSecond'):.1f}"])
        failures.extend([[model,x['testId'],x['runNumber'],x.get('errorType',''),x.get('errorMessage','')] for x in items if x.get('requestFailed')])
        hallucinations.extend([[model,x['testId'],x.get('detectedForbiddenClaims',''),x.get('generatedSummary','')] for x in items if x.get('possibleHallucination')])
    text = "# 로컬 LLM 자동 비교 보고서\n\n## 모델별 자동 평가 요약\n\n"+_table(["모델","호출 수","응답 성공률","JSON 성공률","스키마 성공률","카테고리 정확도","필수 키워드 재현율","금지 표현 발생","평균 응답 시간(ms)","P95(ms)","평균 TPS"],summary)+"\n\n## 모델별 출력 제약 준수율\n\n"+_table(["모델","요약 문장 수","카테고리 값","태그 개수","태그 중복 없음","키워드 개수","키워드 중복 없음"],constraints)+"\n\n## 모델별 속도 비교\n\n"+_table(["모델","콜드 스타트(ms)","평균 웜 응답(ms)","중앙값","P95","입력 토큰","출력 토큰","TPS"],speeds)+"\n\n## 실패 내역\n\n"+_table(["모델","testId","실행 번호","오류 유형","오류 메시지"],failures)+"\n\n## 환각 가능성 내역\n\n"+_table(["모델","testId","감지된 금지 표현","생성 요약"],hallucinations)
    output.write_text(text+"\n", encoding="utf-8")

def generate_final_report(result_dir: Path) -> bool:
    manual = list(csv.DictReader((result_dir/"manual-evaluation.csv").open(encoding="utf-8-sig")))
    required = ("summaryQuality","factuality","tagQuality","readability","hallucinationLevel")
    complete = bool(manual) and all(all(r.get(k,"").strip() for k in required) for r in manual)
    if not complete:
        (result_dir/"ai-text-comparison-final.md").write_text("# 최종 비교 보고서\n\n수동 평가 미완료\n",encoding="utf-8")
        write_csv(result_dir/"ai-text-comparison-final.csv", [{"status":"수동 평가 미완료"}]); return False
    groups=defaultdict(list)
    for r in manual: groups[r["model"]].append(r)
    auto=list(csv.DictReader((result_dir/"detail"/"auto-evaluation.csv").open(encoding="utf-8-sig")))
    ag=defaultdict(list)
    for r in auto: ag[r["model"]].append(r)
    avgt={m:_avg([x for x in rows if x['runType']=='WARM' and x.get('requestFailed','').lower()!='true'],'totalDurationMs') for m,rows in ag.items()}; ss=speed_scores(avgt)
    scores=[]
    for m, rs in groups.items():
        summary_score=_avg(rs,'summaryQuality')/5*25; cat=_pct(ag[m],'categoryCorrect')/100*20
        tk=_avg(rs,'tagQuality')/5*10+_avg(ag[m],'requiredKeywordRecall')*10
        hall=statistics.mean({'NONE':5,'MINOR':2.5,'MAJOR':0}[x['hallucinationLevel'].upper()] for x in rs)
        fact=_avg(rs,'factuality')/5*15+hall; js=_pct(ag[m],'schemaValid')/100*10
        total=summary_score+cat+tk+fact+js+ss.get(m,0)
        scores.append({"model":m,"summary":summary_score,"category":cat,"tagKeyword":tk,"factuality":fact,"json":js,"speed":ss.get(m,0),"total":total})
    scores.sort(key=lambda x:x['total'],reverse=True); out=[]
    for i,x in enumerate(scores,1): out.append({"rank":i,**{k:(f"{v:.2f}" if isinstance(v,float) else v) for k,v in x.items()}})
    write_csv(result_dir/"ai-text-comparison-final.csv",out)
    table=[[x['rank'],x['model'],x['summary'],x['category'],x['tagKeyword'],x['factuality'],x['json'],x['speed'],x['total']] for x in out]
    manual_table=[[m,f"{_avg(rs,'summaryQuality'):.2f}",f"{_avg(rs,'factuality'):.2f}",f"{_avg(rs,'tagQuality'):.2f}",f"{_avg(rs,'readability'):.2f}","; ".join(x.get('reviewNote','') for x in rs if x.get('reviewNote',''))] for m,rs in groups.items()]
    (result_dir/"ai-text-comparison-final.md").write_text("# 최종 비교 보고서\n\n## 모델별 최종 점수\n\n"+_table(["순위","모델","요약 품질","카테고리","태그·키워드","사실성","JSON 안정성","속도","총점"],table)+"\n\n## 수동 평가 평균\n\n"+_table(["모델","요약 품질","사실성","태그 품질","가독성","주요 의견"],manual_table)+f"\n\n## 최종 판단\n\n최종 종합 점수가 가장 높은 모델: {out[0]['model']}\n",encoding="utf-8")
    return True

def _display(value: object, percent: bool = False, digits: int = 1) -> str:
    if value is None or value == "": return "N/A"
    if isinstance(value, float):
        return f"{value * 100:.{digits}f}%" if percent else f"{value:.{digits}f}"
    return str(value)

def summarize_run(rows: list[dict], categories: list[str], mode: str) -> list[dict]:
    summaries: list[dict] = []
    for model in sorted({str(row["model"]) for row in rows}):
        model_rows = [row for row in rows if row["model"] == model]
        warm = [row for row in model_rows if row.get("runType") == "WARM"]
        classification = classification_metrics(warm, categories) if mode in ("category-only", "integrated") else {}
        confidence = confidence_metrics(warm) if mode == "category-only" else {}
        summaries.append({
            "model": model,
            "testMode": mode,
            "callCount": len(model_rows),
            "responseSuccessRate": nullable_rate(model_rows, "responseReceived"),
            "jsonSuccessRate": nullable_rate(model_rows, "jsonValid"),
            "schemaSuccessRate": nullable_rate(model_rows, "schemaValid"),
            "outputConstraintRate": nullable_rate(model_rows, "outputConstraintValid"),
            "categoryAccuracy": classification.get("accuracy"),
            "macroPrecision": classification.get("macroPrecision"),
            "macroRecall": classification.get("macroRecall"),
            "macroF1": classification.get("macroF1"),
            "requiredKeywordRecall": nullable_average(warm, "requiredKeywordRecall"),
            "summaryPointRecall": nullable_average(warm, "summaryPointRecall"),
            "forbiddenClaimRate": nullable_rate(warm, "possibleHallucination"),
            "sourceKeywordRatio": nullable_average(warm, "sourceKeywordRatio"),
            "confidence": confidence,
            "classification": classification,
            "operational": operational_metrics(warm),
        })
    return summaries

def generate_mode_report(metadata: dict, rows: list[dict], categories: list[str], output: Path) -> list[dict]:
    mode = metadata["testMode"]
    summaries = summarize_run(rows, categories, mode)
    lines = [
        f"# AI 텍스트 테스트 보고서: {mode}", "", "## 기본 정보", "",
        f"- 테스트 모드: {mode}",
        f"- 모델: {', '.join(metadata['models'])}",
        f"- 데이터셋: {metadata['datasetType']}",
        f"- 데이터 수: {metadata['datasetCount']}",
        f"- 프롬프트 버전: {metadata['promptVersion']}",
        f"- 실행 일시: {metadata['startedAt']} ~ {metadata['completedAt']}",
        f"- 실행 환경: {metadata['environment']}",
        f"- temperature / seed: {metadata['options'].get('temperature')} / {metadata['options'].get('seed', 'N/A')}",
        f"- thinking mode: {metadata['options'].get('thinking', 'N/A')}",
        f"- context length: {metadata['options'].get('contextLength', 'N/A')}",
        "- 총 응답 시간에는 모델 로딩 시간이 포함되며 순수 생성 시간은 별도로 표시합니다.",
    ]
    for summary in summaries:
        op = summary["operational"]
        lines += [
            "", f"## 모델: {summary['model']}", "", "### 형식 안정성", "",
            _table(
                ["호출 수", "응답 성공률", "JSON 성공률", "스키마 성공률", "출력 제약 준수율"],
                [[summary["callCount"], _display(summary["responseSuccessRate"], True), _display(summary["jsonSuccessRate"], True), _display(summary["schemaSuccessRate"], True), _display(summary["outputConstraintRate"], True)]],
            ),
        ]
        if mode in ("category-only", "integrated"):
            cm = summary["classification"]
            lines += [
                "", "### 분류 성능", "",
                _table(["Accuracy", "Macro Precision", "Macro Recall", "Macro F1", "평가 건수", "유효하지 않은 예측"], [[_display(cm.get("accuracy"), True), _display(cm.get("macroPrecision"), True), _display(cm.get("macroRecall"), True), _display(cm.get("macroF1"), True), cm.get("evaluatedCount", 0), cm.get("invalidPredictionCount", 0)]]),
                "", _table(["카테고리", "표본 수", "Precision", "Recall", "F1"], [[category, values["support"], _display(values["precision"], True), _display(values["recall"], True), _display(values["f1"], True)] for category, values in cm.get("perCategory", {}).items()]),
                "", "주요 혼동: " + (", ".join(f"{x['actual']} → {x['predicted']} ({x['count']})" for x in cm.get("majorConfusions", [])[:5]) or "없음"),
            ]
            if mode == "category-only":
                conf = summary["confidence"]
                lines += ["", "#### Confidence", "", _table(["전체 평균", "정답 평균", "오답 평균"], [[_display(conf.get("averageConfidence"), False, 3), _display(conf.get("averageConfidenceCorrect"), False, 3), _display(conf.get("averageConfidenceIncorrect"), False, 3)]]), "", _table(["구간", "건수", "정확도"], [[x["range"], x["count"], _display(x["accuracy"], True)] for x in conf.get("buckets", [])])]
        if mode in ("summary-only", "integrated"):
            lines += ["", "### 생성 품질", "", _table(["필수 키워드 재현율", "요약 핵심 내용 재현율", "금지 표현 발생률", "수동 평가"], [[_display(summary["requiredKeywordRecall"], True), _display(summary["summaryPointRecall"], True), _display(summary["forbiddenClaimRate"], True), "미평가"]])]
        if mode == "metadata-only":
            lines += ["", "### 메타데이터 품질", "", _table(["태그 개수 준수율", "키워드 개수 준수율", "태그 중복 없음", "키워드 중복 없음", "원문 키워드 비율"], [[_display(nullable_rate([r for r in rows if r['model']==summary['model'] and r.get('runType')=='WARM'], "tagCountValid"), True), _display(nullable_rate([r for r in rows if r['model']==summary['model'] and r.get('runType')=='WARM'], "keywordCountValid"), True), _display(nullable_rate([r for r in rows if r['model']==summary['model'] and r.get('runType')=='WARM'], "tagDuplicateFree"), True), _display(nullable_rate([r for r in rows if r['model']==summary['model'] and r.get('runType')=='WARM'], "keywordDuplicateFree"), True), _display(summary["sourceKeywordRatio"], True)]])]
        lines += [
            "", "### 운영 성능", "",
            _table(["평균(ms)", "중앙값(ms)", "P95(ms)", "최소(ms)", "최대(ms)", "평균 TPS", "입력 토큰", "출력 토큰", "로딩(ms)", "생성(ms)"], [[_display(op["averageResponseTimeMs"]), _display(op["medianResponseTimeMs"]), _display(op["p95ResponseTimeMs"]), _display(op["minResponseTimeMs"]), _display(op["maxResponseTimeMs"]), _display(op["averageTokensPerSecond"]), _display(op["averagePromptTokens"]), _display(op["averageOutputTokens"]), _display(op["averageLoadDurationMs"]), _display(op["averageGenerationDurationMs"])]])
        ]
        model_rows = [r for r in rows if r["model"] == summary["model"]]
        failures = [r for r in model_rows if r.get("requestFailed") or r.get("schemaValid") is False or r.get("categoryCorrect") is False or r.get("thinkingTagDetected") or (r.get("forbiddenClaimCount") or 0) > 0]
        failure_rows = []
        for row in failures:
            kind = row.get("errorType")
            if not kind and row.get("thinkingTagDetected"): kind = "THINK_EXPOSED"
            if not kind and (row.get("forbiddenClaimCount") or 0) > 0: kind = "FORBIDDEN_CLAIM"
            if not kind and row.get("categoryCorrect") is False: kind = "CATEGORY_MISMATCH"
            failure_rows.append([row["testId"], kind or "VALIDATION", row.get("errorMessage", "")])
        p95 = op.get("p95ResponseTimeMs")
        if p95 is not None:
            for row in model_rows:
                if row.get("runType") == "WARM" and row.get("totalDurationMs") not in (None, "") and float(row["totalDurationMs"]) > p95:
                    failure_rows.append([row["testId"], "RESPONSE_TIME_OUTLIER", f"{float(row['totalDurationMs']):.1f}ms > P95 {p95:.1f}ms"])
        lines += ["", "### 실패 사례", "", _table(["testId", "유형", "메시지"], failure_rows) if failure_rows else "없음"]
    output.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return summaries
