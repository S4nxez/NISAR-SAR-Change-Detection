package com.tradeanalytics.domain.errors;

public class DuplicatedUserError extends RuntimeException {
    public DuplicatedUserError(String message) {
        super(message);
    }
}