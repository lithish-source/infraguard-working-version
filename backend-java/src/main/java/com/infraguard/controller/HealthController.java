package com.infraguard.controller;

import com.infraguard.ai.LlmService;
import com.infraguard.config.AppProperties;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.Map;

@RestController
@RequiredArgsConstructor
public class HealthController {

    private final LlmService llmService;
    private final AppProperties appProperties;

    @GetMapping("/health")
    public Map<String, Object> health() {
        return Map.of(
            "status", "healthy",
            "ai_ready", llmService.isEnabled(),
            "llm", llmService.getStatus(),
            "geospatial", Map.of("overpass_enabled", appProperties.getOverpass().isEnabled()),
            "version", "1.0.0",
            "language", "Java 17 + Spring Boot 3.2"
        );
    }

    @GetMapping("/")
    public Map<String, Object> root() {
        return Map.of(
            "app", "InfraGuard",
            "version", "1.0.0",
            "status", "ok",
            "language", "Java 17 + Spring Boot 3.2"
        );
    }
}
