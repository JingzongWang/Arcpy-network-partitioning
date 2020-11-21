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

## Example

### Input
