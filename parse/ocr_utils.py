import cv2
import os

import numpy as np

from paddleocr import PaddleOCR


ocr_standard = PaddleOCR(
    use_angle_cls=True,
    lang='en'
)

ocr_table = PaddleOCR(
    use_angle_cls=True,
    lang='en',
    det_db_box_thresh=0.3,
    det_db_unclip_ratio=1.2,
    draw_img_save=True,
    draw_img_save_dir='./debug_output'
)

def run_ocr(image_path):
    # placeholder for your PaddleOCR wrapper
    pass

def load_image(path):
    '''
    Load .gif file at path and return img object.
    '''

    ext = os.path.splitext(path)[1].lower()
    
    # Use VideoCapture for GIFs (extract image - only 1 frame .gif)
    if ext == ".gif":
        cap = cv2.VideoCapture(path)
        ret, frame = cap.read()
        cap.release()
        if not ret:
            raise ValueError(f"Could not read first frame of GIF: {path}")
        img = frame
    else:
        img = cv2.imread(path)
        if img is None:
            raise ValueError(f"Could not read image: {path}")
    
    return img

def preprocess_image(img, return_title=True):
    '''
    Given an img (array), preprocess the various parts of the timing sheet.
    The Title, which we will use to get the circuit name
    the Table, which contains the timing data
    the Footer, which contains the date metadata

    Preprocessing: crops, often upscales and sharpens

    Returns a dictionary, crops, with keys ['title_img', 'table_img', 'date_img']
    containing img arrays of the respective areas.
    '''

    h, w = img.shape[:2]
    
    # Top half: assumed to contain the timing table
    table_crop = img[int(0.12*h):int(0.5*h), 0:w]
    table_up = cv2.resize(table_crop, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    table_sharp = unsharp_mask(table_up)
    
    # Bottom-right corner: assumed to contain the date
    date_crop = img[int(0.963*h):h, int(0.7*w):w]
    date_up = cv2.resize(date_crop, None, fx=2, fy=2, interpolation=cv2.INTER_LINEAR)
    date_sharp = unsharp_mask(date_up, kernel_size=(5,5), sigma=1.0, amount=1.2, threshold=0.0)

    crops = {
        'table_img': table_sharp,
        'date_img': date_sharp,
    }

    # Optionally include top header for circuit metadata
    if return_title:
        title_crop = img[0:int(0.09*h), 0:int(0.5*w)]
        crops['title_img'] = title_crop

    return crops

def unsharp_mask(image, kernel_size=(5, 5), sigma=1.0, amount=1.0, threshold=0):
    """Return a sharpened version of the image, using an unsharp mask."""

    blurred = cv2.GaussianBlur(image, kernel_size, sigma)
    sharpened = float(amount + 1) * image - float(amount) * blurred
    sharpened = np.maximum(sharpened, np.zeros(sharpened.shape))
    sharpened = np.minimum(sharpened, 255 * np.ones(sharpened.shape))
    sharpened = sharpened.round().astype(np.uint8)
    if threshold > 0:
        low_contrast_mask = np.absolute(image - blurred) < threshold
        np.copyto(sharpened, image, where=low_contrast_mask)
    return sharpened

