import cv2
import glob
import os
from pyzbar.pyzbar import decode
import requests

# image = cv2.imread('C:/Restored Files/python/barcode.png')
# image = cv2.imread('C:/Restored Files/python/photo.jpg')
dirpath = os.path.dirname(__file__)
picpath = os.path.join(dirpath, 'pic/')


def read_barcode(flink,chat_id):
    # url = 'https://api.telegram.org/file/bot1169455288:AAG6iJrpBaH6uDxlyhGgiN1GIiO0tnl-b2w/photos/file_0.jpg'
    myfile = requests.get(flink)
    # print(flink)
    open(picpath+str(chat_id)+'.jpg', 'wb').write(myfile.content)

    image = cv2.imread(picpath+str(chat_id)+'.jpg')
    '''    
    cap = cv2.VideoCapture('https://api.telegram.org/file/bot1169455288:AAG6iJrpBaH6uDxlyhGgiN1GIiO0tnl-b2w/photos/file_0.jpg')

    if(cap.isOpened() ) :
        img = cap.read()
        print(img)
        #image = cv2.imread(filelink)
    '''
    detectedBarcodes = decode(image)

    if not detectedBarcodes:
        # Удалим файлы после использования
        for file in glob.glob(picpath+str(chat_id)+'.jpg'):
            os.remove(file)
            return ('No')
    else:
        for barcode in detectedBarcodes:
            (x, y, w, h) = barcode.rect
            cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 5)

            # Удалим файлы после использования
            for file in glob.glob(picpath + str(chat_id) + '.jpg'):
                os.remove(file)
            return (barcode.data)
            # print(barcode.data)
            # print(barcode.type)

#  cv2.imshow("Image", image)

#  cv2.waitKey(0)
#  cv2.destroyAllWindows()