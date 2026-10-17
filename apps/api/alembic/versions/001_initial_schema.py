"""Initial multi-tenant schema migration for WapiFlow.

Revision ID: 001_initial_schema
Revises:
Create Date: 2026-10-17 00:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = '001_initial_schema'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Profiles
    op.create_table(
        'profiles',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('full_name', sa.String(length=255), nullable=True),
        sa.Column('phone_number', sa.String(length=32), nullable=True),
        sa.Column('avatar_url', sa.String(length=1024), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_profiles_email', 'profiles', ['email'], unique=True)

    # 2. Businesses
    op.create_table(
        'businesses',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('slug', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=32), nullable=True),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=False),
        sa.Column('timezone', sa.String(length=64), server_default='UTC', nullable=False),
        sa.Column('logo_url', sa.String(length=1024), nullable=True),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_businesses_slug', 'businesses', ['slug'], unique=True)

    # 3. Business Members
    op.create_table(
        'business_members',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('user_id', sa.Uuid(), nullable=False),
        sa.Column('role', sa.String(length=32), server_default='staff', nullable=False),
        sa.Column('is_active', sa.Boolean(), nullable=False, server_default=sa.text('true')),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['user_id'], ['profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_id', 'user_id', name='uq_business_member')
    )
    op.create_index('ix_business_members_business_id', 'business_members', ['business_id'])
    op.create_index('ix_business_members_user_id', 'business_members', ['user_id'])

    # 4. Business Settings
    op.create_table(
        'business_settings',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('auto_decrement_stock', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('order_prefix', sa.String(length=16), server_default='WF-', nullable=False),
        sa.Column('whatsapp_catalog_id', sa.String(length=255), nullable=True),
        sa.Column('notification_phone', sa.String(length=32), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_id')
    )

    # 5. Subscriptions
    op.create_table(
        'subscriptions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('plan_tier', sa.String(length=32), server_default='free', nullable=False),
        sa.Column('status', sa.String(length=32), server_default='active', nullable=False),
        sa.Column('current_period_end', sa.DateTime(timezone=True), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_id')
    )

    # 6. Products
    op.create_table(
        'products',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('sku', sa.String(length=64), nullable=False),
        sa.Column('description', sa.Text(), nullable=True),
        sa.Column('price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('compare_at_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('cost_price', sa.Numeric(precision=12, scale=2), nullable=True),
        sa.Column('stock_quantity', sa.Integer(), server_default='0', nullable=False),
        sa.Column('track_inventory', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('image_url', sa.String(length=1024), nullable=True),
        sa.Column('is_active', sa.Boolean(), server_default=sa.text('true'), nullable=False),
        sa.Column('is_archived', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_id', 'sku', name='uq_business_product_sku')
    )
    op.create_index('ix_products_business_id', 'products', ['business_id'])
    op.create_index('ix_products_name', 'products', ['name'])
    op.create_index('ix_products_sku', 'products', ['sku'])

    # 7. Customers
    op.create_table(
        'customers',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('phone_number', sa.String(length=32), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=True),
        sa.Column('delivery_address', sa.Text(), nullable=True),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('total_orders', sa.Integer(), server_default='0', nullable=False),
        sa.Column('total_spend', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_id', 'phone_number', name='uq_business_customer_phone')
    )
    op.create_index('ix_customers_business_id', 'customers', ['business_id'])
    op.create_index('ix_customers_phone_number', 'customers', ['phone_number'])

    # 8. Orders
    op.create_table(
        'orders',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('order_number', sa.String(length=64), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='pending', nullable=False),
        sa.Column('payment_status', sa.String(length=32), server_default='unpaid', nullable=False),
        sa.Column('source', sa.String(length=32), server_default='manual', nullable=False),
        sa.Column('subtotal', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('tax_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('discount_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('shipping_fee', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('total_amount', sa.Numeric(precision=12, scale=2), server_default='0.00', nullable=False),
        sa.Column('currency', sa.String(length=3), server_default='USD', nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('fulfillment_address', sa.Text(), nullable=True),
        sa.Column('idempotency_key', sa.String(length=128), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_id', 'idempotency_key', name='uq_business_order_idempotency')
    )
    op.create_index('ix_orders_business_id', 'orders', ['business_id'])
    op.create_index('ix_orders_order_number', 'orders', ['order_number'])
    op.create_index('ix_orders_status', 'orders', ['status'])

    # 9. Order Items
    op.create_table(
        'order_items',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('order_id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=True),
        sa.Column('product_name', sa.String(length=255), nullable=False),
        sa.Column('product_sku', sa.String(length=64), nullable=False),
        sa.Column('unit_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('quantity', sa.Integer(), nullable=False),
        sa.Column('total_price', sa.Numeric(precision=12, scale=2), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_order_items_order_id', 'order_items', ['order_id'])

    # 10. Order Status History
    op.create_table(
        'order_status_history',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('order_id', sa.Uuid(), nullable=False),
        sa.Column('previous_status', sa.String(length=32), nullable=True),
        sa.Column('new_status', sa.String(length=32), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('changed_by_user_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['changed_by_user_id'], ['profiles.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_order_status_history_order_id', 'order_status_history', ['order_id'])

    # 11. Inventory Movements
    op.create_table(
        'inventory_movements',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('product_id', sa.Uuid(), nullable=False),
        sa.Column('order_id', sa.Uuid(), nullable=True),
        sa.Column('change_quantity', sa.Integer(), nullable=False),
        sa.Column('movement_type', sa.String(length=64), nullable=False),
        sa.Column('notes', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['product_id'], ['products.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['order_id'], ['orders.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_inventory_movements_business_id', 'inventory_movements', ['business_id'])
    op.create_index('ix_inventory_movements_product_id', 'inventory_movements', ['product_id'])

    # 12. WhatsApp Connections
    op.create_table(
        'whatsapp_connections',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('phone_number_id', sa.String(length=128), nullable=False),
        sa.Column('waba_id', sa.String(length=128), nullable=False),
        sa.Column('display_phone_number', sa.String(length=32), nullable=True),
        sa.Column('quality_rating', sa.String(length=32), nullable=True),
        sa.Column('webhook_verified', sa.Boolean(), server_default=sa.text('false'), nullable=False),
        sa.Column('access_token', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('business_id')
    )

    # 13. WhatsApp Messages
    op.create_table(
        'whatsapp_messages',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('business_id', sa.Uuid(), nullable=False),
        sa.Column('customer_id', sa.Uuid(), nullable=True),
        sa.Column('wa_message_id', sa.String(length=255), nullable=False),
        sa.Column('direction', sa.String(length=16), nullable=False),
        sa.Column('sender_phone', sa.String(length=32), nullable=False),
        sa.Column('recipient_phone', sa.String(length=32), nullable=False),
        sa.Column('message_type', sa.String(length=32), server_default='text', nullable=False),
        sa.Column('content', sa.Text(), nullable=True),
        sa.Column('status', sa.String(length=32), server_default='sent', nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.ForeignKeyConstraint(['business_id'], ['businesses.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['customer_id'], ['customers.id'], ondelete='SET NULL'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('wa_message_id')
    )
    op.create_index('ix_whatsapp_messages_business_id', 'whatsapp_messages', ['business_id'])


def downgrade() -> None:
    op.drop_table('whatsapp_messages')
    op.drop_table('whatsapp_connections')
    op.drop_table('inventory_movements')
    op.drop_table('order_status_history')
    op.drop_table('order_items')
    op.drop_table('orders')
    op.drop_table('customers')
    op.drop_table('products')
    op.drop_table('subscriptions')
    op.drop_table('business_settings')
    op.drop_table('business_members')
    op.drop_table('businesses')
    op.drop_table('profiles')
