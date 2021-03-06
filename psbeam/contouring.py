#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Low to mid level functions and classes that mostly involve contouring. For more
info on how they work, visit OpenCV's documentation on contours:

http://docs.opencv.org/trunk/d3/d05/tutorial_py_table_of_contents_contours.html
"""
############
# Standard #
############
import logging

###############
# Third Party #
###############
import cv2
import numpy as np

##########
# Module #
##########
from .images import templates
from .preprocessing import (threshold_image, to_gray, to_uint8)
from .beamexceptions import (NoContoursDetected, InputError)

logger = logging.getLogger(__name__)

def get_contours(image, thresh_mode="otsu", *args, **kwargs):
    """
    Returns the contours of an image according to the inputted threshold.

    Parameters
    ----------
    image : np.ndarray
        Image to extract the contours from.

    thresh_mode : str, optional
        Thresholding mode to use. For extended documentation see
        ``preprocessing.threshold_image``. Valid modes are:
            ['mean', 'top', 'bottom', 'adaptive', 'otsu']

    Returns
    -------
    contours : list
        A list of the contours found in the image.

    Raises
    ------
    NoContoursDetected
        The returned contours list was empty.
    """
    image_thresh = threshold_image(image, mode=thresh_mode, **kwargs)
    _, contours, _ = cv2.findContours(image_thresh, 1, 2)    
    # Check if contours is empty
    if not contours:
        raise NoContoursDetected
    return contours

def get_largest_contour(image=None, contours=None, thresh_mode="otsu",
                        **kwargs):
    """
    Returns largest contour of the contour list. Either an image or a contour
    must be passed. If both are passed, a warning will be logged and the
    contours of the image will be computed and used to find the largest contour.

    Function is making an implicit assumption that there will only be one
    (large) contour in the image. 

    Parameters
    ----------
    image : np.ndarray, optional
        Image to extract the contours from.

    contours : np.ndarray, optional
        Contours found on an image.

    thresh_mode : str, optional
        Thresholding mode to use. For extended documentation see
        ``preprocessing.threshold_image``. Valid modes are:
            ['mean', 'top', 'bottom', 'adaptive', 'otsu']
    
    Returns
    -------
    (contour_largest, area_largest) : tuple
        Contour that encloses the largest area and the area it encloses

    Raises
    ------
    InputError
        If neither an image nor contours are inputted, or largest area is zero
    """
    # Check if contours were inputted
    if image is None and contours is None:
        raise InputError("No image or contours provided.")
    elif image is not None:
        if contours is not None:
            logger.warning("Image and contours inputted. Returning largest "
                           "contour of the image.")
        contours = get_contours(image, thresh_mode=thresh_mode, **kwargs)
        
    # Get area of all the contours found
    areas = np.array([cv2.contourArea(cnt) for cnt in contours])
    # Largest contour and its area
    contour_largest = contours[np.argmax(areas)]
    area_largest = areas.max()

    # Last check to make sure the area is nonzero:
    if area_largest == 0.0:
        raise NoContoursDetected
    
    # Return argmax and max
    return contour_largest, area_largest

def get_moments(image=None, contour=None, **kwargs):
    """
    Returns the moments of an image.

    Attempts to find the moments using an inputted contours first, but if it
    isn't inputted it will compute the contours of the image then compute
    the moments.

    Parameters
    ----------
    image : np.ndarray
        Image to calculate moments from.

    contour : np.ndarray
        Beam contour.

    Returns
    -------
    moments : dict
        Dictionary with all the calculated moments of the image.

    Raises
    ------
    InputError
        If neither an image nor contours are inputted.    
    """
    if image is None and contour is None:
        raise InputError("No image or contour provided.")
    elif image is not None:
        if contour is not None:
            logger.warning("Image and contour inputted. Using largest contour "
                        "of the image.")
        contour, _ = get_largest_contour(image, **kwargs)
        
    return cv2.moments(contour)
        
def get_centroid(M):
    """
    Returns the centroid using the inputted image moments.

    Centroid is computed as being the first moment in x and y divided by the
    zeroth moment.

    Parameters
    ----------
    M : list
        List of image moments.
    
    Returns
    -------
    tuple
        Centroid of the image moments.
    """    
    return int(M['m10']/M['m00']), int(M['m01']/M['m00'])

def get_bounding_box(image=None, contour=None, **kwargs):
    """
    Finds the up-right bounding box that contains the inputted contour. Either
    an image or contours have to be passed.

    Parameters
    ----------
    image : np.ndarray
        Image to calculate moments from.

    contour : np.ndarray
        Beam contour.

    Returns
    -------
    tuple
        Contains x, y, width, height of bounding box.

    It should be noted that the x and y coordinates are for the bottom left
    corner of the bounding box. Use matplotlib.patches.Rectangle to plot.
    """
    if image is None and contour is None:
        raise InputError("No image or contour provided.")
    elif image is not None:
        if contour is not None:
            logger.warning("Image and contour inputted. Using largest contour "
                        "of the image.")
        contour, _ = get_largest_contour(image, **kwargs)
        
    return cv2.boundingRect(contour)

def get_contour_size(image=None, contour=None, **kwargs):
    """
    Returns the length and width of the contour, or the contour of the image
    inputted.

    Parameters
    ----------
    image : np.ndarray
        Image to calculate moments from.

    contour : np.ndarray
        Beam contour.

    Returns
    -------
    tuple
        Length and width of the inputted contour.

    Raises
    ------
    InputError
        If neither an image nor contours are inputted.    
    """
    _, _, w, l = get_bounding_box(image=image, contour=contour, **kwargs)
    return l, w
    
def get_similarity(contour, template="circle", method=1, **kwargs):
    """
    Returns a score of how similar a contour is to a selected template image.

    Parameters
    ----------
    contour : np.ndarray
        Contour to be compared with the template contour

    template : str or np.ndarray, optional
        String for template image to use, or can be a contour

    method : int, optional
        Matches the contours according to an enumeration from 0 to 2. To see
        the methods in detail, go to:
        http://docs.opencv.org/3.1.0/df/d4e/group__imgproc__c.html#gacd971ae682604ff73cdb88645725968d

    Returns
    -------
    float
        Value that is 0.0 or larger, with 0.0 denoting a perfect matching

    Raises
    ------
    InputError
        If string for template image is not in template images, np.ndarray for
        template image is not the right shape, invalid type passed for template.
    """
    # If template is a string, grab it from templates directory
    if isinstance(template, str):
        try:
            template_image = getattr(templates, template)
            # Make sure it is grayscale and uint8
            if len(template_image.shape) != 2:
                template_image = to_gray(template_image)
            if template_image.dtype != np.uint8:
                template_image = to_uint8(template_image)
            template_contour, _ = get_largest_contour(template_image, **kwargs)
        except AttributeError:
            raise InputError("Inputted image '{0}' not an image template."
                             "".format(template))

    # If np.ndarray make sure it is a contour
    elif isinstance(template, np.ndarray):
        if len(template.shape) != 3 or (
                template.shape[1], template.shape[2]) != (1, 2):
            raise InputError("Inputted template contour does not have standard "
                             "contour shape, must be (n, 1, 2), got {0}."
                             "".format(template.shape))
        template_contour = template

    # Handle invalid inputs
    else:
        raise InputError("Inputted template must be str or nd.ndarray. Got "
                         "{0}.".format(type(template)))
                             
    return cv2.matchShapes(template_contour, contour, method, 0)
