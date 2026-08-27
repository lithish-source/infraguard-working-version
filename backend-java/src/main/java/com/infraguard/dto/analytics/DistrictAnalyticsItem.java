package com.infraguard.dto.analytics;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class DistrictAnalyticsItem {
    private String district;
    private long reports;
    private long critical;
    private long resolved;
    private double avgPriority;
}
