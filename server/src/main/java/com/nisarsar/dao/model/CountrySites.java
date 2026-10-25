package com.nisarsar.dao.model;

import java.util.List;

public record CountrySites(
        String country,
        List<SarSite> sites
) {}
