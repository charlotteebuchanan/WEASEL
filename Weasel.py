
from PyQt5 import QtCore 
from PyQt5.QtCore import  Qt, pyqtSignal, QObject
from PyQt5.QtWidgets import (QAction, QApplication, QFileDialog,                            
        QMdiArea, QMessageBox, QWidget, QGridLayout, QVBoxLayout, QSpinBox,
        QMdiSubWindow, QGroupBox, QMainWindow, QHBoxLayout, QDoubleSpinBox,
        QPushButton, QStatusBar, QLabel, QAbstractSlider, QHeaderView,
        QTreeWidgetItem, QGridLayout, QSlider, QCheckBox, QLayout, 
        QProgressBar, QComboBox, QTableWidget, QTableWidgetItem, QFrame)
from PyQt5.QtGui import QCursor, QIcon, QColor

#import pyqtgraph as pg import statement for pip installed version of pyqtGraph
import os
import sys
import time
import re
import struct
import numpy as np
import scipy
from scipy.stats import iqr
import logging
import pathlib
import importlib
import matplotlib.pyplot as plt #delete?
from matplotlib import cm #delete?


#Add folders CoreModules  Developer/ModelLibrary to the Module Search Path. 
#path[0] is the current working directory
#pathlib.Path().absolute() is the current directory where the script is located. 
#It doesn't matter if it's Python SYS or Windows SYS
sys.path.append(os.path.join(sys.path[0],'Developer//WEASEL//Tools//'))
sys.path.append(os.path.join(sys.path[0],
        'Developer//WEASEL//Tools//FERRET_Files//'))
sys.path.append(os.path.join(sys.path[0],'CoreModules'))
sys.path.append(os.path.join(sys.path[0],'CoreModules//WEASEL//'))
import CoreModules.readDICOM_Image as readDICOM_Image
import CoreModules.saveDICOM_Image as saveDICOM_Image

import Developer.WEASEL.Tools.binaryOperationDICOM_Image as binaryOperationDICOM_Image
import CoreModules.styleSheet as styleSheet
from Developer.WEASEL.Tools.FERRET import FERRET as ferret
from CoreModules.weaselXMLReader import WeaselXMLReader
import CoreModules.imagingTools as imagingTools
import CoreModules.WEASEL.TreeView  as treeView
import CoreModules.WEASEL.Menus  as menus
import CoreModules.WEASEL.ToolBar  as toolBar
import CoreModules.WEASEL.DisplayImageColour  as displayImageColour
import Developer.WEASEL.Tools
#access pyqtGraph from the source code imported into this project
import CoreModules.pyqtgraph as pg 

__version__ = '1.0'
__author__ = 'Steve Shillitoe'


DEFAULT_IMAGE_FILE_PATH_NAME = 'C:\DICOM_Image.png'
FERRET_LOGO = 'images\\FERRET_LOGO.png'
#Create and configure the logger
#First delete the previous log file if there is one
LOG_FILE_NAME = "WEASEL1.log"
if os.path.exists(LOG_FILE_NAME):
    os.remove(LOG_FILE_NAME) 
LOG_FORMAT = "%(levelname)s %(asctime)s - %(message)s"
logging.basicConfig(filename=LOG_FILE_NAME, 
                level=logging.INFO, 
                format=LOG_FORMAT)
logger = logging.getLogger(__name__)


class Weasel(QMainWindow):
    def __init__(self): 
        """Creates the MDI container."""
        super (). __init__ () 

        self.showFullScreen()
        self.setWindowTitle("WEASEL")
        self.centralwidget = QWidget(self)
        self.setCentralWidget(self.centralwidget)
        self.centralwidget.setLayout(QVBoxLayout(self.centralwidget))
        self.mdiArea = QMdiArea(self.centralwidget)
        self.mdiArea.tileSubWindows()
        self.centralwidget.layout().addWidget(self.mdiArea)
        self.currentImagePath = ''
        self.statusBar = QStatusBar()
        self.centralwidget.layout().addWidget(self.statusBar)
        self.selectedStudy = ''
        self.selectedSeries = ''
        #self.selectedImagePath = ''
        self.selectedImageName = ''
        self.overRideSavedColourmapAndLevels = False #Set to True if the user checks the Apply Selection tick box
        self.applyUserSelection = False
        self.userSelectionList = []
        
         # XML reader object to process XML configuration file
        self.objXMLReader = WeaselXMLReader() 
        logger.info("WEASEL GUI created successfully.")

        menus.setupMenus(self)
        toolBar.setupToolBar(self)
        self.ApplyStyleSheet()

 
    def ApplyStyleSheet(self):
        """Modifies the appearance of the GUI using CSS instructions"""
        try:
            self.setStyleSheet(styleSheet.TRISTAN_GREY)
            logger.info('WEASEL Style Sheet applied.')
        except Exception as e:
            print('Error in function WEASEL.ApplyStyleSheet: ' + str(e))
  
            
    def getMDIAreaDimensions(self):
        return self.mdiArea.height(), self.mdiArea.width() 


    def setMsgWindowProgBarMaxValue(self, maxValue):
        self.progBarMsg.show()
        self.progBarMsg.setMaximum(maxValue)


    def setMsgWindowProgBarValue(self, value):
        self.progBarMsg.setValue(value)


    def closeMessageSubWindow(self):
        self.msgSubWindow.close()


    @QtCore.pyqtSlot(QTreeWidgetItem, int)
    def onTreeViewItemClicked(self, item, col):
        """When a DICOM study treeview item is clicked, this function
        populates the relevant class variables that store the following
        DICOM image data: study ID, Series ID, Image name, image file path"""
        logger.info("WEASEL onTreeViewItemClicked called")
        selectedText = item.text(0)
        if 'study' in selectedText.lower():
            studyID = selectedText.replace('Study -', '').strip()
            self.selectedStudy = studyID
            self.selectedSeries = ''
            self.selectedImagePath = ''
            self.selectedImageName = ''
            self.statusBar.showMessage('Study - ' + studyID + ' selected.')
        elif 'series' in selectedText.lower():
            seriesID = selectedText.replace('Series -', '').strip()
            studyID = item.parent().text(0).replace('Study -', '').strip()
            self.selectedStudy = studyID
            self.selectedSeries = seriesID
            self.selectedImagePath = ''
            self.selectedImageName = ''
            fullSeriesID = studyID + ': ' + seriesID + ': no image selected.'
            self.statusBar.showMessage('Study and series - ' +  fullSeriesID)
        elif 'image' in selectedText.lower():
            imageID = selectedText.replace('Image -', '')
            imagePath =item.text(3)
            seriesID = item.parent().text(0).replace('Series -', '').strip()
            studyID = item.parent().parent().text(0).replace('Study -', '').strip()
            self.selectedStudy = studyID
            self.selectedSeries = seriesID
            self.selectedImagePath = imagePath.strip()
            self.selectedImageName = imageID.strip()
            fullImageID = studyID + ': ' + seriesID + ': '  + imageID
            self.statusBar.showMessage('Image - ' + fullImageID + ' selected.')


    def displayFERRET(self):
        """
        Displays FERRET in a sub window 
        """
        try:
            logger.info("WEASEL displayFERRET called")
            self.closeAllSubWindows()
            self.subWindow = QMdiSubWindow(self)
            self.subWindow.setAttribute(Qt.WA_DeleteOnClose)
            self.subWindow.setWindowFlags(Qt.CustomizeWindowHint | 
                                          Qt.WindowCloseButtonHint)
            
            ferretWidget = ferret(self.subWindow, self.statusBar)
            self.subWindow.setWidget(ferretWidget.returnFerretWidget())
            
            self.subWindow.setWindowTitle('FERRET')
            self.subWindow.setWindowIcon(QIcon(FERRET_LOGO))
            self.mdiArea.addSubWindow(self.subWindow)
            self.subWindow.showMaximized()
        except Exception as e:
            print('Error in displayFERRET: ' + str(e))
            logger.error('Error in displayFERRET: ' + str(e)) 


    def displayMessageSubWindow(self, message, title="Loading DICOM files"):
        """
        Creates a subwindow that displays a message to the user. 
        """
        try:
            
            logger.info('LoadDICOM.displayMessageSubWindow called.')
            for subWin in self.mdiArea.subWindowList():
                if subWin.objectName() == "Msg_Window":
                    subWin.close()
                    
            widget = QWidget()
            widget.setLayout(QVBoxLayout()) 
            self.msgSubWindow = QMdiSubWindow(self)
            self.msgSubWindow.setAttribute(Qt.WA_DeleteOnClose)
            self.msgSubWindow.setWidget(widget)
            self.msgSubWindow.setObjectName("Msg_Window")
            self.msgSubWindow.setWindowTitle(title)
            height, width = self.getMDIAreaDimensions()
            self.msgSubWindow.setGeometry(0,0,width*0.5,height*0.25)
            lblMsg = QLabel('<H4>' + message + '</H4>')
            widget.layout().addWidget(lblMsg)

            self.progBarMsg = QProgressBar(self)
            widget.layout().addWidget(self.progBarMsg)
            widget.layout().setAlignment(Qt.AlignTop)
            self.progBarMsg.hide()
            self.progBarMsg.setValue(0)

            self.mdiArea.addSubWindow(self.msgSubWindow)
            self.msgSubWindow.show()
            QApplication.processEvents()
        except Exception as e:
            print('Error in : Weasel.displayMessageSubWindow' + str(e))
            logger.error('Error in : Weasel.displayMessageSubWindow' + str(e))

    def synchroniseROIs(self, chkBox):
        """Synchronises the ROIs in all the open image subwindows"""
        logger.info("WEASEL synchroniseROIs")
        if chkBox.isChecked():
            for subWin in self.mdiArea.subWindowList():
                if (subWin.objectName() == 'tree_view' 
                    or subWin.objectName() == 'Binary_Operation'
                    or subWin.objectName() == 'Msg_Window'
                    or subWin.objectName() == 'metaData_Window'):
                    continue
                print ('subwindow object name ', subWin.objectName())
                for item in subWin.widget().children():
                    print ('item', item)
                    for child in item.children():
                        print ('child of item    ', child)               
                QApplication.processEvents()


    def getImagePathList(self, studyID, seriesID):
        return self.objXMLReader.getImagePathList(studyID, seriesID)


    def insertNewBinOpImageInXMLFile(self, newImageFileName, suffix):
        """This function inserts information regarding a new image 
        created by a binary operation on 2 images in the DICOM XML file
       """
        try:
            logger.info("WEASEL insertNewBinOpImageInXMLFile called")
            studyID = self.selectedStudy 
            seriesID = self.selectedSeries
            #returns new series ID
            return self.objXMLReader.insertNewBinOpsImageInXML(
                newImageFileName, studyID, seriesID, suffix)
        except Exception as e:
            print('Error in Weasel.insertNewBinOpImageInXMLFile: ' + str(e))
            logger.error('Error in Weasel.insertNewBinOpImageInXMLFile: ' + str(e))


    def insertNewImageInXMLFile(self, newImageFileName, suffix):
        """This function inserts information regarding a new image 
         in the DICOM XML file
       """
        try:
            logger.info("WEASEL insertNewImageInXMLFile called")
            studyID = self.selectedStudy 
            seriesID = self.selectedSeries
            imagePath = self.selectedImagePath
            #returns new series ID or existing series ID
            #as appropriate
            return self.objXMLReader.insertNewImageInXML(imagePath,
                   newImageFileName, studyID, seriesID, suffix)
            
        except Exception as e:
            print('Error in insertNewImageInXMLFile: ' + str(e))
            logger.error('Error in insertNewImageInXMLFile: ' + str(e))


    def getNewSeriesName(self, studyID, dataset, suffix):
        """This function uses recursion to find the next available
        series name.  A new series name is created by adding a suffix
        at the end of an existing series name. """
        try:
            seriesID = dataset.SeriesDescription + "_" + str(dataset.SeriesNumber)
            imageList = self.objXMLReader.getImageList(studyID, seriesID)
            if imageList:
                #A series of images already exists 
                #for the series called seriesID
                #so make another new series ID 
                #by adding the suffix to the previous
                #new series ID
                dataset.SeriesDescription = dataset.SeriesDescription + suffix
                return self.getNewSeriesName(studyID, dataset, suffix)
            else:
                logger.info("WEASEL getNewSeriesName returns seriesID {}".format(seriesID))
                return seriesID
        except Exception as e:
            print('Error in Weasel.getNewSeriesName: ' + str(e))
            print('Error in Weasel.getNewSeriesName: ' + str(e))


    def insertNewSeriesInXMLFile(self, origImageList, newImageList, suffix):
        """Creates a new series to hold the series of New images"""
        try:
            logger.info("WEASEL insertNewSeriesInXMLFile called")
            #Get current study & series IDs
            studyID = self.selectedStudy 
            seriesID = self.selectedSeries 
            #Get a new series ID
            dataset = readDICOM_Image.getDicomDataset(newImageList[0])
            newSeriesID = self.getNewSeriesName(studyID, dataset, suffix)
            self.objXMLReader.insertNewSeriesInXML(origImageList, 
                     newImageList, studyID, newSeriesID, seriesID, suffix)
            self.statusBar.showMessage('New series created: - ' + newSeriesID)
            return  newSeriesID

        except Exception as e:
            print('Error in Weasel.insertNewSeriesInXMLFile: ' + str(e))
            logger.error('Error in Weasel.insertNewImageInXMLFile: ' + str(e))           

    def displayBinaryOperationsWindow(self):
        """Displays the sub window for performing binary operations
        on 2 images"""
        try:
            logger.info("WEASEL displayBinaryOperationsWindow called")
            self.subWindow = QMdiSubWindow(self)
            self.subWindow.setAttribute(Qt.WA_DeleteOnClose)
            self.subWindow.setWindowFlags(Qt.CustomizeWindowHint
                  | Qt.WindowCloseButtonHint | Qt.WindowMinimizeButtonHint)
            layout = QGridLayout()
            widget = QWidget()
            widget.setLayout(layout)
            self.subWindow.setWidget(widget)
            pg.setConfigOptions(imageAxisOrder='row-major')

            imageViewer1 = pg.GraphicsLayoutWidget()
            viewBox1 = imageViewer1.addViewBox()
            viewBox1.setAspectLocked(True)
            self.img1 = pg.ImageItem(border='w')
            viewBox1.addItem(self.img1)
            self.imv1 = pg.ImageView(view=viewBox1, imageItem=self.img1)
            self.imv1.ui.histogram.hide()
            self.imv1.ui.roiBtn.hide()
            self.imv1.ui.menuBtn.hide()

            imageViewer2 = pg.GraphicsLayoutWidget()
            viewBox2 = imageViewer2.addViewBox()
            viewBox2.setAspectLocked(True)
            self.img2 = pg.ImageItem(border='w')
            viewBox2.addItem(self.img2)
            self.imv2 = pg.ImageView(view=viewBox2, imageItem=self.img2)
            self.imv2.ui.histogram.hide()
            self.imv2.ui.roiBtn.hide()
            self.imv2.ui.menuBtn.hide()

            imageViewer3 = pg.GraphicsLayoutWidget()
            viewBox3 = imageViewer3.addViewBox()
            viewBox3.setAspectLocked(True)
            self.img3 = pg.ImageItem(border='w')
            viewBox3.addItem(self.img3)
            self.imv3 = pg.ImageView(view=viewBox3, imageItem=self.img3)
            self.imv3.ui.histogram.hide()
            self.imv3.ui.roiBtn.hide()
            self.imv3.ui.menuBtn.hide()

            studyID = self.selectedStudy 
            seriesID = self.selectedSeries
            self.lblImageMissing1 = QLabel("<h4>Image Missing</h4>")
            self.lblImageMissing2 = QLabel("<h4>Image Missing</h4>")
            self.lblImageMissing1.hide()
            self.lblImageMissing2.hide()

            self.btnSave = QPushButton('Save')
            self.btnSave.setEnabled(False)
            self.btnSave.clicked.connect(self.saveNewDICOMFileFromBinOp)

            studyID = self.selectedStudy 
            seriesID = self.selectedSeries
            imagePathList = self.objXMLReader.getImagePathList(studyID, 
                                                               seriesID)
            #form a list of image file names without extensions
            imageNameList = [os.path.splitext(os.path.basename(image))[0] 
                             for image in imagePathList]
            self.image_Name_Path_Dict = dict(zip(
                imageNameList, imagePathList))
            self.imageList1 = QComboBox()
            self.imageList2 = QComboBox()
            self.imageList1.currentIndexChanged.connect(
                lambda:self.displayImageForBinOp(1, self.image_Name_Path_Dict))
            self.imageList1.currentIndexChanged.connect(
                self.enableBinaryOperationsCombo)
            self.imageList1.currentIndexChanged.connect(
                lambda:self.doBinaryOperation(self.image_Name_Path_Dict))
            
            self.imageList2.currentIndexChanged.connect(
                lambda:self.displayImageForBinOp(2, self.image_Name_Path_Dict))
            self.imageList2.currentIndexChanged.connect(
                self.enableBinaryOperationsCombo)
            self.imageList2.currentIndexChanged.connect(
                lambda:self.doBinaryOperation(self.image_Name_Path_Dict))

            self.binaryOpsList = QComboBox()
            self.binaryOpsList.currentIndexChanged.connect(
                lambda:self.doBinaryOperation(self.image_Name_Path_Dict))
            self.imageList1.addItems(imageNameList)
            self.imageList2.addItems(imageNameList)
            self.binaryOpsList.addItems(
                binaryOperationDICOM_Image.listBinaryOperations)

            layout.addWidget(self.btnSave, 0, 2)
            layout.addWidget(self.imageList1, 1, 0)
            layout.addWidget(self.imageList2, 1, 1)
            layout.addWidget(self.binaryOpsList, 1, 2)
            layout.addWidget(self.lblImageMissing1, 2, 0)
            layout.addWidget(self.lblImageMissing2, 2, 1)
            #layout.addWidget(imageViewer1, 3, 0)
            #layout.addWidget(imageViewer2, 3, 1)
            #layout.addWidget(imageViewer3, 3, 2)
            layout.addWidget(self.imv1, 3, 0)
            layout.addWidget(self.imv2, 3, 1)
            layout.addWidget(self.imv3, 3, 2)
                
            self.subWindow.setObjectName('Binary_Operation')
            windowTitle = 'Binary Operations'
            self.subWindow.setWindowTitle(windowTitle)
            height, width = self.getMDIAreaDimensions()
            self.subWindow.setGeometry(0,0,width*0.5,height*0.5)
            self.mdiArea.addSubWindow(self.subWindow)
            self.subWindow.show()
        except Exception as e:
            print('Error in displayBinaryOperationsWindow: ' + str(e))
            logger.error('Error in displayBinaryOperationsWindow: ' + str(e))

    
    def saveNewDICOMFileFromBinOp(self):
        """TO DO"""
        try:
            logger.info("WEASEL saveNewDICOMFileFromBinOp called")
            suffix = '_binOp'
            imageName1 = self.imageList1.currentText()
            imagePath1 = self.image_Name_Path_Dict[imageName1]
            imageName2 = self.imageList2.currentText()
            imagePath2 = self.image_Name_Path_Dict[imageName2]
            
            binaryOperation = self.binaryOpsList.currentText()
            prefix = binaryOperationDICOM_Image.getBinOperationFilePrefix(
                                     binaryOperation)
            
            newImageFileName = prefix + '_' + imageName1 \
                + '_' + imageName2 
            newImageFilePath = os.path.dirname(imagePath1) + '\\' + \
                newImageFileName + '.dcm'
            #print(newImageFilePath)
            #Save pixel array to a file
            saveDICOM_Image.saveDicomOutputResult(newImageFilePath, imagePath1, self.binOpArray, "_"+binaryOperation+suffix, list_refs_path=[imagePath2])
            newSeriesID = self.insertNewBinOpImageInXMLFile(newImageFilePath, suffix)
            #print(newSeriesID)
            treeView.refreshDICOMStudiesTreeView(self, newSeriesID)
        except Exception as e:
            print('Error in saveNewDICOMFileFromBinOp: ' + str(e))
            logger.error('Error in saveNewDICOMFileFromBinOp: ' + str(e))


    def doBinaryOperation(self, imageDict):
        """TO DO"""
        try:
            #Get file path of image1
            imageName = self.imageList1.currentText()
            if imageName != '':
                imagePath1 = imageDict[imageName]

            #Get file path of image2
            imageName = self.imageList2.currentText()
            if imageName != '':
                imagePath2 = imageDict[imageName]

            #Get binary operation to be performed
            binOp = self.binaryOpsList.currentText()
            if binOp != 'Select binary Operation' \
                and binOp != '':
                self.btnSave.setEnabled(True)
                self.binOpArray = binaryOperationDICOM_Image.returnPixelArray(
                    imagePath1, imagePath2, binOp)
                minimumValue = np.amin(self.binOpArray) if (np.median(self.binOpArray) - iqr(self.binOpArray, rng=(
                    1, 99))/2) < np.amin(self.binOpArray) else np.median(self.binOpArray) - iqr(self.binOpArray, rng=(1, 99))/2
                maximumValue = np.amax(self.binOpArray) if (np.median(self.binOpArray) + iqr(self.binOpArray, rng=(
                    1, 99))/2) > np.amax(self.binOpArray) else np.median(self.binOpArray) + iqr(self.binOpArray, rng=(1, 99))/2
                self.img3.setImage(self.binOpArray, autoHistogramRange=True, levels=(minimumValue, maximumValue)) 
            else:
                self.btnSave.setEnabled(False)
        except Exception as e:
            print('Error in doBinaryOperation: ' + str(e))
            logger.error('Error in doBinaryOperation: ' + str(e))


    def enableBinaryOperationsCombo(self):
        """TO DO"""
        if self.lblImageMissing1.isHidden() and \
            self.lblImageMissing2.isHidden():
            self.binaryOpsList.setEnabled(True)
        else:
            self.binaryOpsList.setEnabled(False)
            self.btnSave.setEnabled(False)


    def displayImageForBinOp(self, imageNumber, imageDict):
        """TO DO"""
        try:
            objImageMissingLabel = getattr(self, 'lblImageMissing' + str(imageNumber))
            objImage = getattr(self, 'img' + str(imageNumber))
            objComboBox = getattr(self, 'imageList' + str(imageNumber))

            #get name of selected image
            imageName = objComboBox.currentText()
            imagePath = imageDict[imageName]
            pixelArray = readDICOM_Image.returnPixelArray(imagePath)
            if pixelArray is None:
                objImageMissingLabel.show()
                objImage.setImage(np.array([[0,0,0],[0,0,0]])) 
            else:
                objImageMissingLabel.hide()
                minimumValue = np.amin(pixelArray) if (np.median(pixelArray) - iqr(pixelArray, rng=(
                    1, 99))/2) < np.amin(pixelArray) else np.median(pixelArray) - iqr(pixelArray, rng=(1, 99))/2
                maximumValue = np.amax(pixelArray) if (np.median(pixelArray) + iqr(pixelArray, rng=(
                    1, 99))/2) > np.amax(pixelArray) else np.median(pixelArray) + iqr(pixelArray, rng=(1, 99))/2
                objImage.setImage(pixelArray, autoHistogramRange=True, levels=(minimumValue, maximumValue))  
        except Exception as e:
            print('Error in displayImageForBinOp: ' + str(e))
            logger.error('Error in displayImageForBinOp: ' + str(e))


    def closeSubWindow(self, objectName):
        """Closes a particular sub window in the MDI"""
        logger.info("WEASEL closeSubWindow called for {}".format(objectName))
        for subWin in self.mdiArea.subWindowList():
            if subWin.objectName() == objectName:
                QApplication.processEvents()
                subWin.close()
                QApplication.processEvents()
                break


    def closeAllSubWindows(self):
        """Closes all the sub windows open in the MDI"""
        logger.info("WEASEL closeAllSubWindows called")
        self.mdiArea.closeAllSubWindows()
        self.treeView = None  


    def deleteImage(self):
        """TO DO"""
        """This method deletes an image or a series of images by 
        deleting the physical file(s) and then removing their entries
        in the XML file."""
        try:
            studyID = self.selectedStudy
            seriesID = self.selectedSeries
            if self.isAnImageSelected():
                imageName = self.selectedImageName
                imagePath = self.selectedImagePath
                buttonReply = QMessageBox.question(self, 
                  'Delete DICOM image', "You are about to delete image {}".format(imageName), 
                  QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)
                if buttonReply == QMessageBox.Ok:
                    #Delete physical file if it exists
                    if os.path.exists(imagePath):
                        os.remove(imagePath)
                    #If this image is displayed, close its subwindow
                    self.closeSubWindow(imagePath)
                    #Is this the last image in a series?
                    #Get the series containing this image and count the images it contains
                    #If it is the last image in a series then remove the
                    #whole series from XML file
                    #No it is not the last image in a series
                    #so just remove the image from the XML file 
                    images = self.objXMLReader.getImageList(studyID, seriesID)
                    if len(images) == 1:
                        #only one image, so remove the series from the xml file
                        #need to get study (parent) containing this series (child)
                        #then remove child from parent
                        self.objXMLReader.removeSeriesFromXMLFile(studyID, seriesID)
                    elif len(images) > 1:
                        #more than 1 image in the series, 
                        #so just remove the image from the xml file
                        self.objXMLReader.removeOneImageFromSeries(
                            studyID, seriesID, imagePath)
                    #Update tree view with xml file modified above
                    treeView.refreshDICOMStudiesTreeView(self)
            elif self.isASeriesSelected():
                buttonReply = QMessageBox.question(self, 
                  'Delete DICOM series', "You are about to delete series {}".format(seriesID), 
                  QMessageBox.Ok | QMessageBox.Cancel, QMessageBox.Cancel)
                if buttonReply == QMessageBox.Ok:
                    #Delete each physical file in the series
                    #Get a list of names of images in that series
                    imageList = self.objXMLReader.getImagePathList(studyID, 
                                                                   seriesID) 
                    #Iterate through list of images and delete each image
                    for imagePath in imageList:
                        if os.path.exists(imagePath):
                            os.remove(imagePath)
                    #Remove the series from the XML file
                    self.objXMLReader.removeSeriesFromXMLFile(studyID, seriesID)
                    self.closeSubWindow(seriesID)
                treeView.refreshDICOMStudiesTreeView(self)
        except Exception as e:
            print('Error in deleteImage: ' + str(e))
            logger.error('Error in deleteImage: ' + str(e))


    def isAnImageSelected(self):
        """Returns True is a single image is selected in the DICOM
        tree view, else returns False"""
        try:
            logger.info("WEASEL isAnImageSelected called.")
            selectedItem = self.treeView.currentItem()
            if selectedItem:
                if 'image' in selectedItem.text(0).lower():
                    return True
                else:
                    return False
            else:
               return False
        except Exception as e:
            print('Error in isAnImageSelected: ' + str(e))
            logger.error('Error in isAnImageSelected: ' + str(e))
            

    def isASeriesSelected(self):
        """Returns True is a series is selected in the DICOM
        tree view, else returns False"""
        try:
            logger.info("WEASEL isASeriesSelected called.")
            selectedItem = self.treeView.currentItem()
            if selectedItem:
                if 'series' in selectedItem.text(0).lower():
                    return True
                else:
                    return False
            else:
               return False
        except Exception as e:
            print('Error in isASeriesSelected: ' + str(e))
            logger.error('Error in isASeriesSelected: ' + str(e))


    def getDICOMFileData(self):
        """When a DICOM image is selected in the tree view, this function
        returns its description in the form - study number: series number: image name"""
        try:
            logger.info("WEASEL getDICOMFileData called.")
            selectedImage = self.treeView.selectedItems()
            if selectedImage:
                imageNode = selectedImage[0]
                seriesNode  = imageNode.parent()
                imageName = imageNode.text(0)
                series = seriesNode.text(0)
                studyNode = seriesNode.parent()
                study = studyNode.text(0)
                fullImageName = study + ': ' + series + ': '  + imageName
                return fullImageName
            else:
                return ''
        except Exception as e:
            print('Error in getDICOMFileData: ' + str(e))
            logger.error('Error in getDICOMFileData: ' + str(e))


def main():
    app = QApplication(sys . argv )
    winMDI = Weasel()
    winMDI.showMaximized()
    sys.exit(app.exec())

if __name__ == '__main__':
        main()


        