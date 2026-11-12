package com.nisarsar;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;

/** A river lifeline record on disk, laid out as processing/lifeline writes it, for the monitor tests. */
public final class MonitorRecordFixtures {
    public static final String PASS = "2026-10-23_t161A";
    public static final String CATALOG = "{\"schema_version\":1,\"area\":{\"id\":\"tefe\",\"name\":\"Lake Tefé\"},"
            + "\"status_codes\":{\"0\":\"no_data\",\"1\":\"connected\",\"2\":\"at_risk\",\"3\":\"isolated\"},"
            + "\"communities\":[],\"passes\":[]}";

    private MonitorRecordFixtures() {
    }

    public static Path writeCatalog(Path root, String area, String json) throws IOException {
        Path dir = Files.createDirectories(root.resolve(area));
        return Files.writeString(dir.resolve("catalog.json"), json);
    }

    public static Path writePassFile(Path root, String area, String pass, String name, byte[] content)
            throws IOException {
        Path dir = Files.createDirectories(root.resolve(area).resolve("passes").resolve(pass));
        return Files.write(dir.resolve(name), content);
    }
}
