package com.tradeanalytics.domain.services;

import com.tradeanalytics.dao.model.Country;
import com.tradeanalytics.dao.repositories.CountryRepository;
import lombok.RequiredArgsConstructor;
import org.springframework.stereotype.Service;

import java.util.ArrayList;
import java.util.List;

@Service
@RequiredArgsConstructor
public class CountryService {
    private final CountryRepository countryRepository;

    public List<Country> get(){
        return countryRepository.findAll();
    }

}
