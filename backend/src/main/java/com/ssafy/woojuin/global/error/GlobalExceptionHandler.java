package com.ssafy.woojuin.global.error;

import com.ssafy.woojuin.domain.category.exception.CategoryNotFoundException;
import com.ssafy.woojuin.domain.item.exception.ItemNotFoundException;
import com.ssafy.woojuin.domain.item.exception.WorkspaceAccessDeniedException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceInvitationExpiredException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceInvitationNotAllowedException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceInvitationNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceLastOwnerException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceMemberRequiredException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceNotFoundException;
import com.ssafy.woojuin.domain.workspace.exception.WorkspaceOwnerRequiredException;
import com.ssafy.woojuin.global.common.ApiResponse;
import java.util.stream.Collectors;
import org.springframework.http.HttpHeaders;
import org.springframework.http.HttpStatus;
import org.springframework.http.HttpStatusCode;
import org.springframework.http.ResponseEntity;
import org.springframework.security.access.AccessDeniedException;
import org.springframework.web.bind.MethodArgumentNotValidException;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.bind.annotation.ResponseStatus;
import org.springframework.web.bind.annotation.RestControllerAdvice;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.multipart.MaxUploadSizeExceededException;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

/**
 * ResponseEntityExceptionHandler를 상속해서 Spring MVC가 자체적으로 처리하던 예외
 * (헤더·파라미터 누락, 바디 파싱 실패, 허용되지 않은 메서드 등)까지 모두 공통 응답
 * 형식 { status, message, data }으로 내보낸다 (docs/CONVENTIONS.md).
 */
@RestControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {

    @ExceptionHandler(IllegalArgumentException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ApiResponse<Void> handleBadRequest(IllegalArgumentException e) {
        return ApiResponse.of(400, e.getMessage(), null);
    }

    @ExceptionHandler(ItemNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ApiResponse<Void> handleItemNotFound(ItemNotFoundException e) {
        return ApiResponse.of(404, e.getMessage(), null);
    }

    @ExceptionHandler(CategoryNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ApiResponse<Void> handleCategoryNotFound(CategoryNotFoundException e) {
        return ApiResponse.of(404, e.getMessage(), null);
    }

    /** 로그인은 했지만 해당 워크스페이스 멤버가 아닌 경우. 인증 자체가 없는 AccessDeniedException(401)과는 구분한다. */
    @ExceptionHandler(WorkspaceAccessDeniedException.class)
    @ResponseStatus(HttpStatus.FORBIDDEN)
    public ApiResponse<Void> handleWorkspaceAccessDenied(WorkspaceAccessDeniedException e) {
        return ApiResponse.of(403, e.getMessage(), null);
    }

    @ExceptionHandler(WorkspaceNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ApiResponse<Void> handleWorkspaceNotFound(WorkspaceNotFoundException e) {
        return ApiResponse.of(404, e.getMessage(), null);
    }

    @ExceptionHandler(WorkspaceMemberRequiredException.class)
    @ResponseStatus(HttpStatus.FORBIDDEN)
    public ApiResponse<Void> handleWorkspaceMemberRequired(WorkspaceMemberRequiredException e) {
        return ApiResponse.of(403, e.getMessage(), null);
    }

    @ExceptionHandler(WorkspaceOwnerRequiredException.class)
    @ResponseStatus(HttpStatus.FORBIDDEN)
    public ApiResponse<Void> handleWorkspaceOwnerRequired(WorkspaceOwnerRequiredException e) {
        return ApiResponse.of(403, e.getMessage(), null);
    }

    @ExceptionHandler(WorkspaceInvitationNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ApiResponse<Void> handleWorkspaceInvitationNotFound(WorkspaceInvitationNotFoundException e) {
        return ApiResponse.of(404, e.getMessage(), null);
    }

    @ExceptionHandler(WorkspaceInvitationExpiredException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ApiResponse<Void> handleWorkspaceInvitationExpired(WorkspaceInvitationExpiredException e) {
        return ApiResponse.of(400, e.getMessage(), null);
    }

    @ExceptionHandler(WorkspaceInvitationNotAllowedException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ApiResponse<Void> handleWorkspaceInvitationNotAllowed(WorkspaceInvitationNotAllowedException e) {
        return ApiResponse.of(400, e.getMessage(), null);
    }

    @ExceptionHandler(WorkspaceMemberNotFoundException.class)
    @ResponseStatus(HttpStatus.NOT_FOUND)
    public ApiResponse<Void> handleWorkspaceMemberNotFound(WorkspaceMemberNotFoundException e) {
        return ApiResponse.of(404, e.getMessage(), null);
    }

    @ExceptionHandler(WorkspaceLastOwnerException.class)
    @ResponseStatus(HttpStatus.BAD_REQUEST)
    public ApiResponse<Void> handleWorkspaceLastOwner(WorkspaceLastOwnerException e) {
        return ApiResponse.of(400, e.getMessage(), null);
    }

    /**
     * CurrentUserResolver가 인증되지 않은 요청에서 던진다. 정상 운영 중엔 Spring
     * Security의 ExceptionTranslationFilter가 먼저 잡아 RestAuthenticationEntryPoint(401)로
     * 보내지만, @WebMvcTest처럼 시큐리티 필터 체인이 없는 슬라이스 테스트에서는 여기까지
     * 그대로 전파되므로 동일한 401 응답 형식을 보장하기 위해 둔다.
     */
    @ExceptionHandler(AccessDeniedException.class)
    @ResponseStatus(HttpStatus.UNAUTHORIZED)
    public ApiResponse<Void> handleAccessDenied(AccessDeniedException e) {
        return ApiResponse.of(401, "인증이 필요합니다", null);
    }

    /**
     * 이미지 용량 초과 (API 명세서 ITEM_413). MaxUploadSizeExceededException은 부모가
     * 이미 처리 대상으로 잡고 있어서, 별도 @ExceptionHandler를 만들면 매핑이 충돌해
     * 앱이 기동조차 못 한다 — 반드시 이 override 지점을 써야 한다.
     */
    @Override
    protected ResponseEntity<Object> handleMaxUploadSizeExceededException(MaxUploadSizeExceededException ex,
            HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        return handleExceptionInternal(ex, ApiResponse.of(413, "ITEM_413: 이미지 파일 용량 초과", null),
                headers, HttpStatus.PAYLOAD_TOO_LARGE, request);
    }

    /**
     * @Valid 검증 실패. 어떤 필드가 왜 틀렸는지 함께 내려줘서 클라이언트가 바로 고칠 수 있게 한다.
     */
    @Override
    protected ResponseEntity<Object> handleMethodArgumentNotValid(MethodArgumentNotValidException ex,
            HttpHeaders headers, HttpStatusCode status, WebRequest request) {
        String message = ex.getBindingResult().getFieldErrors().stream()
                .map(error -> error.getField() + ": " + error.getDefaultMessage())
                .collect(Collectors.joining(", "));
        return handleExceptionInternal(ex, ApiResponse.of(400, "COMMON_400: " + message, null),
                headers, HttpStatus.BAD_REQUEST, request);
    }

    /**
     * Spring MVC 내부 예외의 최종 응답 지점. body가 아직 공통 형식이 아니면 여기서 감싼다.
     */
    @Override
    protected ResponseEntity<Object> handleExceptionInternal(Exception ex, Object body,
            HttpHeaders headers, HttpStatusCode statusCode, WebRequest request) {
        Object wrapped = (body instanceof ApiResponse<?>)
                ? body
                : ApiResponse.of(statusCode.value(), ex.getMessage(), null);
        return super.handleExceptionInternal(ex, wrapped, headers, statusCode, request);
    }

    // TODO: 에러 코드 정의(노션 API 명세서)에 맞춰 커스텀 예외 체계 추가
}
