FROM mysql:8.4

# Copy the schema to be run on first startup
COPY schema.sql /docker-entrypoint-initdb.d/01-schema.sql

# Set default environment (overridden by Render)
ENV MYSQL_DATABASE=cyber_resilience_db
ENV MYSQL_USER=crps_user

EXPOSE 3306
