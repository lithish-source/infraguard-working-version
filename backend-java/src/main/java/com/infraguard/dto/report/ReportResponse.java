package com.infraguard.dto.report;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;
import java.util.List;

@Data
@Builder
public class ReportResponse {
    private Long id;
    private String referenceCode;
    private String title;
    private String description;
    private String address;
    private Double latitude;
    private Double longitude;
    private Long categoryId;
    private String categoryName;
    private Long districtId;
    private String districtName;
    private String aiSeverity;
    private Double aiConfidence;
    private String aiDamageType;
    private String finalSeverity;
    private String status;
    private Double credibilityScore;
    private Integer verificationCount;
    private Integer upvoteCount;
    private Integer downvoteCount;
    private String assignedTeam;
    private String resolutionNotes;
    private LocalDateTime resolvedAt;
    private LocalDateTime createdAt;
    private LocalDateTime updatedAt;
    private Long userId;
    private String userName;
    private List<ImageResponse> images;
    private PriorityScoreResponse priority;
    private List<VerificationResponse> verifications;
}
