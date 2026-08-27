package com.infraguard.dto.auth;

import lombok.Builder;
import lombok.Data;

@Data
@Builder
public class TokenResponse {
    private String accessToken;
    private String refreshToken;
    private String tokenType;
    private int expiresIn;
    private UserResponse user;

    public static TokenResponse of(String access, String refresh, int expiresInSeconds, UserResponse user) {
        return TokenResponse.builder()
            .accessToken(access)
            .refreshToken(refresh)
            .tokenType("bearer")
            .expiresIn(expiresInSeconds)
            .user(user)
            .build();
    }
}
