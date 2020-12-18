# Capacity-based Network Partitioning

## Summary

This tool creates a new shapefile of service areas for given facilities from a street network. These areas are sized based on each facility's capacity and areas' burden, as well as the proximity to facilities in the network.

## Syntax

cap_based_nt_partitioning(facilities, fac_cap_field, zones, zones_burden_field, streets, network, output, {travel_mode }, {travel_from_to }, {cell_size}, {num_to_find})

| Name         | Data Type                      | Filter                               | Default           |
| ------------ | ------------------------------ | ------------------------------------ | ----------------- |
| facilities   | Shapefile, Layer, Feature Class | Feature Type:[“Point”]               |                   |
| fac_cap_field | Field |                                      |                   |
| zones   | Shapefile, Layer, Feature Class | Feature Type:[“Polygon”]               |                   |
| zones_burden_field | Field |               |                   |
| streets | Shapefile, Layer, Feature Class | Feature Type:[“Polyline”]               |                   |
| network      | Network Dataset                |                                 |                   |
| output  | Shapefile, Feature Class       |                                      |                   |
| travel_mode (Optional) | Network Travel Mode            | Travel Mode Unit Type                | Driving Time      |
| travel_direction (Optional) | String                         | [“FROM_FACILITIES”, “TO_FACILITIES”] | “FROM_FACILITIES” |
| cell_size (Optional) | Double                         |         > 0                    |            |
| num_to_find (Optional) | Long                     |                                      | 5           |

* travel_mode: The name of the travel mode to use in the analysis. The [travel mode](https://pro.arcgis.com/en/pro-app/2.7/help/analysis/networks/travel-modes.htm) represents a collection of network settings, such as travel restrictions and U-turn policies, that determine how a pedestrian, car, truck, or other medium of transportation moves through the network. Travel modes are defined on your network data source.
* travel_direction: Specifies the direction of travel between facilities and incidents.
* cell_size: size of fishnet cells that will be dissolved to create output polygon.
* num_to_find: The number of closest facilities to find per fishnet cell. This parameter will only influence time complexity.  



## Workflow

The overall workflow includes the four modules listed below:

* **Module 1 - Fishnet Creating Module**, which create fishnet cells from input zones.
  * Create fishnet 
  * Filter out fishnet cells that are far from streets (200 meters) or out of zones.
  * Distribute zones' burden to fishnet cells
* **Module 2 - Burden Distributing Module**, which distribute burden to facilities based on thier capacity.
  * burden_of_fac_x  = capacity_of_fac_x / total_capacity * total_burden

* **Module 3 - Cost Matrix Caculating Module**, which calculate cost matrix from each fishnet cell to `num_to_find` closest facilities. For each fishnet cell, `num_to_find` closest facilities' IDs and distance to them will stored in a priority queue with distance as priority. 
* **Module 4 - Cells Assigning Module**, which assign cells to facilities with the goal of assigning each facility appropriate burden and minimizing total cost.
  * Assign each fishnet cell to its nearest facility, check if the facility is overloaded.
  * Move cells from overloaded facilities to underloaded faciities.
    * while there is any overloaded facility
      * for each cell belonging to this facility, calculate the difference between the distance to this facility and to next closest facility. (If no next closest facility found in list, try to find rest of facilities)
      * while the facility is overloaded, pop the cell with the least difference in distance, and move it to next closest facility if the facility is underloaded.
      * check whether the facility is still overloaded.
  * Sum up actual assigned burden for each facility
* **Module 5 - Service Area Creating Module**, which dissolves fishnet cells by facility ID as service areas for facilities.

**Script**: [Capacity_based_network_partitionning.py](https://github.com/JingzongWang/Arcpy-network-partitioning/blob/main/scripts/Capacity_based_network_partitioning.py)

## Example

### Input

<img src="https://github.com/JingzongWang/Arcpy-network-partitionging/blob/main/images/Capacity-based-network-partitioning-input.jpg" width="300"/>

Typical input: 

1. Zones: 
   1. shapfile: 2010 Manhattan Census Tracts (https://data.cityofnewyork.us/City-Government/2010-Census-Tracts/fxpq-c8ku)
   2. population data: 2006-2010 ACS 5-year Estimates
2. Facilities: 
   1. shapefile: Manhattan Public High Schools (https://data.cityofnewyork.us/Education/School-Point-Locations/jfju-ynrr)
   2. enrollment data: 2006 - 2012 School Demographics and Accountability Snapshot(https://data.cityofnewyork.us/Education/2006-2012-School-Demographics-and-Accountability-S/ihfw-zy9j)
3. Streets & network: Manhattan street network(https://data.cityofnewyork.us/City-Government/NYC-Street-Centerline-CSCL-/exjm-f27b)

### Output

Compare the result with theissen polygons.

<img src="https://github.com/JingzongWang/Arcpy-network-partitionging/blob/main/images/Distance-based-network-partitioning-result.jpg" width="300"/>

black solid-line - Network-based Partitions

pink dash-line - Thiessen Polygons



## Limitation

1. Though the cells assigning module in this algorithm can balance the burden among facilities to some extent, the burden usually can not be assigned perfectly. In some cases, overloaded facilities can form enclosed groups that superfulous cells can't be reassgined to underloaded facilities outside the group.
2. Some partitions maybe not continue.