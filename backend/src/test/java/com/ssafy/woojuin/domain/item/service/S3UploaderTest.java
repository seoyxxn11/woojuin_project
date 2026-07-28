package com.ssafy.woojuin.domain.item.service;

import static org.assertj.core.api.Assertions.assertThatCode;
import static org.assertj.core.api.Assertions.assertThatThrownBy;
import static org.mockito.ArgumentMatchers.any;
import static org.mockito.Mockito.never;
import static org.mockito.Mockito.verify;
import static org.mockito.Mockito.when;

import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.extension.ExtendWith;
import org.mockito.Mock;
import org.mockito.junit.jupiter.MockitoExtension;
import software.amazon.awssdk.services.s3.S3Client;
import software.amazon.awssdk.services.s3.model.BucketAlreadyOwnedByYouException;
import software.amazon.awssdk.services.s3.model.CreateBucketRequest;
import software.amazon.awssdk.services.s3.model.HeadBucketRequest;
import software.amazon.awssdk.services.s3.model.NoSuchBucketException;
import software.amazon.awssdk.services.s3.presigner.S3Presigner;

/**
 * ensureBucketExists()의 로컬(MinIO)/운영(AWS S3) 분기와 동시 기동 레이스 흡수를 검증한다.
 */
@ExtendWith(MockitoExtension.class)
class S3UploaderTest {

    @Mock S3Client s3Client;
    @Mock S3Presigner s3Presigner;

    @Test
    void 버킷이_이미_있으면_로컬이든_운영이든_아무것도_안한다() {
        S3Uploader uploader = new S3Uploader(s3Client, s3Presigner, "woojuin-items", "http://localhost:9000");

        uploader.ensureBucketExists();

        verify(s3Client, never()).createBucket(any(CreateBucketRequest.class));
    }

    @Test
    void 로컬모드에서_버킷이_없으면_생성한다() {
        when(s3Client.headBucket(any(HeadBucketRequest.class)))
                .thenThrow(NoSuchBucketException.builder().build());
        S3Uploader uploader = new S3Uploader(s3Client, s3Presigner, "woojuin-items", "http://localhost:9000");

        uploader.ensureBucketExists();

        verify(s3Client).createBucket(any(CreateBucketRequest.class));
    }

    @Test
    void 로컬모드에서_동시기동으로_이미_생성됐으면_무시한다() {
        when(s3Client.headBucket(any(HeadBucketRequest.class)))
                .thenThrow(NoSuchBucketException.builder().build());
        when(s3Client.createBucket(any(CreateBucketRequest.class)))
                .thenThrow(BucketAlreadyOwnedByYouException.builder().build());
        S3Uploader uploader = new S3Uploader(s3Client, s3Presigner, "woojuin-items", "http://localhost:9000");

        assertThatCode(uploader::ensureBucketExists).doesNotThrowAnyException();
    }

    @Test
    void 운영모드에서_버킷이_없으면_자동생성하지_않고_예외를_던진다() {
        when(s3Client.headBucket(any(HeadBucketRequest.class)))
                .thenThrow(NoSuchBucketException.builder().build());
        S3Uploader uploader = new S3Uploader(s3Client, s3Presigner, "woojuin-items", "");

        assertThatThrownBy(uploader::ensureBucketExists)
                .isInstanceOf(IllegalStateException.class);

        verify(s3Client, never()).createBucket(any(CreateBucketRequest.class));
    }
}
