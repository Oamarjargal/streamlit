import geopandas as gpd
import rasterio
import rasterio.mask
import numpy as np
import rasterio
import geopandas as gpd
from shapely.geometry import Polygon
from rasterio.mask import mask
from rasterio.features import shapes
import numpy as np

import streamlit as st

st.title('Calculate Emissions from Unplanned Deforestation')

import os
import streamlit as st

folder_path = st.text_input('Input folder path')

# Scan the folder with files.
file_paths = []
filenames = []  # List to store just filenames
if os.path.isdir(folder_path):
    for fn in os.listdir(folder_path):
        fp = f'{folder_path}/{fn}'
        if os.path.isfile(fp):
            file_paths.append(fp)
            filenames.append(os.path.basename(fp))

# Select file from scanned folder.
selected_file_projBound = st.selectbox('Select project boundary (.shp)', options=filenames)
selected_file_emission = st.selectbox('Select strata emission factor (.tif)', options=filenames)
selected_file_risk = st.selectbox('Select allocated risk (.tif)', options=filenames)

# st.write(f' Project Boundary: {os.path.basename(selected_file_projBound)}')
# st.write(f' Emission Factor: {os.path.basename(selected_file_emission)}')
# st.write(f' Allocated Risk Map: {os.path.basename(selected_file_risk)}')

######################

def calculate_emissions():  
    project_boundary = gpd.read_file(selected_file_projBound) ## read project boundary shapefile

    with rasterio.open(selected_file_emission) as emissions: ## open emissions factor tif & clip it to project boundary 
        emissions_clipped, emissions_transform = rasterio.mask.mask(emissions, project_boundary.geometry, crop=True)

    with rasterio.open(selected_file_risk) as risk: ## open risk map & clip it to project boundary
        risk_clipped, risk_transform = rasterio.mask.mask(risk, project_boundary.geometry, crop=True)

    estimated_emissions = emissions_clipped * risk_clipped  # calculate estimated emissions/pixel via instruction in doc section 5.6.2
    total_emissions = np.nansum(estimated_emissions)  # sum all estimated emissions using nansum to ignore NaNs

    return total_emissions



# Button to trigger calculation
if st.button("Calculate Emissions"):
    total_emissions = calculate_emissions()

    # Display the calculated emissions
    st.write(f"Total Emissions: {total_emissions:.2f} ha")  


runOnSave=True