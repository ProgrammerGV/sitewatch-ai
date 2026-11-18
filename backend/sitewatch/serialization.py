"""Database-row serialization shared by the HTTP route groups."""


def row_dict(row) -> dict:
    return {column.name: getattr(row, column.name) for column in row.__table__.columns}
