package com.tradeanalytics.ui.errors;

import com.tradeanalytics.domain.errors.DuplicatedUserError;
import com.tradeanalytics.domain.errors.ForeignKeyConstraintError;
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
}
