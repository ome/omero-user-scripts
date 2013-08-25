#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
 analysis_scripts/Simple_FRAP.py

-----------------------------------------------------------------------------
  Copyright (C) 2013 University of Dundee. All rights reserved.


  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.
  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.

------------------------------------------------------------------------------

Simply analyses the average pixel intensity for ellipses in a 
movie and attempts to estimate the half-time of FRAP recovery
and the percent recovery (mobile fraction).
Needs ellipses drawn on all timepoints to be included in the 
analysis, and needs at least 1 pre-bleach frame.
"""

import omero
import omero.scripts as scripts
from omero.rtypes import rdouble, rint, rlong, rstring
from omero.gateway import BlitzGateway
import omero.util.script_utils as scriptUtil


# To keep things simple, we'll work with a single Ellipse per T
# =================================================================
def getEllipses(conn, imageId):
    """ 
    Returns the a dict of tIndex: {'cx':cx, 'cy':cy, 'rx':rx, 'ry':ry, 'z':z} 
    NB: Assume only 1 ellipse per time point

    @param conn:    BlitzGateway connection
    @param imageId:     Image ID
    """

    ellipses = {}
    result = conn.getRoiService().findByImage(imageId, None, conn.SERVICE_OPTS)

    for roi in result.rois:
        for shape in roi.copyShapes():
            if type(shape) == omero.model.EllipseI:
                cx = int(shape.getCx().getValue())
                cy = int(shape.getCy().getValue())
                rx = int(shape.getRx().getValue())
                ry = int(shape.getRy().getValue())
                z = int(shape.getTheZ().getValue())
                t = int(shape.getTheT().getValue())
                ellipses[t] = {'cx':cx, 'cy':cy, 'rx':rx, 'ry':ry, 'z':z}
    return ellipses


def getEllipseData(image, ellipses, theC=0):
    """ Returns a dict of t:averageIntensity for all ellipses. 
    
    @param ellipse:     The ellipse defined as a tuple (cx, cy, rx, ry, z, t)
    @returns:           A list of (x,y) points for the ellipse
    """
    data = {}
    for t, e in ellipses.items():
        cx = e['cx']
        cy = e['cy']
        rx = e['rx']
        ry = e['ry']

        # find bounding box of ellipse
        xStart = cx - rx
        xEnd = cx + rx
        yStart = cy - ry
        yEnd = cy + ry
        width = rx * 2
        height = ry * 2

        # get pixel data for the 'tile'
        tileData = image.getPrimaryPixels().getTile(theZ=e['z'], theC=theC, theT=t, tile=(xStart, yStart, width, height))

        # find the pixels within the ellipse
        pixelValues = []
        for x in range(xStart, xEnd):
            for y in range(yStart, yEnd):
                dx = x - e['cx']
                dy = y - e['cy']
                r = float(dx*dx)/float(rx*rx) + float(dy*dy)/float(ry*ry)
                if r <= 1:
                    pixelValues.append(tileData[dx][dy])
        # get the average intensity
        average = sum(pixelValues)/len(pixelValues)
        data[t] = average
    return data


def getTimes(conn, image, theC=0):
    """
    Get a dict of tIndex:time (seconds) for the first plane (Z = 0) at 
    each time-point for the defined image and Channel.
    
    @param conn:        BlitzGateway connection
    @param image:       ImageWrapper
    @return:            A map of tIndex: timeInSecs
    """

    queryService = conn.getQueryService()
    pixelsId = image.getPixelsId()

    params = omero.sys.ParametersI()
    params.add("theC", rint(theC))
    params.add("theZ", rint(0))
    params.add("pixelsId", rlong(pixelsId))

    query = "from PlaneInfo as Info where Info.theZ=:theZ and Info.theC=:theC and pixels.id=:pixelsId"
    infoList = queryService.findAllByQuery(query, params, conn.SERVICE_OPTS)

    timeMap = {}
    for info in infoList:
        tIndex = info.theT.getValue()
        time = info.deltaT.getValue() 
        timeMap[tIndex] = time
    return timeMap    
    


def analyseImage(conn, image, cIndex):

    print "\n---------------------"
    print "Analysing Image: ", image.getName()
    # Get dictionary of tIndex:ellipse
    ellipses = getEllipses(conn, image.getId())
    # Get dictionary of tIndex:averageIntensity
    intensityData = getEllipseData(image, ellipses, cIndex)

    # Get dictionary of tIndex:timeStamp (secs)
    timeValues = getTimes(conn, image)


    # We now have all the Data we need from OMERO

    # create lists of times (secs) and intensities...
    timeList = []
    valueList = []

    # ...Ordered by tIndex
    for t in range(image.getSizeT()):
        if t in intensityData:
            timeList.append( timeValues[t] )
            valueList.append( intensityData[t] )

    print "Analysing pixel values for %s time points" % len(timeList)

    # Find the bleach intensity & time
    bleachValue = min(valueList)
    bleachTindex = valueList.index(bleachValue)
    bleachTime = timeList[bleachTindex]
    preBleachValue = valueList[bleachTindex-1]

    print "Bleach at tIndex: %s, TimeStamp: %0.2f seconds" % (bleachTindex, bleachTime)
    print "Before Bleach: %0.2f, After Bleach: %0.2f" % (preBleachValue, bleachValue)

    # Use last timepoint for max recovery
    recoveryValue = valueList[-1]
    endTimepoint = timeList[-1]
    mobileFraction = (recoveryValue - bleachValue)/(preBleachValue - bleachValue)

    print "Recovered to: %0.2f, after %0.2f seconds" % (recoveryValue, endTimepoint)
    print "Mobile Fraction: %0.2f" % mobileFraction

    halfRecovery = (recoveryValue + bleachValue)/2

    # quick & dirty - pick the first timepoint where we exceed half recovery
    recoveryValues = valueList[bleachTindex:]   # just the values & times after bleach time
    recoveryTimes = timeList[bleachTindex:]
    for t, v in zip(recoveryTimes, recoveryValues):
        if v >= halfRecovery:
            tHalf = t - bleachTime
            break

    print "tHalf: %0.2f seconds" % tHalf


    csvLines = [ 
        "Time (secs)," + ",".join([str(t) for t in timeList]),
        "\n",
        "Average pixel value," + ",".join([str(v) for v in valueList]),
        "\n",
        "tHalf (secs), %0.2f seconds" % tHalf,
        "mobileFraction, %0.2f" % mobileFraction
        ]

    f = open("FRAP.csv", "w")
    f.writelines(csvLines)
    f.close()

    namespace = "/omero-user-scripts/example/Simple_FRAP/"
    scriptUtil.createLinkFileAnnotation(conn, "FRAP.csv", image, ns=namespace)

    return tHalf


def doFrapAnalysis(conn, scriptParams):

    imageIds = scriptParams['IDs']
    cIndex = scriptParams['Channel_Index'] - 1      # convert to 0-based index

    images = conn.getObjects("Image", imageIds)

    results = []

    for i in images:
        rslt = analyseImage(conn, i, cIndex)
        if rslt is not None:
            results.append(rslt)

    return results


def runAsScript():
    """
    The main entry point of the script, as called by the client via the scripting service, passing the required parameters.
    """

    dataTypes = [rstring('Image')]

    client = scripts.client('Simple_FRAP.py', """Analyse average intensity within ellipses over time and
do simple FRAP analysis to get mobile fraction and half-time of recovery.
Needs at least on pre-bleach timepoint and ellipses on all timepoints to be analysed.
""",

    scripts.String("Data_Type", optional=False, grouping="1",
        description="Choose source of images (only Image supported)", values=dataTypes, default="Image"),

    scripts.List("IDs", optional=False, grouping="2",
        description="List of Image IDs to analyse.").ofType(rlong(0)),

    scripts.Int("Channel_Index", optional=False, grouping="3",
        description="The channel to analyse.", default=1, min=1),

    version = "4.4.8",
    authors = ["William Moore", "OME Team"],
    institutions = ["University of Dundee"],
    contact = "ome-users@lists.openmicroscopy.org.uk",
    )

    try:

        # process the list of args above.
        scriptParams = {}
        for key in client.getInputKeys():
            if client.getInput(key):
                scriptParams[key] = client.getInput(key, unwrap=True)

        print scriptParams

        # wrap client to use the Blitz Gateway
        conn = BlitzGateway(client_obj=client)

        # process images in Datasets
        results = doFrapAnalysis(conn, scriptParams)
        if len(results) == 1:
            message = "FRAP tHalf: %0.2f seconds" % results[0]
        elif len(results) == 0:
            message = "No Images Analysed. See Info for more details"
        else:
            average = sum(results)/len(results)
            message = "Average FRAP t-half (%s images): %0.2f seconds. " % (len(results), average)

        # Return the output - display Message:
        client.setOutput("Message", rstring(message))

    finally:
        client.closeSession()

if __name__ == "__main__":
    runAsScript()
