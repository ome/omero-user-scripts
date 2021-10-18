# import the omero package and the omero.scripts package.
import omero
import omero.scripts as scripts
from omero.gateway import BlitzGateway, DatasetWrapper
from omero.rtypes import rlong, rstring, robject
import omero.util.script_utils as script_utils
import numpy as np
'''
Slow, but low memory usage
'''


def log(data):
    """Handle logging or printing in one place."""
    print(data)


def copyMetadata(conn, newImage, image):
    """
    Copy important metadata
    Reload to prevent update conflicts
    """
    newImage = conn.getObject("Image", newImage.getId())
    new_pixs = newImage.getPrimaryPixels()._obj
    old_pixs = image.getPrimaryPixels()._obj
    new_pixs.setPhysicalSizeX(old_pixs.getPhysicalSizeX())
    new_pixs.setPhysicalSizeY(old_pixs.getPhysicalSizeY())
    new_pixs.setPhysicalSizeZ(old_pixs.getPhysicalSizeZ())
    conn.getUpdateService().saveObject(new_pixs)
    for old_channels, new_channels in zip(image.getChannels(),
                                          newImage.getChannels()):
        new_LogicChan = new_channels._obj.getLogicalChannel()
        new_LogicChan.setName(rstring(old_channels.getLabel()))
        new_LogicChan.setEmissionWave(old_channels.getEmissionWave(units=True))
        new_LogicChan.setExcitationWave(
            old_channels.getExcitationWave(units=True))
        conn.getUpdateService().saveObject(new_LogicChan)

    if newImage._prepareRenderingEngine():
        newImage._re.resetDefaultSettings(True)


def getImages(conn, script_params):
    """
    Get the images
    """
    message = ""
    objects, log_message = script_utils.get_objects(conn, script_params)
    message += log_message
    if not objects:
        return None, message

    data_type = script_params["Data_Type"]

    if data_type == 'Dataset':
        images = []
        for ds in objects:
            images.extend(list(ds.listChildren()))
        if not images:
            message += "No image found in dataset(s)"
            return None, message
    else:
        images = objects
    return images


def getRoiShape(s):
    shape = {}
    shape['x'] = int(np.floor(s.getX().getValue()))
    shape['y'] = int(np.floor(s.getY().getValue()))
    shape['w'] = int(np.floor(s.getWidth().getValue()))
    shape['h'] = int(np.floor(s.getHeight().getValue()))
    return shape


def planeGenerator(new_Z, C, T, Z, pixels, projection, shape=None):
    """
    Set up generator of 2D numpy arrays, each of which is a MIP
    To be passed to createImage method so must be order z, c, t
    """
    for z in range(new_Z):  # createImageFromNumpySeq expects Z, C, T order
        for c in range(C):
            for t in range(T):
                for eachz in range(Z[0]-1, Z[1]):
                    plane = pixels.getPlane(eachz, c, t)
                    if shape is not None:
                        plane = plane[shape['y']:shape['y']+shape['h'],
                                      shape['x']:shape['x']+shape['w']]
                    if eachz == Z[0]-1:
                        new_plane = plane
                    else:
                        if projection == 'Maximum':
                            # Replace pixel values if larger
                            new_plane = np.where(np.greater(
                                plane, new_plane), plane, new_plane)
                        elif projection == 'Sum':
                            new_plane = np.add(plane, new_plane)
                        elif projection == 'Minimum':
                            new_plane = np.where(
                                np.less(plane, new_plane), plane, new_plane)
                        elif projection == 'Mean':
                            new_plane = np.mean(
                                np.array([plane, new_plane]), axis=0)
                yield new_plane


def runScript():
    dataTypes = [rstring('Dataset'), rstring('Image')]
    projections = [rstring('Maximum'), rstring('Sum'), rstring('Mean'),
                   rstring('Minimum')]
    client = scripts.client(
        "Intensity_Projection.py", """Creates a new image of the selected \
        intensity projection in Z from an existing image""",
        scripts.String(
            "Data_Type", optional=False, grouping="01", values=dataTypes,
            default="Image"),
        scripts.List(
            "IDs", optional=False, grouping="02",
            description="""IDs of the images to project""").ofType(rlong(0)),
        scripts.String(
            "Method", grouping="03",
            description="""Type of projection to run""", values=projections,
            default='Maximum'),
        scripts.Int(
            "First_Z", grouping="04", min=1,
            description="First Z plane to project, default is first plane"),
        scripts.Int(
            "Last_Z", grouping="05", min=1,
            description="Last Z plane to project, default is last plane"),
        scripts.Bool(
            "Apply_to_ROIs_only", grouping="06", default=False,
            description="Apply maximum projection only to rectangular ROIs, \
            if not rectangular ROIs found, image will be skipped"),
        scripts.String(
            "Dataset_Name", grouping="07",
            description="To save projections to new dataset, enter it's name. \
            To save projections to existing dataset, leave blank"),

        version="0.1",
        authors=["Laura Cooper", "CAMDU"],
        institutions=["University of Warwick"],
        contact="camdu@warwick.ac.uk"
        )
    try:
        conn = BlitzGateway(client_obj=client)
        script_params = client.getInputs(unwrap=True)
        images = getImages(conn, script_params)

        # Create new dataset if Dataset_Name is defined
        if "Dataset_Name" in script_params:
            new_dataset = DatasetWrapper(conn, omero.model.DatasetI())
            new_dataset.setName(script_params["Dataset_Name"])
            new_dataset.save()

        for image in images:
            # If Dataset_Name empty user existing, use new one if not.
            if "Dataset_Name" in script_params:
                dataset = new_dataset
            else:
                dataset = image.getParent()
            Z, C, T = image.getSizeZ(), image.getSizeC(), image.getSizeT()
            if "First_Z" in script_params:
                Z1 = [script_params["First_Z"], Z]
            else:
                Z1 = [1, Z]
            if "Last_Z" in script_params:
                Z1[1] = script_params["Last_Z"]
            # Skip image if Z dimension is 1 or if given Z range is less than 1
            if (Z != 1) or ((Z1[1]-Z1[0]) >= 1):
                # Get plane as numpy array
                pixels = image.getPrimaryPixels()
                if script_params["Apply_to_ROIs_only"]:
                    roi_service = conn.getRoiService()
                    result = roi_service.findByImage(image.getId(), None)
                    if result is not None:
                        for roi in result.rois:
                            for s in roi.copyShapes():
                                if type(s) == omero.model.RectangleI:
                                    shape = getRoiShape(s)
                                    name = "%s_%s_%s" % (image.getName(),
                                                         s.getId().getValue(),
                                                         script_params["Method"])
                                    desc = ("%s intensity Z projection of\
                                            Image ID: %s, shape ID: %s"
                                            % (script_params["Method"],
                                               image.getId(),
                                               s.getId().getValue()))
                else:
                    shape = {}
                    shape['x'] = 0
                    shape['y'] = 0
                    shape['w'] = image.getSizeX()
                    shape['h'] = image.getSizeY()
                    name = "%s_%s" % (
                        image.getName(), script_params["Method"])
                    desc = ("%s intensity Z projection of Image ID: \
                             %s" % (script_params["Method"],
                                    image.getId()))
                print(Z1)
                newImage = conn.createImageFromNumpySeq(
                    planeGenerator(1, C, T, Z1, pixels, script_params["Method"],
                                   shape), name, 1, C, T, description=desc, dataset=dataset)
                copyMetadata(conn, newImage, image)
                client.setOutput("New Image", robject(newImage._obj))

    finally:
        # Cleanup
        client.closeSession()


if __name__ == '__main__':
    runScript()
