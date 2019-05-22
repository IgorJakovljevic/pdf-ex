from app import db

association_table = db.Table('AuthorDocument', db.Model.metadata,
    db.Column('author_id', db.Integer, db.ForeignKey('authors.id')),
    db.Column('document_id', db.Integer, db.ForeignKey('document.id'))
)

class Author(db.Model):
    __tablename__ = 'authors'
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))   
    documents = db.relationship(
        "Document",
        secondary=association_table,
        back_populates="authors")

    def __init__(self, name):
        """initialize with name."""
        self.name = name
    
    def save(self):
        db.session.add(self)
        db.session.commit()
    
    def delete(self):
        db.session.delete(self)
        db.session.commit()

    @staticmethod
    def get_all( author_names):
        # TODO: Fix so it loads properly
        authors = Author.query.order_by(Author.id.desc()).all() 
        
        return_authors = []
        for author in authors:
            if(author.name.lower() in author_names):
                return_authors.append(author)                
        return return_authors  
    
    @staticmethod
    def get_all_new_authors(author_names):
        # TODO: Fix so it loads properly
        authors = Author.query.order_by(Author.id.desc()).all() 
        old_authors = [author.name.lower() for author in authors]
        return_authors = []
        for author_name in author_names:

            if(not author_name in old_authors):
                return_authors.append(author_name)                
        return return_authors

class Document(db.Model):
    """This class represents the document table."""

    __tablename__ = 'document'

    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(255))
    location = db.Column(db.String(255))
    date_created = db.Column(db.DateTime, default=db.func.current_timestamp())
    authors = db.relationship(
        "Author",
        secondary=association_table,
        back_populates="documents")

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