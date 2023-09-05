"""Fix primary table function body.

Revision ID: 4f9ca10b7b9d
Revises: 65e230fee746
Create Date: 2023-09-05 09:27:32.647197

"""

from textwrap import dedent
from typing import Optional, Tuple, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = '4f9ca10b7b9d'
down_revision: str = '65e230fee746'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


def upgrade(engine_name: str = '') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name: str = '') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade default database."""
    op.execute(
        sa.text(
            dedent(
                '''
    CREATE OR REPLACE FUNCTION public.account_account_email_primary_validate()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $function$
    DECLARE
        target RECORD;
    BEGIN
        IF (NEW.account_email_id IS NOT NULL) THEN
            SELECT account_id INTO target FROM account_email WHERE id = NEW.account_email_id;
            IF (target.account_id != NEW.account_id) THEN
                RAISE foreign_key_violation USING MESSAGE = 'The target is not affiliated with this parent';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $function$
    '''
            )
        )
    )

    op.execute(
        sa.text(
            dedent(
                '''
    CREATE OR REPLACE FUNCTION public.account_account_phone_primary_validate()
    RETURNS trigger
    LANGUAGE plpgsql
    AS $function$
    DECLARE
        target RECORD;
    BEGIN
        IF (NEW.account_phone_id IS NOT NULL) THEN
            SELECT account_id INTO target FROM account_phone WHERE id = NEW.account_phone_id;
            IF (target.account_id != NEW.account_id) THEN
                RAISE foreign_key_violation USING MESSAGE = 'The target is not affiliated with this parent';
            END IF;
        END IF;
        RETURN NEW;
    END;
    $function$
    '''
            )
        )
    )


def downgrade_() -> None:
    """Downgrade default database."""
    op.execute(
        sa.text(
            dedent(
                '''
    CREATE OR REPLACE FUNCTION public.account_account_email_primary_validate()
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
    '''
            )
        )
    )

    op.execute(
        sa.text(
            dedent(
                '''
    CREATE OR REPLACE FUNCTION public.account_account_phone_primary_validate()
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
    '''
            )
        )
    )
