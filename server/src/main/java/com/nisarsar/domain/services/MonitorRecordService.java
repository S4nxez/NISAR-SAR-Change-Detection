package com.nisarsar.domain.services;

import com.fasterxml.jackson.core.JsonProcessingException;
import com.fasterxml.jackson.databind.JsonNode;
import com.fasterxml.jackson.databind.ObjectMapper;
import com.nisarsar.dao.model.MonitorFile;
import com.nisarsar.dao.repositories.MonitorRecordRepository;
import com.nisarsar.domain.errors.UnsupportedCatalogError;
import org.springframework.http.MediaType;
import org.springframework.stereotype.Service;

import java.io.IOException;
import java.nio.file.Files;
import java.util.Map;
import java.util.Optional;

/**
 * The river lifeline record served to the web page: the catalog of an area and the images of its passes. The
 * processing worker (processing/lifeline) is the only writer; this service checks what it serves follows the layout
 * it knows. See docs/river-monitor.md for the contract.
 */
@Service
public class MonitorRecordService {
    /** catalog.json layout this backend serves; processing/lifeline/config.py SCHEMA_VERSION must match it. */
    public static final int SCHEMA_VERSION = 1;

    /** Files of a pass the page may load. The rest (water.npz, the packed water mask) stays internal. */
    static final Map<String, MediaType> PASS_LAYERS = Map.of(
            "radar.webp", MediaType.parseMediaType("image/webp"),
            "water.png", MediaType.IMAGE_PNG,
            "change.png", MediaType.IMAGE_PNG);

    private final MonitorRecordRepository repository;
    private final ObjectMapper objectMapper;

    public MonitorRecordService(MonitorRecordRepository repository, ObjectMapper objectMapper) {
        this.repository = repository;
        this.objectMapper = objectMapper;
    }

    public Optional<MonitorFile> findCatalog(String areaId) {
        return repository.findCatalog(areaId);
    }

    /** The catalog's JSON, as written by the worker, once checked to be valid and of the supported version. */
    public byte[] readCatalog(MonitorFile catalog) throws IOException {
        byte[] json = Files.readAllBytes(catalog.path());
        JsonNode root;
        try {
            root = objectMapper.readTree(json);
        } catch (JsonProcessingException e) {
            throw new UnsupportedCatalogError("The catalog is not valid JSON");
        }
        JsonNode version = root == null ? null : root.get("schema_version");
        if (version == null || !version.canConvertToInt() || version.asInt() != SCHEMA_VERSION) {
            throw new UnsupportedCatalogError("The catalog has schema_version " + version
                    + ", this backend serves version " + SCHEMA_VERSION
                    + ": deploy matching versions of the backend and the processing worker");
        }
        return json;
    }

    public Optional<MonitorFile> findPassLayer(String areaId, String passId, String layer) {
        if (!PASS_LAYERS.containsKey(layer)) {
            return Optional.empty();
        }
        return repository.findPassFile(areaId, passId, layer);
    }

    public MediaType mediaTypeOf(String layer) {
        return PASS_LAYERS.getOrDefault(layer, MediaType.APPLICATION_OCTET_STREAM);
    }
}
