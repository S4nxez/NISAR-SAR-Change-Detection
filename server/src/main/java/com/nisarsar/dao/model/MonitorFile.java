package com.nisarsar.dao.model;

import java.nio.file.Path;

/**
 * A file of the river lifeline record (written by processing/lifeline) and when it was last written, in epoch
 * milliseconds, for conditional requests.
 */
public record MonitorFile(Path path, long lastModified) {
}
