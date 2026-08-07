package com.ssafy.woojuin.domain.auth.dto;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.Size;

public record DeviceLinkPollRequest(
        @NotBlank(message = "코드는 필수입니다") String code,
        /*
         * 기기 목록에 표기될 클라이언트 표식(선택) — 예: "Woojuin-Extension/1.0".
         *
         * User-Agent 로 못 하는 이유: 크롬이 fetch 의 UA 재정의를 조용히 무시한다
         * (2026-08-07 실측 — 헤더에 실어도 세션에는 브라우저 UA 가 찍혔다). 브라우저 안에서
         * 도는 클라이언트(익스텐션)는 자기가 누구인지 본문으로 밝히는 수밖에 없다.
         * 워치처럼 UA 를 직접 정할 수 있는 기기는 이 필드가 필요 없다.
         */
        @Size(max = 64, message = "클라이언트 표식은 64자 이하입니다") String client) {
}
