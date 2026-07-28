package com.ssafy.woojuin.domain.item.service;

import jakarta.annotation.PostConstruct;
import java.io.IOException;
import java.time.Duration;
import java.util.Set;
import java.util.UUID;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;
import org.springframework.web.multipart.MultipartFile;
import software.amazon.awssdk.core.sync.RequestBody;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.BucketAlreadyExistsException;
import software.amazon.awssdk.services.s3.model.BucketAlreadyOwnedByYouException;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.services.s3.model.DeleteObjectRequest;
import software.amazon.awssdk.services.s3.model.GetObjectRequest;
import software.amazon.awssdk.services.s3.model.HeadBucketRequest;
import software.amazon.awssdk.services.s3.model.NoSuchBucketException;
import software.amazon.awssdk.services.s3.model.PutObjectRequest;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;
import software.amazon.awssdk.services.s3.presigner.model.GetObjectPresignRequest;

@Slf4j
@Component
public class S3Uploader {

    private static final Set<String> ALLOWED_CONTENT_TYPES =
            Set.of("image/png", "image/jpeg", "image/webp", "image/gif");

    /** presigned GET URL 유효시간. 조회 시점마다 새로 발급하므로 짧게 잡아도 무방하다. */
    private static final Duration PRESIGN_TTL = Duration.ofMinutes(60);

    private final S3Client s3Client;
    private final S3Presigner s3Presigner;
    private final String bucket;
    private final boolean localMode;

    public S3Uploader(S3Client s3Client, S3Presigner s3Presigner,
            @Value("${aws.s3.bucket}") String bucket,
            @Value("${aws.s3.endpoint:}") String endpoint) {
        this.s3Client = s3Client;
        this.s3Presigner = s3Presigner;
        this.bucket = bucket;
        this.localMode = endpoint != null && !endpoint.isBlank();
    }

    /**
     * 로컬(MinIO)은 버킷을 미리 만들어주지 않아 기동 시점에 직접 보장해야 한다.
     * 운영(AWS S3)에서는 버킷이 없다고 자동으로 만들면 안 된다 — AWS_S3_BUCKET 설정을
     * 깜빡했을 때 실제 계정에 의도치 않은 버킷이 생기는 사고로 이어질 수 있어서,
     * 대신 기동을 실패시켜 설정 실수를 바로 드러낸다. 버킷이 이미 있으면 두 경우 다
     * headBucket이 성공해 아무 일도 안 한다.
     */
    @PostConstruct
    void ensureBucketExists() {
        try {
            s3Client.headBucket(HeadBucketRequest.builder().bucket(bucket).build());
        } catch (NoSuchBucketException e) {
            if (localMode) {
                createBucketIfMissing();
            } else {
                throw new IllegalStateException(
                        "S3 버킷이 존재하지 않습니다: " + bucket
                                + " — 운영에서는 자동 생성하지 않으니 미리 만들어두세요", e);
            }
        }
    }

    /**
     * 인스턴스 여러 개가 동시에 기동하면 headBucket에서 둘 다 "없음"을 보고 동시에
     * 여기 들어올 수 있다. 늦게 도착한 쪽은 상대가 이미 만든 버킷 때문에
     * BucketAlreadyOwnedByYouException(같은 계정)이나 BucketAlreadyExistsException을
     * 받는데, 버킷은 어차피 존재하게 됐으니 기동 실패로 취급하지 않고 무시한다.
     */
    private void createBucketIfMissing() {
        try {
            s3Client.createBucket(CreateBucketRequest.builder().bucket(bucket).build());
            log.info("S3 버킷 생성: {}", bucket);
        } catch (BucketAlreadyOwnedByYouException | BucketAlreadyExistsException e) {
            log.debug("S3 버킷이 이미 존재함(동시 기동 레이스로 추정): {}", bucket);
        }
    }

    public String upload(MultipartFile file, Long workspaceId) {
        String contentType = file.getContentType();
        if (contentType == null || !ALLOWED_CONTENT_TYPES.contains(contentType)) {
            throw new IllegalArgumentException("지원하지 않는 이미지 형식입니다: " + contentType);
        }

        String key = "items/%d/%s-%s".formatted(workspaceId, UUID.randomUUID(), file.getOriginalFilename());

        try {
            s3Client.putObject(
                    PutObjectRequest.builder()
                            .bucket(bucket)
                            .key(key)
                            .contentType(contentType)
                            .build(),
                    RequestBody.fromInputStream(file.getInputStream(), file.getSize()));
        } catch (java.io.IOException e) {
            throw new IllegalStateException("이미지 업로드에 실패했습니다", e);
        }

        return key;
    }

    /**
     * IMAGE 목록 카드용 webp 썸네일을 올린다. 키는 원본 키에서 파생시켜(원본키 + ".thumb.webp")
     * 한 이미지의 원본/썸네일이 같은 접두어로 묶이게 한다. 원본과 달리 이미 메모리에 있는
     * 바이트라 InputStream이 아닌 fromBytes로 올린다.
     */
    public String uploadThumbnail(byte[] bytes, String originalKey) {
        String key = originalKey + ".thumb.webp";
        s3Client.putObject(
                PutObjectRequest.builder()
                        .bucket(bucket)
                        .key(key)
                        .contentType("image/webp")
                        .build(),
                RequestBody.fromBytes(bytes));
        return key;
    }

    /**
     * IMAGE 아이템 원본을 브라우저가 직접 읽을 수 있는 presigned GET URL을 만든다.
     * URL엔 만료 시각이 서명돼 있어 컬럼에 저장하면 안 되고(만료되면 죽은 링크), 조회
     * 응답을 만들 때마다 새로 발급해야 한다. presign은 순수 서명 연산이라 네트워크 호출이
     * 없어 목록에서 아이템마다 호출해도 부담이 없다.
     */
    public String presignGet(String key) {
        GetObjectPresignRequest request = GetObjectPresignRequest.builder()
                .signatureDuration(PRESIGN_TTL)
                .getObjectRequest(GetObjectRequest.builder().bucket(bucket).key(key).build())
                .build();
        return s3Presigner.presignGetObject(request).url().toString();
    }

    /** IMAGE 아이템 가공(OCR) 시 원본 바이트를 읽어온다. 실패는 호출부가 판단한다. */
    public byte[] download(String key) {
        try (var obj = s3Client.getObject(GetObjectRequest.builder().bucket(bucket).key(key).build())) {
            return obj.readAllBytes();
        } catch (IOException e) {
            throw new IllegalStateException("이미지 다운로드에 실패했습니다: key=" + key, e);
        }
    }

    /**
     * 영구 삭제 시 S3 원본을 지운다(ERD 설계 노트). 호출 시점엔 DB 삭제가 이미 커밋된
     * 뒤라 여기서 예외를 던져 봐야 되돌릴 것이 없고, 사용자에겐 삭제가 실패한 것처럼
     * 보이기만 한다. 그래서 실패해도 요청은 성공으로 두고 고아 객체를 로그로 남긴다.
     */
    public void deleteQuietly(String key) {
        try {
            s3Client.deleteObject(DeleteObjectRequest.builder().bucket(bucket).key(key).build());
        } catch (RuntimeException e) {
            log.warn("S3 원본 삭제 실패 — 고아 객체로 남음: key={}", key, e);
        }
    }
}
