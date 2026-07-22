import argparse
from pathlib import Path
from src.report_generator import generate_final_report

p=argparse.ArgumentParser(); p.add_argument('--result-dir',required=True); a=p.parse_args(); path=Path(a.result_dir).resolve()
if not path.is_dir(): raise SystemExit(f"결과 디렉터리가 없습니다: {path}")
complete=generate_final_report(path); print(f"{'최종 보고서 생성 완료' if complete else '수동 평가 미완료'}: {path}")
