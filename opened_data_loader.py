# -*- coding: utf-8 -*-
"""
Created on Wed Aug  6 21:16:47 2025

@author: bahaa
"""

import pandas as pd
import os
import glob
from pathlib import Path

def load_freeze_thaw_data():
    """
    Load all freeze-thaw data from Excel files in the current directory.
    Assumes Excel files contain freeze-thaw data with consistent column structure.
    """
    try:
        # Look for Excel files in the current directory
        excel_files = glob.glob("*.xlsx") + glob.glob("*.xls")
        
        if not excel_files:
            print("No Excel files found in the current directory")
            return pd.DataFrame()
        
        all_data = []
        
        for file in excel_files:
            try:
                # Read Excel file
                df = pd.read_excel(file)
                
                # Add season column based on filename if not present
                if 'Season' not in df.columns:
                    # Extract season from filename (assuming format like "2023-2024.xlsx")
                    season = Path(file).stem
                    df['Season'] = season
                
                all_data.append(df)
                print(f"Loaded data from {file}: {len(df)} records")
                
            except Exception as e:
                print(f"Error loading {file}: {str(e)}")
                continue
        
        if all_data:
            combined_data = pd.concat(all_data, ignore_index=True)
            print(f"Total records loaded: {len(combined_data)}")
            return combined_data
        else:
            return pd.DataFrame()
            
    except Exception as e:
        print(f"Error in load_freeze_thaw_data: {str(e)}")
        return pd.DataFrame()

def load_freeze_thaw_data_by_season(season):
    """
    Load freeze-thaw data for a specific season.
    
    Args:
        season (str): The season identifier (e.g., "2023-2024")
    
    Returns:
        pd.DataFrame: Data for the specified season
    """
    try:
        # Try to load from a specific file first
        potential_files = [
            f"{season}.xlsx",
            f"{season}.xls",
            f"FT_{season}.xlsx",
            f"FT_{season}.xls"
        ]
        
        for filename in potential_files:
            if os.path.exists(filename):
                df = pd.read_excel(filename)
                if 'Season' not in df.columns:
                    df['Season'] = season
                print(f"Loaded season {season} from {filename}: {len(df)} records")
                return df
        
        # If no specific file found, try to extract from combined data
        all_data = load_freeze_thaw_data()
        if all_data.empty:
            return pd.DataFrame()
        
        # Filter by season
        season_data = all_data[all_data['Season'] == season]
        print(f"Extracted season {season} from combined data: {len(season_data)} records")
        return season_data
        
    except Exception as e:
        print(f"Error loading season {season}: {str(e)}")
        return pd.DataFrame()

def get_available_seasons():
    """
    Get list of available seasons from Excel files.
    
    Returns:
        list: Sorted list of available seasons
    """
    try:
        seasons = set()
        
        # Look for Excel files in the current directory
        excel_files = glob.glob("*.xlsx") + glob.glob("*.xls")
        
        for file in excel_files:
            try:
                # Extract season from filename
                season = Path(file).stem
                # Remove common prefixes if present
                if season.startswith("FT_"):
                    season = season[3:]
                
                seasons.add(season)
                
            except Exception as e:
                print(f"Error processing file {file}: {str(e)}")
                continue
        
        # Also try to get seasons from data if files contain Season column
        try:
            all_data = load_freeze_thaw_data()
            if not all_data.empty and 'Season' in all_data.columns:
                data_seasons = all_data['Season'].unique()
                seasons.update(data_seasons)
        except:
            pass
        
        # Sort seasons (assuming format like "2023-2024")
        sorted_seasons = sorted(list(seasons))
        print(f"Available seasons: {sorted_seasons}")
        return sorted_seasons
        
    except Exception as e:
        print(f"Error getting available seasons: {str(e)}")
        return []