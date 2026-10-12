package com.nisarsar.dao.model.entities;

import jakarta.persistence.Column;
import jakarta.persistence.Entity;
import jakarta.persistence.Id;
import jakarta.persistence.Table;
import lombok.Getter;
import lombok.Setter;

import java.math.BigDecimal;
import java.time.LocalDateTime;

@Entity
@Getter
@Setter
@Table(name = "sar_site")
public class SarSiteEntity {

    @Id
    @Column(name = "id", length = 50, nullable = false)
    private String id;

    @Column(name = "name", length = 150, nullable = false)
    private String name;

    @Column(name = "country", length = 100, nullable = false)
    private String country;

    @Column(name = "latitude", precision = 9, scale = 6, nullable = false)
    private BigDecimal latitude;

    @Column(name = "longitude", precision = 9, scale = 6, nullable = false)
    private BigDecimal longitude;

    @Column(name = "change_level", length = 20, nullable = false)
    private String changeLevel;

    @Column(name = "change_value", length = 20, nullable = false)
    private String changeValue;

    @Column(name = "category", length = 100, nullable = false)
    private String category;

    @Column(name = "description", nullable = false, columnDefinition = "TEXT")
    private String description;

    @Column(name = "confidence", precision = 4, scale = 3, nullable = false)
    private BigDecimal confidence;

    @Column(name = "created_at", nullable = false, updatable = false)
    private LocalDateTime createdAt;

    protected SarSiteEntity() {
    }
}