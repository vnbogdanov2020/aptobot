import cv2
from pyzbar.pyzbar import decode
import requests

# image = cv2.imread('C:/Restored Files/python/barcode.png')
# image = cv2.imread('C:/Restored Files/python/photo.jpg')
barcode_pic = 'pic/barcode_pic.jpg'


def read_barcode(flink):
    # url = 'https://api.telegram.org/file/bot1169455288:AAG6iJrpBaH6uDxlyhGgiN1GIiO0tnl-b2w/photos/file_0.jpg'
    myfile = requests.get(flink)
    # print(flink)
    open(barcode_pic, 'wb').write(myfile.content)

    image = cv2.imread(barcode_pic)
    '''    
    cap = cv2.VideoCapture('https://api.telegram.org/file/bot1169455288:AAG6iJrpBaH6uDxlyhGgiN1GIiO0tnl-b2w/photos/file_0.jpg')

    if(cap.isOpened() ) :
        img = cap.read()
        print(img)
        #image = cv2.imread(filelink)
    '''
    detectedBarcodes = decode(image)

    if not detectedBarcodes:
        return ('No')
    else:
        for barcode in detectedBarcodes:
            (x, y, w, h) = barcode.rect
            cv2.rectangle(image, (x, y), (x + w, y + h), (255, 0, 0), 5)

            return (barcode.data)
            # print(barcode.data)
            # print(barcode.type)

#  cv2.imshow("Image", image)

#  cv2.waitKey(0)
#  cv2.destroyAllWindows()