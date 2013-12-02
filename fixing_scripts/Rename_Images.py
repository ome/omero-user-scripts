#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This replaces names for each selected image.

@author Pierre Pouchin
<a href="mailto:pierre.pouchin@u-clermont1.fr">pierre.pouchin@u-clermont1.fr</a>
@version 4.3
"""

import omero
import omero.scripts as scripts
from omero.gateway import BlitzGateway
from omero.rtypes import *

PARAM_SEARCH = "Search"
PARAM_REPLACEBY = "Replace_by"
PARAM_DATATYPE = "Data_Type"
PARAM_IDS = "IDs"
PARAM_ALL_IMAGES = "All_Images"

# Global dictionary of original file IDs
original_ids = {}

################################################################################

def run(conn, params):
    """
    For each image defined in the script parameters change the name
    
    @param conn:   The BlitzGateway connection
    @param params: The script parameters
    """
    print "Parameters = %s" % params
    
    images = []
    if params[PARAM_ALL_IMAGES]:
      images = list(conn.getObjects('Image'))
    else:
      objects = conn.getObjects(params[PARAM_DATATYPE], params[PARAM_IDS])
      if params[PARAM_DATATYPE] == 'Dataset':
        for ds in objects:
          images.extend( list(ds.listChildren()) )
      else:
        images = list(objects)
            
      # Remove duplicate images in multiple datasets
      seen = set()
      images = [x for x in images if x.id not in seen and not seen.add(x.id)]

    # Remove images which are not writable for the user
    images = [x for x in images if x.canWrite()]
        
    print("Processing %s image%s" % (
      len(images), len(images) != 1 and 's' or ''))
     
    count = 0 
    for img in images:
      if (img != None):
        oldname = img.getName()
        newname = oldname.replace(params[PARAM_SEARCH],params[PARAM_REPLACEBY])
        if (newname != oldname) :
          img.setName(rstring(newname))
          img.save()
          count += 1
    
    return (count)

def summary(count):
    """Produce a summary message of the number of image(s) renamed"""
    msg = "%d image%s processed" % (count, count != 1 and 's' or '')
    return msg

def run_as_script():
    """
    The main entry point of the script, as called by the client via the 
    scripting service, passing the required parameters. 
    """
    dataTypes = [rstring('Dataset'),rstring('Image')]
    
    client = scripts.client('Rename_Images.py', """\
Replace the specified string in the selected images names.
""", 
    
    scripts.String(PARAM_DATATYPE, optional=False, grouping="1.1",
        description="The data you want to work with.", values=dataTypes, 
        default="Image"),

    scripts.List(PARAM_IDS, optional=True, grouping="1.2",
        description="List of Dataset IDs or Image IDs").ofType(rlong(0)),

    scripts.Bool(PARAM_ALL_IMAGES, grouping="1.3", 
        description="Process all images (ignore the ID parameters)", 
        default=False),

    scripts.String(PARAM_SEARCH, optional=False, grouping="2",
        description="The character string you want to change.",
        default="/data/OMERO/DropBox/"),

    scripts.String(PARAM_REPLACEBY, optional=True, grouping="3",
        description="The character string that will replace the previous value.",
        default=""),

    version = "1.0",
    authors = ["Pierre Pouchin", "GReD"],
    institutions = ["Universite d'Auvergne"],
    contact = "pierre.pouchin@u-clermont1.fr",
    ) 
    
    conn = BlitzGateway(client_obj=client)
    
    # Process the list of args above. 
    params = {}
    for key in client.getInputKeys():
      if client.getInput(key):
        params[key] = client.getInput(key, unwrap=True)
    
    # Call the main script - returns the number of images and total bytes
    count = run(conn, params)
    
    if count >= 0:
      # Combine the totals for the summary message
      msg = summary(count)
      print msg
      client.setOutput("Message", rstring(msg))

    client.closeSession()


if __name__ == "__main__":
    """
    Python entry point
    """
    run_as_script()
    
