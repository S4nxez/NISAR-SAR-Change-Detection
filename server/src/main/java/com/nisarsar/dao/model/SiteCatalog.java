package com.nisarsar.dao.model;

import java.util.List;

public record SiteCatalog(List<String> observationDates, List<SarSite> sites) {}
