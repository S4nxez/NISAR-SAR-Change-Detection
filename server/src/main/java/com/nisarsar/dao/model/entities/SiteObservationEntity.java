package com.nisarsar.dao.model.entities;

import jakarta.persistence.*;
import lombok.Data;

import java.math.BigDecimal;

@Entity
@Data
@Table(name = "sar_observation")
public class SiteObservationEntity {
    @Id
    @GeneratedValue(strategy = GenerationType.IDENTITY)
    private Long id;

    @Column(name = "site_id", nullable = false)
    private String siteId;

    @Column(name = "observation_date", nullable = false)
    private String observationDate;

    @Column(nullable = false, precision = 7, scale = 3)
    private BigDecimal vv;

    @Column(nullable = false, precision = 7, scale = 3)
    private BigDecimal vh;

    protected SiteObservationEntity() {}
}