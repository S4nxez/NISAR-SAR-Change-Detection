package com.nisarsar.domain.services;

import com.nisarsar.dao.model.SarSite;
import com.nisarsar.dao.model.SiteCatalog;
import com.nisarsar.dao.model.entities.SarSiteEntity;
import com.nisarsar.dao.model.entities.SiteObservationEntity;
import com.nisarsar.dao.repositories.SarSiteRepository;
import com.nisarsar.dao.repositories.SiteObservationSeriesRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.Collections;
import java.util.List;
import java.util.Map;
import java.util.function.Function;
import java.util.stream.Collectors;

@Service
@RequiredArgsConstructor
public class SiteCatalogService {

    private final SiteObservationSeriesRepository siteObservationSeriesRepository;
    private final SarSiteRepository sarSiteRepository;

    public SiteCatalog getCatalog() {
        List<SarSiteEntity> siteEntities = sarSiteRepository.findAll();

        List<SiteObservationEntity> observations = siteObservationSeriesRepository.findAll();

        // Fechas globales, ordenadas cronológicamente.
        List<String> dates = observations.stream()
                .map(SiteObservationEntity::getObservationDate)
                .distinct()
                .sorted()
                .toList();

        // Agrupar observaciones por sitio y fecha.
        Map<String, Map<String, SiteObservationEntity>> observationsBySite =
                observations.stream()
                        .collect(Collectors.groupingBy(
                                SiteObservationEntity::getSiteId,
                                Collectors.toMap(
                                        SiteObservationEntity::getObservationDate,
                                        Function.identity()
                                )
                        ));

        List<SarSite> sites = siteEntities.stream()
                .map(site -> {
                    Map<String, SiteObservationEntity> siteObservations =
                            observationsBySite.getOrDefault(
                                    site.getId(),
                                    Collections.emptyMap()
                            );

                    List<Double> vv = dates.stream()
                            .map(date -> siteObservations.get(date))
                            .map(obs -> obs == null
                                    ? null
                                    : obs.getVv().doubleValue())
                            .toList();

                    List<Double> vh = dates.stream()
                            .map(date -> siteObservations.get(date))
                            .map(obs -> obs == null
                                    ? null
                                    : obs.getVh().doubleValue())
                            .toList();

                    return new SarSite(
                            site.getId(),
                            site.getName(),
                            site.getCountry(),
                            site.getLatitude().doubleValue(),
                            site.getLongitude().doubleValue(),
                            site.getChangeLevel(),
                            site.getChangeValue(),
                            site.getCategory(),
                            site.getDescription(),
                            site.getConfidence().doubleValue(),
                            vv,
                            vh
                    );
                })
                .toList();

        return new SiteCatalog(dates, sites);
    }
}
