package com.tradeanalytics.config;

import io.jsonwebtoken.SignatureAlgorithm;
import io.jsonwebtoken.security.Keys;
import org.springframework.context.annotation.Bean;
import org.springframework.context.annotation.Configuration;

import java.security.Key;

@Configuration
public class JwtConfig {
    @Bean("JWT")
    public Key jwtKey() {
        return Keys.secretKeyFor(SignatureAlgorithm.HS256);
    }
}