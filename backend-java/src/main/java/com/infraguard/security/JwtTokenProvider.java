package com.infraguard.security;

import com.infraguard.config.AppProperties;
import io.jsonwebtoken.*;
import io.jsonwebtoken.security.Keys;
import lombok.extern.slf4j.Slf4j;
import org.springframework.stereotype.Component;

import javax.crypto.SecretKey;
import java.nio.charset.StandardCharsets;
import java.util.Date;
import java.util.HashMap;
import java.util.Map;

/**
 * JWT token provider — generates and validates access/refresh tokens.
 *
 * Uses HS256 with a secret loaded from application.yml.
 */
@Slf4j
@Component
public class JwtTokenProvider {

    private final SecretKey secretKey;
    private final long accessTokenExpirationMs;
    private final long refreshTokenExpirationMs;

    public JwtTokenProvider(AppProperties props) {
        this.secretKey = Keys.hmacShaKeyFor(
            props.getJwt().getSecret().getBytes(StandardCharsets.UTF_8)
        );
        this.accessTokenExpirationMs = props.getJwt().getAccessTokenExpirationMinutes() * 60_000L;
        this.refreshTokenExpirationMs = props.getJwt().getRefreshTokenExpirationDays() * 86_400_000L;
    }

    public String generateAccessToken(Long userId, String role) {
        return buildToken(userId, role, "access", accessTokenExpirationMs);
    }

    public String generateRefreshToken(Long userId) {
        return buildToken(userId, null, "refresh", refreshTokenExpirationMs);
    }

    private String buildToken(Long userId, String role, String type, long expirationMs) {
        Date now = new Date();
        Date expiry = new Date(now.getTime() + expirationMs);

        Map<String, Object> claims = new HashMap<>();
        claims.put("type", type);
        if (role != null) claims.put("role", role);

        return Jwts.builder()
                .claims(claims)
                .subject(String.valueOf(userId))
                .issuedAt(now)
                .expiration(expiry)
                .signWith(secretKey)
                .compact();
    }

    public boolean validateToken(String token) {
        try {
            Jwts.parser()
                .verifyWith(secretKey)
                .build()
                .parseSignedClaims(token);
            return true;
        } catch (ExpiredJwtException e) {
            log.debug("JWT expired: {}", e.getMessage());
        } catch (JwtException e) {
            log.debug("Invalid JWT: {}", e.getMessage());
        }
        return false;
    }

    public Claims getClaims(String token) {
        return Jwts.parser()
            .verifyWith(secretKey)
            .build()
            .parseSignedClaims(token)
            .getPayload();
    }

    public Long getUserIdFromToken(String token) {
        return Long.parseLong(getClaims(token).getSubject());
    }

    public String getRoleFromToken(String token) {
        return getClaims(token).get("role", String.class);
    }

    public String getTokenTypeFromToken(String token) {
        return getClaims(token).get("type", String.class);
    }

    public long getAccessTokenExpirationMs() {
        return accessTokenExpirationMs;
    }
}
