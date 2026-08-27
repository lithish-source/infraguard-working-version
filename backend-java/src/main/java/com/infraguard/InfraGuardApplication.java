package com.infraguard;

import org.springframework.boot.SpringApplication;
import org.springframework.boot.autoconfigure.SpringBootApplication;
import org.springframework.scheduling.annotation.EnableAsync;

/**
 * InfraGuard Backend — Spring Boot 3.2 + Java 17.
 *
 * AI-Assisted Crowd-Sourced Community Infrastructure Damage Mapping
 * with Severity Prioritization.
 */
@SpringBootApplication
@EnableAsync
public class InfraGuardApplication {

    public static void main(String[] args) {
        SpringApplication.run(InfraGuardApplication.class, args);
    }
}
