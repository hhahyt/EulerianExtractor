""" 
This script post-processes an Abaqus Odb file and extracts the time 
history of a field output of a body at some fixed spattial location, 
or in mechanics people's word, the Eulerian result of body at one 
spatial location. 

The script creates a very short point-type path that passes the 
spatial location of interest and uses the built-in method of plotting
field output along path to extract the output value at the location. 
The extraction process is repeated for every frame so a time history 
of field output at that spatial location is obtained. A typical Abaqus 
XYData object containing those data is created and plotted after running
this script. Exporting those data to Excel or modifying plot styels can 
be done with the same Abaqus/CAE operations. 
 
author: Yao Ren
website: http://yaor.me
license: MIT 
 
Please feel free to adapt this script to your need. But the author would
really appreciate if you keep the above information. Thanks. 
"""
# Define the odb file name, please include .odb extension at the end.
# Type: string
odbName = '2RR_T1-1000_T2-500_N20-FullIntg.odb'

# Define (x, y, z) coordinates of a spatial location of interest. The
# result of interest of body (defined below) at this spatical location
# will be extracted. 
# Type: tupe of floats
poi = (-1, 0, 0)

# Define the field output name of interest, should not include component.
# Type: string
fieldVarName = 'S'
# Define the component of the vector or tensor type field ouptut, 
# Type: string
# pick one of the below and enclose it with ''
# possible component values for vectors: 1, 2, 3
# possible component values for tensors: 11, 22, 33, 12, 13, 23
# possible invaraint values: Magnitude, Mises, Tresca, Pressure, 
# Third Invariant, Max. Principal, Mid. Principal, Min. Principal, 
# Max. In-Plane Principal, Min. In-Plane Principal, Out-of-Plane Principal
fieldVarComponent = '11'   

# A tolerence that controls the length of the very short path in extracting
# field output value as discussed above. Change this tolerence to make sure
# the path is inside (for solid elements) or pass through (for structural 
# elements)the material body whose field output is to be extracted. 
tol = 1e-5
# End of input

import numpy as np
from random import randint
from odbAccess import *
import visualization
from abaqusConstants import *

odb = openOdb(path=odbName, readOnly=True)
stepRepo = odb.steps

def createPath(poi):
    """ creates a very short path with the poi as middle point
        
        poi: a tuple of 3 float coordinates x, y, z
        return: an Abaqus point-type path
    """
    step = stepRepo[stepRepo.keys()[-1]]
    if len(step.frames[0].fieldOutputs['U'].values[0].data) == 2:
        firstPoint = (poi[0]-tol, poi[1]-tol, poi[2])
        secondPoint = (poi[0]+tol, poi[1]+tol, poi[2])
    else:
        firstPoint = (poi[0]-tol, poi[1]-tol, poi[2]-tol)
        secondPoint = (poi[0]+tol, poi[1]+tol, poi[2]+tol)
    twoEndPointsList = (firstPoint, secondPoint)
    pathPoi = session.Path(name='PathCoverPoi', type=POINT_LIST,
                           expression=twoEndPointsList)
    return pathPoi

def getVarValue(stepInt, frameInt):
    """ averages the data value of XYData created by plot along path
    method
        
        stepInt: an integer indicates step
        frameInt: an integer indicates frame
        return: a float number
    """
    try:
        pathData = session.XYDataFromPath(
                                  path=path, name='tmpPathData',
                                  includeIntersections=includeIntersections,
                                  shape=DEFORMED,
                                  pathStyle=PATH_POINTS,
                                  numIntervals=1,
                                  labelType=TRUE_DISTANCE,
                                  step=stepInt,
                                  frame=frameInt)
    except:
        print ''.join(('Failed to extract data using Path from spatial ',
                        'location in step:', str(stepInt), ' frame: ', 
                        str(frameInt)))
        return
    yDataList = [x[1] for x in pathData.data]
    averageData = sum(yDataList)/float(len(yDataList))
    del session.xyDataObjects['tmpPathData']
    return averageData

def createXYDataObj(xySequence, xyDataName):
    """ creates XYData object with extracted time history of field output
        
        xySequence: a tuple of (frame, field output)
        xyDataName: name of XYData
        return: a newly create XYData if no existed or an old XYData
    """
    if xyDataName not in session.xyDataObjects.keys():
        resXYData = session.XYData(data=xySequence, name=xyDataName)
    else:
        session.xyDataObjects[xyDataName].setValues(data=xySequence)
        resXYData = session.xyDataObjects[xyDataName]
    return resXYData

def intString(s):
    """ check if the string s represents a number for components of field
        output
        
        s: a string
        return: True if s represents a component number
                False if s represents invariants
    """
    try: 
        int(s)
        return True
    except ValueError:
        return False
    return None

def plotData(spatialXYData, fieldVarName, fieldVarComponent):
    """ plot data in Abaqus/Visualization
    
        spatialXYData: XYData containing results at spatial location
        xyDataName: plot name
    """
    xyPlotName = xyDataName.replace('.', '')
    if xyPlotName not in session.xyPlots.keys():
        xyPlot = session.XYPlot(xyPlotName)
    else:
        xyPlot = session.xyPlots[xyPlotName]
    chartName = session.xyPlots[xyPlotName].charts.keys()[0]
    chart = xyPlot.charts[chartName]
    curve = session.Curve(spatialXYData)
    chart.setValues(curvesToPlot=(curve,))
    
    # set title
    if intString(fieldVarComponent):
        variableName = ''.join((fieldVarName, fieldVarComponent))
    else:
        variableName = ''.join((fieldVarName, '-', fieldVarComponent))
    poiStr = ''.join(('(', str(poi[0]), ', ', str(poi[1]), ', ', str(poi[2]), ')'))
    xyPlot.title.setValues(text=''.join((variableName, ' @ ', poiStr)))
    
    # set axes
    chart.axes1[0].axisData.setValues(title='Time')
    chart.axes2[0].axisData.setValues(title=variableName)
    session.viewports['Viewport: 1'].setValues(displayedObject=xyPlot)
    return None

viewportKey = session.viewports.keys()[0]       # current viewport
session.viewports[viewportKey].setValues(displayedObject=odb)
xySeq = ()
fieldOutputInOdb = False    # flag if output field is not in every step
for stepKey in stepRepo.keys():
    step = stepRepo[stepKey]
    if fieldVarName not in step.frames[-1].fieldOutputs.keys():
        print ''.join(('Requested ', fieldVarName, ' is not available in step ',
                        stepKey, ' . Step time skipped.'))
        continue
    else:
        fieldOutputInOdb = True
    
    path = createPath(poi)
    variablePosition = step.frames[-1].fieldOutputs[fieldVarName].locations[0].position
    includeIntersections = True 
    
    if intString(fieldVarComponent):
        refinement = (COMPONENT, ''.join((fieldVarName, fieldVarComponent)))
    else:
        refinement = (INVARIANT, fieldVarComponent)
    xyDataName = ''.join((fieldVarName, fieldVarComponent))
    
    
    stepInt = stepRepo.keys().index(step.name)
    frameInt = 0
    stepFrameNum = len(step.frames) - 1
    session.viewports['Viewport: 1'].odbDisplay.setPrimaryVariable(
                    variableLabel=fieldVarName, 
                    outputPosition=variablePosition, 
                    refinement=refinement,)
    for frame in step.frames:
        dataPoints = []
        time = step.totalTime + frame.frameValue
        print ''.join((stepKey, ': ', str(frameInt), '/', str(stepFrameNum)))
        dataPoints.append(time)
        output = getVarValue(stepInt, frameInt)
        frameInt += 1
        if output is None:
            continue
        dataPoints.append(output)
        xySeq += (tuple(dataPoints),)
    spatialXYData = createXYDataObj(xySequence=xySeq, xyDataName=xyDataName)
    plotData(spatialXYData, fieldVarName, fieldVarComponent)

if not fieldOutputInOdb:
    print ''.join((fieldVarName, ' is not a valid field output for this Odb.'))

