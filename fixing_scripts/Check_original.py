#!/usr/bin/python
# -*- coding: utf-8 -*-
"""
This script checks if all files in DropBox have been imported.

@author Pierre Pouchin
<a href="mailto:pierre.pouchin@u-clermont1.fr">pierre.pouchin@u-clermont1.fr</a>
@version 4.3
"""

import omero
import omero.cli
import omero.scripts as scripts
from omero.gateway import BlitzGateway
from omero.rtypes import *

import os
import shlex

# Global dictionary of original file IDs
original_ids = {}
PARAM_GRP_USERS = "Group_Users"

################################################################################

#def importfile(conn, imgfile):
#    cli = omero.cli.CLI()
#    cli.loadplugins()
#    key = conn._getSessionId()
#    cmd = ["-s", conn.host, "-p", str(conn.port), "-k", key, "import"]
#    ## To re-direct output to a file
#    ## cmd.extend([str("---errs=%s"%t), str("---file=%s"%to)])
##    cmd.extend(shlex.split(self.importArgs))
#    cmd.append(imgfile)
#    print "cli.invoke(%s)", cmd
#    cli.invoke(cmd)
#    retCode = cli.rv
#
#    if retCode == 0:
#      print "Import of %s completed (session=%s)", filename, key
#    else:
#      print "Import of %s failed=%s (session=%s)", fileName, str(retCode), key


def run(conn, params):
    """
    For each image defined in the script parameters change the name
    
    @param conn:   The BlitzGateway connection
    @param params: The script parameters
    """
#    print "Parameters = %s" % params

    count = 0

    usernames = []
    if params[PARAM_GRP_USERS]:
      users = conn.listColleagues() #list(conn.getObjects('Experimenter'))
      for user in users:
        usernames.append(user.getName())
    else:
      usernames.append(conn.getUser().getName())
    
    for username in usernames:
      # Print username
      print "# User: %s" % username

      # Get images
      images = list(conn.getObjects('Image'))
      
      # Remove images which are not owned by the user
      images = [x for x in images if x.getOwner().getName() == username]

      n = len(images)
      print("# %s image%s" % (n, len(images) != 1 and 's' or ''))

      dropdir = "/data/OMERO/DropBox/"
      userdir = dropdir.encode("utf8") + username.encode("utf8")
      tmpdir = "/data"

      for folder, dirs, files in os.walk(userdir):
        for filename in files:
          #print "## File: %s" % filename
          i = 0
#          if not (filename.startswith(".") or filename.endswith(".log")
#                  or filename.endswith(".txt") or filename.endswith(".csv")
#                  or filename.endswith(".xls") or filename.endswith(".doc")
#                  or filename.endswith(".lst") or filename.endswith(".tmp")
#                  or filename.endswith(".ini") or filename.endswith(".mdb")):
          if (filename.endswith(".lif") or filename.endswith(".lsm") 
              or filename.endswith(".tif") or filename.endswith(".ims")
              or filename.endswith(".tiff")):
            fName, fExt = os.path.splitext(filename)
            unifName = unicode(fName,"utf8")
            count += 1
            for img in images:
              i += 1
              name = unicode(img.getName(),"utf8")
            
              if name.startswith(dropdir):
                if name.startswith(userdir):
                  name = name.replace(userdir,"")
                else:
                  break
              
              if name.find(unifName)!=-1:
                count -= 1
                break

          if i == n:
            imgfile = os.path.join(folder, filename)
            print "mv %s %s && mv %s/%s %s" % (imgfile.replace(" ","\ "),tmpdir,tmpdir,filename.replace(" ","\ "),folder.replace(" ","\ "))
#            importfile(conn, imgfile)
 
    return (count)

def summary(count):
    """Produce a summary message of the number of file(s) moved"""
    msg = "%d file%s missing" % (count, count != 1 and 's' or '')
    return msg

def run_as_script():
    """
    The main entry point of the script, as called by the client via the 
    scripting service, passing the required parameters. 
    """

    client = scripts.client('Check_original.py', """\
    Check if the images were correctly imported.
    """, 

    scripts.Bool(PARAM_GRP_USERS, grouping="1",
        description="Process all users in group"),

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
      print "# %s" % msg
      client.setOutput("Message", rstring(msg))

    client.closeSession()


if __name__ == "__main__":
    """
    Python entry point
    """
    run_as_script()
    
