package com.nisarsar.ui.errors;

import com.nisarsar.domain.errors.DuplicatedUserError;
import com.nisarsar.domain.errors.ForeignKeyConstraintError;
import com.nisarsar.domain.errors.UnsupportedCatalogError;
import org.springframework.http.HttpStatus;
import org.springframework.http.ResponseEntity;
import org.springframework.web.bind.annotation.ControllerAdvice;
import org.springframework.web.bind.annotation.ExceptionHandler;
import org.springframework.web.servlet.mvc.method.annotation.ResponseEntityExceptionHandler;

@ControllerAdvice
public class GlobalExceptionHandler extends ResponseEntityExceptionHandler {
    @ExceptionHandler(ForeignKeyConstraintError.class)
    public ResponseEntity<Object> handleForeingKeyConstrainError(ForeignKeyConstraintError ex){
        return ResponseEntity.status(HttpStatus.CONFLICT).body(ex.getMessage());
    }
    @ExceptionHandler(DuplicatedUserError.class)
    public ResponseEntity<Object> handleDuplicatedUserError(DuplicatedUserError ex) {
        return ResponseEntity.status(HttpStatus.CONFLICT).body(ex.getMessage());
    }

    /** The worker and the backend disagree on the record's layout: the record exists but cannot be served yet. */
    @ExceptionHandler(UnsupportedCatalogError.class)
    public ResponseEntity<Object> handleUnsupportedCatalogError(UnsupportedCatalogError ex) {
        return ResponseEntity.status(HttpStatus.SERVICE_UNAVAILABLE).body(ex.getMessage());
    }
}
