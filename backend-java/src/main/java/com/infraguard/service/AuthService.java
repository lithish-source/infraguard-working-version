package com.infraguard.service;

import com.infraguard.config.AppProperties;
import com.infraguard.dto.auth.*;
import com.infraguard.entity.User;
import com.infraguard.repository.UserRepository;
import com.infraguard.security.JwtTokenProvider;
import lombok.RequiredArgsConstructor;
import lombok.extern.slf4j.Slf4j;
import org.springframework.security.authentication.AuthenticationManager;
import org.springframework.security.authentication.UsernamePasswordAuthenticationToken;
import org.springframework.security.core.Authentication;
import org.springframework.security.crypto.password.PasswordEncoder;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.time.LocalDateTime;

@Slf4j
@Service
@RequiredArgsConstructor
public class AuthService {

    private final UserRepository userRepository;
    private final PasswordEncoder passwordEncoder;
    private final JwtTokenProvider tokenProvider;
    private final AuthenticationManager authenticationManager;
    private final AppProperties appProperties;

    @Transactional
    public UserResponse register(UserCreateRequest req) {
        if (userRepository.existsByEmail(req.getEmail())) {
            throw new com.infraguard.exception.GlobalExceptionHandler.ConflictException(
                "A user with this email already exists.");
        }

        if (!req.getRole().equalsIgnoreCase("citizen") && !req.getRole().equalsIgnoreCase("official")) {
            throw new com.infraguard.exception.GlobalExceptionHandler.BadRequestException(
                "Role must be 'citizen' or 'official' (admins are seeded).");
        }

        User user = User.builder()
            .fullName(req.getFullName())
            .email(req.getEmail())
            .phone(req.getPhone())
            .passwordHash(passwordEncoder.encode(req.getPassword()))
            .role(req.getRole().toLowerCase())
            .isActive(true)
            .build();

        user = userRepository.save(user);
        return UserResponse.from(user);
    }

    public TokenResponse login(UserLoginRequest req) {
        User user = userRepository.findByEmail(req.getEmail())
            .orElseThrow(() -> new com.infraguard.exception.GlobalExceptionHandler.BadRequestException(
                "Invalid email or password."));

        if (!passwordEncoder.matches(req.getPassword(), user.getPasswordHash())) {
            throw new com.infraguard.exception.GlobalExceptionHandler.BadRequestException(
                "Invalid email or password.");
        }

        if (!user.getIsActive()) {
            throw new com.infraguard.exception.GlobalExceptionHandler.BadRequestException(
                "Account is deactivated. Contact an administrator.");
        }

        user.setLastLoginAt(LocalDateTime.now());
        userRepository.save(user);

        String access = tokenProvider.generateAccessToken(user.getId(), user.getRole());
        String refresh = tokenProvider.generateRefreshToken(user.getId());

        return TokenResponse.of(access, refresh,
            (int) (tokenProvider.getAccessTokenExpirationMs() / 1000),
            UserResponse.from(user));
    }

    public TokenResponse refresh(String refreshToken) {
        if (!tokenProvider.validateToken(refreshToken)
            || !"refresh".equals(tokenProvider.getTokenTypeFromToken(refreshToken))) {
            throw new com.infraguard.exception.GlobalExceptionHandler.BadRequestException(
                "Invalid refresh token.");
        }
        Long userId = tokenProvider.getUserIdFromToken(refreshToken);
        User user = userRepository.findById(userId)
            .orElseThrow(() -> new com.infraguard.exception.GlobalExceptionHandler.BadRequestException(
                "User not found."));

        if (!user.getIsActive()) {
            throw new com.infraguard.exception.GlobalExceptionHandler.BadRequestException(
                "Account is deactivated.");
        }

        String access = tokenProvider.generateAccessToken(user.getId(), user.getRole());
        String newRefresh = tokenProvider.generateRefreshToken(user.getId());
        return TokenResponse.of(access, newRefresh,
            (int) (tokenProvider.getAccessTokenExpirationMs() / 1000),
            UserResponse.from(user));
    }

    public User getUserByEmail(String email) {
        return userRepository.findByEmail(email)
            .orElseThrow(() -> new com.infraguard.exception.GlobalExceptionHandler.ResourceNotFoundException(
                "User not found: " + email));
    }
}
