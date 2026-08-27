package com.infraguard.dto.report;

import jakarta.validation.constraints.NotBlank;
import jakarta.validation.constraints.NotNull;
import lombok.Data;

@Data
public class VerificationRequest {
    private String severityVote;  // optional
    private String comment;       // optional
    private Boolean isConfirmed = true;
}
