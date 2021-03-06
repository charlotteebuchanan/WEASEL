import os
import sys
import numpy as np
import CoreModules.WEASEL.readDICOM_Image as readDICOM_Image
import CoreModules.WEASEL.saveDICOM_Image as saveDICOM_Image
import CoreModules.WEASEL.TreeView  as treeView
import CoreModules.WEASEL.DisplayImageColour  as displayImageColour
import CoreModules.WEASEL.MessageWindow  as messageWindow
import CoreModules.WEASEL.InterfaceDICOMXMLFile  as interfaceDICOMXMLFile
import CoreModules.WEASEL.InputDialog as inputDialog
from CoreModules.imagingTools import thresholdPixelArray
FILE_SUFFIX = '_Thresholded'


def returnPixelArray(imagePath, *args):
    """Applies a low and high threshold on an image and returns the resulting maskArray"""
    try:
        if os.path.exists(imagePath):
            pixelArray = readDICOM_Image.returnPixelArray(imagePath)
            derivedImage = thresholdPixelArray(pixelArray, *args)
            return derivedImage
        else:
            return None
    except Exception as e:
            print('Error in function thresholdDICOM_Image.returnPixelArray: ' + str(e))


def main(objWeasel):
    """Creates a subwindow that displays a binary DICOM image. Executed using the 
    'Threshold Image' Menu item in the Tools menu."""
    try:
        paramDict = {"Lower Threshold":"integer, 10, 0, 1000", 
                     "Upper Threshold":"integer, 100, 0, 1000"}   
        #for integer & float, the format is "type, default value, minimum value, maximum value"

        helpMsg = "Lower threshold must be less than the upper threshold."
        warning = True
        while True:
            inputDlg = inputDialog.ParameterInputDialog(paramDict, helpText=helpMsg)
            listParams = inputDlg.returnListParameterValues()
            if inputDlg.closeInputDialog():
                #Cancel button has been clicked
                break
            if (listParams[0] < listParams[1]):
                break
            else:
                if warning:
                    helpMsg = helpMsg + "<H4><font color=\"red\"> Check input parameter values.</font></H4>"
                    warning = False  #only show this message once
        
        if inputDlg.closeInputDialog() == False: 
            #The OK button was clicked & the Cancel has not been clicked
            studyID = objWeasel.selectedStudy
            seriesID = objWeasel.selectedSeries
            if treeView.isAnImageSelected(objWeasel):
                imagePath = objWeasel.selectedImagePath
                pixelArray = returnPixelArray(imagePath, *listParams)
                derivedImageFileName = saveDICOM_Image.returnFilePath(imagePath, FILE_SUFFIX)
                # Save the DICOM file in the new file path                                        
                saveDICOM_Image.saveNewSingleDicomImage(derivedImageFileName, imagePath, 
                                                      pixelArray, FILE_SUFFIX)
                #Record squared image in XML file
                newSeriesID = interfaceDICOMXMLFile.insertNewImageInXMLFile(objWeasel, imagePath,
                                                     derivedImageFileName, FILE_SUFFIX)
                #Update tree view with xml file modified above
                treeView.refreshDICOMStudiesTreeView(objWeasel, newSeriesID)
                displayImageColour.displayImageSubWindow(objWeasel, studyID, 
                                                         seriesID, derivedImageFileName)
            elif treeView.isASeriesSelected(objWeasel):
                imagePathList = \
                        objWeasel.objXMLReader.getImagePathList(studyID, seriesID)
                #Iterate through list of images and square each image
                derivedImagePathList = []
                derivedImageList = []
                numImages = len(imagePathList)
                messageWindow.displayMessageSubWindow(objWeasel,
                  "<H4>Thresholding {} DICOM files</H4>".format(numImages),
                  "Thresholding DICOM images")
                messageWindow.setMsgWindowProgBarMaxValue(objWeasel,numImages)
                imageCounter = 0
                for imagePath in imagePathList:
                    derivedImagePath = saveDICOM_Image.returnFilePath(imagePath, FILE_SUFFIX)
                    derivedImage = returnPixelArray(imagePath, listParams[0], listParams[1])
                    derivedImagePathList.append(derivedImagePath)
                    derivedImageList.append(derivedImage)
                    imageCounter += 1
                    messageWindow.setMsgWindowProgBarValue(objWeasel, imageCounter)
                messageWindow.displayMessageSubWindow(objWeasel,
                  "<H4>Saving results into a new DICOM Series</H4>",
                  "Thresholding DICOM images")
                messageWindow.setMsgWindowProgBarMaxValue(objWeasel,2)
                messageWindow.setMsgWindowProgBarValue(objWeasel,1)
                # Save new DICOM series locally
                saveDICOM_Image.saveDicomNewSeries(derivedImagePathList, imagePathList, derivedImageList, FILE_SUFFIX)
                newSeriesID = interfaceDICOMXMLFile.insertNewSeriesInXMLFile(objWeasel,
                                                       imagePathList,
                                                       derivedImagePathList, FILE_SUFFIX)
                messageWindow.setMsgWindowProgBarValue(objWeasel,2)
                messageWindow.closeMessageSubWindow(objWeasel)
                displayImageColour.displayMultiImageSubWindow(objWeasel,
                    derivedImagePathList, studyID, newSeriesID)
                treeView.refreshDICOMStudiesTreeView(objWeasel, newSeriesID)
    except Exception as e:
        exception_type, exception_object, exception_traceback = sys.exc_info()
        #filename = exception_traceback.tb_frame.f_code.co_filename
        line_number = exception_traceback.tb_lineno
        print('Error in thresholdDICOM_Image.main at line {}: '.format(line_number) + str(e))
