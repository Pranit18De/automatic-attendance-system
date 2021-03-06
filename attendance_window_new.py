import cv2
import numpy as np
import os
import time
from PIL import Image, ImageEnhance, ImageStat
import shutil
import sqlite3
import datetime
import math
import face_recognition

from check_attendance import CheckAttendance
from PyQt4 import QtGui,QtCore

def improve_image(file_name):
    img = Image.open(file_name)
    stat = ImageStat.Stat(img)
    orglvl = stat.mean[0]
    
    #1 Brightness
    brght = ImageEnhance.Brightness(img)
    if (orglvl<100):
        x = 100/orglvl
        brght_img = brght.enhance(x)
    else:
        brght_img = brght.enhance(1.0)
                     

    #2 Sharpness
    contrast = ImageEnhance.Sharpness(brght_img)
    shrp_img = contrast.enhance(1.0)    

    #3 Color
    color = ImageEnhance.Color(shrp_img)
    clr_img = color.enhance(0.0)

    #4 Resize
    rsz_img = clr_img.resize((200, 200), Image.ANTIALIAS)
    return rsz_img

conn=sqlite3.connect('Attendance System.db')
c=conn.cursor()

class AttendanceWindow(QtGui.QMainWindow):
    #Attendance Window
    def __init__(self):
        super(AttendanceWindow, self).__init__()
        self.setGeometry(300,50,800,600)
        self.setWindowTitle("Attendance")
        self.setWindowIcon(QtGui.QIcon('other_images/logo.png'))

        #Heading
        h=QtGui.QLabel(self)
        h.setAlignment(QtCore.Qt.AlignCenter)
        h.setGeometry(QtCore.QRect(200,20,400,50))
        h.setStyleSheet("QLabel { background-color : blue;color :white ; }")
        font=QtGui.QFont("Times",20,QtGui.QFont.Bold)
        h.setFont(font)
        h.setText("ATTENDANCE")

        #Label and Subject code entry
        l=QtGui.QLabel(self)
        l.setAlignment(QtCore.Qt.AlignCenter)
        l.setGeometry(QtCore.QRect(275,140,250,30))
        l.setStyleSheet("QLabel { background-color:green;color: white;}")
        font=QtGui.QFont("Times",16,QtGui.QFont.Bold) 
        l.setFont(font)
        l.setText("ENTER SUB-CODE")

        self.e = QtGui.QLineEdit(self)
        self.e.setGeometry(275,175,250,50)
        self.e.setAlignment(QtCore.Qt.AlignCenter)
        self.e.setFont(QtGui.QFont("Times",18,QtGui.QFont.Bold))

        #Recording Button
        b1=QtGui.QPushButton(self)
        b1.setText("RECORD AND MARK")
        b1.setStyleSheet("QPushButton { background-color : gray;color : black ; }")
        b1.setFont(font)
        b1.setGeometry(250,300,300,50)
        b1.clicked.connect(self.record_and_mark)

        #Check Attendance button to check specific subject's Attendance
        b2=QtGui.QPushButton(self)
        b2.setText("CHECK ATTENDANCE")
        b2.setStyleSheet("QPushButton { background-color : gray;color : black ; }")
        b2.setFont(font)
        b2.setGeometry(250,425,300,50)
        b2.clicked.connect(self.create_check_attendance)
        
    def create_check_attendance(self):
        #To check Validity of Subject Code 
        sub=["IT301","IT302"] #TO DO - GET THESE FROM TABLE
        if self.e.text() in sub:
            self._check_attendance = CheckAttendance(self.e.text())
            self._check_attendance.show()

    def record_and_mark(self):
        self.record() #to record the video and save it to folder 'videos'
        self.get_snaps() #to get snaps from the recorded video
        self.extract_faces() #to read all faces from the snaps
        self.match() #match extracted faces to those in database and update the database

    def record(self):
        #to save video with the name self.e.text()
        return

    def get_snaps(self):
        shutil.rmtree("temp",ignore_errors=True)
        os.mkdir("temp")
        os.mkdir("temp/presentFaces")
        os.mkdir("temp/frames")
        os.mkdir("temp/rawPresentFaces")
        video_name = str(self.e.text())
        crop_time = 2
        time_gap = 2
        #cv2 object created that uses the video capture function to open the video file
        cap = cv2.VideoCapture("videos/"+video_name+".mp4")
        fps    = int(cap.get(cv2.CAP_PROP_FPS))
        length = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        count = fps*(crop_time)
        i = 0
        cap.set(1,68)
        while (cap.isOpened()):
            ret , frame = cap.read()
            if(count>length):
                break   
            cv2.waitKey(3)
            if( (count == (crop_time*fps + i*time_gap*fps)) &(count < length)):
                cv2.imwrite('temp/frames/frame'+str(i)+'.jpg',frame)
                i = i+1
                print('snap taken @', count)
            count = count + 1
        cap.release()
        cv2.destroyAllWindows()
        print (i, "snaps taken")


    def extract_faces(self):
        i=0
        face_cascade = cv2.CascadeClassifier("support_files/haarcascade_frontalface_default.xml")
        for eachImg in os.listdir("temp/frames"):
            print(eachImg, 'read')
            img = cv2.imread("temp/frames/" + eachImg, 0)
            faces = face_cascade.detectMultiScale(img) 
            for(x,y,w,h) in faces:
                sub_face = img[y:y+h, x:x+w]
                face_file_name = "temp/rawPresentFaces/face_" + str(i) + ".jpg"
                cv2.imwrite(face_file_name, sub_face)
                new_image = improve_image(face_file_name)
                new_image.save("temp/presentFaces/face_" + str(i) + ".jpg")
                i=i+1
        cv2.waitKey(0)
        cv2.destroyAllWindows()
        print (i, 'faces read')

    def match(self):
        subject = str(self.e.text())
        xyear = (int(subject[2])+1)//2
        # registration picts are in "registration_images/Year2" -> picts are labelled with roll no.
        # extracted faces are in "temp/presentFaces"

        present = {}
        known_faces = []
        known_faces_names = []
        path = "registration_images/Year"+str(xyear)
        imagePaths=[os.path.join(path,f) for f in os.listdir(path)]
        for imagePath in imagePaths:
            img = face_recognition.load_image_file(imagePath)
            known_faces_names.append(imagePath.split(".")[0].split("\\")[1])
            if len(face_recognition.face_encodings(img)) != 0:
                known_faces.append(face_recognition.face_encodings(img)[0])
        # print(known_faces_names)
        path = "temp/presentFaces"
        imagePaths=[os.path.join(path,f) for f in os.listdir(path)]
        for imagePath in imagePaths:
            img = face_recognition.load_image_file(imagePath)
            try:
                unknown_face_encoading = face_recognition.face_encodings(img)[0]
            except IndexError:
                continue
            print(imagePath," Read...")
            results = face_recognition.compare_faces(known_faces, unknown_face_encoading)
            indices = [i for i, x in enumerate(results) if x == True]
            for each in indices:
                present[known_faces_names[each]] = "Present"
        print(present)

        #present = {'33': 'Present', '70': 'Present', '39': 'Present', '67': 'Present', '1': 'Present'}#this dictionary will have the rolls of all students with status.
        
        # getting all the rolls, names of year 2 students from database
        xyear = (int(subject[2])+1)//2
        
        query='SELECT * FROM YEAR{};'.format(xyear)
        c.execute(query)
        rolls = []
        names = []
        for row in c.fetchall():
            rolls.append(row[0])
            names.append(row[1])
            
        temp = []
        for r in rolls:
            if (r in present):
                temp.append('P')
            else:
                temp.append('A')
        
        rolls = list(map(str, rolls))        
        query='INSERT INTO VALUES (20171018,{});'.format(subject, ','.join(rolls), ','.join(temp))
        print (query)
        c.execute(query)

            
if __name__ == '__main__':
    app = QtGui.QApplication([])
    gui = AttendanceWindow()
    gui.show()
    app.exec_()
    c.close()
    conn.commit()
    print ("Data committed")
    conn.close()