package com.infraguard;

import com.infraguard.security.JwtTokenProvider;
import com.infraguard.config.AppProperties;
import org.junit.jupiter.api.Test;

import static org.junit.jupiter.api.Assertions.*;

class JwtTokenProviderTest {

    @Test
    void generateAndValidateAccessToken() {
        AppProperties props = new AppProperties();
        props.getJwt().setSecret("test_secret_for_jwt_validation_at_least_32_bytes_long_a1b2c3d4e5f6");
        props.getJwt().setAccessTokenExpirationMinutes(60);
        props.getJwt().setRefreshTokenExpirationDays(7);

        JwtTokenProvider provider = new JwtTokenProvider(props);

        String access = provider.generateAccessToken(42L, "citizen");
        assertTrue(provider.validateToken(access));
        assertEquals(42L, provider.getUserIdFromToken(access));
        assertEquals("citizen", provider.getRoleFromToken(access));
        assertEquals("access", provider.getTokenTypeFromToken(access));
    }

    @Test
    void generateAndValidateRefreshToken() {
        AppProperties props = new AppProperties();
        props.getJwt().setSecret("test_secret_for_jwt_validation_at_least_32_bytes_long_a1b2c3d4e5f6");
        props.getJwt().setAccessTokenExpirationMinutes(60);
        props.getJwt().setRefreshTokenExpirationDays(7);

        JwtTokenProvider provider = new JwtTokenProvider(props);

        String refresh = provider.generateRefreshToken(42L);
        assertTrue(provider.validateToken(refresh));
        assertEquals("refresh", provider.getTokenTypeFromToken(refresh));
        assertNull(provider.getRoleFromToken(refresh));
    }

    @Test
    void invalidToken_shouldReturnFalse() {
        AppProperties props = new AppProperties();
        props.getJwt().setSecret("test_secret_for_jwt_validation_at_least_32_bytes_long_a1b2c3d4e5f6");
        JwtTokenProvider provider = new JwtTokenProvider(props);

        assertFalse(provider.validateToken("invalid.token.here"));
        assertFalse(provider.validateToken(""));
    }
}
