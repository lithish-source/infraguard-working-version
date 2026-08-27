package com.infraguard.controller;

import com.infraguard.dto.report.*;
import com.infraguard.entity.User;
import com.infraguard.security.CustomUserDetailsService;
import com.infraguard.service.ReportService;
import lombok.RequiredArgsConstructor;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;
import org.springframework.web.multipart.MultipartFile;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/reports")
@RequiredArgsConstructor
public class ReportController {

    private final ReportService reportService;
    private final CustomUserDetailsService userDetailsService;

    @PostMapping(consumes = "multipart/form-data")
    @ResponseStatus(HttpStatus.CREATED)
    public ReportResponse createReport(
        @RequestParam("title") String title,
        @RequestParam("description") String description,
        @RequestParam("category_id") Long categoryId,
        @RequestParam("latitude") Double latitude,
        @RequestParam("longitude") Double longitude,
        @RequestParam(value = "address", required = false) String address,
        @RequestParam(value = "district_id", required = false) Long districtId,
        @RequestParam(value = "images", required = false) List<MultipartFile> images,
        @AuthenticationPrincipal UserDetails principal
    ) {
        User user = userDetailsService.loadUserEntityByEmail(principal.getUsername());
        return reportService.createReport(
            user.getId(), title, description, categoryId, latitude, longitude,
            address, districtId, images
        );
    }

    @GetMapping
    public ReportListResponse listReports(
        @RequestParam(defaultValue = "1") int page,
        @RequestParam(defaultValue = "20") int page_size,
        @RequestParam(required = false) String status,
        @RequestParam(required = false) String severity,
        @RequestParam(value = "category_id", required = false) Long categoryId,
        @RequestParam(value = "district_id", required = false) Long districtId,
        @RequestParam(required = false) String search,
        @RequestParam(defaultValue = "created_at_desc") String order_by
    ) {
        return reportService.listReports(page, page_size, status, severity,
            categoryId, districtId, search, order_by);
    }

    @GetMapping("/map")
    public ResponseEntity<Map<String, Object>> getMapData() {
        // TODO: implement GeoJSON FeatureCollection assembly
        // For now, return empty FeatureCollection
        return ResponseEntity.ok(Map.of("type", "FeatureCollection", "features", List.of()));
    }

    @GetMapping("/heatmap")
    public ResponseEntity<Map<String, Object>> getHeatmap() {
        // TODO: return [[lat, lng, weight], ...]
        return ResponseEntity.ok(Map.of("points", List.of()));
    }

    @GetMapping("/{id}")
    public ReportResponse getReport(@PathVariable Long id) {
        return reportService.getReport(id);
    }

    @GetMapping("/me/my-reports")
    public List<ReportResponse> myReports(@AuthenticationPrincipal UserDetails principal) {
        User user = userDetailsService.loadUserEntityByEmail(principal.getUsername());
        return reportService.myReports(user.getId());
    }

    @PostMapping(value = "/{id}/verifications", consumes = "multipart/form-data")
    public ReportResponse addVerification(
        @PathVariable Long id,
        @RequestParam(value = "severity_vote", required = false) String severityVote,
        @RequestParam(value = "comment", required = false) String comment,
        @RequestParam(value = "is_confirmed", defaultValue = "true") Boolean isConfirmed,
        @RequestParam(value = "image", required = false) MultipartFile image,
        @AuthenticationPrincipal UserDetails principal
    ) {
        VerificationRequest req = new VerificationRequest();
        req.setSeverityVote(severityVote);
        req.setComment(comment);
        req.setIsConfirmed(isConfirmed);
        User user = userDetailsService.loadUserEntityByEmail(principal.getUsername());
        return reportService.addVerification(id, user.getId(), req, image);
    }
}
