package com.infraguard.dto.report;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class ReportListItem {
    private Long id;
    private String referenceCode;
    private String title;
    private Double latitude;
    private Double longitude;
    private String aiSeverity;
    private String finalSeverity;
    private String status;
    private String categoryName;
    private String districtName;
    private Integer verificationCount;
    private Double credibilityScore;
    private LocalDateTime createdAt;
    private Double priorityScore;
    private Integer priorityRank;
    private String imageUrl;
}
