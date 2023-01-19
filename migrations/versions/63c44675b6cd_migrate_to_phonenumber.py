"""Migrate to PhoneNumber.

Revision ID: 63c44675b6cd
Revises: fb90ab2af4c2
Create Date: 2023-01-17 22:58:23.556730

"""

from typing import Optional, Tuple, Union
import hashlib

from alembic import op
from sqlalchemy.sql import column, table
import sqlalchemy as sa

import phonenumbers
import rich.progress

# revision identifiers, used by Alembic.
revision: str = '63c44675b6cd'
down_revision: str = 'fb90ab2af4c2'
branch_labels: Optional[Union[str, Tuple[str, ...]]] = None
depends_on: Optional[Union[str, Tuple[str, ...]]] = None


# SMS delivery status in sms_message table
SMS_STATUS_QUEUED = 1
SMS_STATUS_PENDING = 2
SMS_STATUS_DELIVERED = 3
SMS_STATUS_FAILED = 4
SMS_STATUS_UNKNOWN = 5


user_phone = table(
    'user_phone',
    column('id', sa.Integer),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('phone', sa.Unicode),
    column('phone_number_id', sa.Integer),
    column('blake2b160', sa.LargeBinary),
)

sms_message = table(
    'sms_message',
    column('id', sa.Integer),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('transactionid', sa.Unicode),
    column('status', sa.Integer),
    column('status_at', sa.TIMESTAMP(timezone=True)),
    column('phone_number', sa.Unicode),
    column('phone_number_id', sa.Integer),
)

phone_number = table(
    'phone_number',
    column('id', sa.Integer),
    column('created_at', sa.TIMESTAMP(timezone=True)),
    column('updated_at', sa.TIMESTAMP(timezone=True)),
    column('phone', sa.Unicode),
    column('blake2b160', sa.LargeBinary),
    column('sms_sent_at', sa.TIMESTAMP(timezone=True)),
    column('sms_delivered_at', sa.TIMESTAMP(timezone=True)),
    column('sms_failed_at', sa.TIMESTAMP(timezone=True)),
    column('is_blocked', sa.Boolean),
)


def clean_phone_number(candidate: str) -> str:
    # SmsMessage had a bug causing it to store 0-prefixed numbers for India
    try:
        parsed = phonenumbers.parse(candidate, 'IN')
        if phonenumbers.is_valid_number(parsed) and phonenumbers.number_type(
            parsed
        ) in (
            phonenumbers.PhoneNumberType.MOBILE,
            phonenumbers.PhoneNumberType.FIXED_LINE_OR_MOBILE,
        ):
            return phonenumbers.format_number(
                parsed, phonenumbers.PhoneNumberFormat.E164
            )
    except phonenumbers.NumberParseException:
        pass
    raise ValueError(f"Invalid phone number: {candidate}")


def phone_blake2b160_hash(phone: str) -> bytes:
    """BLAKE2b hash of the given phone number using digest size 20 (160 bits)."""
    return hashlib.blake2b(phone.encode('utf-8'), digest_size=20).digest()


def upgrade(engine_name='') -> None:
    """Upgrade all databases."""
    # Do not modify. Edit `upgrade_` instead
    globals().get(f'upgrade_{engine_name}', lambda: None)()


def downgrade(engine_name='') -> None:
    """Downgrade all databases."""
    # Do not modify. Edit `downgrade_` instead
    globals().get(f'downgrade_{engine_name}', lambda: None)()


def upgrade_() -> None:
    """Upgrade database bind ''."""
    conn = op.get_bind()

    # --- UserPhone --------------------------------------------------------------------
    op.add_column(
        'user_phone', sa.Column('phone_number_id', sa.Integer(), nullable=True)
    )
    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(user_phone))
    items = conn.execute(
        sa.select(
            [
                user_phone.c.id,
                user_phone.c.phone,
                user_phone.c.created_at,
                user_phone.c.updated_at,
            ]
        ).order_by(user_phone.c.id)
    )
    for item in rich.progress.track(items, "user_phone", total=count):
        phone = clean_phone_number(item.phone)
        blake2b160 = phone_blake2b160_hash(phone)
        existing = conn.execute(
            sa.select([phone_number.c.id, phone_number.c.created_at])
            .where(phone_number.c.blake2b160 == blake2b160)
            .limit(1)
        ).fetchone()
        if existing:
            pn_id = existing.id
            if existing.created_at > item.created_at:
                conn.execute(
                    phone_number.update()
                    .where(phone_number.c.id == existing.id)
                    .values(created_at=item.created_at)
                )
        else:
            pn_id = conn.execute(
                phone_number.insert()
                .values(
                    created_at=item.created_at,
                    updated_at=item.updated_at,
                    phone=phone,
                    blake2b160=blake2b160,
                    is_blocked=False,
                )
                .returning(phone_number.c.id)
            ).fetchone()[0]

        conn.execute(
            user_phone.update()
            .where(user_phone.c.id == item.id)
            .values(phone_number_id=pn_id)
        )

    op.alter_column('user_phone', 'phone_number_id', nullable=False)
    op.drop_constraint('user_phone_phone_key', 'user_phone', type_='unique')
    op.create_unique_constraint(
        'user_phone_phone_number_id_key', 'user_phone', ['phone_number_id']
    )
    op.create_foreign_key(
        'user_phone_phone_number_id_fkey',
        'user_phone',
        'phone_number',
        ['phone_number_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.drop_column('user_phone', 'phone')
    op.drop_column('user_phone', 'gets_text')

    # --- SmsMessage -------------------------------------------------------------------
    # Remove rows with no transactionid, as the data is not validated in any way
    conn.execute(sa.delete(sms_message).where(sms_message.c.transactionid.is_(None)))
    op.add_column(
        'sms_message', sa.Column('phone_number_id', sa.Integer(), nullable=True)
    )

    rows_to_delete = set()

    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(sms_message))
    items = conn.execute(
        sa.select(
            [
                sms_message.c.id,
                sms_message.c.phone_number,
                sms_message.c.created_at,
                sms_message.c.updated_at,
                sms_message.c.status,
                sms_message.c.status_at,
            ]
        ).order_by(sms_message.c.id)
    )
    for item in rich.progress.track(items, "sms_message", total=count):
        try:
            phone = clean_phone_number(item.phone_number)
        except ValueError:
            rows_to_delete.add(item.id)
            continue
        blake2b160 = phone_blake2b160_hash(phone)
        existing = conn.execute(
            sa.select(
                [
                    phone_number.c.id,
                    phone_number.c.created_at,
                    phone_number.c.sms_sent_at,
                    phone_number.c.sms_delivered_at,
                    phone_number.c.sms_failed_at,
                ]
            )
            .where(phone_number.c.blake2b160 == blake2b160)
            .limit(1)
        ).fetchone()
        if existing:
            pn_id = existing.id
            timestamps = {}
            if existing.created_at > item.created_at:
                timestamps['created_at'] = item.created_at
            if item.status in (SMS_STATUS_QUEUED, SMS_STATUS_PENDING):
                if not existing.sms_sent_at or item.status_at > existing.sms_sent_at:
                    timestamps['sms_sent_at'] = item.status_at
            elif item.status == SMS_STATUS_DELIVERED:
                if (
                    not existing.sms_delivered_at
                    or item.status_at > existing.sms_delivered_at
                ):
                    timestamps['sms_delivered_at'] = item.status_at
            elif item.status == SMS_STATUS_FAILED:
                if (
                    not existing.sms_failed_at
                    or item.status_at > existing.sms_failed_at
                ):
                    timestamps['sms_failed_at'] = item.status_at
            if timestamps:
                conn.execute(
                    phone_number.update()
                    .where(phone_number.c.id == existing.id)
                    .values(**timestamps)
                )
        else:
            timestamps = {
                'created_at': item.created_at,
                'updated_at': item.updated_at,
            }
            if item.status in (SMS_STATUS_QUEUED, SMS_STATUS_PENDING):
                timestamps['sms_sent_at'] = item.status_at
            elif item.status == SMS_STATUS_DELIVERED:
                timestamps['sms_delivered_at'] = item.status_at
            elif item.status == SMS_STATUS_FAILED:
                timestamps['sms_failed_at'] = item.status_at
            pn_id = conn.execute(
                phone_number.insert()
                .values(
                    phone=phone, blake2b160=blake2b160, is_blocked=False, **timestamps
                )
                .returning(phone_number.c.id)
            ).fetchone()[0]
        conn.execute(
            sms_message.update()
            .where(sms_message.c.id == item.id)
            .values(phone_number_id=pn_id)
        )

    # Remove rows where phone number could not be validated
    print(  # noqa: T201
        f"Deleting {len(rows_to_delete)} rows from sms_message with invalid phone"
        f" numbers"
    )
    conn.execute(sa.delete(sms_message).where(sms_message.c.id.in_(rows_to_delete)))

    op.alter_column('sms_message', 'phone_number_id', nullable=False)
    op.create_index(
        op.f('ix_sms_message_phone_number_id'),
        'sms_message',
        ['phone_number_id'],
        unique=False,
    )
    op.create_foreign_key(
        'sms_message_phone_number_id_fkey',
        'sms_message',
        'phone_number',
        ['phone_number_id'],
        ['id'],
        ondelete='SET NULL',
    )
    op.drop_column('sms_message', 'phone_number')


def downgrade_() -> None:
    """Downgrade database bind ''."""
    conn = op.get_bind()

    # --- SmsMessage -------------------------------------------------------------------
    op.add_column(
        'sms_message',
        sa.Column(
            'phone_number',
            sa.VARCHAR(length=15),
            autoincrement=False,
            nullable=True,
        ),
    )
    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(sms_message))
    items = conn.execute(
        sa.select([sms_message.c.id, phone_number.c.phone]).where(
            sms_message.c.phone_number_id == phone_number.c.id
        )
    )
    for item in rich.progress.track(items, "user_phone", total=count):
        conn.execute(
            sms_message.update()
            .where(sms_message.c.id == item.id)
            .values(phone_number=item.phone)
        )
    op.alter_column('sms_message', 'phone_number', nullable=False)
    op.drop_constraint(
        'sms_message_phone_number_id_fkey', 'sms_message', type_='foreignkey'
    )
    op.drop_index(op.f('ix_sms_message_phone_number_id'), 'sms_message')
    op.drop_column('sms_message', 'phone_number_id')

    # --- UserPhone --------------------------------------------------------------------
    op.add_column(
        'user_phone',
        sa.Column(
            'gets_text',
            sa.BOOLEAN(),
            autoincrement=False,
            nullable=False,
            server_default=sa.sql.expression.true(),
        ),
    )
    op.alter_column('user_phone', 'gets_text', server_default=None)
    op.add_column(
        'user_phone', sa.Column('phone', sa.TEXT(), autoincrement=False, nullable=True)
    )
    count = conn.scalar(sa.select([sa.func.count('*')]).select_from(user_phone))
    items = conn.execute(
        sa.select([user_phone.c.id, phone_number.c.phone]).where(
            user_phone.c.phone_number_id == phone_number.c.id
        )
    )
    for item in rich.progress.track(items, "user_phone", total=count):
        conn.execute(
            user_phone.update()
            .where(user_phone.c.id == item.id)
            .values(phone=item.phone)
        )
    op.alter_column('user_phone', 'phone', nullable=False)
    op.drop_constraint(
        'user_phone_phone_number_id_fkey', 'user_phone', type_='foreignkey'
    )
    op.drop_constraint('user_phone_phone_number_id_key', 'user_phone', type_='unique')
    op.create_unique_constraint('user_phone_phone_key', 'user_phone', ['phone'])
    op.drop_column('user_phone', 'phone_number_id')


def upgrade_geoname() -> None:
    """Upgrade database bind 'geoname'."""


def downgrade_geoname() -> None:
    """Downgrade database bind 'geoname'."""
