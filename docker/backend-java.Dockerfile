# Backend Java Dockerfile — Spring Boot 3.2 + Java 17 + Maven
FROM maven:3.9-eclipse-temurin-17 AS builder

WORKDIR /app

# Copy pom.xml first for dependency caching
COPY backend-java/pom.xml /app/pom.xml
RUN mvn dependency:go-offline -B

# Copy source and build
COPY backend-java/src /app/src
RUN mvn package -DskipTests -B

# Runtime stage
FROM eclipse-temurin:17-jre-jammy

RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq5 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy the built jar
COPY --from=builder /app/target/*.jar /app/app.jar

# Create uploads directory
RUN mkdir -p /app/uploads

ENV JAVA_OPTS="-Xmx512m -Xms256m"
ENV SPRING_PROFILES_ACTIVE=production

EXPOSE 8000

ENTRYPOINT ["sh", "-c", "java $JAVA_OPTS -jar /app/app.jar"]
