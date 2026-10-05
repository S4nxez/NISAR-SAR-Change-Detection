package com.tradeanalytics.dao.repositories.common;

import org.springframework.beans.factory.annotation.Value;
import org.springframework.stereotype.Component;

import java.sql.Connection;
import java.sql.SQLException;

import com.zaxxer.hikari.HikariConfig;
import com.zaxxer.hikari.HikariDataSource;

import javax.sql.DataSource;

@Component
public class PoolDBConnection {

    private final DataSource hikariDataSource;

    public PoolDBConnection(
            @Value("${spring.datasource.url}") String jdbcUrl,
            @Value("${spring.datasource.username}") String username,
            @Value("${spring.datasource.password}") String password,
            @Value("${spring.datasource.driver-class-name}") String driverClassName
    ) {
        this.hikariDataSource = getHikariPool(jdbcUrl, username, password, driverClassName);
    }

    private DataSource getHikariPool(String jdbcUrl, String username, String password, String driverClassName) {
        HikariConfig hikariConfig = new HikariConfig();
        hikariConfig.setJdbcUrl(jdbcUrl);
        hikariConfig.setUsername(username);
        hikariConfig.setPassword(password);
        hikariConfig.setDriverClassName(driverClassName);
        hikariConfig.setMaximumPoolSize(4);

        hikariConfig.addDataSourceProperty("cachePrepStmts", true);
        hikariConfig.addDataSourceProperty("prepStmtCacheSize", 250);
        hikariConfig.addDataSourceProperty("prepStmtCacheSqlLimit", 2048);

        return new HikariDataSource(hikariConfig);
    }

    public Connection getConnection() {
        try {
            return hikariDataSource.getConnection();
        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
    }

    public void closePool() {
        if (hikariDataSource instanceof HikariDataSource) {
            ((HikariDataSource) hikariDataSource).close();
        }
    }
}