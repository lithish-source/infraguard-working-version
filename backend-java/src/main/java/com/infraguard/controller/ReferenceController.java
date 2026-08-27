package com.infraguard.controller;

import com.infraguard.dto.common.MessageResponse;
import com.infraguard.entity.District;
import com.infraguard.entity.InfrastructureType;
import com.infraguard.repository.DistrictRepository;
import com.infraguard.repository.InfrastructureTypeRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;

import java.util.List;
import java.util.Map;
import java.util.stream.Collectors;

@RestController
@RequestMapping("/api/v1/reference")
@RequiredArgsConstructor
public class ReferenceController {

    private final InfrastructureTypeRepository infraTypeRepository;
    private final DistrictRepository districtRepository;

    @GetMapping("/infrastructure-types")
    public List<Map<String, Object>> infrastructureTypes() {
        return infraTypeRepository.findAll().stream()
            .sorted((a, b) -> a.getName().compareToIgnoreCase(b.getName()))
            .map(t -> Map.<String, Object>of(
                "id", t.getId(),
                "name", t.getName(),
                "code", t.getCode(),
                "description", t.getDescription() != null ? t.getDescription() : "",
                "default_priority_weight", t.getDefaultPriorityWeight(),
                "icon", t.getIcon() != null ? t.getIcon() : ""
            ))
            .collect(Collectors.toList());
    }

    @GetMapping("/districts")
    public List<Map<String, Object>> districts() {
        return districtRepository.findAll().stream()
            .sorted((a, b) -> a.getName().compareToIgnoreCase(b.getName()))
            .map(d -> Map.<String, Object>of(
                "id", d.getId(),
                "name", d.getName(),
                "code", d.getCode(),
                "state", d.getState() != null ? d.getState() : "",
                "population", d.getPopulation() != null ? d.getPopulation() : 0,
                "area_sq_km", d.getAreaSqKm() != null ? d.getAreaSqKm() : 0.0
            ))
            .collect(Collectors.toList());
    }
}
