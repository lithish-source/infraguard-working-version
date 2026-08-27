package com.infraguard.dto.analytics;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class DashboardSummary {
    private long totalReports;
    private long pendingReports;
    private long verifiedReports;
    private long resolvedReports;
    private long criticalIncidents;
    private long totalUsers;
    private long totalVerifications;
    private Double avgResponseTimeHours;
    private double responseRate;
}
