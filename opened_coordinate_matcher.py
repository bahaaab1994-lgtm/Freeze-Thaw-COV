# -*- coding: utf-8 -*-
"""
Created on Wed Aug  6 21:27:27 2025

@author: bahaa
"""

import pandas as pd
import numpy as np
from math import radians, cos, sin, asin, sqrt

def haversine_distance(lat1, lon1, lat2, lon2):
    """
    Calculate the great circle distance between two points 
    on the earth (specified in decimal degrees)
    
    Returns distance in kilometers
    """
    # Convert decimal degrees to radians
    lat1, lon1, lat2, lon2 = map(radians, [lat1, lon1, lat2, lon2])
    
    # Haversine formula
    dlat = lat2 - lat1
    dlon = lon2 - lon1
    a = sin(dlat/2)**2 + cos(lat1) * cos(lat2) * sin(dlon/2)**2
    c = 2 * asin(sqrt(a))
    
    # Radius of earth in kilometers
    r = 6371
    
    return c * r

def find_nearest_location(target_lat, target_lon, data, max_distance_km=50):
    """
    Find the nearest monitoring station to the given coordinates.
    
    Args:
        target_lat (float): Target latitude
        target_lon (float): Target longitude
        data (pd.DataFrame): DataFrame containing location data with 'Latitude' and 'Longitude' columns
        max_distance_km (float): Maximum distance in kilometers to consider (default: 50km)
    
    Returns:
        tuple: (nearest_location_row, distance_km) or (None, None) if no location found within max_distance
    """
    try:
        if data.empty:
            return None, None
        
        # Ensure required columns exist
        required_cols = ['Latitude', 'Longitude']
        for col in required_cols:
            if col not in data.columns:
                print(f"Required column '{col}' not found in data")
                return None, None
        
        # Calculate distances to all locations
        distances = []
        valid_indices = []
        
        for idx, row in data.iterrows():
            try:
                lat = float(row['Latitude'])
                lon = float(row['Longitude'])
                
                # Skip rows with invalid coordinates
                if pd.isna(lat) or pd.isna(lon):
                    continue
                
                distance = haversine_distance(target_lat, target_lon, lat, lon)
                distances.append(distance)
                valid_indices.append(idx)
                
            except (ValueError, TypeError):
                # Skip rows with invalid coordinate data
                continue
        
        if not distances:
            print("No valid coordinates found in data")
            return None, None
        
        # Find the nearest location
        min_distance_idx = np.argmin(distances)
        min_distance = distances[min_distance_idx]
        nearest_row_idx = valid_indices[min_distance_idx]
        
        # Check if within maximum distance
        if min_distance > max_distance_km:
            print(f"Nearest location is {min_distance:.2f} km away, which exceeds maximum distance of {max_distance_km} km")
            return None, None
        
        nearest_location = data.loc[nearest_row_idx]
        
        print(f"Found nearest location: {nearest_location.get('County', 'Unknown')}, {nearest_location.get('State', 'Unknown')} at {min_distance:.2f} km")
        
        return nearest_location, min_distance
        
    except Exception as e:
        print(f"Error in find_nearest_location: {str(e)}")
        return None, None

def find_locations_within_radius(target_lat, target_lon, data, radius_km=25):
    """
    Find all monitoring stations within a specified radius of the given coordinates.
    
    Args:
        target_lat (float): Target latitude
        target_lon (float): Target longitude
        data (pd.DataFrame): DataFrame containing location data
        radius_km (float): Search radius in kilometers (default: 25km)
    
    Returns:
        pd.DataFrame: DataFrame of locations within the radius, sorted by distance
    """
    try:
        if data.empty:
            return pd.DataFrame()
        
        # Ensure required columns exist
        required_cols = ['Latitude', 'Longitude']
        for col in required_cols:
            if col not in data.columns:
                print(f"Required column '{col}' not found in data")
                return pd.DataFrame()
        
        # Calculate distances and filter
        results = []
        
        for idx, row in data.iterrows():
            try:
                lat = float(row['Latitude'])
                lon = float(row['Longitude'])
                
                # Skip rows with invalid coordinates
                if pd.isna(lat) or pd.isna(lon):
                    continue
                
                distance = haversine_distance(target_lat, target_lon, lat, lon)
                
                if distance <= radius_km:
                    row_dict = row.to_dict()
                    row_dict['Distance_km'] = distance
                    results.append(row_dict)
                    
            except (ValueError, TypeError):
                # Skip rows with invalid coordinate data
                continue
        
        if not results:
            return pd.DataFrame()
        
        # Convert to DataFrame and sort by distance
        results_df = pd.DataFrame(results)
        results_df = results_df.sort_values('Distance_km')
        
        print(f"Found {len(results_df)} locations within {radius_km} km")
        
        return results_df
        
    except Exception as e:
        print(f"Error in find_locations_within_radius: {str(e)}")
        return pd.DataFrame()
