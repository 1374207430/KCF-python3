import numpy as np
import cv2
import sys
from time import time
import dlib
import os
import mxnet as mx
from detector_model.mtcnn_detector import MtcnnDetector
from detect import mtcnn_detect
import kcftracker

selectingObject = False
initTracking = True
onTracking = False
ix, iy, cx, cy = -1, -1, -1, -1
w, h = 0, 0

inteval = 1
duration = 0.01


# mouse callback function
def draw_boundingbox(event, x, y, flags, param):
    global selectingObject, initTracking, onTracking, ix, iy, cx, cy, w, h

    if event == cv2.EVENT_LBUTTONDOWN:
        selectingObject = True
        onTracking = False
        ix, iy = x, y
        cx, cy = x, y

    elif event == cv2.EVENT_MOUSEMOVE:
        cx, cy = x, y

    elif event == cv2.EVENT_LBUTTONUP:
        selectingObject = False
        if (abs(x - ix) > 10 and abs(y - iy) > 10):
            w, h = abs(x - ix), abs(y - iy)
            ix, iy = min(x, ix), min(y, iy)
            initTracking = True
        else:
            onTracking = False

    elif event == cv2.EVENT_RBUTTONDOWN:
        onTracking = False
        if (w > 0):
            ix, iy = x - w / 2, y - h / 2
            initTracking = True


if __name__ == '__main__':
    detector_model_dir = os.path.join('/Volumes/Transcend/jintian/KCF-python3/detector_model/model')
    detector = MtcnnDetector(model_folder=detector_model_dir, minsize=40, threshold=[0.8, 0.8, 0.9], ctx=mx.cpu(0),
                             num_worker=4,
                             accurate_landmark=False)

    if (len(sys.argv) == 1):
        cap = cv2.VideoCapture("/Volumes/Transcend/jintian/SmartEye/data/videos/1.mp4")
    elif (len(sys.argv) == 2):
        if (sys.argv[1].isdigit()):  # True if sys.argv[1] is str of a nonnegative integer
            cap = cv2.VideoCapture(int(sys.argv[1]))
        else:
            cap = cv2.VideoCapture(sys.argv[1])
            inteval = 30
    else:
        assert (0), "too many arguments"

    tracker = kcftracker.KCFTracker(True, True, True)  # hog, fixed_window, multiscale
    # if you use hog feature, there will be a short pause after you draw a first boundingbox,
    # that is due to the use of Numba.
    cv2.namedWindow('tracking')
    mtcnn_flag = True
    if not mtcnn_flag:
        frontFaceDetector = dlib.get_frontal_face_detector()

    # cv2.setMouseCallback('tracking', draw_boundingbox)

    while (cap.isOpened()):
        ret, frame = cap.read()
        frame = cv2.resize(frame, (0, 0), fx=0.5, fy=0.5)

        if not ret:
            break

        if initTracking:
            if not mtcnn_flag:
                faceRect = frontFaceDetector(frame, 0)
            else:
                _,_,faceRect = mtcnn_detect(detector, frame)
            if (len(faceRect) == 0):
                continue
            bbox = faceRect[0]
            print("only once:", bbox)
            # convert dlib rect to opencv rect
            if not mtcnn_flag:
                curFaceBbox = (int(bbox.left()), int(bbox.top()), int(bbox.right() - bbox.left()),
                               int(bbox.bottom() - bbox.top()))
            else:
                curFaceBbox = (int(bbox[0]), int(bbox[1]), int(bbox[2] - bbox[0]),
                               int(bbox[3] - bbox[1]))

        if (selectingObject):
            cv2.rectangle(frame, (ix, iy), (cx, cy), (0, 255, 255), 1)
        elif (initTracking):
            # cv2.rectangle(frame, (ix, iy), (ix + w, iy + h), (0, 255, 255), 2)
            # tracker.init([ix, iy, w, h], frame)
            # print(curFaceBbox)
            tracker.init(curFaceBbox, frame)
            if not mtcnn_flag:
                cv2.rectangle(frame, (int(bbox.left()), int(bbox.top())), (int(bbox.right()), int(bbox.bottom())),
                              (0, 255, 255), 2)
            else:
                cv2.rectangle(frame, (int(bbox[0]), int(bbox[1])), (int(bbox[2]), int(bbox[3])),
                              (0, 255, 255), 2)
            # cv2.imshow('temp', frame)
            # cv2.waitKey(0)

            initTracking = False
            onTracking = True
        elif (onTracking):
            t0 = time()
            boundingbox = tracker.update(frame)
            t1 = time()

            boundingbox = list(map(int, boundingbox))
            cv2.rectangle(frame, (boundingbox[0], boundingbox[1]),
                          (boundingbox[0] + boundingbox[2], boundingbox[1] + boundingbox[3]), (0, 255, 255), 1)

            duration = 0.8 * duration + 0.2 * (t1 - t0)
            # duration = t1-t0
            cv2.putText(frame, 'FPS: ' + str(1 / duration)[:4].strip('.'), (8, 20), cv2.FONT_HERSHEY_SIMPLEX, 0.6,
                        (0, 0, 255), 2)

        cv2.imshow('tracking', frame)
        c = cv2.waitKey(inteval) & 0xFF
        if c == 27 or c == ord('q'):
            break

    cap.release()
    cv2.destroyAllWindows()
