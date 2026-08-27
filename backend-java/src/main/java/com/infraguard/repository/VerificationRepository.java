package com.infraguard.repository;

import com.infraguard.entity.Verification;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.Optional;

@Repository
public interface VerificationRepository extends JpaRepository<Verification, Long> {

    Optional<Verification> findByReportIdAndUserId(Long reportId, Long userId);

    boolean existsByReportIdAndUserId(Long reportId, Long userId);
}
