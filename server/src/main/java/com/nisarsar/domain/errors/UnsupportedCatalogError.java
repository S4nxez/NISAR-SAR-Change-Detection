package com.nisarsar.domain.errors;

/**
 * The catalog on disk cannot be served: it is not valid JSON or was written by a version of processing/lifeline whose
 * layout this backend does not know (schema_version).
 */
public class UnsupportedCatalogError extends RuntimeException {
    public UnsupportedCatalogError(String message) {
        super(message);
    }
}
