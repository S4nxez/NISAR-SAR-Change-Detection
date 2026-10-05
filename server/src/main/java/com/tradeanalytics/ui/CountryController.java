package com.tradeanalytics.ui;

import com.tradeanalytics.common.Constants;
import com.tradeanalytics.dao.model.Country;
import com.tradeanalytics.domain.services.CountryService;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import java.util.List;

@RestController
@RequiredArgsConstructor
public class CountryController {

    private final CountryService countryService;

    @GetMapping(Constants.COUNTRIES_PATH)
    public List<Country> get(){
        return countryService.get();
    }

}
