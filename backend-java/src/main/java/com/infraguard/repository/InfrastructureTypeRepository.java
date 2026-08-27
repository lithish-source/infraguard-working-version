package com.infraguard.repository;

import com.infraguard.entity.InfrastructureType;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface InfrastructureTypeRepository extends JpaRepository<InfrastructureType, Long> {
    boolean existsByCode(String code);
}
