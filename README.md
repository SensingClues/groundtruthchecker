Check collected ground truth against required ground truth
and create a new map layer that people can use in the field (in Cluey) to collect the remaining points.


PROJECT AIM
Creation of a high quality land cover map, used to monitor changes in the landscape which are subject to local bylaws.

An initiative of By Life Connected and Sensing Clues, supported by 3edata. 

PROCESS
BLC provides a map with the project area boundaries (Area of Responsibility, AoR)
3edata uses this AoR map to create a map with Ground Truth Training Points that need to be collected.

This Ground Truth Training Points Map is uploaded to the Cluey Data Collector (Cluey) of Sensing Clues.
BLC staff use Cluey to visit the training points and assign the applicable classes to the various training points
This ground truth checker tool is used to update the Ground Truth Training Points Map (remove all points that have been collected)


INSTRUCTIONS (for macOS)
download the collected training points with the Observations Report
rename the file to input.csv and place it in the same folder as the place as the python app
make sure the Ground Truth Training Points Map provided map is placed here too, and named input.geojson


open terminal
bash
cd Documents/SensingClues/groundtruthchecker

#if needed
    pip3 install flask
#end of if needed

python3 app.py

See msg in the console: "Running on http://127.0.0.1:5002" 
Note that this address may differ from time to time
