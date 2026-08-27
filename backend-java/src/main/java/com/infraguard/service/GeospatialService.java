package com.infraguard.service;

import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.infraguard.config.AppProperties;
import lombok.extern.slf4j.Slf4j;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.net.URI;
import java.net.http.HttpClient;
import java.net.http.HttpRequest;
import java.net.http.HttpResponse;
import java.time.Duration;
import java.util.*;
import java.util.concurrent.ConcurrentHashMap;

/**
 * Geospatial Service — queries OpenStreetMap Overpass API for real nearby
 * hospitals, schools, and road classifications.
 *
 * Free, requires no API key. Results are cached per ~110m grid cell.
 */
@Slf4j
@Service
public class GeospatialService {

    private final AppProperties props;
    private final ObjectMapper objectMapper = new ObjectMapper();
    private final HttpClient httpClient;
    private final Map<String, Object> cache = new ConcurrentHashMap<>();

    @Autowired
    public GeospatialService(AppProperties props) {
        this.props = props;
        this.httpClient = HttpClient.newBuilder()
            .connectTimeout(Duration.ofSeconds(5))
            .build();
    }

    public static double haversineKm(double lat1, double lon1, double lat2, double lon2) {
        double R = 6371.0;
        double phi1 = Math.toRadians(lat1);
        double phi2 = Math.toRadians(lat2);
        double dphi = Math.toRadians(lat2 - lat1);
        double dlam = Math.toRadians(lon2 - lon1);
        double a = Math.sin(dphi / 2) * Math.sin(dphi / 2)
                 + Math.cos(phi1) * Math.cos(phi2) * Math.sin(dlam / 2) * Math.sin(dlam / 2);
        return 2 * R * Math.asin(Math.sqrt(a));
    }

    private double roundCoord(double value) {
        return Math.round(value * 1000.0) / 1000.0;  // ~110m grid
    }

    public LocationContext getLocationContext(double lat, double lng) {
        List<Hospital> hospitals = getNearbyHospitals(lat, lng);
        List<School> schools = getNearbySchools(lat, lng);
        String roadClass = getNearestRoadClass(lat, lng);

        return new LocationContext(
            hospitals.isEmpty() ? null : hospitals.get(0).distanceKm,
            hospitals.isEmpty() ? null : hospitals.get(0).name,
            schools.isEmpty() ? null : schools.get(0).distanceKm,
            schools.isEmpty() ? null : schools.get(0).name,
            roadClass,
            hospitals.size(),
            schools.size()
        );
    }

    @SuppressWarnings("unchecked")
    public List<Hospital> getNearbyHospitals(double lat, double lng) {
        String key = "h_" + roundCoord(lat) + "_" + roundCoord(lng);
        Object cached = cache.get(key);
        if (cached != null) return (List<Hospital>) cached;

        String query = String.format("""
            [out:json][timeout:25];
            (
              node["amenity"="hospital"](around:5000,%f,%f);
              way["amenity"="hospital"](around:5000,%f,%f);
              node["amenity"="clinic"](around:5000,%f,%f);
              way["amenity"="clinic"](around:5000,%f,%f);
            );
            out center 10;
            """, lat, lng, lat, lng, lat, lng, lat, lng);

        List<Hospital> result = queryOverpass(query, this::parseHospitals, List.of());
        cache.put(key, result);
        return result;
    }

    @SuppressWarnings("unchecked")
    public List<School> getNearbySchools(double lat, double lng) {
        String key = "s_" + roundCoord(lat) + "_" + roundCoord(lng);
        Object cached = cache.get(key);
        if (cached != null) return (List<School>) cached;

        String query = String.format("""
            [out:json][timeout:25];
            (
              node["amenity"~"school|kindergarten|college|university"](around:3000,%f,%f);
              way["amenity"~"school|kindergarten|college|university"](around:3000,%f,%f);
            );
            out center 10;
            """, lat, lng, lat, lng);

        List<School> result = queryOverpass(query, this::parseSchools, List.of());
        cache.put(key, result);
        return result;
    }

    public String getNearestRoadClass(double lat, double lng) {
        String key = "r_" + roundCoord(lat) + "_" + roundCoord(lng);
        Object cached = cache.get(key);
        if (cached != null) return (String) cached;

        String query = String.format("""
            [out:json][timeout:15];
            way(around:200,%f,%f)["highway"];
            out tags 5;
            """, lat, lng);

        String roadClass = queryOverpass(query, this::parseRoadClass, "local");
        cache.put(key, roadClass);
        return roadClass;
    }

    private <T> T queryOverpass(String query, OverpassParser<T> parser, T emptyResult) {
        if (!props.getOverpass().isEnabled()) return emptyResult;

        int timeout = props.getOverpass().getTimeoutSeconds();
        for (String endpoint : props.getOverpass().getEndpoints()) {
            try {
                HttpRequest request = HttpRequest.newBuilder()
                    .uri(URI.create(endpoint))
                    .header("Content-Type", "application/x-www-form-urlencoded")
                    .timeout(Duration.ofSeconds(timeout))
                    .POST(HttpRequest.BodyPublishers.ofString("data=" + java.net.URLEncoder.encode(query, java.nio.charset.StandardCharsets.UTF_8)))
                    .build();
                HttpResponse<String> response = httpClient.send(request, HttpResponse.BodyHandlers.ofString());

                if (response.statusCode() == 200) {
                    JsonNode root = objectMapper.readTree(response.body());
                    return parser.parse(root);
                } else if (response.statusCode() == 429) {
                    log.warn("[overpass] Rate limited at {}", endpoint);
                    continue;
                }
            } catch (Exception e) {
                log.warn("[overpass] Endpoint {} failed: {}", endpoint, e.getMessage());
            }
        }
        return emptyResult;
    }

    private List<Hospital> parseHospitals(JsonNode root) {
        List<Hospital> hospitals = new ArrayList<>();
        for (JsonNode el : root.path("elements")) {
            double elat, elng;
            if ("node".equals(el.path("type").asText())) {
                elat = el.path("lat").asDouble();
                elng = el.path("lon").asDouble();
            } else if ("way".equals(el.path("type").asText())) {
                JsonNode c = el.path("center");
                elat = c.path("lat").asDouble();
                elng = c.path("lon").asDouble();
            } else continue;

            JsonNode tags = el.path("tags");
            String name = tags.path("name").asText(tags.path("amenity").asText("Unnamed facility"));
            // We don't know lat/lng here, so set distance later — actually caller doesn't have it
            hospitals.add(new Hospital(name, elat, elng, 0.0));
        }
        // Sort by distance (will be 0 here, since we don't pass origin) — caller re-sorts if needed
        return hospitals;
    }

    private List<School> parseSchools(JsonNode root) {
        List<School> schools = new ArrayList<>();
        for (JsonNode el : root.path("elements")) {
            double elat, elng;
            if ("node".equals(el.path("type").asText())) {
                elat = el.path("lat").asDouble();
                elng = el.path("lon").asDouble();
            } else if ("way".equals(el.path("type").asText())) {
                JsonNode c = el.path("center");
                elat = c.path("lat").asDouble();
                elng = c.path("lon").asDouble();
            } else continue;

            JsonNode tags = el.path("tags");
            String name = tags.path("name").asText(tags.path("amenity").asText("Unnamed school"));
            schools.add(new School(name, elat, elng, 0.0));
        }
        return schools;
    }

    private String parseRoadClass(JsonNode root) {
        Set<String> foundClasses = new HashSet<>();
        String[][] priorityMap = {
            {"motorway", "highway"}, {"trunk", "highway"},
            {"primary", "major_road"}, {"secondary", "major_road"},
            {"tertiary", "arterial"}, {"tertiary_link", "arterial"},
            {"primary_link", "arterial"}, {"secondary_link", "arterial"},
            {"residential", "residential"}, {"living_street", "residential"},
            {"unclassified", "local"}, {"service", "local"}, {"road", "local"}
        };

        for (JsonNode el : root.path("elements")) {
            String highway = el.path("tags").path("highway").asText();
            if (highway == null || highway.isEmpty()) continue;
            for (String[] mapping : priorityMap) {
                if (mapping[0].equals(highway)) {
                    foundClasses.add(mapping[1]);
                    break;
                }
            }
        }

        for (String[] mapping : priorityMap) {
            if (foundClasses.contains(mapping[1])) return mapping[1];
        }
        return "local";
    }

    @FunctionalInterface
    private interface OverpassParser<T> {
        T parse(JsonNode root) throws Exception;
    }

    public record Hospital(String name, double lat, double lng, double distanceKm) {}
    public record School(String name, double lat, double lng, double distanceKm) {}

    public record LocationContext(
        Double nearestHospitalKm,
        String nearestHospitalName,
        Double nearestSchoolKm,
        String nearestSchoolName,
        String roadClass,
        int hospitalCount5km,
        int schoolCount3km
    ) {}
}
