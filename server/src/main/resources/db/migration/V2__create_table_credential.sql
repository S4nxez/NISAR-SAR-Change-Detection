CREATE TABLE credential (
                          user_id BIGINT UNSIGNED PRIMARY KEY AUTO_INCREMENT,

                          username VARCHAR(100) NOT NULL,

                          password VARCHAR(100) NOT NULL,

                          UNIQUE (user_id, username)
);


