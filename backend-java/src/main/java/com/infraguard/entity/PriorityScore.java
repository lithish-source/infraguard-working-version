package com.infraguard.entity;

import jakarta.persistence.*;
import lombok.*;

import java.time.LocalDateTime;

@Entity
@Table(name = "priority_scores")
@Getter @Setter @NoArgsConstructor @AllArgsConstructor @Builder
public class PriorityScore {

    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    @Column(name = "id")
    private Long id;

    @ManyToOne(fetch = FetchType.LAZY)
    @JoinColumn(name = "report_id", nullable = false)
    private Report report;

    @Column(name = "score", nullable = false)
    private Double score;

    @Column(name = "rank")
    private Integer rank;

    @Column(name = "severity_component", nullable = false)
    private Double severityComponent = 0.0;

    @Column(name = "verification_component", nullable = false)
    private Double verificationComponent = 0.0;

    @Column(name = "population_component", nullable = false)
    private Double populationComponent = 0.0;

    @Column(name = "road_importance_component", nullable = false)
    private Double roadImportanceComponent = 0.0;

    @Column(name = "hospital_proximity_component", nullable = false)
    private Double hospitalProximityComponent = 0.0;

    @Column(name = "school_proximity_component", nullable = false)
    private Double schoolProximityComponent = 0.0;

    @Column(name = "utility_importance_component", nullable = false)
    private Double utilityImportanceComponent = 0.0;

    @Column(name = "time_urgency_component", nullable = false)
    private Double timeUrgencyComponent = 0.0;

    @Column(name = "verification_status_component", nullable = false)
    private Double verificationStatusComponent = 0.0;

    @Column(name = "recommended_response_time", length = 50)
    private String recommendedResponseTime;

    @Column(name = "resource_urgency", length = 30)
    private String resourceUrgency;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    @Column(name = "updated_at", nullable = false)
    private LocalDateTime updatedAt;

    @PrePersist
    protected void onCreate() {
        this.createdAt = LocalDateTime.now();
        this.updatedAt = this.createdAt;
        // Initialize all components to 0.0 if null
        if (severityComponent == null) severityComponent = 0.0;
        if (verificationComponent == null) verificationComponent = 0.0;
        if (populationComponent == null) populationComponent = 0.0;
        if (roadImportanceComponent == null) roadImportanceComponent = 0.0;
        if (hospitalProximityComponent == null) hospitalProximityComponent = 0.0;
        if (schoolProximityComponent == null) schoolProximityComponent = 0.0;
        if (utilityImportanceComponent == null) utilityImportanceComponent = 0.0;
        if (timeUrgencyComponent == null) timeUrgencyComponent = 0.0;
        if (verificationStatusComponent == null) verificationStatusComponent = 0.0;
    }

    @PreUpdate
    protected void onUpdate() {
        this.updatedAt = LocalDateTime.now();
    }
}
