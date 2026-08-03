# GOLD 검토 입력

로컬 AI 실험이 생성한 검토용 JSON 또는 JSONL을 워크스페이스와 실행별
폴더에 저장합니다.

```text
review-inputs/
└── WS-001/
    └── 20260803-auto-category/
        ├── existing-11-plus-ai/
        │   └── review-draft.json
        ├── ai-only/
        │   └── review-draft.json
        └── existing-5-plus-ai/
            └── review-draft.json
```

검토 GUI는 상위 실행 폴더와 JSON이 들어 있는 실험 조건 폴더를 각각 선택
목록으로 보여줍니다. 검토 데이터 파일 이름은 `review-draft.json` 또는
`review-draft.jsonl`을 권장합니다.
