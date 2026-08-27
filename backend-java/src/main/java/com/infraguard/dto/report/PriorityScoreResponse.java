package com.infraguard.dto.report;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class PriorityScoreResponse {
    private Double score;
    private Integer rank;
    private Double severityComponent;
    private Double verificationComponent;
    private Double populationComponent;
    private Double roadImportanceComponent;
    private Double hospitalProximityComponent;
    private Double schoolProximityComponent;
    private Double utilityImportanceComponent;
    private Double timeUrgencyComponent;
    private Double verificationStatusComponent;
    private String recommendedResponseTime;
    private String resourceUrgency;
    private LocalDateTime createdAt;
}
