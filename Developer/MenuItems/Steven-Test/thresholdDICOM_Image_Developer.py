from Developer.DeveloperTools import UserInterfaceTools as ui
from Developer.DeveloperTools import Series, Image
#**************************************************************************
from Developer.External.imagingTools import thresholdPixelArray
FILE_SUFFIX = '_Thresholded'
#***************************************************************************

def isSeriesOnly(self):
    #This functionality only applies to a series of DICOM images
    return True


def main(objWeasel):
    seriesPathList = ui.getCheckedSeries(objWeasel)
    # Lower and upper threshold from the input window 
    inputDict = {"Lower Threshold":"integer", "Upper Threshold":"integer"}
    info = "Insert a value between 0 and 100. Upper threshold must be greater than lower threshold"
    paramList = ui.inputWindow(inputDict, title="Input Parameters", helpText=info)
    if paramList is None: return # Exit function if the user hits the "Cancel" button
    low_thresh = paramList[0]
    high_thresh = paramList[1]
    index_series = 1
    for series in seriesPathList:
        newSeries = Series.newSeriesFrom(series, suffix=FILE_SUFFIX)
        index_bar = 0
        for image in series.children:
            newImage = Image.newImageFrom(image, series=newSeries)
            index_bar = ui.progressBar(objWeasel, maxNumber=series.numberChildren, index=index_bar, msg="Thresholding and saving image {}", title="Threshold of series "+str(index_series))
            pixelArray = image.PixelArray
            pixelArray = thresholdPixelArray(pixelArray, low_thresh, high_thresh) # NOT WORKING WELL ON NEGATIVE IMAGES
            newImage.write(pixelArray, series=newSeries)
        index_series += 1
    ui.closeMessageWindow(objWeasel)
    # Refresh the UI screen
    ui.refreshWeasel(objWeasel, newSeriesName=newSeries.seriesID)
    newSeries.DisplaySeries()