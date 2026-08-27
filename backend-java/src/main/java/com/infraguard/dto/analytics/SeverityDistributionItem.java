package com.infraguard.dto.analytics;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class SeverityDistributionItem {
    private String severity;
    private long count;
    private double percentage;
}
