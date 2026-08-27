package com.infraguard.config;

import lombok.Data;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.context.annotation.Configuration;

import java.util.List;

/**
 * Centralized application properties loaded from application.yml.
 */
@Data
@Configuration
@ConfigurationProperties(prefix = "app")
public class AppProperties {

    private Cors cors = new Cors();
    private Jwt jwt = new Jwt();
    private Upload upload = new Upload();
    private Llm llm = new Llm();
    private Overpass overpass = new Overpass();
    private DefaultAdmin defaultAdmin = new DefaultAdmin();

    @Data
    public static class Cors {
        private List<String> allowedOrigins = List.of("http://localhost:5173");
    }

    @Data
    public static class Jwt {
        private String secret = "change_this_to_a_long_random_string_in_production_5f8a2b9c1e7d";
        private long accessTokenExpirationMinutes = 1440;
        private long refreshTokenExpirationDays = 7;
    }

    @Data
    public static class Upload {
        private String dir = "./uploads";
        private int maxSizeMb = 10;
        private List<String> allowedTypes = List.of("image/jpeg", "image/png", "image/webp");
    }

    @Data
    public static class Llm {
        private String apiKey = "";
        private String apiBaseUrl = "https://api.groq.com/openai/v1";
        private String visionModel = "meta-llama/llama-4-scout-17b-16e-instruct";
        private int requestTimeoutSeconds = 30;
    }

    @Data
    public static class Overpass {
        private boolean enabled = true;
        private int timeoutSeconds = 10;
        private List<String> endpoints = List.of(
            "https://overpass-api.de/api/interpreter"
        );
    }

    @Data
    public static class DefaultAdmin {
        private String email = "admin@infraguard.gov";
        private String password = "Admin@12345";
        private String name = "System Administrator";
    }
}
