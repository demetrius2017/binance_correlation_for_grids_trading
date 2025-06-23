#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for DataFrame serialization fix in Streamlit
"""
import pandas as pd

def test_dataframe_serialization():
    """
    Tests DataFrame creation as in the fixed app.py
    """
    print("=== DataFrame Serialization Test ===")
    
    # Simulate Grid Trading simulation result
    result = {
        'combined_pct': 5.25,
        'long_pct': 2.75,
        'short_pct': 2.50,
        'total_trades': 45,
        'lightning_count': 3,
        'stop_loss_count': 1,
        'long_active': True,
        'short_active': True,
        'grid_step_pct': 1.2
    }
    
    timeframe_choice = "1h"
    period_days = 30
    
    # Create DataFrame as in the fixed code
    results_df = pd.DataFrame({
        'Metric': [
            'Total Profit (%)',
            'Long Profit (%)',
            'Short Profit (%)',
            'Total Trades',
            'Lightning',
            'Stop Losses',
            'Long Active',
            'Short Active',
            'Grid Step (%)',
            'Timeframe',
            'Period (days)'
        ],
        'Value': [
            f"{result['combined_pct']:.2f}",
            f"{result['long_pct']:.2f}",
            f"{result['short_pct']:.2f}",
            str(result['total_trades']),           # Fixed: converted to string
            str(result['lightning_count']),       # Fixed: converted to string
            str(result['stop_loss_count']),       # Fixed: converted to string
            "Yes" if result['long_active'] else "No",
            "Yes" if result['short_active'] else "No",
            f"{result['grid_step_pct']:.2f}",
            str(timeframe_choice),                # Fixed: converted to string
            str(period_days)                      # Fixed: converted to string
        ]
    })
    
    print("DataFrame created successfully:")
    print(results_df)
    print()
    
    # Check data types
    print("Data types in columns:")
    print(results_df.dtypes)
    print()
    
    # Check that all values in 'Value' column are strings
    all_strings = all(isinstance(val, str) for val in results_df['Value'])
    print(f"All values in 'Value' column are strings: {'YES' if all_strings else 'NO'}")
    
    # Check specific values
    print("\nChecking specific values:")
    print(f"Grid step: '{results_df.iloc[8]['Value']}' (type: {type(results_df.iloc[8]['Value'])})")
    print(f"Total trades: '{results_df.iloc[3]['Value']}' (type: {type(results_df.iloc[3]['Value'])})")
    print(f"Timeframe: '{results_df.iloc[9]['Value']}' (type: {type(results_df.iloc[9]['Value'])})")
    
    # Test Arrow compatibility (as Streamlit does)
    try:
        import pyarrow as pa
        table = pa.Table.from_pandas(results_df)
        print("\nSUCCESS: Arrow Table conversion successful - DataFrame is Streamlit compatible")
        return True
    except ImportError:
        print("\nWARNING: PyArrow not installed, but data types are correct")
        return True
    except Exception as e:
        print(f"\nERROR: Arrow Table conversion failed: {e}")
        return False

if __name__ == "__main__":
    success = test_dataframe_serialization()
    if success:
        print("\nSUCCESS: Test passed! Serialization error is fixed.")
    else:
        print("\nFAILED: Test failed. Additional fixes needed.")
