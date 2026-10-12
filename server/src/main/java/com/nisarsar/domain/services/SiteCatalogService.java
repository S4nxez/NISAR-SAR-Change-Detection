package com.nisarsar.domain.services;

import com.fasterxml.jackson.databind.ObjectMapper;
import org.springframework.core.io.ClassPathResource;
import org.springframework.stereotype.Service;
import com.nisarsar.dao.model.SiteCatalog;

import java.io.IOException;

@Service
public class SiteCatalogService {
    private final SiteCatalog catalog;

    public SiteCatalogService(ObjectMapper objectMapper) throws IOException {
        try (var input = new ClassPathResource("data/sites.json").getInputStream()) {
            this.catalog = objectMapper.readValue(input, SiteCatalog.class);
        }
    }

    public SiteCatalog getCatalog() {
        return catalog;
    }
}
