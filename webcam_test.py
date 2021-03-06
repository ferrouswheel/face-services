import os
import sys
import dlib
from skimage import io
import numpy as np
import cv2
import tempfile

from faceutils import render_landmarks, render_bounding_boxes

# external models
landmark68_predictor_path = "models/shape_predictor_68_face_landmarks.dat"
landmark5_predictor_path = "models/shape_predictor_5_face_landmarks.dat"
recognition_model_path = "models/dlib_face_recognition_resnet_model_v1.dat"

cnn_face_detector_path = "models/mmod_human_face_detector.dat"
cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"


def query_capture(cap):
    #   0  CV_CAP_PROP_POS_MSEC Current position of the video file in milliseconds.
    #   1  CV_CAP_PROP_POS_FRAMES 0-based index of the frame to be decoded/captured next.
    #   2  CV_CAP_PROP_POS_AVI_RATIO Relative position of the video file
    #   3  CV_CAP_PROP_FRAME_WIDTH Width of the frames in the video stream.
    #   4  CV_CAP_PROP_FRAME_HEIGHT Height of the frames in the video stream.
    #   5  CV_CAP_PROP_FPS Frame rate.
    #   6  CV_CAP_PROP_FOURCC 4-character code of codec.
    #   7  CV_CAP_PROP_FRAME_COUNT Number of frames in the video file.
    #   8  CV_CAP_PROP_FORMAT Format of the Mat objects returned by retrieve() .
    #   9 CV_CAP_PROP_MODE Backend-specific value indicating the current capture mode.
    #   10 CV_CAP_PROP_BRIGHTNESS Brightness of the image (only for cameras).
    #   11 CV_CAP_PROP_CONTRAST Contrast of the image (only for cameras).
    #   12 CV_CAP_PROP_SATURATION Saturation of the image (only for cameras).
    #   13 CV_CAP_PROP_HUE Hue of the image (only for cameras).
    #   14 CV_CAP_PROP_GAIN Gain of the image (only for cameras).
    #   15 CV_CAP_PROP_EXPOSURE Exposure (only for cameras).
    #   16 CV_CAP_PROP_CONVERT_RGB Boolean flags indicating whether images should be converted to RGB.
    #   17 CV_CAP_PROP_WHITE_BALANCE Currently unsupported
    #   18 CV_CAP_PROP_RECTIFICATION Rectification flag for stereo cameras (note: only supported by DC1394 v 2.x backend currently)

    #pos = cap.get(cv2.CAP_PROP_POS_MSEC)
    #ratio = cap.get(cv2.CAP_PROP_POS_AVI_RATIO)
    #frame_rate = cap.get(cv2.CAP_PROP_FPS)
    width = cap.get(cv2.CAP_PROP_FRAME_WIDTH)
    height = cap.get(cv2.CAP_PROP_FRAME_HEIGHT)
    brightness = cap.get(cv2.CAP_PROP_BRIGHTNESS)
    contrast = cap.get(cv2.CAP_PROP_CONTRAST)
    saturation = cap.get(cv2.CAP_PROP_SATURATION)
    hue = cap.get(cv2.CAP_PROP_HUE)
    gain = cap.get(cv2.CAP_PROP_GAIN)
    exposure = cap.get(cv2.CAP_PROP_EXPOSURE)
    #print("Position: ", pos)
    #print("Ratio: ", ratio)
    #print("Frame Rate: ", frame_rate)
    print("Height: ", height)
    print("Width: ", width)
    print("Brightness: ", brightness)
    print("Contrast: ", contrast)
    print("Saturation: ", saturation)
    print("Hue: ", hue)
    print("Gain: ", gain)
    print("Exposure: ", exposure)

    # Change the camera setting using the set() function
    # cap.set(cv2.cv.CV_CAP_PROP_EXPOSURE, -6.0)
    # cap.set(cv2.cv.CV_CAP_PROP_GAIN, 4.0)
    # cap.set(cv2.cv.CV_CAP_PROP_BRIGHTNESS, 144.0)
    # cap.set(cv2.cv.CV_CAP_PROP_CONTRAST, 27.0)
    # cap.set(cv2.cv.CV_CAP_PROP_HUE, 13.0) # 13.0
    # cap.set(cv2.cv.CV_CAP_PROP_SATURATION, 28.0)
    return int(width), int(height)

def detect_from_webcam(save_video):
    cap = cv2.VideoCapture(0)
    width, height = query_capture(cap)
    do_loop = True

    # face detection/localization
    face_detector_dlib_hog = dlib.get_frontal_face_detector()
    face_detector_dlib_cnn = dlib.cnn_face_detection_model_v1(cnn_face_detector_path)
    face_detector_opencv_haarcascade = cv2.CascadeClassifier(cascade_path)

    # landmark prediction
    landmark68_predictor = dlib.shape_predictor(landmark68_predictor_path)
    landmark5_predictor = dlib.shape_predictor(landmark5_predictor_path)

    # face recognition
    facerec = dlib.face_recognition_model_v1(recognition_model_path)

    landmark_predictors = [landmark5_predictor, landmark68_predictor]
    landmark_idx = 0

    num_face_detectors = 3
    face_idx = 0

    last_identity = np.zeros((128,))

    chip_size = 150
    border = 0.2

    if save_video:
        videowriter = cv2.VideoWriter("test.avi", cv2.VideoWriter_fourcc(*'DIV4'), 20, (width, height))
        chip_size = 300
        border = 1.0
        videowriter_aligned = cv2.VideoWriter("test_align.avi", cv2.VideoWriter_fourcc(*'DIV4'), 20, (chip_size, chip_size))

    fh, temp_file = tempfile.mkstemp('.jpg')
    os.close(fh)
    temp_file_no_ext = ".".join(temp_file.rsplit('.')[:-1])

    while(do_loop):
        # Capture frame-by-frame
        ret, frame = cap.read()

        img = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)

        dets = []
        # face detection
        if face_idx == 0:
            gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
            faces = face_detector_opencv_haarcascade.detectMultiScale(
                gray,
                scaleFactor=1.05,
                minNeighbors=5,
                minSize=(100, 100),
                flags=cv2.CASCADE_SCALE_IMAGE
            )
            # Convert to array of dlib rectangles
            for (x, y, w, h) in faces:
                dets.append(dlib.rectangle(x, y, x+w, y+h))

        elif face_idx == 1:
            dets = face_detector_dlib_hog(img, 1)
        else:
            cnn_dets = face_detector_dlib_cnn(img, 1)
            for cnn_d in cnn_dets:
                # different return type because it includes confidence, get the rect
                d = cnn_d.rect
                h = d.top() - d.bottom()
                # cnn max margin detector seems to cut off the chin and this confuses landmark predictor,
                # expand height by 10%
                dets.append(dlib.rectangle(d.left(), d.top(), d.right(), d.bottom() - int(h / 10.0)))

        print("Number of faces detected: {}".format(len(dets)))

        landmarks = [None] * len(dets)
        for i, d in enumerate(dets):
            #print("Detection {}, score: {}, face_type:{}".format(
            #    d, scores[i], idx[i]))
            #print("Detection {}: Left: {} Top: {} Right: {} Bottom: {}".format(
            #    i, d.left(), d.top(), d.right(), d.bottom()))
            landmark_predictor = landmark_predictors[landmark_idx]
            detection_object = landmark_predictor(img, d)

            # This is a hack to get the aligned face image via the dlib API
            # It writes to a file that we have to read back
            # `compute_face_descriptor` recomputes the alignment and won't accept a differently aligned face
            dlib.save_face_chip(img, detection_object, temp_file_no_ext, chip_size, border)

            aligned_img = cv2.cvtColor(io.imread(temp_file), cv2.COLOR_RGB2BGR)
            if save_video:
                videowriter_aligned.write(aligned_img)
            cv2.imshow("aligned", aligned_img)

            landmarks[i] = detection_object.parts()
            face_descriptor = facerec.compute_face_descriptor(img, detection_object, 10)

            # TODO: this currently is just comparing to the last frame. Won't handle multiple faces.
            # To handle multiple faces we need to compare distance to all previous identities, or
            # track the bbox movement
            new_identity = np.matrix(face_descriptor)
            print("Distance to last identity %.4f" % np.linalg.norm(last_identity - new_identity))
            last_identity = new_identity

        render_bounding_boxes(frame, dets)
        render_landmarks(frame, landmarks)

        cv2.imshow("Faces found", frame)

        if save_video:
            videowriter.write(frame)

        key = cv2.waitKey(1) & 0xFF

        if key != -1:
            if key == ord('q'):
                do_loop = False
            elif key == ord('l'):
                landmark_idx += 1
                landmark_idx %= len(landmark_predictors)
            elif key == ord('d'):
                face_idx += 1
                face_idx %= num_face_detectors
    os.remove(temp_file)

    cv2.destroyAllWindows()
    cap.release()


def process_and_show_detected_faces():
    # Old dlib UI doing batch processing.
    win = dlib.image_window()

    detector = dlib.get_frontal_face_detector()
    for f in sys.argv[1:]:
        print("Processing file: {}".format(f))
        img = io.imread(f)
        # The 1 in the second argument indicates that we should upsample the image
        # 1 time.  This will make everything bigger and allow us to detect more
        # faces.
        dets = detector(img, 1)
        print("Number of faces detected: {}".format(len(dets)))
        for i, d in enumerate(dets):
            print("Detection {}: Left: {} Top: {} Right: {} Bottom: {}".format(
                i, d.left(), d.top(), d.right(), d.bottom()))

        win.clear_overlay()
        win.set_image(img)
        win.add_overlay(dets)
        dlib.hit_enter_to_continue()

if __name__ == "__main__":
    save_video = False
    detect_from_webcam(save_video)
