package com.infraguard.repository;

import com.infraguard.entity.AdminAction;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

import java.util.List;

@Repository
public interface AdminActionRepository extends JpaRepository<AdminAction, Long> {
    List<AdminAction> findByReportIdOrderByCreatedAtDesc(Long reportId);
}
