from app import db


class Document(db.Model):
    """This class represents the document table."""

    __tablename__ = 'document'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    location = db.Column(db.String(255))
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())


    def __init__(self, name, location):
        """initialize with name."""
        self.name = name
        self.location = location

    def save(self):
        db.session.add(self)
        db.session.commit()

    @staticmethod
    def get_all():
        return Document.query.order_by(Document.id.desc()).all()

    def delete(self):
        db.session.delete(self)
        db.session.commit()

    def __repr__(self):
        return "<Document: {}>".format(self.name)