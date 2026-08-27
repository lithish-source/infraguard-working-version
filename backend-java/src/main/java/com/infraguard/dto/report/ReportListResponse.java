package com.infraguard.dto.report;

import lombok.Builder;
import lombok.Data;

import java.util.List;

@Data
@Builder
public class ReportListResponse {
    private List<ReportListItem> items;
    private long total;
    private int page;
    private int pageSize;
}
