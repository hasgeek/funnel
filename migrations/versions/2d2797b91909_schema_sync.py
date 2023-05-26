"""Schema sync.

Revision ID: 2d2797b91909
Revises: f9c44ecb5999
Create Date: 2020-09-10 04:23:46.996917

"""

from typing import Optional, Tuple, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '2d2797b91909'
down_revision = 'f9c44ecb5999'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade() -> None:
    # Migration auto-generated using Migra
    op.execute(
        sa.DDL(
            '''
alter table "comment" drop constraint "comment_state_check";

alter table "email_address" drop constraint "email_address_email_is_blocked_check";

alter table "proposal" drop constraint "proposal_state_check";

alter table "rsvp" drop constraint "rsvp_state_check";

set check_function_bodies = off;

CREATE OR REPLACE FUNCTION project_venue_primary_validate()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
            DECLARE
                target RECORD;
            BEGIN
                IF (NEW.venue_id IS NOT NULL) THEN
                    SELECT project_id INTO target FROM venue WHERE id = NEW.venue_id;
                    IF (target.project_id != NEW.project_id) THEN
                        RAISE foreign_key_violation USING MESSAGE = 'The target is not affiliated with this parent';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $function$
;

CREATE OR REPLACE FUNCTION user_user_email_primary_validate()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
            DECLARE
                target RECORD;
            BEGIN
                IF (NEW.user_email_id IS NOT NULL) THEN
                    SELECT user_id INTO target FROM user_email WHERE id = NEW.user_email_id;
                    IF (target.user_id != NEW.user_id) THEN
                        RAISE foreign_key_violation USING MESSAGE = 'The target is not affiliated with this parent';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $function$
;

CREATE OR REPLACE FUNCTION user_user_phone_primary_validate()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
            DECLARE
                target RECORD;
            BEGIN
                IF (NEW.user_phone_id IS NOT NULL) THEN
                    SELECT user_id INTO target FROM user_phone WHERE id = NEW.user_phone_id;
                    IF (target.user_id != NEW.user_id) THEN
                        RAISE foreign_key_violation USING MESSAGE = 'The target is not affiliated with this parent';
                    END IF;
                END IF;
                RETURN NEW;
            END;
            $function$
;

alter table "organization_membership" add constraint "organization_membership_record_type_check" CHECK ((record_type = ANY (ARRAY[0, 1, 2, 3])));

alter table "profile" add constraint "profile_state_check" CHECK ((state = ANY (ARRAY[0, 1, 2])));

alter table "project_crew_membership" add constraint "project_crew_membership_record_type_check" CHECK ((record_type = ANY (ARRAY[0, 1, 2, 3])));

alter table "proposal_membership" add constraint "proposal_membership_record_type_check" CHECK ((record_type = ANY (ARRAY[0, 1, 2, 3])));

alter table "site_membership" add constraint "site_membership_record_type_check" CHECK ((record_type = ANY (ARRAY[0, 1, 2, 3])));

alter table "update" add constraint "update_name_check" CHECK (((name)::text <> ''::text));

alter table "update" add constraint "update_state_check" CHECK ((state = ANY (ARRAY[0, 1, 2])));

alter table "update" add constraint "update_visibility_state_check" CHECK ((visibility_state = ANY (ARRAY[0, 1])));

alter table "comment" add constraint "comment_state_check" CHECK ((state = ANY (ARRAY[0, 1, 2, 3, 4])));

alter table "email_address" add constraint "email_address_email_is_blocked_check" CHECK (((is_blocked IS NOT TRUE) OR ((is_blocked IS TRUE) AND (email IS NULL) AND (domain IS NULL))));

alter table "proposal" add constraint "proposal_state_check" CHECK ((state = ANY (ARRAY[0, 1, 2, 3, 5, 6, 7, 8, 11, 4, 9, 10])));

alter table "rsvp" add constraint "rsvp_state_check" CHECK ((state = ANY (ARRAY['Y'::bpchar, 'N'::bpchar, 'M'::bpchar, 'A'::bpchar])));
'''
        )
    )


def downgrade() -> None:
    op.execute(
        sa.DDL(
            '''
alter table "organization_membership" drop constraint "organization_membership_record_type_check";

alter table "profile" drop constraint "profile_state_check";

alter table "project_crew_membership" drop constraint "project_crew_membership_record_type_check";

alter table "proposal_membership" drop constraint "proposal_membership_record_type_check";

alter table "site_membership" drop constraint "site_membership_record_type_check";

alter table "update" drop constraint "update_name_check";

alter table "update" drop constraint "update_state_check";

alter table "update" drop constraint "update_visibility_state_check";

alter table "comment" drop constraint "comment_state_check";

alter table "email_address" drop constraint "email_address_email_is_blocked_check";

alter table "proposal" drop constraint "proposal_state_check";

alter table "rsvp" drop constraint "rsvp_state_check";

set check_function_bodies = off;

CREATE OR REPLACE FUNCTION project_venue_primary_validate()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
        DECLARE
            target RECORD;
        BEGIN
            IF (NEW.venue_id IS NOT NULL) THEN
                SELECT project_id INTO target FROM venue WHERE id = NEW.venue_id;
                IF (target.project_id != NEW.project_id) THEN
                    RAISE foreign_key_violation USING MESSAGE = 'The target is not affiliated with this parent';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $function$
;

CREATE OR REPLACE FUNCTION user_user_email_primary_validate()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    target RECORD;
BEGIN
    IF (NEW.user_email_id IS NOT NULL) THEN
        SELECT user_id INTO target FROM user_email WHERE id = NEW.user_email_id;
        IF (target.user_id != NEW.user_id) THEN
            RAISE foreign_key_violation USING MESSAGE = 'The target is not affiliated with this parent';
        END IF;
    END IF;
    RETURN NEW;
END;
$function$
;

CREATE OR REPLACE FUNCTION user_user_phone_primary_validate()
 RETURNS trigger
 LANGUAGE plpgsql
AS $function$
DECLARE
    target RECORD;
BEGIN
    IF (NEW.user_phone_id IS NOT NULL) THEN
        SELECT user_id INTO target FROM user_phone WHERE id = NEW.user_phone_id;
        IF (target.user_id != NEW.user_id) THEN
            RAISE foreign_key_violation USING MESSAGE = 'The target is not affiliated with this parent';
        END IF;
    END IF;
    RETURN NEW;
END;
$function$
;

alter table "comment" add constraint "comment_state_check" CHECK ((state = ANY (ARRAY[3, 4, 1, 2, 0])));

alter table "email_address" add constraint "email_address_email_is_blocked_check" CHECK (((is_blocked IS NOT TRUE) OR ((is_blocked IS TRUE) AND (email IS NULL))));

alter table "proposal" add constraint "proposal_state_check" CHECK ((state = ANY (ARRAY[10, 11, 7, 2, 1, 9, 0, 5, 3, 6, 8, 4])));

alter table "rsvp" add constraint "rsvp_state_check" CHECK ((state = ANY (ARRAY['A'::bpchar, 'M'::bpchar, 'N'::bpchar, 'Y'::bpchar])));
'''
        )
    )
