import numpy as np
import cv2


TURN_THRESHOLD = 0.12
FORWARD_THRESHOLD = 0.08


def process_image(frame_rgb, previous_action=None):
    """
    Elabora un frame RGB e determina l'azione del robot.

    La funzione è indipendente da Gazebo, HTTP e dal nodo
    sul quale viene eseguita.
    """

    # RGB -> BGR
    frame_bgr = cv2.cvtColor(
        frame_rgb,
        cv2.COLOR_RGB2BGR
    )

    # BGR -> HSV
    hsv = cv2.cvtColor(
        frame_bgr,
        cv2.COLOR_BGR2HSV
    )

    # Intervalli HSV del rosso
    lower_red_1 = np.array([0, 100, 100])
    upper_red_1 = np.array([10, 255, 255])

    lower_red_2 = np.array([170, 100, 100])
    upper_red_2 = np.array([180, 255, 255])

    mask_1 = cv2.inRange(
        hsv,
        lower_red_1,
        upper_red_1
    )

    mask_2 = cv2.inRange(
        hsv,
        lower_red_2,
        upper_red_2
    )

    red_mask = cv2.bitwise_or(
        mask_1,
        mask_2
    )

    # Regione di interesse
    h, w = red_mask.shape

    x1 = int(w * 0.30)
    x2 = int(w * 0.70)

    y1 = int(h * 0.25)
    y2 = int(h * 0.85)

    roi = red_mask[y1:y2, x1:x2]

    red_pixels = cv2.countNonZero(roi)
    roi_area = roi.shape[0] * roi.shape[1]

    if roi_area == 0:
        raise ValueError("Regione di interesse non valida")

    red_ratio = red_pixels / roi_area

    # Decisione con isteresi
    if previous_action is None:

        if red_ratio > TURN_THRESHOLD:
            action = "TURN_LEFT"
        else:
            action = "FORWARD"

    elif red_ratio > TURN_THRESHOLD:
        action = "TURN_LEFT"

    elif red_ratio < FORWARD_THRESHOLD:
        action = "FORWARD"

    else:
        action = previous_action

    return {
        "action": action,
        "red_ratio": red_ratio
    }
