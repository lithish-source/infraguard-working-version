package com.infraguard.dto.admin;

import lombok.Data;

public class AdminDtos {

    @Data
    public static class StatusUpdateRequest {
        private String status;
        private String notes;
        private String assignedTeam;
    }

    @Data
    public static class SeverityUpdateRequest {
        private String severity;
        private String notes;
    }

    @Data
    public static class AssignTeamRequest {
        private String team;
        private String notes;
    }
}
