# TouchDesigner Script TOP for Orbbec3D Astra
Orbbec3D Astra python implementation for TouchDesigner Script Top.

### Requirements:
- Windows
- TouchDesigner >= 2021.13610
- Virtualenv
- pip

### Installation instructions
- Clone repo
- create virtualenv in repo directory called venv/ and activate it
- pip install requirements

Open orbec-astra.toe in TouchDesigner. The python scripts for the Script TOPs add the venv/ directory to their paths, so there should be no need to adjust your python path in the TouchDesigner preferencs. 

### Update Orbbec OpenNI SDK
- download Orbbec OpenNI SDK from orbbec3d from https://orbbec3d.com/index/download.html
- replace Redist folder in this repo with the Windows/SDK/x64/Redist folder from the zipfile 


### Note
This project is a work in progress. TouchDesigner sometimes crashes when switching parameters on active streams.

Any help and feedback is welcome. Afaik, there are issues with openni2 when closing devices and streams that result in python exiting (which in turn quits touchdesigner).
