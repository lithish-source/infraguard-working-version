package com.infraguard.controller;

import com.infraguard.dto.admin.AdminDtos;
import com.infraguard.dto.analytics.*;
import com.infraguard.dto.report.ReportResponse;
import com.infraguard.entity.User;
import com.infraguard.security.CustomUserDetailsService;
import com.infraguard.service.AnalyticsService;
import com.infraguard.service.PriorityService;
import com.infraguard.service.ReportService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/admin")
@RequiredArgsConstructor
public class AdminController {

    private final AnalyticsService analyticsService;
    private final ReportService reportService;
    private final PriorityService priorityService;
    private final CustomUserDetailsService userDetailsService;

    @GetMapping("/dashboard/summary")
    public DashboardSummary dashboardSummary() {
        return analyticsService.dashboardSummary();
    }

    @GetMapping("/analytics/severity")
    public List<SeverityDistributionItem> severityDist() {
        return analyticsService.severityDistribution();
    }

    @GetMapping("/analytics/category")
    public List<CategoryDistributionItem> categoryDist() {
        return analyticsService.categoryDistribution();
    }

    @GetMapping("/analytics/monthly")
    public List<MonthlyTrendItem> monthlyTrend(@RequestParam(defaultValue = "6") int months) {
        return analyticsService.monthlyTrend(months);
    }

    @GetMapping("/analytics/districts")
    public List<DistrictAnalyticsItem> districtAnalytics() {
        return analyticsService.districtAnalytics();
    }

    @GetMapping("/analytics/response-time")
    public Map<String, Object> responseTime() {
        return analyticsService.responseTime();
    }

    @GetMapping("/analytics/repeat-incidents")
    public Map<String, Object> repeatIncidents() {
        return analyticsService.repeatIncidents(0.5);
    }

    @GetMapping("/analytics/participation")
    public Map<String, Object> participation() {
        return analyticsService.citizenParticipation();
    }

    @PostMapping("/reports/{id}/status")
    public ReportResponse updateStatus(
        @PathVariable Long id,
        @RequestBody AdminDtos.StatusUpdateRequest req,
        @AuthenticationPrincipal UserDetails principal
    ) {
        User admin = userDetailsService.loadUserEntityByEmail(principal.getUsername());
        return reportService.updateStatus(id, admin.getId(), req);
    }

    @PostMapping("/reports/{id}/severity")
    public ReportResponse updateSeverity(
        @PathVariable Long id,
        @RequestBody AdminDtos.SeverityUpdateRequest req,
        @AuthenticationPrincipal UserDetails principal
    ) {
        User admin = userDetailsService.loadUserEntityByEmail(principal.getUsername());
        return reportService.updateSeverity(id, admin.getId(), req);
    }

    @PostMapping("/reports/{id}/assign")
    public ReportResponse assignTeam(
        @PathVariable Long id,
        @RequestBody AdminDtos.AssignTeamRequest req,
        @AuthenticationPrincipal UserDetails principal
    ) {
        User admin = userDetailsService.loadUserEntityByEmail(principal.getUsername());
        return reportService.assignTeam(id, admin.getId(), req);
    }

    @PostMapping("/priority/recompute")
    public Map<String, Object> recomputePriorities() {
        int count = priorityService.recomputeAllOpen();
        return Map.of("message", "Recomputed priorities for " + count + " open reports.", "count", count);
    }
}
