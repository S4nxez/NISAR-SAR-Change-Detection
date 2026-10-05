package com.tradeanalytics.dao.repositories.common;

public class QuerysSQL {
    public static final String INSERT_INTO_COUNTRIES_NAME_DATE_OF_BIRTH_PHONE_VALUES = "INSERT INTO countries (name, date_of_birth, phone) VALUES (?, ?, ?)";
    public static final String SELECT_ALL_COUNTRIES = "SELECT * FROM countries";
    public static final String UPDATE_COUNTRY = "UPDATE countries SET name = ?, date_of_birth = ?, phone = ? where country_id = ?";

    public QuerysSQL(){
    }
}
