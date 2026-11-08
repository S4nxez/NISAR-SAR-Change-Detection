package com.nisarsar.ui;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nisarsar.dao.repositories.MonitorRecordRepository;
import com.nisarsar.domain.services.MonitorRecordService;
import com.nisarsar.ui.errors.GlobalExceptionHandler;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.springframework.http.HttpHeaders;
import org.springframework.test.web.servlet.MockMvc;
import org.springframework.test.web.servlet.setup.MockMvcBuilders;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.FileTime;
import java.time.Instant;
import java.time.ZoneOffset;
import java.time.format.DateTimeFormatter;

import static com.nisarsar.MonitorRecordFixtures.CATALOG;
import static com.nisarsar.MonitorRecordFixtures.PASS;
import static com.nisarsar.MonitorRecordFixtures.writeCatalog;
import static com.nisarsar.MonitorRecordFixtures.writePassFile;
import static org.hamcrest.Matchers.containsString;
import static org.springframework.test.web.servlet.request.MockMvcRequestBuilders.get;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.content;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.header;
import static org.springframework.test.web.servlet.result.MockMvcResultMatchers.status;

class MonitorControllerTest {
    private static final long WRITTEN = 1_700_000_000_000L;
    private static final String HTTP_DATE = DateTimeFormatter.RFC_1123_DATE_TIME
            .format(Instant.ofEpochMilli(WRITTEN).atZone(ZoneOffset.UTC));

    @TempDir
    Path root;

    private MockMvc mvc;

    @BeforeEach
    void setUp() {
        MonitorRecordService service = new MonitorRecordService(new MonitorRecordRepository(root), new ObjectMapper());
        mvc = MockMvcBuilders.standaloneSetup(new MonitorController(service))
                .setControllerAdvice(new GlobalExceptionHandler())
                .build();
    }

    private void writeCatalogAt(String json, long millis) throws IOException {
        Files.setLastModifiedTime(writeCatalog(root, "tefe", json), FileTime.fromMillis(millis));
    }

    @Test
    void servesTheCatalogOfAnArea() throws Exception {
        writeCatalogAt(CATALOG, WRITTEN);

        mvc.perform(get("/api/monitor/areas/tefe"))
                .andExpect(status().isOk())
                .andExpect(content().contentType("application/json"))
                .andExpect(content().bytes(CATALOG.getBytes(StandardCharsets.UTF_8)))
                .andExpect(header().string(HttpHeaders.CACHE_CONTROL, "no-cache"))
                .andExpect(header().string(HttpHeaders.LAST_MODIFIED, HTTP_DATE));
    }

    @Test
    void answersNotModifiedWhileTheCatalogHasNotChanged() throws Exception {
        writeCatalogAt(CATALOG, WRITTEN);

        mvc.perform(get("/api/monitor/areas/tefe").header(HttpHeaders.IF_MODIFIED_SINCE, HTTP_DATE))
                .andExpect(status().isNotModified())
                .andExpect(content().bytes(new byte[0]));
    }

    @Test
    void servesTheCatalogAgainOnceTheWorkerRewritesIt() throws Exception {
        writeCatalogAt(CATALOG, WRITTEN + 60_000);

        mvc.perform(get("/api/monitor/areas/tefe").header(HttpHeaders.IF_MODIFIED_SINCE, HTTP_DATE))
                .andExpect(status().isOk());
    }

    @Test
    void anAreaWithoutRecordIsNotFound() throws Exception {
        mvc.perform(get("/api/monitor/areas/tefe")).andExpect(status().isNotFound());
        mvc.perform(get("/api/monitor/areas/..%2Fsecret")).andExpect(status().isNotFound());
    }

    @Test
    void aCatalogOfAnotherVersionIsUnavailableNotBroken() throws Exception {
        writeCatalogAt("{\"schema_version\":99}", WRITTEN);

        mvc.perform(get("/api/monitor/areas/tefe"))
                .andExpect(status().isServiceUnavailable())
                .andExpect(content().string(containsString("schema_version 99")));
    }

    @Test
    void servesTheImagesOfAPass() throws Exception {
        Path image = writePassFile(root, "tefe", PASS, "radar.webp", new byte[]{82, 73, 70, 70});
        Files.setLastModifiedTime(image, FileTime.fromMillis(WRITTEN));

        mvc.perform(get("/api/monitor/areas/tefe/passes/{pass}/radar.webp", PASS))
                .andExpect(status().isOk())
                .andExpect(content().contentType("image/webp"))
                .andExpect(content().bytes(new byte[]{82, 73, 70, 70}))
                .andExpect(header().string(HttpHeaders.CACHE_CONTROL, "max-age=3600"))
                .andExpect(header().string(HttpHeaders.LAST_MODIFIED, HTTP_DATE));
        mvc.perform(get("/api/monitor/areas/tefe/passes/{pass}/radar.webp", PASS)
                        .header(HttpHeaders.IF_MODIFIED_SINCE, HTTP_DATE))
                .andExpect(status().isNotModified());
    }

    @Test
    void servesPngLayersAsPng() throws Exception {
        writePassFile(root, "tefe", PASS, "water.png", new byte[]{1});

        mvc.perform(get("/api/monitor/areas/tefe/passes/{pass}/water.png", PASS))
                .andExpect(status().isOk())
                .andExpect(content().contentType("image/png"));
    }

    @Test
    void internalAndMissingFilesOfAPassAreNotFound() throws Exception {
        writePassFile(root, "tefe", PASS, "water.npz", new byte[]{1});

        mvc.perform(get("/api/monitor/areas/tefe/passes/{pass}/water.npz", PASS)).andExpect(status().isNotFound());
        mvc.perform(get("/api/monitor/areas/tefe/passes/{pass}/change.png", PASS)).andExpect(status().isNotFound());
        mvc.perform(get("/api/monitor/areas/tefe/passes/2026-01-01_t001A/radar.webp")).andExpect(status().isNotFound());
    }
}
