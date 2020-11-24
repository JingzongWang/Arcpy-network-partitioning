"""
This script creates a new shapefile or feature class of service areas 
for given facilities from a street network. These areas are sized based on 
proximity or other cost to facilities in the network.
"""

# Import necessary modules
import sys, os, string, math, arcpy, traceback

# Allow output file to overwrite any existing file of the same name
arcpy.env.overwriteOutput = True

try:
    # Read user input    
    arcpy.AddMessage(" ... reading user input")
    
    workspace       = arcpy.GetParameterAsText(0)    # type = folder; direction = Input    
    inputFacilities = arcpy.GetParameterAsText(1)    # type = Shapefile or Layer; direction = Input; Feature type = Point   
    outShp          = arcpy.GetParameterAsText(2)    # type = Shapefile or feature class; direction = Output            
    network         = arcpy.GetParameterAsText(3)    # type = Network; direction = Input          
    travelMode      = arcpy.GetParameterAsText(4)    # type = Network Travel Mode; direction = Input; default = "Driving Time"    
    travelFromTo    = arcpy.GetParameterAsText(5)    # type = Text; direction = Input; value list = ["FROM_FACILITIES", "TO_FACILITIES"]; default = "FROM_FACILITIES"
    maxTravel       = float(arcpy.GetParameterAsText(6))  # type = Double; direction = Input; default = 1000000   


    # Create a list of all objectID
    def objectIDToList(featureClass, fieldName):
        res = []
        featuresEnum = arcpy.SearchCursor(featureClass)
        for feature in featuresEnum:
            res.append(feature.getValue(fieldName))

        return res 
    
    # Create service area polygon for given facilities from a network
    def serviceArea(facilityIDs, outputFC, facilities, 
                    fieldName, saLayerObj, pointBarriers = None):
        # SublyerNames
        sublayerNames = arcpy.na.GetNAClassNames(saLayerObj)                             
        saFacLyrName = sublayerNames["Facilities"]
        saBarriersLyrName = sublayerNames["Barriers"]
        saPolygonsLyrName = sublayerNames["SAPolygons"]
        saPolygons = serviceAreaLyrObj.listLayers(saPolygonsLyrName)[0]    

        # Reset
        arcpy.Delete_management(outputFC)
        arcpy.DeleteFeatures_management(saFacLyrName)
        arcpy.DeleteFeatures_management(v)      

        # Load facilities.
        arcpy.SelectLayerByAttribute_management(facilities, 
                                    "NEW_SELECTION", 
                                    fieldName + " IN (" + str(facilityIDs)[1:-1] + ")")    
        arcpy.na.AddLocations(saLayerObj, saFacLyrName, facilities)

        # Load barriers.
        if pointBarriers is not None:
            arcpy.na.AddLocations(saLayerObj, saBarriersLyrName, pointBarriers)

        # Solve service area
        arcpy.na.Solve(saLayerObj)
        
        # Copy service area to output feature class
        arcpy.CopyFeatures_management(saPolygons, outputFC)      

        return

    # Create boundary points between target point and other points, 
    # such that for each boundary points the impedence to target point 
    # and closest point is equal.
    def creatBoundaryPoints(targetID, othersIDList, output,
                            pointsLayer,  fieldName,  cfLayerObj,  
                            resetBarriers = False,         
                            pointBarriers = None):
        # Sublayer names
        sublayerNames = arcpy.na.GetNAClassNames(cfLayerObj)
        cfFacilitiesLyrName = sublayerNames["Facilities"]
        cfIncidentsLyrName = sublayerNames["Incidents"]    
        cfBarriersLyrName = sublayerNames["Barriers"]

        # Reset
        arcpy.DeleteFeatures_management(cfFacilitiesLyrName)
        arcpy.DeleteFeatures_management(cfIncidentsLyrName)
        if resetBarriers:
            arcpy.DeleteFeatures_management(cfBarriersLyrName)

        # Load facilities 
        arcpy.SelectLayerByAttribute_management(pointsLayer, "NEW_SELECTION", 
                            fieldName + " IN (" + str(othersIDList)[1:-1] + ")" )        
        arcpy.na.AddLocations(cfLayerObj, cfFacilitiesLyrName, pointsLayer)
        
        # Load incidents
        arcpy.SelectLayerByAttribute_management(pointsLayer, "NEW_SELECTION", 
                                fieldName + " = " + str(targetID))         
        arcpy.na.AddLocations(cfLayerObj, cfIncidentsLyrName, pointsLayer)

        # Load polygon barriers
        if pointBarriers is not None:
            arcpy.na.AddLocations(cfLayerObj, cfBarriersLyrName, pointBarriers)
        
        midPoint = "midPoint"
        
        # For each loop, find route to closest facility with previous midpoints 
        # as barriers, add new midpoint to barriers. Stop until can't find new route.
        while True:
            # Slove route to the closest facility
            try: arcpy.na.Solve(cfLayerObj) 
            except: break

            # Find midPoint of new route
            route = arcpy.SearchCursor(cfLayerObj.listLayers()[3]).next()
            newMidPoint = arcpy.PointGeometry(
                route.Shape.positionAlongLine(0.50,True).firstPoint)
            newMidPoint = route.Shape.queryPointAndDistance(newMidPoint)[0]

            # Copy newMidPoint geometry to midPoint feature class
            arcpy.CopyFeatures_management(newMidPoint, midPoint)

            # Add mid point as barrier
            arcpy.na.AddLocations(cfLayerObj, cfBarriersLyrName, midPoint)
        
        del route
        # Copy barriers layer as boundary points to outputFC
        arcpy.CopyFeatures_management(cfLayerObj.listLayers()[2], output)

        return


    def networkPartitioning(facilities, stNetwork, output, 
                            mode = "Driving Time",
                            fromTo = "FROM_FACILITIES",
                            maxCost = 1000000,
                            deleteProcess = True):
        
        # Check out Network Analyst license if available. 
        # Fail if the Network Analyst license is not available.
        if arcpy.CheckExtension("network") == "Available":
            arcpy.CheckOutExtension("network")
        else:
            raise arcpy.ExecuteError("Network Analyst Extension license is not available.") 

        # Initialize
        arcpy.AddMessage(" ... initializing names")
        partitions = "Partitions"
        facLayer = "FacilitiesLayer"    
        boundaryPoints  = "BoundaryPoints"

        arcpy.MakeFeatureLayer_management(facilities, facLayer)
        idFieldName   = arcpy.ListFields(facLayer)[0].name    

        # Initialize network analysis
        # Create a new closest facility analysis layer.
        arcpy.AddMessage(" ... initializing closest facility analysis")
        closestFacLyrObj = arcpy.na.MakeClosestFacilityAnalysisLayer(
                                        stNetwork, "Closest_Facility",
                                        mode, fromTo, 
                                        number_of_facilities_to_find = 1).getOutput(0)

        # Create a new service area analysis layer
        arcpy.AddMessage(" ... initializing service area analysis")
        serviceAreaLyrObj = arcpy.na.MakeServiceAreaAnalysisLayer(
                                stNetwork, "Service_Area", mode, 
                                fromTo, [maxCost],
                                geometry_at_overlaps = "SPLIT").getOutput(0)


        # Create a list of all facilities' ID for loop through
        allIDs = objectIDToList(facLayer)
        # Create a list of remain facilities' ID
        remainIDs = allIDs.copy()

        arcpy.AddMessage(" ... starting network partitioning")
        
        # For each loop, find all boundary points for current facility
        # and add them to boundaryPoints    
        for currentID in allIDs:
            if currentID == allIDs[-1]: break    # skip the last facility
            arcpy.AddMessage(" ...... solving partition of facility: " + str(currentID))
            remainIDs.remove(currentID)   # remove currentID from remainIDs list 
            
            # Create boundary points for current facility and add them to boundaryPoints
            creatBoundaryPoints(currentID, remainIDs, boundaryPoints,
                                facLayer,  idFieldName, closestFacLyrObj)
        # Solve partitions for all facilities with boundary point
        # from previous step as barriers
        serviceArea(facilityIDs, outputFC, facLayer, 
                    idFieldName, serviceAreaLyrObj, pointBarriers = boundaryPoints)
        # Join the facilities information back to partitions and create output file.
        arcpy.SpatialJoin_analysis(partitions, facLayer,
                                   os.path.join(workspace, outShp))
        if deleteProcess:
            arcpy.Delete_management([partitions, facLayer, boundaryPoints, 
                                     closestFacLyrObj, serviceAreaLyrObj])
        return

    arcpy.env.workspace = workspace

    networkPartitioning(inputFacilities, network, outShp,
                        travelMode, travelFromTo, maxTravel)

except Exception as e:
    # If unsuccessful, end gracefully by indicating why
    arcpy.AddError('\n' + "Script failed because: \t\t" + e.args[0] )
    # ... and where
    exceptionreport = sys.exc_info()[2]
    fullermessage   = traceback.format_tb(exceptionreport)[0]
    arcpy.AddError("at this location: \n\n" + fullermessage + "\n")


