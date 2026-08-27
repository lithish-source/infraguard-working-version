package com.infraguard.service;

import com.infraguard.dto.notification.NotificationResponse;
import com.infraguard.entity.Notification;
import com.infraguard.entity.User;
import com.infraguard.repository.NotificationRepository;
import com.infraguard.repository.UserRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;
import org.springframework.transaction.annotation.Transactional;

import java.util.List;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class NotificationService {

    private final NotificationRepository notificationRepository;
    private final UserRepository userRepository;

    @Transactional(readOnly = true)
    public List<NotificationResponse> list(Long userId, boolean unreadOnly) {
        List<Notification> notifs = unreadOnly
            ? notificationRepository.findByUserIdAndIsReadFalseOrderByCreatedAtDesc(userId)
            : notificationRepository.findTop50ByUserIdOrderByCreatedAtDesc(userId);
        return notifs.stream().map(this::toResponse).collect(Collectors.toList());
    }

    @Transactional
    public void markRead(Long notificationId, Long userId) {
        Notification n = notificationRepository.findById(notificationId)
            .orElseThrow(() -> new com.infraguard.exception.GlobalExceptionHandler.ResourceNotFoundException(
                "Notification not found"));
        if (!n.getUser().getId().equals(userId)) {
            throw new com.infraguard.exception.GlobalExceptionHandler.BadRequestException(
                "Notification does not belong to user");
        }
        n.setIsRead(true);
        notificationRepository.save(n);
    }

    @Transactional
    public int markAllRead(Long userId) {
        return notificationRepository.markAllAsRead(userId);
    }

    private NotificationResponse toResponse(Notification n) {
        return NotificationResponse.builder()
            .id(n.getId())
            .title(n.getTitle())
            .message(n.getMessage())
            .type(n.getType())
            .isRead(n.getIsRead())
            .reportId(n.getReport() != null ? n.getReport().getId() : null)
            .createdAt(n.getCreatedAt())
            .build();
    }
}
