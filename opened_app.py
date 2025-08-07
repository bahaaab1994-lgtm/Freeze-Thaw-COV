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
        if hasattr(unique_states, 'tolist'):
            states_list = unique_states.tolist()
        else:
            states_list = list(unique_states)
        # Remove any empty strings and ensure proper deduplication
        clean_states = [state for state in states_list if state and state.strip()]
        # Use set to ensure no duplicates, then sort
        return sorted(list(set(clean_states)))
    except Exception as e:
        st.error(f"Error loading states for season {season}: {str(e)}")
        return []

def calculate_statistics(location_data, available_seasons):
    """Calculate 20-year, 5-year averages and COV for a specific location"""
    try:
        # Get data for all seasons for this location
        location_stats = []
        
        for season in available_seasons:
            try:
                season_data = load_freeze_thaw_data_by_season(season)
                if season_data.empty:
                    continue
                
                # Find matching record for this location
                matching_record = season_data[
                    (season_data['State'] == location_data['State']) &
                    (season_data['County'] == location_data['County']) &
                    (abs(season_data['Latitude'] - location_data['Latitude']) < 0.001) &
                    (abs(season_data['Longitude'] - location_data['Longitude']) < 0.001)
                ]
                
                if not matching_record.empty:
                    record = matching_record.iloc[0]
                    location_stats.append({
                        'Season': season,
                        'Total_Cycles': record['Total_Freeze_Thaw_Cycles'],
                        'Damaging_Cycles': record['Damaging_Freeze_Thaw_Cycles']
                    })
            except Exception as e:
                continue
        
        if not location_stats:
            return None
        
        # Convert to DataFrame and sort by season (most recent first)
        stats_df = pd.DataFrame(location_stats)
        stats_df = stats_df.sort_values('Season', ascending=False)
        
        # Calculate statistics
        total_cycles = stats_df['Total_Cycles'].values
        damaging_cycles = stats_df['Damaging_Cycles'].values
        
        # 20-year average (all available data, up to 20 years)
        total_20yr_avg = np.mean(total_cycles[:20]) if len(total_cycles) > 0 else 0
        damaging_20yr_avg = np.mean(damaging_cycles[:20]) if len(damaging_cycles) > 0 else 0
        
        # 5-year average
        total_5yr_avg = np.mean(total_cycles[:5]) if len(total_cycles) > 0 else 0
        damaging_5yr_avg = np.mean(damaging_cycles[:5]) if len(damaging_cycles) > 0 else 0
        
        # COV calculations
        total_cov = (np.std(total_cycles) / np.mean(total_cycles) * 100) if len(total_cycles) > 1 and np.mean(total_cycles) > 0 else 0
        damaging_cov = (np.std(damaging_cycles) / np.mean(damaging_cycles) * 100) if len(damaging_cycles) > 1 and np.mean(damaging_cycles) > 0 else 0
        
        return {
            'data': stats_df,
            'total_20yr_avg': total_20yr_avg,
            'damaging_20yr_avg': damaging_20yr_avg,
            'total_5yr_avg': total_5yr_avg,
            'damaging_5yr_avg': damaging_5yr_avg,
            'total_cov': total_cov,
            'damaging_cov': damaging_cov,
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
    
    available_seasons = get_available_seasons()
    if not available_seasons:
        st.error("No freeze-thaw data files found. Please add Excel files to the project.")
        return
    
    # Create columns for season selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        selected_season = st.selectbox(
            "Choose a season:",
            available_seasons,
            index=len(available_seasons)-1,  # Select most recent season by default
            help="Select the season for which you want to query freeze-thaw data"
        )
    
    with col2:
        st.metric("Available Seasons", len(available_seasons))
    
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
        state = st.text_input(
            "State", 
            placeholder="e.g., Colorado",
            help="Enter the state name"
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
        if not state or state.strip() == "":
            st.error("Please enter a state name.")
            return
        
        if latitude is None or longitude is None:
            st.error("Please enter both latitude and longitude values.")
            return
        
        # Load fresh data for the selected season for the search
        search_data = load_freeze_thaw_data_by_season(selected_season)
        if search_data.empty:
            st.error(f"No data available for season {selected_season}")
            return
        
        # Normalize state input
        state_normalized = state.strip().title()
        
        # Filter data by state first
        state_data = search_data[search_data['State'].str.contains(state_normalized, case=False, na=False)]
        
        if state_data.empty:
            st.error(f"No data found for state: {state_normalized}")
            
            # Show available states
            available_states = sorted(search_data['State'].unique())
            st.info("Available states in database:")
            st.write(", ".join(available_states))
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
                stats = calculate_statistics(nearest_location, available_seasons)
            
            if stats is None:
                st.warning("Unable to calculate historical statistics for this location.")
            else:
                # Display statistical summary
                st.subheader("🎯 Statistical Summary")
                
                # Create metrics layout
                metric_col1, metric_col2 = st.columns(2)
                
                with metric_col1:
                    st.markdown("**Total Freeze-Thaw Cycles**")
                    
                    avg_col1, avg_col2 = st.columns(2)
                    with avg_col1:
                        years_text = f"{min(stats['years_available'], 20)}-Year Average"
                        st.metric(years_text, f"{stats['total_20yr_avg']:.1f}")
                    with avg_col2:
                        years_text = f"{min(stats['years_available'], 5)}-Year Average" 
                        st.metric(years_text, f"{stats['total_5yr_avg']:.1f}")
                    
                    # COV for total cycles
                    total_var_cat, total_var_icon = get_variability_category(stats['total_cov'])
                    st.metric(
                        "Variability (COV)",
                        f"{stats['total_cov']:.1f}%",
                        help="Coefficient of Variation - measures data variability"
                    )
                    st.markdown(f"{total_var_icon} **{total_var_cat} Variability**")
                
                with metric_col2:
                    st.markdown("**Damaging Freeze-Thaw Cycles**")
                    
                    avg_col1, avg_col2 = st.columns(2)
                    with avg_col1:
                        years_text = f"{min(stats['years_available'], 20)}-Year Average"
                        st.metric(years_text, f"{stats['damaging_20yr_avg']:.1f}")
                    with avg_col2:
                        years_text = f"{min(stats['years_available'], 5)}-Year Average"
                        st.metric(years_text, f"{stats['damaging_5yr_avg']:.1f}")
                    
                    # COV for damaging cycles
                    damaging_var_cat, damaging_var_icon = get_variability_category(stats['damaging_cov'])
                    st.metric(
                        "Variability (COV)",
                        f"{stats['damaging_cov']:.1f}%",
                        help="Coefficient of Variation - measures data variability"
                    )
                    st.markdown(f"{damaging_var_icon} **{damaging_var_cat} Variability**")
                
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
                    damage_percentage_20yr = (stats['damaging_20yr_avg'] / stats['total_20yr_avg'] * 100) if stats['total_20yr_avg'] > 0 else 0
                    damage_percentage_5yr = (stats['damaging_5yr_avg'] / stats['total_5yr_avg'] * 100) if stats['total_5yr_avg'] > 0 else 0
                    
                    st.markdown("### 🔍 Analysis Summary")
                    st.info(
                        f"**Long-term Analysis ({min(stats['years_available'], 20)} years):** "
                        f"{damage_percentage_20yr:.1f}% of freeze-thaw cycles are classified as potentially damaging.\n\n"
                        f"**Recent Analysis ({min(stats['years_available'], 5)} years):** "
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
    This application provides freeze-thaw cycle data with comprehensive statistical analysis from monitoring stations across various states.
    
    **Statistical Features:**
    - **Multi-year Averages**: Shows both long-term (up to 20 years) and recent (5 years) trends
    - **Variability Analysis**: Coefficient of Variation (COV) measures data consistency over time
    - **Historical Context**: Individual season data for the most recent 5 years
    
    **Data Definitions:**
    - **Total Freeze-Thaw Cycles**: All freezing events during the monitoring period
    - **Damaging Freeze-Thaw Cycles**: Cycles when Degree of Saturation (DOS) exceeded 80%, indicating potential for concrete damage
    - **Each season represents a winter period from September to April**
    
    *Note: Results are based on the nearest available monitoring station and may not reflect exact conditions at your specific location.*
    """)

if __name__ == "__main__":
    main()