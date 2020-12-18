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
    
    workspace = arcpy.GetParameterAsText(0)  
    inFacilities = arcpy.GetParameterAsText(1)     
    outShp = arcpy.GetParameterAsText(2)            
    inNetwork = arcpy.GetParameterAsText(3)         
    inMode = arcpy.GetParameterAsText(4)     
    inFromTo = arcpy.GetParameterAsText(5)  
    maxTravel = float(arcpy.GetParameterAsText(6))   


    # Create a list of all objectID
    def id_to_list(fc):
        res = []
        field = arcpy.ListFields(fc)[0].name
        features_enum = arcpy.SearchCursor(fc)
        for feature in features_enum:
            res.append(feature.getValue(field))

        return res 
    
    # Create service area polygon for given facilities from a network
    def service_area(fac_ids, output, facilities, sa_layer_obj, point_barriers = None):
        # SublyerNames
        sublayer_names = arcpy.na.GetNAClassNames(sa_layer_obj)                             
        sa_fac_lyr_name = sublayer_names["Facilities"]
        sa_barriers_lyr_name = sublayer_names["Barriers"]
        sa_polygons_lyr_name = sublayer_names["SAPolygons"]
        sa_polygons = sa_layer_obj.listLayers(sa_polygons_lyr_name)[0]    

        # Reset
        arcpy.Delete_management(output)
        arcpy.DeleteFeatures_management(sa_fac_lyr_name)
        arcpy.DeleteFeatures_management(sa_barriers_lyr_name)      

        # Load facilities.
        
        field_name = arcpy.ListFields(facilities)[0].name
        arcpy.SelectLayerByAttribute_management(facilities, "NEW_SELECTION", 
                                    field_name + " IN (" + str(fac_ids)[1:-1] + ")")    
        arcpy.na.AddLocations(sa_layer_obj, sa_fac_lyr_name, facilities)

        # Load barriers.
        if point_barriers is not None:
            arcpy.na.AddLocations(sa_layer_obj, sa_barriers_lyr_name, point_barriers)

        # Solve service area
        arcpy.na.Solve(sa_layer_obj)
        
        # Copy service area to output feature class
        arcpy.CopyFeatures_management(sa_polygons, output)      


    # Create boundary points between target point and other points, 
    # such that for each boundary points the impedence to target point 
    # and closest point is equal.
    def create_boundary_points(target_id, others_id_list, output,
                            points_layer, cf_layer_Obj,  
                            reset_barriers = False,         
                            point_barriers = None):
        # Sublayer names
        sublayer_names = arcpy.na.GetNAClassNames(cf_layer_Obj)
        cfFacilities_lyr_name = sublayer_names["Facilities"]
        cfIncidents_lyr_name = sublayer_names["Incidents"]    
        cfBarriers_lyr_name = sublayer_names["Barriers"]

        # Reset
        arcpy.DeleteFeatures_management(cfFacilities_lyr_name)
        arcpy.DeleteFeatures_management(cfIncidents_lyr_name)
        if reset_barriers:
            arcpy.DeleteFeatures_management(cfBarriers_lyr_name)

        # Load facilities 
        field_name = arcpy.ListFields(points_layer)[0].name
        arcpy.SelectLayerByAttribute_management(points_layer, "NEW_SELECTION", 
                            field_name + " IN (" + str(others_id_list)[1:-1] + ")" )        
        arcpy.na.AddLocations(cf_layer_Obj, cfFacilities_lyr_name, points_layer)
        
        # Load incidents
        arcpy.SelectLayerByAttribute_management(points_layer, "NEW_SELECTION", 
                                field_name + " = " + str(target_id))         
        arcpy.na.AddLocations(cf_layer_Obj, cfIncidents_lyr_name, points_layer)

        # Load polygon barriers
        if point_barriers is not None:
            arcpy.na.AddLocations(cf_layer_Obj, cfBarriers_lyr_name, point_barriers)
        
        mid_point = "mid_point"
        
        # For each loop, find route to closest facility with previous mid_points 
        # as barriers, add new mid_point to barriers. Stop until can't find new route.
        while True:
            # Slove route to the closest facility
            try: arcpy.na.Solve(cf_layer_Obj) 
            except: break

            # Find mid_point of new route
            route = arcpy.SearchCursor(cf_layer_Obj.listLayers()[3]).next()
            new_mid_point = arcpy.PointGeometry(
                route.Shape.positionAlongLine(0.50,True).firstPoint)
            new_mid_point = route.Shape.queryPointAndDistance(new_mid_point)[0]

            # Copy new_mid_point geometry to mid_point feature class
            arcpy.CopyFeatures_management(new_mid_point, mid_point)

            # Add mid point as barrier
            arcpy.na.AddLocations(cf_layer_Obj, cfBarriers_lyr_name, mid_point)
        
        del route
        # Copy barriers layer as boundary points to outputFC
        arcpy.CopyFeatures_management(cf_layer_Obj.listLayers()[2], output)



    def dist_based_nt_partitioning(facilities, st_network, output, 
                            mode = "Driving Time",
                            direction = "FROM_FACILITIES",
                            max_cost = 1000000):
        
        # Check out Network Analyst license if available. 
        # Fail if the Network Analyst license is not available.
        if arcpy.CheckExtension("network") == "Available":
            arcpy.CheckOutExtension("network")
        else:
            raise arcpy.ExecuteError("Network Analyst Extension license is not available.") 

        # Initialize
        arcpy.AddMessage(" ... initializing names")
        partitions = "Partitions"
        fac_layer = "FacilitiesLayer"    
        boundary_points  = "boundary_points"

        arcpy.MakeFeatureLayer_management(facilities, fac_layer)
        idfield_name   = arcpy.ListFields(fac_layer)[0].name    

        # Create a new closest facility analysis layer.
        arcpy.AddMessage(" ... initializing closest facility analysis")
        cf_lyr_obj = arcpy.na.MakeClosestFacilityAnalysisLayer(
                                        st_network, "Closest_Facility",
                                        mode, direction, 
                                        number_of_facilities_to_find = 1).getOutput(0)

        # Create a list of all facilities' ID for loop through
        all_ids = id_to_list(fac_layer)
        # Create a list of remain facilities' ID
        remain_ids = all_ids.copy()

        arcpy.AddMessage(" ... starting network partitioning")
        
        # For each loop, find all boundary points for current facility
        # and add them to boundary_points    
        for current_id in all_ids:
            if current_id == all_ids[-1]: break    # skip the last facility
            arcpy.AddMessage(" ...... solving partition of facility: " + str(current_id))
            remain_ids.remove(current_id)   # remove current_id from remain_ids list 
            
            # Create boundary points for current facility and add them to boundary_points
            create_boundary_points(current_id, remain_ids, boundary_points,
                                fac_layer, cf_lyr_obj)


        # Create a new service area analysis layer
        arcpy.AddMessage(" ... initializing service area analysis")
        sa_lyr_obj = arcpy.na.MakeServiceAreaAnalysisLayer(
                                st_network, "Service_Area", mode, 
                                direction, [max_cost],
                                geometry_at_overlaps = "SPLIT").getOutput(0)

        # Solve partitions for all facilities with boundary point
        # from previous step as barriers
        service_area(all_ids, output, fac_layer, 
                     sa_lyr_obj, point_barriers = boundary_points)
        # Join the facilities information back to partitions and create output file.
        arcpy.SpatialJoin_analysis(partitions, fac_layer,
                                   os.path.join(workspace, output))
        try: 
            arcpy.Delete_management(partitions)
            arcpy.Delete_management(fac_layer)
            arcpy.Delete_management(boundary_points)
        except: pass

    arcpy.env.workspace = workspace

    dist_based_nt_partitioning(inFacilities, inNetwork, outShp,
                        inMode, inFromTo, maxTravel)

except Exception as e:
    # If unsuccessful, end gracefully by indicating why
    arcpy.AddError('\n' + "Script failed because: \t\t" + e.args[0] )
    # ... and where
    exceptionreport = sys.exc_info()[2]
    fullermessage   = traceback.format_tb(exceptionreport)[0]
    arcpy.AddError("at this location: \n\n" + fullermessage + "\n")


