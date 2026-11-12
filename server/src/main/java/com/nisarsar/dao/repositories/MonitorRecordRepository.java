package com.nisarsar.dao.repositories;

import com.nisarsar.dao.model.MonitorFile;
import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Repository;

import java.io.IOException;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.Optional;
import java.util.regex.Pattern;

/**
 * The river lifeline record on disk, as the processing worker writes it (MONITOR_DATA_DIR, the monitor_data volume
 * of podman-compose.yml):
 * <pre>
 *   &lt;area&gt;/catalog.json
 *   &lt;area&gt;/passes/&lt;pass&gt;/&lt;file&gt;
 * </pre>
 * Every name comes from the request URL, so only plain names are accepted and the resolved path must stay inside
 * the data folder: anything else is reported as missing.
 */
@Repository
public class MonitorRecordRepository {
    private static final Pattern NAME = Pattern.compile("[A-Za-z0-9_-]{1,64}");
    private static final Pattern FILE_NAME = Pattern.compile("[A-Za-z0-9_-]{1,64}\\.[a-z0-9]{1,8}");

    private final Path root;

    public MonitorRecordRepository(@Value("${monitor.data-dir}") Path root) {
        this.root = root.toAbsolutePath().normalize();
    }

    public Optional<MonitorFile> findCatalog(String areaId) {
        if (!isName(areaId)) {
            return Optional.empty();
        }
        return find(root.resolve(areaId).resolve("catalog.json"));
    }

    public Optional<MonitorFile> findPassFile(String areaId, String passId, String fileName) {
        if (!isName(areaId) || !isName(passId) || fileName == null || !FILE_NAME.matcher(fileName).matches()) {
            return Optional.empty();
        }
        return find(root.resolve(areaId).resolve("passes").resolve(passId).resolve(fileName));
    }

    static boolean isName(String name) {
        return name != null && NAME.matcher(name).matches();
    }

    private Optional<MonitorFile> find(Path path) {
        Path normalized = path.normalize();
        if (!normalized.startsWith(root) || !Files.isRegularFile(normalized)) {
            return Optional.empty();
        }
        try {
            return Optional.of(new MonitorFile(normalized, Files.getLastModifiedTime(normalized).toMillis()));
        } catch (IOException e) {
            // removed or rewritten between the two calls: the next request will find it again
            return Optional.empty();
        }
    }
}
