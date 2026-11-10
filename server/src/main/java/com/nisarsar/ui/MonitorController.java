package com.nisarsar.ui;

import com.nisarsar.common.Constants;
import com.nisarsar.dao.model.MonitorFile;
import com.nisarsar.domain.services.MonitorRecordService;
import org.springframework.core.io.FileSystemResource;
import org.springframework.core.io.Resource;
import org.springframework.http.CacheControl;
import org.springframework.http.HttpStatus;
import org.springframework.http.MediaType;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.context.request.WebRequest;
import org.springframework.web.server.ResponseStatusException;

import java.io.IOException;
import java.time.Duration;

/**
 * River lifeline monitor API: the record the processing worker publishes, for the web page.
 * <ul>
 *   <li>GET /api/monitor/areas/{area}: catalog.json of the area (no-cache: the page polls it for new passes, and
 *   gets 304 Not Modified while it has not changed)</li>
 *   <li>GET /api/monitor/areas/{area}/passes/{pass}/{layer}: radar.webp, water.png or change.png of a pass</li>
 * </ul>
 */
@RestController
@RequestMapping(Constants.API + Constants.MONITOR + Constants.AREAS)
public class MonitorController {
    /** A pass's images only change when the worker re-evaluates the record. */
    static final Duration LAYER_MAX_AGE = Duration.ofHours(1);

    private final MonitorRecordService monitorRecordService;

    public MonitorController(MonitorRecordService monitorRecordService) {
        this.monitorRecordService = monitorRecordService;
    }

    @GetMapping("/{areaId}")
    public ResponseEntity<byte[]> getCatalog(@PathVariable String areaId, WebRequest request) throws IOException {
        MonitorFile catalog = monitorRecordService.findCatalog(areaId)
                .orElseThrow(() -> notFound("No pass record for area " + areaId));
        if (request.checkNotModified(catalog.lastModified())) {
            return null;   // 304, answered by checkNotModified
        }
        return ResponseEntity.ok()
                .cacheControl(CacheControl.noCache())
                .lastModified(catalog.lastModified())
                .contentType(MediaType.APPLICATION_JSON)
                .body(monitorRecordService.readCatalog(catalog));
    }

    @GetMapping("/{areaId}" + Constants.PASSES + "/{passId}/{layer:.+}")
    public ResponseEntity<Resource> getPassLayer(@PathVariable String areaId, @PathVariable String passId,
                                                 @PathVariable String layer, WebRequest request) {
        MonitorFile file = monitorRecordService.findPassLayer(areaId, passId, layer)
                .orElseThrow(() -> notFound("No " + layer + " for pass " + passId + " of area " + areaId));
        if (request.checkNotModified(file.lastModified())) {
            return null;
        }
        return ResponseEntity.ok()
                .cacheControl(CacheControl.maxAge(LAYER_MAX_AGE))
                .lastModified(file.lastModified())
                .contentType(monitorRecordService.mediaTypeOf(layer))
                .body(new FileSystemResource(file.path()));
    }

    private static ResponseStatusException notFound(String message) {
        return new ResponseStatusException(HttpStatus.NOT_FOUND, message);
    }
}
