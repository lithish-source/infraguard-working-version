package com.infraguard.config;

import com.infraguard.entity.*;
import com.infraguard.repository.*;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.boot.ApplicationArguments;
import org.springframework.boot.ApplicationRunner;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Component;

import java.util.List;

/**
 * Seeds the database on first startup with:
 *   - Default admin user (if not exists)
 *   - 10 infrastructure types
 *   - 5 demo districts (Pune area, India)
 *   - 8 demo citizen accounts (deterministic emails matching frontend quick-logins)
 *
 * The seed is idempotent — safe to run multiple times.
 */
@Slf4j
@Component
@RequiredArgsConstructor
public class DataSeeder implements ApplicationRunner {

    private final UserRepository userRepository;
    private final DistrictRepository districtRepository;
    private final InfrastructureTypeRepository infraTypeRepository;
    private final PasswordEncoder passwordEncoder;
    private final AppProperties appProperties;

    @Override
    public void run(ApplicationArguments args) {
        long start = System.currentTimeMillis();
        seedInfrastructureTypes();
        seedDistricts();
        seedAdmin();
        seedDemoCitizens();
        log.info("[seed] Seeding complete in {}ms", System.currentTimeMillis() - start);
    }

    private void seedInfrastructureTypes() {
        if (infraTypeRepository.count() > 0) return;

        Object[][] types = {
            {"Road", "ROAD", "Surface roads including potholes, cracks, subsidence", 7.0, "road"},
            {"Bridge", "BRIDGE", "Bridges, overpasses, flyovers", 9.5, "bridge"},
            {"Drainage System", "DRAINAGE", "Storm drains, culverts, canals", 6.0, "water"},
            {"Streetlight", "STREETLIGHT", "Public street lighting", 4.0, "lightbulb"},
            {"Water Pipeline", "WATER", "Public water supply pipelines", 8.5, "faucet"},
            {"Public Building", "BUILDING", "Government offices, schools, hospitals", 7.5, "building"},
            {"Traffic Signal", "TRAFFIC", "Traffic lights and signaling", 8.0, "traffic"},
            {"Footpath", "FOOTPATH", "Pedestrian walkways", 3.5, "walking"},
            {"Public Toilet", "TOILET", "Sanitation facilities", 3.0, "restroom"},
            {"Park Equipment", "PARK", "Benches, playground equipment", 2.5, "tree"}
        };
        for (Object[] t : types) {
            infraTypeRepository.save(InfrastructureType.builder()
                .name((String) t[0])
                .code((String) t[1])
                .description((String) t[2])
                .defaultPriorityWeight((Double) t[3])
                .icon((String) t[4])
                .build());
        }
        log.info("[seed] Created {} infrastructure types", types.length);
    }

    private void seedDistricts() {
        if (districtRepository.count() > 0) return;

        Object[][] districts = {
            {"Central District", "CD", "Maharashtra", 850000, 75.0},
            {"North District",   "ND", "Maharashtra", 620000, 92.0},
            {"South District",   "SD", "Maharashtra", 730000, 88.0},
            {"East District",    "ED", "Maharashtra", 540000, 110.0},
            {"West District",    "WD", "Maharashtra", 690000, 84.0}
        };
        for (Object[] d : districts) {
            districtRepository.save(District.builder()
                .name((String) d[0])
                .code((String) d[1])
                .state((String) d[2])
                .population((Integer) d[3])
                .areaSqKm((Double) d[4])
                .build());
        }
        log.info("[seed] Created {} districts", districts.length);
    }

    private void seedAdmin() {
        // ALWAYS update the password (in case seed.sql created a placeholder)
        User existing = userRepository.findByEmail(appProperties.getDefaultAdmin().getEmail()).orElse(null);
        String correctHash = passwordEncoder.encode(appProperties.getDefaultAdmin().getPassword());

        if (existing != null) {
            existing.setFullName(appProperties.getDefaultAdmin().getName());
            existing.setPasswordHash(correctHash);
            existing.setRole("admin");
            existing.setIsActive(true);
            userRepository.save(existing);
            log.info("[seed] Updated admin password for {}", existing.getEmail());
        } else {
            userRepository.save(User.builder()
                .fullName(appProperties.getDefaultAdmin().getName())
                .email(appProperties.getDefaultAdmin().getEmail())
                .passwordHash(correctHash)
                .role("admin")
                .isActive(true)
                .build());
            log.info("[seed] Created admin user: {}", appProperties.getDefaultAdmin().getEmail());
        }
    }

    private void seedDemoCitizens() {
        long existing = userRepository.findByRole("citizen").size();
        if (existing >= 8) return;

        // Deterministic list — index 0 must match the frontend's quick-login button
        String[][] fixed = {
            {"Aarav", "Sharma"},
            {"Diya", "Patel"},
            {"Vihaan", "Reddy"},
            {"Ananya", "Iyer"},
            {"Arjun", "Nair"},
            {"Ishaan", "Kapoor"},
            {"Saanvi", "Singh"},
            {"Kabir", "Mehta"}
        };

        String hashedPassword = passwordEncoder.encode("Citizen@12345");
        int created = 0;
        for (int i = 0; i < fixed.length; i++) {
            String fn = fixed[i][0];
            String ln = fixed[i][1];
            String email = fn.toLowerCase() + "." + ln.toLowerCase() + i + "@example.com";
            if (userRepository.existsByEmail(email)) continue;

            List<District> districts = districtRepository.findAll();
            District district = districts.isEmpty() ? null : districts.get(i % districts.size());

            userRepository.save(User.builder()
                .fullName(fn + " " + ln)
                .email(email)
                .phone("+9198765" + String.format("%05d", 43210 - i))
                .passwordHash(hashedPassword)
                .role("citizen")
                .isActive(true)
                .district(district)
                .build());
            created++;
        }
        log.info("[seed] Created {} demo citizens", created);
    }
}
