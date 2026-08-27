package com.infraguard.service;

import com.infraguard.dto.analytics.*;
import com.infraguard.entity.*;
import com.infraguard.repository.*;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class AnalyticsService {

    private final ReportRepository reportRepository;
    private final UserRepository userRepository;
    private final VerificationRepository verificationRepository;
    private final InfrastructureTypeRepository infraTypeRepository;
    private final DistrictRepository districtRepository;
    private final PriorityScoreRepository priorityScoreRepository;

    @Transactional(readOnly = true)
    public DashboardSummary dashboardSummary() {
        long total = reportRepository.count();
        long pending = reportRepository.countByStatus("Reported");
        long verified = reportRepository.countByStatus("Verified");
        long resolved = reportRepository.countByStatus("Resolved");
        long critical = reportRepository.countCritical();
        long users = userRepository.count();
        long verifications = verificationRepository.count();
        Double avgResp = reportRepository.avgResponseTimeHours();
        double responseRate = total > 0 ? (resolved * 100.0 / total) : 0.0;

        return DashboardSummary.builder()
            .totalReports(total)
            .pendingReports(pending)
            .verifiedReports(verified)
            .resolvedReports(resolved)
            .criticalIncidents(critical)
            .totalUsers(users)
            .totalVerifications(verifications)
            .avgResponseTimeHours(avgResp != null ? Math.round(avgResp * 100.0) / 100.0 : null)
            .responseRate(Math.round(responseRate * 100.0) / 100.0)
            .build();
    }

    @Transactional(readOnly = true)
    public List<SeverityDistributionItem> severityDistribution() {
        String[] severities = {"Low", "Moderate", "High", "Critical", "Unassessed"};
        long total = reportRepository.count() + 1;
        List<SeverityDistributionItem> result = new ArrayList<>();
        for (String sev : severities) {
            long count;
            if ("Unassessed".equals(sev)) {
                count = reportRepository.countTotal() - reportRepository.countBySeverity("Low")
                      - reportRepository.countBySeverity("Moderate")
                      - reportRepository.countBySeverity("High")
                      - reportRepository.countBySeverity("Critical");
                if (count < 0) count = 0;
            } else {
                count = reportRepository.countBySeverity(sev);
            }
            double pct = Math.round((count * 100.0 / total) * 100.0) / 100.0;
            result.add(SeverityDistributionItem.builder()
                .severity(sev).count(count).percentage(pct).build());
        }
        return result;
    }

    @Transactional(readOnly = true)
    public List<CategoryDistributionItem> categoryDistribution() {
        List<InfrastructureType> all = infraTypeRepository.findAll();
        List<Report> allReports = reportRepository.findAll();
        List<CategoryDistributionItem> result = new ArrayList<>();
        for (InfrastructureType it : all) {
            long count = allReports.stream().filter(r -> r.getInfrastructureType() != null
                && r.getInfrastructureType().getId().equals(it.getId())).count();
            long crit = allReports.stream().filter(r -> r.getInfrastructureType() != null
                && r.getInfrastructureType().getId().equals(it.getId())
                && ("Critical".equals(r.getAiSeverity()) || "Critical".equals(r.getFinalSeverity()))).count();
            result.add(CategoryDistributionItem.builder()
                .category(it.getName()).count(count).criticalCount(crit).build());
        }
        return result;
    }

    @Transactional(readOnly = true)
    public List<MonthlyTrendItem> monthlyTrend(int months) {
        LocalDateTime since = LocalDateTime.now().minusMonths(months);
        List<Report> reports = reportRepository.findAll().stream()
            .filter(r -> r.getCreatedAt() != null && r.getCreatedAt().isAfter(since))
            .collect(Collectors.toList());

        Map<String, long[]> byMonth = new TreeMap<>();  // [reports, resolved]
        for (Report r : reports) {
            String month = r.getCreatedAt().format(DateTimeFormatter.ofPattern("yyyy-MM"));
            long[] arr = byMonth.computeIfAbsent(month, k -> new long[2]);
            arr[0]++;
            if ("Resolved".equals(r.getStatus())) arr[1]++;
        }

        return byMonth.entrySet().stream()
            .map(e -> MonthlyTrendItem.builder()
                .month(e.getKey())
                .reports(e.getValue()[0])
                .resolved(e.getValue()[1])
                .build())
            .collect(Collectors.toList());
    }

    @Transactional(readOnly = true)
    public List<DistrictAnalyticsItem> districtAnalytics() {
        List<District> all = districtRepository.findAll();
        List<Report> allReports = reportRepository.findAll();
        List<DistrictAnalyticsItem> result = new ArrayList<>();
        for (District d : all) {
            List<Report> reports = allReports.stream()
                .filter(r -> r.getDistrict() != null && r.getDistrict().getId().equals(d.getId()))
                .collect(Collectors.toList());
            long crit = reports.stream().filter(r -> "Critical".equals(r.getAiSeverity())
                || "Critical".equals(r.getFinalSeverity())).count();
            long resolved = reports.stream().filter(r -> "Resolved".equals(r.getStatus())).count();
            double avgP = reports.stream()
                .mapToDouble(r -> priorityScoreRepository.findFirstByReportIdOrderByCreatedAtDesc(r.getId())
                    .map(PriorityScore::getScore).orElse(0.0))
                .average().orElse(0.0);
            result.add(DistrictAnalyticsItem.builder()
                .district(d.getName())
                .reports(reports.size())
                .critical(crit)
                .resolved(resolved)
                .avgPriority(Math.round(avgP * 100.0) / 100.0)
                .build());
        }
        return result;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> responseTime() {
        Map<String, Object> map = new HashMap<>();
        Double avg = reportRepository.avgResponseTimeHours();
        Double min = reportRepository.minResponseTimeHours();
        Double max = reportRepository.maxResponseTimeHours();
        map.put("avg_hours", avg != null ? Math.round(avg * 100.0) / 100.0 : null);
        map.put("min_hours", min != null ? Math.round(min * 100.0) / 100.0 : null);
        map.put("max_hours", max != null ? Math.round(max * 100.0) / 100.0 : null);
        return map;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> citizenParticipation() {
        Map<String, Object> map = new HashMap<>();
        map.put("total_citizens", userRepository.count());
        map.put("citizens_who_reported", userRepository.countActiveReporters());
        map.put("citizens_who_verified", userRepository.countVerifiers());
        Double avgVerifs = reportRepository.avgVerificationsPerReport();
        map.put("avg_verifications_per_report", avgVerifs != null
            ? Math.round(avgVerifs * 100.0) / 100.0 : 0.0);
        return map;
    }

    @Transactional(readOnly = true)
    public Map<String, Object> repeatIncidents(double thresholdKm) {
        List<Report> reports = reportRepository.findAllForClustering();
        List<Map<String, Object>> clusters = new ArrayList<>();
        Set<Long> used = new HashSet<>();
        for (int i = 0; i < reports.size(); i++) {
            Report r1 = reports.get(i);
            if (used.contains(r1.getId())) continue;
            List<Long> groupIds = new ArrayList<>();
            groupIds.add(r1.getId());
            for (int j = i + 1; j < reports.size(); j++) {
                Report r2 = reports.get(j);
                if (used.contains(r2.getId())) continue;
                if (r1.getInfrastructureType() == null || r2.getInfrastructureType() == null) continue;
                if (!r1.getInfrastructureType().getId().equals(r2.getInfrastructureType().getId())) continue;
                double d = com.infraguard.service.GeospatialService.haversineKm(
                    r1.getLatitude(), r1.getLongitude(),
                    r2.getLatitude(), r2.getLongitude()
                );
                if (d <= thresholdKm) {
                    groupIds.add(r2.getId());
                    used.add(r2.getId());
                }
            }
            if (groupIds.size() > 1) {
                Map<String, Object> cluster = new HashMap<>();
                cluster.put("infrastructure_type_id", r1.getInfrastructureType().getId());
                Map<String, Double> center = new HashMap<>();
                center.put("lat", r1.getLatitude());
                center.put("lng", r1.getLongitude());
                cluster.put("center", center);
                cluster.put("count", groupIds.size());
                cluster.put("report_ids", groupIds);
                clusters.add(cluster);
                used.add(r1.getId());
            }
        }
        return Map.of("clusters", clusters);
    }
}
