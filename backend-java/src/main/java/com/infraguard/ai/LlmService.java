package com.infraguard.ai;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.fasterxml.jackson.databind.node.ObjectNode;
import com.infraguard.config.AppProperties;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.Base64;
import java.util.HashMap;
import java.util.Map;

/**
 * LLM Vision Service — optional integration with an OpenAI-compatible LLM API
 * (Groq/Llama 4 Scout by default).
 *
 * If LLM_API_KEY is empty, returns null and the system falls back to the
 * rule-based severity classifier.
 */
@Slf4j
@Service
public class LlmService {

    private final AppProperties props;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final HttpClient httpClient;

    @Autowired
    public LlmService(AppProperties props) {
        this.props = props;
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(10))
            .build();
    }

    public boolean isEnabled() {
        return props.getLlm().getApiKey() != null && !props.getLlm().getApiKey().isBlank();
    }

    public LlmAnalysisResult analyzeImage(String imagePath) {
        if (!isEnabled()) return null;

        try {
            byte[] imageBytes = java.nio.file.Files.readAllBytes(java.nio.file.Paths.get(imagePath));
            String base64 = Base64.getEncoder().encodeToString(imageBytes);
            String mimeType = guessMimeType(imagePath);
            String dataUrl = "data:" + mimeType + ";base64," + base64;

            String prompt = """
                You are an infrastructure damage assessor. Analyze the photo and return STRICT JSON only.

                Output format (no markdown, no explanation, just JSON):
                {
                  "severity": "Low" | "Moderate" | "High" | "Critical",
                  "damage_type": "<one of: Surface Crack, Pothole, Structural Damage, Corrosion, Water Logging, Broken Component, Erosion, Vegetation Overgrowth, Subsidence, Faulty Wiring>",
                  "confidence": <float between 0.0 and 1.0>,
                  "description": "<one-sentence description of the visible damage>",
                  "reasoning": "<one-sentence justification for the severity level>"
                }

                Severity guidelines:
                - Low: Minor cosmetic damage, no safety risk
                - Moderate: Functional impairment, moderate safety risk
                - High: Significant damage, high safety risk
                - Critical: Severe damage, immediate safety hazard

                Return ONLY the JSON object.""";

            // Build request JSON using Jackson tree model
            ObjectNode content = objectMapper.createObjectNode();
            content.put("model", props.getLlm().getVisionModel());
            content.put("temperature", 0.2);
            content.put("max_tokens", 400);
            content.putObject("response_format").put("type", "json_object");

            var messagesArray = content.putArray("messages");
            var message = messagesArray.addObject();
            message.put("role", "user");
            var contentArray = message.putArray("content");

            var textPart = contentArray.addObject();
            textPart.put("type", "text");
            textPart.put("text", prompt);

            var imagePart = contentArray.addObject();
            imagePart.put("type", "image_url");
            imagePart.putObject("image_url").put("url", dataUrl);

            String requestBody = objectMapper.writeValueAsString(content);

            HttpRequest request = HttpRequest.newBuilder()
                .uri(URI.create(props.getLlm().getApiBaseUrl().replaceAll("/$", "") + "/chat/completions"))
                .header("Authorization", "Bearer " + props.getLlm().getApiKey())
                .header("Content-Type", "application/json")
                .timeout(Duration.ofSeconds(props.getLlm().getRequestTimeoutSeconds()))
                .POST(HttpRequest.BodyPublishers.ofString(requestBody))
                .build();

            HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

            if (response.statusCode() != 200) {
                log.warn("[llm] API returned {}: {}", response.statusCode(),
                    response.body().substring(0, Math.min(300, response.body().length())));
                return null;
            }

            JsonNode root = objectMapper.readTree(response.body());
            String contentStr = root.path("choices").get(0).path("message").path("content").asText();

            // Strip ```json wrappers if present
            contentStr = contentStr.trim();
            if (contentStr.startsWith("```")) {
                contentStr = contentStr.replaceAll("^```[a-zA-Z]*\\n?", "").replaceAll("```$", "").trim();
            }

            JsonNode parsed = objectMapper.readTree(contentStr);

            String severity = parsed.path("severity").asText("").trim();
            severity = Character.toUpperCase(severity.charAt(0)) + severity.substring(1).toLowerCase();
            if (!severity.equals("Low") && !severity.equals("Moderate")
                && !severity.equals("High") && !severity.equals("Critical")) {
                log.warn("[llm] Invalid severity from LLM: {}", severity);
                return null;
            }

            double confidence = parsed.path("confidence").asDouble(0.7);
            confidence = Math.max(0.0, Math.min(1.0, confidence));

            return new LlmAnalysisResult(
                severity,
                parsed.path("damage_type").asText("Unknown"),
                confidence,
                parsed.path("description").asText(""),
                parsed.path("reasoning").asText(""),
                props.getLlm().getVisionModel()
            );

        } catch (Exception e) {
            log.warn("[llm] Inference failed: {}", e.getMessage());
            return null;
        }
    }

    private String guessMimeType(String path) {
        String lower = path.toLowerCase();
        if (lower.endsWith(".png")) return "image/png";
        if (lower.endsWith(".webp")) return "image/webp";
        return "image/jpeg";
    }

    public Map<String, Object> getStatus() {
        Map<String, Object> map = new HashMap<>();
        map.put("enabled", isEnabled());
        map.put("api_base_url", props.getLlm().getApiBaseUrl());
        map.put("vision_model", props.getLlm().getVisionModel());
        return map;
    }

    public record LlmAnalysisResult(
        String severity,
        String damageType,
        double confidence,
        String description,
        String reasoning,
        String model
    ) {}
}
