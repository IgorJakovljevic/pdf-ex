
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
# sys.setdefaultencoding() does not exist, here!
reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

# initialize sql-alchemy
db = SQLAlchemy()


def create_app(config_name):
    from .models import Document
    app = FlaskAPI(__name__, instance_relative_config=True)
    CORS(app)
    app.config.from_object(app_config[config_name])
    app.config.from_pyfile('config.py')
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    db.init_app(app)
    
    def word_extraction(text, folder, file, file_id):
        print("word_extraction 1")
        porter = nltk.PorterStemmer()
        stop_words = set(stopwords.words('english') + list(string.punctuation) + ['the', 'in', 'for', 'the ']) 
        print("word_extraction 2")
        words = nltk.word_tokenize(text)
        words = [w for w in words if not w in stop_words] 
        words = [w for w in words if len(w) > 2] 
        words = [porter.stem(t) for t in words]
        print("word_extraction 3")
        fdist = FreqDist(words) 
        print("word_extraction 4")       
        wordlist_file = folder + str(file_id) +"worddist.json"
        print("word_extraction 5")
        print(wordlist_file)
        with open(wordlist_file, "w") as f:       
            f.write(json.dumps(fdist.most_common(50)))
        print("word_extraction")

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
            directory = folder+file_id            
            if not os.path.exists(directory):
                os.makedirs(directory)

            for img in doc.getPageImageList(i):
                xref = img[0]
                pix = fitz.Pixmap(doc, xref)
                if pix.n < 5:       # this is GRAY or RGB
                    pix.writePNG("%s%s/p%s-%s.png" % (folder, file_id, i, xref))
                else:               # CMYK: convert to RGB first
                    pix1 = fitz.Pixmap(fitz.csRGB, pix)
                    pix1.writePNG("%s%sp%s-%s.png" % (folder,file_id, i, xref))
                    pix1 = None
                pix = None 

    def extract_abstract(folder, file, file_id):
        abstract_file = folder + str(file_id) +"abstract.txt"
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

    @app.route('/getdocuments', methods=['GET'])
    def get_files():
        documents = Document.get_all()
        results = []

        for document in documents:
            try:               
                obj = {
                'id': document.id,
                'name': document.name,
                'date_created': document.date_created,
                'location': document.location,
                'information': get_file_info(document.location)
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
        
        basedir = os.path.abspath(os.path.dirname(__file__))
        file_dir = os.path.join(basedir, app.config['UPLOAD_FOLDER'], str(id))    
        image_locations = []
        abstract = ""
        word_dist = dict()
        if(os.path.isdir(file_dir)):
            image_locations = os.listdir(file_dir)  
            abstract_location = file_dir + "abstract.txt"
            if os.path.isfile(abstract_location):
                with open(abstract_location, 'r') as myfile:
                    abstract = myfile.read()             
            word_dist_location = file_dir + "worddist.json"   
            if os.path.isfile(word_dist_location):
                with open(word_dist_location, 'r') as myfile:
                    print("HERE")
                    word_dist = json.load(myfile)             

            file_dir = file_dir + "/"

        results["images"] = image_locations
        results["images_base_dir"] = file_dir
        results["abstract"] = abstract
        results["word_dist"] = word_dist
        response = jsonify(results)
        response.status_code = 200
        return response


    @app.route('/fileupload', methods=['POST'])
    def upload_file():
        if request.method == 'POST':            
            # check if the post request has the file part
            if 'file' not in request.files:
                print('No file part')
                return redirect(request.url)
            file = request.files['file']
            if file.filename == '':
                flash('No selected file')
                return redirect(request.url)
            
            try:
                filename = file.filename
                
                basedir = os.path.abspath(os.path.dirname(__file__))
                new_path = os.path.join(basedir, app.config['UPLOAD_FOLDER'], filename)
                
                document = Document(name = file.filename, location=new_path)
                document.save()                
                file.save(new_path)
                file_folder = os.path.join(basedir, app.config['UPLOAD_FOLDER'])
                extract_image(file_folder, filename, document.id)
                extract_abstract(file_folder, filename, document.id)
                obj = {
                'id': document.id,
                'name': document.name,
                'date_created': document.date_created,
                'location': document.location,
                'information': get_file_info(document.location)
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

    return app