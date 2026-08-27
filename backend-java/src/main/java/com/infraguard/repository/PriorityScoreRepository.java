package com.infraguard.repository;

import com.infraguard.entity.PriorityScore;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface PriorityScoreRepository extends JpaRepository<PriorityScore, Long> {

    Optional<PriorityScore> findFirstByReportIdOrderByCreatedAtDesc(Long reportId);

    List<PriorityScore> findAllByOrderByScoreDesc();

    @Query("""
        SELECT AVG(p.score) FROM PriorityScore p
        WHERE p.report.id = :reportId
        """)
    Double avgScoreForReport(@Param("reportId") Long reportId);

    @Query("""
        SELECT p FROM PriorityScore p
        WHERE p.report.status NOT IN ('Resolved', 'Rejected')
        ORDER BY p.score DESC
        """)
    List<PriorityScore> findLatestForOpenReports();
}
