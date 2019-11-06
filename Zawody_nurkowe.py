import cv2
import numpy as np
import imutils
import threading
from threading import Lock
import math
import msvcrt
import os
import sqlite3
from datetime import datetime
import time

orangeLower = (0, 75, 0)
orangeUpper = (60, 255, 255)

class Camera:
    last_frame = None
    last_ready = None
    lock = Lock()

    def __init__(self, rtsp_link):
        capture = cv2.VideoCapture(rtsp_link)
        thread = threading.Thread(target=self.rtsp_cam_buffer, args=(capture,), name="rtsp_read_thread")
        thread.daemon = True
        thread.start()

    def rtsp_cam_buffer(self, capture):
        while True:
            with self.lock:
                self.last_ready, self.last_frame = capture.read()


    def getFrame(self):
        if (self.last_ready is not None) and (self.last_frame is not None):
            return imutils.resize(self.last_frame, width=960).copy()
        else:
            return None

def Get_center(frame):
    if(frame is not None):
        blurred = cv2.GaussianBlur(frame, (11, 11), 0)
        hsv = cv2.cvtColor(blurred, cv2.COLOR_BGR2HSV)
        mask = cv2.inRange(hsv, orangeLower, orangeUpper)
        mask = cv2.erode(mask, None, iterations=2)
        mask = cv2.dilate(mask, None, iterations=2)
        cnts = cv2.findContours(mask.copy(), cv2.RETR_EXTERNAL,cv2.CHAIN_APPROX_SIMPLE)
        cnts = imutils.grab_contours(cnts)
        center = None
        if len(cnts) > 0:
            c = max(cnts, key=cv2.contourArea)
            M = cv2.moments(c)
            center = (int(M["m10"] / M["m00"]), int(M["m01"] / M["m00"]))
    return center

def Measure_person(id = 0):
    print("Start " + str(id))
    cap = None
    if(id == 0):
        cap = Camera('rtsp://192.168.1.238:554/user=admin_password=tlJwpbo6_channel=1_stream=0.sdp?real_stream')
    elif(id == 1):
        cap = Camera('Nagrania_2019-09-26_20-05-27.mp4')
    else:
        cap = Camera('Nagrania_2019-09-21_17-01-54.mp4')
    frame = cap.getFrame()
    while(frame is None):
        frame = cap.getFrame()
        key = cv2.waitKey(100)
        if key==27:
            break
    center = Get_center(frame)
    distance = 0
    start = time.time()
    while(frame is not None):
        center_old = center
        center = Get_center(frame)
        if(center is None):
            center = center_old
        #print("old " + str(center_old) + " new " + str(center))
        distance += math.sqrt(pow((center_old[0]-center[0]),2) + pow((center_old[1]-center[1]),2))
        cv2.circle(frame, center, 5, (0, 0, 255), -1)
        cv2.imshow("Camera view", frame)
        frame = cap.getFrame()
        key = cv2.waitKey(1)
        if key==27:
            break
    duration = time.time() - start
    print(distance)
    print(duration)
    print("Stop personID: " + str(id) + " distance= " + str(distance/ duration))
    cv2.destroyAllWindows()
    return distance, duration
    
    
def Get_user_from_database(id):
    name = "Test"
    return True, name
    
    
def Get_userid_from_console():
    isvalid = False
    id = str(input("\nPodaj identyfikator zawodnika (q-cofnij): "))
    for i in range(1, 3):
        try:
            isvalid, name = Get_user_from_database(int(id))
        except ValueError:
            isvalid = False
        if isvalid == True:
            return True, id 
        id = str(input("\nNieznaleziono identyfikatora zawodnika (q-cofnij): "))
        if key == 'q' or key == 'Q':
            break
    return False, None
    


if __name__== "__main__":
    connection = sqlite3.connect('example.db')
    while(True):
        key = str(input("\nWybierz \nq-wyjście\nh-pomoc\np-nowy pomiar\n\nKomenda: "))
        if key == 'q' or key == 'Q':
            break
        elif key == 'h' or key == 'H':
            print("Wyjście z programu - wpisz koemndę q.")
        elif key == 'p' or key == 'P':
            confirm, person_id = Get_userid_from_console()
            if confirm == True:
                distance, duration = Measure_person(person_id)
                today = datetime.now()
                now_date = today.year * 10000 + today.month * 100 + today.day
                now_time = today.hour * 10000 + today.minute * 100 + today.second
                curs = connection.cursor()
                sql = '''INSERT INTO Pomiary(zawodnik,czas,droga,data,time) VALUES(?,?,?,?,?)'''
                pomiar = (person_id, duration, distance, now_date, now_time)
                print(pomiar)
                curs.execute(sql, pomiar)
                connection.commit()
        else:
            print("Błędna komenda")
