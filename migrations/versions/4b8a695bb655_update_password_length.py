"""Update password length

Revision ID: 4b8a695bb655
Revises: cee41d03a4fa
Create Date: 2024-09-19 14:00:46.008835

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = '4b8a695bb655'
down_revision = 'cee41d03a4fa'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('change_passowrds', schema=None) as batch_op:
        batch_op.drop_index('email')
        batch_op.drop_index('username')

    op.drop_table('change_passowrds')
    with op.batch_alter_table('admins', schema=None) as batch_op:
        batch_op.alter_column('password',
               existing_type=mysql.VARCHAR(length=150),
               type_=sa.String(length=350),
               existing_nullable=False)

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('admins', schema=None) as batch_op:
        batch_op.alter_column('password',
               existing_type=sa.String(length=350),
               type_=mysql.VARCHAR(length=150),
               existing_nullable=False)

    op.create_table('change_passowrds',
    sa.Column('id', mysql.INTEGER(), autoincrement=True, nullable=False),
    sa.Column('username', mysql.VARCHAR(length=150), nullable=False),
    sa.Column('email', mysql.VARCHAR(length=150), nullable=False),
    sa.Column('password', mysql.VARCHAR(length=200), nullable=False),
    sa.Column('admin_id', mysql.INTEGER(), autoincrement=False, nullable=False),
    sa.ForeignKeyConstraint(['admin_id'], ['admins.id'], name='change_passowrds_ibfk_1'),
    sa.PrimaryKeyConstraint('id'),
    mysql_collate='utf8mb4_0900_ai_ci',
    mysql_default_charset='utf8mb4',
    mysql_engine='InnoDB'
    )
    with op.batch_alter_table('change_passowrds', schema=None) as batch_op:
        batch_op.create_index('username', ['username'], unique=True)
        batch_op.create_index('email', ['email'], unique=True)

    # ### end Alembic commands ###
