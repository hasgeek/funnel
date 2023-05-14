#!/bin/bash
set -e

psql -c "create user funnel;"
psql -c "create database funnel;"
psql -c "create database geoname;"
psql funnel << $$
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
$$
psql geoname << $$
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
$$
psql -c "grant all privileges on database funnel to funnel;"
psql -c "grant all privileges on database geoname to funnel;"
psql funnel -c "grant all privileges on schema public to funnel; grant all privileges on all tables in schema public to funnel; grant all privileges on all sequences in schema public to funnel;"
psql geoname -c "grant all privileges on schema public to funnel; grant all privileges on all tables in schema public to funnel; grant all privileges on all sequences in schema public to funnel;"
