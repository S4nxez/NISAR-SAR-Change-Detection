package com.nisarsar.dao.model;

import java.util.List;


public record SarSite(
        String id,
        String name,
        String country,
        double lat,
        double lng,
        String level,
        String change,
        String category,
        String description,
        double confidence,
        List<Double> vv,
        List<Double> vh
) {}
