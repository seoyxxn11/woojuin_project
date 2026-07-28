# 멀티스테이지 빌드.
#
# 이전에는 호스트에서 미리 만들어 둔 jar(build/libs/*.jar)를 복사만 했는데,
# 그러면 이미지를 만드는 쪽에 Java 21 + Gradle 이 깔려 있어야 한다.
# CI(Jenkins) 컨테이너에는 둘 다 없으므로, 빌드까지 이미지 안에서 끝내
# `docker build` 한 번으로 배포 가능한 이미지가 나오게 한다.
#
#   docker build -t woojuin-backend:<커밋SHA> -f backend/Dockerfile backend

# ---------- 1단계: 빌드 ----------
FROM gradle:8.8-jdk21 AS build
WORKDIR /src

# 의존성 레이어 캐싱: 빌드 스크립트만 먼저 넣고 의존성을 받아 두면
# 소스만 바뀐 재빌드에서 이 레이어를 그대로 재사용해 빌드가 빨라진다.
# (의존성 목록이 안 바뀌면 아래 RUN 은 캐시 히트)
COPY build.gradle settings.gradle ./
RUN gradle dependencies --no-daemon --quiet || true

COPY src ./src
RUN gradle bootJar --no-daemon

# ---------- 2단계: 실행 ----------
# JRE만 있는 alpine 이미지라 최종 이미지가 작다(빌드 도구는 1단계에 두고 온다).
FROM eclipse-temurin:21-jre-alpine
WORKDIR /app

# 루트 권한으로 돌리지 않는다. 컨테이너가 뚫려도 권한을 최소화하기 위함.
RUN addgroup -S app && adduser -S -G app app

COPY --from=build /src/build/libs/*.jar app.jar
RUN chown app:app app.jar
USER app

EXPOSE 8080

# 셸 형태로 실행해야 $JAVA_OPTS(-Xmx 등 compose 에서 주는 값)가 치환된다.
# exec 를 붙여 java 가 PID 1 이 되게 하는데, 그래야 `docker stop` 의 SIGTERM 을
# JVM 이 직접 받아 Spring 이 graceful shutdown 을 할 수 있다.
ENTRYPOINT ["sh", "-c", "exec java $JAVA_OPTS -jar /app/app.jar"]
