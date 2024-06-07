import rasterio
import numpy as np
import streamlit as st
import os
import folium



st.title('Forest Cover Benchmark Area and Map')
folder_path = st.text_input('Copy/Paste Project Folder Path')

#scan the folder with files
file_paths = []
filenames = []  
if os.path.isdir(folder_path):
    for fn in os.listdir(folder_path):
        fp = f'{folder_path}/{fn}'
        if os.path.isfile(fp):
            file_paths.append(fp)
            filenames.append(os.path.basename(fp))

#select file from scanned folder
start_HRP= st.selectbox('Select Start HRP Map (.tif)', options=filenames)
midpoint_HRP = st.selectbox('Select Midpoint HRP Map (.tif)', options=filenames)
end_HRP = st.selectbox('Select End HRP Map (.tif)', options=filenames)

#define the 8 forest transitional values/classes based on VMD0055 Table 15 and using dictionary 1=forest, 2=non-forest, 0=nodata
transitional_class_mapping = {
    (2, 2, 2): 1,  #stable non-forest
    (2, 2, 1): 2,  #stable non-forest
    (2, 1, 2): 3,  #stable non-forest
    (2, 1, 1): 4,  #stable non-forest
    (1, 1, 1): 5,  #stable forest
    (1, 2, 2): 6,  #deforested in first half of HRP(2008-2011)
    (1, 2, 1): 7,  #deforested in first half of HRP(2008-2011) 
    (1, 1, 2): 8   #deforested in second half of HRP(2011-2014)
}


##define the interpreted classes mapping based on VMD0055 Table 15
interpreted_class_mapping = {
    1: 1,  
    2: 1,  
    3: 1,  
    4: 1, 
    5: 2, 
    6: 3,  
    7: 3,  
    8: 4   
}

def create_fcbm(start_HRP, midpoint_HRP, end_HRP):
    with rasterio.open(start_HRP) as tif_start, rasterio.open(midpoint_HRP) as tif_midpoint, rasterio.open(end_HRP) as tif_end:
        map_start_HRP = tif_start.read()
        map_midpoint_HRP = tif_midpoint.read()
        map_end_HRP = tif_end.read()
        
        ##intiatilize empty forest cover benchmark map with zeroes using same shape as tif
        fcbm = np.zeros_like(map_start_HRP, dtype=np.uint8)
        
        ##iterate through the mapping to assign the new class values
        for (vStart, vMid, vEnd), new_class in transitional_class_mapping.items():
            mask = (map_start_HRP == vStart) & (map_midpoint_HRP == vMid) & (map_end_HRP == vEnd) #boolean mask
            fcbm[mask] = new_class #assign forest transitional values to the 8 boolean masks
            
        ##calculate area in hectares for each forest transition class
        if (tif_start.res[0] != tif_midpoint.res[0] or tif_start.res[0] != tif_end.res[0] or
        tif_start.res[1] != tif_midpoint.res[1] or tif_start.res[1] != tif_end.res[1]):
            raise ValueError("Input tifs must have the same resolution") #verify resolution of 3 input tifs match        
        
        pixel_area_ha = (tif_start.res[0] * tif_start.res[1]) / 10000  #sq meter to ha
        
        ##calculate area of all forest transition classes
        transitional_class_areas = {} #initialize empty dictionary to store class areas
        for new_class in transitional_class_mapping.values():
            count = np.sum(fcbm == new_class) #count number of pixels assigned to class
            transitional_class_area_ha = count * pixel_area_ha #multiply count by pixel area ha to get total area
            transitional_class_areas[new_class] = transitional_class_area_ha #add to dictionary   
        
        ##map forest transition classes to interpreted classes and calculate area
        interpreted_class_areas = {}
        for transition_class, interpreted_class in interpreted_class_mapping.items():
            if interpreted_class not in interpreted_class_areas:
                interpreted_class_areas[interpreted_class] = 0
            interpreted_class_areas[interpreted_class] += transitional_class_areas.get(transition_class, 0)
        
        ##save/write the fcbm
        profile = tif_start.profile
        profile.update(dtype=rasterio.uint8, count=1, compress='lzw')
        
        with rasterio.open('fcbm.tif', 'w', **profile) as dst:
            dst.write(fcbm)
        
    return fcbm, transitional_class_areas, interpreted_class_areas

##run function and get results
fcbm, transitional_class_areas, interpreted_class_areas = create_fcbm(start_HRP, midpoint_HRP, end_HRP)

transitional_class_descriptions = {
    1: "Stable non-forest",
    2: "Stable non-forest",
    3: "Stable non-forest",
    4: "Stable non-forest",
    5: "Stable forest",
    6: "Deforested in first half of HRP",
    7: "Deforested in first half of HRP",
    8: "Deforested in second half of HRP"
}

interpreted_class_descriptions = {
    1: "Stable non-forest",
    2: "Stable forest",
    3: "Deforested in first half of HRP",
    4: "Deforested in second half of HRP"
}

def display_areas(transitional_class_areas, interpreted_class_areas):
    st.write("\nInterpreted Classes:")
    for cls, area in interpreted_class_areas.items():
        class_description = interpreted_class_descriptions.get(cls)
        if class_description:
            st.write(f"Class {cls} ({class_description}): {area:.2f} ha")

#button to trigger calculation
if st.button("Calculate Forest Cover Benchmark Area"):
    display_areas(transitional_class_areas, interpreted_class_areas)


########################################### DISPLAY MAP ON STREAMLIT

import streamlit as st
import rasterio
from rasterio.plot import show
from tempfile import NamedTemporaryFile
import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.colors as mcolors
import matplotlib.patches as mpatches

#upload TIFF file
uploaded_file = st.file_uploader("Upload FCBM (.tif) here", type=["tif"])

if uploaded_file is not None:
    with NamedTemporaryFile(delete=False, suffix=".tif") as tmp:
        tmp.write(uploaded_file.getvalue())
        tmp_path = tmp.name

    with rasterio.open(tmp_path) as src:
        #st.write(f"Number of bands: {src.count}")
        #st.write(f"Width: {src.width}")
        #st.write(f"Height: {src.height}")

        band1 = src.read(1)

        #find unique values (transitional class)
        unique_values = np.unique(band1)
        #st.write(f"Unique values: {unique_values}")

        #map unique values to colors
        cmap = plt.get_cmap('tab20', len(unique_values))
        norm = mcolors.BoundaryNorm(unique_values, cmap.N)

        #plot image
        st.subheader("FCBM: Forest Transition Values")
        fig, ax = plt.subplots()
        cax = ax.imshow(band1, cmap=cmap, norm=norm)
        
        #legend
        patches = [mpatches.Patch(color=cmap(norm(val)), label=f"Value {val}") for val in unique_values]
        ax.legend(handles=patches, bbox_to_anchor=(1.05, 1), loc='upper left')
        
        st.pyplot(fig)

    
    os.unlink(tmp_path)



runOnSave=True