package com.infraguard.dto.report;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class VerificationResponse {
    private Long id;
    private Long reportId;
    private Long userId;
    private String severityVote;
    private String comment;
    private Boolean isConfirmed;
    private LocalDateTime createdAt;
}
