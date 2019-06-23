
from flask import request, url_for, send_from_directory
from flask import jsonify, abort, send_file
from flask_api import FlaskAPI, status, exceptions
from flask_sqlalchemy import SQLAlchemy

from flask_cors import CORS

from PyPDF2 import PdfFileReader
import os
import fitz
import textract
import nltk
import json
import string
from nltk.probability  import FreqDist 
from nltk.corpus import stopwords
# local import
from instance.config import app_config

import sys
import requests
# sys.setdefaultencoding() does not exist, here!
reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

# initialize sql-alchemy
db = SQLAlchemy()


def create_app(config_name):
    from .models import Document, Author
    app = FlaskAPI(__name__, instance_relative_config=True)
    CORS(app)
    app.config.from_object(app_config[config_name])
    app.config.from_pyfile('config.py')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    def word_extraction(text, folder, file, file_id):
        porter = nltk.PorterStemmer()
        stop_words = set(stopwords.words('english') + list(string.punctuation) + ['the', 'in', 'for', 'the ']) 
        words = nltk.word_tokenize(text)
        words = [w for w in words if not w in stop_words] 
        words = [w for w in words if len(w) > 2] 
        words = [porter.stem(t) for t in words]
        fdist = FreqDist(words)      
        wordlist_file = folder + str(file_id) +"/worddist.json"
        print(wordlist_file)
        with open(wordlist_file, "w") as f:       
            f.write(json.dumps(fdist.most_common(50)))

    def get_file_info(path):
        with open(path, 'rb') as f:
            pdf = PdfFileReader(f)
            info = pdf.getDocumentInfo()
            number_of_pages = pdf.getNumPages() 

        return info, number_of_pages

    def extract_image(folder, file, file_id):        
        file_id = str(file_id)
        doc = fitz.open(folder + file)
        for i in range(len(doc)):            
            directory = folder + file_id  +"/images"          
            if not os.path.exists(directory):
                os.makedirs(directory)

            for img in doc.getPageImageList(i):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.n < 5:       # this is GRAY or RGB
                    pix.writePNG("%s%s/images/p%s-%s.png" % (folder, file_id, i, xref))
                else:               # CMYK: convert to RGB first
                    pix1 = fitz.Pixmap(fitz.csRGB, pix)
                    pix1.writePNG("%s%s/images/p%s-%s.png" % (folder,file_id, i, xref))
                    pix1 = None
                pix = None 

    def extract_abstract_text(folder, file):
        text = textract.process(folder + file)
        with open("text.txt", "w") as f:         
            f.write(text)

        abastract = ""
        
        with open("text.txt") as infile:
            copy = False
            
            for line in infile:
                line = line.strip()
                if ("abstract" in line or "Abstract" in line):
                    copy = True

                elif(not line and copy):
                    break
                
                elif "\n" in line or "\r" in line:
                    copy = False
                    break

                if copy:                    
                    abastract += line
        os.remove("text.txt")
        return abastract

    def save_words(folder, file, file_id):
        text = textract.process(folder + file)
        word_extraction(text, folder, file, file_id)

    def save_abstract(folder, file, file_id, abstract):
        abstract_file = folder + "/" + str(file_id) +"/abstract.txt"       
        with open(abstract_file, 'w') as outfile:
            outfile.write(abstract)

    def extract_abstract(folder, file, file_id):
        abstract_file = folder + "/" + str(file_id) +"/abstract.txt"
        text = textract.process(folder + file)
        word_extraction(text, folder, file, file_id)
        with open("text.txt", "w") as f:         
            f.write(text)

        with open("text.txt") as infile, open(abstract_file, 'w') as outfile:
            copy = False
            
            for line in infile:
                line = line.strip()
                if ("abstract" in line or "Abstract" in line):
                    copy = True

                elif(not line and copy):
                    break
                
                elif "\n" in line or "\r" in line:
                    copy = False
                    break

                if copy:
                    outfile.write(line)
        os.remove("text.txt")

    def load_save_author_data(file_folder, file_id, authors):
        directory = file_folder+ "/" + str(file_id) +"/author/"
        if not os.path.exists(directory):
            os.makedirs(directory)

        for ix, author in enumerate(authors):            
            r = requests.get('https://dblp.org/search/publ/api', params={'format': 'json', 'q':author})     
            authod_data_file = directory+str(ix)+".json"
            with open(authod_data_file, "w") as f: 
                item = json.dumps(r.content)
                item = item.rstrip('\r')    
                item = item.replace('\r', '')      
                f.write(item)

    @app.route('/author', methods=['POST'])
    def save_author():
        fullname =  request.form.get('fullname')
        author = Author(fullname)
        author.save()

        response = jsonify(author)
        response.status_code = 200
        return response
    
    @app.route('/author', methods=['GET'])
    def get_authors():
        authors = Author.query.order_by(Author.id.desc()).all()
        results = []
        for author in authors:
            obj = {
            'id': author.id,
            'name': author.name    ,
            'documents' : [[document.name, document.id] for document in author.documents] 
            }
            results.append(obj)

        response = jsonify(results)
        response.status_code = 200
        return response
    

    @app.route('/getallauthors', methods=['GET'])
    def get_all_authors():                
        authors = Author.query.order_by(Author.id.desc()).all()
        results = []
        for author in authors:
            obj = {
            'id': author.id,
            'name': author.name ,
            'documents' : [[document.name, document.id] for document in author.documents] 
            }
            results.append(obj)

        response = jsonify(results)
        response.status_code = 200
        return response

    @app.route('/authors', methods=['GET'])
    def get_authors_byname():                
        authors =  request.args.get('authors')        
        authors = authors.split(',')  
        authors = [x.lower() for x in authors]  
        authors = Author.get_all(authors)
        results = []
        for author in authors:
            obj = {
            'id': author.id,
            'name': author.name,
            'documents' : [[document.name, document.id] for document in author.documents] 
            }
            results.append(obj)

        response = jsonify(results)
        response.status_code = 200
        return response

    @app.route('/getauthordocuments/<id>', methods=['GET'])
    def get_author_documents(id):
        _id = int(id)        
        author = Author.query.filter_by(id=_id).first()
        author_name = author.name
        documents = author.documents

        results = []
        result = {}
        basedir = os.path.abspath(os.path.dirname(__file__))
        file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'], str(id))   

        for document in documents:
            
            file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'], str(document.id))               
            word_dist = dict()
            word_dist_location = file_dir + "/worddist.json" 
            if os.path.isfile(word_dist_location):
                with open(word_dist_location, 'r') as myfile:                    
                    word_dist = json.load(myfile)  
            print(document.authors)
            authors = ",".join([author.name for author in document.authors])
            try:               
                obj = {
                'id': document.id,
                'name': document.name,
                'date_created': document.date_created,
                'location': document.location,
                'information': get_file_info(document.location),
                'authors': authors,
                "word_dist": word_dist                 
                }
                results.append(obj)
            except Exception as e:
                continue
        result['documents']= results
        result['author']= author_name
        response = jsonify(result)
        response.status_code = 200
        return response

    @app.route('/getdocuments/', defaults={'query': ""})
    @app.route('/getdocuments/<query>', methods=['GET'])
    def get_files(query):
        documents = Document.query.filter(Document.name.ilike("%"+query+"%"))
        results = []
        basedir = os.path.abspath(os.path.dirname(__file__))
        file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'], str(id))   

        for document in documents:
            
            file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'], str(document.id))               
            word_dist = dict()
            word_dist_location = file_dir + "/worddist.json" 
            if os.path.isfile(word_dist_location):
                with open(word_dist_location, 'r') as myfile:                    
                    word_dist = json.load(myfile)  
            print(document.authors)
            authors = ",".join([author.name for author in document.authors])
            try:               
                obj = {
                'id': document.id,
                'name': document.name,
                'date_created': document.date_created,
                'location': document.location,
                'information': get_file_info(document.location),
                'authors': authors,
                "word_dist": word_dist                 
                }
                results.append(obj)
            except Exception as e:
                continue
            
        response = jsonify(results)
        response.status_code = 200
        return response

    @app.route("/getdocument/<id>", methods=['GET'])
    def get_file(id):
        _id = int(id)        
        document = Document.query.filter_by(id=_id).first()
        location = get_file_info(document.location)
        results = dict()
        results["file_info"] = location
        results["location"] = document.location        
        results["authors"] = [{"name": author.name, "id": author.id}for author in document.authors]
        results["title"] = document.name
        basedir = os.path.abspath(os.path.dirname(__file__))
        file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'], str(id))    
        image_locations = []
        abstract = ""
        word_dist = dict()
        author_data = []
        if(os.path.isdir(file_dir)):
            image_locations = os.listdir(file_dir + "/images/")  
            abstract_location = file_dir + "/abstract.txt"
            if os.path.isfile(abstract_location):
                with open(abstract_location, 'r') as myfile:
                    abstract = myfile.read()             
            word_dist_location = file_dir + "/worddist.json"   
            
            if os.path.isfile(word_dist_location):
                with open(word_dist_location, 'r') as myfile:                    
                    word_dist = json.load(myfile)             

            author_data_locations = os.listdir(file_dir + "/author/") 
            print(author_data_locations)
            for author_data_loc in author_data_locations:
                with open(file_dir + "/author/" +author_data_loc, 'r') as myfile:                    
                    author_data.append(json.load(myfile))
                        
            file_dir = file_dir + "/"

        results["images"] = image_locations 
        results["images_base_dir"] = file_dir + "/images/"
        results["abstract"] = abstract
        results["word_dist"] = word_dist
        results["author_data"] = author_data
        response = jsonify(results)
        response.status_code = 200
        return response

    def add_new_authors(authors):
        authors = [x.lower() for x in authors]  
        authors = Author.get_all_new_authors(authors)
        for author in authors:
            
            author = Author(author)
            author.save()


    @app.route('/upload_file', methods=['POST'])
    def upload_file():
        if request.method == 'POST':            
            # check if the post request has the file part
            if 'file' not in request.files:                
                return redirect(request.url)
            print("HERE2")
            file = request.files['file']
            title =  request.form.get('title')
            authors =  request.form.get('authors')
            abstract =  request.form.get('abstract')
            authors = authors.split(',')
            add_new_authors(authors)
            print("HERE1")
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            
            try:
                filename = file.filename
                
                basedir = os.path.abspath(os.path.dirname(__file__))
                new_path = os.path.join(basedir, app.config['UPLOAD_FOLDER'], filename)
                print("HERE3")
                document = Document(name = file.filename, location=new_path)
                authors = [x.lower() for x in authors]  
                authors = Author.get_all(authors)
                document.authors = authors
                print("HERE4")
                document.save()  
                print("HERE5")
                
                file.save(new_path)
                file_folder = os.path.join(basedir, app.config['UPLOAD_FOLDER'])
                extract_image(file_folder, filename, document.id)                
                save_abstract(file_folder, filename, document.id, abstract)
                save_words(file_folder, filename, document.id)
                file_info = get_file_info(document.location)
                load_save_author_data(file_folder, document.id, authors)

                obj = {
                'id': document.id,
                'name': document.name,
                'date_created': document.date_created,
                'location': document.location,
                'information': file_info
                }

                
                response = jsonify(obj)
                response.status_code = 200
                return response
            except Exception as e: 
                print(e)       
            
            return '''
            <!doctype html>
            <title>Upload new File</title>
            <h1>Upload new File</h1>
            <form method=post enctype=multipart/form-data>
            <p><input type=file name=file>
                <input type=submit value=Upload>
            </form>
            '''


    @app.route('/preprocessfile', methods=['POST'])
    def preprocess_file():
        if request.method == 'POST':            
            # check if the post request has the file part
            if 'file' not in request.files:                
                return redirect(request.url)
            file = request.files['file']
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            
            try:
                filename = file.filename
                temp_location = "temp_preprocess.pdf"
                basedir = os.path.abspath(os.path.dirname(__file__))
                file_folder = os.path.join(basedir, app.config['UPLOAD_FOLDER'])
                new_path = os.path.join(file_folder, temp_location)                                                
                file.save(new_path)                                
                abstract = extract_abstract_text(file_folder, temp_location)
                file_info = get_file_info(new_path)                

                obj = {                
                'name': filename,
                'information': file_info,
                'abstract':abstract
                }
                response = jsonify(obj)
                response.status_code = 200
                return response
            except Exception as e: 
                print(e)       
        response.status_code = 500
        return response

    return app