import matplotlib.pyplot as plt
import geopandas as gpd
import pandas as pd
import numpy as np

from bezier import bezierSpherical
from tqdm import tqdm
from shapely.geometry import Point, LineString
from bezier import bezier as bz


# THe code includes plotting commands, but are marked as comments as default. The lines can be activated if wanted.


def draw(control_points, nodes, edges, n, use_3d, draw_map, output_option):

    if draw_map:
        nodes_list = pd.read_csv("/NUTS2_cents.csv", sep=',', encoding="latin-1") # NUT2-region centroids
        #map_2 = gpd.read_file('') # Data for background map, e.g. shapefile of NUTS2-regions. Used for plotting
        geometry = [Point(xy) for xy in zip(nodes_list['X'], nodes_list['Y'])]
        original_routes = gpd.read_file('OD_movement_DATA.csv', sep=',', encoding="utf-8", usecols=['OD_ID','ORIGIN','DESTINATION','COUNT']) # movement data, used for merging later on
         

        geo_df = gpd.GeoDataFrame(nodes_list, crs='epsg:4326', geometry=geometry)
      

        #fig, ax = plt.subplots(figsize=(50, 25))
        #map_2.plot(ax=ax, alpha=0.4, color='grey')
        #geo_df.plot(ax=ax, markersize=1)
    else:
        plt.gcf().set_dpi(300)

    if use_3d:
        n = -1
        step_size = 5
        #bezierSpherical.plot_spherical(control_points, nodes, edges, n, step_size)
    else:
        # create and bezier curves
        bezier_polygons = []
        for controlPoints in tqdm(control_points, desc="Drawing curves: "):
            polygon = bz.create_bezier_polygon(controlPoints, n)  # returns list of 2d vectors
            bezier_polygons.append(polygon)
            x = [arr[0] for arr in polygon]
            y = [arr[1] for arr in polygon]
            #plt.plot(x, y, color='red', linewidth=0.1, alpha=1)
        
        # create a list for the first and last points of each bezier line
        cp_list = [] #lista 1. ja vika control_points
        for poly in bezier_polygons:
            cp_list.append(np.array([poly[0], poly[-1]]))
                           
        
        # create a dataframe from control points to create origin and destination coordinate points
        cp_df = pd.DataFrame(columns=['orig', 'dest'])
        for cp in cp_list:
            cp_df = cp_df.append({'orig': cp[0], 'dest': cp[1]}, ignore_index=True)
        # adding an index column to the OD dataframe
        cp_df['id'] = cp_df.index
        
        
        # adding orig_nuts and dest_nuts ID's for control_points for later on happening join
        for index, poly in cp_df.iterrows():
            for _, centroid in geo_df.iterrows():
                if (poly['orig'][0] == centroid['X']) and (poly['orig'][1] == centroid['Y']):
                    cp_df.at[index, 'orig_nuts'] = centroid['NUTS_ID']

        for index, poly in cp_df.iterrows():
            for _, centroid in geo_df.iterrows():
                if (poly['dest'][0] == centroid['X']) and (poly['dest'][1] == centroid['Y']):
                    cp_df.at[index, 'dest_nuts'] = centroid['NUTS_ID']
                
        
        # create list of bezier linestrings
        lines = []
        for poly in bezier_polygons:
            a = LineString(poly)
            lines.append(a)

        # create dataframe and geodataframe for bezier lines
        lines_df = pd.DataFrame(lines, columns=['geometry'])
        
        lines_gdf = gpd.GeoDataFrame(lines_df, crs='epsg:4326', geometry='geometry')
        # adding an index column to the lines dataframe
        lines_gdf['id'] = lines_gdf.index
        
        # merging orig_nuts and dest_nuts to lines_gdf
        merged_lines_gdf = lines_gdf.merge(cp_df[['id','orig_nuts','dest_nuts']], on='id', how='left')
        
        # generate od ids
        merged_lines_gdf['OD_ID'] = merged_lines_gdf['orig_nuts'] + '_' + merged_lines_gdf['dest_nuts']
        
        # join original count data based on od_id
        merged_counts = merged_lines_gdf.merge(original_routes[['OD_ID','COUNT']], on=['OD_ID'], how='left')
        
        merged_counts['COUNT'] = merged_counts['COUNT'].astype(float)

        
        # empty list for dataframes
        straight_edges = []

        # draw lines without detour or with detour that was too long
        for edge in tqdm(edges, desc="Drawing lines: "):
            if edge.skip:
                continue
            
            # get nodes
            o = nodes[edge.source]
            d = nodes[edge.destination]
            
            # get names of nodes
            o_name = o.name
            d_name = d.name
                        
            # get count of flow for edge connecting the nodes
            count = edge.count

            # generate geometry for the edge
            line = LineString([Point([o.longitude, o.latitude]), Point([d.longitude, d.latitude])])
            
            # old lat lon stuff
            x = [o.longitude, d.longitude]
            y = [o.latitude, d.latitude]
            
            # create dataframe
            straight_df = pd.DataFrame(columns=['orig_nuts', 'dest_nuts', 'OD_ID', 'COUNT', 'geometry'])
            
            # add row
            straight_df = straight_df.append({'orig_nuts': o_name,
                                              'dest_nuts': d_name,
                                              'OD_ID': o_name + '_' + d_name,
                                              'COUNT': count,
                                              'geometry': line}, ignore_index=True)
                                              
            straight_df['COUNT'] = straight_df['COUNT'].astype(float)
                    
            # add to list
            straight_edges.append(straight_df)
            
            #plt.plot(x, y, color='red', linewidth=0.1, alpha=1)
        
      
        # concatenate list to dataframe
        straights = pd.concat(straight_edges)
        
        # add orig and dest nuts
        straights['orig_nuts'] = straights['OD_ID'].apply(lambda x: x.split('_')[0])
        straights['dest_nuts'] = straights['OD_ID'].apply(lambda x: x.split('_')[1])
        
        # create geodataframe of straight lines
        straights = gpd.GeoDataFrame(straights, crs='epsg:4326', geometry='geometry')
        
        # get results
        results = merged_counts.append(straights, ignore_index=True)
                     
        # choose file output options
        if output_option == 1:
            results.to_file('/straights_AND_bezier.shp')
            
        elif output_option == 2:
            straights.to_file('/straight_lines.shp')
            merged_counts.to_file('/Bezier.shp')
            
        elif output_option == 3:
            results.to_file('/straights_AND_bezier.shp')
            straights.to_file('/straight_lines.shp')
            merged_counts.to_file('/Bezier.shp')
        
    #plt.axis('scaled')
    #plt.axis('off')
    #plt.tight_layout()
    #plt.show()