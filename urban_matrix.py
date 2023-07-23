import streamlit as st
import os
from streamlit_folium import folium_static
import folium
from streamlit_folium import st_folium
import rasterio
from rasterio.warp import calculate_default_transform, reproject, Resampling
import numpy as np
from matplotlib import cm
import tempfile
from matplotlib.colors import ListedColormap, LinearSegmentedColormap
#import matplotlib.pylab as pl

import pylandstats as pls
from pylandstats import Landscape as ld
import geopandas as gpd
import pandas as pd
import altair as alt
from shapely.geometry import Point


cmap = ListedColormap(["white","red",'yellow','white'])
m = folium.Map(location=[30.316496, 78.032188], zoom_start=11)

#map = st_folium(m, height=550, width=1000)
st.title("Landscape Metrics Calculation")




patch_option = ('Perimeter Area Ratio','Perimeter','Shape Index','Euclidean Nearest Neighbor','Fractal Dimension')
Class_option = ('Proportion of Landscape','Edge Density','Total Area','Number of Patches','Patch Density','Largest Patch Index','Total Edge','Landscape Shape Index')
landscape_option = ('LEI','Total Area','Edge Density','Number of Patches','Patch Density','Largest Patch Index','Landscape Shape Index','Effective Mesh Size','Shannon Diversity Index')





option = st.sidebar.selectbox('Choose Spatial Metrics Type',('Choose Spatial Metrics Type','Patch','Class','Landscape'))

if (option == 'Patch'):
    #option1.selectbox('Choose Patch Metric Type',patch_option)
    option1 = st.sidebar.selectbox('Choose Patch Metrics Type',patch_option)


elif (option == 'Class'):
    option1 = st.sidebar.selectbox('Choose Class Metrics Type',Class_option)

elif (option == 'Landscape'):
    option1 = st.sidebar.selectbox('Choose Landscape Metrics Type',landscape_option)

else:
  option1 = ""

option1 = option1.lower().replace(' ','_')
#st.write(option1)
uploaded_files = st.sidebar.file_uploader("Please choose a file", type=['tif','tiff','geotiff'],accept_multiple_files=True)

#def click_function():

  #st.write(option1)


#submit = st.sidebar.button("Submit",on_click=click_function)

#st.write('You selected:', option1)


patch_number=[]
year=[]

base_mask = Point(78.032188, 30.316496)
base_mask_crs = "+proj=longlat +ellps=WGS84 +datum=WGS84 +no_defs"

# buffer distances (in meters)
#buffer_dists = [2000, 4000, 6000, 8000, 10000, 12000]

buffer_dists = [4000]

for file in uploaded_files:

  tempfile1 = tempfile.NamedTemporaryFile(delete=False,suffix='.tif')
  tempfile1.write(file.getbuffer())
  src = rasterio.open(tempfile1.name)
  array = src.read()
  dstCrs = {'init': 'EPSG:4326'}

  bounds = src.bounds
  x1,y1,x2,y2 = src.bounds
  bbox = [(bounds.bottom, bounds.left), (bounds.top, bounds.right)]

  transform, width, height = calculate_default_transform(
        src.crs, dstCrs, src.width, src.height, *src.bounds)

  transform1=rasterio.transform.array_bounds(height, width, transform)
  bbox1 = [(transform1[1], transform1[0]), (transform1[3], transform1[2])]

  #tempfile2 = tempfile.NamedTemporaryFile(delete=False,suffix='.tif')
  destination = np.zeros(array.shape, np.uint8)
  #dstRst = rasterio.open(tempfile2.name)

  for i in range(1, src.count + 1):

    reproject(
        source=rasterio.band(src, i),
        destination=destination,
        #src_transform=srcRst.transform,
        src_crs=src.crs,
        #dst_transform=transform,
        dst_crs=dstCrs,
        resampling=Resampling.nearest)



  #st.write(bbox1)
  #st.write(bbox)
  img = folium.raster_layers.ImageOverlay(
    name=file.name,
    image=np.moveaxis(destination, 0, -1),
    bounds=bbox1,
    opacity=0.9,
    interactive=True,
    cross_origin=False,
    zindex=1,
    colormap=cmap
    )
  img.add_to(m)

  #matrix Calculation
  ls = pls.Landscape(tempfile1.name)
  #class_metrics_df = ls.compute_class_metrics_df(metrics=['proportion_of_landscape', 'edge_density' , 'total_area' , 'number_of_patches' ,'landscape_shape_index' ])
  #class_metrics_df = ls.compute_class_metrics_df(metrics=[option1])

  if (option == 'Patch'):
    metrics_df = ls.compute_patch_metrics_df(metrics=[option1])


  elif (option == 'Class'):
    metrics_df = ls.compute_class_metrics_df(metrics=[option1])

  elif (option == 'Landscape'):

    #st.write(option1)

    if (option1 == 'lei'):

      ba = pls.BufferAnalysis(
        tempfile1.name,
        base_mask,
        buffer_dists,
        buffer_rings=True,
        base_mask_crs=base_mask_crs,
        )



      df = ba.compute_class_metrics_df(metrics = ['total_area'])

      # split the dataframe base on the 'class_val column
      grouped = df.groupby('class_val')

      # create a list of dataframes split by group
      dfs = [grouped.get_group(x) for x in grouped.groups]

      # create a new dataframe by joining the split dataframes using the 'buffer_dists' column
      new_df = dfs[0]
      for i in range(1, len(dfs)):
          new_df = new_df.merge(dfs[i], on = 'buffer_dists')

      new_df['total_area'] = new_df.iloc[:, -2:].sum(axis=1)
      new_df['lei'] = (new_df['total_area_x'] / new_df['total_area'])*100
      metrics_df = new_df
      #st.write(list(metrics_df))

    else:


      metrics_df = ls.compute_landscape_metrics_df(metrics=[option1])
      #st.write(list(metrics_df))


  #st.write(list(class_metrics_df[option1]))
  patch_number.append(list(metrics_df[option1])[0])

  file_name = file.name
  year.append(file_name.split('_')[1])

folium.LayerControl().add_to(m)
folium_static(m)


if (len(year) > 0):
  st.title (option1.upper().replace('_',' '))

  chart_data = pd.DataFrame({
    'year': year,
    option1: patch_number,
    })

  st.dataframe(data=chart_data)

  c = alt.Chart(data = chart_data, title=option1.upper().replace('_',' ')).mark_line(point=True).encode(
    alt.Text('year'),
    alt.Y(option1+':Q', axis=alt.Axis(title=option1.upper().replace('_',' '))),
    x=alt.X('year:Q', axis=alt.Axis(title="Year",format=".0f")))


  text = c.mark_text(
    align='left',
    baseline='middle',
    dx=3  # Nudges text to right so it doesn't appear on top of the bar
  ).encode(
    text='year:Q'
  )
    #x=alt.X('year:Q', axis=alt.Axis(title="Year",format=".0f"), bin=alt.Bin(extent=[1990, 2021], step=5)))
  (c + text).properties(height=900)
  st.altair_chart((c + text), use_container_width=True)
