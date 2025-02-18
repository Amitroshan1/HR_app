"""removed 

Revision ID: c84b5d46d324
Revises: bd5bfb19dcd8
Create Date: 2025-02-10 12:30:29.615587

"""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

# revision identifiers, used by Alembic.
revision = 'c84b5d46d324'
down_revision = 'bd5bfb19dcd8'
branch_labels = None
depends_on = None


def upgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('admins', schema=None) as batch_op:
        batch_op.drop_index('signup_id')
        batch_op.drop_constraint('admins_ibfk_1', type_='foreignkey')
        batch_op.drop_column('signup_id')

    # ### end Alembic commands ###


def downgrade():
    # ### commands auto generated by Alembic - please adjust! ###
    with op.batch_alter_table('admins', schema=None) as batch_op:
        batch_op.add_column(sa.Column('signup_id', mysql.INTEGER(), autoincrement=False, nullable=False))
        batch_op.create_foreign_key('admins_ibfk_1', 'signups', ['signup_id'], ['id'])
        batch_op.create_index('signup_id', ['signup_id'], unique=True)

    # ### end Alembic commands ###
