#!/usr/bin/env python
# -*- coding: utf-8 -*-

#
# Copyright (C) 2011 University of Dundee & Open Microscopy Environment.
#                    All Rights Reserved.
# Use is subject to license terms supplied in LICENSE.txt
#

"""
FOR TRAINING PURPOSES ONLY!
"""

from omero.gateway import BlitzGateway
from omero.rtypes import *
from Connect_To_OMERO import USERNAME, PASSWORD, HOST, PORT


# Create a connection
# =================================================================
conn = BlitzGateway(USERNAME, PASSWORD, host=HOST, port=PORT)
conn.connect()


# Configuration
# =================================================================
dataset_name = "MyDataset"
tag_name = "MyTag"


# Create Datasets
# =================================================================
object_array = list()
for i in xrange(3):
    dataset = omero.model.DatasetI()
    dataset.setName(rstring(dataset_name))
    object_array.append(dataset)
conn.getUpdateService().saveArray(object_array)


# Create Tags
# =================================================================
object_array = list()
for i in xrange(3):
    tag = omero.model.TagAnnotationI()
    tag.setTextValue(rstring(tag_name))
    tag.setDescription(rstring("%s %i" % (tag_name, i)))
    object_array.append(tag)
conn.getUpdateService().saveArray(object_array)


# Find the datasets by name.
# =================================================================
datasets = conn.getObjects("Dataset", attributes={'name': dataset_name})
print "\nList Datasets:"
for d in datasets:
    print "ID:", d.getId(), "Name:", d.getName()


# Find the tag by textValue
# =================================================================
Tags = conn.getObjects("TagAnnotation", attributes={'textValue': tag_name})
print "\nList Tags:"
for t in Tags:
    print "ID:", t.getId(), "Text:", t.getTextValue(), "Desc:", t.getDescription()


# Close connection:
# =================================================================
# When you're done, close the session to free up server resources.
conn._closeSession()
