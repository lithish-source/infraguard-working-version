package com.infraguard.repository;

import com.infraguard.entity.District;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.stereotype.Repository;

@Repository
public interface DistrictRepository extends JpaRepository<District, Long> {
    boolean existsByCode(String code);
}
