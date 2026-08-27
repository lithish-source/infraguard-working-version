package com.infraguard.service;

import com.infraguard.ai.LlmService;
import com.infraguard.ai.PriorityEngine;
import com.infraguard.entity.*;
import com.infraguard.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.Duration;
import java.time.LocalDateTime;
import java.util.HashMap;
import java.util.Map;

/**
 * Priority Service — wraps the AI PriorityEngine and persists PriorityScore rows.
 *
 * Uses REAL geospatial data from Overpass API for hospital/school/road proximity.
 * Falls back to district-based estimates if Overpass is unavailable or skipped
 * (e.g. during seeding).
 */
@Slf4j
@Service
@RequiredArgsConstructor
public class PriorityService {

    private final PriorityEngine engine = new PriorityEngine();
    private final PriorityScoreRepository priorityScoreRepository;
    private final InfrastructureTypeRepository infraTypeRepository;
    private final DistrictRepository districtRepository;
    private final GeospatialService geospatialService;

    @Transactional
    public PriorityScore computeAndSavePriority(Report report, boolean skipOverpass) {
        InfrastructureType infra = report.getInfrastructureType();
        District district = report.getDistrict();

        String severity = report.getFinalSeverity() != null ? report.getFinalSeverity() : report.getAiSeverity();

        Double hospitalDistanceKm = null;
        Double schoolDistanceKm = null;
        String roadClass = null;

        if (!skipOverpass) {
            try {
                GeospatialService.LocationContext ctx =
                    geospatialService.getLocationContext(report.getLatitude(), report.getLongitude());
                hospitalDistanceKm = ctx.nearestHospitalKm();
                schoolDistanceKm = ctx.nearestSchoolKm();
                roadClass = ctx.roadClass();
            } catch (Exception e) {
                log.warn("[priority] Overpass query failed, using fallback: {}", e.getMessage());
            }
        }

        // Fallback to district-based estimates
        if (hospitalDistanceKm == null && district != null && district.getAreaSqKm() != null) {
            double approxRadiusKm = Math.max(1.0, Math.sqrt(district.getAreaSqKm())) / 2.0;
            hospitalDistanceKm = approxRadiusKm * 0.6;
        }
        if (schoolDistanceKm == null && district != null && district.getAreaSqKm() != null) {
            double approxRadiusKm = Math.max(1.0, Math.sqrt(district.getAreaSqKm())) / 2.0;
            schoolDistanceKm = approxRadiusKm * 0.4;
        }

        // Fallback road class from infra code
        if (roadClass == null && infra != null) {
            String code = infra.getCode().toUpperCase();
            if (code.equals("ROAD") || code.equals("BRIDGE")) roadClass = "major_road";
            else if (code.equals("TRAFFIC")) roadClass = "arterial";
            else if (code.equals("STREETLIGHT")) roadClass = "local";
        }

        PriorityEngine.PriorityResult result = engine.compute(
            severity,
            report.getVerificationCount() != null ? report.getVerificationCount() : 0,
            district != null ? district.getPopulation() : null,
            roadClass,
            hospitalDistanceKm,
            schoolDistanceKm,
            infra != null ? infra.getCode() : null,
            report.getCreatedAt(),
            report.getStatus(),
            report.getCredibilityScore() != null ? report.getCredibilityScore() : 0.0,
            LocalDateTime.now()
        );

        PriorityScore score = PriorityScore.builder()
            .report(report)
            .score(result.score)
            .rank(result.rank)
            .severityComponent(result.components.get("severity_component"))
            .verificationComponent(result.components.get("verification_component"))
            .populationComponent(result.components.get("population_component"))
            .roadImportanceComponent(result.components.get("road_importance_component"))
            .hospitalProximityComponent(result.components.get("hospital_proximity_component"))
            .schoolProximityComponent(result.components.get("school_proximity_component"))
            .utilityImportanceComponent(result.components.get("utility_importance_component"))
            .timeUrgencyComponent(result.components.get("time_urgency_component"))
            .verificationStatusComponent(result.components.get("verification_status_component"))
            .recommendedResponseTime(result.recommendedResponseTime)
            .resourceUrgency(result.resourceUrgency)
            .build();

        return priorityScoreRepository.save(score);
    }

    /** Convenience overload — uses Overpass by default. */
    public PriorityScore computeAndSavePriority(Report report) {
        return computeAndSavePriority(report, false);
    }

    @Transactional
    public int recomputeAllOpen() {
        int count = 0;
        for (Report r : priorityScoreRepository.findLatestForOpenReports()
                .stream().map(PriorityScore::getReport).distinct().toList()) {
            computeAndSavePriority(r, false);
            count++;
        }
        return count;
    }
}
