package com.infraguard.entity;

import jakarta.persistence.*;
import lombok.*;
import org.hibernate.annotations.JdbcTypeCode;
import org.hibernate.type.SqlTypes;
import org.locationtech.jts.geom.Point;

import java.time.LocalDateTime;
import java.util.ArrayList;
import java.util.List;

@Entity
@Table(name = "reports")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class Report {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @Column(name = "reference_code", nullable = false, unique = true, length = 30)
    private String referenceCode;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "user_id", nullable = false)
    private User user;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "district_id")
    private District district;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "infrastructure_type_id", nullable = false)
    private InfrastructureType infrastructureType;

    @Column(name = "title", nullable = false, length = 255)
    private String title;

    @Column(name = "description", nullable = false, columnDefinition = "TEXT")
    private String description;

    @Column(name = "address", length = 500)
    private String address;

    @Column(name = "latitude", nullable = false)
    private Double latitude;

    @Column(name = "longitude", nullable = false)
    private Double longitude;

    @Column(name = "geom", columnDefinition = "geometry(POINT,4326)")
    private Point geom;

    @Column(name = "ai_severity", length = 20)
    private String aiSeverity;

    @Column(name = "ai_confidence")
    private Double aiConfidence;

    @Column(name = "ai_damage_type", length = 100)
    private String aiDamageType;

    @Column(name = "ai_features", columnDefinition = "jsonb")
    @JdbcTypeCode(SqlTypes.JSON)
    private String aiFeatures;

    @Column(name = "final_severity", length = 20)
    private String finalSeverity;

    @Column(name = "status", nullable = false, length = 30)
    private String status = "Reported";

    @Column(name = "credibility_score", nullable = false)
    private Double credibilityScore = 0.0;

    @Column(name = "verification_count", nullable = false)
    private Integer verificationCount = 0;

    @Column(name = "upvote_count", nullable = false)
    private Integer upvoteCount = 0;

    @Column(name = "downvote_count", nullable = false)
    private Integer downvoteCount = 0;

    @Column(name = "assigned_team", length = 150)
    private String assignedTeam;

    @Column(name = "resolution_notes", columnDefinition = "TEXT")
    private String resolutionNotes;

    @Column(name = "resolved_at")
    private LocalDateTime resolvedAt;

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("isPrimary DESC, createdAt ASC")
    private List<Image> images = new ArrayList<>();

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Verification> verifications = new ArrayList<>();

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    @OrderBy("createdAt DESC")
    private List<PriorityScore> priorityScores = new ArrayList<>();

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<Notification> notifications = new ArrayList<>();

    @OneToMany(mappedBy = "report", cascade = CascadeType.ALL, orphanRemoval = true)
    private List<AdminAction> adminActions = new ArrayList<>();

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        this.createdAt = LocalDateTime.now();
        this.updatedAt = this.createdAt;
        if (this.status == null) this.status = "Reported";
        if (this.credibilityScore == null) this.credibilityScore = 0.0;
        if (this.verificationCount == null) this.verificationCount = 0;
        if (this.upvoteCount == null) this.upvoteCount = 0;
        if (this.downvoteCount == null) this.downvoteCount = 0;
    }

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }

    /** Returns the effective severity (admin override takes priority over AI). */
    @Transient
    public String getEffectiveSeverity() {
        return finalSeverity != null ? finalSeverity : aiSeverity;
    }
}
