import rasterio
import numpy as np
import streamlit as st
import os
import folium



st.title('Forest Cover Benchmark Map and Area')
folder_path = st.text_input('Copy/paste project folder path')

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
start_HRP= st.selectbox('Select start HRP map (.tif)', options=filenames)
midpoint_HRP = st.selectbox('Select midpoint HRP map (.tif)', options=filenames)
end_HRP = st.selectbox('Select end HRP map (.tif)', options=filenames)


# ## file paths/names
# tif_2008_path = 'fnf_2008_clipped.tif'
# tif_2011_path = 'fnf_2011_clipped.tif'
# tif_2014_path = 'fnf_2014_clipped.tif'

## define the 8 forest transitional values/classes based on VMD0055 Table 15 and using dictionary 1=forest, 2=non-forest, 0=nodata
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


## define the interpreted classes mapping based on VMD0055 Table 15
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
        
        ## intiatilize empty forest cover benchmark map with zeroes using same shape as tif
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
        
        ## save/write the fcbm
        profile = tif_start.profile
        profile.update(dtype=rasterio.uint8, count=1, compress='lzw')
        
        with rasterio.open('fcbm.tif', 'w', **profile) as dst:
            dst.write(fcbm)
        
    return fcbm, transitional_class_areas, interpreted_class_areas

## run function and get results
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
    """Displays areas of transitional and interpreted classes."""

    # st.write("Forest Transition Classes:")
    # for cls, area in transitional_class_areas.items():
    #     class_description = transitional_class_descriptions.get(cls)
    #     if class_description:
    #         st.write(f"Class {cls} ({class_description}): {area:.2f} ha")

    st.write("\nInterpreted Classes:")
    for cls, area in interpreted_class_areas.items():
        class_description = interpreted_class_descriptions.get(cls)
        if class_description:
            st.write(f"Class {cls} ({class_description}): {area:.2f} ha")



# Button to trigger calculation
if st.button("Calculate Forest Cover Area Benchmark"):
    # Call the display_areas function to show results
    display_areas(transitional_class_areas, interpreted_class_areas)


########################### DISPLAY MAP ON STREAMLIT


import streamlit as st
from streamlit_folium import folium_static
import folium
import rasterio
import numpy as np

# A dummy Sentinel 2 COG I had laying around
tif = fcbm
# This is probably hugely inefficient, but it works. Opens the COG as a numpy array
src = rasterio.open(tif)
array = src.read()
bounds = src.bounds

x1,y1,x2,y2 = src.bounds
bbox = [(bounds.bottom, bounds.left), (bounds.top, bounds.right)]


st.title("Plotting maps!")
# center on Liberty Bell
m = folium.Map(location=[14.59, 120.98], zoom_start=6)

# add marker for Liberty Bell
tooltip = "Manilla city"
folium.Marker(
    [14.599512, 120.984222], popup="This is it!", tooltip=tooltip
).add_to(m)

img = folium.raster_layers.ImageOverlay(
    name="Sentinel 2",
    image=np.moveaxis(array, 0, -1),
    bounds=bbox,
    opacity=0.9,
    interactive=True,
    cross_origin=False,
    zindex=1,
)

# folium.Popup("I am an image").add_to(img)
img.add_to(m)
folium.LayerControl().add_to(m)

# call to render Folium map in Streamlit
folium_static(m)






runOnSave=True