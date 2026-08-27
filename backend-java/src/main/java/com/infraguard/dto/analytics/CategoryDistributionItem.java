package com.infraguard.dto.analytics;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class CategoryDistributionItem {
    private String category;
    private long count;
    private long criticalCount;
}
