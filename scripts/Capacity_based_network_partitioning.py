# This tool creates a new shapefile of service areas for given facilities from a street network. 
# These areas are sized based on each facility's capacity and areas' burden, 
# as well as the proximity to facilities in the network.

# Import necessary modules
import sys, os, string, math, arcpy, traceback, heapq
from collections import Counter
# Allow output file to overwrite any existing file of the same name
arcpy.env.overwriteOutput = True

try:
    # Read user input    
    arcpy.AddMessage(" ... reading user input")

    workspace = arcpy.GetParameterAsText(0)   
    outShp = arcpy.GetParameterAsText(1)
    inZones = arcpy.GetParameterAsText(2) 
    inBurdenField = arcpy.GetParameterAsText(3)
    inFacilities = arcpy.GetParameterAsText(4)
    inCapacityField = arcpy.GetParameterAsText(5)
    inStreets = arcpy.GetParameterAsText(6)         
    inCellSize = float(arcpy.GetParameterAsText(7))
    inNetwork = arcpy.GetParameterAsText(8)            
    inMode = arcpy.GetParameterAsText(9)     
    inDirection = arcpy.GetParameterAsText(10)   
    if arcpy.GetParameterAsText(11):
        inNumToFind = int(arcpy.GetParameterAsText(11))
    else: inNumToFind = None

    for i in range(0, 12):
        arcpy.AddMessage(arcpy.GetParameterAsText(i))

    # Sum up a column.
    def sum_col(fc, field_name):
        total = 0
        with arcpy.da.SearchCursor(fc, [field_name]) as search_rows:
            for row in search_rows:
                total += row[0]
        return total

    # Distribute zones' burden to facilities.    
    def distr_burden(points, burden_field, facilities, capacity_field):
        total_burden = sum_col(points, burden_field)
        total_capacity = sum_col(facilities, capacity_field)
        ratio = total_burden / total_capacity

        arcpy.AddField_management(facilities, 'Burden', 'DOUBLE')
        with arcpy.da.UpdateCursor(facilities, [capacity_field, 'Burden']) as update_rows:
            for row in update_rows:
                row[1] = row[0] * ratio 
                update_rows.updateRow(row)

    # Distribute zones' burden to fishnet cells.
    def distribute_value(fc, ID, valueFieldName):
        #Add the count field
        arcpy.AddField_management(fc, 'VALUE', 'DOUBLE')

        #Do the counting:
        value_list = []
        with arcpy.da.SearchCursor(fc, [ID]) as search_rows:
            for row in search_rows:
                value_list.append(row[0])

        counts = Counter(value_list)
        del value_list
        
        with arcpy.da.UpdateCursor(fc, [ID, valueFieldName, 'VALUE']) as update_rows:
            for row in update_rows:
                row[2] = row[1] / counts[row[0]]
                update_rows.updateRow(row)

    # Create fishnet cells from input zones.           
    def create_fishnet(polygon, polyline, output_points, output_fishnet, size, valueField):
        arcpy.AddMessage("...creating fishnet from polygon.")
        # Create fishnet.
        desc = arcpy.Describe(polygon)
        temp_fishnet = "temp_fishnet"
        temp_points = "temp_points"
        arcpy.CreateFishnet_management(temp_fishnet,
            str(desc.extent.lowerLeft),
            str(desc.extent.XMin) + " " + str(desc.extent.YMax), 
            size, size, "0","0", 
            str(desc.extent.upperRight),"", polygon,
            geometry_type = 'POLYGON')
        
        # Select points near streets.
        nearStreet = arcpy.SelectLayerByLocation_management(
            temp_fishnet + '_label', 'WITHIN_A_DISTANCE',
            polyline, '200 Meters')

        # Intersect with polygon
        arcpy.Intersect_analysis([nearStreet, polygon], output_points)
        
        
        selected = arcpy.SelectLayerByLocation_management(temp_fishnet, 'INTERSECT',
                                               output_points)         
        
        arcpy.CopyFeatures_management(selected, output_fishnet)

        arcpy.Delete_management(selected)    
        arcpy.Delete_management(temp_fishnet) 
        arcpy.Delete_management(temp_fishnet  + '_label')
        arcpy.Delete_management(temp_points) 
        
        # Distribute value from each polygon to points
        distribute_value(output_points, arcpy.ListFields(output_points)[3].name, valueField)
          
    # Calculate cost matrix from each fishnet cell to `num_to_find` closest facilities.
    def dist_matrix(fac, st_network, mode, direction, fishnet, num_to_find = 5):
        arcpy.AddMessage("...generating distance matrix")

        # Initialize points_dict
        points_dict = {}
        with arcpy.da.SearchCursor(fishnet, ['OID@','VALUE']) as search_rows:
                    for row in search_rows:
                        points_dict[row[0]] = [row[1], False, []]


        # Initialize network analysis                
        # Create a new closest facility analysis layer.
        arcpy.AddMessage(" ... initializing closest facility analysis")
        closest_fac_lyr_obj = arcpy.na.MakeClosestFacilityAnalysisLayer(
                st_network, "Closest_Facility",
                mode, direction, 
                number_of_facilities_to_find = num_to_find).getOutput(0)
        # Sublayer names
        sublayer_names = arcpy.na.GetNAClassNames(closest_fac_lyr_obj)
        cf_fac_lyr_name = sublayer_names["Facilities"]
        cf_incidents_lyr_name = sublayer_names["Incidents"]
        cf_routes_lyr_name = sublayer_names["CFRoutes"]

        # Load facilities 
        arcpy.na.AddLocations(closest_fac_lyr_obj, cf_fac_lyr_name, fac)
        # Load incidents      
        arcpy.na.AddLocations(closest_fac_lyr_obj, cf_incidents_lyr_name, fishnet)

        arcpy.na.Solve(closest_fac_lyr_obj)


        # Copy object ID to a new field for later spatial join
        arcpy.CalculateField_management(fishnet, "FishnetID", "!OBJECTID!", "PYTHON3")
        arcpy.CalculateField_management(fac, "FacID", "!OBJECTID!", "PYTHON3")

        # Spatial join to associate loactions with original ID
        fac_join = cf_fac_lyr_name + "_join"
        inc_join = cf_incidents_lyr_name + "_join"
        arcpy.SpatialJoin_analysis(cf_fac_lyr_name, fac, fac_join, match_option = "CLOSEST")
        arcpy.SpatialJoin_analysis(cf_incidents_lyr_name, fishnet, inc_join, match_option = "CLOSEST")

        # Join facility and fishnet ID to routes.
        routes = cf_routes_lyr_name + "_copy"
        arcpy.CopyFeatures_management(cf_routes_lyr_name, routes) 
        arcpy.JoinField_management(routes, "FacilityID", fac_join, "TARGET_FID", ["FacID"])
        arcpy.JoinField_management(routes, "IncidentID", inc_join, "TARGET_FID", ["FishnetID"])

        # Populate points_dict with distance.
        # Using heap to keep it sorted.
        with arcpy.da.SearchCursor(routes, ['FishnetID','FacID','Total_Length']) as search_rows:
            for row in search_rows:
                heapq.heappush(points_dict[int(row[0])][2], (row[2], row[1])) 

        arcpy.Delete_management(closest_fac_lyr_obj)
        arcpy.Delete_management(os.path.join(arcpy.env.workspace,  "ClosestFacility"))
        arcpy.Delete_management(routes)
        arcpy.Delete_management(fac_join)
        arcpy.Delete_management(inc_join)
        

        return points_dict

    # Initialize closest facility analysis.
    def initialize_find_rest(f, network, mode, direction, num_fac):
        # Initialize network analysis
        # Create a new closest facility analysis layer.
        arcpy.AddMessage(" ... initializing closest facility analysis")
        closest_fac_lyr_obj = arcpy.na.MakeClosestFacilityAnalysisLayer(
                network, "Closest_Facility",
                mode, direction, 
                number_of_facilities_to_find = num_fac).getOutput(0)
        # Sublayer names
        sublayer_names = arcpy.na.GetNAClassNames(closest_fac_lyr_obj)
        cf_fac_lyr_name = sublayer_names["Facilities"]
        cf_incidents_lyr_name = sublayer_names["Incidents"]
        cf_routes_lyr_name = sublayer_names["CFRoutes"]

        # Load facilities 
        arcpy.SelectLayerByAttribute_management(f, "NEW_SELECTION")
        arcpy.na.AddLocations(closest_fac_lyr_obj, cf_fac_lyr_name, f)

        fac_join = os.path.join(arcpy.env.workspace,  "fac_join")
        arcpy.SpatialJoin_analysis(cf_fac_lyr_name, f, fac_join, 
            match_option = "CLOSEST")
        
        return closest_fac_lyr_obj, fac_join

    # Find the distance from this point to all other facilities.
    def find_rest(targetID, fc, fc_dict, num, cf_obj, fac_join):
        # Sublayer names
        sublayer_names = arcpy.na.GetNAClassNames(cf_obj)
        cf_fac_lyr_name = sublayer_names["Facilities"]
        cf_incidents_lyr_name = sublayer_names["Incidents"]
        cf_routes_lyr_name = sublayer_names["CFRoutes"]
        
        # Select the point and add as incident
        arcpy.SelectLayerByAttribute_management(fc, "NEW_SELECTION", 
                                    '"OBJECTID" = ' + str(targetID))
        arcpy.DeleteFeatures_management(cf_incidents_lyr_name)
        arcpy.na.AddLocations(cf_obj, cf_incidents_lyr_name, fc)
        arcpy.SelectLayerByAttribute_management(fc, "NEW_SELECTION")
        
        arcpy.na.Solve(cf_obj)    
        routes = fc + "_routes_copy"
        arcpy.CopyFeatures_management(cf_routes_lyr_name, routes) 
        arcpy.JoinField_management(routes, "FacilityID", fac_join, "TARGET_FID", ["FacID"])
        
        # Populate points list with distance.
        # Using heap to keep it sorted.
        with arcpy.da.SearchCursor(routes, ['FacID','Total_Length']) as search_rows:
            for row in search_rows:
                heapq.heappush(fc_dict[targetID][2], (row[1], row[0])) 
                
        arcpy.Delete_management(routes) 
        
        while num > 0:
            heapq.heappop(fc_dict[targetID][2])
            num -= 1  

    # Assign a point to a facility. Check if the facility is overloaded.       
    def assign_to(c_id, c_dict, f_id, f_dict, d, q):
        fac = f_dict[int(f_id)]
        point = c_dict[int(c_id)]
        fac[2][c_id] = d
        fac[1] += point[0] 
        point[1] = f_id
        if fac[1] > fac[0]: q.add(f_id)

    # Dissociate a point from a facility.
    def remove_from(c_id, c_dict, f_id, f_dict):
        fac = f_dict[int(f_id)]
        point = c_dict[int(c_id)]
        del fac[2][c_id]
        fac[1] -= point[0]
        point[1] = None
        heapq.heappop(point[2])

    # Assign fishnet cells to facilities with the goal of 
    # assigning each facility appropriate burden and minimizing total cost.
    def assign_points(fac_layer, points_dict, fishnet, network, mode, direction, num_found):
        arcpy.AddMessage("...assign points to facilities")

        network_initialized = False
        num_fac = int(arcpy.GetCount_management(fac_layer)[0])
        
        # Create a dictionary of facilities
        fac_dict = {}
        with arcpy.da.SearchCursor(fac_layer, ['OID@','Burden']) as search_rows:
                    for row in search_rows:
                        fac_dict[row[0]] = [row[1], 0, {}]
 
        # Assign all points to their nearest facilities.
        overloaded = set()
        for point_id, point in points_dict.items():
            if point[2]:
                distance, fac_id = heapq.heappop(point[2])
                assign_to(point_id, points_dict, fac_id, fac_dict, distance, overloaded)

        count = 0
        tried = []

        # Move points from overloaded facilities to underloaded facilities.
        while overloaded and count < num_fac:            
            prev_len = len(overloaded) 
            fac_id = int(overloaded.pop())
            fac = fac_dict[fac_id] 
            
            # Calculate the difference of distance from point to this facitity and its next nearest facility.
            diff_distance = []
            for point_id, dist in fac[2].items():
                point_id = int(point_id)
                # If no facility in point's list, find rest nearest facilities.
                if len(points_dict[point_id][2]) == 0:
                    if not network_initialized:
                        cf_obj, fac_join = initialize_find_rest(fac_layer, network, mode, direction, num_fac)
                        network_initialized = True
                    if point_id in tried:
                        continue
                    
                    find_rest(point_id, fishnet, points_dict, 
                              num_found, cf_obj, fac_join)        
                    tried.append(point_id)
                    
                # Add the point and the next facility to the priority queue with 
                # the difference of distance as priority.
                next_dist, next_fac = points_dict[point_id][2][0]
                heapq.heappush(diff_distance,(next_dist - dist, [point_id, next_fac, next_dist]))

            # Move superfluous points with smaller cost. 
            while fac[1] > fac[0] and diff_distance:
                point_id, next_fac_id, next_dist = heapq.heappop(diff_distance)[1]    
                next_fac = fac_dict[int(next_fac_id)]
                if next_fac[1] > next_fac[0] : continue
                remove_from(point_id, points_dict, fac_id, fac_dict)
                assign_to(point_id, points_dict, next_fac_id, fac_dict, next_dist, overloaded)     
                
            # If this facility is still overloaded, add it back.
            if fac[1] > fac[0]: overloaded.add(fac_id)

            # Avoid infinite loop.
            if len(overloaded) == prev_len:
                count += 1  
            else: count = 0

        # Populate Current burden.
        arcpy.AddField_management(fac_layer, 'Assigned_burden', 'DOUBLE')
        with arcpy.da.UpdateCursor(fac_layer, ['OID@', 'Assigned_burden']) as update_rows:
            for row in update_rows:
                row[1] = fac_dict[int(row[0])][1]
                update_rows.updateRow(row)

        # Add assigned 'FacilityID' to fishnet feature layer.      
        arcpy.AddField_management(fishnet, 'FacilityID', 'TEXT')            
        with arcpy.da.UpdateCursor(fishnet, ['OID@', 'FacilityID']) as update_rows:
            for row in update_rows:
                row[1] = str(points_dict[int(row[0])][1])
                update_rows.updateRow(row)
        
        try: arcpy.Delete_management(fac_join) 
        except: pass
        arcpy.Delete_management(os.path.join(arcpy.env.workspace,  "ClosestFacility"))

        return fac_dict


    def cap_based_nt_partitioning(
        facilities, fac_cap_field, 
        zones, zones_burden_field, 
        streets, network, output, 
        travel_mode = "Driving Time", 
        travel_direction = "FROM_FACILITIES", 
        cell_size = 0.003,
        num_to_find = 5
        ):
        # Check out Network Analyst license if available. 
        # Fail if the Network Analyst license is not available.
        if arcpy.CheckExtension("network") == "Available":
            arcpy.CheckOutExtension("network")
        else:
            raise arcpy.ExecuteError("Network Analyst Extension license is not available.") 

        if num_to_find == None: num_to_find = 5

        fishnet = os.path.join(arcpy.env.workspace,  "fishnet")
        fishnet_points = "fishnet_points"
        fishnet_points = os.path.join(arcpy.env.workspace,  fishnet_points) 

        # Create feature layer.
        facilities_lyr = os.path.join(arcpy.env.workspace, "facilities_lyr") 
        arcpy.MakeFeatureLayer_management(facilities, facilities_lyr)         
        
        zones_lyr = os.path.join(arcpy.env.workspace, "zones_lyr") 
        arcpy.MakeFeatureLayer_management(zones, zones_lyr)  
        
        temp_output = os.path.join(arcpy.env.workspace, "temp_output")
        

        # Create fishnet points from input zones.
        create_fishnet(zones_lyr, streets, fishnet_points, fishnet, cell_size, zones_burden_field)     

        # Distribute burden to facilities.
        distr_burden(fishnet_points, 'VALUE', facilities_lyr, fac_cap_field)        

        # Calculate distance matrix between facilities and fishnet points.
        points = dist_matrix(facilities_lyr, network, 
            travel_mode, travel_direction, fishnet_points, num_to_find)
     
        # Assign fishnet points to facilities based on the distance between them and facilities' capacity.
        assign_points(facilities_lyr, points, fishnet_points, 
            network, travel_mode, travel_direction, num_to_find)

        # Create output feature class.
        output_table = arcpy.AddJoin_management(fishnet, arcpy.ListFields(fishnet)[0].name, 
            fishnet_points, arcpy.ListFields(fishnet_points)[0].name, "KEEP_COMMON")
        arcpy.Dissolve_management(output_table, temp_output, ["fishnet_points.FacilityID"])
        arcpy.JoinField_management(temp_output, "fishnet_points_FacilityID", 
            facilities_lyr, "FacID", ["Burden", "Assigned_burden"])
   
        arcpy.CopyFeatures_management(temp_output, output)

        arcpy.Delete_management(facilities_lyr)
        arcpy.Delete_management(zones_lyr)
        arcpy.Delete_management(fishnet)
        arcpy.Delete_management(fishnet_points)
        arcpy.Delete_management(output_table)
        arcpy.Delete_management(temp_output)



    arcpy.env.workspace = workspace
    cap_based_nt_partitioning(inFacilities, inCapacityField, inZones, inBurdenField, 
        inStreets, inNetwork, outShp, inMode, inDirection, inCellSize, inNumToFind)

except Exception as e:
    # If unsuccessful, end gracefully by indicating why
    arcpy.AddError('\n' + "Script failed because: \t\t" + e.args[0] )
    # ... and where
    exceptionreport = sys.exc_info()[2]
    fullermessage   = traceback.format_tb(exceptionreport)[0]
    arcpy.AddError("at this location: \n\n" + fullermessage + "\n")



