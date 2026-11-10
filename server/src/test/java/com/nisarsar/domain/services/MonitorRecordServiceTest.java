package com.nisarsar.domain.services;

import com.fasterxml.jackson.databind.ObjectMapper;
import com.nisarsar.dao.model.MonitorFile;
import com.nisarsar.dao.repositories.MonitorRecordRepository;
import com.nisarsar.domain.errors.UnsupportedCatalogError;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.ValueSource;
import org.springframework.http.MediaType;

import java.io.IOException;
import java.nio.charset.StandardCharsets;
import java.nio.file.Path;

import static com.nisarsar.MonitorRecordFixtures.CATALOG;
import static com.nisarsar.MonitorRecordFixtures.PASS;
import static com.nisarsar.MonitorRecordFixtures.writeCatalog;
import static com.nisarsar.MonitorRecordFixtures.writePassFile;
import static org.assertj.core.api.Assertions.assertThat;
import static org.assertj.core.api.Assertions.assertThatThrownBy;

class MonitorRecordServiceTest {
    @TempDir
    Path root;

    private MonitorRecordService service;

    @BeforeEach
    void setUp() {
        service = new MonitorRecordService(new MonitorRecordRepository(root), new ObjectMapper());
    }

    private MonitorFile catalog(String json) throws IOException {
        writeCatalog(root, "tefe", json);
        return service.findCatalog("tefe").orElseThrow();
    }

    @Test
    void servesTheCatalogBytesAsWritten() throws IOException {
        byte[] served = service.readCatalog(catalog(CATALOG));

        assertThat(new String(served, StandardCharsets.UTF_8)).isEqualTo(CATALOG);
    }

    @ParameterizedTest
    @ValueSource(strings = {
            "{\"schema_version\":2,\"passes\":[]}",
            "{\"schema_version\":0}",
            "{\"schema_version\":\"one\"}",
            "{\"passes\":[]}",
            "[]",
            "null"})
    void refusesACatalogOfAnotherOrNoVersion(String json) throws IOException {
        MonitorFile file = catalog(json);

        assertThatThrownBy(() -> service.readCatalog(file))
                .isInstanceOf(UnsupportedCatalogError.class)
                .hasMessageContaining("this backend serves version " + MonitorRecordService.SCHEMA_VERSION);
    }

    @Test
    void refusesACatalogThatIsNotJson() throws IOException {
        MonitorFile file = catalog("{\"schema_version\":1,");

        assertThatThrownBy(() -> service.readCatalog(file))
                .isInstanceOf(UnsupportedCatalogError.class)
                .hasMessage("The catalog is not valid JSON");
    }

    @Test
    void servesTheImagesOfAPass() throws IOException {
        for (String layer : new String[]{"radar.webp", "water.png", "change.png"}) {
            writePassFile(root, "tefe", PASS, layer, new byte[]{1});
            assertThat(service.findPassLayer("tefe", PASS, layer)).as(layer).isPresent();
        }
        assertThat(service.mediaTypeOf("radar.webp")).isEqualTo(MediaType.parseMediaType("image/webp"));
        assertThat(service.mediaTypeOf("water.png")).isEqualTo(MediaType.IMAGE_PNG);
        assertThat(service.mediaTypeOf("change.png")).isEqualTo(MediaType.IMAGE_PNG);
    }

    @Test
    void keepsTheOtherFilesOfAPassInternal() throws IOException {
        writePassFile(root, "tefe", PASS, "water.npz", new byte[]{1});
        writePassFile(root, "tefe", PASS, "notes.txt", new byte[]{1});

        assertThat(service.findPassLayer("tefe", PASS, "water.npz")).isEmpty();
        assertThat(service.findPassLayer("tefe", PASS, "notes.txt")).isEmpty();
        assertThat(service.mediaTypeOf("water.npz")).isEqualTo(MediaType.APPLICATION_OCTET_STREAM);
    }

    @Test
    void aMissingImageIsMissing() {
        assertThat(service.findPassLayer("tefe", PASS, "change.png")).isEmpty();
    }
}
