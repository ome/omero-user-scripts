#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
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

This script searches for Images, using database queries queries generated
from a number of parameters.
"""

import omero.scripts as scripts
from omero.gateway import BlitzGateway
from omero.rtypes import *

from datetime import datetime


def searchImages(conn, scriptParams):
    """
    Here we build our hql query and get the results from the queryService
    """

    # Script has defaults for some parameters, so we know these are filled
    minSizeC = scriptParams["Min_Channel_Count"]
    minSizeZ = scriptParams["Min_Size_Z"]
    minSizeT = scriptParams["Min_Size_T"]
    # For others, we check if specified
    channelNames = "Channel_Names" in scriptParams and scriptParams["Channel_Names"] or []
    nominalMagnification = "Magnification" in scriptParams and scriptParams["Magnification"] or None
    lensNA = "Lens_NA" in scriptParams and scriptParams["Lens_NA"] or None
    excitationWave = "Excitation_Wavelength" in scriptParams and scriptParams["Excitation_Wavelength"] or None
    objectiveModel = "Objective_Model" in scriptParams and scriptParams["Objective_Model"] or None

    qs = conn.getQueryService()
    params = omero.sys.Parameters()
    params.map = {}
    clauses = []

    query = "select i from Image i left outer join i.pixels as pixels"

    if minSizeZ > 1 or minSizeC > 1 or minSizeT > 1:
        # We have already joined pixels
        if minSizeZ > 1:
            params.map["sizeZ"] = rint(minSizeZ)
            clauses.append("pixels.sizeZ>=:sizeZ")
        if minSizeC > 1:
            params.map["sizeC"] = rint(minSizeC)
            clauses.append("pixels.sizeC>=:sizeC")
        if minSizeT > 1:
            params.map["sizeT"] = rint(minSizeT)
            clauses.append("pixels.sizeT>=:sizeT")

    if len(channelNames) > 0 or excitationWave is not None:
        query = query + " left outer join pixels.channels as c join c.logicalChannel as lc"
        if len(channelNames) > 0:
            params.map["cNames"] = wrap(channelNames)
            clauses.append("lc.name in (:cNames)")
        if excitationWave is not None:
            params.map["exWave"] = wrap(excitationWave)
            clauses.append("lc.excitationWave=:exWave)")


    if nominalMagnification is not None or lensNA is not None or objectiveModel is not None:
        query += " join i.objectiveSettings as objS join objS.objective as ob"
        if nominalMagnification is not None:
            params.map["nomMag"] = rint(nominalMagnification)
            clauses.append("ob.nominalMagnification=:nomMag")
        if lensNA is not None:
            params.map["lensNA"] = rdouble(lensNA)
            clauses.append("ob.lensNA=:lensNA")
        if objectiveModel is not None:
            params.map["objectiveModel"] = wrap(objectiveModel)
            clauses.append("ob.model=:objectiveModel")

    query = query + " where " + " and ".join(clauses)

    print "Searh parameters map:", unwrap(params.map)
    print query

    imgs = qs.findAllByQuery(query, params)
    return imgs


def tagImages(conn, imageIds, searchDesc=None):
    """
    Creates a new 'search results' Tag with timestamp and links to the images
    """

    now = datetime.now()
    tagText = "Search Results %s %s:%s:%s" % (now.date(), now.hour, now.minute, now.second)
    tag = omero.model.TagAnnotationI()
    tag.setTextValue(wrap(tagText))
    if searchDesc is not None:
        tag.setDescription(wrap(searchDesc))

    newLinks = []
    for iid in imageIds:
        link = omero.model.ImageAnnotationLinkI()
        link.setParent(omero.model.ImageI(iid, False))
        link.child = tag
        newLinks.append(link)

    conn.getUpdateService().saveAndReturnArray(newLinks)
    return tagText


def metadataSearch(conn, scriptParams):
    """
    Here we do the main work of the script, performing search and
    tagging the resulting images. Returns a message for the user.
    """

    searchParams = ["%s: %s" % (k, v) for k, v in scriptParams.items()]
    searchDesc = "\n".join(searchParams)

    # Do the search...
    imageResults = searchImages(conn, scriptParams)
    imgIds = [i.id.val for i in imageResults]
    imgIds = list(set(imgIds))  # remove any duplicates

    print "Result Image IDs: ", imgIds
    tagText = tagImages(conn, imgIds, searchDesc)

    return "%s Images found. Tagged with '%s'" % (len(imgIds), tagText)


def runScript():
    """
    The main entry point of the script, as called by the client via the
    scripting service, passing the required parameters.
    """

    client = scripts.client('Metadata_Search.py', """This script searches for Images,
using database queries generated from a number of parameters.""",

    scripts.Int("Min_Size_Z", grouping="1", default=1, min=1,
        description="Find images with this number of Z-planes or more"),

    scripts.Int("Min_Size_T", grouping="2", default=1, min=1,
        description="Find images with this number of time-points or more"),

    scripts.Int("Min_Channel_Count", grouping="3", default=1, min=1,
        description="Find images with this number of channels or more"),

    scripts.List("Channel_Names", grouping="4",
        description="Find images containing channels with these names"),

    scripts.Int("Excitation_Wavelength", grouping="4.1",
        description="Find images with channels of this excitation wavelength"),

    scripts.String("Objective_Model", grouping="5",
        description="Save individual channels as separate images"),

    scripts.Int("Magnification", grouping="5.1",
        description="Find images with this Nominal Magnification"),

    scripts.String("Lens_NA", grouping="5.2",
        description="Find images with this Lens NA value"),

    version = "4.4.9",
    authors = ["William Moore", "OME Team"],
    institutions = ["University of Dundee"],
    contact = "ome-users@lists.openmicroscopy.org.uk",
    )

    try:
        scriptParams = {}

        conn = BlitzGateway(client_obj=client)

        # process the list of args above.
        for key in client.getInputKeys():
            if client.getInput(key):
                scriptParams[key] = client.getInput(key, unwrap=True)
        print scriptParams

        # call the main script - returns a message
        message = metadataSearch(conn, scriptParams)

        client.setOutput("Message", rstring(message))

    finally:
        client.closeSession()

if __name__ == "__main__":
    runScript()