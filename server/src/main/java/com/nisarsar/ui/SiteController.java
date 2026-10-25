package com.nisarsar.ui;

import com.nisarsar.common.Constants;
import com.nisarsar.dao.model.SarSite;
import com.nisarsar.dao.model.SiteCatalog;
import com.nisarsar.dao.model.SiteObservationSeries;
import com.nisarsar.domain.services.SiteCatalogService;
import org.springframework.http.HttpStatus;
import org.springframework.web.bind.annotation.GetMapping;
import org.springframework.web.bind.annotation.PathVariable;
import org.springframework.web.bind.annotation.RequestMapping;
import org.springframework.web.bind.annotation.RestController;
import org.springframework.web.server.ResponseStatusException;

@RestController
@RequestMapping(Constants.API)
public class SiteController {
    private final SiteCatalogService siteCatalogService;

    public SiteController(SiteCatalogService siteCatalogService) {
        this.siteCatalogService = siteCatalogService;
    }

    @GetMapping(Constants.SITES)
    public SiteCatalog getSites() {
        return siteCatalogService.getCatalog();
    }

    @GetMapping( Constants.SITES+ "/{id}")
    public SarSite getSite(@PathVariable String id) {
        return siteCatalogService.getCatalog().countries().stream()
                .flatMap(country -> country.sites().stream())
                .filter(site -> site.id().equals(id))
                .findFirst()
                .orElseThrow(() -> new ResponseStatusException(HttpStatus.NOT_FOUND, "Sar site not found" + id));
    }

    @GetMapping(Constants.SITES + "/{id}" + Constants.OBSERVATIONS)
    public SiteObservationSeries getObservations(@PathVariable String id) {
        SarSite site = getSite(id);

        return new SiteObservationSeries(
                null,
                site.id(),
                siteCatalogService.getCatalog().observationDates(),
                site.vv(),
                site.vh()
        );
    }
}
