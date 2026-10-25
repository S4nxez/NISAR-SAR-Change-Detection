package com.nisarsar.dao.repositories.common;

public class QuerysSQL {
    public static final String SELECT_ALL_SAR_SITES = "SELECT * FROM sar_site";
    public static final String SELECT_SAR_SITE_BY_ID = "SELECT * FROM sar_site WHERE id = ?";
    public static final String SELECT_OBSERVATIONS_BY_SITE = "SELECT * FROM sar_observation WHERE site_id = ? ORDER BY observation_date";
    public static final String INSERT_SAR_OBSERVATION = "INSERT INTO sar_observation (site_id, observation_date, vv, vh) VALUES (?, ?, ?, ?)";
    public static final String UPDATE_SAR_SITE_CHANGE = "UPDATE sar_site SET change_level = ?, change_value = ?, confidence = ? WHERE id = ?";

    public QuerysSQL(){
    }
}
