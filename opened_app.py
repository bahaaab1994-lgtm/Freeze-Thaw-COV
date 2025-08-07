# -*- coding: utf-8 -*-
"""
Created on Wed Aug  6 21:15:35 2025

@author: bahaa
"""

import streamlit as st
import pandas as pd
import numpy as np
from data_loader import load_freeze_thaw_data, load_freeze_thaw_data_by_season, get_available_seasons
from coordinate_matcher import find_nearest_location

# Set page configuration
st.set_page_config(
    page_title="Freeze-Thaw Cycle Data Query",
    page_icon="❄️",
    layout="centered"
)

# Load data
@st.cache_data
def get_data():
    """Load and cache the freeze-thaw cycle data"""
    return load_freeze_thaw_data()

@st.cache_data
def get_states_for_season(season):
    """Get available states for a specific season"""
    try:
        data = load_freeze_thaw_data_by_season(season)
        if data.empty:
            return []
        # Get unique states, clean and deduplicate
        states = data['State'].dropna().astype(str).str.strip()
        unique_states = states.unique()
        clean_states = [state for state in unique_states if state and state.strip()]
        return sorted(list(set(clean_states)))
    except Exception as e:
        st.error(f"Error loading states for season {season}: {str(e)}")
        return []

def calculate_statistics(location_data, available_seasons):
    """Calculate statistics for all years and last 5 years for a specific location"""
    try:
        # Get data for all seasons for this location
        location_stats = []
        
        print(f"Calculating statistics for: {location_data['County']}, {location_data['State']}")
        print(f"Target coordinates: {location_data['Latitude']:.6f}, {location_data['Longitude']:.6f}")
        
        for season in available_seasons:
            try:
                season_data = load_freeze_thaw_data_by_season(season)
                if season_data.empty:
                    continue
                
                # First try exact match by State and County
                exact_match = season_data[
                    (season_data['State'].str.strip().str.upper() == location_data['State'].strip().upper()) &
                    (season_data['County'].str.strip().str.upper() == location_data['County'].strip().upper())
                ]
                
                if not exact_match.empty:
                    # If multiple matches, find the one with closest coordinates
                    if len(exact_match) > 1:
                        distances = []
                        for idx, row in exact_match.iterrows():
                            lat_diff = abs(row['Latitude'] - location_data['Latitude'])
                            lon_diff = abs(row['Longitude'] - location_data['Longitude'])
                            distance = (lat_diff**2 + lon_diff**2)**0.5
                            distances.append(distance)
                        
                        closest_idx = exact_match.index[np.argmin(distances)]
                        record = exact_match.loc[closest_idx]
                    else:
                        record = exact_match.iloc[0]
                    
                    location_stats.append({
                        'Season': season,
                        'Total_Cycles': record['Total_Freeze_Thaw_Cycles'],
                        'Damaging_Cycles': record['Damaging_Freeze_Thaw_Cycles']
                    })
                    print(f"Found data for {season}: Total={record['Total_Freeze_Thaw_Cycles']}, Damaging={record['Damaging_Freeze_Thaw_Cycles']}")
                else:
                    print(f"No matching data found for {season}")
                    
            except Exception as e:
                print(f"Error processing season {season}: {str(e)}")
                continue
        
        print(f"Total seasons with data: {len(location_stats)}")
        
        if not location_stats:
            return None
        
        # Convert to DataFrame and sort by season (most recent first)
        stats_df = pd.DataFrame(location_stats)
        stats_df = stats_df.sort_values('Season', ascending=False)
        
        # Get data arrays
        total_cycles = stats_df['Total_Cycles'].values
        damaging_cycles = stats_df['Damaging_Cycles'].values
        
        # ALL YEARS STATISTICS
        total_all_avg = float(np.mean(total_cycles)) if len(total_cycles) > 0 else 0
        damaging_all_avg = float(np.mean(damaging_cycles)) if len(damaging_cycles) > 0 else 0
        
        total_all_cov = float((np.std(total_cycles) / np.mean(total_cycles) * 100)) if len(total_cycles) > 1 and np.mean(total_cycles) > 0 else 0
        damaging_all_cov = float((np.std(damaging_cycles) / np.mean(damaging_cycles) * 100)) if len(damaging_cycles) > 1 and np.mean(damaging_cycles) > 0 else 0
        
        # LAST 5 YEARS STATISTICS
        total_5yr_avg = float(np.mean(total_cycles[:5])) if len(total_cycles) >= 5 else float(np.mean(total_cycles)) if len(total_cycles) > 0 else 0
        damaging_5yr_avg = float(np.mean(damaging_cycles[:5])) if len(damaging_cycles) >= 5 else float(np.mean(damaging_cycles)) if len(damaging_cycles) > 0 else 0
        
        # COV for last 5 years
        recent_total = total_cycles[:5] if len(total_cycles) >= 5 else total_cycles
        recent_damaging = damaging_cycles[:5] if len(damaging_cycles) >= 5 else damaging_cycles
        
        total_5yr_cov = float((np.std(recent_total) / np.mean(recent_total) * 100)) if len(recent_total) > 1 and np.mean(recent_total) > 0 else 0
        damaging_5yr_cov = float((np.std(recent_damaging) / np.mean(recent_damaging) * 100)) if len(recent_damaging) > 1 and np.mean(recent_damaging) > 0 else 0
        
        return {
            'data': stats_df,
            'total_all_avg': total_all_avg,
            'damaging_all_avg': damaging_all_avg,
            'total_all_cov': total_all_cov,
            'damaging_all_cov': damaging_all_cov,
            'total_5yr_avg': total_5yr_avg,
            'damaging_5yr_avg': damaging_5yr_avg,
            'total_5yr_cov': total_5yr_cov,
            'damaging_5yr_cov': damaging_5yr_cov,
            'years_available': len(total_cycles)
        }
    except Exception as e:
        st.error(f"Error calculating statistics: {str(e)}")
        return None

def get_variability_category(cov):
    """Categorize variability based on COV"""
    if cov < 15:
        return "Low", "🟢"
    elif cov <= 40:
        return "Moderate", "🟡"
    else:
        return "High", "🔴"

def main():
    st.title("❄️ Freeze-Thaw Cycle Data")
    st.markdown("Select a season and location details to find freeze-thaw cycle information with statistical analysis.")
    
    # Season selection
    st.subheader("📅 Select Season")
    
    all_seasons = get_available_seasons()
    if not all_seasons:
        st.error("No freeze-thaw data files found. Please add Excel files to the project.")
        return
    
    # Show only last 5 recent seasons
    recent_seasons = sorted(all_seasons, reverse=True)[:5]
    
    # Create columns for season selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_season = st.selectbox(
            "Choose a season (Last 5 seasons):",
            recent_seasons,
            index=0,  # Select most recent season by default
            help="Select the season for which you want to query freeze-thaw data"
        )
    
    with col2:
        st.metric("Recent Seasons", len(recent_seasons))
    
    # Load data for selected season
    try:
        data = load_freeze_thaw_data_by_season(selected_season)
        if data.empty:
            st.error(f"No data found for season {selected_season}")
            return
    except Exception as e:
        st.error(f"Error loading data: {str(e)}")
        return
    
    # Get available states for the selected season
    available_states = get_states_for_season(selected_season)
    if not available_states:
        st.error(f"No states found for season {selected_season}")
        return
    
    # Separator
    st.markdown("---")
    
    # Input form
    st.subheader("🔍 Location Query")
    
    # Add helpful note about coordinates
    st.info("💡 **Coordinate Tips:** For US locations, longitude values are negative (west of Greenwich). "
            "For example: Denver, CO is at 39.7392, -104.9903")
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        state = st.selectbox(
            "State",
            available_states,
            index=0,
            help="Select the state name"
        )
    
    with col2:
        latitude = st.number_input(
            "Latitude",
            min_value=-90.0,
            max_value=90.0,
            value=None,
            format="%.6f",
            help="Enter latitude in decimal degrees"
        )
    
    with col3:
        longitude = st.number_input(
            "Longitude",
            min_value=-180.0,
            max_value=180.0,
            value=None,
            format="%.6f",
            help="Enter longitude in decimal degrees"
        )
    
    # Search button
    if st.button("Search for Freeze-Thaw Data", type="primary"):
        # Validate inputs
        if not state:
            st.error("Please select a state.")
            return
        
        if latitude is None or longitude is None:
            st.error("Please enter both latitude and longitude values.")
            return
        
        # Load fresh data for the selected season for the search
        search_data = load_freeze_thaw_data_by_season(selected_season)
        if search_data.empty:
            st.error(f"No data available for season {selected_season}")
            return
        
        # Use selected state directly
        state_normalized = state
        
        # Filter data by state first
        state_data = search_data[search_data['State'].str.contains(state_normalized, case=False, na=False)]
        
        if state_data.empty:
            st.error(f"No data found for state: {state_normalized}")
            
            # Show available states
            available_states_list = sorted(search_data['State'].unique())
            st.info("Available states in database:")
            st.write(", ".join(available_states_list))
            return
        
        # Find nearest location
        try:
            nearest_location, distance = find_nearest_location(
                latitude, longitude, state_data
            )
            
            if nearest_location is None:
                st.warning(
                    f"No monitoring stations found within 50 km of the specified coordinates in {state_normalized}. "
                    "Try searching with coordinates closer to populated areas."
                )
                
                # Show available locations in the state
                st.subheader(f"Available monitoring stations in {state_normalized}:")
                display_data = state_data[['County', 'Latitude', 'Longitude', 'Total_Freeze_Thaw_Cycles', 'Damaging_Freeze_Thaw_Cycles']].copy()
                st.dataframe(display_data, use_container_width=True)
                return
            
            # Display results
            st.success(f"✅ Nearest monitoring station found!")
            
            # Location information
            st.subheader("📍 Location Details")
            
            info_col1, info_col2 = st.columns(2)
            
            with info_col1:
                st.metric("County", nearest_location['County'])
                st.metric("State", nearest_location['State'])
                st.metric("Distance", f"{distance:.2f} km")
            
            with info_col2:
                st.metric("Station Latitude", f"{nearest_location['Latitude']:.6f}")
                st.metric("Station Longitude", f"{nearest_location['Longitude']:.6f}")
            
            # Calculate historical statistics
            st.subheader("📊 Historical Analysis")
            
            with st.spinner("Calculating historical statistics..."):
                stats = calculate_statistics(nearest_location, all_seasons)
            
            if stats is None:
                st.warning("Unable to calculate historical statistics for this location.")
            else:
                # Display statistical summary
                st.subheader("🎯 Statistical Summary")
                
                # ALL YEARS SECTION
                st.markdown("### 📈 All Years Analysis")
                all_col1, all_col2 = st.columns(2)
                
                with all_col1:
                    st.markdown("**Total Freeze-Thaw Cycles (All Years)**")
                    st.metric("Average", f"{stats['total_all_avg']:.1f}")
                    
                    total_all_var_cat, total_all_var_icon = get_variability_category(stats['total_all_cov'])
                    st.metric("COV", f"{stats['total_all_cov']:.1f}%")
                    st.markdown(f"{total_all_var_icon} **{total_all_var_cat} Variability**")
                
                with all_col2:
                    st.markdown("**Damaging Freeze-Thaw Cycles (All Years)**")
                    st.metric("Average", f"{stats['damaging_all_avg']:.1f}")
                    
                    damaging_all_var_cat, damaging_all_var_icon = get_variability_category(stats['damaging_all_cov'])
                    st.metric("COV", f"{stats['damaging_all_cov']:.1f}%")
                    st.markdown(f"{damaging_all_var_icon} **{damaging_all_var_cat} Variability**")
                
                # LAST 5 YEARS SECTION
                st.markdown("### 📊 Last 5 Years Analysis")
                recent_col1, recent_col2 = st.columns(2)
                
                with recent_col1:
                    st.markdown("**Total Freeze-Thaw Cycles (Last 5 Years)**")
                    st.metric("Average", f"{stats['total_5yr_avg']:.1f}")
                    
                    total_5yr_var_cat, total_5yr_var_icon = get_variability_category(stats['total_5yr_cov'])
                    st.metric("COV", f"{stats['total_5yr_cov']:.1f}%")
                    st.markdown(f"{total_5yr_var_icon} **{total_5yr_var_cat} Variability**")
                
                with recent_col2:
                    st.markdown("**Damaging Freeze-Thaw Cycles (Last 5 Years)**")
                    st.metric("Average", f"{stats['damaging_5yr_avg']:.1f}")
                    
                    damaging_5yr_var_cat, damaging_5yr_var_icon = get_variability_category(stats['damaging_5yr_cov'])
                    st.metric("COV", f"{stats['damaging_5yr_cov']:.1f}%")
                    st.markdown(f"{damaging_5yr_var_icon} **{damaging_5yr_var_cat} Variability**")
                
                # Variability interpretation guide
                st.info(
                    "**Variability Categories:** "
                    "🟢 Low (COV < 15%) • 🟡 Moderate (COV 15-40%) • 🔴 High (COV > 40%)"
                )
                
                # Current season data
                st.subheader(f"❄️ Current Season Data ({selected_season})")
                
                cycle_col1, cycle_col2 = st.columns(2)
                
                with cycle_col1:
                    st.metric(
                        "Total Freeze-Thaw Cycles",
                        int(nearest_location['Total_Freeze_Thaw_Cycles']),
                        help="Total number of freeze-thaw cycles recorded at this location"
                    )
                
                with cycle_col2:
                    st.metric(
                        "Damaging Freeze-Thaw Cycles",
                        int(nearest_location['Damaging_Freeze_Thaw_Cycles']),
                        help="Number of freeze-thaw cycles that could cause structural damage"
                    )
                
                # Recent 5 seasons detailed data
                st.subheader("📈 Last 5 Seasons Detail")
                
                recent_data = stats['data'].head(5)  # Already sorted by most recent
                if not recent_data.empty:
                    # Prepare display data
                    display_recent = recent_data[['Season', 'Total_Cycles', 'Damaging_Cycles']].copy()
                    display_recent.columns = ['Season', 'Total Cycles', 'Damaging Cycles']
                    
                    st.dataframe(
                        display_recent, 
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.warning("No recent season data available for detailed display.")
                
                # Additional analysis
                if stats['years_available'] >= 2:
                    damage_percentage_all = (stats['damaging_all_avg'] / stats['total_all_avg'] * 100) if stats['total_all_avg'] > 0 else 0
                    damage_percentage_5yr = (stats['damaging_5yr_avg'] / stats['total_5yr_avg'] * 100) if stats['total_5yr_avg'] > 0 else 0
                    
                    st.markdown("### 🔍 Analysis Summary")
                    st.info(
                        f"**All Years Analysis ({stats['years_available']} years):** "
                        f"{damage_percentage_all:.1f}% of freeze-thaw cycles are classified as potentially damaging.\n\n"
                        f"**Recent Analysis (Last 5 years):** "
                        f"{damage_percentage_5yr:.1f}% of freeze-thaw cycles are classified as potentially damaging."
                    )
            
            # Show location on map
            st.subheader("📍 Station Location")
            map_data = pd.DataFrame({
                'lat': [nearest_location['Latitude']],
                'lon': [nearest_location['Longitude']]
            })
            st.map(map_data, zoom=8)
            
        except Exception as e:
            st.error(f"Error processing search: {str(e)}")
    
    # Additional information
    st.markdown("---")
    st.subheader("ℹ️ About This Data")
    st.markdown("""
    This application provides freeze-thaw cycle data from monitoring stations across various states.
    
    - **Each season represents a winter period from September to April.**
    - **Total Freeze-Thaw Cycles**: Represents all freezing events that the concrete experienced during the monitoring period, regardless of the moisture condition.
    - **Damaging Freeze-Thaw Cycles**: Refers to the subset of freeze-thaw cycles during which the Degree of Saturation (DOS) exceeded the critical threshold of 80%, making the concrete susceptible to freeze-thaw damage.
    
    *Note: Results are based on the nearest available monitoring station and may not reflect exact conditions at your specific location.*
    """)

if __name__ == "__main__":
    main()