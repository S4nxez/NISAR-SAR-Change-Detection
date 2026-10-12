package com.nisarsar.dao.repositories;

import com.nisarsar.dao.model.entities.SiteObservationEntity;
import org.springframework.data.jpa.repository.JpaRepository;

import java.util.List;

public interface SiteObservationSeriesRepository extends JpaRepository<SiteObservationEntity, Long> {

}
