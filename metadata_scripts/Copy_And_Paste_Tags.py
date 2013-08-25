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

Copy Tags from Datasets or Images and apply them to the 
child images of the Dataset and/or other Datasets / Images
"""

import omero.scripts as scripts
from omero.gateway import BlitzGateway
from omero.rtypes import rstring, rlong


dataTypes = [rstring('Dataset'),rstring('Image')]


def copyAndPasteTags(conn, scriptParams):

    from_type = scriptParams["Data_Type"]
    from_ids = scriptParams["IDs"]

    to_type = scriptParams["Paste_To_Type"]
    to_ids = []
    if "Paste_To_IDs" in scriptParams:
        to_ids = scriptParams["Paste_To_IDs"]

    Paste_To_Contained_Images = scriptParams["Paste_To_Contained_Images"]

    # The Tags we're going to apply
    tags = []

    # The Datasets or Images to add them to
    apply_to = []

    # Get Tags from input Objects
    for obj in conn.getObjects(from_type, from_ids):
        t = [ann for ann in obj.listAnnotations() if ann._obj.__class__.__name__ == "TagAnnotationI"]
        tags.extend(t)

        # Also get the Child Images if we want to tag them
        if Paste_To_Contained_Images and from_type == "Dataset":
            for img in obj.listChildren():
                apply_to.append(img)


    print "Tags", tags

    # If we're applying Tags to other objects, add them to the list
    if to_type is not None and len(to_ids) > 0:
        for obj in conn.getObjects(to_type, to_ids):
            apply_to.append(obj)


    # Do the Tagging
    for obj in apply_to:
        for t in tags:
            # Check the tag is not already on the object
            if len(list(conn.getAnnotationLinks(obj.OMERO_CLASS, parent_ids=[obj.id], ann_ids=[t.id]))) == 0:
                print "Adding Tag:", t.getValue(), " to ", obj.OMERO_CLASS, obj.getName()
                obj.linkAnnotation(t, sameOwner=False)
            else:
                print "** Tag:", t.getValue(), " already on ", obj.OMERO_CLASS, obj.getName()



client = scripts.client('Copy_And_Paste_Tags.py',
"""
Copy Tags from Datasets or Images and apply them to the 
child images of the Dataset and/or other Datasets / Images
""",

    scripts.String("Data_Type", optional=False, grouping="1",
    description="The object type to Copy tags from.", values=dataTypes, default="Dataset"),

    scripts.List("IDs", optional=False, grouping="2",
    description="IDs of Datasets or Images to Copy tags from.").ofType(rlong(0)),

    scripts.Bool("Paste_To_Contained_Images", grouping="3", 
        description="If Copying from Dataset, Add Tags to child Images?", default=False),

    scripts.Bool("Paste_To_Other_Datasets_Or_Images", grouping="4", 
        description="Can also choose other targets to paste the same tags", default=False),

    scripts.String("Paste_To_Type", grouping="4.1",
    description="The object type to Paste tags to.", values=dataTypes, default="Dataset"),

    scripts.List("Paste_To_IDs", grouping="4.2",
    description="IDs of Datasets or Images to Paste Tags to.").ofType(rlong(0)),
)

try:

    session = client.getSession()
    scriptParams = {}

    conn = BlitzGateway(client_obj=client)

    # process the list of args above. 
    for key in client.getInputKeys():
        if client.getInput(key):
            scriptParams[key] = client.getInput(key, unwrap=True)
    print scriptParams

    copyAndPasteTags(conn, scriptParams)

    client.setOutput("Message", rstring("Tagging DONE. See info for details"))

finally:
    client.closeSession()