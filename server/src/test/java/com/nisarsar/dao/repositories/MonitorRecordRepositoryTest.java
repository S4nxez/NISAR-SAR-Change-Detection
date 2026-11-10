package com.nisarsar.dao.repositories;

import com.nisarsar.dao.model.MonitorFile;
import org.junit.jupiter.api.BeforeEach;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.io.TempDir;
import org.junit.jupiter.params.ParameterizedTest;
import org.junit.jupiter.params.provider.NullAndEmptySource;
import org.junit.jupiter.params.provider.ValueSource;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.nio.file.attribute.FileTime;

import static com.nisarsar.MonitorRecordFixtures.CATALOG;
import static com.nisarsar.MonitorRecordFixtures.PASS;
import static com.nisarsar.MonitorRecordFixtures.writeCatalog;
import static com.nisarsar.MonitorRecordFixtures.writePassFile;
import static org.assertj.core.api.Assertions.assertThat;

class MonitorRecordRepositoryTest {
    @TempDir
    Path root;

    private MonitorRecordRepository repository;

    @BeforeEach
    void setUp() {
        repository = new MonitorRecordRepository(root.resolve("data"));
    }

    @Test
    void findsTheCatalogOfAnAreaWithItsModificationTime() throws IOException {
        Path catalog = writeCatalog(root.resolve("data"), "tefe", CATALOG);
        Files.setLastModifiedTime(catalog, FileTime.fromMillis(1_700_000_000_000L));

        assertThat(repository.findCatalog("tefe"))
                .contains(new MonitorFile(catalog.toAbsolutePath().normalize(), 1_700_000_000_000L));
    }

    @Test
    void anAreaWithoutCatalogIsMissing() throws IOException {
        Files.createDirectories(root.resolve("data/tefe"));

        assertThat(repository.findCatalog("tefe")).isEmpty();
        assertThat(repository.findCatalog("other")).isEmpty();
    }

    @Test
    void aMissingDataFolderIsNotAnError() {
        assertThat(repository.findCatalog("tefe")).isEmpty();
        assertThat(repository.findPassFile("tefe", PASS, "radar.webp")).isEmpty();
    }

    @ParameterizedTest
    @NullAndEmptySource
    @ValueSource(strings = {"..", "../data/tefe", "tefe/..", "te fe", "tefe%2F..", "a/b", "C:", "x12345678901234567890123456789012345678901234567890123456789012345"})
    void onlyPlainAreaNamesAreLookedUp(String area) throws IOException {
        writeCatalog(root, "secret", CATALOG);   // next to the data folder: must never be reachable
        writeCatalog(root.resolve("data"), "tefe", CATALOG);

        assertThat(repository.findCatalog(area)).isEmpty();
    }

    @Test
    void findsAFileOfAPass() throws IOException {
        Path image = writePassFile(root.resolve("data"), "tefe", PASS, "radar.webp", new byte[]{1, 2});

        assertThat(repository.findPassFile("tefe", PASS, "radar.webp")).get()
                .extracting(MonitorFile::path).isEqualTo(image.toAbsolutePath().normalize());
    }

    @ParameterizedTest
    @ValueSource(strings = {"../catalog.json", "..", "radar", ".webp", "radar.webp/..", "radar.WEBP.png.x.y", ""})
    void onlyPlainFileNamesOfAPassAreLookedUp(String name) throws IOException {
        writePassFile(root.resolve("data"), "tefe", PASS, "radar.webp", new byte[]{1});
        writeCatalog(root.resolve("data"), "tefe", CATALOG);

        assertThat(repository.findPassFile("tefe", PASS, name)).isEmpty();
    }

    @Test
    void aFolderIsNotAFile() throws IOException {
        Files.createDirectories(root.resolve("data/tefe/passes").resolve(PASS).resolve("radar.webp"));

        assertThat(repository.findPassFile("tefe", PASS, "radar.webp")).isEmpty();
    }

    @Test
    void passIdsAreCheckedLikeAreaIds() throws IOException {
        writePassFile(root.resolve("data"), "tefe", PASS, "radar.webp", new byte[]{1});

        assertThat(repository.findPassFile("tefe", "..", "radar.webp")).isEmpty();
        assertThat(repository.findPassFile("..", PASS, "radar.webp")).isEmpty();
        assertThat(repository.findPassFile("tefe", PASS, null)).isEmpty();
    }
}
