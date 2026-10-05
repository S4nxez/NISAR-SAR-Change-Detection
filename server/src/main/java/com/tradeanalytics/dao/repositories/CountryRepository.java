package com.tradeanalytics.dao.repositories;

import com.tradeanalytics.dao.model.Country;
import org.springframework.data.jpa.repository.JpaRepository;

public interface CountryRepository extends JpaRepository<Country, Long> {
}
