#!/bin/bash
set -e

psql -c "create user funnel;"
psql -c "create database funnel_testing;"
psql -c "create database geoname_testing;"
psql funnel_testing << $$
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
$$
psql geoname_testing << $$
CREATE EXTENSION IF NOT EXISTS pg_trgm;
CREATE EXTENSION IF NOT EXISTS unaccent;
CREATE EXTENSION IF NOT EXISTS pgcrypto;
$$
psql -c "grant all privileges on database funnel_testing to funnel;"
psql -c "grant all privileges on database geoname_testing to funnel;"
psql funnel_testing -c "grant all privileges on schema public to funnel; grant all privileges on all tables in schema public to funnel; grant all privileges on all sequences in schema public to funnel;"
psql geoname_testing -c "grant all privileges on schema public to funnel; grant all privileges on all tables in schema public to funnel; grant all privileges on all sequences in schema public to funnel;"
