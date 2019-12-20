import os
import numpy as np
import pydicom
from pydicom.dataset import Dataset, FileDataset
from pydicom.sequence import Sequence
import datetime
import copy
import readDICOM_Image
#import FileManagement.ParametricMapsDictionary as param # THIS IS FROM JOAO'S SKETCHPAD


def save_automatically_and_returnFilePath(imagePath, pixelArray, suffix):
    """This method reads the DICOM file in imagePath and returns the Image/Pixel array"""
    try:
        if os.path.exists(imagePath):
            # Need to think about what new name to give to the file and how to save multiple files for the same sequence
            dataset = readDICOM_Image.getDicomDataset(imagePath)
            oldFileName = os.path.splitext(imagePath)
            newFilePath = oldFileName[0] + suffix + '.dcm'
            newDataset = create_new_single_dicom(dataset, pixelArray, comment=suffix)
            save_dicom_to_file(newDataset, output_path=newFilePath)
            return newFilePath
        else:
            return None
    except Exception as e:
        print('Error in function saveDICOM_Image.save_automatically_and_returnFilePath: ' + str(e))


def save_dicom_binOpResult(imagePath1, imagePath2, pixelArray, imageFilePath, suffix):
    try:
        if os.path.exists(imagePath1) & os.path.exists(imagePath2):
            # Need to think about what new name to give to the file and how to save multiple files for the same sequence
            dataset1 = readDICOM_Image.getDicomDataset(imagePath1)
            dataset2 = readDICOM_Image.getDicomDataset(imagePath2)
            newDataset = create_new_single_dicom(dataset1, pixelArray, comment=suffix, list_refs=dataset2)
            save_dicom_to_file(newDataset, output_path=imageFilePath)
            return
        else:
            return None
    except Exception as e:
        print('Error in function saveDICOM_Image.save_dicom_binOpResult: ' + str(e))


def save_dicom_to_file(dicomData, output_path=None):
    """This method takes a DICOM object and saves it as a DICOM file 
        with the set filename in the input arguments.
    """
    if output_path is None:
        output_path = os.getcwd() + copy.deepcopy(dicomData.SOPInstanceUID) + ".dcm"

    pydicom.filewriter.dcmwrite(output_path, dicomData, write_like_original=True)
    del dicomData
    return


#WE WILL HAVE TO DISCUSS ABOUT SETTING A UID FOR SERIES AND IT'S LINK WITH THE XML FILE. AT THE MOMENT 2 IMAGES MIGHT BE LABELLED AS PART OF THE SAME SEQUENCE IN XML BUT NOT IN THE DICOM METADATA
def create_new_single_dicom(dicomData, imageArray, series_id=None, series_uid=None, comment=None, parametric_map=None, list_refs=None):
    """This function takes a DICOM Object, copies most of the DICOM tags from the DICOM given in input
        and writes the imageArray into the new DICOM Object in PixelData. 
    """
    newDicom = copy.deepcopy(dicomData)
    imageArray = copy.deepcopy(imageArray)

    # Generate Unique ID
    newDicom.SOPInstanceUID = pydicom.uid.generate_uid()

    # Series ID and UID
    if series_id is None:
        newDicom.SeriesNumber = int(str(dicomData.SeriesNumber) + "999999")
    else:
        newDicom.SeriesNumber = series_id
    if series_uid is None:
        newDicom.SeriesInstanceUID = pydicom.uid.generate_uid()
    else:
        newDicom.SeriesInstanceUID = series_uid

    # Date and Time of Creation
    dt = datetime.datetime.now()
    timeStr = dt.strftime('%H%M%S')  # long format with micro seconds
    newDicom.ContentDate = dt.strftime('%Y%m%d')
    newDicom.ContentTime = timeStr
    newDicom.InstanceCreationDate = dt.strftime('%Y%m%d')
    newDicom.InstanceCreationTime = timeStr
    newDicom.SeriesDate = dt.strftime('%Y%m%d')
    newDicom.ImageDate = dt.strftime('%Y%m%d')
    newDicom.AcquisitionDate = dt.strftime('%Y%m%d')
    newDicom.SeriesTime = timeStr
    newDicom.ImageTime = timeStr
    newDicom.AcquisitionTime = timeStr

    # Image Type - DERIVED
    newDicom.ImageType[0] = "DERIVED"

    # Series, Instance and Class for Reference
    refd_series_sequence = Sequence()
    newDicom.ReferencedSeriesSequence = refd_series_sequence
    refd_series1 = Dataset()
    refd_instance_sequence = Sequence()
    refd_series1.ReferencedInstanceSequence = refd_instance_sequence
    refd_instance1 = Dataset()
    refd_instance1.ReferencedSOPClassUID = dicomData.SOPClassUID
    refd_instance1.ReferencedSOPInstanceUID = dicomData.SOPInstanceUID
    refd_instance_sequence.append(refd_instance1)
    refd_series1.SeriesInstanceUID = dicomData.SeriesInstanceUID
    refd_series_sequence.append(refd_series1)

    # Extra references, besides the main one, which is dicom_list
    if list_refs is not None:
        if np.shape(list_refs) == ():
            refd_series1 = Dataset()
            refd_instance_sequence = Sequence()
            refd_series1.ReferencedInstanceSequence = refd_instance_sequence
            refd_instance1 = Dataset()
            refd_instance1.ReferencedSOPInstanceUID = list_refs.SOPInstanceUID
            refd_instance1.ReferencedSOPClassUID = list_refs.SOPClassUID
            refd_instance_sequence.append(refd_instance1)
            refd_series1.SeriesInstanceUID = list_refs.SeriesInstanceUID
            refd_series_sequence.append(refd_series1)
        else:
            for individual_ref in list_refs:
                refd_series1 = Dataset()
                refd_instance_sequence = Sequence()
                refd_series1.ReferencedInstanceSequence = refd_instance_sequence
                refd_instance1 = Dataset()
                refd_instance1.ReferencedSOPInstanceUID = individual_ref.SOPInstanceUID
                refd_instance1.ReferencedSOPClassUID = individual_ref.SOPClassUID
                refd_instance_sequence.append(refd_instance1)
                refd_series1.SeriesInstanceUID = individual_ref.SeriesInstanceUID
                refd_series_sequence.append(refd_series1)
        del list_refs

    # Comments
    if comment is not None:
        newDicom.ImageComments = comment
        if len(dicomData.dir("SeriesDescription"))>0:
            newDicom.SeriesDescription = dicomData.SeriesDescription + comment
        elif len(dicomData.dir("SequenceName"))>0 & len(dicomData.dir("PulseSequenceName"))==0:
            newDicom.SeriesDescription = dicomData.SequenceName + comment
        elif len(dicomData.dir("SeriesDescription"))>0:
            newDicom.SeriesDescription = dicomData.SeriesDescription + comment
        elif len(dicomData.dir("ProtocolName"))>0:
            newDicom.SeriesDescription = dicomData.ProtocolName + comment
        else:
            newDicom.SeriesDescription = "NewSeries" + newDicom.SeriesNumber 

    # Parametric Map
    if parametric_map is not None:
        # param.edit_dicom(newDicom, imageArray, parametric_map)
        # This parametric map code exists in Joao Sousa sketchpad. It will be implemented in another occasion/time.
        imageArray = np.rot90(imageArray, -3)
        newDicom.PixelData = imageArray.tobytes()
    else:
        # COULD INSERT IF ENHANCED MRI HERE?! - Only for Slope and Intercept!
        # if hasattr(sequence[0], 'PerFrameFunctionalGroupsSequence'):
        # for each frame, slope and intercept are M and B. For registration, I will have to add Image Position and Orientation
        
        imageArray = np.rot90(imageArray, -3)
        # I'M FORCING EVERY IMAGE TO HAVE PIXELREPRESENTATION=1 AND INT VALUES.
        # I NEED TO TEST WITH PIXELREPRESENTATION=0 AND UINT VALUES - EG. SAMPLE DATA
        newDicom.PixelRepresentation = 1
        target = (np.power(2, dicomData.BitsAllocated) - 1)*np.ones(np.shape(imageArray))
        maximum = np.ones(np.shape(imageArray))*np.amax(imageArray)
        minimum = np.ones(np.shape(imageArray))*np.amin(imageArray)
        extra = target/(2*np.ones(np.shape(imageArray)))
        imageScaled = target * (imageArray - minimum) / (maximum - minimum) - extra
        slope =  target / (maximum - minimum)
        intercept = (- target * minimum - extra * (maximum-minimum))/ (maximum - minimum)
        rescaleSlope = np.ones(np.shape(imageArray)) / slope
        rescaleIntercept = - intercept / slope

        if newDicom.BitsAllocated == 8:
            imageArrayInt = imageScaled.astype(np.int8)
        elif newDicom.BitsAllocated == 16:
            imageArrayInt = imageScaled.astype(np.int16)
        elif newDicom.BitsAllocated == 32:
            imageArrayInt = imageScaled.astype(np.int32)
        elif newDicom.BitsAllocated == 64:
            imageArrayInt = imageScaled.astype(np.int64)
        else:
            imageArrayInt = imageScaled.astype(dicomData.pixel_array.dtype)

        # NEED TO REVIEW THIS
        #print(np.amin(imageArrayInt))                
        #newDicom.SmallestImagePixelValue = int(np.amin(imageArrayInt))
        #newDicom.LargestImagePixelValue = np.amax(imageArrayInt)
        #newDicom.WindowCenter = np.median(imageArrayInt)
        #newDicom.WindowWidth = np.absolute(np.amax(imageArrayInt))
        newDicom.RescaleSlope = rescaleSlope.flatten()[0]
        newDicom.RescaleIntercept = rescaleIntercept.flatten()[0]
        newDicom.PixelData = imageArrayInt.tobytes()

    del dicomData, imageArray, imageScaled, imageArrayInt

    return newDicom