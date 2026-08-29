package com.infraguard.service;

import com.infraguard.ai.LlmService;
import com.infraguard.dto.admin.AdminDtos;
import com.infraguard.dto.report.*;
import com.infraguard.entity.*;
import com.infraguard.exception.GlobalExceptionHandler.*;
import com.infraguard.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.PageRequest;
import org.springframework.data.domain.Sort;
import org.springframework.data.jpa.domain.Specification;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;
import org.springframework.web.multipart.MultipartFile;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.Paths;
import java.security.SecureRandom;
import java.time.LocalDateTime;
import java.time.format.DateTimeFormatter;
import java.util.*;
import java.util.stream.Collectors;

@Slf4j
@Service
@RequiredArgsConstructor
public class ReportService {

    private final ReportRepository reportRepository;
    private final UserRepository userRepository;
    private final DistrictRepository districtRepository;
    private final InfrastructureTypeRepository infraTypeRepository;
    private final ImageRepository imageRepository;
    private final VerificationRepository verificationRepository;
    private final PriorityScoreRepository priorityScoreRepository;
    private final NotificationRepository notificationRepository;
    private final AdminActionRepository adminActionRepository;
    private final PriorityService priorityService;
    private final LlmService llmService;

    @Value("${app.upload.dir:./uploads}")
    private String uploadDir;

    private static final SecureRandom RANDOM = new SecureRandom();
    private static final String ALLOWED_EXTENSIONS = ".jpg.jpeg.png.webp";

    // ---------- Create ----------

    @Transactional
    public ReportResponse createReport(Long userId, String title, String description,
                                        Long categoryId, Double latitude, Double longitude,
                                        String address, Long districtId,
                                        List<MultipartFile> images) {
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        InfrastructureType infra = infraTypeRepository.findById(categoryId)
            .orElseThrow(() -> new ResourceNotFoundException("Invalid infrastructure type"));

        District district = districtId != null
            ? districtRepository.findById(districtId).orElse(null)
            : districtRepository.findAll().stream().findFirst().orElse(null);

        Report report = Report.builder()
            .referenceCode(generateReferenceCode())
            .user(user)
            .district(district)
            .infrastructureType(infra)
            .title(title)
            .description(description)
            .address(address)
            .latitude(latitude)
            .longitude(longitude)
            .status("Reported")
            .credibilityScore(1.0)
            .build();

        report = reportRepository.save(report);

        // Save images + run AI analysis on primary
        List<Image> savedImages = new ArrayList<>();
        for (int i = 0; i < (images != null ? images.size() : 0); i++) {
            MultipartFile file = images.get(i);
            try {
                SavedImage saved = saveUpload(file, "rpt" + report.getId());
                Image img = Image.builder()
                    .report(report)
                    .user(user)
                    .filePath(saved.path)
                    .fileUrl(saved.url)
                    .fileSizeBytes(saved.size)
                    .mimeType(saved.mimeType)
                    .isPrimary(i == 0)
                    .build();
                img = imageRepository.save(img);
                savedImages.add(img);

                if (i == 0) {
                    LlmService.LlmAnalysisResult ai = llmService.analyzeImage(saved.path);
                    if (ai != null) {
                        report.setAiSeverity(ai.severity());
                        report.setAiConfidence(ai.confidence());
                        report.setAiDamageType(ai.damageType());
                        report.setAiFeatures(String.format(
                            "{\"llm_severity\":\"%s\",\"llm_description\":\"%s\",\"llm_reasoning\":\"%s\",\"llm_model\":\"%s\"}",
                            ai.severity(), escape(ai.description()), escape(ai.reasoning()), escape(ai.model())
                        ));
                    }
                }
            } catch (IOException e) {
                log.error("[reports] Could not save image: {}", e.getMessage());
                throw new BadRequestException("Could not save image: " + file.getOriginalFilename());
            }
        }
        report.setImages(savedImages);

        // Initial priority (skip Overpass during report creation for speed — admin can recompute)
        try {
            priorityService.computeAndSavePriority(report, false);
        } catch (Exception e) {
            log.warn("[reports] Initial priority computation failed: {}", e.getMessage());
            priorityService.computeAndSavePriority(report, true);
        }

        // Notify the reporter
        notificationRepository.save(Notification.builder()
            .user(user)
            .report(report)
            .title("Report submitted")
            .message("Your report " + report.getReferenceCode() + " has been received and is being analyzed.")
            .type("success")
            .build());

        return toReportResponse(report);
    }

    // ---------- List ----------

    @Transactional(readOnly = true)
    public ReportListResponse listReports(int page, int pageSize, String status, String severity,
                                          Long categoryId, Long districtId, String search,
                                          String orderBy) {
        Sort sort = switch (orderBy) {
            case "created_at_asc" -> Sort.by(Sort.Direction.ASC, "createdAt");
            case "severity_desc" -> Sort.by(Sort.Direction.DESC, "aiSeverity");
            default -> Sort.by(Sort.Direction.DESC, "createdAt");
        };
        PageRequest pageable = PageRequest.of(Math.max(0, page - 1), Math.min(pageSize, 100), sort);

        Specification<Report> spec = (root, query, cb) -> {
            if (query != null && !Long.class.equals(query.getResultType()) && !long.class.equals(query.getResultType())) {
                root.fetch("infrastructureType", jakarta.persistence.criteria.JoinType.LEFT);
                root.fetch("district", jakarta.persistence.criteria.JoinType.LEFT);
                root.fetch("user", jakarta.persistence.criteria.JoinType.LEFT);
                query.distinct(true);
            }
            List<jakarta.persistence.criteria.Predicate> predicates = new ArrayList<>();
            if (status != null && !status.isBlank()) {
                predicates.add(cb.equal(root.get("status"), status));
            }
            if (severity != null && !severity.isBlank()) {
                predicates.add(cb.or(
                    cb.equal(root.get("aiSeverity"), severity),
                    cb.equal(root.get("finalSeverity"), severity)
                ));
            }
            if (categoryId != null) {
                predicates.add(cb.equal(root.get("infrastructureType").get("id"), categoryId));
            }
            if (districtId != null) {
                predicates.add(cb.equal(root.get("district").get("id"), districtId));
            }
            if (search != null && !search.isBlank()) {
                String pattern = "%" + search.trim().toLowerCase() + "%";
                predicates.add(cb.or(
                    cb.like(cb.lower(root.get("title")), pattern),
                    cb.like(cb.lower(root.get("description")), pattern),
                    cb.like(cb.lower(root.get("referenceCode")), pattern)
                ));
            }
            return cb.and(predicates.toArray(new jakarta.persistence.criteria.Predicate[0]));
        };

        Page<Report> result = reportRepository.findAll(spec, pageable);

        List<ReportListItem> items = result.getContent().stream().map(r -> {
            PriorityScore ps = priorityScoreRepository
                .findFirstByReportIdOrderByCreatedAtDesc(r.getId()).orElse(null);
            String primaryImg = r.getImages().stream()
                .filter(Image::getIsPrimary).findFirst()
                .or(() -> r.getImages().stream().findFirst())
                .map(Image::getFileUrl).orElse(null);
            return ReportListItem.builder()
                .id(r.getId())
                .referenceCode(r.getReferenceCode())
                .title(r.getTitle())
                .latitude(r.getLatitude())
                .longitude(r.getLongitude())
                .aiSeverity(r.getAiSeverity())
                .finalSeverity(r.getFinalSeverity())
                .status(r.getStatus())
                .categoryName(r.getInfrastructureType() != null ? r.getInfrastructureType().getName() : null)
                .districtName(r.getDistrict() != null ? r.getDistrict().getName() : null)
                .verificationCount(r.getVerificationCount())
                .credibilityScore(r.getCredibilityScore())
                .createdAt(r.getCreatedAt())
                .priorityScore(ps != null ? ps.getScore() : null)
                .priorityRank(ps != null ? ps.getRank() : null)
                .imageUrl(primaryImg)
                .build();
        }).collect(Collectors.toList());

        return ReportListResponse.builder()
            .items(items)
            .total(result.getTotalElements())
            .page(page)
            .pageSize(pageSize)
            .build();
    }

    @Transactional(readOnly = true)
    public ReportResponse getReport(Long id) {
        Report report = reportRepository.findById(id)
            .orElseThrow(() -> new ResourceNotFoundException("Report not found"));
        return toReportResponse(report);
    }

    @Transactional(readOnly = true)
    public List<ReportResponse> myReports(Long userId) {
        return reportRepository.findByUserIdOrderByCreatedAtDesc(userId).stream()
            .map(this::toReportResponse)
            .collect(Collectors.toList());
    }

    // ---------- Verifications ----------

    @Transactional
    public ReportResponse addVerification(Long reportId, Long userId, VerificationRequest req,
                                           MultipartFile imageFile) {
        Report report = reportRepository.findById(reportId)
            .orElseThrow(() -> new ResourceNotFoundException("Report not found"));
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new ResourceNotFoundException("User not found"));

        if (Objects.equals(report.getUser().getId(), user.getId())) {
            throw new BadRequestException("You cannot verify your own report.");
        }
        if (verificationRepository.existsByReportIdAndUserId(reportId, userId)) {
            throw new ConflictException("You have already verified this report.");
        }

        String imagePath = null;
        if (imageFile != null && !imageFile.isEmpty()) {
            try {
                SavedImage saved = saveUpload(imageFile, "ver" + reportId);
                imagePath = saved.url;
                imageRepository.save(Image.builder()
                    .report(report)
                    .user(user)
                    .filePath(saved.path)
                    .fileUrl(saved.url)
                    .fileSizeBytes(saved.size)
                    .mimeType(saved.mimeType)
                    .isPrimary(false)
                    .caption("Verification by user #" + userId)
                    .build());
            } catch (IOException e) {
                log.warn("[verify] Could not save verification image: {}", e.getMessage());
            }
        }

        Verification v = Verification.builder()
            .report(report)
            .user(user)
            .severityVote(req.getSeverityVote())
            .comment(req.getComment())
            .isConfirmed(req.getIsConfirmed() != null ? req.getIsConfirmed() : true)
            .imagePath(imagePath)
            .build();
        verificationRepository.save(v);

        if (Boolean.TRUE.equals(req.getIsConfirmed())) {
            report.setUpvoteCount(report.getUpvoteCount() + 1);
        } else {
            report.setDownvoteCount(report.getDownvoteCount() + 1);
        }
        report.setVerificationCount(report.getVerificationCount() + 1);
        report.setCredibilityScore(Math.min(10.0, report.getCredibilityScore() + 1.0));

        if (report.getVerificationCount() >= 3 && "Reported".equals(report.getStatus())) {
            report.setStatus("Verified");
            notificationRepository.save(Notification.builder()
                .user(report.getUser())
                .report(report)
                .title("Report verified")
                .message("Your report " + report.getReferenceCode() + " has been verified by community consensus.")
                .type("success")
                .build());
        }

        report = reportRepository.save(report);

        try {
            priorityService.computeAndSavePriority(report, true);
        } catch (Exception e) {
            log.warn("[verify] Priority recompute failed: {}", e.getMessage());
        }

        notificationRepository.save(Notification.builder()
            .user(report.getUser())
            .report(report)
            .title("New verification on your report")
            .message(user.getFullName() + " " + (Boolean.TRUE.equals(req.getIsConfirmed()) ? "confirmed" : "flagged")
                + " your report " + report.getReferenceCode() + ".")
            .type("info")
            .build());

        return toReportResponse(report);
    }

    // ---------- Admin actions ----------

    @Transactional
    public ReportResponse updateStatus(Long reportId, Long adminId, AdminDtos.StatusUpdateRequest req) {
        Report report = reportRepository.findById(reportId)
            .orElseThrow(() -> new ResourceNotFoundException("Report not found"));
        User admin = userRepository.findById(adminId)
            .orElseThrow(() -> new ResourceNotFoundException("Admin not found"));

        Set<String> allowed = Set.of("Reported", "Verified", "Rejected", "Assigned", "In Progress", "Resolved");
        if (!allowed.contains(req.getStatus())) {
            throw new BadRequestException("Invalid status: " + req.getStatus());
        }

        String oldStatus = report.getStatus();
        report.setStatus(req.getStatus());
        if (req.getAssignedTeam() != null) report.setAssignedTeam(req.getAssignedTeam());
        if ("Resolved".equals(req.getStatus())) {
            report.setResolvedAt(LocalDateTime.now());
            if (req.getNotes() != null) report.setResolutionNotes(req.getNotes());
        } else if (req.getNotes() != null) {
            report.setResolutionNotes(req.getNotes());
        }

        adminActionRepository.save(AdminAction.builder()
            .admin(admin)
            .report(report)
            .action("status_change")
            .previousValue(oldStatus)
            .newValue(req.getStatus())
            .notes(req.getNotes())
            .build());

        notificationRepository.save(Notification.builder()
            .user(report.getUser())
            .report(report)
            .title("Report status updated")
            .message("Your report " + report.getReferenceCode() + " is now: " + req.getStatus() + ".")
            .type("info")
            .build());

        report = reportRepository.save(report);
        return toReportResponse(report);
    }

    @Transactional
    public ReportResponse updateSeverity(Long reportId, Long adminId, AdminDtos.SeverityUpdateRequest req) {
        Report report = reportRepository.findById(reportId)
            .orElseThrow(() -> new ResourceNotFoundException("Report not found"));
        User admin = userRepository.findById(adminId)
            .orElseThrow(() -> new ResourceNotFoundException("Admin not found"));

        Set<String> allowed = Set.of("Low", "Moderate", "High", "Critical");
        if (!allowed.contains(req.getSeverity())) {
            throw new BadRequestException("Invalid severity.");
        }

        String old = report.getFinalSeverity();
        report.setFinalSeverity(req.getSeverity());
        adminActionRepository.save(AdminAction.builder()
            .admin(admin)
            .report(report)
            .action("severity_override")
            .previousValue(old)
            .newValue(req.getSeverity())
            .notes(req.getNotes())
            .build());

        report = reportRepository.save(report);
        priorityService.computeAndSavePriority(report, true);
        return toReportResponse(report);
    }

    @Transactional
    public ReportResponse assignTeam(Long reportId, Long adminId, AdminDtos.AssignTeamRequest req) {
        Report report = reportRepository.findById(reportId)
            .orElseThrow(() -> new ResourceNotFoundException("Report not found"));
        User admin = userRepository.findById(adminId)
            .orElseThrow(() -> new ResourceNotFoundException("Admin not found"));

        String old = report.getAssignedTeam();
        report.setAssignedTeam(req.getTeam());
        if ("Reported".equals(report.getStatus()) || "Verified".equals(report.getStatus())) {
            report.setStatus("Assigned");
        }
        adminActionRepository.save(AdminAction.builder()
            .admin(admin)
            .report(report)
            .action("assign_team")
            .previousValue(old)
            .newValue(req.getTeam())
            .notes(req.getNotes())
            .build());

        notificationRepository.save(Notification.builder()
            .user(report.getUser())
            .report(report)
            .title("Response team assigned")
            .message("Report " + report.getReferenceCode() + " has been assigned to: " + req.getTeam() + ".")
            .type("info")
            .build());

        report = reportRepository.save(report);
        return toReportResponse(report);
    }

    // ---------- Helpers ----------

    private String generateReferenceCode() {
        String today = LocalDateTime.now().format(DateTimeFormatter.ofPattern("yyyyMMdd"));
        byte[] bytes = new byte[3];
        RANDOM.nextBytes(bytes);
        String suffix = bytesToHex(bytes).toUpperCase();
        return "RPT-" + today + "-" + suffix;
    }

    private String bytesToHex(byte[] bytes) {
        StringBuilder sb = new StringBuilder();
        for (byte b : bytes) sb.append(String.format("%02x", b));
        return sb.toString();
    }

    private record SavedImage(String path, String url, int size, String mimeType) {}

    private SavedImage saveUpload(MultipartFile file, String prefix) throws IOException {
        String originalName = file.getOriginalFilename() != null ? file.getOriginalFilename() : "image.jpg";
        String ext = originalName.contains(".") ? originalName.substring(originalName.lastIndexOf("."))
                                                 .toLowerCase() : ".jpg";
        if (!ALLOWED_EXTENSIONS.contains(ext)) {
            throw new BadRequestException("Unsupported file type: " + ext);
        }
        String mimeType = file.getContentType() != null ? file.getContentType() : "image/jpeg";
        String filename = prefix + "_" + System.currentTimeMillis() + "_" + UUID.randomUUID().toString().substring(0, 8) + ext;
        Path dirPath = Paths.get(uploadDir);
        Files.createDirectories(dirPath);
        Path target = dirPath.resolve(filename);
        file.transferTo(target.toFile());
        return new SavedImage(target.toString(), "/uploads/" + filename, (int) file.getSize(), mimeType);
    }

    private String escape(String s) {
        return s == null ? "" : s.replace("\"", "\\\"").replace("\n", " ");
    }

    public ReportResponse toReportResponse(Report r) {
        PriorityScore ps = priorityScoreRepository
            .findFirstByReportIdOrderByCreatedAtDesc(r.getId()).orElse(null);

        List<ImageResponse> images = r.getImages().stream()
            .map(img -> ImageResponse.builder()
                .id(img.getId())
                .fileUrl(img.getFileUrl())
                .isPrimary(img.getIsPrimary())
                .caption(img.getCaption())
                .width(img.getWidth())
                .height(img.getHeight())
                .createdAt(img.getCreatedAt())
                .build())
            .collect(Collectors.toList());

        List<VerificationResponse> verifs = r.getVerifications().stream()
            .map(v -> VerificationResponse.builder()
                .id(v.getId())
                .reportId(r.getId())
                .userId(v.getUser() != null ? v.getUser().getId() : null)
                .severityVote(v.getSeverityVote())
                .comment(v.getComment())
                .isConfirmed(v.getIsConfirmed())
                .createdAt(v.getCreatedAt())
                .build())
            .collect(Collectors.toList());

        return ReportResponse.builder()
            .id(r.getId())
            .referenceCode(r.getReferenceCode())
            .title(r.getTitle())
            .description(r.getDescription())
            .address(r.getAddress())
            .latitude(r.getLatitude())
            .longitude(r.getLongitude())
            .categoryId(r.getInfrastructureType() != null ? r.getInfrastructureType().getId() : null)
            .categoryName(r.getInfrastructureType() != null ? r.getInfrastructureType().getName() : null)
            .districtId(r.getDistrict() != null ? r.getDistrict().getId() : null)
            .districtName(r.getDistrict() != null ? r.getDistrict().getName() : null)
            .aiSeverity(r.getAiSeverity())
            .aiConfidence(r.getAiConfidence())
            .aiDamageType(r.getAiDamageType())
            .finalSeverity(r.getFinalSeverity())
            .status(r.getStatus())
            .credibilityScore(r.getCredibilityScore())
            .verificationCount(r.getVerificationCount())
            .upvoteCount(r.getUpvoteCount())
            .downvoteCount(r.getDownvoteCount())
            .assignedTeam(r.getAssignedTeam())
            .resolutionNotes(r.getResolutionNotes())
            .resolvedAt(r.getResolvedAt())
            .createdAt(r.getCreatedAt())
            .updatedAt(r.getUpdatedAt())
            .userId(r.getUser() != null ? r.getUser().getId() : null)
            .userName(r.getUser() != null ? r.getUser().getFullName() : null)
            .images(images)
            .priority(ps != null ? PriorityScoreResponse.builder()
                .score(ps.getScore())
                .rank(ps.getRank())
                .severityComponent(ps.getSeverityComponent())
                .verificationComponent(ps.getVerificationComponent())
                .populationComponent(ps.getPopulationComponent())
                .roadImportanceComponent(ps.getRoadImportanceComponent())
                .hospitalProximityComponent(ps.getHospitalProximityComponent())
                .schoolProximityComponent(ps.getSchoolProximityComponent())
                .utilityImportanceComponent(ps.getUtilityImportanceComponent())
                .timeUrgencyComponent(ps.getTimeUrgencyComponent())
                .verificationStatusComponent(ps.getVerificationStatusComponent())
                .recommendedResponseTime(ps.getRecommendedResponseTime())
                .resourceUrgency(ps.getResourceUrgency())
                .createdAt(ps.getCreatedAt())
                .build() : null)
            .verifications(verifs)
            .build();
    }

    @Transactional(readOnly = true)
    public Map<String, Object> getMapData(Long districtId, Long categoryId, String severity, String status) {
        List<Report> reports = reportRepository.findForMap(districtId, categoryId, severity, status);
        List<Map<String, Object>> features = new ArrayList<>();
        for (Report r : reports) {
            String sev = r.getFinalSeverity() != null ? r.getFinalSeverity() : r.getAiSeverity();
            String sevColor = switch (sev != null ? sev : "") {
                case "Low" -> "#22c55e";
                case "Moderate" -> "#f59e0b";
                case "High" -> "#ef4444";
                case "Critical" -> "#7c3aed";
                default -> "#6b7280";
            };
            PriorityScore ps = priorityScoreRepository.findFirstByReportIdOrderByCreatedAtDesc(r.getId()).orElse(null);
            String primaryImg = r.getImages().stream()
                .filter(Image::getIsPrimary).findFirst()
                .or(() -> r.getImages().stream().findFirst())
                .map(Image::getFileUrl).orElse(null);

            Map<String, Object> props = new HashMap<>();
            props.put("id", r.getId());
            props.put("reference_code", r.getReferenceCode());
            props.put("title", r.getTitle());
            props.put("severity", sev);
            props.put("severity_color", sevColor);
            props.put("status", r.getStatus());
            props.put("category", r.getInfrastructureType() != null ? r.getInfrastructureType().getName() : null);
            props.put("category_icon", r.getInfrastructureType() != null ? r.getInfrastructureType().getIcon() : null);
            props.put("verification_count", r.getVerificationCount());
            props.put("credibility_score", r.getCredibilityScore());
            props.put("priority_score", ps != null ? ps.getScore() : null);
            props.put("priority_rank", ps != null ? ps.getRank() : null);
            props.put("image_url", primaryImg);
            props.put("created_at", r.getCreatedAt() != null ? r.getCreatedAt().toString() : null);

            Map<String, Object> geom = Map.of(
                "type", "Point",
                "coordinates", List.of(r.getLongitude(), r.getLatitude())
            );

            features.add(Map.of(
                "type", "Feature",
                "geometry", geom,
                "properties", props
            ));
        }
        return Map.of("type", "FeatureCollection", "features", features);
    }

    @Transactional(readOnly = true)
    public List<List<Object>> getHeatmap(String severity) {
        List<Report> reports = reportRepository.findForMap(null, null, severity, null);
        List<List<Object>> points = new ArrayList<>();
        for (Report r : reports) {
            String sev = r.getFinalSeverity() != null ? r.getFinalSeverity() : r.getAiSeverity();
            double weight = switch (sev != null ? sev : "") {
                case "Low" -> 0.3;
                case "Moderate" -> 0.6;
                case "High" -> 0.85;
                case "Critical" -> 1.0;
                default -> 0.4;
            };
            points.add(List.of(r.getLatitude(), r.getLongitude(), weight));
        }
        return points;
    }
}
