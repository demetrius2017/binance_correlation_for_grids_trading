#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Simple test for fixed Grid Trading simulation logic
"""

import pandas as pd
import numpy as np
from modules.grid_analyzer import GridAnalyzer

def quick_test():
    """
    Quick test of the fixed simulation logic
    """
    print("=== QUICK TEST OF FIXED SIMULATION ===")
    
    # Mock collector
    class MockCollector:
        def __init__(self):
            self.client = None
      collector = MockCollector()
    analyzer = GridAnalyzer(collector)  # type: ignore
    
    # Create simple test data with 1 stop-loss scenario
    data = []
    base_price = 1.0
    
    # 10 normal candles
    for i in range(10):
        data.append({
            'open': base_price,
            'high': base_price * 1.002,  # 0.2% upper wick
            'low': base_price * 0.998,   # 0.2% lower wick  
            'close': base_price * 1.001, # Small body
            'volume': 1000
        })
        base_price *= 1.001
    
    # 1 stop-loss candle (big drop)
    data.append({
        'open': base_price,
        'high': base_price * 1.01,
        'low': base_price * 0.92,    # 8% drop (triggers stop-loss)
        'close': base_price * 0.93,  # 7% drop
        'volume': 1000
    })
    
    df = pd.DataFrame(data)
    
    print("Test data: 11 candles, last one has 7% drop (should trigger stop-loss)")
    print()
    
    # Run simulation
    result = analyzer.estimate_dual_grid_by_candles(
        df,
        grid_range_pct=20.0,
        grid_step_pct=0.5,
        use_real_commissions=True,
        stop_loss_pct=5.0,
        stop_loss_coverage=0.5,
        stop_loss_strategy="independent"
    )
    
    print("RESULTS:")
    print(f"Combined PnL: {result['combined_pct']:.2f}%")
    print(f"Long PnL: {result['long_pct']:.2f}%") 
    print(f"Short PnL: {result['short_pct']:.2f}%")
    print(f"Stop losses: {result['stop_loss_count']}")
    print(f"Total trades: {result['total_trades']:.0f}")
    print()
    
    # Check if stop-loss was properly accounted
    if result['stop_loss_count'] > 0:
        print("✅ Stop-loss detected and processed")
        if result['long_pct'] < 0:
            print("✅ Long PnL is negative (stop-loss caused real loss)")
        else:
            print("⚠️ Long PnL should be negative after stop-loss")
    else:
        print("❌ Stop-loss not detected")
    
    # Check for realistic results
    if abs(result['combined_pct']) < 50:
        print("✅ Results are in realistic range (<50%)")
    else:
        print("❌ Results still seem unrealistic")
    
    print()
    print("BEFORE FIX: Would show ~1000%+ profit")
    print("AFTER FIX: Should show realistic profit/loss with stop-loss impact")

if __name__ == "__main__":
    quick_test()
