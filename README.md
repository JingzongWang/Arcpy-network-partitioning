# Arcpy-network-partitioning
Tools for solving different kinds of network partitioning problems in ArcGIS Pro
## Features
* [Distance_based_network_partitioning.py](https://github.com/JingzongWang/Arcpy-network-partitioning/blob/main/scripts/Distance_based_network_partitioning.py) This script creates a new shapefile or feature class of service areas for given facilities from a street network. These areas are sized based on proximity or other cost to facilities in the network. 

  <img src="https://github.com/JingzongWang/Arcpy-network-partitioning/blob/main/images/Network-based-partitioning-result.jpg?raw=true" width="300"/>

  (black solid-line - Network-based Partitions; pink dash-line - Thiessen Polygons)

* [Capacity_based_network_partitionning.py](https://github.com/JingzongWang/Arcpy-network-partitioning/blob/main/scripts/Capacity_based_network_partitioning.py) This script creates a new shapefile of service areas for given facilities from a street network. These areas are sized based on each facility's capacity and areas' burden, as well as the proximity to facilities in the network.

  <img src="https://github.com/JingzongWang/Arcpy-network-partitioning/blob/main/images/Capacity-based-partitioning-output.jpg?raw=true" width="300"/>
## Instructions
1. Download the latest release
2. Modify the code to suit your needs
3. Run the code in standalone python, or run the provided geoprocessing tool from within ArcGIS Pro.
## Requirements
* ArcGIS Pro 2.5 or later
* the Network Analyst extension license
## Documents
* <a href = "https://github.com/JingzongWang/Arcpy-network-partitionging/blob/main/documents/Distance_based_network_partitioning.md">Distance_based_network_partitioning</a>
* <a href = "https://github.com/JingzongWang/Arcpy-network-partitionging/blob/main/documents/Capacity_based_network_partitioning.md">Capacity_based_network_partitioning</a>

## Issues
Please let me know if you find a bug by submitting an issue.

## <a href = "https://github.com/JingzongWang/Arcpy-network-partitioning/blob/main/LICENSE">Licensing</a>
