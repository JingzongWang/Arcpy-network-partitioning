# Distance-based Network Partitioning

## Summary

This tool creates a new shapefile or feature class of service areas for given facilities from a street network. These areas are sized based on proximity or other cost to facilities in the network.

## Syntax

dist_based_nt_partitioning(facilities, st_network, output, {mode}, {from_to}, {max_cost})

|	Name|	Data Type|	Filter|	Default|
|-|-|-|-|
| facilities | Shapefile,Layer, Feature Class| Feature Type:[“Point”]| |
| st_network | Network Dataset |  | |
| output | Shapefile, Feature Class| | |
| mode (Optional) | Network Travel Mode| Travel Mode Unit Type| Driving Time|
| direction (Optional) | String| [“FROM_FACILITIES”, “TO_FACILITIES”]| “FROM_FACILITIES”|
| max_cost (Optional) | Double| > 0 | 1000000 |

* mode: The name of the travel mode to use in the analysis. The [travel mode](https://pro.arcgis.com/en/pro-app/2.7/help/analysis/networks/travel-modes.htm) represents a collection of network settings, such as travel restrictions and U-turn policies, that determine how a pedestrian, car, truck, or other medium of transportation moves through the network. Travel modes are defined on your network data source.

* direction: Specifies the direction of travel between facilities and incidents.

  

## Workflow

The overall workflow includes the two modules listed below:
* **Module 1 - Iterative Boundary Building Module**, which iteratively create points barriers as boundry of network partitions:
  * Initialize closest facility analysis.
  * For each facility (skip the last one), add it as incidents and other unfinished facilities as faciliites.
    * while it is reachable from other facilities:
      * Add this facility as incidents and other unfinished facilities as faciliites.
      * Find route to its closest facility.
      * Add the mid point of the route as barriers.
      * Continue loop until can't find route to other facility any more.
  * Copy barriers layer to a new feature class which contains all the boundary points we need for creating partitions.

* **Module 2 - Partition Creating Module**, which create service area polygon for each facility:
  * Initialize service area analysis.
  * With boundary points from previous module as barriers, solve service area for all facilities.
  * Spatial join the facilities' information back to these areas.
  * Copy it to output file.

**Script**: [Distance_based_network_partitioning.py](https://github.com/JingzongWang/Arcpy-network-partitioning/blob/main/scripts/Distance_based_network_partitioning.py)

## Example

### Input

<img src="https://github.com/JingzongWang/Arcpy-network-partitionging/blob/main/images/Distance-based-network-partitioning-input.jpg" width="300"/>

Typical input: images

1.facilities: Manhattan Heath Facilites (https://data.cityofnewyork.us/Health/NYC-Health-Hospitals-patient-care-locations-2011/f7b6-v6v3/data)
	
2.network: Manhattan street network(https://data.cityofnewyork.us/City-Government/NYC-Street-Centerline-CSCL-/exjm-f27b)

### Process

<img src="https://github.com/JingzongWang/Arcpy-network-partitionging/blob/main/images/Distance-based-network-partitioning-process.jpg" width="300"/>

### Output

Compare the result with theissen polygons.

<img src="https://github.com/JingzongWang/Arcpy-network-partitionging/blob/main/images/Distance-based-network-partitioning-result.jpg" width="300"/>

black solid-line - Network-based Partitions

pink dash-line - Thiessen Polygons

