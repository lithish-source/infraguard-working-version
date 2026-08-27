package com.infraguard.ai;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * Severity Prioritization Engine — 9-factor weighted scoring.
 *
 * Combines multiple signals into a single priority score (0-100),
 * a rank, a resource urgency label, and a recommended response time.
 *
 * Ported directly from the Python implementation for consistency.
 */
public class PriorityEngine {

    // Weight per component (sums to ~1.0)
    public static final Map<String, Double> WEIGHTS = new HashMap<>();
    static {
        WEIGHTS.put("severity", 0.28);
        WEIGHTS.put("verification", 0.12);
        WEIGHTS.put("population", 0.10);
        WEIGHTS.put("road_importance", 0.10);
        WEIGHTS.put("hospital_proximity", 0.10);
        WEIGHTS.put("school_proximity", 0.07);
        WEIGHTS.put("utility_importance", 0.08);
        WEIGHTS.put("time_urgency", 0.08);
        WEIGHTS.put("verification_status", 0.07);
    }

    private static final Map<String, Double> SEVERITY_WEIGHTS = new HashMap<>();
    static {
        SEVERITY_WEIGHTS.put("Low", 1.0);
        SEVERITY_WEIGHTS.put("Moderate", 2.5);
        SEVERITY_WEIGHTS.put("High", 4.0);
        SEVERITY_WEIGHTS.put("Critical", 5.0);
    }

    public PriorityResult compute(
        String severity,
        int verificationCount,
        Integer population,
        String roadClass,
        Double hospitalDistanceKm,
        Double schoolDistanceKm,
        String infrastructureCode,
        LocalDateTime createdAt,
        String status,
        double credibilityScore,
        LocalDateTime now
    ) {
        if (now == null) now = LocalDateTime.now();
        if (createdAt == null) createdAt = now;

        double sevScore = severityToScore(severity);
        double verScore = normalize(verificationCount, 1.0, 15.0);
        double popScore = populationScore(population);
        double roadScore = roadImportanceScore(roadClass);
        double hospScore = hospitalProximityScore(hospitalDistanceKm);
        double schoolScore = schoolProximityScore(schoolDistanceKm);
        double utilScore = utilityImportanceScore(infrastructureCode);
        double timeScore = timeUrgency(createdAt, now);
        double statusScore = verificationStatusScore(status);

        double credibilityFactor = 0.9 + Math.min(0.2, credibilityScore / 10.0);

        Map<String, Double> components = new HashMap<>();
        components.put("severity_component", sevScore);
        components.put("verification_component", verScore);
        components.put("population_component", popScore);
        components.put("road_importance_component", roadScore);
        components.put("hospital_proximity_component", hospScore);
        components.put("school_proximity_component", schoolScore);
        components.put("utility_importance_component", utilScore);
        components.put("time_urgency_component", timeScore);
        components.put("verification_status_component", statusScore);

        double raw = sevScore * WEIGHTS.get("severity")
                   + verScore * WEIGHTS.get("verification")
                   + popScore * WEIGHTS.get("population")
                   + roadScore * WEIGHTS.get("road_importance")
                   + hospScore * WEIGHTS.get("hospital_proximity")
                   + schoolScore * WEIGHTS.get("school_proximity")
                   + utilScore * WEIGHTS.get("utility_importance")
                   + timeScore * WEIGHTS.get("time_urgency")
                   + statusScore * WEIGHTS.get("verification_status");

        double score0to1 = Math.min(1.0, raw * credibilityFactor);
        double score = Math.round(score0to1 * 100.0 * 100.0) / 100.0;  // 2 decimal places

        String urgency;
        String response;
        if (score >= 80) { urgency = "Immediate"; response = "Within 2 hours"; }
        else if (score >= 60) { urgency = "High"; response = "Within 6 hours"; }
        else if (score >= 40) { urgency = "Medium"; response = "Within 24 hours"; }
        else if (score >= 20) { urgency = "Low"; response = "Within 72 hours"; }
        else { urgency = "Minimal"; response = "Within 7 days"; }

        return new PriorityResult(score, null, components, response, urgency, severity);
    }

    private double severityToScore(String severity) {
        if (severity == null) return 0.5;
        Double w = SEVERITY_WEIGHTS.get(severity);
        return w == null ? 0.5 : w / 5.0;
    }

    private double normalize(double value, double low, double high) {
        if (high <= low) return 0.0;
        return Math.max(0.0, Math.min(1.0, (value - low) / (high - low)));
    }

    private double timeUrgency(LocalDateTime createdAt, LocalDateTime now) {
        long hours = Math.max(0L, Duration.between(createdAt, now).toHours());
        return normalize(hours, 6.0, 72.0);
    }

    private double hospitalProximityScore(Double distanceKm) {
        if (distanceKm == null) return 0.5;
        return Math.max(0.0, 1.0 - (distanceKm / 5.0));
    }

    private double schoolProximityScore(Double distanceKm) {
        if (distanceKm == null) return 0.4;
        return Math.max(0.0, 1.0 - (distanceKm / 3.0));
    }

    private double roadImportanceScore(String roadClass) {
        if (roadClass == null) return 0.5;
        return switch (roadClass.toLowerCase()) {
            case "highway" -> 1.0;
            case "major_road" -> 0.85;
            case "arterial" -> 0.7;
            case "collector" -> 0.55;
            case "local" -> 0.35;
            case "residential" -> 0.25;
            default -> 0.5;
        };
    }

    private double populationScore(Integer population) {
        if (population == null || population == 0) return 0.4;
        return normalize(population.doubleValue(), 5000.0, 500_000.0);
    }

    private double utilityImportanceScore(String infraCode) {
        if (infraCode == null) return 0.5;
        String code = infraCode.toUpperCase();
        if (code.matches("WATER|POWER|BRIDGE|TRAFFIC|HOSPITAL")) return 1.0;
        if (code.matches("ROAD|DRAINAGE|STREETLIGHT")) return 0.7;
        return 0.5;
    }

    private double verificationStatusScore(String status) {
        if ("Verified".equals(status)) return 1.0;
        if ("Reported".equals(status)) return 0.6;
        return 0.3;
    }

    public static class PriorityResult {
        public final double score;
        public Integer rank;
        public final Map<String, Double> components;
        public final String recommendedResponseTime;
        public final String resourceUrgency;
        public final String severityInput;

        public PriorityResult(double score, Integer rank, Map<String, Double> components,
                              String recommendedResponseTime, String resourceUrgency, String severityInput) {
            this.score = score;
            this.rank = rank;
            this.components = components;
            this.recommendedResponseTime = recommendedResponseTime;
            this.resourceUrgency = resourceUrgency;
            this.severityInput = severityInput;
        }
    }
}
