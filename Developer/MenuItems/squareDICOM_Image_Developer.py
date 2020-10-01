
import Developer.MenuItems.developerToolsModule as tool
#**************************************************************************
#Added by third party developer to the template module. 
#The function containing the image processing algorithm must be given the 
#generic name, funcAlgorithm
#uncomment and edit the following line of code to import the function 
#containing your image processing algorith. 
from Developer.ScientificLibrary.imagingTools import squareAlgorithm
FILE_SUFFIX = '_Square'
#***************************************************************************

def isSeriesOnly(self):
    #This functionality only applies to a series of DICOM images
    return True


def processPipeline2D(objWeasel):
    if tool.treeView.isAnImageSelected(objWeasel):
        imagePath = tool.getImagePath(objWeasel)
        derivedImageFileName = tool.setNewFilePath(imagePath, FILE_SUFFIX)
        pixelArray = tool.getPixelArrayFromDICOM(imagePath)
        derivedImage = tool.applyProcessInOneImage(squareAlgorithm, pixelArray)
        tool.saveNewDICOMAndDisplayResult(objWeasel, imagePath, derivedImageFileName, derivedImage, FILE_SUFFIX)
    elif tool.treeView.isASeriesSelected(objWeasel):
        imagePathList = tool.getImagePathList(objWeasel)
        derivedImagePathList, derivedImageList = tool.applyProcessIterativelyInSeries(objWeasel, imagePathList, FILE_SUFFIX, squareAlgorithm, progress_bar=True)        
        tool.saveNewDICOMAndDisplayResult(objWeasel, imagePathList, derivedImagePathList, derivedImageList, FILE_SUFFIX)


def processPipeline3D(objWeasel):
        imagePathList = tool.getImagePathList(objWeasel)
        tool.showProcessingMessageBox(objWeasel)
        pixelArray = tool.getPixelArrayFromDICOM(imagePathList)
        derivedImage = tool.applyProcessInOneImage(squareAlgorithm, pixelArray)
        #pixelArray = np.square(pixelArray)

        #derivedImagePathList, derivedImageList = tool.prepareBulkSeriesSave(objWeasel, imagePathList, derivedImage, FILE_SUFFIX)
        #tool.saveNewDICOMAndDisplayResult(objWeasel, imagePathList, derivedImagePathList, derivedImageList, FILE_SUFFIX)
        
        resultingPath = tool.writeNewPixelArray(objWeasel, derivedImage, imagePathList, FILE_SUFFIX)
        tool.displayImage(objWeasel, resultingPath)