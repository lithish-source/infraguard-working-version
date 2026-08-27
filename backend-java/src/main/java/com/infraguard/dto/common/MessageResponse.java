package com.infraguard.dto.common;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class MessageResponse {
    private String message;
    private String detail;
}
