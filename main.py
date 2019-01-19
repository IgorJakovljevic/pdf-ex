import fitz
import json
import textract

import re
import string
import cv2
import numpy as np
import nltk
from nltk.probability  import FreqDist 
from nltk.corpus import stopwords
from PyPDF2 import PdfFileReader

import sys
# sys.setdefaultencoding() does not exist, here!
reload(sys)  # Reload does the trick!
sys.setdefaultencoding('UTF8')

pdf_file = "file.pdf"
folder = "data/"
def extract_image(file, folder):
    doc = fitz.open(file)
    for i in range(len(doc)):
        import os
        directory = folder+file
        if not os.path.exists(directory):
            os.makedirs(directory)

        for img in doc.getPageImageList(i):
            xref = img[0]
            pix = fitz.Pixmap(doc, xref)
            if pix.n < 5:       # this is GRAY or RGB
                pix.writePNG("%s%s/p%s-%s.png" % (folder, file, i, xref))
            else:               # CMYK: convert to RGB first
                pix1 = fitz.Pixmap(fitz.csRGB, pix)
                pix1.writePNG("%s%sp%s-%s.png" % (folder,file, i, xref))
                pix1 = None
            pix = None 
 
def get_info(path):
    with open(path, 'rb') as f:
        pdf = PdfFileReader(f)
        info = pdf.getDocumentInfo()
        number_of_pages = pdf.getNumPages() 

    return info, number_of_pages

def get_page_number(path):
    with open(path, 'rb') as f:
        pdf = PdfFileReader(f)
        info = pdf.getDocumentInfo()
        number_of_pages = pdf.getNumPages() 

    return number_of_pages

# extract_image(pdf_file, folder)

res = get_info(pdf_file)
number_of_pages = get_page_number(pdf_file)
text = textract.process(pdf_file)
f = open("text.txt", "w")
f.write(text)


with open('text.txt') as infile, open('abstract.txt', 'w') as outfile:
    copy = False
    
    for line in infile:
        print(1)
        line = line.strip()
        if ("abstract" in line or "Abstract" in line):
            print(line)
            copy = True

        elif(not line and copy):
            print(line)
            print("This was the end")
            break
        
        elif "\n" in line or "\r" in line:
            print("new_line")
            print(line)
            copy = False
            break

        if copy:
            outfile.write(line)
exit()
f = open("metadata.json", "w")
f.write(json.dumps(res))


porter = nltk.PorterStemmer()
stop_words = set(stopwords.words('english') + list(string.punctuation) + ['the', 'in', 'for', 'the ']) 

words = nltk.word_tokenize(text)
words = [w for w in words if not w in stop_words] 
words = [w for w in words if len(w) > 2] 
words = [porter.stem(t) for t in words]
fdist = FreqDist(words)



comon_words = fdist.most_common(50)

f = open("worddist.json", "w")
f.write(json.dumps(fdist.most_common(50)))


searchwords=[word[0] for word in comon_words]
pages_text=[]
words_start_pos={}
words={}
pdfReader= PdfFileReader(pdf_file)
with open('FoundWordsList.csv', 'w') as f:
    f.write('{0},{1}\n'.format("Sheet Number", "Search Word"))
    for word in searchwords:
        for page in range(number_of_pages):            
            pages_text.append(pdfReader.getPage(page).extractText())
            words_start_pos[page]=[dwg.start() for dwg in re.finditer(word, pages_text[page].lower())]
            words[page]=[pages_text[page][value:value+len(word)] for value in words_start_pos[page]]
        for page in words:
            for i in range(0,len(words[page])):
               if str(words[page][i]) != 'nan':
                    f.write('{0},{1}\n'.format(page+1, words[page][i]))

img = cv2.imread('images/GoldenGateSunset.png', -1)
color = ('b','g','r')
histogram = dict()
for channel,col in enumerate(color):
    histr = cv2.calcHist([img],[channel],None,[256],[0,256])
    histogram[channel] = histr
print(histogram)

print("DONE")                    