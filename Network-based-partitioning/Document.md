## Summary

This tool creates a new shapefile or feature class of service areas for given facilities from a street network. These areas are sized based on proximity or other cost to facilities in the network.

## Parameters

|Label|	Name|	Data Type|	Type|	Direction|	Filter|	Default|
|-|-|-|-|-|-|-|
|workspace| workspace| Folder| Required| Input| | |
|facilities| facilities| Shapefile,Layer, Feature Class| Required| Input| Feature Type:[“Point”]| |
output| outShp| Shapefile, Feature Class| Required| Output| | |
network| network| Network| Dataset| Required| Input| | |
travel mode| travelMode| Network Travel Mode| Optional| Input| Travel Mode Unit Type| Driving Time|
from or toward facilities| travelFromTo| String| Optional| Input| [“FROM_FACILITIES”, “TO_FACILITIES”]| “FROM_FACILITIES”|
max| search| cost| maxTravel| Double| Optional| Input| | 1000000

## Algorithm

There are two main steps:
1. **Find boudary points**: To find boundary points, we start at one facility, find route to another facility closest to it, add the mid point of the route as barriers, then continue finding next route to closest facility with barriers. Barriers will keep increasing through this process, and finally this facility is unreachable to any other facilities or can’t access to any facility from this one. After finished this one, we will circle through whole facilities and keep adding mid points as barriers. The last facility can be skipped. Finally, barriers layer contains all the boundary points we need for creating partitions.
2. **Create partitions**: With these boundary points as barriers, create service area polygon for each facility, spatial join the facilities back to these areas and copy it to output file.

### Pseudo code:

1. Initialization
2. for each facility:
	1.while can find route to any other facility:
		1. find route to nearest facility
		2. add mid point of the route as barriers
3. Solve service areas with boudary points as barriers
4. Spatial join service areas with facilities and copy to output file.

## Example

### Input

<img src="https://github.com/JingzongWang/Arcpy-network-partitionging/blob/main/Network-based-partitioning/Network-based-partitioning-input.jpg" width="300"/>

Typical input: 

1.facilities: Manhattan Heath Facilites (https://data.cityofnewyork.us/Health/NYC-Health-Hospitals-patient-care-locations-2011/f7b6-v6v3/data)
	
2.network: Manhattan street network(https://data.cityofnewyork.us/City-Government/NYC-Street-Centerline-CSCL-/exjm-f27b)

### Process

<img src="https://github.com/JingzongWang/Arcpy-network-partitionging/blob/main/Network-based-partitioning/Network-based-partitioning-process.jpg" width="300"/>

### Output

Compare the result with theissen polygons.

<img src="https://github.com/JingzongWang/Arcpy-network-partitionging/blob/main/Network-based-partitioning/Network-based-partitioning-result.jpg" width="300"/>

black solid-line - Network-based Partitions

pink dash-line - Thiessen Polygons

