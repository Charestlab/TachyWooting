#!/usr/bin/env python3
"""
Test script to verify threshold is logged in HDF5
"""
import h5py

def main():
    print("\n" + "="*60)
    print("Checking HDF5 attributes for threshold")
    print("="*60)
    
    with h5py.File("/tmp/test_none_duration.hdf5", "r") as f:
        print("\nFile structure:")
        print(f"  Root keys: {list(f.keys())}")
        
        if "trials" in f:
            trials_group = f["trials"]
            print(f"  Trials: {list(trials_group.keys())}")
            
            trial = trials_group["0001"]
            print(f"\nTrial 0001 attributes:")
            for attr_name in trial.attrs.keys():
                attr_value = trial.attrs[attr_name]
                if isinstance(attr_value, bytes):
                    attr_value = attr_value.decode('utf-8')
                print(f"    {attr_name}: {attr_value}")
            
            if "threshold" in trial.attrs:
                threshold = trial.attrs["threshold"]
                print(f"\n✓ Threshold found: {threshold}")
            else:
                print(f"\n✗ Threshold NOT found in attributes")
                print(f"  This file was created before threshold logging was added.")

if __name__ == "__main__":
    main()
