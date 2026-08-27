package com.infraguard.dto.analytics;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class MonthlyTrendItem {
    private String month;
    private long reports;
    private long resolved;
}
