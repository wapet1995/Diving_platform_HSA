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
        cap = Camera('Nagrania_testowe/Nagrania_2019-09-26_20-05-27.mp4')
    else:
        cap = Camera('Nagrania_testowe/Nagrania_2019-09-21_17-01-54.mp4')
    frame = cap.getFrame()
    while(frame is None):
        frame = cap.getFrame()
        key = cv2.waitKey(1)
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
    curs = connection.cursor()
    curs.execute("SELECT imie FROM Zawodnicy WHERE  nr_start='%d'" %id)
    zawodnik = curs.fetchone()
    print(zawodnik)
    if(zawodnik is None):
        return False, None
    name = zawodnik[0]
    return True, name
    
    
def Add_user_to_database():
    name = str(input("\nPodaj imie zawodnika (q-cofnij): "))
    if(name == 'q'or name =='Q'):
        return False
    birthday_day = str(input("\nPodaj dzień urodzenia zawodnika 1-31(q-cofnij): "))
    if(birthday_day == 'q'or birthday_day =='Q'):
        return False
    birthday_month = str(input("\nPodaj miesiąc urodzenia zawodnika 1-12 (q-cofnij): "))
    if(birthday_month == 'q'or birthday_month =='Q'):
        return False
    birthday_year = str(input("\nPodaj rok urodzenia zawodnika (rrrr) (q-cofnij): "))
    if(birthday_year == 'q'or birthday_year =='Q'):
        return False
    if((name is not None) and (name != "") and (birthday_day.isdigit()) and (0 < int(birthday_day) < 32) and (birthday_month.isdigit()) and (0 < int(birthday_month) < 13) and (birthday_year.isdigit()) and (int(birthday_year) > 1900)):
        birthday = int(birthday_year) * 10000 + int(birthday_month) * 100 + int(birthday_day)
        print(birthday)
        curs = connection.cursor()
        sql = '''INSERT INTO Zawodnicy(imie,data_urodzenia) VALUES(?,?)'''
        zawodnik = (name, birthday)
        curs.execute(sql, zawodnik)
        connection.commit()
        curs.execute("SELECT nr_start FROM Zawodnicy WHERE imie=? and data_urodzenia=?", zawodnik)
        zawodnik_id = curs.fetchone()
        if(zawodnik_id is None):
            print("Nie udało się dodać zawodnika, spróbuj ponownie.")
            return False
        print("Numer zawodnika ", name, " jest ", zawodnik_id[0])
        return True
    else:
        print("Podano błędne dane zawodnika, spróbuj ponownie.")
    return False
    
    
def Get_userid_from_console():
    isvalid = False
    id = str(input("\nPodaj identyfikator zawodnika (q-cofnij): "))
    if id == 'q' or id == 'Q':
        return False, None
    for i in range(1, 3):
        try:
            isvalid, name = Get_user_from_database(int(id))
            if isvalid == True:
                decision = str(input("\nZnaleziono zawodnika o imieniu " + name + "\nCzy chcesz wykonać dla niego pomiar? T/N:"))
                isvalid = (decision == 't' or decision == 'T')
        except ValueError:
            isvalid = False
        if isvalid == True:
            return True, id
        id = str(input("\nNieznaleziono identyfikatora zawodnika, podaj inny (q-cofnij): "))
        if id == 'q' or id == 'Q':
            return False, None
    return False, None


def View_all_users_from_database():
    curs = connection.cursor()
    i = 1
    print('''Zawodnicy:\n\t%-6s%-16s%-10s%s''' %('lp', 'Numer startowy', 'Imię', 'Data urodzenia'))
    for row in curs.execute('SELECT nr_start, imie, data_urodzenia FROM Zawodnicy ORDER BY nr_start'):
        year = int(row[2] / 10000)
        month = int(row[2] %10000 / 100)
        day = int(row[2] %100)
        date_pom = "{0:04d}-{1:02d}-{2:02d}".format(year, month, day)
        print("\t%-6d%-16d%-10s%s"  %(i, row[0], row[1], date_pom))
        i += 1


def View_all_measures_from_database():
    curs = connection.cursor()
    i = 1
    print('''Pomiary:\n\t%-6s%-16s%-10s%-12s%-15s%-11s%-8s''' %('lp', 'Numer startowy', 'Imię', 'Czas [s]', 'Odległość', 'Dzień', 'Godzina'))
    for row in curs.execute('SELECT zawodnik, imie, czas, droga, data, time FROM Pomiary, Zawodnicy WHERE zawodnik=nr_start ORDER BY czas, droga'):
        year = int(row[4] / 10000)
        month = int(row[4] %10000 / 100)
        day = int(row[4] %100)
        hour = int(row[5] / 10000)
        minute = int(row[5] %10000 / 100)
        second = int(row[5] %100)
        date_pom = "{0:04d}-{1:02d}-{2:02d}".format(year, month, day)
        time_pom = "{0:02d}:{1:02d}:{2:02d}".format(hour, minute, second)
        print("\t%-5d %-15d %-9s %-11.4f %-14.4f %-10s %-8s"  %(i, row[0], row[1], row[2], row[3], date_pom, time_pom))
        i += 1


if __name__== "__main__":
    connection = sqlite3.connect('example.db')
    key = str(input('''
    Wybierz
    q-wyjście
    h-pomoc
    p-nowy pomiar
    z-dodaj zawodnika
    w-wyświetl zawodników
    t-wyświetl tabelę pomiarów\n\nKomenda: '''))
    while(True):
        if key == 'q' or key == 'Q':
            break
        elif key == 'h' or key == 'H':
            print('''
                Wyświetl tabelę pomiarów - wpisz komendę t lub T
                Wyświetl zawodników      - wpisz komendę w lub W
                Dodaj zawodnika          - wpisz komendę z lub Z
                Nowy pomiar              - wpisz komendę p lub P
                Pomoc                    - wpisz komendę h lub H
                Wyjście z programu       - wpisz komendę q lub Q.
            ''')
        elif key == 'z' or key == 'Z':
            Add_user_to_database()
        elif key == 'w' or key == 'W':
            View_all_users_from_database()
        elif key == 't' or key == 'T':
            View_all_measures_from_database()
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
                #print(pomiar)
                curs.execute(sql, pomiar)
                connection.commit()
        else:
            print("Błędna komenda")
        key = str(input("\nKomenda: "))
