package com.nisarsar.domain.errors;

public class DuplicatedUserError extends RuntimeException {
    public DuplicatedUserError(String message) {
        super(message);
    }
}