package com.nisarsar.dao.model;

import java.util.List;

public record SiteObservationSeries(
        Long id,
        String siteId,
        List<String> dates,
        List<Double> vv,
        List<Double> vh
) {}
