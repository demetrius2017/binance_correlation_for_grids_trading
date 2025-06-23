#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Test for corrected stop-loss logic: losses calculated from total capital
"""

import pandas as pd
import numpy as np
from modules.grid_analyzer import GridAnalyzer

def test_capital_based_stop_loss():
    """
    Tests the corrected stop-loss logic where losses are calculated from total capital
    """
    print("=== TEST: CAPITAL-BASED STOP-LOSS LOGIC ===")
    print()
    
    # Mock collector
    class MockCollector:
        def __init__(self):
            self.client = None
    
    collector = MockCollector()
    analyzer = GridAnalyzer(collector)  # type: ignore
    
    # Create test scenario:
    # 1. Some profitable trades first (build capital)
    # 2. Then a stop-loss event
    data = []
    base_price = 1.0
    
    print("SCENARIO:")
    print("1. Start with 100% capital")
    print("2. Make some profitable trades (increase capital)")
    print("3. Trigger stop-loss (should reduce total capital)")
    print()
    
    # 5 profitable candles with wicks
    for i in range(5):
        data.append({
            'open': base_price,
            'high': base_price * 1.008,  # 0.8% upper wick
            'low': base_price * 0.992,   # 0.8% lower wick  
            'close': base_price * 1.002, # Small green body
            'volume': 1000
        })
        base_price *= 1.002
    
    # 1 stop-loss candle (big drop)
    data.append({
        'open': base_price,
        'high': base_price * 1.01,
        'low': base_price * 0.90,    # 10% drop
        'close': base_price * 0.92,  # 8% drop (triggers 5% stop-loss)
        'volume': 1000
    })
    
    df = pd.DataFrame(data)
    
    print("TEST DATA:")
    print(f"- 5 profitable candles (0.8% wicks each)")
    print(f"- 1 stop-loss candle (8% drop)")
    print()
    
    # Run simulation
    result = analyzer.estimate_dual_grid_by_candles(
        df,
        grid_range_pct=20.0,
        grid_step_pct=0.5,  # 0.5% grid step
        use_real_commissions=True,
        stop_loss_pct=5.0,  # 5% stop-loss threshold
        stop_loss_coverage=0.5,
        stop_loss_strategy="independent"
    )
    
    print("RESULTS:")
    print("-" * 30)
    print(f"Combined PnL: {result['combined_pct']:.2f}%")
    print(f"Long PnL: {result['long_pct']:.2f}%")
    print(f"Short PnL: {result['short_pct']:.2f}%")
    print(f"Stop losses triggered: {result['stop_loss_count']}")
    print(f"Total trades: {result['total_trades']:.0f}")
    print()
    
    # Analysis
    print("ANALYSIS:")
    print("-" * 15)
    
    # Check if stop-loss was triggered
    if result['stop_loss_count'] > 0:
        print("✅ Stop-loss was triggered")
        
        # With new logic, both grids should lose money from the stop-loss
        if result['long_pct'] < 0 or result['short_pct'] < 0:
            print("✅ Stop-loss caused losses (as expected)")
        else:
            print("⚠️ Both grids still profitable despite stop-loss")
        
        # Combined result should be significantly affected
        if result['combined_pct'] < 10:
            print("✅ Stop-loss significantly impacted total result")
        else:
            print("⚠️ Stop-loss impact seems limited")
            
    else:
        print("❌ Stop-loss was not triggered (8% > 5% threshold)")
    
    print()
    print("EXPECTED BEHAVIOR:")
    print("- Initial capital: 100%")
    print("- After 5 profitable candles: ~105-110%")
    print("- After stop-loss (8% from ~107%): ~99-101%")
    print("- Final result: Small profit or small loss")
    
    return result

def compare_old_vs_new_logic():
    """
    Compares the impact of old vs new stop-loss logic
    """
    print("\n=== COMPARISON: OLD vs NEW STOP-LOSS LOGIC ===")
    print()
    
    print("OLD LOGIC (INCORRECT):")
    print("- Stop-loss: 8% drop")
    print("- Loss calculation: Only affected one grid")
    print("- Result: Long -8%, Short unchanged")
    print("- Total impact: -4% (averaged)")
    print()
    
    print("NEW LOGIC (CORRECT):")
    print("- Stop-loss: 8% drop")
    print("- Loss calculation: 8% from total capital")
    print("- Result: Both grids lose proportionally")
    print("- Total impact: -8% from current capital")
    print()
    
    print("EXAMPLE:")
    print("- Current capital: 120% (after profits)")
    print("- Stop-loss: 8% drop")
    print("- Loss amount: 120% × 8% = 9.6%")
    print("- New capital: 120% - 9.6% = 110.4%")
    print("- Result: 10.4% profit instead of huge gains")

if __name__ == "__main__":
    test_capital_based_stop_loss()
    compare_old_vs_new_logic()
