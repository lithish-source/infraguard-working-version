package com.infraguard.controller;

import com.infraguard.dto.common.MessageResponse;
import com.infraguard.dto.notification.NotificationResponse;
import com.infraguard.entity.User;
import com.infraguard.security.CustomUserDetailsService;
import com.infraguard.service.NotificationService;
import lombok.RequiredArgsConstructor;
import org.springframework.security.core.annotation.AuthenticationPrincipal;
import org.springframework.security.core.userdetails.UserDetails;
import org.springframework.web.bind.annotation.*;

import java.util.List;
import java.util.Map;

@RestController
@RequestMapping("/api/v1/notifications")
@RequiredArgsConstructor
public class NotificationController {

    private final NotificationService notificationService;
    private final CustomUserDetailsService userDetailsService;

    @GetMapping
    public List<NotificationResponse> list(
        @RequestParam(defaultValue = "false") boolean unread_only,
        @AuthenticationPrincipal UserDetails principal
    ) {
        User user = userDetailsService.loadUserEntityByEmail(principal.getUsername());
        return notificationService.list(user.getId(), unread_only);
    }

    @PostMapping("/{id}/read")
    public MessageResponse markRead(
        @PathVariable Long id,
        @AuthenticationPrincipal UserDetails principal
    ) {
        User user = userDetailsService.loadUserEntityByEmail(principal.getUsername());
        notificationService.markRead(id, user.getId());
        return MessageResponse.builder().message("Marked as read.").build();
    }

    @PostMapping("/read-all")
    public Map<String, Object> markAllRead(@AuthenticationPrincipal UserDetails principal) {
        User user = userDetailsService.loadUserEntityByEmail(principal.getUsername());
        int n = notificationService.markAllRead(user.getId());
        return Map.of("message", "Marked " + n + " notifications as read.");
    }
}
