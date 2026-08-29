package com.infraguard.repository;

import com.infraguard.entity.Report;
import org.springframework.data.domain.Page;
import org.springframework.data.domain.Pageable;
import org.springframework.data.jpa.repository.JpaSpecificationExecutor;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.time.LocalDateTime;
import java.util.List;

@Repository
public interface ReportRepository extends JpaRepository<Report, Long>, JpaSpecificationExecutor<Report> {

    List<Report> findByUserIdOrderByCreatedAtDesc(Long userId);

    @Query(value = """
        SELECT r FROM Report r
        LEFT JOIN FETCH r.infrastructureType it
        LEFT JOIN FETCH r.district d
        LEFT JOIN FETCH r.user u
        WHERE (:status IS NULL OR r.status = :status)
          AND (:severity IS NULL OR r.aiSeverity = :severity OR r.finalSeverity = :severity)
          AND (:categoryId IS NULL OR it.id = :categoryId)
          AND (:districtId IS NULL OR d.id = :districtId)
          AND (:searchPattern IS NULL OR LOWER(r.title) LIKE :searchPattern
                                     OR LOWER(r.description) LIKE :searchPattern
                                     OR LOWER(r.referenceCode) LIKE :searchPattern)
          AND (:since IS NULL OR r.createdAt >= :since)
          AND (:until IS NULL OR r.createdAt <= :until)
        """,
        countQuery = """
        SELECT COUNT(r) FROM Report r
        LEFT JOIN r.infrastructureType it
        LEFT JOIN r.district d
        WHERE (:status IS NULL OR r.status = :status)
          AND (:severity IS NULL OR r.aiSeverity = :severity OR r.finalSeverity = :severity)
          AND (:categoryId IS NULL OR it.id = :categoryId)
          AND (:districtId IS NULL OR d.id = :districtId)
          AND (:searchPattern IS NULL OR LOWER(r.title) LIKE :searchPattern
                                     OR LOWER(r.description) LIKE :searchPattern
                                     OR LOWER(r.referenceCode) LIKE :searchPattern)
          AND (:since IS NULL OR r.createdAt >= :since)
          AND (:until IS NULL OR r.createdAt <= :until)
        """)
    Page<Report> findWithFilters(
            @Param("status") String status,
            @Param("severity") String severity,
            @Param("categoryId") Long categoryId,
            @Param("districtId") Long districtId,
            @Param("searchPattern") String searchPattern,
            @Param("since") LocalDateTime since,
            @Param("until") LocalDateTime until,
            Pageable pageable
    );

    @Query("""
        SELECT DISTINCT r FROM Report r
        LEFT JOIN FETCH r.infrastructureType it
        LEFT JOIN FETCH r.images img
        WHERE (:districtId IS NULL OR r.district.id = :districtId)
          AND (:categoryId IS NULL OR it.id = :categoryId)
          AND (:severity IS NULL OR r.aiSeverity = :severity OR r.finalSeverity = :severity)
          AND (:status IS NULL OR r.status = :status)
        """)
    List<Report> findForMap(
            @Param("districtId") Long districtId,
            @Param("categoryId") Long categoryId,
            @Param("severity") String severity,
            @Param("status") String status
    );

    @Query("SELECT COUNT(r) FROM Report r")
    long countTotal();

    @Query("SELECT COUNT(r) FROM Report r WHERE r.status = :status")
    long countByStatus(@Param("status") String status);

    @Query("""
        SELECT COUNT(r) FROM Report r
        WHERE r.aiSeverity = :severity OR r.finalSeverity = :severity
        """)
    long countBySeverity(@Param("severity") String severity);

    @Query("""
        SELECT COUNT(r) FROM Report r
        WHERE (r.aiSeverity = 'Critical' OR r.finalSeverity = 'Critical')
        """)
    long countCritical();

    // Native SQL queries for date/time arithmetic (Hibernate 6 JPQL doesn't support
    // EXTRACT(EPOCH FROM duration) — it requires a Temporal, not a Duration).
    @Query(value = """
        SELECT AVG(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600.0)
        FROM reports
        WHERE status = 'Resolved' AND resolved_at IS NOT NULL
        """, nativeQuery = true)
    Double avgResponseTimeHours();

    @Query(value = """
        SELECT MIN(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600.0)
        FROM reports
        WHERE status = 'Resolved' AND resolved_at IS NOT NULL
        """, nativeQuery = true)
    Double minResponseTimeHours();

    @Query(value = """
        SELECT MAX(EXTRACT(EPOCH FROM (resolved_at - created_at)) / 3600.0)
        FROM reports
        WHERE status = 'Resolved' AND resolved_at IS NOT NULL
        """, nativeQuery = true)
    Double maxResponseTimeHours();

    @Query("""
        SELECT AVG(r.verificationCount) FROM Report r
        """)
    Double avgVerificationsPerReport();

    @Query("""
        SELECT r FROM Report r
        LEFT JOIN FETCH r.infrastructureType
        WHERE r.status <> 'Rejected'
        """)
    List<Report> findAllForClustering();
}