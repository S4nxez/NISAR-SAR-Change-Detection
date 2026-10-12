package com.nisarsar.dao.model;

import jakarta.persistence.Table;

import java.util.List;

@Table(name = "sar_observation")
public record SiteObservationSeries(String siteId, List<String> dates, List<Double> vv, List<Double> vh) {}
