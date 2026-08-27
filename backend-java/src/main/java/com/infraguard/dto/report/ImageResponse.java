package com.infraguard.dto.report;

import lombok.Builder;
import lombok.Data;

import java.time.LocalDateTime;

@Data
@Builder
public class ImageResponse {
    private Long id;
    private String fileUrl;
    private Boolean isPrimary;
    private String caption;
    private Integer width;
    private Integer height;
    private LocalDateTime createdAt;
}
