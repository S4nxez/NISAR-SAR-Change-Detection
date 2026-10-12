package com.nisarsar.dao.model;

import jakarta.persistence.Entity;
import jakarta.persistence.Table;
import jakarta.persistence.Id;

import java.util.List;


@Entity
@Table(name = "sar_site")
public record SarSite(
        @Id
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
