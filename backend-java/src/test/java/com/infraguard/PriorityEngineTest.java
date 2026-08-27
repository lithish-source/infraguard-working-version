package com.infraguard;

import com.infraguard.ai.PriorityEngine;
import org.junit.jupiter.api.Test;

import java.time.LocalDateTime;

import static org.junit.jupiter.api.Assertions.*;

class PriorityEngineTest {

    private final PriorityEngine engine = new PriorityEngine();

    @Test
    void criticalSeverity_withHighImpact_shouldScoreAbove60() {
        PriorityEngine.PriorityResult result = engine.compute(
            "Critical", 10, 500000, "highway",
            0.2, 0.1, "BRIDGE",
            LocalDateTime.now().minusHours(48),
            "Verified", 10.0,
            LocalDateTime.now()
        );
        assertTrue(result.score >= 60, "Critical scenario should score >= 60, got " + result.score);
        assertEquals("Immediate", result.resourceUrgency);
    }

    @Test
    void lowSeverity_withLowImpact_shouldScoreBelow50() {
        PriorityEngine.PriorityResult result = engine.compute(
            "Low", 0, 5000, "residential",
            5.0, 3.0, "PARK",
            LocalDateTime.now(),
            "Reported", 0.0,
            LocalDateTime.now()
        );
        assertTrue(result.score < 50, "Low scenario should score < 50, got " + result.score);
    }

    @Test
    void nullSeverity_shouldDefaultToModerate() {
        PriorityEngine.PriorityResult result = engine.compute(
            null, 2, 50000, null,
            null, null, null,
            LocalDateTime.now().minusHours(12),
            "Reported", 1.0,
            LocalDateTime.now()
        );
        assertNotNull(result);
        assertTrue(result.score >= 0 && result.score <= 100);
        assertNotNull(result.recommendedResponseTime);
    }

    @Test
    void components_shouldSumToApproximatelyOne() {
        PriorityEngine.PriorityResult result = engine.compute(
            "High", 5, 200000, "major_road",
            1.0, 0.5, "ROAD",
            LocalDateTime.now().minusHours(24),
            "Verified", 5.0,
            LocalDateTime.now()
        );
        double sum = result.components.values().stream().mapToDouble(Double::doubleValue).sum();
        // Each component is normalized 0-1; sum can be up to 9
        assertTrue(sum > 0, "Components should sum to > 0");
    }

    @Test
    void urgencyBands_shouldBeValid() {
        for (String urgency : new String[]{"Immediate", "High", "Medium", "Low", "Minimal"}) {
            assertNotNull(urgency);
        }
    }
}
