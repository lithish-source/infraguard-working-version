package com.infraguard.repository;

import com.infraguard.entity.User;
import org.springframework.data.jpa.repository.JpaRepository;
import org.springframework.data.jpa.repository.Query;
import org.springframework.data.repository.query.Param;
import org.springframework.stereotype.Repository;

import java.util.List;
import java.util.Optional;

@Repository
public interface UserRepository extends JpaRepository<User, Long> {

    Optional<User> findByEmail(String email);

    List<User> findByRole(String role);

    boolean existsByEmail(String email);

    @Query("SELECT COUNT(u) FROM User u")
    long countTotal();

    @Query("SELECT COUNT(DISTINCT r.user.id) FROM Report r")
    long countActiveReporters();

    @Query("SELECT COUNT(DISTINCT v.user.id) FROM Verification v WHERE v.user IS NOT NULL")
    long countVerifiers();
}
