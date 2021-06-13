# TouchDesigner Script TOP for Orbbec3D Astra
Orbbec3D Astra python implementation for TouchDesigner Script Top.
Work in progress. Still unstable. TouchDesigner might crash when switching parameters on active streams.

Any help and feedback is welcome.

### Requirements:
- Windows
- TouchDesigner >= 2021.13610
- Virtualenv
- pip

### Installation instructions
- Clone repo
- create virtualenv in repo directory called venv/ and activate it
- pip install requirements

Open orbec-astra.toe in TouchDesigner

### Update Orbbec OpenNI SDK
- download Orbbec OpenNI SDK from orbbec3d from https://orbbec3d.com/develop/
- replace Redist folder in this repo with the Windows/SDK/x64/Redist folder from the zipfile 
